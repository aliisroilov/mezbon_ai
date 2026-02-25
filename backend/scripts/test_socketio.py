"""Test Socket.IO connection and events.

Tests:
  B. Socket connection with auth
  C. Emit kiosk:touch_action and receive ai:response

Usage:
  1. Start the backend: uvicorn app.main:application --port 8000
  2. Run this script: python scripts/test_socketio.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import socketio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
DEVICE_ID = "kiosk-lobby-1"

# You need a valid JWT token. Generate one with:
#   python -c "from app.core.security import create_access_token; print(create_access_token({'sub': 'test', 'clinic_id': '<clinic_id>'}))"
# Or use the login endpoint to get one.
TOKEN = os.environ.get("TEST_JWT_TOKEN", "")


async def main():
    print("=" * 60)
    print("Socket.IO Connection Test")
    print("=" * 60)
    print(f"  Backend URL: {BACKEND_URL}")
    print(f"  Device ID:   {DEVICE_ID}")
    print(f"  Token:       {'SET' if TOKEN else 'NOT SET'}")
    print()

    if not TOKEN:
        print("WARNING: No JWT token set. Connection may be rejected.")
        print("Set TEST_JWT_TOKEN environment variable with a valid JWT.")
        print("Or run: python -c \"from app.core.security import create_access_token; print(create_access_token({'sub': 'test', 'clinic_id': 'your-clinic-id'}))\"")
        print()

    sio = socketio.AsyncClient(logger=False)
    response_received = asyncio.Event()
    received_data = {}

    @sio.on("connect")
    async def on_connect():
        print("[OK] Connected to Socket.IO server")

    @sio.on("disconnect")
    async def on_disconnect():
        print("[INFO] Disconnected")

    @sio.on("ai:response")
    async def on_ai_response(data):
        print("[OK] Received ai:response:")
        print(f"     session_id: {data.get('session_id')}")
        print(f"     text:       {data.get('text', '')[:100]}")
        print(f"     state:      {data.get('state')}")
        print(f"     ui_action:  {data.get('ui_action')}")
        print(f"     audio:      {'yes' if data.get('audio_base64') else 'no'}")
        received_data.update(data)
        response_received.set()

    @sio.on("ai:error")
    async def on_ai_error(data):
        print(f"[ERROR] ai:error: {data}")
        received_data.update(data)
        response_received.set()

    @sio.on("ai:state_change")
    async def on_state_change(data):
        print(f"[INFO] ai:state_change: {data}")

    try:
        auth = {"token": TOKEN, "device_id": DEVICE_ID} if TOKEN else {"device_id": DEVICE_ID}
        await sio.connect(
            BACKEND_URL,
            socketio_path="/ws/socket.io",
            auth=auth,
            transports=["websocket"],
        )
        print("[OK] Socket.IO connected")

        # Test: Emit a touch action
        print("\n--- Test: Emitting kiosk:touch_action ---")
        await sio.emit("kiosk:touch_action", {
            "device_id": DEVICE_ID,
            "session_id": "test-socket-session",
            "action": "select_intent",
            "data": {"intent": "INFORMATION"},
        })

        # Wait for response
        try:
            await asyncio.wait_for(response_received.wait(), timeout=10.0)
            print("\n[OK] Response received within timeout")
        except asyncio.TimeoutError:
            print("\n[FAIL] No response within 10 seconds")

    except socketio.exceptions.ConnectionError as e:
        print(f"[FAIL] Could not connect: {e}")
        print("  Make sure the backend is running: uvicorn app.main:application --port 8000")
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
    finally:
        if sio.connected:
            await sio.disconnect()

    print("\n" + "=" * 60)
    print("Socket.IO test complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
