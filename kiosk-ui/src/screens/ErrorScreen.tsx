import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";

// ── Countdown bar ───────────────────────────────────────────

function CountdownBar({
  duration,
  onComplete,
}: {
  duration: number;
  onComplete: () => void;
}) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const start = performance.now();

    function tick() {
      const elapsed = performance.now() - start;
      const p = Math.min(elapsed / (duration * 1000), 1);
      setProgress(p);
      if (p < 1) {
        requestAnimationFrame(tick);
      } else {
        onComplete();
      }
    }

    requestAnimationFrame(tick);
  }, [duration, onComplete]);

  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-slate-200">
      <motion.div
        className="h-full rounded-full bg-amber-500"
        style={{ width: `${progress * 100}%` }}
      />
    </div>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface ErrorScreenProps {
  error?: string;
  onRetry: () => void;
  onCallStaff: () => void;
  onAutoReset: () => void;
}

export function ErrorScreen({
  error,
  onRetry,
  onCallStaff,
  onAutoReset,
}: ErrorScreenProps) {
  const { t } = useTranslation();

  const handleAutoReset = useCallback(() => {
    onAutoReset();
  }, [onAutoReset]);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <HeaderBar title="" />

      {/* ── Center content ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-12">
        {/* Warning icon */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{
            type: "spring" as const,
            stiffness: 200,
            damping: 15,
            delay: 0.1,
          }}
          className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-amber-50"
        >
          <AlertTriangle className="h-12 w-12 text-amber-500" />
        </motion.div>

        {/* Error message */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-center text-h1 tracking-heading text-text-primary"
        >
          {t("error.unknown").replace(".", "")}
        </motion.h1>

        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-3 max-w-md text-center text-body text-text-muted"
          >
            {error}
          </motion.p>
        )}

        {/* Action buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="mt-10 flex w-full max-w-xs flex-col gap-3"
        >
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={onRetry}
          >
            {t("common.retry")}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            className="w-full"
            onClick={onCallStaff}
          >
            {t("intent.complaint")}
          </Button>
        </motion.div>
      </div>

      {/* ── Bottom with auto-reset countdown ── */}
      <div className="px-12 pb-8">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mb-3 text-center text-caption text-text-muted"
        >
          {t("farewell.redirecting")}
        </motion.p>
        <CountdownBar duration={30} onComplete={handleAutoReset} />
      </div>
    </motion.div>
  );
}
