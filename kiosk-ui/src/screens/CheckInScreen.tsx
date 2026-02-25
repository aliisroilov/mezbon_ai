import { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  Calendar,
  Clock,
  Stethoscope,
  Delete,
} from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { SuccessAnimation } from "../components/feedback/SuccessAnimation";
import { LoadingDots } from "../components/feedback/LoadingDots";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";

// ── NumPad ──────────────────────────────────────────────────

interface NumPadProps {
  onDigit: (digit: string) => void;
  onBackspace: () => void;
  onClear: () => void;
}

function NumPad({ onDigit, onBackspace, onClear }: NumPadProps) {
  const keys = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["C", "0", "⌫"],
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {keys.flat().map((key) => {
        const isAction = key === "C" || key === "⌫";
        return (
          <motion.button
            key={key}
            whileTap={{ scale: 0.95 }}
            onClick={() => {
              if (key === "⌫") onBackspace();
              else if (key === "C") onClear();
              else onDigit(key);
            }}
            className={cn(
              "flex h-[72px] items-center justify-center rounded-2xl text-[28px] font-semibold transition-all duration-150",
              isAction
                ? key === "C"
                  ? "bg-red-50 text-danger"
                  : "bg-slate-100 text-text-body"
                : "bg-white text-text-primary shadow-card hover:shadow-card-hover active:bg-primary-50",
            )}
          >
            {key === "⌫" ? <Delete className="h-6 w-6" /> : key}
          </motion.button>
        );
      })}
    </div>
  );
}

// ── Phone display ───────────────────────────────────────────

function PhoneDisplay({ value }: { value: string }) {
  const formatted = useMemo(() => {
    const digits = value.replace(/\D/g, "");
    const parts: string[] = [];
    if (digits.length > 0) parts.push(digits.slice(0, 2));
    if (digits.length > 2) parts.push(digits.slice(2, 5));
    if (digits.length > 5) parts.push(digits.slice(5, 7));
    if (digits.length > 7) parts.push(digits.slice(7, 9));
    return parts.join(" ");
  }, [value]);

  return (
    <div className="flex h-touch-lg items-center justify-center rounded-card border border-border bg-white px-6">
      <span className="mr-3 text-h2 text-text-muted">+998</span>
      <span className="text-[40px] font-bold tracking-wider text-text-primary">
        {formatted || (
          <span className="text-text-muted">__ ___ __ __</span>
        )}
      </span>
    </div>
  );
}

// ── Appointment card ────────────────────────────────────────

