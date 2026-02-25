# 🔥 COMPLETE VOICE SYSTEM FIX - CLAUDE CODE PROMPT

**MISSION:** Fix voice recognition system completely and autonomously. No questions, just fix everything.

---

## 🎯 SITUATION

**Frontend:** ✅ Working perfectly - capturing and sending audio  
**Backend:** ⚠️ Receiving audio but returning empty responses  
**Muxlisa API:** ❌ HTTP 500 errors (server down)  
**Current logs:**
```
useSession.ts:44 [session] ai:response received: Object
(but Object is empty - no text, no transcript)
```

---

## 📋 YOUR AUTONOMOUS MISSION

**YOU HAVE FULL AUTHORITY TO:**
- Read/modify ANY file in the project
- Restart services
- Test everything
- Fix ALL bugs
- NO need to ask permission

**GOAL:** Voice works perfectly with mock STT by end of this prompt execution.

---

## STEP 1: VERIFY MOCK MODE IS ENABLED

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/.env`

**Check:**
```bash
grep "MUXLISA_MOCK" .env
```

**If it shows `false`:**
```bash
sed -i '' 's/MUXLISA_MOCK=false/MUXLISA_MOCK=true/' .env
```

**Verify:**
```bash
grep "MUXLISA_MOCK" .env
# Should show: MUXLISA_MOCK=true
```

---

## STEP 2: CHECK BACKEND LOGS FOR ACTUAL ERROR

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/logs/mezbon.log`

**Read last 50 lines:**
```bash
tail -50 /Users/aliisroilov/Desktop/AI\ Reception/backend/logs/mezbon.log | grep -E "(STT|speech|transcript|error|ERROR)"
```

**Look for:**
- Any errors in orchestrator.py
- Any errors in muxlisa_service.py
- Empty transcript warnings
- Session state issues

**Document what you find.**

---

## STEP 3: ADD COMPREHENSIVE DEBUG LOGGING

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/ai/orchestrator.py`

**In the `handle_speech` method, find this section (around line 150):**

```python
# 1. Speech-to-text
t_stt = time.monotonic()
stt_result = await self.muxlisa.speech_to_text(audio_bytes)
stt_ms = (time.monotonic() - t_stt) * 1000
transcript = stt_result.transcript
language = stt_result.language
```

**Add EXTENSIVE logging right after:**

```python
# 1. Speech-to-text
t_stt = time.monotonic()
stt_result = await self.muxlisa.speech_to_text(audio_bytes)
stt_ms = (time.monotonic() - t_stt) * 1000
transcript = stt_result.transcript
language = stt_result.language

# === CRITICAL DEBUG LOGGING ===
logger.info(
    "🎤 STT RESULT RECEIVED",
    extra={
        "session_id": session_id,
        "transcript": transcript,
        "transcript_length": len(transcript) if transcript else 0,
        "language": language,
        "confidence": stt_result.confidence,
        "stt_ms": round(stt_ms, 1),
        "audio_bytes_received": len(audio_bytes),
    }
)

if not transcript or len(transcript.strip()) < 3:
    logger.warning(
        "⚠️ EMPTY OR SHORT TRANSCRIPT",
        extra={
            "session_id": session_id,
            "transcript": repr(transcript),
            "audio_size": len(audio_bytes),
        }
    )
# === END DEBUG LOGGING ===
```

---

## STEP 4: FIX EMPTY TRANSCRIPT HANDLING

**In the same file, find this code (around line 160):**

```python
if not transcript.strip() or len(transcript.strip()) < 3:
    lang = language or session.get("language", "uz")
    # Track consecutive empty transcripts...
```

**REPLACE the entire empty transcript handling block with:**

```python
if not transcript or not transcript.strip() or len(transcript.strip()) < 3:
    lang = language or session.get("language", "uz")
    
    logger.warning(
        "Empty transcript - checking mock mode",
        extra={
            "mock_mode": self.muxlisa.mock_mode,
            "transcript": repr(transcript),
            "session_id": session_id,
        }
    )
    
    # Track consecutive empty transcripts to avoid spamming
    empty_count = int(
        (await self.session_mgr.get_context(session_id)).get(
            "empty_transcript_count", 0
        )
    )
    empty_count += 1
    await self.session_mgr.set_context(
        session_id, "empty_transcript_count", empty_count
    )

    if empty_count == 1:
        text = _EMPTY_STT_TEXTS.get(lang, _EMPTY_STT_TEXTS["uz"])
    elif empty_count == 2:
        text = _EMPTY_STT_TEXTS_2.get(lang, _EMPTY_STT_TEXTS_2["uz"])
    else:
        # 3+ consecutive empty transcripts — stay silent, don't spam
        logger.warning(
            f"3+ consecutive empty transcripts, staying silent",
            extra={"session_id": session_id, "empty_count": empty_count}
        )
        return OrchestratorResponse(
            text="",
            state=session["state"],
            session_id=session_id,
            transcript=None,  # Explicitly set to None
        )

    logger.info(
        f"Returning empty transcript message: {text}",
        extra={"session_id": session_id, "empty_count": empty_count}
    )

    return OrchestratorResponse(
        text=text,
        audio_base64=None,
        state=session["state"],
        session_id=session_id,
        transcript=None,  # Explicitly set to None
    )
