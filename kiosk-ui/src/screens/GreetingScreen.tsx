import { useCallback, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { ArrowRight, Calendar, Clock } from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
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

        {/* ── AI Prompt Bar ── */}
        <div className="px-8 pt-8 pb-4">
          <AIPromptBar
            message={greetingText}
            avatarState={voice.avatarState}
            voiceState={voice.voiceState}
            onVoiceClick={voice.toggleMic}
          />
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
          {INTENTS[4] && (
            <div className="mt-4">
              <IntentCard intent={INTENTS[4]} index={4}
                selected={selectedIntent === INTENTS[4].id}
                onSelect={() => handleIntent(INTENTS[4]!.id)} />
            </div>
          )}
        </div>
      </div>

      {/* Bottom nav */}
      <BottomNav onBack={() => { useSessionStore.getState().resetSession(); }} />
    </motion.div>
  );
}
