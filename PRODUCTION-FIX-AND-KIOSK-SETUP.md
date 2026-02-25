# MEZBON AI — PRODUCTION FIX + KIOSK DEPLOYMENT PROMPT

## CONTEXT FOR CLAUDE CODE

You are fixing the Mezbon AI clinic reception kiosk — a production system deployed on a 32" vertical touchscreen kiosk (1080×1920 portrait, Intel i5-12450H, 8GB RAM, Windows, built-in webcam + thermal printer).

The codebase is at the current working directory. Read CLAUDE.md for full architecture.

**After the last round of fixes, there are STILL multiple bugs. Your job is to fix ALL of them and make this 100% production-ready, then create the Windows kiosk deployment config.**

---

## PHASE 1: AUDIT — READ BEFORE YOU TOUCH ANYTHING

Read these files FIRST. Do NOT start coding until you've read all of them:

```
backend/app/ai/orchestrator.py
backend/app/ai/gemini_service.py
backend/app/ai/muxlisa_service.py
backend/app/ai/session_manager.py
backend/app/ai/prompts/system_prompt.py
backend/app/ai/prompts/functions.py
backend/app/sockets/kiosk_events.py
kiosk-ui/src/App.tsx
kiosk-ui/src/hooks/useSession.ts
kiosk-ui/src/hooks/useMicrophone.ts
kiosk-ui/src/hooks/useVoiceChat.ts
kiosk-ui/src/hooks/useInactivity.ts
kiosk-ui/src/hooks/useAudio.ts
kiosk-ui/src/services/socket.ts
kiosk-ui/src/store/sessionStore.ts
kiosk-ui/src/router/ScreenRouter.tsx
kiosk-ui/src/router/useScreenHandlers.ts
kiosk-ui/src/screens/IdleScreen.tsx
kiosk-ui/src/screens/GreetingScreen.tsx
kiosk-ui/src/screens/IntentScreen.tsx
kiosk-ui/src/screens/DepartmentSelectScreen.tsx
kiosk-ui/src/screens/DoctorSelectScreen.tsx
kiosk-ui/src/screens/TimeSlotScreen.tsx
kiosk-ui/src/screens/BookingConfirmScreen.tsx
kiosk-ui/src/screens/QueueTicketScreen.tsx
kiosk-ui/src/screens/CheckInScreen.tsx
kiosk-ui/src/screens/PaymentScreen.tsx
kiosk-ui/src/screens/FarewellScreen.tsx
kiosk-ui/src/screens/InfoScreen.tsx
kiosk-ui/src/screens/HandOffScreen.tsx
kiosk-ui/src/types/index.ts
kiosk-ui/src/styles/globals.css
kiosk-ui/tailwind.config.ts
kiosk-ui/src/components/ai/AIAvatar.tsx
kiosk-ui/src/components/ai/ResponseBubble.tsx
kiosk-ui/src/components/ai/VoiceIndicator.tsx
kiosk-ui/src/components/feedback/LoadingMessage.tsx
kiosk-ui/src/components/feedback/SuccessAnimation.tsx
kiosk-ui/src/components/feedback/CountUpNumber.tsx
kiosk-ui/src/components/ui/Button.tsx
kiosk-ui/src/components/ui/Badge.tsx
kiosk-ui/src/components/ui/LanguageSelector.tsx
kiosk-ui/src/components/ui/DegradationBanner.tsx
kiosk-ui/src/utils/mockData.ts
kiosk-ui/src/i18n/uz.json
kiosk-ui/src/i18n/ru.json
kiosk-ui/src/i18n/en.json
kiosk-ui/vite.config.ts
```

After reading, list ALL bugs you find. Then fix them one by one.

---

## PHASE 2: KNOWN BUGS — FIX ALL OF THESE

### BUG A: INFINITE MIC LOOP (silence → "eshitmadim" spam)

