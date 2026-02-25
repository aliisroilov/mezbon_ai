# MEZBON AI — PREMIUM UI REDESIGN + NANO MEDICAL BRANDING

## WHAT'S WRONG (from kiosk photos)

I took photos of the kiosk running. The UI quality is **unacceptable for a production clinic**. Here's everything wrong:

### Critical Problems
1. **Browser chrome visible** — Tab bar, address bar, minimize/maximize/close buttons all showing. This is NOT kiosk mode.
2. **Windows taskbar visible** — Start menu, search bar, system tray all exposed. Patient could exit the app.
3. **"Offline" indicator** — Big ugly red dot + "Offline" text in top-left. Looks broken.
4. **60% empty white space** — Content only fills the top 40% of the 1920px-tall portrait screen. Bottom is blank.
5. **Avatar looks like a children's toy** — A green blob with 2 dots and a smile. Not professional for a medical clinic.
6. **No clinic branding** — No Nano Medical logo, no brand colors on intent/department screens. Could be any generic app.
7. **Cards are flat and basic** — Department/intent cards look like default Tailwind with barely-there backgrounds. No depth, no visual appeal.
8. **Icons inconsistent** — Mix of Lucide icons and random emoji. Some cards have emoji, others have stroke icons.
9. **Background is plain** — The gradient is so subtle it looks like flat gray. No premium feel.
10. **Voice indicator lost** — "Tinglayapman..." text is tiny, stuck between avatar and content. Not prominent.
11. **Layout doesn't use portrait height** — Everything crammed at top. Should vertically center and space out for 1080×1920.
12. **Language selector is tiny** — UZ RU GB in bottom corner. Hard to tap on 32" screen.
13. **"Orqaga" back button** — Tiny text link in bottom-right. Should be a proper button.
14. **"resepshn" misspelling** — Should be "raqamli qabulxona" (digital reception)

### The Standard We Must Hit
Think: **Samsung hospital kiosks**, **Apple Genius Bar iPad**, **Emirates check-in terminal**. Clean, confident, premium. Not "student hackathon demo."

---

## BRAND IDENTITY — NANO MEDICAL CLINIC

### Colors (extracted from logo)
The logo uses deep **indigo-navy** (`#1E2070` family). NOT teal, NOT blue. It's a distinctive dark purple-navy.

```
Primary:          #1E2A6E (deep indigo-navy — logo dominant)
Primary Dark:     #141D52 (hover, pressed states)
Primary Light:    #2D3A8C (lighter interactive elements)
Primary 50:       #EEF0F7 (very light backgrounds)
Primary 100:      #D0D4E8 (light borders, subtle fills)

Accent:           #3B82F6 (bright blue — buttons, CTAs, links)
Accent Light:     #DBEAFE (light blue backgrounds)

Surface:          #F8FAFC (main background)
Surface Card:     #FFFFFF (card backgrounds)
Surface Elevated: #FFFFFF (modals, elevated surfaces)

Text Primary:     #0F172A (headings)
Text Body:        #334155 (body text)
Text Muted:       #94A3B8 (secondary, captions)
Text Inverse:     #FFFFFF (on dark backgrounds)

Success:          #10B981 (confirmations, active)
Warning:          #F59E0B (attention)
Danger:           #EF4444 (errors, cancel)
Info:             #3B82F6 (information)

Border:           #E2E8F0 (subtle lines)
Border Active:    #1E2A6E (selected states)

Shadow Color:     rgba(30, 42, 110, 0.08) (indigo-tinted shadows)
```

### Brand Usage Rules
- **Primary indigo-navy** is used for: header bars, avatar gradient, selected states, primary buttons
- **Accent blue** is used for: interactive links, secondary CTAs, icons on light backgrounds
- **NEVER use teal/emerald** — that was the old generic color. Replace ALL teal references.
- **Logo** appears on: IdleScreen (large, centered), top-left header area on all other screens (small, 48px)

---

