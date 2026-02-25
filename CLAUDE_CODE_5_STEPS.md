# CLAUDE CODE: FIX VOICE IN 5 STEPS

Copy this ENTIRE prompt to Claude Code. It will fix the voice system.

---

## CONTEXT
- Frontend: Captures audio ✅
- Backend: Receives audio ✅  
- Problem: Returns empty Object to frontend ❌

---

## STEP 1: SEE WHAT FRONTEND RECEIVES

**Edit:** `/Users/aliisroilov/Desktop/AI Reception/kiosk-ui/src/hooks/useSession.ts`

**Line 44, change from:**
```typescript
console.log('[session] ai:response received:', response);
```

**To:**
```typescript
console.log('[session] ai:response received:');
console.log('FULL RESPONSE:', JSON.stringify(response, null, 2));
```

Save. Rebuild frontend (`npm run dev`). Test. Screenshot console output.

---

## STEP 2: FORCE WORKING BACKEND RESPONSE

**Edit:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/kiosk_events.py`

**Find line ~150 with `orchestrator.handle_speech`**

**Replace that entire try block with:**

```python
try:
    # TEMPORARY: Force a working response
    from app.ai.orchestrator import OrchestratorResponse
    
    print("\n🎯 FORCING RESPONSE")
    
    response = OrchestratorResponse(
        text="Salom! Mock rejimda ishlayman.",
        session_id=session_id,
        state="GREETING",
        transcript="mock",
    )
    
    print(f"Response text: {response.text}")
    
    response_data = response.model_dump()
    
    print(f"Response data: {response_data}")
    print(f"Keys: {list(response_data.keys())}")
    
    await emit_to_device("ai:response", response_data, device_id)
    
    print("✅ Sent!")
```

Save. Restart backend (`python3 -m app.main`). Test. Look at terminal output.

---

## STEP 3: IF STEP 2 WORKS

**The orchestrator is the problem.**

**Edit:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/ai/orchestrator.py`

**At the START of `handle_speech` method (~line 130), add:**

```python
async def handle_speech(self, session_id: str, audio_bytes: bytes) -> OrchestratorResponse:
    # TEMPORARY: Return immediately
    logger.warning("ORCHESTRATOR: Returning mock immediately")
    return OrchestratorResponse(
        text="Test from orchestrator",
        session_id=session_id,
        state="GREETING",
        transcript="mock",
    )
    # (rest of method below)
```

Test. If this works, the problem is INSIDE handle_speech.

---

## STEP 4: IF STEP 2 FAILS

**The socket is the problem.**

**Edit:** `/Users/aliisroilov/Desktop/AI Reception/backend/app/sockets/server.py`

**Find `emit_to_device` function. Replace with:**

```python
async def emit_to_device(event: str, data: dict[str, Any], device_id: str) -> None:
    """Emit to specific device."""
    print(f"\n📡 emit_to_device:")
    print(f"   Event: {event}")
    print(f"   Data: {data}")
    print(f"   Device: {device_id}")
    
    for sid, meta in _sid_metadata.items():
        if meta.get("device_id") == device_id:
            print(f"   Emitting to SID: {sid}")
            await sio.emit(event, data, to=sid)
            print(f"   ✅ Done")
            return
    
    print(f"   ❌ Device {device_id} not found!")
```

Test. Look at terminal. Does it emit? Does frontend receive?

---

## STEP 5: VERIFY .ENV

**Run:**
```bash
grep MUXLISA_MOCK /Users/aliisroilov/Desktop/AI\ Reception/backend/.env
```

**Must show:** `MUXLISA_MOCK=true`

**If not, run:**
```bash
echo "MUXLISA_MOCK=true" >> /Users/aliisroilov/Desktop/AI\ Reception/backend/.env
```

---

## AFTER EXECUTING

**Tell me:**
1. Output from Step 1 (frontend console)
2. Output from Step 2 (backend terminal)
3. Which step worked or failed
4. Full error messages if any

---

**EXECUTE THESE 5 STEPS NOW.**
