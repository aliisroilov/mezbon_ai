import { useState, useCallback, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  ChevronRight,
  CreditCard,
  Banknote,
  QrCode,
  X,
} from "lucide-react";
import { SuccessAnimation } from "../components/feedback/SuccessAnimation";
import { ConfettiEffect } from "../components/feedback/ConfettiEffect";
import { LoadingDots } from "../components/feedback/LoadingDots";
import { ErrorShake } from "../components/feedback/ErrorShake";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { useSessionStore } from "../store/sessionStore";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";

// ── Payment method card ─────────────────────────────────────

type MethodId = "uzcard" | "humo" | "click" | "payme" | "cash";

interface PaymentMethodConfig {
  id: MethodId;
  nameKey: string;
  subtitle: string;
  color: string;
  bgColor: string;
  icon: React.ReactNode;
}

const PAYMENT_METHODS: PaymentMethodConfig[] = [
  {
    id: "uzcard",
    nameKey: "payment.uzcard",
    subtitle: "Karta orqali",
    color: "#1E40AF",
    bgColor: "bg-blue-50",
    icon: <CreditCard className="h-6 w-6" />,
  },
  {
    id: "humo",
    nameKey: "payment.humo",
    subtitle: "Karta orqali",
    color: "#059669",
    bgColor: "bg-green-50",
    icon: <CreditCard className="h-6 w-6" />,
  },
  {
    id: "click",
    nameKey: "payment.click",
    subtitle: "QR kod",
    color: "#2563EB",
    bgColor: "bg-blue-50",
    icon: <QrCode className="h-6 w-6" />,
  },
  {
    id: "payme",
    nameKey: "payment.payme",
    subtitle: "QR kod",
    color: "#1B3A6B",
    bgColor: "bg-primary-50",
    icon: <QrCode className="h-6 w-6" />,
  },
  {
    id: "cash",
    nameKey: "payment.cash",
    subtitle: "Kassaga murojaat qiling",
    color: "#92400E",
    bgColor: "bg-amber-50",
    icon: <Banknote className="h-6 w-6" />,
  },
];

interface MethodCardProps {
  method: PaymentMethodConfig;
  index: number;
  onSelect: () => void;
}

function MethodCard({ method, index, onSelect }: MethodCardProps) {
  const { t } = useTranslation();

  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{
        delay: 0.1 + index * 0.06,
        duration: 0.4,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileTap={{ scale: 0.97 }}
      onClick={onSelect}
      className={cn(
        "group flex w-full items-center gap-5 rounded-card p-5 text-left transition-shadow duration-200",
        "bg-white shadow-card hover:shadow-card-hover",
      )}
    >
      <div
        className={cn(
          "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
          method.bgColor,
        )}
        style={{ color: method.color }}
      >
        {method.icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-h3 tracking-heading text-text-primary">
          {t(method.nameKey)}
        </p>
        <p className="text-caption text-text-muted">{method.subtitle}</p>
      </div>
      <ChevronRight className="h-5 w-5 shrink-0 text-text-muted opacity-40 transition-opacity group-hover:opacity-100" />
    </motion.button>
  );
}

// ── QR Payment view ─────────────────────────────────────────

interface QRPaymentViewProps {
  method: PaymentMethodConfig;
  amount: string;
  onCancel: () => void;
}

function QRPaymentView({ method, amount, onCancel }: QRPaymentViewProps) {
  const { t } = useTranslation();
  const [timeLeft, setTimeLeft] = useState(120);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onCancel();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [onCancel]);

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center"
    >
      {/* Selected method badge */}
      <div
        className={cn(
          "mb-6 inline-flex items-center gap-2 rounded-full px-4 py-2 text-caption font-semibold",
          method.bgColor,
        )}
        style={{ color: method.color }}
      >
        {method.icon}
        {t(method.nameKey)}
      </div>

      {/* Amount */}
      <p className="mb-8 text-h2 font-bold text-text-primary">{amount}</p>

      {/* QR Code placeholder with animated border */}
      <motion.div
        className="relative rounded-2xl bg-white p-6 shadow-card"
        animate={{
          boxShadow: [
            "0 0 0 2px rgba(30,42,110,0.2)",
            "0 0 0 4px rgba(30,42,110,0.1)",
            "0 0 0 2px rgba(30,42,110,0.2)",
          ],
        }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="flex h-[280px] w-[280px] items-center justify-center rounded-xl bg-slate-50">
          <div className="grid grid-cols-5 gap-1.5">
            {Array.from({ length: 25 }).map((_, i) => (
              <motion.div
                key={i}
                className="h-10 w-10 rounded-sm bg-slate-800"
                initial={{ opacity: 0 }}
                animate={{ opacity: Math.random() > 0.3 ? 1 : 0.2 }}
                transition={{ delay: i * 0.02 }}
              />
            ))}
          </div>
        </div>
      </motion.div>

      {/* Scan instruction */}
      <p className="mt-6 text-body text-text-muted">
        {t("payment.scanQR")}
      </p>

      {/* Timer */}
      <motion.p
        className="mt-3 text-h3 font-semibold tabular-nums text-text-primary"
        animate={timeLeft <= 30 ? { color: ["#0F172A", "#EF4444", "#0F172A"] } : undefined}
        transition={timeLeft <= 30 ? { duration: 1, repeat: Infinity } : undefined}
      >
        {minutes}:{String(seconds).padStart(2, "0")}
      </motion.p>

      {/* Cancel */}
      <Button
        variant="ghost"
        size="sm"
        className="mt-4 text-danger"
        onClick={onCancel}
      >
        {t("common.cancel")}
      </Button>
    </motion.div>
  );
}