```

---

## STEP 5: ENSURE MOCK MODE WORKS

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/ai/muxlisa_service.py`

**Find the mock mode code (around line 77):**

```python
if self.mock_mode:
    result = STTResponse(
        transcript="Stomatologga yozilmoqchiman",
        language="uz",
        confidence=0.95,
    )
    self._log_stt(start, result, mock=True)
    return result
```

**Replace with MORE ROBUST version:**

```python
if self.mock_mode:
    logger.info(
        "🎭 MOCK MODE ACTIVE - Returning simulated transcript",
        extra={
            "audio_bytes": len(audio_bytes),
            "audio_format": audio_format,
        }
    )
    result = STTResponse(
        transcript="Stomatologga yozilmoqchiman",
        language="uz",
        confidence=0.95,
    )
    self._log_stt(start, result, mock=True)
    logger.info(
        f"✅ Mock STT returned: '{result.transcript}'",
        extra={"language": result.language, "confidence": result.confidence}
    )
    return result
```

---

## STEP 6: VERIFY RESPONSE CONSTRUCTION

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/ai/orchestrator.py`

**At the END of `handle_speech` method (around line 250), BEFORE the final return, add:**

```python
# === FINAL RESPONSE LOGGING ===
logger.info(
    "📤 FINAL RESPONSE BEING SENT",
    extra={
        "session_id": session_id,
        "response_text": response_text[:100] if response_text else "(empty)",
        "response_text_length": len(response_text) if response_text else 0,
        "ui_action": chat_response.ui_action,
        "final_state": final_state.value,
        "transcript": transcript[:50] if transcript else "(none)",
        "has_audio": audio_base64 is not None,
    }
)
# === END FINAL RESPONSE LOGGING ===

return OrchestratorResponse(
    text=response_text,
    audio_base64=None,  # TTS disabled
    ui_action=chat_response.ui_action or _STATE_UI_ACTIONS.get(final_state),
    ui_data=self._extract_ui_data(chat_response),
    state=final_state.value,
    patient=self._patient_from_context(context),
    session_id=session_id,
    transcript=transcript,  # Make sure transcript is passed!
)
```

---

## STEP 7: CHECK SOCKET HANDLER

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/kiosk_events.py`

**Find `handle_speech_audio` function (around line 135).**

**Add logging BEFORE and AFTER orchestrator call:**

```python
logger.info(
    "🎤 speech_audio received",
    extra={
        "sid": sid,
        "session_id": session_id,
        "audio_bytes": len(audio_bytes),
        "device_id": device_id,
        "audio_type": type(audio_raw).__name__,
    },
)

# Immediately acknowledge receipt so the frontend shows "processing"
await emit_to_device("ai:processing", {
    "session_id": session_id,
}, device_id)

try:
    orchestrator = get_orchestrator()
    
    # === ADD THIS LOG ===
    logger.info(
        "Calling orchestrator.handle_speech",
        extra={"session_id": session_id, "audio_size": len(audio_bytes)}
    )
    
    response = await orchestrator.handle_speech(
        session_id=session_id,
        audio_bytes=audio_bytes,
    )

    # === ADD THIS LOG ===
    logger.info(
        "✅ orchestrator.handle_speech completed",
        extra={
            "session_id": session_id,
            "response_text": response.text[:80] if response.text else "(empty)",
            "response_text_length": len(response.text) if response.text else 0,
            "transcript": response.transcript[:60] if response.transcript else "(none)",
            "state": response.state,
            "ui_action": response.ui_action,
        }
    )

    response_data = response.model_dump()
    
    # === ADD THIS LOG ===
    logger.info(
        "Emitting ai:response to device",
        extra={
            "session_id": session_id,
            "response_keys": list(response_data.keys()),
            "text_present": bool(response_data.get("text")),
            "transcript_present": bool(response_data.get("transcript")),
        }
    )
    
    await emit_to_device("ai:response", response_data, device_id)
```

---

## STEP 8: TEST WITH SIMPLIFIED FLOW

**Create test script:** `/Users/aliisroilov/Desktop/AI Reception/backend/test_mock_stt.py`

