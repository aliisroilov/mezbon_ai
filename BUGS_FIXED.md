# BUGS FIXED - Mezbon AI Kiosk System

**Date:** 2026-02-25
**Scope:** Full-stack analysis and bug fixes

---

## CRITICAL FIXES

### 1. GreetingScreen Back Button Non-Functional
**File:** `kiosk-ui/src/screens/GreetingScreen.tsx:340`
**Bug:** BottomNav `onBack` handler was empty (`() => { /* go to idle */ }`)
**Fix:** Changed to `resetSession()` which properly clears all state and returns to IDLE
**Impact:** Users could not go back from the greeting screen

### 2. BookingConfirmScreen Double-Submit Race Condition
**File:** `kiosk-ui/src/screens/BookingConfirmScreen.tsx:267-279`
**Bug:** Rapid double-tap on confirm button could trigger two bookings because React state updates are async
**Fix:** Added `confirmingRef` ref guard that immediately blocks duplicate calls before React state updates
**Impact:** Prevented duplicate appointment bookings

### 3. useMicrophone Race Condition on Rapid Start
**File:** `kiosk-ui/src/hooks/useMicrophone.ts:143-144`
**Bug:** `startRecording()` called twice rapidly could create duplicate AudioContext and MediaStream instances, causing memory leaks
**Fix:** Added `startingRef` lock that prevents concurrent `startRecording()` calls during the async getUserMedia phase
**Impact:** Prevented audio subsystem crashes and memory leaks

### 4. Navigation State Leak - Back to Departments
**File:** `kiosk-ui/src/router/useScreenHandlers.ts:157-161`
**Bug:** `handleBackToDepartments` didn't clear `doctors[]`, `services[]`, or `currentService`, leaving stale data when selecting a different department
**Fix:** Added cleanup of `setDoctors([])`, `setServices([])`, `setCurrentService(null)`
**Impact:** Prevented showing doctors from previously selected department

### 5. Navigation State Leak - Back to Doctors
**File:** `kiosk-ui/src/router/useScreenHandlers.ts:179-183`
**Bug:** `handleBackToDoctors` didn't clear `availableSlots[]`, leaving stale time slots visible briefly
**Fix:** Added `setAvailableSlots([])`
**Impact:** Prevented showing time slots from previously selected doctor

### 6. Booking Fallback Timer Not Cancellable
**File:** `kiosk-ui/src/router/useScreenHandlers.ts:187-206`
**Bug:** 5-second fallback timeout in `handleConfirmBooking` was never stored or cancelled. If backend responded at 3s, the timer still fired at 5s, potentially overriding backend data
**Fix:** Stored timer in `bookingFallbackRef` with proper cleanup, clearing previous timer before setting new one
**Impact:** Prevented mock data overriding real backend booking data

---

## SECURITY FIXES

### 7. Console Logs Leaking to Production
**Files:** `socket.ts`, `useAudio.ts`, `useMicrophone.ts`, `useSession.ts`, `printer.ts`
**Bug:** 13 `console.log/warn/error` statements would output debug info in production builds
**Fix:** Wrapped all console statements with `if (import.meta.env.DEV)` guard
**Impact:** Prevented information leakage in production

### 8. Backend Socket.IO Missing Input Size Validation
**File:** `backend/app/sockets/kiosk_events.py`
**Bug:** No size limits on `kiosk:face_frame` and `kiosk:speech_audio` payloads - malicious client could send gigabytes of base64 data causing memory exhaustion
**Fix:** Added 5MB limit for face frames, 10MB limit for speech audio with proper error responses
**Impact:** Prevented denial-of-service via oversized payloads

### 9. Backend Session Dictionary Access Without Validation
**File:** `backend/app/ai/orchestrator.py:155,303`
**Bug:** `session["clinic_id"]` accessed without checking key existence - corrupted Redis session data would cause `KeyError` crash
**Fix:** Changed to `session.get("clinic_id")` with early return on missing data
**Impact:** Prevented crash on corrupted session data

---

## UI/UX FIXES

### 10. Missing Medical Icon Mappings
**File:** `kiosk-ui/src/components/icons/MedicalIcons.tsx:142`
**Bug:** Mock departments "Mammologiya", "Reanimatsiya", "Radiologiya" had no icon mapping, falling back to generic hospital icon
**Fix:** Added specific icon mappings: HeartPulseIcon for mammology, HospitalIcon for reanimation, EyeIcon for radiology
**Impact:** Proper visual differentiation for all 8 departments

---

## KNOWN ISSUES (Not Fixed - Documented)

### Backend Issues Requiring Larger Changes:
1. **Redis connection lifecycle** - `aclose()` calls on pooled connections need architectural review
2. **Session state race conditions** - Need Redis SETNX/Lua script locking for atomic transitions
3. **Device auth not verified against DB** - `/auth/device` endpoint issues JWT for any device (dev/demo mode)
4. **Payment gateways are stubs** - All 4 payment integrations (Uzcard, Humo, Click, Payme) return placeholder errors
5. **Gemini fallback to demo data** - No UI indication when real DB functions fail and demo data is used
6. **Face service lacks shutdown cleanup** - InsightFace model resources not released on shutdown
7. **Gemini in-memory history leak** - `_memory_history` dict grows unbounded when Redis is unavailable

### Frontend Issues Requiring Discussion:
1. **IntentScreen.tsx is dead code** - Imported in ScreenRouter but never rendered (INTENT_DISCOVERY maps to "greeting")
2. **CheckInScreen phone lookup always returns "not found"** - Simulation only, needs backend integration
3. **PaymentScreen has hardcoded 20% failure rate** - Demo simulation
4. **useSession timeouts not tracked** - `setTimeout` calls in AI response handler are not stored for cleanup on unmount
