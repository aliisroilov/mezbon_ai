import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { MapPin, Clock, ArrowUp } from "lucide-react";
import { SuccessAnimation } from "../components/feedback/SuccessAnimation";
import { CountUpNumber } from "../components/feedback/CountUpNumber";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { useSessionStore } from "../store/sessionStore";
import { printTicket } from "../utils/printer";
import { sounds } from "../utils/sounds";

// ── Queue position visualization ────────────────────────────

function QueueVisualization({ ahead, total }: { ahead: number; total: number }) {
  const dots = Math.min(total, 8);
  const yourIndex = ahead;

  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: dots }).map((_, i) => {
        const isFilled = i < yourIndex;
        const isYou = i === yourIndex;
        return (
          <motion.div
            key={i}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.8 + i * 0.08, duration: 0.3 }}
            className={
              isYou
                ? "h-4 w-4 rounded-full bg-amber-500"
                : isFilled
                  ? "h-3 w-3 rounded-full bg-primary"
                  : "h-3 w-3 rounded-full bg-slate-200"
            }
          >
            {isYou && (
              <motion.div
                className="h-4 w-4 rounded-full bg-amber-500"
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              />
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface QueueTicketScreenProps {
  onDone: () => void;
}

export function QueueTicketScreen({ onDone }: QueueTicketScreenProps) {
  const { t } = useTranslation();
  const queueTicket = useSessionStore((s) => s.queueTicket);
  const currentDepartment = useSessionStore((s) => s.currentDepartment);

  const [showDetails, setShowDetails] = useState(false);

  // Show details after ticket animation + play success sound
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowDetails(true);
      sounds.success();
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  // Auto-print queue ticket when it appears
  useEffect(() => {
    if (!queueTicket || !currentDepartment) return;

    const { deviceId, currentDoctor } = useSessionStore.getState();

    if (deviceId) {
      printTicket({
        ticketNumber: queueTicket.ticket_number,
        departmentName: departmentName,
        doctorName: currentDoctor?.full_name,
        date: new Date().toLocaleDateString("uz-UZ"),
        time: new Date().toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" }),
        roomNumber: String(room),
        floor: floor,
        estimatedWait: estimatedWait,
      });
    }
  }, [queueTicket, currentDepartment]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-navigate after 15 seconds
  useEffect(() => {
    const timer = setTimeout(() => onDone(), 15000);
    return () => clearTimeout(timer);
  }, [onDone]);

  // Extract numeric part for CountUpNumber
  const ticketNum = queueTicket?.ticket_number ?? "K-001";
  const ticketPrefix = ticketNum.replace(/\d+$/, "");
  const ticketNumber = parseInt(ticketNum.replace(/\D/g, ""), 10) || 1;

  const departmentName =
    queueTicket?.department_name ?? currentDepartment?.name ?? "";
  const floor = currentDepartment?.floor ?? 1;
  const room = currentDepartment?.room_number ?? "101";
  const estimatedWait = queueTicket?.estimated_wait_minutes ?? 8;
  const peopleAhead = Math.max(0, estimatedWait / 3);

  const handleDone = useCallback(() => {
    onDone();
  }, [onDone]);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <HeaderBar title={t("queue.title")} />

      {/* ── Center content ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-12">
        {/* "Your number" label */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="mb-4 text-h2 text-text-muted"
        >
          {t("queue.yourTicket")}
        </motion.p>

        {/* Ticket number with glow */}
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{
            type: "spring" as const,
            stiffness: 200,
            damping: 15,
            delay: 0.3,
          }}
          className="relative mb-6"
        >
          {/* Glow behind number */}
          <div
            className="absolute inset-0 -m-8 rounded-full"
            style={{
              background:
                "radial-gradient(circle, rgba(30,42,110,0.15) 0%, transparent 70%)",
            }}
          />
          <div className="relative text-[80px] font-extrabold leading-none text-primary">
            <CountUpNumber
              target={ticketNumber}
              duration={800}
              prefix={ticketPrefix}
              className="tabular-nums"
            />
          </div>
        </motion.div>

        {/* Success checkmark */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          <SuccessAnimation size={64} />
        </motion.div>

        {/* Info card */}
        <AnimatePresenceWrapper show={showDetails}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="mt-8 w-full max-w-md rounded-card bg-white p-6 shadow-card"
          >
            <div className="flex flex-col gap-4">
              {/* Department + room */}
              <div className="flex items-center gap-3">
                <MapPin className="h-5 w-5 shrink-0 text-primary" />
                <div>
                  <p className="text-body font-semibold text-text-primary">
                    {departmentName}
                  </p>
                  <p className="text-caption text-text-muted">
                    {t("department.floor", { floor })} •{" "}
                    {t("department.room", { room })}
                  </p>
                </div>
              </div>

              {/* Estimated wait */}
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 shrink-0 text-primary" />
                <p className="text-body text-text-body">
                  {t("queue.estimatedWait")}:{" "}
                  <span className="font-semibold">
                    {t("queue.minutes", { count: estimatedWait })}
                  </span>
                </p>
              </div>

              {/* Direction hint */}
              <div className="flex items-center gap-3 rounded-xl bg-primary-50 p-3">
                <ArrowUp className="h-5 w-5 shrink-0 text-primary" />
                <p className="text-caption font-medium text-primary">
                  {t("queue.goToRoom", { room: `${floor}-${t("department.floor", { floor })}, ${room}-${t("department.room", { room })}` })}
                </p>
              </div>
            </div>

            {/* Queue visualization */}
            <div className="mt-5 flex flex-col items-center gap-2">
              <p className="text-caption text-text-muted">
                {t("queue.peopleAhead", { count: Math.round(peopleAhead) })}
              </p>
              <QueueVisualization
                ahead={Math.round(peopleAhead)}
                total={Math.round(peopleAhead) + 3}
              />
            </div>
          </motion.div>
        </AnimatePresenceWrapper>
      </div>

      {/* ── Bottom ── */}
      <div className="px-12 pb-8">
        <p className="mb-4 text-center text-caption text-text-muted">
          {t("queue.yourTurn")}
        </p>
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          onClick={handleDone}
        >
          {t("common.ok")}
        </Button>
      </div>
    </motion.div>
  );
}

// Helper to avoid importing AnimatePresence just for conditional rendering
function AnimatePresenceWrapper({
  show,
  children,
}: {
  show: boolean;
  children: React.ReactNode;
}) {
  if (!show) return null;
  return <>{children}</>;
}
