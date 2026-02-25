# KIOSK UI — CRITICAL FIX PROMPT (Feed to Claude Code)

## CONTEXT
I took photos of the kiosk running. There are MAJOR layout and styling problems.
This document has EXACT code changes needed. Follow every instruction precisely.

---

## PROBLEM LIST (from photos)

1. **GreetingScreen**: ResponseBubble overlaps ON TOP of the AIAvatar (the mini-avatar badge sits right on the orb)
2. **GreetingScreen**: No intent cards visible — huge empty white space below (60%+ of 1920px screen is empty)
3. **IntentScreen**: Cards are too small and flat — don't fill the screen
4. **IntentScreen**: Default Lucide icons look generic — need custom SVG medical icons
5. **IntentScreen**: Avatar too small, weirdly positioned (scale(0.4) makes it tiny)
6. **Both screens**: "resepshn" misspelling in greeting text
7. **Browser chrome still visible** — tabs, address bar, close buttons
8. **Windows taskbar still showing** at bottom
9. **"Qayta ulanmoqda..." reconnecting banner** overlapping header title
10. **ResponseBubble MiniAvatar** badge (-top-3 -left-3) creates visual collision with main avatar

---

## FIX 1: Fix "resepshn" misspelling

**File: `kiosk-ui/src/i18n/uz.json`**

Replace TWO occurrences:

```json
"tagline": "Raqamli Resepshn"
→
"tagline": "Raqamli Qabulxona"
```

```json
"newVisitor": "Nano Medical Clinic ga xush kelibsiz! Men Mezbon — raqamli resepshn."
→
"newVisitor": "Nano Medical Clinic ga xush kelibsiz! Men Mezbon — raqamli qabulxona."
```

---

## FIX 2: MERGE GreetingScreen + IntentScreen into ONE screen

The GreetingScreen currently shows JUST the avatar + greeting + "Sizga qanday yordam bera olaman?" 
with 60% empty space below. The IntentScreen shows the cards but has a tiny avatar.

**SOLUTION**: Combine them. The GreetingScreen should show avatar + greeting + intent cards all in one screen. Remove the separate IntentScreen navigation step — when a visitor is greeted, show the intent cards immediately below.

**File: `kiosk-ui/src/screens/GreetingScreen.tsx`** — FULL REWRITE:

```tsx
import { useCallback, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { ArrowRight, Calendar, Clock } from "lucide-react";
import { AIAvatar } from "../components/ai/AIAvatar";
import { ResponseBubble } from "../components/ai/ResponseBubble";
import { VoiceIndicator } from "../components/ai/VoiceIndicator";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { IconCircle } from "../components/ui/IconCircle";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";

// ── Custom Medical SVG Icons (not default Lucide) ───────────

function CalendarPlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="3" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <line x1="12" y1="14" x2="12" y2="18" />
      <line x1="10" y1="16" x2="14" y2="16" />
    </svg>
  );
}

function ClipboardCheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="m9 14 2 2 4-4" />
    </svg>
  );
}

function InfoBookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <circle cx="12" cy="10" r="1" fill="currentColor" stroke="none" />
      <line x1="12" y1="13" x2="12" y2="16" />
    </svg>
  );
}

function WalletIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5z" />
      <path d="M16 12h5v4h-5a2 2 0 0 1 0-4z" />
      <circle cx="18" cy="14" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ChatBubbleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <circle cx="9" cy="10" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="12" cy="10" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="15" cy="10" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

// ── Intent definitions with custom icons ────────────────────

interface IntentAction {
  id: string;
  labelKey: string;
  subtitleKey: string;
  icon: React.ReactNode;
  bgColor: string;
  iconColor: string;
}

const INTENTS: IntentAction[] = [
  {
    id: "book",
    labelKey: "intent.bookAppointment",
    subtitleKey: "intent.bookAppointmentDesc",
    icon: <CalendarPlusIcon className="h-7 w-7" />,
    bgColor: "bg-primary-50",
    iconColor: "text-primary",
  },
  {
    id: "checkin",
    labelKey: "intent.checkIn",
    subtitleKey: "intent.checkInDesc",
    icon: <ClipboardCheckIcon className="h-7 w-7" />,
    bgColor: "bg-emerald-50",
    iconColor: "text-emerald-600",
  },
  {
    id: "info",
    labelKey: "intent.information",
    subtitleKey: "intent.informationDesc",
    icon: <InfoBookIcon className="h-7 w-7" />,
    bgColor: "bg-blue-50",
    iconColor: "text-blue-600",
  },
  {
    id: "payment",
    labelKey: "intent.payment",
    subtitleKey: "intent.paymentDesc",
    icon: <WalletIcon className="h-7 w-7" />,
    bgColor: "bg-amber-50",
    iconColor: "text-amber-600",
  },
  {
    id: "other",
    labelKey: "intent.faq",
    subtitleKey: "intent.faqDesc",
    icon: <ChatBubbleIcon className="h-7 w-7" />,
    bgColor: "bg-violet-50",
    iconColor: "text-violet-600",
  },
];

// ── Intent Card (premium, fills space) ──────────────────────

function IntentCard({
  intent,
  index,
  selected,
  onSelect,
}: {
  intent: IntentAction;
  index: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();

  return (
    <motion.button
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 + index * 0.07, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileTap={{ scale: 0.97 }}
      onClick={onSelect}
      className={cn(
        "group relative flex flex-col items-center justify-center gap-4 rounded-card bg-white p-6 text-center",
        "shadow-card transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5",
        "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/40 focus-visible:ring-offset-4",
        "min-h-[160px]",
        selected && "ring-2 ring-primary bg-primary-50 shadow-card-hover",
      )}
    >
      {/* Selected left accent */}
      <motion.div
        className="absolute left-0 top-4 bottom-4 w-1 rounded-full bg-primary"
        initial={{ scaleY: 0 }}
        animate={{ scaleY: selected ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        style={{ originY: 0.5 }}
      />

      {/* Icon circle */}
      <div className={cn(
        "flex h-16 w-16 items-center justify-center rounded-2xl transition-transform duration-200 group-hover:scale-110",
        intent.bgColor, intent.iconColor,
      )}>
        {intent.icon}
      </div>

      {/* Text */}
      <div>
        <p className="text-[19px] font-semibold leading-tight tracking-heading text-text-primary">
          {t(intent.labelKey)}
        </p>
        <p className="mt-1.5 text-[14px] leading-snug text-text-muted">
          {t(intent.subtitleKey)}
        </p>
      </div>
    </motion.button>
  );
}

// ── Today's appointment card (known patients) ───────────────

function TodayAppointmentCard({
  doctorName, department, time, onCheckIn,
}: {
  doctorName: string; department: string; time: string; onCheckIn: () => void;
}) {
  const { t } = useTranslation();
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.4 }}
      className="w-full rounded-card bg-white p-6 shadow-card"
    >
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-50">
          <Calendar className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-h3 tracking-heading text-text-primary">{doctorName}</p>
          <p className="text-caption text-text-muted">{department}</p>
        </div>
      </div>
      <div className="mb-5 flex items-center gap-2 text-body text-text-body">
        <Clock className="h-4 w-4 text-text-muted" />
        <span>{t("days.today")} — {time}</span>
      </div>
      <Button variant="primary" size="lg" className="w-full" onClick={onCheckIn}
        iconRight={<ArrowRight className="h-5 w-5" />}>
        {t("checkIn.confirmCheckIn")}
      </Button>
    </motion.div>
  );
}

// ── Floating orbs ───────────────────────────────────────────

function BrightOrbs() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <motion.div className="absolute rounded-full" style={{ width: 220, height: 220, left: "5%", top: "20%", background: "rgba(30, 42, 110, 0.10)", filter: "blur(100px)" }}
        animate={{ x: [0, 20, -10, 0], y: [0, -15, 10, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div className="absolute rounded-full" style={{ width: 260, height: 260, right: "5%", top: "50%", background: "rgba(30, 42, 110, 0.12)", filter: "blur(100px)" }}
        animate={{ x: [0, -25, 15, 0], y: [0, 10, -20, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }} />
    </div>
  );
}

// ── MAIN SCREEN ─────────────────────────────────────────────

interface GreetingScreenProps {
  onContinue: () => void;
  onCheckIn: () => void;
  onSelectIntent?: (intentId: string) => void;
}

export function GreetingScreen({ onContinue, onCheckIn, onSelectIntent }: GreetingScreenProps) {
  const { t } = useTranslation();
  const patient = useSessionStore((s) => s.patient);
  const aiMessage = useSessionStore((s) => s.aiMessage);
  const userTranscript = useSessionStore((s) => s.userTranscript);
  const currentAppointment = useSessionStore((s) => s.currentAppointment);
  const [selectedIntent, setSelectedIntent] = useState<string | null>(null);

  const isKnown = patient !== null;
  const voice = useVoiceChat({ autoStartDelay: 1500 });

  const greetingText = useMemo(() => {
    if (aiMessage) return aiMessage;
    if (isKnown) return t("greeting.knownPatient", { name: patient.full_name });
    return t("greeting.newVisitor");
  }, [aiMessage, isKnown, patient, t]);

  const handleIntent = useCallback((id: string) => {
    sounds.tap();
    setSelectedIntent(id);
    // If parent provides onSelectIntent, use it; otherwise fall through to onContinue
    if (onSelectIntent) {
      setTimeout(() => onSelectIntent(id), 200);
    } else {
      setTimeout(() => onContinue(), 200);
    }
  }, [onSelectIntent, onContinue]);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <HeaderBar title={t("intent.title")} />
      <BrightOrbs />

      {/* Scrollable content area — fills the screen between header and bottom nav */}
      <div className="flex flex-1 flex-col overflow-y-auto scrollbar-hide">

        {/* ── AI Section: Avatar + Greeting + Voice ── */}
        <div className="flex flex-col items-center px-8 pt-8 pb-4">
          {/* Avatar — moderate size, NOT too big, NOT tiny */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 18, delay: 0.1 }}
            className="mb-4"
          >
            <div style={{ width: 120, height: 120 }}>
              <AIAvatar state={voice.avatarState} />
            </div>
          </motion.div>

          {/* User transcript */}
          {userTranscript && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className="mb-3 w-full max-w-lg">
              <div className="ml-auto w-fit max-w-[75%] rounded-2xl rounded-br-md bg-slate-100 px-5 py-3">
                <p className="text-[16px] text-text-muted">{userTranscript}</p>
              </div>
            </motion.div>
          )}

          {/* Greeting bubble — NO MiniAvatar badge, clean layout */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
            className="w-full max-w-lg">
            <ResponseBubble message={greetingText} messageKey={greetingText} animate
              className="[&_.mini-avatar-badge]:hidden" />
          </motion.div>

          {/* Voice indicator */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }} className="mt-4">
            <VoiceIndicator state={voice.voiceState} onClick={voice.toggleMic} />
          </motion.div>
        </div>

        {/* ── Known patient: Today's appointment ── */}
        {isKnown && currentAppointment && (
          <div className="px-8 pb-4">
            <TodayAppointmentCard
              doctorName={currentAppointment.doctor_name}
              department={currentAppointment.service_name}
              time={new Date(currentAppointment.scheduled_at).toLocaleTimeString("uz-UZ", {
                hour: "2-digit", minute: "2-digit", hour12: false,
              })}
              onCheckIn={onCheckIn}
            />
          </div>
        )}

        {/* ── Intent Title ── */}
        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="px-8 pb-4 text-center text-h2 tracking-heading text-text-body"
        >
          {t("intent.title")}
        </motion.h2>

        {/* ── Intent Cards Grid — fills remaining space ── */}
        <div className="flex-1 px-8 pb-6">
          <div className="grid grid-cols-2 gap-4">
            {INTENTS.slice(0, 4).map((intent, i) => (
              <IntentCard key={intent.id} intent={intent} index={i}
                selected={selectedIntent === intent.id}
                onSelect={() => handleIntent(intent.id)} />
            ))}
          </div>
          {/* 5th card — full width below */}
          <div className="mt-4">
            <IntentCard intent={INTENTS[4]} index={4}
              selected={selectedIntent === INTENTS[4].id}
              onSelect={() => handleIntent(INTENTS[4].id)} />
          </div>
        </div>
      </div>

      {/* Bottom nav */}
      <BottomNav onBack={() => { /* go to idle */ }} />
    </motion.div>
  );
}
```

