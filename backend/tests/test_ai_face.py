"""Tests for the InsightFace service — mocked model, real encryption logic."""

import io
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import cv2
import numpy as np
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.ai.face_service import (
    FaceService,
    _EMBEDDING_CACHE_TTL,
    _MATCH_THRESHOLD,
    _MIN_CONFIDENCE,
)
from app.core.exceptions import AIServiceError, ForbiddenError, ValidationError
from app.schemas.ai import FaceDetectionResponse, FaceIdentifyResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_test_image(width: int = 200, height: int = 200, color: tuple = (0, 120, 255)) -> bytes:
    """Generate a simple colored rectangle as a test image (JPEG bytes)."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    success, buf = cv2.imencode(".jpg", img)
    assert success
    return buf.tobytes()


def _make_mock_face(
    bbox: tuple = (10.0, 20.0, 110.0, 120.0),
    det_score: float = 0.95,
    embedding: np.ndarray | None = None,
) -> MagicMock:
    """Build a mock InsightFace face object."""
    face = MagicMock()
    face.bbox = np.array(bbox, dtype=np.float32)
    face.det_score = det_score
    if embedding is None:
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
    face.embedding = embedding
    return face


def _make_known_embedding() -> np.ndarray:
    """Generate a deterministic normalized 512-dim embedding."""
    rng = np.random.RandomState(42)
    emb = rng.randn(512).astype(np.float32)
    return emb / np.linalg.norm(emb)


# ---------------------------------------------------------------------------
# Image decoding
# ---------------------------------------------------------------------------
class TestImageDecoding:
    def test_decode_valid_jpeg(self) -> None:
        img_bytes = _make_test_image()
        result = FaceService._decode_image(img_bytes)
        assert isinstance(result, np.ndarray)
        assert result.shape == (200, 200, 3)

    def test_decode_valid_png(self) -> None:
        img = np.full((100, 100, 3), (255, 0, 0), dtype=np.uint8)
        success, buf = cv2.imencode(".png", img)
        result = FaceService._decode_image(buf.tobytes())
        assert result.shape == (100, 100, 3)

    def test_decode_invalid_bytes(self) -> None:
        with pytest.raises(ValidationError, match="Invalid image"):
            FaceService._decode_image(b"not an image")

    def test_decode_empty_bytes(self) -> None:
        with pytest.raises(ValidationError, match="Invalid image"):
            FaceService._decode_image(b"")


# ---------------------------------------------------------------------------
# Face detection
# ---------------------------------------------------------------------------
class TestFaceDetection:
    @pytest_asyncio.fixture
    async def svc(self) -> FaceService:
        service = FaceService()
        service.app = MagicMock()
        service._initialized = True
        return service

    async def test_detect_single_face(self, svc: FaceService) -> None:
        face = _make_mock_face(bbox=(50, 60, 150, 180), det_score=0.92)
        svc.app.get = MagicMock(return_value=[face])

        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[face])
            result = await svc.detect_faces(_make_test_image())

        assert isinstance(result, FaceDetectionResponse)
        assert len(result.faces) == 1
        assert result.faces[0].confidence == 0.92
        assert result.faces[0].bbox.x == 50.0
        assert result.faces[0].bbox.width == 100.0  # 150 - 50
        assert result.faces[0].bbox.height == 120.0  # 180 - 60

    async def test_detect_multiple_faces(self, svc: FaceService) -> None:
        faces = [
            _make_mock_face(bbox=(10, 10, 60, 60), det_score=0.85),
            _make_mock_face(bbox=(100, 100, 180, 180), det_score=0.90),
        ]

        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=faces)
            result = await svc.detect_faces(_make_test_image())

        assert len(result.faces) == 2

    async def test_detect_filters_low_confidence(self, svc: FaceService) -> None:
        faces = [
            _make_mock_face(det_score=0.3),  # below threshold
            _make_mock_face(det_score=0.8),  # above threshold
        ]

        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=faces)
            result = await svc.detect_faces(_make_test_image())

        assert len(result.faces) == 1
        assert result.faces[0].confidence == 0.8

    async def test_detect_no_faces(self, svc: FaceService) -> None:
        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[])
            result = await svc.detect_faces(_make_test_image())

        assert len(result.faces) == 0

    async def test_detect_not_initialized(self) -> None:
        svc = FaceService()
        with pytest.raises(AIServiceError, match="not initialized"):
            await svc.detect_faces(_make_test_image())


# ---------------------------------------------------------------------------
# Embedding extraction
# ---------------------------------------------------------------------------
class TestEmbedding:
    @pytest_asyncio.fixture
    async def svc(self) -> FaceService:
        service = FaceService()
        service.app = MagicMock()
        service._initialized = True
        return service

    async def test_get_embedding_returns_normalized(self, svc: FaceService) -> None:
        raw_emb = np.random.randn(512).astype(np.float32)
        face = _make_mock_face(det_score=0.9, embedding=raw_emb)

        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[face])
            result = await svc.get_embedding(_make_test_image())

        assert result.shape == (512,)
        # Should be L2-normalized
        assert abs(np.linalg.norm(result) - 1.0) < 1e-5

    async def test_get_embedding_no_face_raises(self, svc: FaceService) -> None:
        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[])
            with pytest.raises(ValidationError, match="No face detected"):
                await svc.get_embedding(_make_test_image())

    async def test_get_embedding_low_confidence_only(self, svc: FaceService) -> None:
        face = _make_mock_face(det_score=0.2)  # below threshold

        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[face])
            with pytest.raises(ValidationError, match="No face detected"):
                await svc.get_embedding(_make_test_image())

    async def test_get_embedding_face_index_out_of_range(self, svc: FaceService) -> None:
        face = _make_mock_face(det_score=0.9)

        with patch("app.ai.face_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[face])
            with pytest.raises(ValidationError, match="face_index .* out of range"):
                await svc.get_embedding(_make_test_image(), face_index=5)


# ---------------------------------------------------------------------------
# Embedding comparison
# ---------------------------------------------------------------------------
class TestEmbeddingComparison:
    def test_identical_embeddings(self) -> None:
        emb = _make_known_embedding()
        assert FaceService.compare_embeddings(emb, emb) == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_embeddings(self) -> None:
        emb1 = np.zeros(512, dtype=np.float32)
        emb1[0] = 1.0
        emb2 = np.zeros(512, dtype=np.float32)
        emb2[1] = 1.0
        assert FaceService.compare_embeddings(emb1, emb2) == pytest.approx(0.0, abs=1e-5)

    def test_similar_embeddings(self) -> None:
        emb1 = _make_known_embedding()
        noise = np.random.randn(512).astype(np.float32) * 0.05
        emb2 = emb1 + noise
        emb2 = emb2 / np.linalg.norm(emb2)
        sim = FaceService.compare_embeddings(emb1, emb2)
        assert 0.8 < sim < 1.0

    def test_clamps_to_range(self) -> None:
        emb1 = np.ones(512, dtype=np.float32)
        emb2 = -np.ones(512, dtype=np.float32)
        sim = FaceService.compare_embeddings(emb1 / np.linalg.norm(emb1), emb2 / np.linalg.norm(emb2))
        assert sim == 0.0  # clamped from negative


# ---------------------------------------------------------------------------
# Embedding encryption roundtrip
# ---------------------------------------------------------------------------
class TestEmbeddingEncryption:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        original = _make_known_embedding()
        encrypted = FaceService._encrypt_embedding(original)

        # Should be bytes (nonce + ciphertext)
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 512 * 4  # larger than raw float32 data

        decrypted = FaceService._decrypt_embedding(encrypted)
        np.testing.assert_array_almost_equal(original, decrypted, decimal=5)

    def test_encryption_is_nondeterministic(self) -> None:
        emb = _make_known_embedding()
        enc1 = FaceService._encrypt_embedding(emb)
        enc2 = FaceService._encrypt_embedding(emb)
        assert enc1 != enc2  # different nonces


# ---------------------------------------------------------------------------
# Face identification
# ---------------------------------------------------------------------------
class TestFaceIdentification:
    @pytest_asyncio.fixture
    async def svc(self) -> FaceService:
        service = FaceService()
        service.app = MagicMock()
        service._initialized = True
        return service

    async def test_identify_match_found(self, svc: FaceService) -> None:
        known_emb = _make_known_embedding()
        patient_id = uuid.uuid4()

        # The image embedding should be very similar to known
        with (
            patch.object(svc, "get_embedding", return_value=known_emb),
            patch.object(
                svc,
                "_load_known_embeddings",
                return_value=[(patient_id, "Alisher Usmanov", known_emb)],
            ),
        ):
            result = await svc.identify(_make_test_image(), uuid.uuid4(), AsyncMock())

        assert result is not None
        assert isinstance(result, FaceIdentifyResponse)
        assert result.patient_id == patient_id
        assert result.patient_name == "Alisher Usmanov"
        assert result.similarity == pytest.approx(1.0, abs=1e-5)

    async def test_identify_no_match(self, svc: FaceService) -> None:
        query_emb = _make_known_embedding()
        # Create a completely different embedding
        different_emb = np.zeros(512, dtype=np.float32)
        different_emb[0] = 1.0

        with (
            patch.object(svc, "get_embedding", return_value=query_emb),
            patch.object(
                svc,
                "_load_known_embeddings",
                return_value=[(uuid.uuid4(), "Other Person", different_emb)],
            ),
        ):
            result = await svc.identify(_make_test_image(), uuid.uuid4(), AsyncMock())

        assert result is None

    async def test_identify_no_registered_embeddings(self, svc: FaceService) -> None:
        with (
            patch.object(svc, "get_embedding", return_value=_make_known_embedding()),
            patch.object(svc, "_load_known_embeddings", return_value=[]),
        ):
            result = await svc.identify(_make_test_image(), uuid.uuid4(), AsyncMock())

        assert result is None

    async def test_identify_best_match_among_multiple(self, svc: FaceService) -> None:
        query_emb = _make_known_embedding()
        patient1_id = uuid.uuid4()
        patient2_id = uuid.uuid4()

        # patient1 has exact match, patient2 has slightly different embedding
        noise = np.random.randn(512).astype(np.float32) * 0.3
        different_emb = query_emb + noise
        different_emb = different_emb / np.linalg.norm(different_emb)

        with (
            patch.object(svc, "get_embedding", return_value=query_emb),
            patch.object(
                svc,
                "_load_known_embeddings",
                return_value=[
                    (patient2_id, "Other Person", different_emb),
                    (patient1_id, "Best Match", query_emb),
                ],
            ),
        ):
            result = await svc.identify(_make_test_image(), uuid.uuid4(), AsyncMock())

        assert result is not None
        assert result.patient_id == patient1_id
        assert result.patient_name == "Best Match"


# ---------------------------------------------------------------------------
# Face registration
# ---------------------------------------------------------------------------
class TestFaceRegistration:
    @pytest_asyncio.fixture
    async def svc(self) -> FaceService:
        service = FaceService()
        service.app = MagicMock()
        service._initialized = True
        return service

    async def test_register_without_consent_raises(self, svc: FaceService) -> None:
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ForbiddenError, match="consent"):
            await svc.register_face(
                image_bytes=_make_test_image(),
                patient_id=uuid.uuid4(),
                clinic_id=uuid.uuid4(),
                device_id="kiosk-001",
                db=db,
            )

    async def test_register_with_consent_succeeds(self, svc: FaceService) -> None:
        db = AsyncMock()
        patient_id = uuid.uuid4()
        clinic_id = uuid.uuid4()

        mock_consent = MagicMock()
        mock_patient = MagicMock()
        mock_patient.face_embedding_enc = None

        # First call = consent check, second call = patient lookup
        consent_result = MagicMock()
        consent_result.scalar_one_or_none.return_value = mock_consent

        patient_result = MagicMock()
        patient_result.scalar_one_or_none.return_value = mock_patient

        db.execute = AsyncMock(side_effect=[consent_result, patient_result])
        db.flush = AsyncMock()
        db.add = MagicMock()

        mock_redis = AsyncMock(spec=Redis)
        mock_redis.delete = AsyncMock()

        emb = _make_known_embedding()

        with (
            patch.object(svc, "get_embedding", return_value=emb),
            patch("app.ai.face_service.get_redis", return_value=mock_redis),
        ):
            await svc.register_face(
                image_bytes=_make_test_image(),
                patient_id=patient_id,
                clinic_id=clinic_id,
                device_id="kiosk-001",
                db=db,
            )

        # Patient embedding should have been set
        assert mock_patient.face_embedding_enc is not None
        assert isinstance(mock_patient.face_embedding_enc, bytes)

        # Redis cache should be invalidated
        mock_redis.delete.assert_called_once_with(f"face_embeddings:{clinic_id}")

        # Audit log should be added
        db.add.assert_called()


# ---------------------------------------------------------------------------
# Embedding cache serialization
# ---------------------------------------------------------------------------
class TestEmbeddingCache:
    def test_serialize_deserialize_roundtrip(self) -> None:
        emb1 = _make_known_embedding()
        emb2 = np.random.randn(512).astype(np.float32)
        emb2 = emb2 / np.linalg.norm(emb2)

        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        data = [(id1, "Patient A", emb1), (id2, "Patient B", emb2)]

        serialized = FaceService._serialize_embedding_cache(data)
        assert isinstance(serialized, str)

        deserialized = FaceService._deserialize_embedding_cache(serialized)
        assert len(deserialized) == 2
        assert deserialized[0][0] == id1
        assert deserialized[0][1] == "Patient A"
        np.testing.assert_array_almost_equal(deserialized[0][2], emb1, decimal=5)
        assert deserialized[1][0] == id2

    async def test_load_known_embeddings_uses_cache(self) -> None:
        svc = FaceService()
        emb = _make_known_embedding()
        patient_id = uuid.uuid4()

        cache_data = FaceService._serialize_embedding_cache(
            [(patient_id, "Cached Patient", emb)]
        )

        mock_redis = AsyncMock(spec=Redis)
        mock_redis.get = AsyncMock(return_value=cache_data)

        db = AsyncMock()

        with patch("app.ai.face_service.get_redis", return_value=mock_redis):
            result = await svc._load_known_embeddings(uuid.uuid4(), db)

        assert len(result) == 1
        assert result[0][0] == patient_id
        assert result[0][1] == "Cached Patient"
        # DB should NOT have been queried
        db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------
class TestFaceServiceInit:
    async def test_initialize_sets_initialized(self) -> None:
        svc = FaceService()

        mock_app = MagicMock()
        with patch.object(FaceService, "_load_model", return_value=mock_app):
            await svc.initialize()

        assert svc._initialized is True
        assert svc.app is mock_app

    async def test_initialize_failure_raises(self) -> None:
        svc = FaceService()

        with patch.object(FaceService, "_load_model", side_effect=RuntimeError("Model not found")):
            with pytest.raises(AIServiceError, match="initialization failed"):
                await svc.initialize()

        assert svc._initialized is False
