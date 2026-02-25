"""Muxlisa AI service — Uzbek/Russian/English speech-to-text and text-to-speech.

API contract (Muxlisa v2):
  TTS: POST /tts  — json {"text", "speaker"} → raw WAV bytes
  STT: POST /stt  — multipart form-data {audio} → json {"text": "..."}
  Auth: x-api-key header (NOT Bearer)
"""

import asyncio
import base64
import hashlib
import struct
import time

import httpx
from loguru import logger

from app.config import settings
from app.core.redis import get_redis
from app.schemas.ai import STTResponse

# Retry configuration — keep retries low for speed
_MAX_RETRIES = 2
_BASE_BACKOFF_S = 0.5

# TTS cache TTL in Redis (1 hour)
_TTS_CACHE_TTL = 3600

# Muxlisa limits
_TTS_MAX_CHARS = 512
_STT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class MuxlisaService:
    """Async client for Muxlisa STT/TTS API with mock mode for development."""

    def __init__(self) -> None:
        self.base_url: str = settings.MUXLISA_API_URL.rstrip("/")
        self.api_key: str = settings.MUXLISA_API_KEY
        self.mock_mode: bool = settings.MUXLISA_MOCK
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=2.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"x-api-key": self.api_key},
        )
        logger.info(
            "MuxlisaService created",
            extra={"mock_mode": self.mock_mode, "base_url": self.base_url},
        )

    # ------------------------------------------------------------------
    # STT — Speech to Text
    # ------------------------------------------------------------------

    async def speech_to_text(
        self, audio_bytes: bytes, audio_format: str = "wav"
    ) -> STTResponse:
        """Convert speech audio to text via Muxlisa STT API.

        API: POST /stt
        Headers: x-api-key
        Body: multipart form-data with field "audio"
        Response: {"text": "transcribed text"}

        Args:
            audio_bytes: Raw audio data (max 5 MB, max 60s).
            audio_format: Audio format hint (wav, ogg, webm, mp4, flac, aac, amr).

        Returns:
            STTResponse with transcript, detected language, and confidence.
        """
        start = time.monotonic()

        if self.mock_mode:
            result = STTResponse(
                transcript="Stomatologga yozilmoqchiman",
                language="uz",
                confidence=0.95,
            )
            self._log_stt(start, result, mock=True)
            return result

        if len(audio_bytes) > _STT_MAX_BYTES:
            logger.warning(
                "Audio too large for STT",
                extra={"size_bytes": len(audio_bytes), "max_bytes": _STT_MAX_BYTES},
            )
            return STTResponse(transcript="", language="uz", confidence=0.0)

        mime_map = {
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "webm": "audio/webm",
            "mp4": "audio/mp4",
            "flac": "audio/flac",
            "mpeg": "audio/mpeg",
            "aac": "audio/aac",
            "amr": "audio/amr",
            "3gpp": "audio/3gpp",
        }
        mime_type = mime_map.get(audio_format, "audio/wav")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info(
                    f"🎤 Muxlisa STT attempt {attempt}/{_MAX_RETRIES}",
                    extra={
                        "audio_size": len(audio_bytes),
                        "audio_format": audio_format,
                        "mime_type": mime_type,
                        "url": f"{self.base_url}/stt",
                    }
                )
                
                response = await self.client.post(
                    f"{self.base_url}/stt",
                    headers={"x-api-key": self.api_key},
                    files={"audio": (f"audio.{audio_format}", audio_bytes, mime_type)},
                )
                
                logger.info(
                    f"📡 Muxlisa STT response",
                    extra={
                        "status_code": response.status_code,
                        "content_length": len(response.content),
                        "content_type": response.headers.get("content-type"),
                    }
                )
                
                response.raise_for_status()
                data = response.json()

                logger.info(
                    f"📦 Muxlisa STT data",
                    extra={
                        "response_keys": list(data.keys()),
                        "raw_response": str(data)[:500],
                    }
                )

                transcript = data.get("text", "")
                detected_language = self.detect_language(transcript)

                logger.info(
                    f"✅ Muxlisa STT success",
                    extra={
                        "transcript": transcript[:100] if transcript else "(empty)",
                        "transcript_len": len(transcript),
                        "language": detected_language,
                    }
                )

                result = STTResponse(
                    transcript=transcript,
                    language=detected_language,
                    confidence=0.9,  # Muxlisa doesn't return confidence
                )
                self._log_stt(start, result, mock=False)
                return result

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                try:
                    resp_body = exc.response.text[:500]
                except Exception:
                    resp_body = "<unreadable>"
                logger.warning(
                    "Muxlisa STT HTTP error",
                    extra={
                        "attempt": attempt,
                        "status_code": status,
                        "response_body": resp_body,
                        "url": str(exc.request.url),
                    },
                )
                # If 500 error (server issue), use Google fallback immediately
                if status == 500:
                    logger.warning("Muxlisa server error - using Google STT fallback")
                    try:
                        from app.ai.google_stt import GoogleSpeechSTT
                        fallback = GoogleSpeechSTT()
                        return await fallback.speech_to_text(audio_bytes, audio_format)
                    except Exception as fallback_err:
                        logger.error(f"Fallback STT also failed: {fallback_err}")
                        # Continue to retry Muxlisa
                
                # Don't retry on 400 (bad request), 402 (payment), 429 (rate limit)
                if status in (400, 402, 429):
                    break
            except httpx.TimeoutException:
                logger.warning(
                    "Muxlisa STT timeout",
                    extra={"attempt": attempt, "max_retries": _MAX_RETRIES},
                )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Muxlisa STT connection error",
                    extra={"attempt": attempt, "error": str(exc)},
                )

            if attempt < _MAX_RETRIES:
                backoff = _BASE_BACKOFF_S * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        logger.error("Muxlisa STT failed after all retries")
        return STTResponse(transcript="", language="uz", confidence=0.0)

    # ------------------------------------------------------------------
    # TTS — Text to Speech
    # ------------------------------------------------------------------

    async def text_to_speech(
        self, text: str, language: str = "uz", voice: str = "female"
    ) -> bytes | None:
        """TTS disabled — Muxlisa server returns HTTP 500.

        Kept as a no-op so callers don't break.
        """
        return None

    async def _tts_request(self, text: str, speaker: int) -> bytes | None:
        """Send a single TTS request to Muxlisa API with retry.

        Args:
            text: Text to synthesize (max 512 chars).
            speaker: 0 = female, 1 = male.

        Returns:
            Raw WAV audio bytes, or None on failure.
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self.client.post(
                    f"{self.base_url}/tts",
                    json={"text": text, "speaker": speaker},
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                    },
                )
                response.raise_for_status()
                return response.content  # raw WAV bytes

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                try:
                    resp_body = exc.response.text[:500]
                except Exception:
                    resp_body = "<unreadable>"
                logger.warning(
                    "Muxlisa TTS HTTP error",
                    extra={
                        "attempt": attempt,
                        "status_code": status,
                        "response_body": resp_body,
                        "url": str(exc.request.url),
                    },
                )
                # Don't retry on 400 (bad request), 402 (payment), 429 (rate limit)
                if status in (400, 402, 429):
                    break
            except httpx.TimeoutException:
                logger.warning(
                    "Muxlisa TTS timeout",
                    extra={"attempt": attempt, "max_retries": _MAX_RETRIES},
                )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Muxlisa TTS connection error",
                    extra={"attempt": attempt, "error": str(exc)},
                )

            if attempt < _MAX_RETRIES:
                backoff = _BASE_BACKOFF_S * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        logger.error("Muxlisa TTS request failed after all retries")
        return None

    # ------------------------------------------------------------------
    # Language detection (heuristic — Muxlisa doesn't return language)
    # ------------------------------------------------------------------

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language from text using character-set heuristics.

        Returns:
            Language code: "uz", "ru", or "en".
        """
        if not text.strip():
            return "uz"

        cyrillic_count = 0
        latin_count = 0
        total = 0

        for char in text:
            if char.isalpha():
                total += 1
                if "\u0400" <= char <= "\u04ff":
                    cyrillic_count += 1
                elif char.isascii():
                    latin_count += 1

        if total == 0:
            return "uz"

        cyrillic_ratio = cyrillic_count / total
        if cyrillic_ratio > 0.5:
            return "ru"

        # Uzbek Latin markers
        text_lower = text.lower()
        uzbek_markers = ["oʻ", "gʻ", "o'", "g'", "sh", "ch", "ng"]
        uzbek_hits = sum(1 for m in uzbek_markers if m in text_lower)
        if uzbek_hits >= 1:
            return "uz"

        latin_ratio = latin_count / total
        if latin_ratio > 0.8:
            uzbek_words = {"va", "bu", "men", "siz", "bilan", "uchun", "kerak", "qanday", "yordam"}
            words = set(text_lower.split())
            if words & uzbek_words:
                return "uz"
            return "en"

        return "uz"

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
        logger.info("MuxlisaService closed")

    # ------------------------------------------------------------------
    # Text splitting for long TTS
    # ------------------------------------------------------------------

    @staticmethod
    def _split_text(text: str, max_length: int = 512) -> list[str]:
        """Split text into chunks at sentence boundaries, respecting max_length."""
        if len(text) <= max_length:
            return [text]

        chunks: list[str] = []
        # Split on sentence-ending punctuation
        import re
        sentences = re.split(r'(?<=[.!?।\n])\s*', text)

        current_chunk = ""
        for sentence in sentences:
            if not sentence.strip():
                continue
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If a single sentence is too long, force-split it
                if len(sentence) > max_length:
                    while len(sentence) > max_length:
                        # Split at last space before max_length
                        split_pos = sentence.rfind(" ", 0, max_length)
                        if split_pos == -1:
                            split_pos = max_length
                        chunks.append(sentence[:split_pos].strip())
                        sentence = sentence[split_pos:].strip()
                    current_chunk = sentence
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    @staticmethod
    def _concatenate_wav(parts: list[bytes]) -> bytes:
        """Concatenate multiple WAV files into a single WAV.

        Assumes all parts have the same sample rate, channels, and bit depth.
        """
        if len(parts) == 1:
            return parts[0]

        all_data = bytearray()
        sample_rate = 16000
        num_channels = 1
        bits_per_sample = 16

        for part in parts:
            if len(part) < 44:
                continue
            # Parse WAV header to get data chunk
            try:
                # Find "data" chunk
                data_pos = part.find(b"data")
                if data_pos == -1:
                    continue
                data_size = struct.unpack_from("<I", part, data_pos + 4)[0]
                audio_data = part[data_pos + 8: data_pos + 8 + data_size]
                all_data.extend(audio_data)

                # Extract format info from first valid part
                if part[:4] == b"RIFF" and len(part) >= 28:
                    num_channels = struct.unpack_from("<H", part, 22)[0]
                    sample_rate = struct.unpack_from("<I", part, 24)[0]
                    bits_per_sample = struct.unpack_from("<H", part, 34)[0]
            except (struct.error, IndexError):
                continue

        if not all_data:
            return parts[0] if parts else _generate_silent_wav()

        # Build new WAV
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = len(all_data)

        header = struct.pack(
            "<4sI4s"
            "4sIHHIIHH"
            "4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b"data",
            data_size,
        )

        return bytes(header) + bytes(all_data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tts_cache_key(text: str, language: str, voice: str) -> str:
        """Build a Redis cache key for TTS output."""
        content = f"{text}:{language}:{voice}"
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"tts_cache:{digest}"

    @staticmethod
    async def _cache_tts(redis: object, key: str, audio: bytes) -> None:
        """Store TTS audio in Redis as base64 (decode_responses=True safe)."""
        try:
            await redis.set(key, base64.b64encode(audio).decode("ascii"), ex=_TTS_CACHE_TTL)
        except Exception as exc:
            logger.warning("Failed to cache TTS audio", extra={"error": str(exc)})

    @staticmethod
    def _log_stt(start: float, result: STTResponse, *, mock: bool) -> None:
        latency_ms = (time.monotonic() - start) * 1000
        logger.info(
            "STT completed",
            extra={
                "latency_ms": round(latency_ms, 1),
                "transcript_len": len(result.transcript),
                "language": result.language,
                "confidence": result.confidence,
                "mock": mock,
            },
        )

    @staticmethod
    def _log_tts(
        start: float,
        text_len: int,
        language: str,
        *,
        mock: bool,
        cached: bool = False,
    ) -> None:
        latency_ms = (time.monotonic() - start) * 1000
        logger.info(
            "TTS completed",
            extra={
                "latency_ms": round(latency_ms, 1),
                "text_len": text_len,
                "language": language,
                "mock": mock,
                "cached": cached,
            },
        )


def _generate_silent_wav(duration_ms: int = 1000, sample_rate: int = 16000) -> bytes:
    """Generate a valid silent WAV file.

    Args:
        duration_ms: Duration in milliseconds.
        sample_rate: Sample rate in Hz.

    Returns:
        WAV file as bytes.
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    header = struct.pack(
        "<4sI4s"
        "4sIHHIIHH"
        "4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    samples = b"\x00" * data_size
    return header + samples


# Module-level singleton
muxlisa_service = MuxlisaService()
