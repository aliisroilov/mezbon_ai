# CLAUDE CODE: FIX EMPTY VOICE RESPONSE - SIMPLE & DIRECT

## THE PROBLEM
Frontend gets `Object` but it's empty - no text, no transcript.

## YOUR MISSION
Fix this in 15 minutes. No overthinking. Just fix it.

---

## STEP 1: SEE WHAT'S ACTUALLY BEING RETURNED

**File:** `/Users/aliisroilov/Desktop/AI Reception/kiosk-ui/src/hooks/useSession.ts`

**Find line 44:** `console.log('[session] ai:response received:', ...)`

**Replace with:**
```typescript
console.log('[session] ai:response received:');
console.log('  Full object:', JSON.stringify(response, null, 2));
console.log('  text:', response.text);
console.log('  transcript:', response.transcript);
console.log('  state:', response.state);
console.log('  All keys:', Object.keys(response));
```

**Save, rebuild frontend, test again. Look at browser console.**

---

## STEP 2: CHECK BACKEND IS SENDING DATA

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/kiosk_events.py`

**Find the `handle_speech_audio` function around line 135.**

**RIGHT BEFORE `await emit_to_device("ai:response", response_data, device_id)` add:**

```python
# === DEBUG: PRINT EXACT RESPONSE ===
print("\n" + "="*60)
print("🔍 RESPONSE ABOUT TO BE SENT:")
print(f"   session_id: {session_id}")
print(f"   response_data keys: {list(response_data.keys())}")
print(f"   text: {response_data.get('text', 'MISSING')}")
print(f"   transcript: {response_data.get('transcript', 'MISSING')}")
print(f"   state: {response_data.get('state', 'MISSING')}")
print(f"   Full response_data: {response_data}")
print("="*60 + "\n")
# === END DEBUG ===
```

**Save, restart backend, test again. Look at backend terminal.**

---

## STEP 3: FORCE A WORKING RESPONSE

**Same file, same function.**

**REPLACE the orchestrator call section with this FORCED response:**

```python
# Immediately acknowledge receipt
await emit_to_device("ai:processing", {
    "session_id": session_id,
}, device_id)

try:
    # === FORCE A KNOWN-GOOD RESPONSE ===
    logger.warning(f"🚨 FORCING MOCK RESPONSE (session: {session_id})")
    
    # Import the response model
    from app.ai.orchestrator import OrchestratorResponse
    
    # Create a simple, guaranteed-to-work response
    response = OrchestratorResponse(
        text="Salom! Men sizning ovozingizni eshitdim. Mock rejimida ishlayman.",
        audio_base64=None,
        ui_action="show_greeting",
        ui_data=None,
        state="GREETING",
        patient=None,
        session_id=session_id,
        transcript="Test transcript - mock mode",
    )
    
    logger.info(f"✅ Forced response created: {response.text[:50]}")
    # === END FORCED RESPONSE ===
    
    # COMMENT OUT the real orchestrator call for now:
    # orchestrator = get_orchestrator()
    # response = await orchestrator.handle_speech(
    #     session_id=session_id,
    #     audio_bytes=audio_bytes,
    # )
```

**Save, restart backend, test.**

**IF THIS WORKS:** The orchestrator is the problem.  
**IF THIS FAILS:** The socket/serialization is the problem.

---

## STEP 4A: IF FORCED RESPONSE WORKS

**The orchestrator is broken. Fix it:**

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/ai/orchestrator.py`

**Find `handle_speech` method.**

**At the VERY START of the method, add:**

```python
async def handle_speech(
    self,
    session_id: str,
    audio_bytes: bytes,
) -> OrchestratorResponse:
    """Visitor spoke something — STT → Gemini → TTS."""
    
    # === FORCE MOCK MODE RESPONSE FOR DEBUG ===
    logger.warning(f"🎭 ORCHESTRATOR: Forcing mock response (session: {session_id})")
    return OrchestratorResponse(
        text="Assalomu alaykum! Sizga qanday yordam bera olaman?",
        audio_base64=None,
        ui_action="show_greeting",
        ui_data=None,
        state="GREETING",
        patient=None,
        session_id=session_id,
        transcript="Mock transcript from orchestrator",
    )
    # === END FORCE - REMOVE WHEN WORKING ===
    
    # Rest of the method...
```

**If this works, gradually uncomment the real code to find where it breaks.**

---

## STEP 4B: IF FORCED RESPONSE STILL FAILS

**The response isn't being serialized properly.**

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/ai/orchestrator.py`

**Check the `OrchestratorResponse` model (top of file):**

```python
class OrchestratorResponse(BaseModel):
    """Standard response from the orchestrator to the kiosk."""

    text: str
    audio_base64: str | None = None
    ui_action: str | None = None
    ui_data: dict[str, Any] | None = None
    state: str
    patient: dict[str, Any] | None = None
    session_id: str
    transcript: str | None = None
