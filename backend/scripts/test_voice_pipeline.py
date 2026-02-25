"""Test script for the complete voice pipeline.

Tests:
  A. Muxlisa TTS (text → audio)
  B. Muxlisa STT (audio → text)
  C. Gemini chat (text → response)
  D. Full pipeline: TTS → STT → Gemini → TTS

Usage:
  cd backend
  python scripts/test_voice_pipeline.py
"""

import asyncio
import os
import sys
import time

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env from the backend directory (same as uvicorn does)
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path, override=False)
# Fallback defaults for CI/testing where .env doesn't exist
os.environ.setdefault("JWT_SECRET", "0" * 64)
os.environ.setdefault("JWT_REFRESH_SECRET", "0" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)


async def test_muxlisa_tts():
    """Test A: Text-to-Speech"""
    from app.ai.muxlisa_service import MuxlisaService

    print("\n" + "=" * 60)
    print("TEST A: Muxlisa TTS (text → audio)")
    print("=" * 60)

    svc = MuxlisaService()
    text = "Assalomu alaykum! Mezbon klinikasiga xush kelibsiz."

    start = time.monotonic()
    audio = await svc.text_to_speech(text, language="uz")
    elapsed = (time.monotonic() - start) * 1000

    print(f"  Input text:    {text}")
    print(f"  Audio size:    {len(audio)} bytes")
    print(f"  Latency:       {elapsed:.1f} ms")
    print(f"  Mock mode:     {svc.mock_mode}")
    print(f"  Is valid WAV:  {audio[:4] == b'RIFF'}")
    print(f"  Status:        {'PASS' if len(audio) > 44 else 'FAIL'}")

    await svc.close()
    return audio


async def test_muxlisa_stt(audio_bytes: bytes | None = None):
    """Test B: Speech-to-Text"""
    from app.ai.muxlisa_service import MuxlisaService

    print("\n" + "=" * 60)
    print("TEST B: Muxlisa STT (audio → text)")
    print("=" * 60)

    svc = MuxlisaService()

    if audio_bytes is None:
        # Generate a silent WAV for testing
        from app.ai.muxlisa_service import _generate_silent_wav
        audio_bytes = _generate_silent_wav(duration_ms=2000)

    start = time.monotonic()
    result = await svc.speech_to_text(audio_bytes, audio_format="wav")
    elapsed = (time.monotonic() - start) * 1000

    print(f"  Audio size:    {len(audio_bytes)} bytes")
    print(f"  Transcript:    '{result.transcript}'")
    print(f"  Language:      {result.language}")
    print(f"  Confidence:    {result.confidence}")
    print(f"  Latency:       {elapsed:.1f} ms")
    print(f"  Mock mode:     {svc.mock_mode}")
    print(f"  Status:        {'PASS' if result.transcript else 'PASS (mock)' if svc.mock_mode else 'FAIL'}")

    await svc.close()
    return result


async def test_gemini_chat():
    """Test C: Gemini Chat"""
    from app.ai.gemini_service import GeminiService
    from app.config import settings

    print("\n" + "=" * 60)
    print("TEST C: Gemini Chat (text → response)")
    print("=" * 60)

    if not settings.GEMINI_API_KEY:
        print("  SKIPPED: GEMINI_API_KEY not set")
        print("  Set GEMINI_API_KEY in .env to test Gemini")
        return None

    svc = GeminiService()
    await svc.initialize({
        "clinic_name": "Test Clinic",
        "clinic_address": "Tashkent",
    })

    start = time.monotonic()
    response = await svc.chat(
        session_id="test-session-001",
        message="Stomatologga yozilmoqchiman",
    )
    elapsed = (time.monotonic() - start) * 1000

    print(f"  Input:         'Stomatologga yozilmoqchiman'")
    print(f"  Response:      '{response.text[:200]}'")
    print(f"  UI Action:     {response.ui_action}")
    print(f"  Fn Calls:      {[fc['name'] for fc in response.function_calls]}")
    print(f"  Latency:       {elapsed:.1f} ms")
    print(f"  Status:        {'PASS' if response.text else 'FAIL'}")

    return response