## PHASE 1: FIX CRITICAL DEPLOYMENT ISSUES

### 1.1 — Chrome Kiosk Mode
The kiosk startup must launch Chrome in TRUE kiosk mode:
```
chrome --kiosk --start-fullscreen --disable-session-crashed-bubble --noerrdialogs --disable-translate --no-first-run --disable-features=TranslateUI --disable-infobars --disable-pinch --overscroll-history-navigation=0
```
This removes: tabs, address bar, close buttons, right-click, etc.

### 1.2 — Hide Windows Taskbar
In `kiosk-setup/startup.bat`, add PowerShell commands to auto-hide taskbar before launching Chrome.

### 1.3 — Fullscreen on Load
In `App.tsx`, request fullscreen on first touch/click:
```typescript
document.documentElement.requestFullscreen?.();
```
Already exists (verify it works). Also add:
```css
html, body { overflow: hidden; cursor: none; } /* Hide cursor on kiosk */
```
Show cursor only when touch is detected (for non-touch fallback).

---

## PHASE 2: COMPLETE COLOR MIGRATION (teal → indigo-navy)

### 2.1 — `tailwind.config.ts`
Replace the entire color system:

```typescript
colors: {
  primary: {
    DEFAULT: "#1E2A6E",
    dark: "#141D52",
    light: "#2D3A8C",
    50: "#EEF0F7",
    100: "#D0D4E8",
    200: "#A8AECF",
    300: "#7880B5",
    400: "#4E579B",
    500: "#1E2A6E",
    600: "#1A2561",
    700: "#141D52",
    800: "#0F1642",
    900: "#0A0F33",
  },
  accent: {
    DEFAULT: "#3B82F6",
    dark: "#2563EB",
    light: "#DBEAFE",
    50: "#EFF6FF",
  },
  surface: {
    DEFAULT: "#F8FAFC",
    card: "#FFFFFF",
  },
  text: {
    primary: "#0F172A",
    body: "#334155",
    muted: "#94A3B8",
    inverse: "#FFFFFF",
  },
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  info: "#3B82F6",
  border: {
    DEFAULT: "#E2E8F0",
    active: "#1E2A6E",
  },
},
boxShadow: {
  card: "0 4px 24px rgba(30, 42, 110, 0.06), 0 1px 3px rgba(30, 42, 110, 0.04)",
  "card-hover": "0 8px 32px rgba(30, 42, 110, 0.12), 0 2px 4px rgba(30, 42, 110, 0.06)",
  modal: "0 24px 48px rgba(30, 42, 110, 0.18)",
  button: "0 2px 12px rgba(30, 42, 110, 0.25)",
  glow: "0 0 40px rgba(30, 42, 110, 0.15)",
  "glow-active": "0 0 60px rgba(30, 42, 110, 0.25)",
},
```

### 2.2 — `globals.css`
Add CSS variables and keyframes:
```css
:root {
  --color-primary: #1E2A6E;
  --color-primary-dark: #141D52;
  --color-primary-light: #2D3A8C;
  --color-accent: #3B82F6;
}
```

### 2.3 — Global Search & Replace
Search the ENTIRE `kiosk-ui/src/` for these and replace:
```
"#0D9488"     → "#1E2A6E"
"#0F766E"     → "#141D52"
"#CCFBF1"     → "#EEF0F7"
"#F59E0B"     → "#3B82F6"  (accent color, where used as primary accent)
"teal-600"    → "primary"
"teal-700"    → "primary-dark"
"teal-50"     → "primary-50"
"teal-"       → replace contextually with "primary-" variants
"emerald-"    → replace contextually with "success" or "primary-"
rgba(13, 148, 136  → rgba(30, 42, 110   (shadow/glow colors)
rgba(45, 212, 191  → rgba(30, 42, 110   (glow colors)
```

