# KIOSK UI — COMPREHENSIVE FIX PROMPT V2
# Feed this ENTIRE file to Claude Code

## CRITICAL CONTEXT

I took photos of the kiosk running. The SAME bugs appear on EVERY screen.
This prompt fixes ALL of them at once with a systematic approach.

---

## PHOTO ANALYSIS — RECURRING BUGS ON EVERY SCREEN

### BUG 1: Avatar OVERLAPS ResponseBubble (WORST BUG — appears on ALL screens)
Every inner screen uses this broken pattern:
```tsx
<motion.div style={{ transform: "scale(0.3)", transformOrigin: "top left", width: 60, height: 60 }}>
  <AIAvatar state={voice.avatarState} />
</motion.div>
```
The CSS `scale(0.3)` does NOT actually shrink the DOM element — the avatar
is still 200px in layout, causing it to render as a HUGE blue orb that
overlaps/hides behind the ResponseBubble text. The `width: 60` wrapper
doesn't clip because there's no `overflow: hidden`.

**Affected files (ALL have this exact broken pattern):**
- `src/screens/DepartmentSelectScreen.tsx` (line ~199)
- `src/screens/DoctorSelectScreen.tsx` (line ~205)
- `src/screens/TimeSlotScreen.tsx` (line ~287)
- `src/screens/BookingConfirmScreen.tsx` (line ~333)
- `src/screens/CheckInScreen.tsx` (line ~298)
- `src/screens/InfoScreen.tsx` (line ~348)
- `src/screens/IntentScreen.tsx` (uses scale(0.4))

### BUG 2: Logo NOT visible — file doesn't exist
`HeaderBar.tsx` references `/nano-medical-logo.png` but the file
does NOT exist in `kiosk-ui/public/`. The `public/` folder only
has `start-kiosk.bat`. The logo silently fails with `onError` handler.

### BUG 3: "Qayta ulanmoqda..." overlapping header
In `src/App.tsx`, `ConnectionStatus` component is positioned at
`fixed left-1/2 top-[88px] z-50` — this sits right ON the screen
title/avatar area, overlapping content on every screen.

### BUG 4: ResponseBubble has MiniAvatar badge
The `MiniAvatar` circle at `absolute -top-3 -left-3` collides with
the main AIAvatar orb, creating visual mess.

### BUG 5: ResponseBubble text gets TRUNCATED
`max-w-[80%]` clips long text like "Endokrinologiya bo'limi shifok..."
The text is cut off on the right edge.

### BUG 6: Default emoji icons in DepartmentSelectScreen
Still using 🫀 🦷 🧒 🧠 🩺 etc. These look unprofessional on the
32" kiosk screen. Need custom SVG icons.

### BUG 7: "resepshn" typo
`src/i18n/uz.json` has "Raqamli Resepshn" and "raqamli resepshn"

### BUG 8: Massive empty space on most screens
Cards don't fill the 1920px vertical space. Content sits in top 40%.

---

## SOLUTION ARCHITECTURE

### STEP 1: Create a reusable `AIPromptBar` component

Instead of fixing the broken avatar pattern in 7 files individually,
create ONE shared component that ALL screens will use.

**Create file: `src/components/ai/AIPromptBar.tsx`**

This component replaces the broken avatar+bubble+voice pattern used on every screen.
It renders a compact horizontal bar with: small avatar (48px) | response text | voice indicator.