// ── Main screen ─────────────────────────────────────────────

type PaymentPhase = "select" | "qr" | "processing" | "success" | "failed";

interface PaymentScreenProps {
  onSuccess: () => void;
  onBack: () => void;
}

export function PaymentScreen({ onSuccess, onBack }: PaymentScreenProps) {
  const { t } = useTranslation();
  const currentService = useSessionStore((s) => s.currentService);
  const currentAppointment = useSessionStore((s) => s.currentAppointment);

  const [phase, setPhase] = useState<PaymentPhase>("select");
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethodConfig | null>(null);
  const [errorShake, setErrorShake] = useState(false);

  const amount = currentService?.price_uzs ?? 0;
  const amountFormatted = useMemo(
    () =>
      `${new Intl.NumberFormat("uz-UZ").format(amount)} ${t("common.somCurrency")}`,
    [amount, t],
  );
  const serviceName =
    currentService?.name ?? currentAppointment?.service_name ?? "";

  const handleSelectMethod = useCallback(
    (method: PaymentMethodConfig) => {
      setSelectedMethod(method);
      if (method.id === "cash") {
        // Cash — just mark success
        setPhase("processing");
        setTimeout(() => {
          setPhase("success");
          sounds.success();
          setTimeout(() => onSuccess(), 3000);
        }, 1500);
      } else {
        setPhase("qr");
        // Simulate payment after 5 seconds
        setTimeout(() => {
          setPhase("processing");
          setTimeout(() => {
            // 80% success, 20% failure for demo
            if (Math.random() > 0.2) {
              setPhase("success");
              sounds.success();
              setTimeout(() => onSuccess(), 3000);
            } else {
              setPhase("failed");
              sounds.error();
              setErrorShake(true);
              setTimeout(() => setErrorShake(false), 500);
            }
          }, 2000);
        }, 5000);
      }
    },
    [onSuccess],
  );

  const handleRetry = useCallback(() => {
    setPhase("select");
    setSelectedMethod(null);
    setErrorShake(false);
  }, []);

  const handleOtherMethod = useCallback(() => {
    setPhase("select");
    setSelectedMethod(null);
  }, []);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Confetti on success */}
      <ConfettiEffect active={phase === "success"} />

      {/* Header */}
      <HeaderBar title={t("payment.title")} />

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto px-12 pb-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {/* ── Select payment method ── */}
          {phase === "select" && (
            <motion.div
              key="select"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-auto max-w-lg"
            >
              {/* Amount card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="mb-8 rounded-card bg-white p-7 text-center shadow-card"
              >
                <p className="text-body text-text-muted">
                  {t("payment.amount")}
                </p>
                <p className="mt-2 text-display font-extrabold text-text-primary">
                  {amountFormatted}
                </p>
                <p className="mt-1 text-body text-text-muted">{serviceName}</p>
              </motion.div>

              {/* Methods */}
              <p className="mb-4 text-h3 text-text-primary">
                {t("payment.subtitle")}
              </p>
              <div className="flex flex-col gap-4">
                {PAYMENT_METHODS.map((method, i) => (
                  <MethodCard
                    key={method.id}
                    method={method}
                    index={i}
                    onSelect={() => handleSelectMethod(method)}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* ── QR view ── */}
          {phase === "qr" && selectedMethod && (
            <motion.div
              key="qr"
              className="mx-auto max-w-lg py-4"
            >
              <QRPaymentView
                method={selectedMethod}
                amount={amountFormatted}
                onCancel={handleOtherMethod}
              />
            </motion.div>
          )}

          {/* ── Processing ── */}
          {phase === "processing" && (
            <motion.div
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-20"
            >
              <LoadingDots className="mb-6" color="bg-primary" />
              <p className="text-body-lg text-text-muted">
                {t("loading.payment")}
              </p>
            </motion.div>
          )}

          {/* ── Success ── */}
          {phase === "success" && (
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
                className="mt-8 text-h1 tracking-heading text-success"
              >
                {t("payment.success")}
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="mt-3 text-h2 font-bold text-text-primary"
              >
                {amountFormatted}
              </motion.p>
            </motion.div>
          )}

          {/* ── Failed ── */}
          {phase === "failed" && (
            <ErrorShake trigger={errorShake}>
              <motion.div
                key="failed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-16"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{
                    type: "spring" as const,
                    stiffness: 200,
                    damping: 15,
                  }}
                  className="flex h-24 w-24 items-center justify-center rounded-full bg-red-50"
                >
                  <X className="h-12 w-12 text-danger" />
                </motion.div>

                <h2 className="mt-6 text-h2 tracking-heading text-danger">
                  {t("payment.failed")}
                </h2>
                <p className="mt-2 text-body text-text-muted">
                  {t("error.paymentFailed")}
                </p>

                <div className="mt-8 flex flex-col gap-3 w-full max-w-xs">
                  <Button
                    variant="primary"
                    size="lg"
                    className="w-full"
                    onClick={handleRetry}
                  >
                    {t("payment.retry")}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full"
                    onClick={handleOtherMethod}
                  >
                    {t("payment.subtitle")}
                  </Button>
                </div>
              </motion.div>
            </ErrorShake>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom navigation */}
      <BottomNav onBack={onBack} backDisabled={phase !== "select"} />
    </motion.div>
  );
}