### 2.4 — `AIAvatar.tsx` gradient colors
Update ALL gradient definitions:
```typescript
const GRADIENT_STOPS: Record<AvatarState, [string, string, string]> = {
  idle:      ["#2D3A8C", "#1E2A6E", "#3B82F6"],
  listening: ["#3B82F6", "#1E2A6E", "#6366F1"],
  speaking:  ["#2D3A8C", "#1E2A6E", "#4F46E5"],
  thinking:  ["#6366F1", "#1E2A6E", "#8B5CF6"],
  success:   ["#10B981", "#059669", "#10B981"],
};
```

---

## PHASE 3: LAYOUT SYSTEM FOR PORTRAIT 1080×1920

Every screen must properly use the full 1080×1920 portrait layout. The current layout wastes 60% of vertical space.

### Screen Layout Template
Every screen should follow this structure:
```
┌──────────────────────────┐ ← 0px
│  Header Bar (80px)        │  Logo left, title center, lang right
│  ─────────────────────── │
│                           │
│  AI Section (300-400px)   │  Avatar + message bubble + voice indicator
│                           │
│  ─────────────────────── │
│                           │
│  Content Area (flex-1)    │  Cards, lists, forms — SCROLLABLE if needed
│                           │
│  ─────────────────────── │
│  Bottom Bar (100px)       │  Navigation buttons, back/home
└──────────────────────────┘ ← 1920px
```

### Header Bar Component — CREATE NEW: `components/layout/HeaderBar.tsx`
```
Height: 80px
Background: white with subtle bottom border
Left: Nano Medical logo (48px height, link to home)
Center: Screen title (h2 size)
Right: Language selector (pill buttons UZ | RU)
```
This header appears on ALL screens except IdleScreen.

### Bottom Navigation — CREATE NEW: `components/layout/BottomNav.tsx`
```
Height: 100px (safe area for standing users who look down)
Background: white with subtle top border
Left: "← Orqaga" button (secondary, icon + text, 56px height)
Center: (optional progress indicator for multi-step flows)
Right: "🏠 Asosiy" home button (ghost, icon + text)
```
Appears on all screens except Idle and Farewell.

---

## PHASE 4: REDESIGN EVERY SCREEN

### 4.1 — IdleScreen (the "Welcome Display")

This is the FIRST thing patients see. It must look like a premium digital display, not a web page.

**Layout:**
```
Full screen, vertically centered.
Background: Animated gradient using brand colors
  linear-gradient(135deg, #EEF0F7 0%, #F8FAFC 30%, #E8ECF5 60%, #F0F2FA 100%)
  Slowly rotating (20s cycle)

Floating orbs: 3 orbs using primary color (rgba(30, 42, 110, 0.1-0.15))

Center content:
  ┌─────────────────────────┐
  │                          │
  │    [NANO MEDICAL LOGO]   │  280px width, crisp, with breathing glow
  │                          │
  │   "Nano Medical Clinic"  │  H1, 44px, primary color
  │    "Raqamli qabulxona"   │  Body-lg, 20px, text-muted
  │                          │
  │       [Animated wave]    │  Subtle hand wave emoji or motion graphic
  │   "Yaqinlashing yoki     │  Body-lg, pulsing opacity
  │    ekranni bosing"       │
  │                          │
  └─────────────────────────┘

Bottom: Language selector (left) | Clock + Date (center) | "Nano Medical" small text (right)
```

**The logo must be PROMINENT.** Use the actual `nano-medical-logo.png`. Place it in a white circle container (280px) with a soft indigo glow shadow that pulses gently (breathing animation).

### 4.2 — GreetingScreen

**Remove the smiley-face avatar for this screen.** Instead:

```
Top section (40% of screen):
  ┌─────────────────────────┐
  │  [Header Bar]            │
  │                          │
  │     [AI AVATAR]          │  120px, professional, indigo gradient
  │                          │
  │  ┌──────────────────┐   │
  │  │ AI Message Bubble │   │  White card, 20px radius, shadow
  │  │ "Nano Medical     │   │  Max-width 85%
  │  │  Clinic ga xush   │   │
  │  │  kelibsiz!"       │   │
  │  └──────────────────┘   │
  │                          │
  │  🎙 Tinglayapman...     │  Voice indicator, prominent
  └─────────────────────────┘

Bottom section (60% of screen):
  "Sizga qanday yordam beraman?" — H2 centered

  [Intent cards grid — 2 columns]
  ┌────────────┐ ┌────────────┐
  │ 📅 Qabulga │ │ ✅ Ro'yxat-│
  │  yozilish  │ │ dan o'tish │
  └────────────┘ └────────────┘
  ┌────────────┐ ┌────────────┐
  │ ℹ️ Ma'lumot│ │ 💳 To'lov  │
  │   olish    │ │   qilish   │
  └────────────┘ └────────────┘
       ┌────────────────┐
       │ ❓ Ko'p so'rala-│
       │ digan savollar  │
       └────────────────┘

  [Bottom Nav with home button]
```

**Key change:** Combine GreetingScreen and IntentScreen into ONE screen. Currently they're separate, which wastes time and feels disconnected. The greeting message + intent options should be on the same screen.

If they MUST stay separate (state machine requires it), then at least make IntentScreen show the AI avatar + last message at the top (not duplicated separate greeting).

### 4.3 — DepartmentSelectScreen

```
┌─────────────────────────────┐
│ [Header: "Bo'limni tanlang"] │
│                              │
│ [AI Avatar small] "Qaysi    │
│  bo'limga murojaat           │
│  qilmoqchisiz?"              │
│                              │
│ 🎙 Tinglayapman...          │
│                              │
│ ┌────────────┐┌────────────┐ │  ← Cards START here
│ │ 🔬         ││ 🔪         │ │
│ │ Endokrino- ││ Xirurgiya  │ │  Each card: 160px height
│ │ logiya     ││            │ │  White bg, 20px radius
│ │ 1-qavat    ││ 1-qavat    │ │  Left: colored icon circle
│ │ 1 shifokor ││ 1 shifokor │ │  Title: H3 (22px)
│ └────────────┘└────────────┘ │  Subtitle: caption
│ ┌────────────┐┌────────────┐ │  Doctor count: badge
│ │ 🧠         ││ 🫀         │ │
│ │ Nevrolo-   ││ Kardiolo-  │ │  On tap:
│ │ giya       ││ giya       │ │   scale(0.97) → bounce back
│ └────────────┘└────────────┘ │   left border turns primary
│ ┌────────────┐┌────────────┐ │
│ │ 🩺         ││ 💊         │ │
│ │ Mammolo-   ││ Terapiya   │ │
│ │ giya       ││            │ │
│ └────────────┘└────────────┘ │
│ ┌────────────┐┌────────────┐ │
│ │ 📡         ││ 🚑         │ │
│ │ Radiolo-   ││ Reanima-   │ │
│ │ giya       ││ tsiya      │ │
│ └────────────┘└────────────┘ │
│                              │
│ [Bottom Nav: ← Orqaga  🏠]  │
└─────────────────────────────┘
```

**Card design must be PREMIUM:**
- White background with indigo-tinted shadow
- Left side: 48px colored circle with white icon/emoji
- The circle background should be `primary-50` with `primary` icon
- On hover/tap: card gets a 3px left border in primary color + slight scale + elevated shadow
- Selected state: primary-50 background + primary left border + checkmark top-right
- Minimum card height: 140px (comfortable touch target)
- Gap between cards: 16px
- Outer padding: 24px

### 4.4 — DoctorSelectScreen

Similar grid layout. Doctor cards should show:
- Doctor initial in a colored circle (since no photos): "Н" for Nasirxodjaev, "А" for Aripova, etc.
- Full name (H3)
- Specialty (body, muted)
- Experience badge: "28 yil tajriba" in a small pill
- Schedule: "08:00-16:00" in caption
- Rating stars (optional, from demo data)

