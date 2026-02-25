"""Tests for the Muxlisa STT/TTS service — mock mode and simulated real mode."""

import struct
import wave
from io import BytesIO
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.ai.muxlisa_service import (
    MuxlisaService,
    _TTS_CACHE_TTL,
    _generate_silent_wav,
)
from app.schemas.ai import STTResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_test_wav(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate a tiny valid WAV file for test uploads."""
    return _generate_silent_wav(duration_ms=duration_ms, sample_rate=sample_rate)


def _wav_is_valid(data: bytes) -> bool:
    """Check that bytes form a valid WAV header."""
    if len(data) < 44:
        return False
    return data[:4] == b"RIFF" and data[8:12] == b"WAVE"


# ---------------------------------------------------------------------------
# Silent WAV generation
# ---------------------------------------------------------------------------
class TestSilentWav:
    def test_generates_valid_wav(self) -> None:
        wav = _generate_silent_wav(duration_ms=500)
        assert _wav_is_valid(wav)

    def test_wav_duration_scales_with_input(self) -> None:
        wav_short = _generate_silent_wav(duration_ms=100)
        wav_long = _generate_silent_wav(duration_ms=1000)
        assert len(wav_long) > len(wav_short)

    def test_wav_parseable_by_wave_module(self) -> None:
        wav_bytes = _generate_silent_wav(duration_ms=200, sample_rate=16000)
        buf = BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2  # 16-bit
            assert wf.getframerate() == 16000
            # ~3200 frames for 200ms at 16kHz
            assert wf.getnframes() == 3200

    def test_zero_duration(self) -> None:
        wav = _generate_silent_wav(duration_ms=0)
        assert _wav_is_valid(wav)
        assert len(wav) == 44  # header only, no samples


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
class TestLanguageDetection:
    @pytest.fixture
    def svc(self) -> MuxlisaService:
        with patch("app.ai.muxlisa_service.settings") as mock_s:
            mock_s.MUXLISA_API_URL = "https://api.test.uz"
            mock_s.MUXLISA_API_KEY = "test-key"
            mock_s.MUXLISA_MOCK = True
            return MuxlisaService()

    def test_uzbek_latin(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("Shifokorga yozilmoqchiman") == "uz"

    def test_uzbek_with_special_chars(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("Men oʻzbek tilida gaplashaman") == "uz"

    def test_uzbek_with_apostrophe(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("O'zbekiston klinikasi") == "uz"

    def test_russian_cyrillic(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("Здравствуйте, я хочу записаться к врачу") == "ru"

    def test_english(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("I would like to book an appointment please") == "en"

    def test_mixed_defaults_by_ratio(self, svc: MuxlisaService) -> None:
        # Mostly Cyrillic
        assert svc.detect_language("Привет world") == "ru"

    def test_empty_string(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("") == "uz"

    def test_numbers_only(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("12345") == "uz"

    def test_uzbek_common_words(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("Men bugun kelaman") == "uz"

    def test_uzbek_sh_ch_markers(self, svc: MuxlisaService) -> None:
        assert svc.detect_language("Shifokor chaqirish kerak") == "uz"


# ---------------------------------------------------------------------------
# STT — mock mode
# ---------------------------------------------------------------------------
class TestSTTMockMode:
    @pytest_asyncio.fixture
    async def svc(self) -> MuxlisaService:
        with patch("app.ai.muxlisa_service.settings") as mock_s:
            mock_s.MUXLISA_API_URL = "https://api.test.uz"
            mock_s.MUXLISA_API_KEY = "test-key"
            mock_s.MUXLISA_MOCK = True
            service = MuxlisaService()
            yield service
            await service.close()

    async def test_returns_default_mock_transcript(self, svc: MuxlisaService) -> None:
        result = await svc.speech_to_text(b"fake audio")
        assert isinstance(result, STTResponse)
        assert result.transcript == "Stomatologga yozilmoqchiman"
        assert result.language == "uz"
        assert result.confidence == 0.95

    async def test_mock_ignores_format(self, svc: MuxlisaService) -> None:
        result = await svc.speech_to_text(b"fake", audio_format="mp3")
        assert result.transcript == "Stomatologga yozilmoqchiman"


# ---------------------------------------------------------------------------
# STT — real mode (mocked httpx)
# ---------------------------------------------------------------------------
class TestSTTRealMode:
    @pytest_asyncio.fixture
    async def svc(self) -> MuxlisaService:
        with patch("app.ai.muxlisa_service.settings") as mock_s:
            mock_s.MUXLISA_API_URL = "https://api.test.uz"
            mock_s.MUXLISA_API_KEY = "real-key"
            mock_s.MUXLISA_MOCK = False
            service = MuxlisaService()
            yield service
            await service.close()

    async def test_successful_stt(self, svc: MuxlisaService) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "transcript": "Kardiologiya bo'limiga bormoqchiman",
                "detected_language": "uz",
                "confidence": 0.91,
            },
        )

        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(return_value=mock_response)

        result = await svc.speech_to_text(_make_test_wav())
        assert result.transcript == "Kardiologiya bo'limiga bormoqchiman"
        assert result.language == "uz"
        assert result.confidence == 0.91

    async def test_stt_timeout_retries_then_empty(self, svc: MuxlisaService) -> None:
        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await svc.speech_to_text(_make_test_wav())

        assert result.transcript == ""
        assert result.confidence == 0.0
        assert svc.client.post.call_count == 3  # 3 retries

    async def test_stt_http_error_retries(self, svc: MuxlisaService) -> None:
        error_resp = httpx.Response(500, request=httpx.Request("POST", "http://test/stt"))
        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(side_effect=httpx.HTTPStatusError("error", request=error_resp.request, response=error_resp))

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await svc.speech_to_text(_make_test_wav())

        assert result.transcript == ""
        assert svc.client.post.call_count == 3

    async def test_stt_succeeds_on_second_attempt(self, svc: MuxlisaService) -> None:
        good_response = httpx.Response(
            200,
            json={"transcript": "Salom", "detected_language": "uz", "confidence": 0.88},
        )

        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(
            side_effect=[httpx.TimeoutException("timeout"), good_response]
        )

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await svc.speech_to_text(_make_test_wav())

        assert result.transcript == "Salom"
        assert svc.client.post.call_count == 2


# ---------------------------------------------------------------------------
# TTS — mock mode
# ---------------------------------------------------------------------------
class TestTTSMockMode:
    @pytest_asyncio.fixture
    async def svc(self) -> MuxlisaService:
        with patch("app.ai.muxlisa_service.settings") as mock_s:
            mock_s.MUXLISA_API_URL = "https://api.test.uz"
            mock_s.MUXLISA_API_KEY = "test-key"
            mock_s.MUXLISA_MOCK = True
            service = MuxlisaService()
            yield service
            await service.close()

    async def test_returns_valid_wav(self, svc: MuxlisaService) -> None:
        audio = await svc.text_to_speech("Salom, qanday yordam bera olaman?")
        assert _wav_is_valid(audio)

    async def test_duration_scales_with_text_length(self, svc: MuxlisaService) -> None:
        short = await svc.text_to_speech("Hi")
        long = await svc.text_to_speech("This is a much longer sentence for testing purposes")
        assert len(long) > len(short)

    async def test_empty_text_still_returns_wav(self, svc: MuxlisaService) -> None:
        # Even 0 chars → some silent wav
        audio = await svc.text_to_speech("x")  # min 1 char
        assert _wav_is_valid(audio)


# ---------------------------------------------------------------------------
# TTS — real mode (mocked httpx + Redis)
# ---------------------------------------------------------------------------
class TestTTSRealMode:
    @pytest_asyncio.fixture
    async def svc(self) -> MuxlisaService:
        with patch("app.ai.muxlisa_service.settings") as mock_s:
            mock_s.MUXLISA_API_URL = "https://api.test.uz"
            mock_s.MUXLISA_API_KEY = "real-key"
            mock_s.MUXLISA_MOCK = False
            service = MuxlisaService()
            yield service
            await service.close()

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        redis = AsyncMock(spec=Redis)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis

    async def test_successful_tts(self, svc: MuxlisaService, mock_redis: AsyncMock) -> None:
        fake_audio = _make_test_wav(duration_ms=500)
        mock_response = httpx.Response(200, content=fake_audio)

        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(return_value=mock_response)

        with patch("app.ai.muxlisa_service.get_redis", return_value=mock_redis):
            audio = await svc.text_to_speech("Salom", language="uz")

        assert _wav_is_valid(audio)
        # Should cache
        mock_redis.set.assert_called_once()

    async def test_tts_cache_hit(self, svc: MuxlisaService) -> None:
        cached_audio = _make_test_wav(duration_ms=100)
        mock_redis = AsyncMock(spec=Redis)
        # Redis with decode_responses returns str
        mock_redis.get = AsyncMock(return_value=cached_audio.decode("latin-1"))

        svc.client = AsyncMock(spec=httpx.AsyncClient)

        with patch("app.ai.muxlisa_service.get_redis", return_value=mock_redis):
            audio = await svc.text_to_speech("Cached text", language="uz")

        assert _wav_is_valid(audio)
        # HTTP client should NOT have been called
        svc.client.post.assert_not_called()

    async def test_tts_timeout_returns_silent(self, svc: MuxlisaService, mock_redis: AsyncMock) -> None:
        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.ai.muxlisa_service.get_redis", return_value=mock_redis):
            with patch("asyncio.sleep", new=AsyncMock()):
                audio = await svc.text_to_speech("Test timeout")

        assert _wav_is_valid(audio)  # should get silent fallback

    async def test_tts_retries_on_http_error(self, svc: MuxlisaService, mock_redis: AsyncMock) -> None:
        fake_audio = _make_test_wav()
        good_response = httpx.Response(200, content=fake_audio)
        error_resp = httpx.Response(503, request=httpx.Request("POST", "http://test/tts"))

        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.post = AsyncMock(
            side_effect=[
                httpx.HTTPStatusError("error", request=error_resp.request, response=error_resp),
                good_response,
            ]
        )

        with patch("app.ai.muxlisa_service.get_redis", return_value=mock_redis):
            with patch("asyncio.sleep", new=AsyncMock()):
                audio = await svc.text_to_speech("Retry test")

        assert _wav_is_valid(audio)
        assert svc.client.post.call_count == 2


# ---------------------------------------------------------------------------
# TTS cache key
# ---------------------------------------------------------------------------
class TestTTSCacheKey:
    def test_same_input_same_key(self) -> None:
        k1 = MuxlisaService._tts_cache_key("Salom", "uz", "female")
        k2 = MuxlisaService._tts_cache_key("Salom", "uz", "female")
        assert k1 == k2

    def test_different_text_different_key(self) -> None:
        k1 = MuxlisaService._tts_cache_key("Salom", "uz", "female")
        k2 = MuxlisaService._tts_cache_key("Xayr", "uz", "female")
        assert k1 != k2

    def test_different_language_different_key(self) -> None:
        k1 = MuxlisaService._tts_cache_key("Hello", "en", "female")
        k2 = MuxlisaService._tts_cache_key("Hello", "ru", "female")
        assert k1 != k2

    def test_key_starts_with_prefix(self) -> None:
        key = MuxlisaService._tts_cache_key("test", "uz", "female")
        assert key.startswith("tts_cache:")


# ---------------------------------------------------------------------------
# Service lifecycle
# ---------------------------------------------------------------------------
class TestServiceLifecycle:
    async def test_close_shuts_down_client(self) -> None:
        with patch("app.ai.muxlisa_service.settings") as mock_s:
            mock_s.MUXLISA_API_URL = "https://api.test.uz"
            mock_s.MUXLISA_API_KEY = "test-key"
            mock_s.MUXLISA_MOCK = True
            svc = MuxlisaService()

        svc.client = AsyncMock(spec=httpx.AsyncClient)
        svc.client.aclose = AsyncMock()
        await svc.close()
        svc.client.aclose.assert_called_once()
