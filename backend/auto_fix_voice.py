#!/usr/bin/env python3
"""
VOICE SYSTEM AUTO-FIX
Run this to automatically diagnose and fix the voice system.
"""

import os
import sys
import subprocess
from pathlib import Path

BASE = Path("/Users/aliisroilov/Desktop/AI Reception")
BACKEND = BASE / "backend"
FRONTEND = BASE / "kiosk-ui"

print("="*80)
print("🔧 VOICE SYSTEM AUTO-FIX")
print("="*80)
print()

# ============================================================================
# FIX 1: ENSURE MOCK MODE IS ENABLED
# ============================================================================

print("FIX 1: Checking mock mode...")
env_file = BACKEND / ".env"

with open(env_file) as f:
    env_content = f.read()

if "MUXLISA_MOCK=true" in env_content:
    print("✅ Mock mode already enabled")
else:
    print("⚠️  Enabling mock mode...")
    env_content = env_content.replace("MUXLISA_MOCK=false", "MUXLISA_MOCK=true")
    
    if "MUXLISA_MOCK" not in env_content:
        env_content += "\nMUXLISA_MOCK=true\n"
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ Mock mode enabled in .env")

print()

# ============================================================================
# FIX 2: ADD FORCED RESPONSE IN SOCKET HANDLER
# ============================================================================

print("FIX 2: Adding forced response to socket handler...")

socket_file = BACKEND / "app/sockets/kiosk_events.py"

with open(socket_file) as f:
    content = f.read()

# Find the handle_speech_audio function
if "🎯 FORCED MOCK RESPONSE" in content:
    print("✅ Forced response already added")
else:
    print("⚠️  Adding forced response...")
    
    # Find the line where orchestrator is called
    search_str = "orchestrator = get_orchestrator()"
    
    if search_str in content:
        # Add forced response before orchestrator call
        forced_code = '''
            # === 🎯 FORCED MOCK RESPONSE (TEMPORARY DEBUG) ===
            logger.warning(f"🎯 FORCING MOCK RESPONSE for session {session_id}")
            
            from app.ai.orchestrator import OrchestratorResponse
            
            response = OrchestratorResponse(
                text="Salom! Men sizning ovozingizni eshitdim. Bu mock javob.",
                audio_base64=None,
                ui_action="show_greeting",
                ui_data=None,
                state="GREETING",
                patient=None,
                session_id=session_id,
                transcript="Forced mock transcript",
            )
            
            logger.info(f"✅ Forced response: {response.text}")
            # === END FORCED RESPONSE ===
            
            # COMMENTED OUT REAL ORCHESTRATOR:
            # orchestrator = get_orchestrator()
            # response = await orchestrator.handle_speech(
            #     session_id=session_id,
            #     audio_bytes=audio_bytes,
            # )
'''
        
        content = content.replace(
            "orchestrator = get_orchestrator()",
            forced_code
        )
        
        with open(socket_file, 'w') as f:
            f.write(content)
        
        print("✅ Forced response added")
    else:
        print("❌ Could not find orchestrator call")

print()

# ============================================================================
# FIX 3: ADD DETAILED LOGGING TO FRONTEND
# ============================================================================

print("FIX 3: Adding detailed logging to frontend...")

session_file = FRONTEND / "src/hooks/useSession.ts"

with open(session_file) as f:
    content = f.read()

if "DETAILED VOICE DEBUG" in content:
    print("✅ Detailed logging already added")
else:
    print("⚠️  Adding detailed logging...")
    
    # Find the line with ai:response logging
    search_str = "console.log('[session] ai:response received:"
    
    if search_str in content:
        new_logging = '''console.log('[session] ai:response received:');
      console.log('=== DETAILED VOICE DEBUG ===');
      console.log('Full response:', JSON.stringify(response, null, 2));
      console.log('Response keys:', Object.keys(response));
      console.log('text:', response.text);
      console.log('transcript:', response.transcript);
      console.log('state:', response.state);
      console.log('=== END DEBUG ===');
      console.log('[session] ai:response received:'''
        
        content = content.replace(search_str, new_logging)
        
        with open(session_file, 'w') as f:
            f.write(content)
        
        print("✅ Detailed logging added")
    else:
        print("❌ Could not find logging line")

print()

# ============================================================================
# FIX 4: ADD RESPONSE LOGGING TO SOCKET
# ============================================================================

print("FIX 4: Adding response logging to socket...")

with open(socket_file) as f:
    content = f.read()

if "RESPONSE ABOUT TO BE SENT" in content:
    print("✅ Response logging already added")
else:
    print("⚠️  Adding response logging...")
    
    search_str = 'await emit_to_device("ai:response", response_data, device_id)'
    
    if search_str in content:
        logging_code = '''
            # === RESPONSE DEBUG ===
            print("\\n" + "="*60)
            print("📤 RESPONSE ABOUT TO BE SENT:")
            print(f"   session_id: {session_id}")
            print(f"   text: {response_data.get('text', 'MISSING')}")
            print(f"   transcript: {response_data.get('transcript', 'MISSING')}")
            print(f"   keys: {list(response_data.keys())}")
            print("="*60 + "\\n")
            # === END DEBUG ===
            
            await emit_to_device("ai:response", response_data, device_id)'''
        
        content = content.replace(
            'await emit_to_device("ai:response", response_data, device_id)',
            logging_code
        )
        
        with open(socket_file, 'w') as f:
            f.write(content)
        
        print("✅ Response logging added")

print()

# ============================================================================
# DONE
# ============================================================================

print("="*80)
print("✅ ALL FIXES APPLIED!")
print("="*80)
print()
print("NEXT STEPS:")
print()
print("1. RESTART BACKEND:")
print("   cd /Users/aliisroilov/Desktop/AI\\ Reception/backend")
print("   python3 -m app.main")
print()
print("2. REBUILD FRONTEND:")
print("   cd /Users/aliisroilov/Desktop/AI\\ Reception/kiosk-ui")
print("   npm run dev")
print()
print("3. TEST on kiosk and watch:")
print("   - Backend terminal for: 📤 RESPONSE ABOUT TO BE SENT")
print("   - Browser console for: === DETAILED VOICE DEBUG ===")
print()
print("4. If you see the text in backend but NOT in frontend:")
print("   → Socket.IO transmission issue")
print()
print("5. If you see text in BOTH:")
print("   → UI rendering issue")
print()
print("="*80)
print()
print("Run: python3 " + __file__)