### 4.5 — TimeSlotScreen

- Date selector at top (today/tomorrow/+2 days as pill buttons)
- Time slots in 3-column grid
- Each slot: pill shape, ~52px height
- Available: white bg, primary-100 border, primary text
- Selected: primary bg, white text, button shadow
- Unavailable: slate-100 bg, line-through, disabled
- Selected slot confirmation at bottom before proceeding

### 4.6 — BookingConfirmScreen

Premium confirmation card:
- White elevated card with larger shadow (modal-level)
- Top: Doctor name + specialty in primary color header
- Divider
- Details with icons: 📅 Date, 🕐 Time, 💊 Service, 💰 Price
- Each detail row: icon (primary-50 circle) + label (muted) + value (body)
- Divider
- Large "Tasdiqlash" primary button (72px height, full width)
- Smaller "Bekor qilish" ghost button below

### 4.7 — QueueTicketScreen

This is the VICTORY screen — patient successfully booked!

```
Center of screen:
  ┌─────────────────────────┐
  │   ✅ Muvaffaqiyatli!    │  Success animation (checkmark draw)
  │                          │
  │   Sizning raqamingiz:    │  Body-lg
  │                          │
  │      ┌─────────┐        │
  │      │  A-142   │        │  HUGE: 80px font, 800 weight
  │      │          │        │  Primary color, pulsing glow
  │      └─────────┘        │
  │                          │
  │   🏥 Endokrinologiya    │  Department
  │   👨‍⚕️ Nasirxodjaev Yo.B. │  Doctor
  │   🕐 14:30              │  Time
  │   📍 1-qavat, 101-xona  │  Room
  │                          │
  │   [🖨 Chop etish]       │  Print ticket button
  └─────────────────────────┘

  Auto-redirect timer: "10 soniyada asosiy sahifaga o'tiladi"
  Progress bar at bottom counting down
```

### 4.8 — FarewellScreen

- Large friendly message centered
- "Rahmat! Sog'liq tilaymiz!" in H1
- Nano Medical logo below (120px)
- Auto-reset countdown bar (10 seconds)
- Smooth fade-out transition to Idle

---

## PHASE 5: AI AVATAR REDESIGN

The current smiley-face green blob is NOT acceptable for a medical clinic. Redesign:

### Option A: Abstract Orb (recommended)
Keep the orb concept but make it professional:
- **Main circle:** Deep indigo gradient (`#1E2A6E` → `#2D3A8C` → `#3B82F6`)
- **Remove the eyes and smile** — they look childish. A premium AI doesn't need a face.
- Instead: subtle **inner glow** pattern that shifts based on state
- Listening: concentric ripple rings expanding outward (indigo)
- Speaking: smooth wave visualization around the orb (thin lines, elegant)
- Thinking: gentle pulse with 3 dots below
- Idle: slow breathing scale animation with soft glow

### Option B: Medical Cross/Stethoscope Icon
- Circular container with the Nano Medical logo inside
- Animated border that changes based on state
- More branded, less generic "AI ball"

**Go with Option A** — but remove the cartoon face. The orb should look like a Siri/Alexa-style AI indicator, not a Tamagotchi.

Update `AIAvatar.tsx`:
- Remove `AvatarEyes` component entirely
- Remove `AvatarSmile` component entirely
- Replace with inner glow/light pattern that subtly shifts
- Keep `CircularWaveform` for speaking (but use thinner, more elegant lines)
- Keep ripple rings for listening
- Keep thinking dots
- Add a very subtle inner highlight (like a light reflection on glass) that slowly rotates

---

## PHASE 6: CARD COMPONENT REDESIGN

