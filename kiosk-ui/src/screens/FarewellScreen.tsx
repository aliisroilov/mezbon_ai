import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";

// ── Rating button ───────────────────────────────────────────

interface RatingButtonProps {
  emoji: string;
  label: string;
  isSelected: boolean;
  isOther: boolean;
  onSelect: () => void;
}

function RatingButton({
  emoji,
  label,
  isSelected,
  isOther,
  onSelect,
}: RatingButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.95 }}
      animate={
        isSelected
          ? { scale: 1.15, opacity: 1 }
          : isOther
            ? { scale: 0.9, opacity: 0.4 }
            : { scale: 1, opacity: 1 }
      }
      transition={{
        type: "spring" as const,
        stiffness: 300,
        damping: 20,
      }}
      onClick={onSelect}
      className={cn(
        "flex flex-col items-center gap-2 rounded-2xl p-4 transition-colors duration-200",
        isSelected
          ? "bg-primary-50"
          : "hover:bg-slate-50",
      )}
    >
      <span className="text-[72px] leading-none">{emoji}</span>
      <span
        className={cn(
          "text-caption font-medium",
          isSelected ? "text-primary" : "text-text-muted",
        )}
      >
        {label}
      </span>
    </motion.button>
  );
}

// ── Progress bar ────────────────────────────────────────────

function CountdownBar({ duration, onComplete }: { duration: number; onComplete: () => void }) {
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
        className="h-full rounded-full bg-primary"
        style={{ width: `${progress * 100}%` }}
      />
    </div>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface FarewellScreenProps {
  onDone: () => void;
}

export function FarewellScreen({ onDone }: FarewellScreenProps) {
  const { t } = useTranslation();
  const [selectedRating, setSelectedRating] = useState<string | null>(null);
  const [showThankYou, setShowThankYou] = useState(false);

  const ratings = [
    { emoji: "\u{1F60A}", label: t("farewell.great"), value: "great" },
    { emoji: "\u{1F610}", label: t("farewell.okay"), value: "okay" },
    { emoji: "\u{1F61E}", label: t("farewell.poor"), value: "poor" },
  ];

  const handleRate = useCallback(
    (value: string) => {
      if (selectedRating) return;
      sounds.tap();
      setSelectedRating(value);
      setShowThankYou(true);
    },
    [selectedRating],
  );

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -30 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* ── Center content ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-12">
        {/* Success animation / icon */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{
            type: "spring" as const,
            stiffness: 200,
            damping: 15,
            delay: 0.2,
          }}
          className="mb-6 text-[80px] leading-none"
        >
          ✓
        </motion.div>

        {/* Main message */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4 }}
          className="text-center text-h1 tracking-heading text-text-primary"
        >
          {t("farewell.title")} {t("farewell.message")}
        </motion.h1>

        {/* Satisfaction rating */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.4 }}
          className="mt-12 flex flex-col items-center"
        >
          <AnimatePresence mode="wait">
            {showThankYou ? (
              <motion.p
                key="thanks"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-body-lg text-primary"
              >
                {t("farewell.thankYouRating")}
              </motion.p>
            ) : (
              <motion.div key="rate" className="flex flex-col items-center">
                <p className="mb-6 text-caption text-text-muted">
                  {t("farewell.rateExperience")}
                </p>
                <div className="flex gap-8">
                  {ratings.map((r) => (
                    <RatingButton
                      key={r.value}
                      emoji={r.emoji}
                      label={r.label}
                      isSelected={selectedRating === r.value}
                      isOther={
                        selectedRating !== null && selectedRating !== r.value
                      }
                      onSelect={() => handleRate(r.value)}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* ── Bottom with countdown ── */}
      <div className="px-12 pb-8">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mb-3 text-center text-caption text-text-muted"
        >
          {t("farewell.redirecting")}
        </motion.p>
        <CountdownBar duration={10} onComplete={onDone} />
      </div>
    </motion.div>
  );
}
