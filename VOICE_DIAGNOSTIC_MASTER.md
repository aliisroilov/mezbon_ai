# 🔬 COMPLETE AI VOICE DIAGNOSTIC & FIX

## THE ISSUE

**Frontend:** ✅ Working perfectly - capturing audio, sending to backend  
**Backend:** ❌ Returning empty transcripts (`transcript: undefined`)  
**Result:** "Ovozingiz eshitilmayapti" (Voice not heard)

---

## 🎯 AUTONOMOUS DIAGNOSTIC MISSION

**YOU ARE AUTHORIZED TO:**
- Read any file
- Modify any code  
- Run any test
- Install dependencies
- Fix ALL bugs
- NO NEED TO ASK PERMISSION

**DO NOT STOP** until voice recognition is working 100%.

---

## 📋 DIAGNOSTIC SEQUENCE

### PHASE 1: TEST MUXLISA API DIRECTLY

**Run this test:**

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 test_muxlisa_stt.py
```

**Expected issues:**
1. ❌ API key invalid → Fix: Get new key from Muxlisa
2. ❌ API endpoint wrong → Fix: Update MUXLISA_API_URL in .env
3. ❌ Network error → Fix: Check internet/firewall
4. ❌ Audio format rejected → Fix: Change format

**If test fails, STOP and report the error.**

---

### PHASE 2: CREATE COMPREHENSIVE TEST SUITE

Create `/Users/aliisroilov/Desktop/AI Reception/backend/test_full_voice_pipeline.py`:

```python
#!/usr/bin/env python3
"""
COMPLETE VOICE PIPELINE DIAGNOSTIC
Tests EVERY step from audio input → final response
"""

import asyncio
import sys
import os
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.ai.muxlisa_service import MuxlisaService
from app.ai.gemini_service import GeminiService
from app.ai.orchestrator import Orchestrator
from app.ai.session_manager import SessionManager
from app.ai.face_service import FaceService
from app.core.database import async_session_factory
from app.config import settings
from loguru import logger
import httpx

print("=" * 80)
print("🔬 COMPLETE VOICE PIPELINE DIAGNOSTIC")
print("=" * 80)
print()

async def test_1_config():
    """Test 1: Verify configuration"""
    print("TEST 1: Configuration Check")
    print("-" * 80)
    
    print(f"✓ MUXLISA_API_URL: {settings.MUXLISA_API_URL}")
    print(f"✓ MUXLISA_API_KEY: {settings.MUXLISA_API_KEY[:20]}...{settings.MUXLISA_API_KEY[-4:]}")
    print(f"✓ MUXLISA_MOCK: {settings.MUXLISA_MOCK}")
    print(f"✓ GEMINI_API_KEY: {settings.GEMINI_API_KEY[:20]}...")
    print(f"✓ GEMINI_MODEL: {settings.GEMINI_MODEL}")
    print()
    
    if settings.MUXLISA_MOCK:
        print("⚠️  WARNING: Muxlisa is in MOCK mode!")
        print("   Set MUXLISA_MOCK=false in .env to test real API")
        print()
    
    return True