```

**Make sure it has `model_config`:**

```python
class OrchestratorResponse(BaseModel):
    """Standard response from the orchestrator to the kiosk."""
    
    model_config = {"from_attributes": True}  # Add this line
    
    text: str
    audio_base64: str | None = None
    # ... rest of fields
```

---

## STEP 5: CHECK .ENV

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/.env`

**Run:**
```bash
grep MUXLISA_MOCK .env
```

**MUST show:**
```
MUXLISA_MOCK=true
```

**If not:**
```bash
echo "MUXLISA_MOCK=true" >> .env
```

---

## STEP 6: NUCLEAR OPTION - BYPASS EVERYTHING

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/kiosk_events.py`

**Replace ENTIRE `handle_speech_audio` function with:**

```python
@sio.on("kiosk:speech_audio")
async def handle_speech_audio(sid: str, data: dict[str, Any]) -> None:
    """SIMPLIFIED VERSION - JUST RETURN TEXT"""
    
    print("\n🎤 Speech audio received!")
    
    meta = get_sid_meta(sid)
    if not meta:
        print("❌ No meta")
        return
    
    device_id = data.get("device_id") or meta.get("device_id")
    session_id = data.get("session_id") or "test-session-123"
    
    print(f"   Device: {device_id}")
    print(f"   Session: {session_id}")
    
    # Send processing acknowledgment
    await emit_to_device("ai:processing", {"session_id": session_id}, device_id)
    
    # Send simple response
    simple_response = {
        "text": "Salom! Men sizning ovozingizni eshitdim. Sizga qanday yordam bera olaman?",
        "audio_base64": None,
        "ui_action": "show_greeting",
        "ui_data": None,
        "state": "GREETING",
        "patient": None,
        "session_id": session_id,
        "transcript": "Mock transcript",
    }
    
    print(f"📤 Sending response: {simple_response['text'][:50]}")
    
    await emit_to_device("ai:response", simple_response, device_id)
    
    print("✅ Response sent!\n")
```

**Save, restart backend, test.**

**IF THIS WORKS:** Build back up from here.  
**IF THIS FAILS:** The emit_to_device or Socket.IO is broken.

---

## STEP 7: CHECK SOCKET EMISSION

**File:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/server.py`

**Find `emit_to_device` function.**

**Add logging:**

```python
async def emit_to_device(event: str, data: dict[str, Any], device_id: str) -> None:
    """Emit to specific device by device_id."""
    
    print(f"🔊 emit_to_device called:")
    print(f"   Event: {event}")
    print(f"   Device ID: {device_id}")
    print(f"   Data keys: {list(data.keys()) if isinstance(data, dict) else 'NOT A DICT'}")
    
    # Find SID for this device
    for sid, meta in _sid_metadata.items():
        if meta.get("device_id") == device_id:
            print(f"   Found SID: {sid}")
            await sio.emit(event, data, to=sid)
            print(f"   ✅ Emitted!")
            return
    
    print(f"   ❌ Device not found: {device_id}")
    logger.warning(f"Device {device_id} not found in active connections")
```

---

## QUICK TEST SCRIPT

**Create:** `/Users/aliisroilov/Desktop/AI Reception/backend/test_response.py`

```python
#!/usr/bin/env python3
"""Test OrchestratorResponse serialization"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.ai.orchestrator import OrchestratorResponse

# Create a response
response = OrchestratorResponse(
    text="Test response",
    audio_base64=None,
    ui_action="show_greeting",
    ui_data=None,
    state="GREETING",
    patient=None,
    session_id="test-123",
    transcript="Test transcript",
)

print("Response object created:")
print(f"  text: {response.text}")
print(f"  session_id: {response.session_id}")

# Serialize it
data = response.model_dump()
print("\nSerialized (model_dump):")
print(f"  Keys: {list(data.keys())}")
print(f"  text: {data.get('text')}")

import json
json_str = json.dumps(data)
print(f"\nJSON length: {len(json_str)}")
print(f"JSON: {json_str[:200]}")

print("\n✅ Serialization works!")
```

**Run:**
```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 test_response.py
```

---

## EXECUTION ORDER

1. **Add frontend logging** → See what's received
2. **Add backend logging** → See what's sent
3. **Force simple response** → Bypass orchestrator
4. **If forced works** → Problem is orchestrator
5. **If forced fails** → Problem is socket/serialization
6. **Fix the problem layer**
7. **Test again**

---

## REPORT BACK WITH

1. Frontend console output (with the detailed logging)
2. Backend terminal output (with the print statements)
3. Result of `test_response.py`
4. Which step fixed it

---

**DO IT NOW. EXECUTE STEPS 1-6 IN ORDER. REPORT RESULTS.**