**Symptom:** Console shows endless cycle of `kiosk:speech_audio` emissions even when nobody is speaking. AI repeatedly says "Kechirasiz, eshitmadim..."

**Root cause analysis needed:** The VAD in `useMicrophone.ts` is supposed to prevent sending silence, but something is still triggering audio sends. Check:

1. Is the `silenceThreshold` (0.015 in useMicrophone, 0.01 in useVoiceChat) too low? The kiosk mic in a clinic lobby will have ambient noise above 0.01 RMS. **FIX: Set threshold to 0.02 in BOTH places and make useVoiceChat pass its value to useMicrophone.**
2. Is `SPEECH_START_FRAMES = 8` too few? At ~30fps RAF, 8 frames = ~260ms. A door slam or cough could trigger this. **FIX: Increase to 12 frames (~400ms).**
3. After `stopRecording()`, the mic auto-restarts via `shouldListen`. Is it restarting too fast and catching echo/noise? **FIX: In useSession.ts, increase MIC_RESTART_DELAY from 2000 to 3000ms.**
4. The 2s cooldown in useVoiceChat `handleAudioReady` — is `lastSendRef` surviving across mic restarts? **Verify this works correctly.**
5. Is the `buildAndSendWAV` minimum duration check (200ms) too short? **FIX: Increase to 500ms minimum duration.**
6. Backend: the empty transcript counter resets on `empty_transcript_count = 0` when real speech arrives. But what if Muxlisa STT returns a very short transcript (1-2 chars) that's just noise? The `len(transcript.strip()) < 3` check in orchestrator.py catches this but increments the counter. **Verify the counter logic works and doesn't reset prematurely.**

### BUG B: DOCTORS SCREEN INFINITE LOADING

**Symptom:** User says "tish shifokoriga yozilmoqchiman". AI correctly navigates to DoctorSelectScreen but shows "Shifokorlar qidirilmoqda..." forever.

**Root cause chain — trace EVERY link:**

1. Gemini calls `get_department_info("stomatologiya")` + `navigate_screen("doctors")`
2. `gemini_service.py` `_execute_function_call` runs the real DB query OR demo fallback
3. `_extract_ui_data()` should put doctors into `ui_data.doctors`
4. `orchestrator.py` returns `ui_action="show_doctors"` + `ui_data={doctors: [...]}`
5. `kiosk_events.py` emits `ai:response` with full data
6. `useSession.ts` `handleUIAction("show_doctors", ...)` calls `s.setDoctors(normalizeDoctors(uiData.doctors))`
7. `sessionStore.ts` `doctors` array updates
8. `DoctorSelectScreen.tsx` reads `doctors` from store

**Fix every link that's broken:**
- In `_extract_ui_data()`: when `get_department_info` returns a single department with `doctors` array nested inside, make sure those doctors are extracted to `ui_data.doctors`. CHECK: the code does `if "doctors" in result and isinstance(result["doctors"], list): ui_data["doctors"] = result["doctors"]` — but only inside the `get_department_info` case. **Verify the demo fallback `_fn_demo_get_department_info` actually returns a `doctors` array.**
- In `useSession.ts` `handleUIAction`: the `show_doctors` case checks `if (Array.isArray(uiData.doctors))` — this is correct. But the fallback at the bottom also checks `fnResults`. **Verify fnResults parsing works for demo data.**
- The `DoctorSelectScreen` has a 3s loading timeout which is good. **But ensure the loading message actually disappears when doctors arrive (check that `doctors.length > 0` triggers the correct branch).**

### BUG C: WRONG SCREEN AFTER BOOKING

**Symptom:** Full booking flow works, AI says confirmation code, but screen shows registration/greeting instead of QueueTicketScreen.

**Root cause chain:**
1. When AI calls `book_appointment()`, Gemini should also call `navigate_screen("queue_ticket")`
2. The system prompt says: "Chipta: book_appointment() + navigate_screen('queue_ticket')"
3. `_determine_ui_action()` maps `book_appointment` → `"show_queue_ticket"` as fallback
4. `handleUIAction("show_queue_ticket", ...)` should set state to `BOOKING_COMPLETE`
5. `ScreenRouter` maps `BOOKING_COMPLETE` → `"queue"` → `QueueTicketScreen`