---

## FIX 3: ResponseBubble — Remove MiniAvatar badge

The MiniAvatar badge (small circle at -top-3 -left-3) collides with the main AIAvatar above it.

**File: `kiosk-ui/src/components/ai/ResponseBubble.tsx`**

Find and REMOVE the entire MiniAvatar function and its usage:

```tsx
// DELETE THIS ENTIRE FUNCTION:
function MiniAvatar() { ... }

// In the JSX, DELETE this line:
<div className="absolute -top-3 -left-3">
  <MiniAvatar />
</div>

// Also change the message padding from "pl-3 pt-1" to just "pt-1" since there's no mini avatar anymore
```

The bubble should be a clean white card with text — no overlapping badge.

---

## FIX 4: AIAvatar — Accept `size` prop and render at correct size

Currently the screens use CSS `transform: scale(0.4)` to shrink the avatar — this creates blurry results and wrong layout dimensions (the avatar still takes 200px of space but looks tiny).

**File: `kiosk-ui/src/components/ai/AIAvatar.tsx`**

Add a `size` prop to the component:

```tsx
interface AIAvatarProps {
  state?: AvatarState;
  audioData?: Float32Array | null;
  size?: number;  // ADD THIS — pixel size, default 200
  className?: string;
}
```

At the top of the component, use the size prop:

```tsx
export function AIAvatar({ state = "idle", audioData = null, size, className }: AIAvatarProps) {
  const actualSize = size ?? OUTER_SIZE; // OUTER_SIZE = 200
  const scale = actualSize / OUTER_SIZE;
  
  // Wrap the entire render in a div that scales
  return (
    <div 
      className={cn("relative flex items-center justify-center", className)}
      style={{ width: actualSize, height: actualSize }}
    >
      <div style={{ transform: `scale(${scale})`, transformOrigin: "center center", width: OUTER_SIZE, height: OUTER_SIZE }}>
        {/* ... existing avatar render code ... */}
      </div>
    </div>
  );
}
```

This way, screens can do `<AIAvatar state={voice.avatarState} size={120} />` instead of using CSS scale hacks.

---

## FIX 5: IntentScreen — Either DELETE or redirect to GreetingScreen

Since we merged intents into GreetingScreen, the IntentScreen should either:
- Option A: Delete `IntentScreen.tsx` and update the router to go from Greeting → Departments directly
- Option B: Keep IntentScreen but have the ScreenRouter skip it and go from GREETING → DEPARTMENT_SELECT

Check `kiosk-ui/src/router/ScreenRouter.tsx` and make sure the flow is:
`IDLE → GREETING (with intents) → DEPARTMENT_SELECT → DOCTOR_SELECT → TIME_SLOT → BOOKING_CONFIRM → QUEUE_TICKET → FAREWELL`

The GreetingScreen's `onSelectIntent` callback should trigger the appropriate navigation (e.g., "book" → go to DEPARTMENT_SELECT).

---

## FIX 6: Kiosk Mode — Chrome Fullscreen

**File: `kiosk-ui/index.html`** — Add this script to auto-enter fullscreen on first interaction:

```html
<script>
  // Auto-enter fullscreen kiosk mode on first touch
  document.addEventListener('click', function enterFullscreen() {
    document.removeEventListener('click', enterFullscreen);
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else if (document.documentElement.webkitRequestFullscreen) {
      document.documentElement.webkitRequestFullscreen();
    }
  }, { once: true });
</script>
```