```tsx
import { motion } from "framer-motion";
import { AIAvatar, type AvatarState } from "./AIAvatar";
import { VoiceIndicator, type VoiceState } from "./VoiceIndicator";
import { cn } from "../../lib/cn";

interface AIPromptBarProps {
  /** The AI message text to display */
  message: string;
  /** Avatar animation state */
  avatarState?: AvatarState;
  /** Voice indicator state */
  voiceState?: VoiceState;
  /** Voice toggle callback */
  onVoiceClick?: () => void;
  className?: string;
}

/**
 * Compact AI prompt bar for inner screens.
 * Shows: [Avatar 48px] [Message text] [Voice indicator]
 * 
 * IMPORTANT: This replaces the broken pattern of scale(0.3) AIAvatar
 * + separate ResponseBubble + separate VoiceIndicator that caused
 * overlap issues on every screen.
 */
export function AIPromptBar({
  message,
  avatarState = "idle",
  voiceState = "inactive",
  onVoiceClick,
  className,
}: AIPromptBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className={cn(
        "flex items-center gap-4 rounded-2xl bg-white/80 backdrop-blur-sm",
        "border border-border/50 px-5 py-3.5 shadow-card",
        className,
      )}
    >
      {/* Small avatar — uses overflow:hidden to properly clip */}
      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full">
        <div
          style={{
            transform: "scale(0.24)",
            transformOrigin: "top left",
            width: 200,
            height: 200,
            position: "absolute",
            top: 0,
            left: 0,
          }}
        >
          <AIAvatar state={avatarState} />
        </div>
      </div>

      {/* Message text — takes remaining space, NO truncation */}
      <p className="min-w-0 flex-1 text-[17px] leading-snug text-text-primary">
        {message}
      </p>

      {/* Voice indicator — compact */}
      <div className="shrink-0">
        <VoiceIndicator state={voiceState} onClick={onVoiceClick} />
      </div>
    </motion.div>
  );
}
```

KEY DIFFERENCES from broken pattern:
- `overflow: hidden` on avatar wrapper — avatar is ACTUALLY clipped to 48px
- `position: absolute` inside overflow wrapper — no layout bleed
- Message text uses `min-w-0 flex-1` — takes all space, never truncated
- Voice indicator inline — no separate line
- Single component replaces 3 separate components (Avatar + ResponseBubble + VoiceIndicator)

---

### STEP 2: Replace broken pattern in ALL 7 screens

In each of these files, find the AI prompt section (the `<div>` containing
AIAvatar + ResponseBubble + VoiceIndicator) and replace it with `<AIPromptBar>`.

**For each file below, find and replace the entire AI prompt section:**

#### File: `src/screens/DepartmentSelectScreen.tsx`

FIND this entire block (approximately lines 195-215):
```tsx
{/* ── AI prompt area ── */}
<div className="flex items-start gap-4 px-12 pb-6">
  <motion.div
    initial={{ scale: 0.7, opacity: 0 }}
    animate={{ scale: 1, opacity: 1 }}
    transition={{ delay: 0.1, duration: 0.3 }}
    className="shrink-0"
    style={{ transform: "scale(0.3)", transformOrigin: "top left", width: 60, height: 60 }}
  >
    <AIAvatar state={voice.avatarState} />
  </motion.div>

  <div className="flex min-w-0 flex-1 flex-col gap-3">
    <ResponseBubble
      message={responseText}
      messageKey={responseText}
      animate={false}
      className="max-w-full [&>div]:max-w-full"
    />
    <VoiceIndicator state={voice.voiceState} onClick={voice.toggleMic} />
  </div>
</div>
```

REPLACE WITH:
```tsx
{/* ── AI prompt bar ── */}
<div className="px-8 pb-4">
  <AIPromptBar
    message={responseText}
    avatarState={voice.avatarState}
    voiceState={voice.voiceState}
    onVoiceClick={voice.toggleMic}
  />
</div>
```

Also update imports: add `import { AIPromptBar } from "../components/ai/AIPromptBar";`
Remove unused imports: `AIAvatar`, `ResponseBubble`, `VoiceIndicator` (if not used elsewhere in file)

#### REPEAT for these files (same find/replace pattern):
- `src/screens/DoctorSelectScreen.tsx`
- `src/screens/TimeSlotScreen.tsx`
- `src/screens/BookingConfirmScreen.tsx`
- `src/screens/InfoScreen.tsx`
- `src/screens/IntentScreen.tsx`

#### File: `src/screens/CheckInScreen.tsx` (slightly different structure)

The AI prompt section is inside a `<div className="mb-6 flex items-start gap-4">`.
Replace that entire div with:
```tsx
<div className="mb-6">
  <AIPromptBar
    message={aiMessage || responseText}
    avatarState={voice.avatarState}
    voiceState={voice.voiceState}
    onVoiceClick={voice.toggleMic}
  />
</div>
```

---

### STEP 3: Fix ResponseBubble — Remove MiniAvatar badge

**File: `src/components/ai/ResponseBubble.tsx`**

DELETE the entire `MiniAvatar` function (lines ~48-54):
```tsx
// DELETE THIS:
function MiniAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-dark">
      <div className="h-3 w-3 rounded-full bg-white/20" />
    </div>
  );
}
```