**Verify:**
- After `book_appointment()` executes, does `_extract_ui_data()` create a `ticket` object from the result? YES — the code creates `ui_data["ticket"]` from `confirmation_code`.
- Does `handleUIAction("show_queue_ticket", ...)` correctly find `uiData.ticket`? **Check if the `ticket` field name matches between backend and frontend.**
- Does the state actually transition to `BOOKING_COMPLETE`? The orchestrator calls `_transition_through()` — **check if the state machine allows direct transition from CONFIRM_BOOKING → BOOKING_COMPLETE. If not, intermediate states may be needed.**
- In `useScreenHandlers.ts` `handleConfirmBooking`: it sets `MOCK_QUEUE_TICKET` and state to `BOOKING_COMPLETE`. **This is the touch path — it uses mock data. When voice path sends the real booking, does `handleUIAction` run AFTER `handleConfirmBooking`? There may be a race condition.**

**FIX: Ensure the voice path (handleUIAction) takes priority over mock data when sessionId exists. In handleConfirmBooking, do NOT set mock ticket if sessionId exists — let the backend response drive it.**

### BUG D: TOUCH-ONLY FLOW RESETS TO GREETING

**Symptom:** Using touch buttons only (no voice), screen randomly jumps back to GreetingScreen mid-flow.

**Root cause candidates:**
1. `useInactivity` in App.tsx has `warningMs: 180_000` (3 min) and `resetMs: 300_000` (5 min). **But the events it listens to are: touchstart, mousedown, keydown + AI interaction changes. Touch taps should reset the timer.** Verify the event listeners are firing.
2. `onSessionTimeout` in `useSession.ts`: if `data.warning` is falsy, it calls `s.resetSession()`. **Is the backend sending unexpected timeout events?** Check if `session_manager.py` has a background TTL that triggers before the frontend timer.
3. The state machine: when `emitTouchAction` fires, the backend processes it and emits back `ai:state_change`. **If the backend's session has expired in Redis (600s TTL), the response will be `_expired_response` which sets state to IDLE.** This would show as a jump to GreetingScreen/IdleScreen.
4. **FIX: In `useScreenHandlers.ts`, EVERY handler that calls `emit()` should also call `window.dispatchEvent(new Event("user-interaction"))`. Add this custom event to the inactivity timer's reset events in App.tsx.**
5. **FIX: Backend session_manager.py — increase Redis session TTL from 600s to 900s. And ensure `touch()` (TTL refresh) is called on EVERY touch action.**

### BUG E: INACTIVITY TIMER STILL TOO AGGRESSIVE

**Symptom:** Warning popup appears while user is actively looking at doctors/time slots.

**Root cause:** The inactivity hook only listens to `touchstart, mousedown, keydown`. If the user is READING the screen (looking at doctor cards, deciding which time slot), there are no events firing.

**FIX:**
1. In `useInactivity.ts`, add `scroll` event to the listener list.
2. In `App.tsx`, also listen to `"screen-navigated"` custom event and fire it from ScreenRouter when screen changes.
3. Increase `warningMs` from 180_000 to 240_000 (4 min) and `resetMs` from 300_000 to 360_000 (6 min).
4. The processing/speaking/listening effects in App.tsx already call `recordActivity()` — verify these fire when voice interaction happens.

### BUG F: UI ISSUES ON ALL SCREENS

**Systematically check EVERY screen for these issues:**