Also create or update `kiosk-ui/public/start-kiosk.bat` (Windows startup script):

```bat
@echo off
REM Hide Windows taskbar
powershell -command "&{$t=[Runtime.InteropServices.Marshal]::GetFunctionPointerForDelegate((New-Object Action{param()}).Method);$s=Add-Type -MemberDefinition '[DllImport(\"user32.dll\")] public static extern int FindWindow(string a,string b); [DllImport(\"user32.dll\")] public static extern int ShowWindow(int a,int b);' -Name W -PassThru;$h=$s::FindWindow('Shell_TrayWnd','');$s::ShowWindow($h,0)}"

REM Launch Chrome in kiosk mode
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --kiosk ^
  --start-fullscreen ^
  --disable-session-crashed-bubble ^
  --noerrdialogs ^
  --disable-infobars ^
  --disable-translate ^
  --no-first-run ^
  --fast ^
  --fast-start ^
  --disable-features=TranslateUI ^
  --overscroll-history-navigation=0 ^
  http://10.99.0.133:5173
```

---

## FIX 7: Hide the "Qayta ulanmoqda..." reconnecting banner

This ugly banner overlaps the HeaderBar title. Find the component that shows this reconnecting status (likely in a DegradationBanner or a socket status component) and either:
- Move it to a subtle toast at the bottom of the screen
- Or make it a small dot indicator in the HeaderBar instead of a full banner

Search for "Qayta ulanmoqda" or "reconnecting" in the codebase and find where it renders. It should NOT overlap the header title.

**File: `kiosk-ui/src/components/ui/DegradationBanner.tsx`** — Modify to show as a subtle indicator, not a full-width banner:

```tsx
// Instead of a banner that overlaps content, render as a small pill in the top-right:
<div className="fixed top-2 right-2 z-50 flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-xs text-amber-700 shadow-sm">
  <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
  {t("connection.reconnecting")}
</div>
```

---

## FIX 8: globals.css — Hide cursor on kiosk

**File: `kiosk-ui/src/styles/globals.css`** — Add to the base layer:

```css
/* Kiosk mode: hide cursor */
html.kiosk-mode,
html.kiosk-mode * {
  cursor: none !important;
}
```

---

## FIX 9: DepartmentSelectScreen — Cards should fill vertical space

The cards use `gap-5` and `px-12` which leaves too much empty space. 

**File: `kiosk-ui/src/screens/DepartmentSelectScreen.tsx`**

Change the AI prompt area from `px-12` to `px-8`:
```tsx
<div className="flex items-start gap-4 px-8 pb-4">
```

Change the cards grid from `px-12 gap-5` to `px-8 gap-4`:
```tsx
<div className="flex-1 overflow-y-auto px-8 pb-6 scrollbar-hide">
  ...
  <div className="grid grid-cols-2 gap-4">
```

Also, the AIAvatar in DepartmentSelectScreen uses `style={{ transform: "scale(0.3)" }}` — change to use the new size prop:
```tsx
<AIAvatar state={voice.avatarState} size={56} />
```

And remove the wrapping div with `transform: "scale(0.3)"` and `width: 60, height: 60`.

---

## FIX 10: IntentScreen AIAvatar same fix

**File: `kiosk-ui/src/screens/IntentScreen.tsx`**

Same as Fix 9 — replace the scale hack:
```tsx
// REMOVE this:
style={{ transform: "scale(0.4)", transformOrigin: "top left", width: 80, height: 80 }}

// REPLACE with:
<AIAvatar state={voice.avatarState} size={72} />
```

---

## VERIFICATION CHECKLIST

After all changes:

1. [ ] `npm run build` succeeds with no errors
2. [ ] GreetingScreen shows: HeaderBar → Avatar (120px) → Greeting bubble → Voice indicator → Intent title → 5 intent cards → BottomNav
3. [ ] NO empty space below intent cards (cards + bottom nav fill the screen)
4. [ ] NO MiniAvatar badge overlapping the main avatar
5. [ ] "resepshn" replaced with "qabulxona" everywhere
6. [ ] Intent cards have custom SVG icons, NOT default Lucide icons
7. [ ] Intent cards are 160px+ tall with centered vertical layout
8. [ ] "Qayta ulanmoqda..." shows as subtle pill, NOT overlapping header
9. [ ] Chrome kiosk mode script exists at `public/start-kiosk.bat`
10. [ ] Fullscreen auto-trigger on first touch in index.html
11. [ ] AIAvatar accepts `size` prop — no more CSS scale() hacks
12. [ ] DepartmentSelectScreen uses px-8 padding, gap-4 cards
13. [ ] Test in 1080×1920 viewport: ALL screens fill vertical space

---

## PRIORITY ORDER

1. Fix "resepshn" typo (30 seconds)
2. ResponseBubble — remove MiniAvatar (2 minutes)
3. AIAvatar — add size prop (5 minutes)
4. Merge Greeting + Intent into one screen (15 minutes)
5. Update ScreenRouter navigation flow (5 minutes)
6. Fix DepartmentSelectScreen spacing (3 minutes)
7. Fix reconnecting banner (3 minutes)
8. Add kiosk mode scripts (2 minutes)
9. Test everything (5 minutes)


---

## FIX 11: ScreenRouter — Pass onSelectIntent to GreetingScreen

**File: `kiosk-ui/src/router/ScreenRouter.tsx`**

In the GreetingScreen render section, add `onSelectIntent`:

```tsx
{screenKey === "greeting" && (
  <GreetingScreen
    onContinue={handlers.handleContinueToIntent}
    onCheckIn={handlers.handleCheckIn}
    onSelectIntent={handlers.handleSelectIntent}
  />
)}
```

Also, map INTENT_DISCOVERY state to show GreetingScreen instead of IntentScreen:

In the `getScreenKey` function, change:
```tsx
case "INTENT_DISCOVERY":
  return "greeting";  // was "intent" — now shows GreetingScreen with embedded intents
```

And in the ScreenRouter render, either DELETE the IntentScreen render block or keep it as dead code. The intent selection is now handled directly by GreetingScreen.

This means when a user taps "Qabulga yozilish" on the GreetingScreen, it calls handleSelectIntent("book") which:
1. Emits socket event
2. Sets departments from mock data
3. Sets state to SELECT_DEPARTMENT
4. ScreenRouter renders DepartmentSelectScreen

No separate intent screen needed.

---

## FIX 12: useScreenHandlers — handleBackToIntent should go to GREETING

Since INTENT_DISCOVERY now renders as GreetingScreen, the "back to intent" handler should go to GREETING:

**File: `kiosk-ui/src/router/useScreenHandlers.ts`**

```tsx
const handleBackToIntent = useCallback(() => {
  setState("GREETING");  // was "INTENT_DISCOVERY"
  setCurrentDepartment(null);
  setDoctors([]);
  setServices([]);
}, [setState, setCurrentDepartment, setDoctors, setServices]);
```

Also update these handlers that reference INTENT_DISCOVERY:
- `handleCancelBooking` → change to `setState("GREETING")`
- `handleBackFromCheckIn` → change to `setState("GREETING")`
- `handlePaymentBack` → change to `setState("GREETING")`
- `handleInfoBack` → change to `setState("GREETING")`
- `handleHandOffCancel` → change to `setState("GREETING")`

---

## SUMMARY OF ALL FILES TO MODIFY

