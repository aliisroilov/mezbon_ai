import { motion, AnimatePresence, LayoutGroup } from "framer-motion";
import { Mic, MicOff, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/cn";

export type VoiceState = "inactive" | "listening" | "processing" | "speaking" | "error";

interface VoiceIndicatorProps {
  state?: VoiceState;
  /** Audio volume 0-1 for sound bar animation when listening */
  audioLevel?: number;
  /** Error message to show (overrides default) */
  errorMessage?: string;
  /** Countdown seconds for error auto-retry */
  retryCountdown?: number;
  onClick?: () => void;
  className?: string;
}

// ── Micro sound bars next to mic ────────────────────────────

function MiniSoundBars({ audioLevel = 0 }: { audioLevel: number }) {
  return (
    <div className="flex items-center gap-[3px]">
      {[0, 1, 2, 3].map((i) => {
        const base = 6 + i * 2;
        const height = base + audioLevel * 14;
        return (
          <motion.div
            key={i}
            className="w-[3px] rounded-full bg-primary"
            animate={
              audioLevel > 0
                ? { height }
                : { height: [base, base + 8, base] }
            }
            transition={
              audioLevel > 0
                ? { duration: 0.06, ease: "linear" }
                : { duration: 0.5, repeat: Infinity, delay: i * 0.1, ease: "easeInOut" }
            }
          />
        );
      })}
    </div>
  );
}

// ── Pulsing dots for loading ─────────────────────────────────

function AnimatedDots() {
  return (
    <span className="inline-flex gap-[3px]">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="inline-block h-1 w-1 rounded-full bg-current"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </span>
  );
}

// ── Mini waveform for speaking ───────────────────────────────

function SpeakingWave() {
  return (
    <div className="flex items-center gap-[2px]">
      {[0, 1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          className="w-[2.5px] rounded-full bg-primary"
          animate={{ height: [4, 12, 4] }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.08,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

// ── Icon per state ───────────────────────────────────────────

function StateIcon({ state }: { state: VoiceState }) {
  const iconClass = "h-5 w-5 shrink-0";

  switch (state) {
    case "inactive":
      return <MicOff className={cn(iconClass, "text-text-muted")} />;
    case "listening":
      return <Mic className={cn(iconClass, "text-primary")} />;
    case "processing":
      return <Mic className={cn(iconClass, "text-accent")} />;
    case "speaking":
      return <Mic className={cn(iconClass, "text-primary")} />;
    case "error":
      return <AlertCircle className={cn(iconClass, "text-danger")} />;
  }
}

// ── Main component ───────────────────────────────────────────

export function VoiceIndicator({
  state = "inactive",
  audioLevel = 0,
  errorMessage,
  retryCountdown,
  onClick,
  className,
}: VoiceIndicatorProps) {
  const { t } = useTranslation();

  const bgClass = cn(
    "bg-white/90 backdrop-blur-md border",
    state === "error" ? "border-danger/20" : "border-border",
    state === "inactive" && "opacity-60",
  );

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      {/* Ripple rings behind for listening */}
      {state === "listening" && (
        <>
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute rounded-full border border-primary/20"
              style={{ width: 56, height: 56 }}
              animate={{ scale: [1, 2.4], opacity: [0.4, 0] }}
              transition={{
                duration: 2,
                repeat: Infinity,
                delay: i * 0.5,
                ease: "easeOut",
              }}
            />
          ))}
        </>
      )}

      <LayoutGroup>
        <motion.button
          layout
          onClick={onClick}
          aria-label={
            state === "inactive"
              ? t("voice.tapToSpeak")
              : state === "listening"
                ? t("accessibility.stopRecording")
                : undefined
          }
          className={cn(
            "relative z-10 flex h-14 items-center gap-3 rounded-full px-5",
            "shadow-card transition-colors duration-200",
            bgClass,
            onClick && "cursor-pointer active:scale-95",
          )}
          whileTap={onClick ? { scale: 0.95 } : undefined}
          transition={{ layout: { type: "spring" as const, stiffness: 300, damping: 25 } }}
        >
          {/* Icon */}
          <motion.div layout="position">
            <StateIcon state={state} />
          </motion.div>

          {/* Sound bars next to mic for listening */}
          <AnimatePresence>
            {state === "listening" && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
              >
                <MiniSoundBars audioLevel={audioLevel} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Speaking waveform */}
          <AnimatePresence>
            {state === "speaking" && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
              >
                <SpeakingWave />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Status text */}
          <AnimatePresence mode="wait">
            <motion.span
              key={state}
              layout="position"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 8 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "whitespace-nowrap text-[15px] font-medium",
                state === "inactive" && "text-text-muted",
                state === "listening" && "text-primary",
                state === "processing" && "text-accent",
                state === "speaking" && "text-primary",
                state === "error" && "text-danger",
              )}
            >
              {state === "inactive" && t("voice.tapToSpeak")}
              {state === "listening" && (
                <span className="flex items-center gap-1">
                  {t("voice.listening").replace("...", "")}
                  <AnimatedDots />
                </span>
              )}
              {state === "processing" && (
                <span className="flex items-center gap-1">
                  {t("voice.processing").replace("...", "")}
                  <AnimatedDots />
                </span>
              )}
              {state === "speaking" && t("voice.speaking").replace("...", "")}
              {state === "error" && (
                <span className="flex items-center gap-1">
                  {errorMessage || t("voice.error")}
                  {retryCountdown != null && (
                    <span className="tabular-nums text-[13px]">({retryCountdown}s)</span>
                  )}
                </span>
              )}
            </motion.span>
          </AnimatePresence>
        </motion.button>
      </LayoutGroup>
    </div>
  );
}