1. **Portrait layout (1080×1920):** The kiosk is VERTICAL. All screens must work in portrait mode. No horizontal scrolling. Content must fit in 1080px width.
2. **Text overflow:** Long doctor names, department names, or AI messages must truncate with `...` or wrap gracefully. No text bleeding outside cards.
3. **Missing back/home buttons:** Every screen (except Idle) must have "← Orqaga" back button and "🏠" home button.
4. **Loading states:** Every screen that fetches data must have:
   - Immediate loading indicator
   - 5s timeout → show "Ma'lumot topilmadi" with retry button
   - Never infinite spinner
5. **Button tap targets:** Minimum 56px height on all buttons. Test by checking `min-h-[56px]` or equivalent.
6. **AI conversation display on interactive screens:** Screens with voice (Greeting, Doctor, TimeSlot, Booking) should show:
   - AI message bubble (left, white bg)
   - User's last speech (right, teal-50 bg, "Siz:" prefix)
   - Show last 2-3 messages only
   - Processing indicator when `isProcessing=true`
7. **FarewellScreen auto-reset:** Should auto-navigate to IDLE after 10s countdown. Verify timer works.
8. **QueueTicketScreen:** Auto-navigate to FAREWELL after 15s (already coded, verify it works). Ticket number should be 60-80px font.

### BUG G: USEAUDIO.TS — DEAD CODE

The file `kiosk-ui/src/hooks/useAudio.ts` may still have TTS audio playback logic. Since TTS is disabled (Muxlisa returns 500), this entire file should be a no-op. **Verify it's not blocking the response flow or causing delays.**

### BUG H: SOCKET RECONNECTION HANDLING

When the socket disconnects and reconnects:
1. Does `sessionId` survive? If the socket reconnects, the old session may still be in Redis.
2. If the session expired during disconnect, does the UI handle the error gracefully?
3. **FIX: On reconnect, if we have a sessionId, emit a "ping" to verify it's still valid. If not, reset to IDLE.**

---

## PHASE 3: SPEED OPTIMIZATION

Target: < 2 seconds from speech end to text appearing on screen.

### Backend timing
The orchestrator already has timing logs:
```
⏱ Pipeline timing | stt_ms: X | intent_ms: X | llm_ms: X | total_ms: X
```

**Verify these optimizations are actually in place:**

1. **Gemini config:** `max_output_tokens=100, temperature=0.2` — CONFIRMED in gemini_service.py
2. **History trimming:** `history[-10:]` — CONFIRMED in gemini_service.py
3. **System prompt:** Under 800 tokens — CONFIRMED in system_prompt.py
4. **httpx client reuse:** `MuxlisaService` creates client in `__init__` — CONFIRMED
5. **No TTS call:** `text_to_speech` returns None — CONFIRMED

**Additional optimizations to add:**
6. **Skip intent classification for non-early states:** In orchestrator.py, `classify_intent` is only called when state is GREETING or INTENT_DISCOVERY. CONFIRMED. But it's a separate Gemini call. **Consider removing intent classification entirely and letting the main chat handle intent via function calling.** This saves ~500ms.
7. **Frontend: show "Bir lahza..." instantly** when audio is sent. The `ai:processing` event is emitted immediately. **Verify the frontend shows a processing indicator in the conversation area, not just the avatar state.**
8. **Audio: 16kHz sample rate** — CONFIRMED in useMicrophone.ts `targetSampleRate = 16000`

---

## PHASE 4: KIOSK WINDOWS DEPLOYMENT

The kiosk hardware:
- 32" vertical touchscreen (1080×1920 portrait, FullHD)
- Intel i5-12450H, 8GB RAM, 256GB SSD M2
- Built-in 1080p webcam
- Built-in 80mm thermal receipt printer
- Windows 11

### Create these files in the project root:

#### 1. `kiosk-setup/install.bat`
Windows batch script that:
- Installs Node.js (LTS) silently if not present
- Installs Python 3.11 silently if not present
- Sets up the backend (venv, pip install, migrations)
- Builds kiosk-ui for production (`npm run build`)
- Installs and configures a lightweight HTTP server to serve the built frontend
- Creates Windows auto-login user account
- Configures Windows kiosk mode (Assigned Access or Shell Launcher)
- Opens Chrome in kiosk mode (`--kiosk --start-fullscreen --disable-session-crashed-bubble --noerrdialogs`) pointing to localhost
- Sets display orientation to portrait (1080×1920)
- Disables screen timeout / sleep
- Configures Windows firewall to allow backend port 8000
- Creates a Windows Task Scheduler entry to auto-start backend on boot
- Creates a startup script that launches both backend and Chrome