async def test_2_network():
    """Test 2: Network connectivity to Muxlisa"""
    print("TEST 2: Network Connectivity")
    print("-" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            print(f"Testing connection to {settings.MUXLISA_API_URL}...")
            
            # Try ping/health endpoint
            try:
                response = await client.get(
                    f"{settings.MUXLISA_API_URL}/health",
                    headers={"x-api-key": settings.MUXLISA_API_KEY}
                )
                print(f"✅ Health endpoint: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Health endpoint unavailable (might be normal): {e}")
            
            # Try STT endpoint with OPTIONS (CORS preflight)
            try:
                response = await client.options(
                    f"{settings.MUXLISA_API_URL}/stt",
                    headers={"x-api-key": settings.MUXLISA_API_KEY}
                )
                print(f"✅ STT endpoint reachable: {response.status_code}")
            except Exception as e:
                print(f"❌ STT endpoint unreachable: {e}")
                return False
            
        print("✅ Network connectivity OK")
        print()
        return True
        
    except Exception as e:
        print(f"❌ NETWORK ERROR: {e}")
        print()
        print("FIXES:")
        print("  1. Check internet connection")
        print("  2. Check if Muxlisa API is down")
        print("  3. Verify MUXLISA_API_URL is correct")
        print()
        return False

async def test_3_muxlisa_stt():
    """Test 3: Muxlisa STT with real audio"""
    print("TEST 3: Muxlisa STT Test")
    print("-" * 80)
    
    muxlisa = MuxlisaService()
    
    # Generate test audio (440Hz beep for 1 second)
    print("Generating test audio (1s beep at 440Hz)...")
    test_audio = generate_beep_wav(1000, 440)
    print(f"Test audio size: {len(test_audio)} bytes")
    print()
    
    print("Sending to Muxlisa STT API...")
    print("-" * 40)
    
    try:
        result = await muxlisa.speech_to_text(test_audio, "wav")
        
        print(f"Transcript: '{result.transcript}'")
        print(f"Language: {result.language}")
        print(f"Confidence: {result.confidence}")
        print()
        
        if not result.transcript:
            print("❌ EMPTY TRANSCRIPT!")
            print()
            print("This is THE PROBLEM - Muxlisa is not transcribing audio.")
            print()
            print("Possible causes:")
            print("  1. Audio format not supported by Muxlisa")
            print("  2. Audio is just a tone (no speech)")
            print("  3. Muxlisa API key lacks STT permissions")
            print("  4. Muxlisa server returning errors")
            print()
            
            # Test with silence
            print("Testing with 2 seconds of silence...")
            silence = generate_silence_wav(2000)
            result2 = await muxlisa.speech_to_text(silence, "wav")
            print(f"Silence transcript: '{result2.transcript}'")
            print()
            
            await muxlisa.close()
            return False
        else:
            print("✅ Muxlisa STT working (transcribed beep as speech)")
            print()
        
        await muxlisa.close()
        return True
        
    except Exception as e:
        print(f"❌ STT FAILED: {e}")
        logger.exception("STT error")
        await muxlisa.close()
        return False

async def test_4_real_audio():
    """Test 4: Test with captured real audio from frontend"""
    print("TEST 4: Real Audio Test")
    print("-" * 80)
    
    print("This test uses actual audio captured from your kiosk.")
    print()
    
    # Check if we have saved audio
    audio_dir = Path("/Users/aliisroilov/Desktop/AI Reception/backend/test_audio")
    audio_dir.mkdir(exist_ok=True)
    
    # Look for test audio files
    test_files = list(audio_dir.glob("*.wav"))
    
    if not test_files:
        print("⚠️  No test audio files found.")
        print(f"   Save a real recording to: {audio_dir}")
        print()
        print("To capture real audio:")
        print("  1. Speak into kiosk mic")
        print("  2. In browser console, run:")
        print("     window.saveLastAudio = function(blob) {")
        print("       const url = URL.createObjectURL(blob);")
        print("       const a = document.createElement('a');")
        print("       a.href = url;")
        print("       a.download = 'test_audio.wav';")
        print("       a.click();")
        print("     }")
        print()
        return True  # Not a failure, just skip
    
    print(f"Found {len(test_files)} test audio files")
    print()
    
    muxlisa = MuxlisaService()
    
    for audio_file in test_files[:3]:  # Test first 3
        print(f"Testing: {audio_file.name}")
        audio_bytes = audio_file.read_bytes()
        print(f"Size: {len(audio_bytes)} bytes")
        
        try:
            result = await muxlisa.speech_to_text(audio_bytes, "wav")
            print(f"✅ Transcript: '{result.transcript}'")
            print(f"   Language: {result.language}")
            print()
            
            if not result.transcript:
                print("❌ Empty transcript from real audio!")
                print()
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    
    await muxlisa.close()
    return True

async def test_5_audio_format():
    """Test 5: Verify audio format compatibility"""
    print("TEST 5: Audio Format Test")
    print("-" * 80)
    
    print("Testing different audio formats...")
    print()
    
    muxlisa = MuxlisaService()
    
    formats = [
        ("wav", generate_beep_wav(500, 440)),
        # Add more formats if needed
    ]
    
    for fmt, audio_bytes in formats:
        print(f"Format: {fmt} ({len(audio_bytes)} bytes)")
        try:
            result = await muxlisa.speech_to_text(audio_bytes, fmt)
            status = "✅" if result.transcript else "⚠️ "
            print(f"{status} Result: '{result.transcript[:50] if result.transcript else '(empty)'}'")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
    
    await muxlisa.close()
    return True

async def test_6_gemini():
    """Test 6: Gemini API connectivity"""
    print("TEST 6: Gemini API Test")
    print("-" * 80)
    
    print("Testing Gemini connection...")
    
    try:
        gemini = GeminiService()
        
        # Simple test message
        async with async_session_factory() as db:
            from uuid import uuid4, UUID
            
            test_session_id = str(uuid4())
            test_clinic_id = UUID("00000000-0000-0000-0000-000000000000")
            
            response = await gemini.chat(
                session_id=test_session_id,
                message="Salom, qanday yordam bera olaman?",
                patient_context=None,
                clinic_id=test_clinic_id,
                db=db,
            )
            
            print(f"✅ Gemini response: '{response.text[:100]}'")
            print()
            return True
            
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        logger.exception("Gemini test failed")
        return False

async def test_7_full_pipeline():
    """Test 7: Complete pipeline (STT → Gemini → Response)"""
    print("TEST 7: Full Pipeline Test")
    print("-" * 80)
    
    print("Testing complete voice processing pipeline...")
    print()
    
    try:
        # Create services
        muxlisa = MuxlisaService()
        gemini = GeminiService()
        face = FaceService()
        session_mgr = SessionManager()
        
        orchestrator = Orchestrator(
            gemini=gemini,
            face=face,
            muxlisa=muxlisa,
            session_mgr=session_mgr,
            db_session_factory=async_session_factory,
        )
        
        # Generate test audio
        test_audio = generate_beep_wav(1000, 440)
        
        print(f"1. Test audio generated: {len(test_audio)} bytes")
        
        # Create test session
        from uuid import UUID
        test_session_id = await session_mgr.create_session(
            device_id="test-device",
            clinic_id=UUID("00000000-0000-0000-0000-000000000000"),
        )
        
        print(f"2. Session created: {test_session_id}")
        
        # Transition to GREETING state
        from app.ai.session_manager import SessionState
        await session_mgr.transition(test_session_id, SessionState.DETECTED)
        await session_mgr.transition(test_session_id, SessionState.GREETING)
        
        print(f"3. Session in GREETING state")
        print()
        
        # Process speech
        print("4. Processing speech through orchestrator...")
        print("-" * 40)
        
        response = await orchestrator.handle_speech(
            session_id=test_session_id,
            audio_bytes=test_audio,
        )
        
        print()
        print(f"✅ Pipeline Response:")
        print(f"   Text: '{response.text}'")
        print(f"   Transcript: '{response.transcript}'")
        print(f"   State: {response.state}")
        print(f"   UI Action: {response.ui_action}")
        print()
        
        if not response.transcript:
            print("❌ PIPELINE ISSUE: No transcript!")
            print()
            print("The orchestrator processed audio but got no transcript.")
            print("This confirms Muxlisa STT is the bottleneck.")
            print()
            return False
        
        print("✅ Full pipeline working!")
        await muxlisa.close()
        return True
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        logger.exception("Pipeline test failed")
        return False

async def test_8_backend_logs():
    """Test 8: Check backend logs for errors"""
    print("TEST 8: Backend Logs Analysis")
    print("-" * 80)
    
    log_file = Path("/Users/aliisroilov/Desktop/AI Reception/backend/logs/mezbon.log")
    
    if not log_file.exists():
        print("⚠️  No log file found")
        print(f"   Expected: {log_file}")
        print()
        return True
    
    print(f"Analyzing {log_file}...")
    print()
    
    # Read last 100 lines
    with open(log_file) as f:
        lines = f.readlines()
        recent_lines = lines[-100:]
    
    # Look for STT errors
    stt_errors = [l for l in recent_lines if "STT" in l and ("error" in l.lower() or "fail" in l.lower())]
    muxlisa_errors = [l for l in recent_lines if "Muxlisa" in l and ("error" in l.lower() or "fail" in l.lower())]
    
    if stt_errors:
        print("❌ Found STT errors in logs:")
        for line in stt_errors[-5:]:
            print(f"   {line.strip()}")
        print()
    
    if muxlisa_errors:
        print("❌ Found Muxlisa errors in logs:")
        for line in muxlisa_errors[-5:]:
            print(f"   {line.strip()}")
        print()
    
    if not stt_errors and not muxlisa_errors:
        print("✅ No obvious STT errors in recent logs")
        print()
    
    return True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_beep_wav(duration_ms: int, frequency: int = 440) -> bytes:
    """Generate WAV with sine wave beep"""
    import struct
    import math
    
    sample_rate = 16000
    num_samples = int(sample_rate * duration_ms / 1000)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    
    samples = bytearray()
    for i in range(num_samples):
        sample = int(16000 * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples.extend(struct.pack("<h", sample))
    
    return header + bytes(samples)

def generate_silence_wav(duration_ms: int) -> bytes:
    """Generate silent WAV"""
    import struct
    
    sample_rate = 16000
    num_samples = int(sample_rate * duration_ms / 1000)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
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

# ============================================================================
# MAIN DIAGNOSTIC RUNNER
# ============================================================================

async def run_all_tests():
    """Run all diagnostic tests"""
    
    tests = [
        ("Configuration", test_1_config),
        ("Network Connectivity", test_2_network),
        ("Muxlisa STT", test_3_muxlisa_stt),
        ("Real Audio", test_4_real_audio),
        ("Audio Formats", test_5_audio_format),
        ("Gemini API", test_6_gemini),
        ("Full Pipeline", test_7_full_pipeline),
        ("Backend Logs", test_8_backend_logs),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            logger.exception(f"{name} test failed")
            results[name] = False
        
        print()
    
    # Summary
    print("=" * 80)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print()
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    
    failed = [name for name, passed in results.items() if not passed]
    
    if failed:
        print(f"❌ {len(failed)} test(s) failed:")
        for name in failed:
            print(f"   - {name}")
        print()
        print("NEXT STEPS:")
        print("  1. Fix failing tests in order")
        print("  2. Focus on Muxlisa STT first (most likely culprit)")
        print("  3. Re-run this diagnostic after fixes")
        print()
    else:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("If voice still doesn't work:")
        print("  1. Check browser console for frontend errors")
        print("  2. Verify microphone permissions")
        print("  3. Test with different microphone")
        print()
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
```

**Save this and run:**

```bash
python3 test_full_voice_pipeline.py
```

---

### PHASE 3: CAPTURE REAL AUDIO FOR TESTING

Add this to your frontend to save the exact audio being sent:

In `/Users/aliisroilov/Desktop/AI Reception/kiosk-ui/src/hooks/useMicrophone.ts`, modify `buildAndSendWAV`:

```typescript
const buildAndSendWAV = useCallback(() => {
  // ... existing code ...
  
  if (wavBlob.size > 44 && durationMs > 500) {
    console.log(`[mic] Sending audio: ${durationMs}ms, ${wavBlob.size} bytes`);
    
    // 🔬 DIAGNOSTIC: Save audio to download
    if ((window as any).debugSaveAudio) {
      const url = URL.createObjectURL(wavBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `test_audio_${Date.now()}.wav`;
      a.click();
      URL.revokeObjectURL(url);
      console.log('💾 Audio saved for diagnostics');
    }
    
    onAudioReady?.(wavBlob);
  }
}, [onAudioReady, targetSampleRate]);
```

**Then in browser console:**
```javascript
window.debugSaveAudio = true;
```

Now when you speak, it will download the WAV file. Upload that to:
```
/Users/aliisroilov/Desktop/AI Reception/backend/test_audio/
```

---

### PHASE 4: FIX MUXLISA API ISSUE

Based on test results, apply one of these fixes:

#### FIX A: API Key Invalid

Update `.env`:
```env
MUXLISA_API_KEY=NEW_KEY_FROM_MUXLISA
```

#### FIX B: Wrong Audio Format

Modify `muxlisa_service.py` to try different formats:

```python
# Try multiple formats
for fmt in ["wav", "webm", "ogg"]:
    try:
        result = await self._try_format(audio_bytes, fmt)
        if result.transcript:
            return result
    except:
        continue
```

#### FIX C: Add Audio Preprocessing

Before sending to Muxlisa, ensure proper format:

```python
async def _preprocess_audio(self, audio_bytes: bytes) -> bytes:
    """Ensure audio is in Muxlisa-compatible format"""
    import io
    import wave
    
    # Verify it's valid WAV
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
            # Must be: 16kHz, mono, 16-bit
            if wav.getframerate() != 16000:
                # Resample needed
                audio_bytes = await self._resample(audio_bytes, 16000)
            
            if wav.getnchannels() != 1:
                # Convert to mono
                audio_bytes = await self._to_mono(audio_bytes)
    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
    
    return audio_bytes
```

---

### PHASE 5: ADD FALLBACK TTS

If Muxlisa TTS fails, use Google TTS:

```python
async def text_to_speech_fallback(self, text: str, language: str) -> bytes:
    """Fallback TTS using gTTS"""
    try:
        from gtts import gTTS
        import io
        
        tts = gTTS(text=text, lang=language, slow=False)
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        return audio_io.getvalue()
    except Exception as e:
        logger.error(f"Fallback TTS failed: {e}")
        return None
```

---

## 🎯 EXECUTION CHECKLIST

- [ ] Run `test_full_voice_pipeline.py`
- [ ] Identify which test fails
- [ ] Fix the failing component
- [ ] Re-run diagnostics
- [ ] Test on real kiosk
- [ ] Confirm "transcript" is not undefined
- [ ] Celebrate! 🎉

---

## 📊 EXPECTED ROOT CAUSE

Based on your logs showing `transcript: undefined`, the issue is **99% likely**:

1. **Muxlisa API returning empty responses** (most likely)
2. **Audio format mismatch**
3. **API key lacks STT permissions**
4. **Network/timeout issues**

---

## 🚀 IMMEDIATE ACTION

**RUN THIS NOW:**

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 test_full_voice_pipeline.py
```

**Then send me the COMPLETE output.** It will tell us EXACTLY what's broken and I'll provide the instant fix! 🎯
