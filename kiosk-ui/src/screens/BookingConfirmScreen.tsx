import { useState, useCallback, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  Calendar,
  Clock,
  Stethoscope,
  Timer,
  Banknote,
  Camera,
  Delete,
} from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Divider } from "../components/ui/Divider";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { SuccessAnimation } from "../components/feedback/SuccessAnimation";
import { ConfettiEffect } from "../components/feedback/ConfettiEffect";
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
                : "bg-white text-text-primary shadow-card hover:shadow-card-hover",
            )}
          >
            {key === "⌫" ? <Delete className="h-6 w-6" /> : key}
          </motion.button>
        );
      })}
    </div>
  );
}

// ── Phone input with prefix ─────────────────────────────────

interface PhoneInputProps {
  value: string;
  onChange: (val: string) => void;
}

function PhoneInput({ value, onChange }: PhoneInputProps) {
  const { t } = useTranslation();

  const formatted = useMemo(() => {
    // Format: XX XXX XX XX
    const digits = value.replace(/\D/g, "");
    const parts: string[] = [];
    if (digits.length > 0) parts.push(digits.slice(0, 2));
    if (digits.length > 2) parts.push(digits.slice(2, 5));
    if (digits.length > 5) parts.push(digits.slice(5, 7));
    if (digits.length > 7) parts.push(digits.slice(7, 9));
    return parts.join(" ");
  }, [value]);

  return (
    <div className="flex flex-col gap-2">
      <label className="text-caption font-semibold text-text-body">
        {t("common.phone")}
      </label>
      <div className="flex h-touch-md items-center rounded-input border border-border bg-white px-4">
        <span className="mr-3 text-body text-text-muted">+998</span>
        <span className="text-[24px] font-semibold tracking-wider text-text-primary">
          {formatted || (
            <span className="text-text-muted">__ ___ __ __</span>
          )}
        </span>
      </div>
      <NumPad
        onDigit={(d) => {
          if (value.length < 9) onChange(value + d);
        }}
        onBackspace={() => onChange(value.slice(0, -1))}
        onClear={() => onChange("")}
      />
    </div>
  );
}

// ── Registration form ───────────────────────────────────────

interface RegistrationFormProps {
  onSubmit: (name: string, phone: string, dob: string) => void;
}

function RegistrationForm({ onSubmit }: RegistrationFormProps) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [dob, setDob] = useState("");

  const isValid = name.trim().length >= 3 && phone.length === 9;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 30 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="rounded-card bg-white p-7 shadow-card"
    >
      <h2 className="mb-6 text-h2 tracking-heading text-text-primary">
        {t("booking.register")}
      </h2>

      <div className="flex flex-col gap-5">
        <Input
          label={t("common.name")}
          placeholder={t("booking.namePlaceholder")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />

        <PhoneInput value={phone} onChange={setPhone} />

        <Input
          label={t("booking.dateOfBirth")}
          type="date"
          value={dob}
          onChange={(e) => setDob(e.target.value)}
        />
      </div>

      <Button
        variant="primary"
        size="lg"
        className="mt-6 w-full"
        disabled={!isValid}
        onClick={() => onSubmit(name, phone, dob)}
      >
        {t("common.next")}
      </Button>
    </motion.div>
  );
}

// ── Confirmation summary ────────────────────────────────────

interface ConfirmDetailRowProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

function ConfirmDetailRow({ icon, label, value }: ConfirmDetailRowProps) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-primary">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-caption text-text-muted">{label}</p>
        <p className="text-body font-semibold text-text-primary">{value}</p>
      </div>
    </div>
  );
}

// ── Face consent ────────────────────────────────────────────

interface FaceConsentProps {
  enabled: boolean;
  onToggle: (val: boolean) => void;
}