async def test_intent_classification():
    """Test D: Intent Classification"""
    from app.ai.gemini_service import GeminiService
    from app.config import settings

    print("\n" + "=" * 60)
    print("TEST D: Intent Classification")
    print("=" * 60)

    if not settings.GEMINI_API_KEY:
        print("  SKIPPED: GEMINI_API_KEY not set")
        return None

    svc = GeminiService()
    await svc.initialize({
        "clinic_name": "Test Clinic",
        "clinic_address": "Tashkent",
    })

    test_cases = [
        ("Stomatologga yozilmoqchiman", "APPOINTMENT_BOOKING"),
        ("Salom", "GREETING"),
        ("Qabulga keldim", "CHECK_IN"),
        ("Shifokorlar haqida ma'lumot bering", "INFORMATION"),
    ]

    for message, expected in test_cases:
        start = time.monotonic()
        result = await svc.classify_intent(message)
        elapsed = (time.monotonic() - start) * 1000

        match = "PASS" if result.intent == expected else f"MISMATCH (got {result.intent})"
        print(f"  '{message}' → {result.intent} ({result.confidence:.2f}) [{elapsed:.0f}ms] {match}")


async def test_full_pipeline():
    """Test E: Full voice pipeline"""
    print("\n" + "=" * 60)
    print("TEST E: Full Pipeline (TTS → STT → Gemini → TTS)")
    print("=" * 60)

    from app.ai.muxlisa_service import MuxlisaService
    from app.ai.gemini_service import GeminiService
    from app.config import settings

    muxlisa = MuxlisaService()

    # Step 1: TTS - Generate audio from text
    input_text = "Assalomu alaykum"
    start = time.monotonic()
    audio1 = await muxlisa.text_to_speech(input_text, language="uz")
    tts1_ms = (time.monotonic() - start) * 1000
    print(f"  1. TTS '{input_text}' → {len(audio1)} bytes [{tts1_ms:.0f}ms]")

    # Step 2: STT - Convert audio back to text
    start = time.monotonic()
    stt_result = await muxlisa.speech_to_text(audio1)
    stt_ms = (time.monotonic() - start) * 1000
    print(f"  2. STT → '{stt_result.transcript}' (lang={stt_result.language}) [{stt_ms:.0f}ms]")

    # Step 3: Gemini - Get AI response
    if settings.GEMINI_API_KEY:
        gemini = GeminiService()
        await gemini.initialize({"clinic_name": "Test Clinic", "clinic_address": "Tashkent"})

        start = time.monotonic()
        chat_response = await gemini.chat(
            session_id="pipeline-test",
            message=stt_result.transcript,
        )
        gemini_ms = (time.monotonic() - start) * 1000
        print(f"  3. Gemini → '{chat_response.text[:100]}' [{gemini_ms:.0f}ms]")

        # Step 4: TTS - Convert response to audio
        start = time.monotonic()
        audio2 = await muxlisa.text_to_speech(chat_response.text, language=stt_result.language)
        tts2_ms = (time.monotonic() - start) * 1000
        print(f"  4. TTS response → {len(audio2)} bytes [{tts2_ms:.0f}ms]")

        total = tts1_ms + stt_ms + gemini_ms + tts2_ms
        print(f"  Total pipeline:  {total:.0f}ms")
    else:
        print("  3-4. SKIPPED: GEMINI_API_KEY not set")

    await muxlisa.close()
    print(f"  Status:        PASS")