#### 2. `kiosk-setup/startup.bat`
Runs on every boot:
```batch
@echo off
REM Start PostgreSQL service
net start postgresql-x64-16

REM Start Redis
start /min redis-server

REM Start backend
cd /d C:\mezbon\backend
start /min cmd /c ".venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to be ready
timeout /t 10 /nobreak

REM Launch Chrome in kiosk mode
start chrome --kiosk --start-fullscreen --disable-session-crashed-bubble --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-features=TranslateUI http://localhost:5173
```

#### 3. `kiosk-setup/set-portrait.ps1`
PowerShell script to set display to portrait mode (1080×1920 rotation).

#### 4. `kiosk-setup/disable-peripherals.ps1`
PowerShell script to:
- Disable right-click
- Disable keyboard shortcuts (Alt+Tab, Win key, Ctrl+Alt+Del screen)
- Disable task manager access
- Hide taskbar
- Disable USB storage (prevent plugging in USB drives)
- Keep webcam and printer enabled

#### 5. `kiosk-setup/README.md`
Step-by-step deployment guide for the kiosk hardware.

#### 6. `kiosk-ui/vite.config.ts` update
If not already, configure Vite for production build:
- Set `base: './'` for relative paths (runs from file:// or local server)
- Enable gzip compression
- Set preview server to host `0.0.0.0`

#### 7. `kiosk-ui/src/config.ts` — NEW FILE
Create a runtime config that detects if running on kiosk:
```typescript
export const IS_KIOSK = window.location.hostname === 'localhost' 
  || window.location.hostname === '127.0.0.1';
export const KIOSK_ORIENTATION = 'portrait'; // 1080x1920
export const PRINTER_ENABLED = IS_KIOSK;
```

#### 8. Thermal printer integration
Create `kiosk-ui/src/utils/printer.ts`:
- Function to print queue ticket on the 80mm thermal printer
- Use the browser's `window.print()` with a special print stylesheet
- OR create a backend endpoint `POST /api/v1/print/ticket` that sends ESC/POS commands to the printer via USB serial
- The ticket should print: clinic logo, ticket number (LARGE), department, doctor, time, date, room number, QR code

Create `backend/app/api/printer.py`:
- Endpoint to print to thermal printer
- Use `python-escpos` or `pyserial` to communicate with the USB thermal printer
- ESC/POS protocol for 80mm paper width
- Print content: ticket number, department, doctor, time, room

---

## PHASE 5: COMPREHENSIVE TESTING

After ALL fixes, run these tests:

### Test 1: Silence test
1. Open kiosk, go to GreetingScreen
2. Don't say anything for 60 seconds
3. ✅ Console shows ZERO `kiosk:speech_audio` emissions
4. ✅ No "eshitmadim" messages appear
5. ✅ Mic stays in WAITING state (green ring, no activity)

### Test 2: Speed test
1. Say "Salom"
2. Check backend logs: `⏱ Pipeline timing`
3. ✅ STT + Gemini + TOTAL < 3000ms
4. ✅ Text appears on screen within 2-3 seconds of speech ending

### Test 3: Voice booking flow
1. Say "Tish shifokoriga yozilmoqchiman"
2. ✅ DepartmentSelectScreen appears with departments (not loading forever)
3. ✅ OR DoctorSelectScreen appears with stomatologiya doctors
4. Voice-select a doctor, time slot, confirm
5. ✅ QueueTicketScreen shows with ticket number (not registration page)
6. ✅ Ticket number is 60-80px, clearly visible

### Test 4: Touch-only booking flow
1. Tap "Boshlash" on IdleScreen
2. Tap through: Intent → Department → Doctor → Time → Confirm
3. ✅ Every screen loads within 1 second
4. ✅ QueueTicketScreen shows at the end
5. ✅ No random resets to GreetingScreen during flow
6. ✅ Back buttons work on every screen

### Test 5: Inactivity timer
1. Start a booking, get to DoctorSelectScreen
2. Don't touch anything for 4 minutes
3. ✅ NO warning popup appears during the first 4 minutes
4. At 4 minutes: ✅ Warning popup appears
5. Tap "Davom etish": ✅ Popup closes, stays on same screen
6. Wait another 2 minutes without touching: ✅ Auto-resets to IDLE

### Test 6: Portrait layout
1. Set browser to 1080×1920 (or use kiosk)
2. Go through every screen
3. ✅ No horizontal scrolling
4. ✅ All text readable
5. ✅ All buttons tappable (minimum 56px height)
6. ✅ AI messages don't overflow
7. ✅ Long doctor names truncate properly

### Test 7: Error recovery
1. Disconnect network (turn off WiFi)
2. ✅ "Offline" indicator appears
3. Try to interact
4. ✅ Error message shown (not crash)
5. Reconnect network
6. ✅ System recovers and works again

### Test 8: Console cleanliness
1. Open browser DevTools → Console
2. Go through a full booking flow
3. ✅ Zero red errors
4. ✅ Zero uncaught exceptions
5. ✅ No infinite loops of any event
6. ✅ No "undefined" or "null" appearing in visible UI text

---

## PHASE 6: FINAL VERIFICATION CHECKLIST

Before declaring "done", verify EVERY item:

- [ ] `npm run build` succeeds with ZERO errors
- [ ] Backend starts with ZERO import errors
- [ ] Socket connection establishes on page load
- [ ] IdleScreen shows and camera activates
- [ ] GreetingScreen → IntentScreen navigation works (touch)
- [ ] Department cards load and are tappable
- [ ] Doctor cards load and are tappable
- [ ] Time slot pills load and are tappable
- [ ] BookingConfirmScreen shows summary correctly
- [ ] QueueTicketScreen shows after confirmation (not registration)
- [ ] FarewellScreen auto-resets after 10s
- [ ] Voice: mic activates, VAD works, sends only real speech
- [ ] Voice: AI response appears on screen
- [ ] Voice: mic auto-restarts after AI response
- [ ] No "eshitmadim" spam when room is quiet
- [ ] Inactivity timer: 4min warning, 6min reset
- [ ] All screens render correctly in 1080×1920 portrait
- [ ] All i18n keys exist in uz.json, ru.json, en.json
- [ ] Back buttons work on every screen
- [ ] Error boundary catches crashes and shows retry button
- [ ] Socket reconnection works
- [ ] No console errors or warnings (except expected React dev ones)
- [ ] kiosk-setup/ directory has all deployment files

---

## IMPORTANT RULES

1. **Do NOT delete files or rewrite from scratch.** Fix the existing code surgically.
2. **Do NOT change the tech stack.** Gemini, Muxlisa, React, FastAPI, Socket.IO — all stay.
3. **Do NOT change the CLAUDE.md** unless adding the "CURRENT STATUS" section at the end.
4. **Test after every change.** Don't make 20 changes then test — fix → test → fix → test.
5. **If a fix requires changing more than 3 files, explain why before doing it.**
6. **Prioritize: Bug A (mic spam) → Bug B (doctors loading) → Bug C (wrong screen) → rest.**
7. **For UI issues, use the exact design system from CLAUDE.md** (colors, spacing, shadows, fonts).
8. **Every screen must work in BOTH voice and touch modes.**
9. **The kiosk-setup/ files should work on Windows 11 out of the box.**
10. **Update the i18n files (uz.json, ru.json, en.json) for any new UI strings you add.**