1. `kiosk-ui/src/i18n/uz.json` — Fix "resepshn" → "qabulxona" (2 places)
2. `kiosk-ui/src/components/ai/ResponseBubble.tsx` — Remove MiniAvatar badge
3. `kiosk-ui/src/components/ai/AIAvatar.tsx` — Add `size` prop
4. `kiosk-ui/src/screens/GreetingScreen.tsx` — FULL REWRITE with embedded intents
5. `kiosk-ui/src/router/ScreenRouter.tsx` — Map INTENT_DISCOVERY → greeting, pass onSelectIntent
6. `kiosk-ui/src/router/useScreenHandlers.ts` — Update back handlers to GREETING
7. `kiosk-ui/src/screens/DepartmentSelectScreen.tsx` — Fix avatar size, reduce padding
8. `kiosk-ui/src/screens/IntentScreen.tsx` — Fix avatar size (or can be left since it won't render)
9. `kiosk-ui/src/components/ui/DegradationBanner.tsx` — Subtle pill instead of overlapping banner
10. `kiosk-ui/src/styles/globals.css` — Add kiosk cursor hide
11. `kiosk-ui/index.html` — Add fullscreen auto-trigger
12. `kiosk-ui/public/start-kiosk.bat` — Create Windows kiosk launcher


---

## FIX 13: ConnectionStatus in App.tsx — Move below HeaderBar

**File: `kiosk-ui/src/App.tsx`**

The ConnectionStatus renders at `fixed left-1/2 top-3` which overlaps the 80px HeaderBar.

Change the positioning to sit BELOW the header:

```tsx
function ConnectionStatus() {
  const isConnected = useSessionStore((s) => s.isConnected);
  if (isConnected) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="fixed left-1/2 top-[88px] z-50 -translate-x-1/2"
    >
      <div className="flex items-center gap-2 rounded-full bg-amber-50/90 backdrop-blur-sm px-4 py-1.5 text-[13px] font-medium text-amber-700 shadow-sm border border-amber-200/50">
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        <span>Qayta ulanmoqda...</span>
      </div>
    </motion.div>
  );
}
```

Key changes:
- `top-3` → `top-[88px]` (below 80px header + 8px gap)
- Added `backdrop-blur-sm` and `border` for polish
- Smaller text `text-[13px]` so it's subtle
- Pulsing dot instead of WifiOff icon

---

## FIX 14: IdleScreen — Remove default emoji 👋

**File: `kiosk-ui/src/screens/IdleScreen.tsx`**

Replace the 👋 emoji with a subtle animated hand SVG or just remove it entirely and use a pulsing arrow/chevron:

```tsx
// REPLACE this block:
<div className="text-3xl" style={{ animation: "bounce-gentle 2s ease-in-out infinite" }}>
  👋
</div>

// WITH this SVG animation:
<motion.svg
  width="40" height="40" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
  className="text-primary/60"
  animate={{ y: [0, 6, 0] }}
  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
>
  <path d="M12 5v14M5 12l7 7 7-7" />
</motion.svg>
```

This replaces the default system emoji with a clean animated down-arrow in the brand color.

---

## COMPLETE FILES LIST (Final)

| # | File | Change |
|---|------|--------|
| 1 | `src/i18n/uz.json` | "resepshn" → "qabulxona" (2 places) |
| 2 | `src/components/ai/ResponseBubble.tsx` | Remove MiniAvatar badge |
| 3 | `src/components/ai/AIAvatar.tsx` | Add `size` prop |
| 4 | `src/screens/GreetingScreen.tsx` | FULL REWRITE — merge intents in |
| 5 | `src/router/ScreenRouter.tsx` | INTENT_DISCOVERY → greeting, pass onSelectIntent |
| 6 | `src/router/useScreenHandlers.ts` | Back handlers → GREETING not INTENT_DISCOVERY |
| 7 | `src/screens/DepartmentSelectScreen.tsx` | Fix avatar size, reduce padding |
| 8 | `src/App.tsx` | ConnectionStatus → top-[88px], smaller, subtle |
| 9 | `src/screens/IdleScreen.tsx` | Replace 👋 emoji with SVG arrow |
| 10 | `src/styles/globals.css` | Add kiosk cursor hide class |
| 11 | `index.html` | Fullscreen auto-trigger (already in App.tsx, verify) |
| 12 | `public/start-kiosk.bat` | Create Windows kiosk launcher |

Total: 12 files, ~45 minutes of work for Claude Code.
