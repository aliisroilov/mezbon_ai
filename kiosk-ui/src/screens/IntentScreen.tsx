import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  CalendarPlus,
  UserCheck,
  Info,
  CreditCard,
  MessageCircle,
} from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { IconCircle } from "../components/ui/IconCircle";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";

// ── Intent card data ────────────────────────────────────────

interface IntentAction {
  id: string;
  labelKey: string;
  subtitleKey: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}

const INTENTS: IntentAction[] = [
  {
    id: "book",
    labelKey: "intent.bookAppointment",
    subtitleKey: "intent.bookAppointmentDesc",
    icon: <CalendarPlus className="h-6 w-6" />,
    iconBg: "bg-primary-50",
    iconColor: "text-primary",
  },
  {
    id: "checkin",
    labelKey: "intent.checkIn",
    subtitleKey: "intent.checkInDesc",
    icon: <UserCheck className="h-6 w-6" />,
    iconBg: "bg-green-50",
    iconColor: "text-green-600",
  },
  {
    id: "info",
    labelKey: "intent.information",
    subtitleKey: "intent.informationDesc",
    icon: <Info className="h-6 w-6" />,
    iconBg: "bg-accent-50",
    iconColor: "text-accent",
  },
  {
    id: "payment",
    labelKey: "intent.payment",
    subtitleKey: "intent.paymentDesc",
    icon: <CreditCard className="h-6 w-6" />,
    iconBg: "bg-amber-50",
    iconColor: "text-amber-600",
  },
  {
    id: "other",
    labelKey: "intent.faq",
    subtitleKey: "intent.faqDesc",
    icon: <MessageCircle className="h-6 w-6" />,
    iconBg: "bg-violet-50",
    iconColor: "text-violet-600",
  },
];

// ── Single intent card ──────────────────────────────────────

interface IntentCardProps {
  intent: IntentAction;
  index: number;
  selected: boolean;
  onSelect: () => void;
}

function IntentCard({ intent, index, selected, onSelect }: IntentCardProps) {
  const { t } = useTranslation();

  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: 0.15 + index * 0.08,
        duration: 0.4,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.97 }}
      onClick={onSelect}
      aria-label={t(intent.labelKey)}
      className={cn(
        "group relative flex w-full items-center gap-5 rounded-card bg-white p-6 text-left shadow-card",
        "transition-shadow duration-200 hover:shadow-card-hover",
        "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/40 focus-visible:ring-offset-4",
        selected && "ring-2 ring-primary/40",
      )}
    >
      {/* Teal left border — slides in on hover/select */}
      <motion.div
        className="absolute left-0 top-4 bottom-4 w-1 rounded-full bg-primary"
        initial={{ scaleY: 0 }}
        animate={{ scaleY: selected ? 1 : 0 }}
        whileHover={{ scaleY: 1 }}
        transition={{ duration: 0.2 }}
        style={{ originY: 0.5 }}
      />

      {/* Icon */}
      <IconCircle
        size="md"
        className={cn(intent.iconBg, intent.iconColor, "shrink-0")}
      >
        {intent.icon}
      </IconCircle>

      {/* Text */}
      <div className="min-w-0 flex-1">
        <p className="text-h3 tracking-heading text-text-primary">
          {t(intent.labelKey)}
        </p>
        <p className="mt-1 text-body text-text-muted">
          {t(intent.subtitleKey)}
        </p>
      </div>

      {/* Arrow hint */}
      <motion.div
        className="shrink-0 text-text-muted"
        initial={{ x: 0, opacity: 0.4 }}
        whileHover={{ x: 4, opacity: 1 }}
        transition={{ duration: 0.15 }}
      >
        <svg
          viewBox="0 0 20 20"
          width={20}
          height={20}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
        >
          <path d="M7 4l6 6-6 6" />
        </svg>
      </motion.div>
    </motion.button>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface IntentScreenProps {
  onSelectIntent: (intentId: string) => void;
  onBack: () => void;
}

export function IntentScreen({ onSelectIntent, onBack }: IntentScreenProps) {
  const { t } = useTranslation();
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 800 });

  const responseText = aiMessage || t("intent.title");

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Header */}
      <HeaderBar title={t("intent.title")} />

      {/* ── AI prompt bar ── */}
      <div className="px-8 pt-6">
        <AIPromptBar
          message={responseText}
          avatarState={voice.avatarState}
          voiceState={voice.voiceState}
          onVoiceClick={voice.toggleMic}
        />
      </div>

      {/* ── Center area: intent cards (65%) ── */}
      <div className="flex flex-1 flex-col px-8 pt-4">

        {/* 2-column grid, last card centered if odd */}
        <div className="grid grid-cols-2 gap-4">
          {INTENTS.map((intent, i) => {
            const isLastOdd = i === INTENTS.length - 1 && INTENTS.length % 2 !== 0;
            return (
              <div
                key={intent.id}
                className={cn(isLastOdd && "col-span-2 mx-auto w-1/2")}
              >
                <IntentCard
                  intent={intent}
                  index={i}
                  selected={false}
                  onSelect={() => { sounds.tap(); onSelectIntent(intent.id); }}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom navigation */}
      <BottomNav onBack={onBack} />
    </motion.div>
  );
}