### Create `components/ui/Card.tsx` — Base card component
```typescript
interface CardProps {
  children: React.ReactNode;
  selected?: boolean;
  onClick?: () => void;
  icon?: React.ReactNode;
  className?: string;
}
```
Features:
- White bg, `rounded-[20px]`, `shadow-card`
- On press: `scale(0.97)` spring animation (150ms)
- On release: `scale(1.02)` then `scale(1)` (bounce effect)
- Selected: `bg-primary-50`, `border-l-4 border-primary`, elevated shadow
- Hover: `translateY(-2px)`, enhanced shadow
- Active: slight bg opacity change
- Transition: `all 200ms ease`

### Department Card — redesign
```
┌───────────────────────────┐
│  ┌────┐                   │
│  │ 🔬 │  Endokrinologiya  │  ← 48px icon circle (primary-50 bg)
│  └────┘  1-qavat • 101-xona│ ← Subtitle in muted
│          ● 1 shifokor  →  │  ← Doctor count badge + arrow
└───────────────────────────┘
   min-height: 120px
   padding: 24px
   gap between icon and text: 16px
```

### Intent Card — redesign
```
┌───────────────────────────┐
│         ┌────┐            │  ← 56px icon circle (primary-50 bg)
│         │ 📅 │            │
│         └────┘            │
│    Qabulga yozilish       │  ← H3 centered
│  Shifokor tanlang va      │  ← Caption centered, muted
│    vaqt belgilang          │
└───────────────────────────┘
   min-height: 160px (taller for intent)
   text-align: center
   Vertical layout (icon on top)
```

---

## PHASE 7: VOICE INDICATOR REDESIGN

### Create prominent voice section
The voice indicator must be prominent and clear — patients need to know they can speak.

```
┌──────────────────────────────┐
│                              │
│     🎙️  Gapiring...         │  When listening
│     ●●●  Kutilmoqda...      │  When thinking
│     🔊  Javob berilmoqda... │  When speaking
│                              │
└──────────────────────────────┘
```

Design:
- Centered pill-shaped container: `bg-primary-50`, `rounded-full`, `px-8 py-4`
- Mic icon: animated (pulsing scale when active)
- Text: `text-body`, `text-primary`
- When listening: mic icon has concentric ring animation (ripple)
- When inactive: mic icon is muted color, "Tinglash uchun bosing" text
- Minimum height: 56px (tappable)
- Tap toggles mic on/off

---

## PHASE 8: TYPOGRAPHY & SPACING POLISH

### Font sizes for 32" screen
Users stand 60-100cm from the kiosk. Text must be READABLE. Current sizes in CLAUDE.md are good, but verify:
- H1: 40px minimum (screen titles)
- H2: 28px (section headers)  
- H3: 22px (card titles)
- Body: 18px (regular text)
- Caption: 14px (only for truly secondary info)
- Display: 56px+ (ticket numbers, greetings)

### Spacing
- Screen outer padding: 32px (not 48px — we need the horizontal space on 1080px)
- Card inner padding: 24px
- Card gap: 16px
- Section gap: 32px
- Button min-height: 56px (primary actions: 64px)
- Touch target: minimum 56×56px

---

## PHASE 9: UPDATE CLAUDE.md DESIGN SYSTEM

Rewrite the `🎨 UI/UX DESIGN SYSTEM` section of CLAUDE.md to reflect:

1. **Colors:** Replace ALL teal references with indigo-navy Nano Medical brand
2. **Avatar:** Remove smiley face description. Describe professional abstract orb.
3. **Cards:** Update card specs with new shadow colors, selected states
4. **Layout:** Add portrait 1080×1920 layout template with header/content/bottom zones
5. **Brand:** Add Nano Medical logo usage rules
6. **Voice indicator:** Update description for new prominent design
7. **Remove DO NOT #1 about dark mode** — keep it, but update context
8. **Update all rgba() shadow colors** from teal to indigo

---

## FILES TO MODIFY