function FaceConsent({ enabled, onToggle }: FaceConsentProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-start gap-4 rounded-xl bg-primary-50 p-4">
      <Camera className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
        <p className="text-body text-text-primary">{t("booking.faceConsentLabel")}</p>
        <p className="mt-1 text-caption text-text-muted">{t("booking.faceConsentNote")}</p>
      </div>
      <motion.button
        whileTap={{ scale: 0.95 }}
        onClick={() => onToggle(!enabled)}
        className={cn(
          "relative h-7 w-12 shrink-0 rounded-full transition-colors duration-200",
          enabled ? "bg-primary" : "bg-slate-300",
        )}
      >
        <motion.div
          className="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-sm"
          animate={{ left: enabled ? 22 : 2 }}
          transition={{ type: "spring" as const, stiffness: 500, damping: 30 }}
        />
      </motion.button>
    </div>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface BookingConfirmScreenProps {
  onConfirm: () => void;
  onCancel: () => void;
  onBack: () => void;
}

export function BookingConfirmScreen({
  onConfirm,
  onCancel,
  onBack,
}: BookingConfirmScreenProps) {
  const { t } = useTranslation();
  const patient = useSessionStore((s) => s.patient);
  const currentDoctor = useSessionStore((s) => s.currentDoctor);
  const currentService = useSessionStore((s) => s.currentService);
  const selectedSlot = useSessionStore((s) => s.selectedSlot);
  const selectedDate = useSessionStore((s) => s.selectedDate);
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 800 });

  const [isNewPatient] = useState(patient === null);
  const [registered, setRegistered] = useState(false);
  const [faceConsent, setFaceConsent] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const handleRegister = useCallback(
    (_name: string, _phone: string, _dob: string) => {
      // In production, this would call registerPatient API
      setRegistered(true);
    },
    [],
  );

  const confirmingRef = useRef(false);
  const handleConfirm = useCallback(() => {
    if (confirmingRef.current) return;
    confirmingRef.current = true;
    setConfirming(true);
    // Simulate confirmation delay
    setTimeout(() => {
      setConfirming(false);
      setConfirmed(true);
      sounds.success();
      // Navigate after success animation
      setTimeout(() => {
        onConfirm();
      }, 2000);
    }, 1500);
  }, [onConfirm]);

  const showRegistration = isNewPatient && !registered;

  // Format date for display
  const dateDisplay = useMemo(() => {
    if (!selectedDate) return "";
    const date = new Date(selectedDate);
    const dayNames = [
      t("days.sunday"),
      t("days.monday"),
      t("days.tuesday"),
      t("days.wednesday"),
      t("days.thursday"),
      t("days.friday"),
      t("days.saturday"),
    ];
    const monthKeys = [
      "months.january", "months.february", "months.march", "months.april",
      "months.may", "months.june", "months.july", "months.august",
      "months.september", "months.october", "months.november", "months.december",
    ];
    return `${dayNames[date.getDay()] ?? ""}, ${date.getDate()}-${t(monthKeys[date.getMonth()] ?? "months.january").toLowerCase()} ${date.getFullYear()}`;
  }, [selectedDate, t]);

  const timeDisplay = useMemo(() => {
    if (!selectedSlot) return "";
    return `${selectedSlot.start_time.slice(0, 5)} — ${selectedSlot.end_time.slice(0, 5)}`;
  }, [selectedSlot]);

  const priceFormatted = currentService
    ? `${new Intl.NumberFormat("uz-UZ").format(currentService.price_uzs)} ${t("common.somCurrency")}`
    : "";

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Confetti on success */}
      {confirmed && <ConfettiEffect active />}

      {/* Header */}
      <HeaderBar title={t("booking.title")} />

      {/* ── AI prompt bar ── */}
      <div className="px-8 pb-4">
        <AIPromptBar
          message={aiMessage || t("booking.title")}
          avatarState={voice.avatarState}
          voiceState={voice.voiceState}
          onVoiceClick={voice.toggleMic}
        />
      </div>

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto px-8 pb-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {/* Success state */}
          {confirmed ? (
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
                {t("booking.success")}
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="mt-3 text-body-lg text-text-muted"
              >
                {t("booking.successDesc")}
              </motion.p>
            </motion.div>
          ) : showRegistration ? (
            /* Registration form for new patients */
            <motion.div key="register" className="mx-auto max-w-md py-4">
              <RegistrationForm onSubmit={handleRegister} />
            </motion.div>
          ) : (
            /* Confirmation summary */
            <motion.div
              key="confirm"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="mx-auto max-w-lg"
            >
              {/* Doctor header */}
              <div className="mb-6 flex flex-col items-center">
                {currentDoctor?.photo_url ? (
                  <img
                    src={currentDoctor.photo_url}
                    alt={currentDoctor.full_name}
                    className="h-20 w-20 rounded-full object-cover shadow-card"
                  />
                ) : currentDoctor ? (
                  <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-dark shadow-card">
                    <span className="text-h2 font-bold text-white">
                      {currentDoctor.full_name
                        .split(" ")
                        .map((w) => w[0])
                        .slice(0, 2)
                        .join("")
                        .toUpperCase()}
                    </span>
                  </div>
                ) : null}
                {currentDoctor && (
                  <>
                    <h2 className="mt-4 text-h2 tracking-heading text-text-primary">
                      {currentDoctor.full_name}
                    </h2>
                    <p className="mt-1 text-body text-text-muted">{currentDoctor.specialty}</p>
                  </>
                )}
              </div>

              <Divider className="mb-6" />

              {/* Detail rows */}
              <div className="flex flex-col gap-5">
                <ConfirmDetailRow
                  icon={<Calendar className="h-5 w-5" />}
                  label={t("booking.date")}
                  value={dateDisplay}
                />
                <ConfirmDetailRow
                  icon={<Clock className="h-5 w-5" />}
                  label={t("booking.time")}
                  value={timeDisplay}
                />
                {currentService && (
                  <>
                    <ConfirmDetailRow
                      icon={<Stethoscope className="h-5 w-5" />}
                      label={t("booking.service")}
                      value={currentService.name}
                    />
                    <ConfirmDetailRow
                      icon={<Timer className="h-5 w-5" />}
                      label={t("booking.duration")}
                      value={`${currentService.duration_minutes} ${t("booking.minutes")}`}
                    />
                    <ConfirmDetailRow
                      icon={<Banknote className="h-5 w-5" />}
                      label={t("booking.price")}
                      value={priceFormatted}
                    />
                  </>
                )}
              </div>

              {/* Face consent for new patients */}
              {isNewPatient && registered && (
                <>
                  <Divider className="my-6" />
                  <FaceConsent enabled={faceConsent} onToggle={setFaceConsent} />
                </>
              )}

              <Divider className="my-6" />

              {/* Action buttons */}
              <div className="flex flex-col gap-3">
                <Button
                  variant="primary"
                  size="lg"
                  className="w-full bg-success hover:bg-green-600"
                  onClick={handleConfirm}
                  loading={confirming}
                  disabled={confirming}
                >
                  {t("booking.confirm")} ✓
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-danger"
                  onClick={onCancel}
                  disabled={confirming}
                >
                  {t("booking.cancel")}
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom navigation */}
      <BottomNav onBack={onBack} backDisabled={confirming || confirmed} />
    </motion.div>
  );
}
