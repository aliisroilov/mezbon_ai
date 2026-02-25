import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { ChevronRight, RefreshCw } from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { LoadingMessage } from "../components/feedback/LoadingMessage";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";
import type { Doctor } from "../types";

// ── Doctor initials avatar ──────────────────────────────────

function DoctorAvatar({ doctor }: { doctor: Doctor }) {
  const initials = doctor.full_name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  if (doctor.photo_url) {
    return (
      <img
        src={doctor.photo_url}
        alt={doctor.full_name}
        className="h-[72px] w-[72px] shrink-0 rounded-full object-cover"
      />
    );
  }

  return (
    <div className="flex h-[72px] w-[72px] shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-dark">
      <span className="text-h3 font-bold text-white">{initials}</span>
    </div>
  );
}

// ── Availability badge ──────────────────────────────────────

function AvailabilityBadge({ doctor }: { doctor: Doctor }) {
  const { t } = useTranslation();

  if (!doctor.next_available_slot) {
    return <Badge variant="neutral">{t("doctor.noAvailable")}</Badge>;
  }

  const slotDate = new Date(doctor.next_available_slot);
  const now = new Date();
  const isToday =
    slotDate.getFullYear() === now.getFullYear() &&
    slotDate.getMonth() === now.getMonth() &&
    slotDate.getDate() === now.getDate();

  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const isTomorrow =
    slotDate.getFullYear() === tomorrow.getFullYear() &&
    slotDate.getMonth() === tomorrow.getMonth() &&
    slotDate.getDate() === tomorrow.getDate();

  const time = slotDate.toLocaleTimeString("uz-UZ", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  if (isToday) {
    return (
      <Badge variant="success">
        {t("days.today")} {time} {t("doctor.nextAvailableShort", { defaultValue: "bo'sh" })}
      </Badge>
    );
  }

  if (isTomorrow) {
    return (
      <Badge variant="warning">
        {t("days.tomorrow")} {time} {t("doctor.nextAvailableShort", { defaultValue: "bo'sh" })}
      </Badge>
    );
  }

  return <Badge variant="neutral">{t("doctor.noAvailable")}</Badge>;
}

// ── Doctor card ─────────────────────────────────────────────

interface DoctorCardProps {
  doctor: Doctor;
  index: number;
  onSelect: () => void;
}

function DoctorCard({ doctor, index, onSelect }: DoctorCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: 0.15 + index * 0.06,
        duration: 0.4,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.97 }}
      onClick={onSelect}
      className={cn(
        "group relative flex w-full items-center gap-5 rounded-card bg-white p-6 text-left shadow-card",
        "transition-shadow duration-200 hover:shadow-card-hover",
        "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/40 focus-visible:ring-offset-4",
      )}
    >
      {/* Teal left border on hover */}
      <motion.div
        className="absolute left-0 top-4 bottom-4 w-1 rounded-full bg-primary"
        initial={{ scaleY: 0 }}
        whileHover={{ scaleY: 1 }}
        transition={{ duration: 0.2 }}
        style={{ originY: 0.5 }}
      />

      {/* Doctor avatar */}
      <DoctorAvatar doctor={doctor} />

      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="text-h3 tracking-heading text-text-primary">{doctor.full_name}</p>
        <p className="mt-1 text-body text-text-muted">{doctor.specialty}</p>
        <div className="mt-2">
          <AvailabilityBadge doctor={doctor} />
        </div>
      </div>

      {/* Chevron */}
      <ChevronRight className="h-5 w-5 shrink-0 text-text-muted opacity-40 transition-opacity group-hover:opacity-100" />
    </motion.button>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface DoctorSelectScreenProps {
  onSelectDoctor: (doctor: Doctor) => void;
  onBack: () => void;
}

export function DoctorSelectScreen({
  onSelectDoctor,
  onBack,
}: DoctorSelectScreenProps) {
  const { t } = useTranslation();
  const doctors = useSessionStore((s) => s.doctors);
  const currentDepartment = useSessionStore((s) => s.currentDepartment);
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 800 });

  // 5s loading timeout — show empty state instead of infinite spinner
  const [loadingTimedOut, setLoadingTimedOut] = useState(false);
  useEffect(() => {
    if (doctors.length > 0) { setLoadingTimedOut(false); return; }
    const timer = setTimeout(() => setLoadingTimedOut(true), 5000);
    return () => clearTimeout(timer);
  }, [doctors.length]);

  const responseText = aiMessage || t("doctor.subtitle", { department: currentDepartment?.name ?? "" });

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* ── Header ── */}
      <HeaderBar title={t("doctor.title")} />

      {/* ── Department badge ── */}
      {currentDepartment && (
        <div className="px-8 pb-3">
          <motion.span
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15, duration: 0.3 }}
            className="inline-flex items-center gap-2 rounded-full bg-primary-50 px-4 py-2 text-caption font-semibold text-primary"
          >
            {currentDepartment.name}
          </motion.span>
        </div>
      )}

      {/* ── AI prompt bar ── */}
      <div className="px-8 pb-4">
        <AIPromptBar
          message={responseText}
          avatarState={voice.avatarState}
          voiceState={voice.voiceState}
          onVoiceClick={voice.toggleMic}
        />
      </div>

      {/* ── Doctor cards ── */}
      <div className="flex-1 overflow-y-auto px-8 pb-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {doctors.length > 0 ? (
            <div className="flex flex-col gap-4">
              {doctors.map((doc, i) => (
                <DoctorCard
                  key={doc.id}
                  doctor={doc}
                  index={i}
                  onSelect={() => { sounds.tap(); onSelectDoctor(doc); }}
                />
              ))}
            </div>
          ) : loadingTimedOut ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center gap-4 py-16"
            >
              <p className="text-body text-text-muted">{t("loading.notFound", { defaultValue: "Ma'lumot topilmadi" })}</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => { setLoadingTimedOut(false); onBack(); }}
                iconLeft={<RefreshCw className="h-4 w-4" />}
              >
                {t("common.retry", { defaultValue: "Qayta urinish" })}
              </Button>
            </motion.div>
          ) : (
            <LoadingMessage message={t("loading.doctors")} />
          )}
        </AnimatePresence>
      </div>

      {/* ── Bottom nav ── */}
      <BottomNav onBack={onBack} />
    </motion.div>
  );
}