Priority order:
1. `tailwind.config.ts` — Colors, shadows, animations
2. `src/styles/globals.css` — CSS variables, keyframes, base styles
3. `src/components/ai/AIAvatar.tsx` — Remove face, professional orb
4. `src/components/ai/VoiceIndicator.tsx` — Prominent redesign
5. `src/components/ai/ResponseBubble.tsx` — Indigo accent colors
6. `src/components/ui/Button.tsx` — Indigo primary, blue accent
7. `src/components/ui/Card.tsx` — NEW: base card component
8. `src/components/layout/HeaderBar.tsx` — NEW: screen header
9. `src/components/layout/BottomNav.tsx` — NEW: bottom navigation
10. `src/screens/IdleScreen.tsx` — Premium welcome display with logo
11. `src/screens/GreetingScreen.tsx` — Avatar + greeting + intent cards
12. `src/screens/IntentScreen.tsx` — Redesign or merge with greeting
13. `src/screens/DepartmentSelectScreen.tsx` — Premium cards, full height
14. `src/screens/DoctorSelectScreen.tsx` — Doctor cards with initials
15. `src/screens/TimeSlotScreen.tsx` — Pill grid, date selector
16. `src/screens/BookingConfirmScreen.tsx` — Premium summary card
17. `src/screens/QueueTicketScreen.tsx` — Victory screen with ticket
18. `src/screens/FarewellScreen.tsx` — Thank you + auto-reset
19. `src/screens/CheckInScreen.tsx` — Update colors
20. `src/screens/PaymentScreen.tsx` — Update colors
21. `src/screens/InfoScreen.tsx` — Update colors
22. `src/screens/HandOffScreen.tsx` — Update colors
23. `src/components/ui/LanguageSelector.tsx` — Larger, pill buttons
24. `src/components/feedback/LoadingMessage.tsx` — Indigo shimmer
25. `src/router/ScreenRouter.tsx` — Verify all transitions work

---

## IMPORTANT RULES

1. **Every color must be from the Nano Medical brand palette.** No teal, no generic blue. Use `#1E2A6E` family.
2. **Every screen must fill the full 1080×1920 portrait layout.** No 60% empty space.
3. **Every screen must have HeaderBar (except Idle) and BottomNav (except Idle/Farewell).**
4. **The avatar must NOT have a cartoon face.** Professional abstract orb only.
5. **Cards must have depth.** Shadows, border radius, hover/press animations.
6. **Touch targets minimum 56px.** No tiny text links as buttons.
7. **The Nano Medical logo must appear on IdleScreen (large) and HeaderBar (small).**
8. **No horizontal scrolling on any screen.** Everything fits in 1080px width.
9. **Test every screen in 1080×1920 viewport** before declaring done.
10. **Don't break existing functionality.** This is a visual redesign, not a logic rewrite. All Socket.IO events, state transitions, and voice hooks must continue working.

---

## VERIFICATION CHECKLIST

After ALL changes:

- [ ] `npm run build` succeeds with zero errors
- [ ] Set browser to 1080×1920 — every screen renders correctly
- [ ] IdleScreen: Nano Medical logo prominent, indigo gradient, no teal
- [ ] GreetingScreen: Professional avatar (no smiley face), intent cards visible
- [ ] DepartmentScreen: 8 cards, all tappable, premium shadows, indigo accents
- [ ] DoctorScreen: Doctor cards with initials, experience, schedule
- [ ] TimeSlotScreen: 3-column grid, pills, date selector
- [ ] BookingConfirmScreen: Premium summary card, all details visible
- [ ] QueueTicketScreen: Large ticket number (80px), success animation
- [ ] FarewellScreen: Auto-reset works, thank you message
- [ ] Voice indicator: Prominent, tappable, clear state feedback
- [ ] HeaderBar: Logo + title + language on all screens (except Idle)
- [ ] BottomNav: Back + Home buttons on all screens (except Idle/Farewell)
- [ ] ALL teal/emerald colors replaced with indigo-navy
- [ ] ALL shadows use indigo-tinted rgba (not teal)
- [ ] No cartoon face on avatar
- [ ] No horizontal scrolling
- [ ] All buttons ≥ 56px height
- [ ] Console: zero errors