DELETE the MiniAvatar usage in the JSX (around line ~107):
```tsx
// DELETE THIS:
<div className="absolute -top-3 -left-3">
  <MiniAvatar />
</div>
```

Change the message text container from `"pl-3 pt-1"` to `"pt-1"`:
```tsx
// CHANGE:
<div className="pl-3 pt-1">
// TO:
<div className="pt-1">
```

Also change `max-w-[80%]` to `max-w-full` to prevent text truncation:
```tsx
// CHANGE:
"mx-auto w-full max-w-[80%]",
// TO:
"mx-auto w-full",
```

---

### STEP 4: Add Nano Medical Logo file

The logo file `/nano-medical-logo.png` does NOT EXIST in `kiosk-ui/public/`.
This is why the HeaderBar shows no logo on any screen.

**Option A (recommended):** Create an SVG text-based logo as a fallback.

**File: Create `src/components/ui/NanoMedicalLogo.tsx`**

```tsx
import { cn } from "../../lib/cn";

interface LogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: { height: 32, fontSize: 14, iconSize: 20 },
  md: { height: 48, fontSize: 18, iconSize: 28 },
  lg: { height: 220, fontSize: 32, iconSize: 64 },
};

export function NanoMedicalLogo({ className, size = "md" }: LogoProps) {
  const s = sizes[size];

  return (
    <div className={cn("flex items-center gap-2.5", className)} style={{ height: s.height }}>
      {/* Icon — stylized "N" with medical cross */}
      <svg width={s.iconSize} height={s.iconSize} viewBox="0 0 40 40" fill="none">
        <rect width="40" height="40" rx="10" fill="#1E2A6E" />
        <path d="M12 28V12h3l10 12V12h3v16h-3L15 16v12h-3z" fill="white" />
        <rect x="18" y="8" width="4" height="10" rx="1" fill="#3B82F6" opacity="0.9" />
        <rect x="15" y="11" width="10" height="4" rx="1" fill="#3B82F6" opacity="0.9" />
      </svg>
      {/* Text */}
      <div className="flex flex-col leading-none">
        <span
          className="font-bold tracking-tight text-primary"
          style={{ fontSize: s.fontSize }}
        >
          NANO MEDICAL
        </span>
        {size !== "sm" && (
          <span
            className="font-medium tracking-wider text-text-muted"
            style={{ fontSize: s.fontSize * 0.5 }}
          >
            CLINIC
          </span>
        )}
      </div>
    </div>
  );
}
```

**File: Update `src/components/layout/HeaderBar.tsx`**

Replace the `<img>` logo with the new component:

```tsx
import { motion } from "framer-motion";
import { LanguageSelector } from "../ui/LanguageSelector";
import { NanoMedicalLogo } from "../ui/NanoMedicalLogo";
import { cn } from "../../lib/cn";

interface HeaderBarProps {
  title: string;
  className?: string;
}

export function HeaderBar({ title, className }: HeaderBarProps) {
  return (
    <div
      className={cn(
        "flex h-[80px] shrink-0 items-center justify-between border-b border-slate-200/60 bg-white/80 px-8 backdrop-blur-sm",
        className,
      )}
    >
      {/* Logo */}
      <NanoMedicalLogo size="sm" />

      {/* Title */}
      {title && (
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
          className="text-h2 tracking-heading text-text-primary"
        >
          {title}
        </motion.h1>
      )}

      {/* Language selector */}
      <LanguageSelector />
    </div>
  );
}
```

**Also update IdleScreen.tsx** — replace the `<img>` logo with:
```tsx
import { NanoMedicalLogo } from "../components/ui/NanoMedicalLogo";

// In the center content section, replace the logo circle + img with:
<div
  className="flex h-[280px] w-[280px] items-center justify-center rounded-full bg-white shadow-glow will-change-transform"
  style={{ animation: "logo-glow 3s ease-in-out infinite" }}
>
  <NanoMedicalLogo size="lg" />
</div>
```

---

### STEP 5: Fix "Qayta ulanmoqda..." connection status position

**File: `src/App.tsx`**

The `ConnectionStatus` component is at `fixed left-1/2 top-[88px]` which
overlaps the screen content. Move it to the bottom of the screen:

```tsx
function ConnectionStatus() {
  const isConnected = useSessionStore((s) => s.isConnected);
  if (isConnected) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="fixed bottom-[108px] left-1/2 z-50 -translate-x-1/2"
    >
      <div className="flex items-center gap-2 rounded-full bg-amber-50/90 backdrop-blur-sm px-4 py-1.5 text-[13px] font-medium text-amber-700 shadow-sm border border-amber-200/50">
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        <span>Qayta ulanmoqda...</span>
      </div>
    </motion.div>
  );
}
```

Changed: `top-[88px]` → `bottom-[108px]` (above the BottomNav bar)

---

### STEP 6: Fix "resepshn" typo

**File: `src/i18n/uz.json`**

Find and replace (2 occurrences):
- `"tagline": "Raqamli Resepshn"` → `"tagline": "Raqamli Qabulxona"`
- `"newVisitor": "...raqamli resepshn."` → `"...raqamli qabulxona."`

---

### STEP 7: Replace default emoji icons with custom SVG icons

**File: `src/screens/DepartmentSelectScreen.tsx`**

Replace the `DEPARTMENT_ICONS` emoji map and `getDepartmentIcon` function with
custom SVG icons. Create a new file:

**Create file: `src/components/icons/MedicalIcons.tsx`**

```tsx
import { cn } from "../../lib/cn";

interface IconProps {
  className?: string;
}

export function HeartPulseIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19.5 12.572l-7.5 7.428-7.5-7.428A5 5 0 1 1 12 6.006a5 5 0 1 1 7.5 6.572" />
      <path d="M7 12h2l2-3 2 6 2-3h2" />
    </svg>
  );
}

export function ToothIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2C8 2 5 5 5 8c0 2 .5 3.5 1 5 .8 2.4 1 4 1.5 6 .3 1 .8 1.5 1.5 1.5s1.2-.5 1.5-2c.3-1.5.5-2 1.5-2s1.2.5 1.5 2c.3 1.5.8 2 1.5 2s1.2-.5 1.5-1.5c.5-2 .7-3.6 1.5-6 .5-1.5 1-3 1-5 0-3-3-6-7-6z" />
    </svg>
  );
}

export function BabyIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="5" />
      <path d="M12 13c-4 0-7 2-7 5v1h14v-1c0-3-3-5-7-5z" />
      <circle cx="10" cy="7.5" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="14" cy="7.5" r="0.5" fill="currentColor" stroke="none" />
      <path d="M10.5 9.5c.5.5 2.5.5 3 0" />
    </svg>
  );
}

export function BrainIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a5 5 0 0 0-4.5 2.8A4 4 0 0 0 4 9a4 4 0 0 0 1.2 2.8A4.5 4.5 0 0 0 7 17.5V20h4v-8" />
      <path d="M12 2a5 5 0 0 1 4.5 2.8A4 4 0 0 1 20 9a4 4 0 0 1-1.2 2.8A4.5 4.5 0 0 1 17 17.5V20h-4v-8" />
      <path d="M8 10h.01M16 10h.01" />
    </svg>
  );
}

export function StethoscopeIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3" />
      <path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4" />
      <circle cx="20" cy="10" r="2" />
    </svg>
  );
}

export function EyeIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function SkinIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
      <path d="M8 12h.01M12 12h.01M16 12h.01" />
      <path d="M7 8l2 2M15 8l2 2" />
    </svg>
  );
}

export function BoneIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.2 3.4a2 2 0 0 1 3.4 2l-.5 1a2 2 0 0 0 .5 2.1l.5.5a2 2 0 0 1-1 3.4L18 13l-7 7-2-.5a2 2 0 0 1-1.4-1L7 17.2a2 2 0 0 1 .3-2.1l.5-.5a2 2 0 0 0-.4-2.9L6.8 11a2 2 0 0 1 0-3.4l1.2-.5A2 2 0 0 0 9.4 5l.5-1.2a2 2 0 0 1 3.4 0l.5.5a2 2 0 0 0 2 .7L17.2 3.4z" />
    </svg>
  );
}

export function HospitalIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21h18" />
      <path d="M5 21V7l8-4 8 4v14" />
      <rect x="9" y="9" width="6" height="6" rx="0.5" />
      <line x1="12" y1="9" x2="12" y2="15" />
      <line x1="9" y1="12" x2="15" y2="12" />
    </svg>
  );
}

export function EarIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 8.5a6.5 6.5 0 1 1 13 0c0 6-6 6.5-6 10.5" />
      <path d="M15 8.5a2.5 2.5 0 0 0-5 0v1a2 2 0 0 0 4 0" />
      <circle cx="13" cy="19" r="1" />
    </svg>
  );
}

export function ButterflyIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v18" />
      <path d="M3.5 8C5 5 8 3 12 3c4 0 7 2 8.5 5C22 11 22 14 20 16c-2 2-5 2-8 2s-6 0-8-2c-2-2-2-5-.5-8z" />
    </svg>
  );
}

// Icon map by department name keyword
export const MEDICAL_ICON_MAP: Record<string, React.FC<IconProps>> = {
  cardiology: HeartPulseIcon,
  kardiologiya: HeartPulseIcon,
  stomatology: ToothIcon,
  stomatologiya: ToothIcon,
  pediatrics: BabyIcon,
  pediatriya: BabyIcon,
  neurology: BrainIcon,
  nevrologiya: BrainIcon,
  therapy: StethoscopeIcon,
  terapiya: StethoscopeIcon,
  ophthalmology: EyeIcon,
  okulistika: EyeIcon,
  dermatology: SkinIcon,
  dermatologiya: SkinIcon,
  orthopedics: BoneIcon,
  ortopediya: BoneIcon,
  gynecology: BabyIcon,
  ginekologiya: BabyIcon,
  urology: HospitalIcon,
  urologiya: HospitalIcon,
  ent: EarIcon,
  lor: EarIcon,
  surgery: HospitalIcon,
  xirurgiya: HospitalIcon,
  endocrinology: ButterflyIcon,
  endokrinologiya: ButterflyIcon,
};

export function getMedicalIcon(name: string): React.FC<IconProps> {
  const lower = name.toLowerCase();
  for (const [key, Icon] of Object.entries(MEDICAL_ICON_MAP)) {
    if (lower.includes(key)) return Icon;
  }
  return HospitalIcon;
}
```