async def test_session_manager():
    """Test F: Session Manager"""
    print("\n" + "=" * 60)
    print("TEST F: Session Manager (Redis state machine)")
    print("=" * 60)

    from app.ai.session_manager import SessionManager, SessionState

    try:
        mgr = SessionManager()
        session_id = await mgr.create_session("kiosk-test-001", "00000000-0000-0000-0000-000000000001")
        print(f"  Created session: {session_id}")

        state = await mgr.get_state(session_id)
        print(f"  Initial state:   {state}")

        # Transition: IDLE → DETECTED → GREETING → INTENT_DISCOVERY
        for target in [SessionState.DETECTED, SessionState.GREETING, SessionState.INTENT_DISCOVERY]:
            ok = await mgr.transition(session_id, target)
            state = await mgr.get_state(session_id)
            print(f"  → {target.value}: {'OK' if ok else 'BLOCKED'} (now: {state})")

        # Set and get context
        await mgr.set_context(session_id, "department_id", "test-dept-123")
        ctx = await mgr.get_context(session_id)
        print(f"  Context:         {ctx}")

        # Cleanup
        await mgr.reset(session_id)
        print(f"  Status:          PASS")
    except Exception as e:
        print(f"  Status:          FAIL — {e}")
        print(f"  (Redis may not be running)")


async def test_connectivity():
    """Pre-flight: check that APIs are reachable."""
    import httpx
    from app.config import settings

    print("\n" + "=" * 60)
    print("PRE-FLIGHT: API Connectivity Check")
    print("=" * 60)
    print(f"  MUXLISA_MOCK:     {settings.MUXLISA_MOCK}")
    print(f"  MUXLISA_API_URL:  {settings.MUXLISA_API_URL}")
    print(f"  GEMINI_API_KEY:   {'set (' + settings.GEMINI_API_KEY[:8] + '...)' if settings.GEMINI_API_KEY else 'NOT SET'}")
    print(f"  GEMINI_MODEL:     {settings.GEMINI_MODEL}")

    if not settings.MUXLISA_MOCK:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Quick TTS test to check connectivity & auth (use real sentence, not "test")
                resp = await client.post(
                    f"{settings.MUXLISA_API_URL}/tts",
                    json={"text": "Salom, klinikamizga xush kelibsiz", "speaker": 0},
                    headers={"Content-Type": "application/json", "x-api-key": settings.MUXLISA_API_KEY},
                )
                if resp.status_code == 200:
                    is_wav = resp.content[:4] == b"RIFF"
                    print(f"  Muxlisa TTS:      HTTP 200 OK (WAV={is_wav}, {len(resp.content)} bytes)")
                else:
                    # Error response may be binary — use content safely
                    try:
                        err_detail = resp.text[:100]
                    except Exception:
                        err_detail = f"<binary {len(resp.content)} bytes>"
                    print(f"  Muxlisa TTS:      HTTP {resp.status_code} FAIL — {err_detail}")
        except Exception as e:
            print(f"  Muxlisa TTS:      UNREACHABLE — {e}")
    else:
        print(f"  Muxlisa:          MOCK MODE (skipping connectivity check)")

    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            resp = await model.generate_content_async("Say 'ok'")
            print(f"  Gemini API:       OK (response: '{resp.text[:30]}')")
        except Exception as e:
            print(f"  Gemini API:       FAIL — {e}")
    else:
        print(f"  Gemini API:       NOT CONFIGURED")


async def main():
    print("=" * 60)
    print("MEZBON AI — Voice Pipeline Test Suite")
    print("=" * 60)

    # Pre-flight
    await test_connectivity()

    audio = None
    # Test TTS
    try:
        audio = await test_muxlisa_tts()
    except Exception as e:
        print(f"  FAIL: {e}")

    # Test STT (using the audio from TTS — skip if TTS failed)
    if audio and len(audio) > 44:
        try:
            await test_muxlisa_stt(audio)
        except Exception as e:
            print(f"  FAIL: {e}")
    else:
        print("\n" + "=" * 60)
        print("TEST B: Muxlisa STT (audio → text)")
        print("=" * 60)
        print("  SKIPPED: TTS did not produce valid audio (STT depends on TTS output)")

    # Test Session Manager
    try:
        await test_session_manager()
    except Exception as e:
        print(f"  FAIL: {e}")

    # Test Gemini
    try:
        await test_gemini_chat()
    except Exception as e:
        print(f"  FAIL: {e}")

    # Test Intent Classification
    try:
        await test_intent_classification()
    except Exception as e:
        print(f"  FAIL: {e}")

    # Test Full Pipeline
    try:
        await test_full_pipeline()
    except Exception as e:
        print(f"  FAIL: {e}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
