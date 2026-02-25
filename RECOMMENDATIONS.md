# RECOMMENDATIONS - Mezbon AI Kiosk System

**Date:** 2026-02-25
**Priority Levels:** P0 (critical), P1 (high), P2 (medium), P3 (low)

---

## P0 - Fix Before Any Demo/Deployment

### 1. Device Authentication Must Verify Against DB
**File:** `backend/app/api/auth.py:49-63`
**Current:** Issues JWT for ANY device_id + clinic_id pair without DB check
**Action:** Query `devices` table to verify device exists and belongs to clinic before issuing JWT

### 2. Payment Gateway Integration
**Files:** `backend/app/integrations/payment/{uzcard,humo,click,payme}.py`
**Current:** All return placeholder errors
**Action:** Implement at least one gateway (Payme or Click recommended for Uzbekistan market)

### 3. Remove Demo Simulation Code
**Files:**
- `kiosk-ui/src/screens/PaymentScreen.tsx` - Remove 20% failure rate
- `kiosk-ui/src/screens/CheckInScreen.tsx` - Connect phone lookup to backend API
- `kiosk-ui/src/screens/BookingConfirmScreen.tsx` - Connect registration to backend API

---

## P1 - Fix Before Production

### 4. Add Socket.IO Rate Limiting
**File:** `backend/app/sockets/kiosk_events.py`
**Risk:** DoS via event flooding
**Action:** Add Redis-backed rate limiter: max 10 face frames/sec, max 2 audio/sec per device

### 5. Session State Locking
**File:** `backend/app/ai/orchestrator.py`
**Risk:** Race condition when speech and touch events arrive simultaneously
**Action:** Use Redis SETNX or Lua scripts for atomic state transitions

### 6. Gemini Chat History Cleanup
**File:** `backend/app/ai/gemini_service.py:72`
**Risk:** Memory leak in `_memory_history` dict
**Action:** Use `cachetools.TTLCache` with 30-minute TTL, or add periodic cleanup task

### 7. Track and Cancel Timeouts in useSession
**File:** `kiosk-ui/src/hooks/useSession.ts`
**Risk:** Orphaned timers modifying store state after unmount
**Action:** Store setTimeout IDs and clear them in cleanup function

### 8. Face Service Shutdown
**File:** `backend/app/ai/face_service.py`
**Risk:** Resource leak on app restart
**Action:** Add `async def close()` method to release InsightFace model, call in lifespan shutdown

---

## P2 - Quality Improvements

### 9. Delete Dead Code
- `kiosk-ui/src/screens/IntentScreen.tsx` - Never rendered (INTENT_DISCOVERY maps to GreetingScreen)
- Remove its import from `ScreenRouter.tsx`

### 10. Extract Shared NumPad Component
- Duplicate NumPad exists in `BookingConfirmScreen.tsx` and `CheckInScreen.tsx`
- Extract to `components/ui/NumPad.tsx`

### 11. Add Error Tracking
- Integrate Sentry SDK for both frontend and backend
- Configure source maps upload for production builds

### 12. Add Health Monitoring
- Implement `/api/v1/health` endpoint with dependency checks (DB, Redis, Gemini API)
- Add device heartbeat monitoring with alerts

### 13. Demo Mode Indicator
- When Gemini fallback to demo data occurs, add flag to response
- Show subtle indicator in UI so admin knows demo data is being shown

---

## P3 - Nice to Have

### 14. TTS Audio Playback
- Currently disabled (text-only responses)
- Implement Muxlisa TTS integration with audio playback via useAudio hook
- Add speaking avatar animation sync with audio

### 15. Offline Fallback
- Add service worker for basic offline page
- Cache static assets for faster load times

### 16. Accessibility Improvements
- Add ARIA labels for all interactive elements in current language
- Ensure focus management between screens
- Test with screen readers

### 17. i18n Completeness
- Audit ru.json and en.json for missing translations
- Add pluralization support where needed

### 18. Performance Monitoring
- Add Core Web Vitals tracking
- Monitor animation performance (FPS drops on lower-end kiosk hardware)
- Add bundle size budget to CI

---

## Architecture Notes

### What's Working Well:
- Zustand store design is clean and well-organized
- Socket.IO event architecture is sound
- Voice pipeline (VAD → WAV → Socket.IO → STT) is well-engineered
- Screen transition animations are smooth
- Mock data fallback system is a good safety net
- Bundle size is excellent (182KB gzipped)

### What Needs Attention:
- Backend session management needs locking for concurrent access
- Payment integration is entirely stubbed
- Device authentication is bypassed in current state
- No error tracking or monitoring in place
- TTS is disabled, making the kiosk text-only