Now update `DepartmentSelectScreen.tsx`:

DELETE the old `DEPARTMENT_ICONS` map and `getDepartmentIcon` function.

Add import: `import { getMedicalIcon } from "../components/icons/MedicalIcons";`

In `DepartmentCard`, replace the emoji icon rendering:
```tsx
// REPLACE:
<IconCircle size="md" className="shrink-0 bg-primary-50 text-2xl">
  <span>{icon}</span>
</IconCircle>

// WITH:
{(() => {
  const Icon = getMedicalIcon(department.name);
  return (
    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary">
      <Icon className="h-7 w-7" />
    </div>
  );
})()}
```

Also update `InfoScreen.tsx` — replace its `DEPARTMENT_ICONS` emoji map with:
```tsx
import { getMedicalIcon } from "../components/icons/MedicalIcons";
```
And in `DepartmentInfoCard`, replace the emoji with:
```tsx
{(() => {
  const Icon = getMedicalIcon(department.name);
  return (
    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary text-2xl">
      <Icon className="h-6 w-6" />
    </div>
  );
})()}
```

---

### STEP 8: Reduce padding across all screens

Every screen uses `px-12` (48px each side on 1080px = 96px total padding).
This wastes space. Change to `px-8` (32px each side).

In ALL screen files, find and replace:
- `px-12` → `px-8`
- `gap-5` → `gap-4` (in card grids)

---

### STEP 9: GreetingScreen — merge with IntentScreen

The GreetingScreen MUST show intent cards (Qabulga yozilish, Ro'yxatdan o'tish, etc.)
directly below the greeting. Do NOT have a separate IntentScreen step.

See the full GreetingScreen rewrite in the previous KIOSK-CRITICAL-FIXES.md file.
Key changes:
1. Greeting + Intent cards on ONE screen
2. Avatar at 120px (centered, above bubble)
3. Intent cards with custom SVG icons in 2-column grid
4. Cards fill remaining vertical space
5. BottomNav at bottom

Also update `ScreenRouter.tsx`:
- Map `INTENT_DISCOVERY` state to render `"greeting"` screen key
- Pass `onSelectIntent={handlers.handleSelectIntent}` to GreetingScreen
- Add `onSelectIntent` prop to GreetingScreen component

And update `useScreenHandlers.ts`:
- All "back to intent" handlers should `setState("GREETING")` instead of `"INTENT_DISCOVERY"`

---

## COMPLETE FILE LIST TO MODIFY

