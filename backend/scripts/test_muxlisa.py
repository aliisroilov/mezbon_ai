#!/usr/bin/env python3
"""
Test Muxlisa STT/TTS service — connection, TTS output, WAV header parsing, STT with silence.
Run: cd backend && python3 scripts/test_muxlisa.py
"""

import asyncio
import os
import struct
import sys
import time

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(backend_dir, ".env"))

# ── Colors ──────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {BOLD}{CYAN}{title}{RESET}")
    print(f"{'=' * 60}")


def info(label: str, value: str) -> None:
    print(f"  {DIM}{label}:{RESET} {value}")


def success(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}[WARN]{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def parse_wav_header(data: bytes) -> dict | None:
    """Parse a standard 44-byte WAV header and return metadata."""
    if len(data) < 44:
        return None
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None

    try:
        file_size = struct.unpack_from("<I", data, 4)[0] + 8
        fmt_tag = struct.unpack_from("<H", data, 20)[0]
        num_channels = struct.unpack_from("<H", data, 22)[0]
        sample_rate = struct.unpack_from("<I", data, 24)[0]
        byte_rate = struct.unpack_from("<I", data, 28)[0]
        block_align = struct.unpack_from("<H", data, 32)[0]
        bits_per_sample = struct.unpack_from("<H", data, 34)[0]

        # Find data chunk size
        data_chunk_size = 0
        pos = 36
        while pos < min(len(data), 200):
            chunk_id = data[pos:pos + 4]
            if len(data) < pos + 8:
                break
            chunk_size = struct.unpack_from("<I", data, pos + 4)[0]
            if chunk_id == b"data":
                data_chunk_size = chunk_size
                break
            pos += 8 + chunk_size

        duration_s = 0.0
        if byte_rate > 0 and data_chunk_size > 0:
            duration_s = data_chunk_size / byte_rate

        return {
            "file_size": file_size,
            "fmt_tag": fmt_tag,
            "channels": num_channels,
            "sample_rate": sample_rate,
            "byte_rate": byte_rate,
            "block_align": block_align,
            "bits_per_sample": bits_per_sample,
            "data_chunk_size": data_chunk_size,
            "duration_s": duration_s,
        }
    except (struct.error, IndexError):
        return None


def generate_silent_wav(duration_ms: int = 500, sample_rate: int = 16000) -> bytes:
    """Generate a valid silent WAV file for STT testing."""
    num_samples = int(sample_rate * duration_ms / 1000)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    header_bytes = struct.pack(
        "<4sI4s"
        "4sIHHIIHH"
        "4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    return header_bytes + (b"\x00" * data_size)


async def test_tts(service) -> bytes | None:
    """Test TTS: synthesize Uzbek text and save to file."""
    header("TEST 1: Text-to-Speech")

    text = "Assalomu alaykum"
    info("Input text", f'"{text}"')
    info("Language", "uz")
    info("Mock mode", str(service.mock_mode))

    start = time.monotonic()
    try:
        audio_bytes = await service.text_to_speech(text, language="uz")
    except Exception as exc:
        fail(f"TTS call raised exception: {exc}")
        return None

    elapsed_ms = (time.monotonic() - start) * 1000

    if not audio_bytes:
        fail("TTS returned empty bytes")
        return None

    success(f"TTS returned {len(audio_bytes):,} bytes in {elapsed_ms:.0f}ms")

    # Save to file
    output_path = "/tmp/test_tts.wav"
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    success(f"Saved to {output_path}")
    info("File size", f"{os.path.getsize(output_path):,} bytes")

    # Print first 44 bytes as hex (WAV header)
    print(f"\n  {BOLD}WAV Header (first 44 bytes, hex):{RESET}")
    hex_header = audio_bytes[:44].hex()
    # Format in groups of 2 (bytes), 16 per line
    for i in range(0, min(88, len(hex_header)), 32):
        chunk = hex_header[i:i + 32]
        formatted = " ".join(chunk[j:j + 2] for j in range(0, len(chunk), 2))
        ascii_repr = ""
        for j in range(i // 2, min(i // 2 + 16, 44)):
            b = audio_bytes[j]
            ascii_repr += chr(b) if 32 <= b < 127 else "."
        print(f"    {i // 2:04x}: {formatted:<48s} |{ascii_repr}|")

    # Parse WAV header
    wav_info = parse_wav_header(audio_bytes)
    if wav_info:
        print(f"\n  {BOLD}WAV Metadata:{RESET}")
        fmt_names = {1: "PCM", 3: "IEEE Float", 6: "A-law", 7: "mu-law"}
        info("Format", fmt_names.get(wav_info["fmt_tag"], f"Unknown ({wav_info['fmt_tag']})"))
        info("Channels", str(wav_info["channels"]))
        info("Sample rate", f"{wav_info['sample_rate']:,} Hz")
        info("Bit depth", f"{wav_info['bits_per_sample']} bits")
        info("Byte rate", f"{wav_info['byte_rate']:,} bytes/sec")
        info("Block align", f"{wav_info['block_align']} bytes")
        info("Audio data size", f"{wav_info['data_chunk_size']:,} bytes")
        info("Duration", f"{wav_info['duration_s']:.2f} seconds")
        success("Valid WAV file confirmed")
    else:
        fail("Could not parse WAV header -- file may not be valid WAV")

    return audio_bytes


async def test_stt(service) -> None:
    """Test STT: send a short silent WAV and see what the API returns."""
    header("TEST 2: Speech-to-Text (silent WAV)")

    silent_wav = generate_silent_wav(duration_ms=500, sample_rate=16000)
    info("Input", f"Silent WAV, 500ms, 16kHz, mono, 16-bit")
    info("Size", f"{len(silent_wav):,} bytes")
    info("Mock mode", str(service.mock_mode))

    start = time.monotonic()
    try:
        result = await service.speech_to_text(silent_wav, audio_format="wav")
    except Exception as exc:
        fail(f"STT call raised exception: {exc}")
        return

    elapsed_ms = (time.monotonic() - start) * 1000

    success(f"STT completed in {elapsed_ms:.0f}ms")
    info("Transcript", f'"{result.transcript}"' if result.transcript else "(empty)")
    info("Language", result.language)
    info("Confidence", f"{result.confidence:.2f}")

    if service.mock_mode:
        warn("Mock mode is ON -- transcript is hardcoded, not from real API")
    elif not result.transcript:
        success("Empty transcript for silent audio is expected behavior")


async def test_language_detection(service) -> None:
    """Test the heuristic language detection."""
    header("TEST 3: Language Detection (heuristic)")

    test_cases = [
        ("Assalomu alaykum, men shifokorga yozilmoqchiman", "uz"),
        ("Здравствуйте, я хочу записаться к врачу", "ru"),
        ("Hello, I would like to book an appointment", "en"),
        ("Men bugun tish shifokori ko'rigiga kelmoqchiman", "uz"),
        ("", "uz"),
    ]

    all_passed = True
    for text, expected in test_cases:
        detected = service.detect_language(text)
        status = f"{GREEN}OK{RESET}" if detected == expected else f"{RED}MISMATCH{RESET}"
        if detected != expected:
            all_passed = False
        display_text = text[:50] + "..." if len(text) > 50 else text
        print(f"  [{status}] \"{display_text}\" -> {detected} (expected: {expected})")

    if all_passed:
        success("All language detection tests passed")
    else:
        warn("Some language detection tests did not match expected values")


async def main() -> None:
    print(f"\n{BOLD}{CYAN}Muxlisa AI Service Test{RESET}")
    print(f"{DIM}Testing STT + TTS connectivity and output{RESET}")

    # Show config
    from app.config import settings
    header("CONFIGURATION")
    info("API URL", settings.MUXLISA_API_URL)
    info("API Key", settings.MUXLISA_API_KEY[:8] + "..." if settings.MUXLISA_API_KEY else "(not set)")
    info("Mock mode", str(settings.MUXLISA_MOCK))

    # We need Redis for TTS caching (used by the service).
    # If Redis is not available, we patch get_redis to use a dummy.
    redis_available = False
    try:
        from app.core.redis import get_redis
        r = get_redis()
        await r.ping()
        redis_available = True
        await r.aclose()
        info("Redis", f"{GREEN}connected{RESET}")
    except Exception as exc:
        info("Redis", f"{YELLOW}unavailable ({exc}){RESET} -- will patch caching")

    if not redis_available:
        # Patch _cache_tts and get_redis to be no-ops
        import app.ai.muxlisa_service as ms_module

        class FakeRedis:
            async def get(self, key):
                return None
            async def set(self, key, value, ex=None):
                pass

        original_get_redis = ms_module.get_redis
        ms_module.get_redis = lambda: FakeRedis()

    # Create service instance (not the module singleton to avoid import-time Redis issues)
    from app.ai.muxlisa_service import MuxlisaService
    service = MuxlisaService()

    try:
        await test_tts(service)
        await test_stt(service)
        await test_language_detection(service)
    finally:
        await service.close()
        if not redis_available:
            ms_module.get_redis = original_get_redis

    print(f"\n{'=' * 60}")
    print(f"  {BOLD}{GREEN}All tests completed.{RESET}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