function AppointmentCard() {
  const { t } = useTranslation();
  const currentDoctor = useSessionStore((s) => s.currentDoctor);
  const currentService = useSessionStore((s) => s.currentService);
  const currentAppointment = useSessionStore((s) => s.currentAppointment);

  const scheduledTime = useMemo(() => {
    if (!currentAppointment?.scheduled_at) return "";
    const d = new Date(currentAppointment.scheduled_at);
    return d.toLocaleTimeString("uz-UZ", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }, [currentAppointment]);

  const scheduledDate = useMemo(() => {
    if (!currentAppointment?.scheduled_at) return "";
    const d = new Date(currentAppointment.scheduled_at);
    return d.toLocaleDateString("uz-UZ", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }, [currentAppointment]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="rounded-card bg-white p-7 shadow-card"
    >
      {/* Doctor header */}
      <div className="mb-5 flex items-center gap-4">
        {currentDoctor?.photo_url ? (
          <img
            src={currentDoctor.photo_url}
            alt={currentDoctor.full_name}
            className="h-16 w-16 rounded-full object-cover shadow-sm"
          />
        ) : currentDoctor ? (
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-dark">
            <span className="text-h3 font-bold text-white">
              {currentDoctor.full_name
                .split(" ")
                .map((w) => w[0])
                .slice(0, 2)
                .join("")
                .toUpperCase()}
            </span>
          </div>
        ) : null}
        <div className="min-w-0 flex-1">
          <p className="text-h3 tracking-heading text-text-primary">
            {currentDoctor?.full_name ?? currentAppointment?.doctor_name ?? ""}
          </p>
          <p className="text-body text-text-muted">
            {currentDoctor?.specialty ?? ""}
          </p>
        </div>
        <Badge variant="info">{t("checkIn.appointmentFound")}</Badge>
      </div>

      {/* Detail rows */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Calendar className="h-5 w-5 text-primary" />
          <span className="text-body text-text-body">{scheduledDate}</span>
        </div>
        <div className="flex items-center gap-3">
          <Clock className="h-5 w-5 text-primary" />
          <span className="text-body text-text-body">{scheduledTime}</span>
        </div>
        {(currentService ?? currentAppointment) && (
          <div className="flex items-center gap-3">
            <Stethoscope className="h-5 w-5 text-primary" />
            <span className="text-body text-text-body">
              {currentService?.name ?? currentAppointment?.service_name ?? ""}
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface CheckInScreenProps {
  onCheckInComplete: () => void;
  onBookAppointment: () => void;
  onBack: () => void;
}

export function CheckInScreen({
  onCheckInComplete,
  onBookAppointment,
  onBack,
}: CheckInScreenProps) {
  const { t } = useTranslation();
  const patient = useSessionStore((s) => s.patient);
  const currentAppointment = useSessionStore((s) => s.currentAppointment);
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 800 });

  const isRecognized = patient !== null;
  const hasAppointment = currentAppointment !== null;

  const [phone, setPhone] = useState("");
  const [lookingUp, setLookingUp] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);
  const [checkedIn, setCheckedIn] = useState(false);

  const responseText = useMemo(() => {
    if (checkedIn) return t("checkIn.checkedIn");
    if (isRecognized && hasAppointment) {
      return t("greeting.knownPatient", { name: patient?.full_name ?? "" });
    }
    if (notFound) return t("checkIn.noAppointment");
    return t("checkIn.enterPhone");
  }, [checkedIn, isRecognized, hasAppointment, notFound, patient, t]);

  // Auto-lookup when 9 digits entered
  const handlePhoneChange = useCallback(
    (val: string) => {
      setPhone(val);
      setNotFound(false);
      if (val.length === 9) {
        setLookingUp(true);
        // Simulate API lookup
        setTimeout(() => {
          setLookingUp(false);
          // In production, this would check the backend
          // For now, simulate not found
          setNotFound(true);
        }, 1500);
      }
    },
    [],
  );

  const handleCheckIn = useCallback(() => {
    setCheckingIn(true);
    setTimeout(() => {
      setCheckingIn(false);
      setCheckedIn(true);
      sounds.success();
      setTimeout(() => {
        onCheckInComplete();
      }, 2000);
    }, 1500);
  }, [onCheckInComplete]);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* ── Header ── */}
      <HeaderBar title={t("checkIn.title")} />

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto px-8 pb-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {/* Success state */}
          {checkedIn ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center justify-center py-12"
            >
              <SuccessAnimation size={140} />
              <motion.h2
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="mt-8 text-h1 tracking-heading text-text-primary"
              >
                {t("checkIn.checkedIn")}
              </motion.h2>
            </motion.div>
          ) : (
            <motion.div
              key="checkin"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-auto max-w-lg"
            >
              {/* AI prompt area */}
              <div className="mb-6">
                <AIPromptBar
                  message={aiMessage || responseText}
                  avatarState={voice.avatarState}
                  voiceState={voice.voiceState}
                  onVoiceClick={voice.toggleMic}
                />
              </div>

              {/* Mode A: Recognized patient with appointment */}
              {isRecognized && hasAppointment && !checkedIn && (
                <div className="flex flex-col gap-6">
                  <AppointmentCard />
                  <Button
                    variant="primary"
                    size="lg"
                    className="w-full bg-success hover:bg-green-600"
                    onClick={handleCheckIn}
                    loading={checkingIn}
                    disabled={checkingIn}
                  >
                    {t("checkIn.confirmCheckIn")} ✓
                  </Button>
                </div>
              )}

              {/* Mode B: Not recognized — phone input */}
              {!isRecognized && !checkedIn && (
                <div className="flex flex-col gap-5">
                  <PhoneDisplay value={phone} />

                  {lookingUp ? (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center gap-3 py-6"
                    >
                      <LoadingDots />
                      <p className="text-body text-text-muted">
                        {t("loading.checkIn")}
                      </p>
                    </motion.div>
                  ) : notFound ? (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex flex-col items-center gap-4 py-4"
                    >
                      <p className="text-body text-text-muted">
                        {t("checkIn.noAppointment")}
                      </p>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={onBookAppointment}
                      >
                        {t("intent.bookAppointment")}
                      </Button>
                    </motion.div>
                  ) : (
                    <NumPad
                      onDigit={(d) => {
                        if (phone.length < 9) handlePhoneChange(phone + d);
                      }}
                      onBackspace={() =>
                        handlePhoneChange(phone.slice(0, -1))
                      }
                      onClear={() => handlePhoneChange("")}
                    />
                  )}

                  {/* If phone lookup found appointment, show it */}
                  {!lookingUp && hasAppointment && phone.length === 9 && (
                    <div className="flex flex-col gap-4">
                      <AppointmentCard />
                      <Button
                        variant="primary"
                        size="lg"
                        className="w-full bg-success hover:bg-green-600"
                        onClick={handleCheckIn}
                        loading={checkingIn}
                        disabled={checkingIn}
                      >
                        {t("checkIn.confirmCheckIn")} ✓
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Bottom nav ── */}
      <BottomNav onBack={onBack} backDisabled={checkingIn || checkedIn} />
    </motion.div>
  );
}