| # | File | Action |
|---|------|--------|
| 1 | `src/components/ai/AIPromptBar.tsx` | **CREATE** — new reusable component |
| 2 | `src/components/ui/NanoMedicalLogo.tsx` | **CREATE** — SVG logo component |
| 3 | `src/components/icons/MedicalIcons.tsx` | **CREATE** — custom SVG medical icons |
| 4 | `src/components/ai/ResponseBubble.tsx` | **EDIT** — remove MiniAvatar, fix max-width |
| 5 | `src/components/layout/HeaderBar.tsx` | **EDIT** — use NanoMedicalLogo |
| 6 | `src/screens/DepartmentSelectScreen.tsx` | **EDIT** — use AIPromptBar, SVG icons, px-8 |
| 7 | `src/screens/DoctorSelectScreen.tsx` | **EDIT** — use AIPromptBar, px-8 |
| 8 | `src/screens/TimeSlotScreen.tsx` | **EDIT** — use AIPromptBar, px-8 |
| 9 | `src/screens/BookingConfirmScreen.tsx` | **EDIT** — use AIPromptBar, px-8 |
| 10 | `src/screens/CheckInScreen.tsx` | **EDIT** — use AIPromptBar, px-8 |
| 11 | `src/screens/InfoScreen.tsx` | **EDIT** — use AIPromptBar, SVG icons, px-8 |
| 12 | `src/screens/IntentScreen.tsx` | **EDIT** — use AIPromptBar, SVG icons, px-8 |
| 13 | `src/screens/GreetingScreen.tsx` | **REWRITE** — merge intents, use NanoMedicalLogo |
| 14 | `src/screens/IdleScreen.tsx` | **EDIT** — use NanoMedicalLogo |
| 15 | `src/App.tsx` | **EDIT** — move ConnectionStatus to bottom |
| 16 | `src/i18n/uz.json` | **EDIT** — fix "resepshn" typo |
| 17 | `src/router/ScreenRouter.tsx` | **EDIT** — map INTENT_DISCOVERY→greeting |
| 18 | `src/router/useScreenHandlers.ts` | **EDIT** — back handlers to GREETING |

---

## VERIFICATION CHECKLIST

After ALL changes, verify:

1. [ ] `npm run build` succeeds — zero errors
2. [ ] AIPromptBar.tsx created and used in ALL inner screens
3. [ ] Avatar is SMALL (48px) on inner screens — NO overlap with text
4. [ ] Avatar is properly clipped (overflow:hidden) — NO bleed outside 48px
5. [ ] NanoMedicalLogo shows in HeaderBar on ALL screens
6. [ ] NanoMedicalLogo shows large on IdleScreen
7. [ ] "Qayta ulanmoqda..." shows at BOTTOM, not overlapping header
8. [ ] MiniAvatar badge REMOVED from ResponseBubble
9. [ ] ResponseBubble text NOT truncated (max-w-full)
10. [ ] "resepshn" replaced with "qabulxona" (2 places in uz.json)
11. [ ] DepartmentSelectScreen uses custom SVG icons (NOT emoji)
12. [ ] InfoScreen uses custom SVG icons (NOT emoji)
13. [ ] All screens use px-8 (not px-12)
14. [ ] GreetingScreen shows intent cards directly
15. [ ] INTENT_DISCOVERY maps to greeting screen in router
16. [ ] Back navigation goes to GREETING (not INTENT_DISCOVERY)
17. [ ] Test at 1080×1920 viewport — no empty space

---

## PRIORITY ORDER (do in this exact order)

1. Create AIPromptBar.tsx (5 min) — fixes the WORST bug across all screens
2. Create NanoMedicalLogo.tsx (3 min) — fixes missing logo
3. Create MedicalIcons.tsx (5 min) — fixes emoji icons
4. Fix ResponseBubble.tsx (2 min) — remove MiniAvatar
5. Fix HeaderBar.tsx (1 min) — use NanoMedicalLogo
6. Fix App.tsx ConnectionStatus (1 min) — move to bottom
7. Fix uz.json typo (30 sec)
8. Update ALL 7 inner screens to use AIPromptBar + px-8 (15 min)
9. Rewrite GreetingScreen with merged intents (10 min)
10. Update IdleScreen to use NanoMedicalLogo (2 min)
11. Update ScreenRouter + useScreenHandlers (3 min)
12. Build and test (5 min)