```python
#!/usr/bin/env python3
"""Quick test of mock STT"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.ai.muxlisa_service import MuxlisaService
from app.config import settings

async def test():
    print("=" * 60)
    print(f"Mock mode in settings: {settings.MUXLISA_MOCK}")
    print("=" * 60)
    
    service = MuxlisaService()
    print(f"Mock mode in service: {service.mock_mode}")
    
    # Test with dummy audio
    test_audio = b"RIFF" + b"\x00" * 100
    result = await service.speech_to_text(test_audio)
    
    print(f"\nResult:")
    print(f"  Transcript: '{result.transcript}'")
    print(f"  Language: {result.language}")
    print(f"  Confidence: {result.confidence}")
    
    if result.transcript:
        print("\n✅ MOCK STT WORKING!")
    else:
        print("\n❌ MOCK STT FAILED!")
    
    await service.close()

if __name__ == "__main__":
    asyncio.run(test())
```

**Run it:**
```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 test_mock_stt.py
```

**Expected output:**
```
Mock mode in settings: True
Mock mode in service: True
Result:
  Transcript: 'Stomatologga yozilmoqchiman'
  Language: uz
  Confidence: 0.95
✅ MOCK STT WORKING!
```

**If it fails, check .env file again!**

---

## STEP 9: RESTART BACKEND

**Kill existing backend:**
```bash
pkill -f "python.*app.main"
```

**Start fresh:**
```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 -m app.main
```

**Watch logs:**
```bash
tail -f logs/mezbon.log | grep -E "(STT|speech|transcript|Mock|MOCK)"
```

---

## STEP 10: TEST FROM KIOSK

**Speak into kiosk and watch backend logs for:**

1. `🎭 MOCK MODE ACTIVE` - confirms mock is working
2. `✅ Mock STT returned: 'Stomatologga yozilmoqchiman'` - STT working
3. `📤 FINAL RESPONSE BEING SENT` - response constructed
4. `Emitting ai:response to device` - sent to frontend

**If you see all 4, it's working!**

---

## STEP 11: IF STILL FAILING - NUCLEAR OPTION

**Create a FORCED mock response in socket handler:**

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/kiosk_events.py`

**In `handle_speech_audio`, REPLACE the orchestrator call with:**

```python
try:
    orchestrator = get_orchestrator()
    
    # === FORCE MOCK RESPONSE (TEMPORARY DEBUG) ===
    logger.warning("🚨 FORCING MOCK RESPONSE FOR DEBUG")
    from app.schemas.ai import OrchestratorResponse
    
    response = OrchestratorResponse(
        text="Salom! Men Mezbon AI. Sizga qanday yordam bera olaman?",
        audio_base64=None,
        ui_action="show_greeting",
        ui_data=None,
        state="GREETING",
        patient=None,
        session_id=session_id,
        transcript="FORCED MOCK TRANSCRIPT FOR DEBUG",
    )
    # === END FORCE ===
    
    # Uncomment this when testing real orchestrator:
    # response = await orchestrator.handle_speech(
    #     session_id=session_id,
    #     audio_bytes=audio_bytes,
    # )
```

**Test this - if it works, then the issue is in the orchestrator, not socket/frontend.**

---

## STEP 12: FINAL VERIFICATION

**Run complete diagnostic:**
```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 test_full_voice_pipeline.py
```

**Expected with mock mode:**
```
TEST 3: Muxlisa STT Test
✅ Transcript: 'Stomatologga yozilmoqchiman'
✅ Language: uz
✅ Confidence: 0.95
```

---

## 📊 SUCCESS CRITERIA

**System is FIXED when:**
- [x] `test_mock_stt.py` shows mock working
- [x] Backend logs show `🎭 MOCK MODE ACTIVE`
- [x] Backend logs show `✅ Mock STT returned`
- [x] Backend logs show `📤 FINAL RESPONSE BEING SENT` with text
- [x] Frontend receives response with text
- [x] Kiosk shows AI response instead of "Ovozingiz eshitilmayapti"

---

## 🎯 EXECUTION ORDER

1. Verify/enable mock mode in .env
2. Add all debug logging
3. Fix empty transcript handling
4. Test with test_mock_stt.py
5. Restart backend
6. Watch logs while testing on kiosk
7. If still fails, use nuclear option (forced mock response)
8. Document what fixed it

---

## 📝 REPORT BACK

**After execution, provide:**
1. Contents of `.env` MUXLISA_MOCK line
2. Output of `test_mock_stt.py`
3. Last 30 lines of backend logs when testing voice
4. What fixed it (which step)

---

**BEGIN EXECUTION NOW. FIX EVERYTHING. REPORT RESULTS.**
