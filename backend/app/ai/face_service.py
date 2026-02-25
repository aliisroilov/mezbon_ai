"""InsightFace service — face detection, embedding extraction, and identification."""

import asyncio
import base64
import os
import time
import uuid
from functools import partial

import cv2
import numpy as np
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AIServiceError, ForbiddenError, ValidationError
from app.core.redis import get_redis
from app.schemas.ai import BoundingBox, DetectedFace, FaceDetectionResponse, FaceIdentifyResponse

# Minimum detection confidence to accept a face
_MIN_CONFIDENCE = 0.6

# Cosine similarity threshold for a positive identity match
_MATCH_THRESHOLD = 0.6

# How long to cache clinic embeddings in Redis (seconds)
_EMBEDDING_CACHE_TTL = 300  # 5 minutes

# AES-GCM nonce size (must match core/encryption.py)
_NONCE_SIZE = 12


class FaceService:
    """Async wrapper around InsightFace for face detection and recognition."""

    def __init__(self) -> None:
        self.app = None
        self._initialized = False

    async def initialize(self) -> None:
        """Load InsightFace model at startup.

        Runs model loading in a thread pool since it is CPU-heavy.
        """
        start = time.monotonic()
        loop = asyncio.get_running_loop()

        try:
            self.app = await loop.run_in_executor(None, self._load_model)
            self._initialized = True
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "FaceService initialized",
                extra={
                    "model": settings.INSIGHTFACE_MODEL,
                    "device": settings.INSIGHTFACE_DEVICE,
                    "load_time_ms": round(elapsed_ms, 1),
                },
            )
        except Exception as exc:
            logger.error("Failed to initialize FaceService", extra={"error": str(exc)})
            raise AIServiceError(f"InsightFace initialization failed: {exc}") from exc

    @staticmethod
    def _load_model():
        """Synchronous model loading — called in executor."""
        import insightface
        from insightface.app import FaceAnalysis

        fa = FaceAnalysis(
            name=settings.INSIGHTFACE_MODEL,
            providers=(
                ["CUDAExecutionProvider"] if settings.INSIGHTFACE_DEVICE == "cuda"
                else ["CPUExecutionProvider"]
            ),
        )
        fa.prepare(ctx_id=0 if settings.INSIGHTFACE_DEVICE == "cuda" else -1, det_size=(640, 640))
        return fa

    async def detect_faces(self, image_bytes: bytes) -> FaceDetectionResponse:
        """Detect all faces in an image.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG).

        Returns:
            FaceDetectionResponse with list of detected faces.
        """
        if not self._initialized or self.app is None:
            raise AIServiceError("FaceService not initialized — call initialize() first")

        img = self._decode_image(image_bytes)
        loop = asyncio.get_running_loop()
        faces = await loop.run_in_executor(None, partial(self.app.get, img))

        detected: list[DetectedFace] = []
        for face in faces:
            score = float(face.det_score)
            if score < _MIN_CONFIDENCE:
                continue
            bbox = face.bbox  # [x1, y1, x2, y2]
            detected.append(
                DetectedFace(
                    bbox=BoundingBox(
                        x=float(bbox[0]),
                        y=float(bbox[1]),
                        width=float(bbox[2] - bbox[0]),
                        height=float(bbox[3] - bbox[1]),
                    ),
                    confidence=score,
                )
            )

        logger.info("Face detection completed", extra={"face_count": len(detected)})
        return FaceDetectionResponse(faces=detected)

    async def get_embedding(self, image_bytes: bytes, face_index: int = 0) -> np.ndarray:
        """Extract a 512-dim face embedding from the detected face.

        Args:
            image_bytes: Raw image bytes.
            face_index: Which detected face to extract (0 = first/largest).

        Returns:
            L2-normalized 512-dim numpy array.

        Raises:
            ValidationError: If no face found or face_index out of range.
        """
        if not self._initialized or self.app is None:
            raise AIServiceError("FaceService not initialized — call initialize() first")

        img = self._decode_image(image_bytes)
        loop = asyncio.get_running_loop()
        faces = await loop.run_in_executor(None, partial(self.app.get, img))

        # Filter by confidence
        valid_faces = [f for f in faces if float(f.det_score) >= _MIN_CONFIDENCE]
        if not valid_faces:
            raise ValidationError("No face detected in the image")
        if face_index >= len(valid_faces):
            raise ValidationError(
                f"face_index {face_index} out of range — only {len(valid_faces)} face(s) detected"
            )

        embedding = valid_faces[face_index].embedding  # 512-dim
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    @staticmethod
    def compare_embeddings(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Cosine similarity between two L2-normalized embeddings.

        Returns:
            Float between 0.0 and 1.0 (higher = more similar).
        """
        similarity = float(np.dot(emb1, emb2))
        return max(0.0, min(1.0, similarity))

    async def identify(
        self,
        image_bytes: bytes,
        clinic_id: uuid.UUID,
        db: AsyncSession,
    ) -> FaceIdentifyResponse | None:
        """Detect face, compare against registered patients, return best match.

        Args:
            image_bytes: Raw image bytes from kiosk camera.
            clinic_id: Tenant scope.
            db: Database session.

        Returns:
            FaceIdentifyResponse with patient match, or None if no match.
        """
        embedding = await self.get_embedding(image_bytes)

        known = await self._load_known_embeddings(clinic_id, db)
        if not known:
            logger.info("No registered face embeddings for clinic", extra={"clinic_id": str(clinic_id)})
            return None

        best_match: tuple[uuid.UUID | None, float, str | None] = (None, 0.0, None)
        for patient_id, patient_name, known_emb in known:
            sim = self.compare_embeddings(embedding, known_emb)
            if sim > best_match[1]:
                best_match = (patient_id, sim, patient_name)

        patient_id, similarity, patient_name = best_match
        if similarity < _MATCH_THRESHOLD:
            logger.info(
                "Face identification: no match above threshold",
                extra={"best_similarity": round(similarity, 3), "clinic_id": str(clinic_id)},
            )
            return None

        logger.info(
            "Face identification: match found",
            extra={
                "patient_id": str(patient_id),
                "similarity": round(similarity, 3),
                "clinic_id": str(clinic_id),
            },
        )
        return FaceIdentifyResponse(
            patient_id=patient_id,
            similarity=similarity,
            patient_name=patient_name,
        )

    async def register_face(
        self,
        image_bytes: bytes,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        device_id: str,
        db: AsyncSession,
    ) -> None:
        """Store face embedding for a patient after verifying consent.

        Args:
            image_bytes: Raw image bytes.
            patient_id: Patient UUID.
            clinic_id: Tenant scope.
            device_id: Kiosk device identifier.
            db: Database session.

        Raises:
            ForbiddenError: If no active FACE_RECOGNITION consent found.
            ValidationError: If no face detected.
        """
        from app.models.consent import ConsentRecord, ConsentType
        from app.models.patient import Patient

        # Verify consent
        consent = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.clinic_id == clinic_id,
                ConsentRecord.patient_id == patient_id,
                ConsentRecord.consent_type == ConsentType.FACE_RECOGNITION,
                ConsentRecord.revoked_at.is_(None),
            )
        )
        if consent.scalar_one_or_none() is None:
            raise ForbiddenError(
                "Face registration requires FACE_RECOGNITION consent. "
                "Patient must grant consent before face data can be stored."
            )

        # Get embedding
        embedding = await self.get_embedding(image_bytes)

        # Encrypt embedding bytes
        encrypted = self._encrypt_embedding(embedding)

        # Update patient record
        result = await db.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.id == patient_id,
            )
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Patient not found")

        patient.face_embedding_enc = encrypted
        await db.flush()

        # Invalidate Redis cache for this clinic's embeddings
        redis = get_redis()
        await redis.delete(f"face_embeddings:{clinic_id}")

        # Audit log
        from app.models.audit_log import AuditLog
        audit = AuditLog(
            clinic_id=clinic_id,
            action="FACE_REGISTERED",
            entity_type="Patient",
            entity_id=patient_id,
            new_value={"device_id": device_id},
        )
        db.add(audit)
        await db.flush()

        logger.info(
            "Face embedding registered",
            extra={
                "patient_id": str(patient_id),
                "clinic_id": str(clinic_id),
                "device_id": device_id,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray:
        """Decode raw bytes to a BGR numpy array for OpenCV/InsightFace."""
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValidationError("Invalid image — could not decode")
        return img

    @staticmethod
    def _encrypt_embedding(embedding: np.ndarray) -> bytes:
        """Encrypt a numpy embedding with AES-256-GCM.

        The result is: nonce (12 bytes) + ciphertext.
        Stored directly as LargeBinary (not base64) since the column is bytes.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key_bytes = bytes.fromhex(settings.ENCRYPTION_KEY)
        aesgcm = AESGCM(key_bytes)
        nonce = os.urandom(_NONCE_SIZE)
        plaintext = embedding.astype(np.float32).tobytes()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    @staticmethod
    def _decrypt_embedding(encrypted: bytes) -> np.ndarray:
        """Decrypt an AES-256-GCM encrypted embedding back to numpy."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key_bytes = bytes.fromhex(settings.ENCRYPTION_KEY)
        aesgcm = AESGCM(key_bytes)
        nonce = encrypted[:_NONCE_SIZE]
        ciphertext = encrypted[_NONCE_SIZE:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return np.frombuffer(plaintext, dtype=np.float32)

    async def _load_known_embeddings(
        self,
        clinic_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[tuple[uuid.UUID, str, np.ndarray]]:
        """Load and cache patient embeddings for a clinic.

        Returns list of (patient_id, patient_name, embedding) tuples.
        """
        from app.core.encryption import decrypt_field
        from app.models.patient import Patient

        redis = get_redis()
        cache_key = f"face_embeddings:{clinic_id}"

        # Try cache first
        cached = await redis.get(cache_key)
        if cached is not None:
            try:
                return self._deserialize_embedding_cache(cached)
            except Exception:
                logger.warning("Corrupted face embedding cache, reloading from DB")

        # Load from DB
        result = await db.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.face_embedding_enc.isnot(None),
            )
        )
        patients = result.scalars().all()

        embeddings: list[tuple[uuid.UUID, str, np.ndarray]] = []
        for patient in patients:
            try:
                emb = self._decrypt_embedding(patient.face_embedding_enc)
                name = decrypt_field(patient.full_name_enc)
                embeddings.append((patient.id, name, emb))
            except Exception as exc:
                logger.warning(
                    "Failed to decrypt face embedding",
                    extra={"patient_id": str(patient.id), "error": str(exc)},
                )

        # Cache as serialized bytes
        if embeddings:
            serialized = self._serialize_embedding_cache(embeddings)
            await redis.set(cache_key, serialized, ex=_EMBEDDING_CACHE_TTL)

        logger.info(
            "Loaded patient embeddings",
            extra={"clinic_id": str(clinic_id), "count": len(embeddings)},
        )
        return embeddings

    @staticmethod
    def _serialize_embedding_cache(
        data: list[tuple[uuid.UUID, str, np.ndarray]],
    ) -> str:
        """Serialize embeddings list to a JSON-compatible string for Redis."""
        import json

        entries = []
        for patient_id, name, emb in data:
            entries.append({
                "id": str(patient_id),
                "name": name,
                "emb": base64.b64encode(emb.astype(np.float32).tobytes()).decode("ascii"),
            })
        return json.dumps(entries)

    @staticmethod
    def _deserialize_embedding_cache(
        raw: str,
    ) -> list[tuple[uuid.UUID, str, np.ndarray]]:
        """Deserialize cached embeddings from Redis."""
        import json

        entries = json.loads(raw)
        result = []
        for entry in entries:
            emb_bytes = base64.b64decode(entry["emb"])
            emb = np.frombuffer(emb_bytes, dtype=np.float32).copy()
            if emb.shape[0] != 512:
                logger.warning("Skipping embedding with invalid dimension", extra={
                    "patient_id": entry["id"], "dim": emb.shape[0], "expected": 512,
                })
                continue
            result.append((uuid.UUID(entry["id"]), entry["name"], emb))
        return result


# Module-level singleton
face_service = FaceService()
