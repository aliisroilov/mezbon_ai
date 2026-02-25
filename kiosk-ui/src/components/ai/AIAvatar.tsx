import { useEffect, useRef, useState, useMemo } from "react";
import { motion, AnimatePresence, useAnimation } from "framer-motion";
import { cn } from "../../lib/cn";

export type AvatarState = "idle" | "listening" | "speaking" | "thinking" | "success";

interface AIAvatarProps {
  state?: AvatarState;
  /** Float32Array from Web Audio API analyser for waveform visualization */
  audioData?: Float32Array | null;
  /** Pixel size of the avatar container. Defaults to OUTER_SIZE (200). */
  size?: number;
  className?: string;
}

// ── Constants ──────────────────────────────────────────────

const OUTER_SIZE = 200;
const MAIN_CIRCLE = 160;
const INNER_CIRCLE = 140;
const BAR_COUNT = 32;
const WAVE_BAR_RADIUS = 90;
const SOUND_BAR_COUNT = 4;
const SOUND_BAR_WIDTH = 4;
const SUCCESS_HOLD_MS = 1500;

// ── Sub-components ─────────────────────────────────────────

/** Circular waveform bars around the avatar (speaking state) */
function CircularWaveform({ audioData }: { audioData: Float32Array | null }) {
  const bars = useMemo(() => {
    const items: { angle: number; index: number }[] = [];
    for (let i = 0; i < BAR_COUNT; i++) {
      items.push({ angle: (i / BAR_COUNT) * Math.PI * 2 - Math.PI / 2, index: i });
    }
    return items;
  }, []);

  return (
    <g>
      {bars.map(({ angle, index }) => {
        const dataIndex = audioData
          ? Math.floor((index / BAR_COUNT) * audioData.length)
          : 0;
        const amplitude = audioData ? Math.abs(audioData[dataIndex] ?? 0) : 0;
        const barHeight = 6 + amplitude * 40;

        const cx = OUTER_SIZE / 2;
        const cy = OUTER_SIZE / 2;
        const x1 = cx + Math.cos(angle) * WAVE_BAR_RADIUS;
        const y1 = cy + Math.sin(angle) * WAVE_BAR_RADIUS;
        const x2 = cx + Math.cos(angle) * (WAVE_BAR_RADIUS + barHeight);
        const y2 = cy + Math.sin(angle) * (WAVE_BAR_RADIUS + barHeight);

        return (
          <motion.line
            key={index}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="#3B82F6"
            strokeWidth={2.5}
            strokeLinecap="round"
            opacity={0.4 + amplitude * 0.6}
            initial={false}
            animate={{ x2, y2, opacity: 0.4 + amplitude * 0.6 }}
            transition={{ duration: 0.05, ease: "linear" }}
          />
        );
      })}
    </g>
  );
}

/** 4 sound wave bars below the avatar */
function SoundBars({ active, audioData }: { active: boolean; audioData?: Float32Array | null }) {
  if (!active) return null;

  return (
    <div className="absolute -bottom-8 left-1/2 flex -translate-x-1/2 items-end gap-1">
      {Array.from({ length: SOUND_BAR_COUNT }).map((_, i) => {
        const dataIndex = audioData
          ? Math.floor((i / SOUND_BAR_COUNT) * audioData.length)
          : 0;
        const amplitude = audioData ? Math.abs(audioData[dataIndex] ?? 0) : 0;
        const baseHeight = 8 + i * 3;
        const dynamicHeight = baseHeight + amplitude * 24;

        return (
          <motion.div
            key={i}
            className="rounded-full bg-primary"
            style={{ width: SOUND_BAR_WIDTH }}
            animate={
              audioData
                ? { height: dynamicHeight }
                : { height: [baseHeight, baseHeight + 12, baseHeight] }
            }
            transition={
              audioData
                ? { duration: 0.05, ease: "linear" }
                : {
                    duration: 0.6,
                    repeat: Infinity,
                    delay: i * 0.12,
                    ease: "easeInOut",
                  }
            }
          />
        );
      })}
    </div>
  );
}

/** SVG checkmark that draws in (success state).
 *  Uses a plain <path> with CSS animation to avoid d="undefined" in AnimatePresence exit. */
function SuccessOverlay() {
  const cx = OUTER_SIZE / 2;
  const cy = OUTER_SIZE / 2;
  const checkPath = `M ${cx - 24} ${cy} L ${cx - 6} ${cy + 18} L ${cx + 28} ${cy - 16}`;

  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <path
        d={checkPath}
        fill="none"
        stroke="white"
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={100}
        strokeDashoffset={100}
        style={{ animation: "checkmark-draw 0.35s 0.15s ease-out forwards" }}
      />
    </motion.g>
  );
}

// ── Gradient definitions per state ──────────────────────────

const GRADIENT_STOPS: Record<AvatarState, [string, string, string]> = {
  idle: ["#2D3A8C", "#1E2A6E", "#3B82F6"],
  listening: ["#3B82F6", "#1E2A6E", "#6366F1"],
  speaking: ["#2D3A8C", "#1E2A6E", "#4F46E5"],
  thinking: ["#6366F1", "#1E2A6E", "#8B5CF6"],
  success: ["#10B981", "#059669", "#10B981"],
};

const INNER_GRADIENT_STOPS: Record<AvatarState, [string, string]> = {
  idle: ["#3B82F6", "#1E2A6E"],
  listening: ["#6366F1", "#3B82F6"],
  speaking: ["#3B82F6", "#1E2A6E"],
  thinking: ["#8B5CF6", "#6366F1"],
  success: ["#34D399", "#10B981"],
};

// ── Main component ──────────────────────────────────────────

export function AIAvatar({
  state = "idle",
  audioData = null,
  size,
  className,
}: AIAvatarProps) {
  const actualSize = size ?? OUTER_SIZE;
  const sizeScale = actualSize / OUTER_SIZE;
  const controls = useAnimation();
  const [showSuccess, setShowSuccess] = useState(false);
  const prevStateRef = useRef<AvatarState>(state);

  // Handle success flash: show checkmark for SUCCESS_HOLD_MS then revert visuals
  useEffect(() => {
    if (state === "success") {
      setShowSuccess(true);
      const timer = setTimeout(() => setShowSuccess(false), SUCCESS_HOLD_MS);
      return () => clearTimeout(timer);
    }
    setShowSuccess(false);
  }, [state]);

  // Main circle animation per state
  useEffect(() => {
    prevStateRef.current = state;

    switch (state) {
      case "idle":
        controls.start({
          scale: [1.0, 1.04, 1.0],
          transition: { duration: 3, repeat: Infinity, ease: "easeInOut" },
        });
        break;
      case "listening":
        controls.start({
          scale: 1.05,
          transition: { type: "spring" as const, stiffness: 200, damping: 15 },
        });
        break;
      case "speaking":
        controls.start({
          scale: [1.0, 1.03, 1.0],
          transition: { duration: 1.2, repeat: Infinity, ease: "easeInOut" },
        });
        break;
      case "thinking":
        controls.start({
          scale: [1.0, 1.02, 1.0],
          transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
        });
        break;
      case "success":
        controls.start({
          scale: [1.0, 1.08, 1.0],
          transition: { duration: 0.5, ease: "easeOut" },
        });
        break;
    }
  }, [state, controls]);

  const gradientId = "avatar-gradient-main";
  const gradientInnerId = "avatar-gradient-inner";
  const glowId = "avatar-glow";

  const stops = GRADIENT_STOPS[state];
  const innerStops = INNER_GRADIENT_STOPS[state];

  const glowShadowClass = cn(
    state === "speaking" && "shadow-[0_0_60px_rgba(30,42,110,0.5)]",
    state === "listening" && "shadow-[0_0_50px_rgba(30,42,110,0.4)]",
    state === "success" && "shadow-[0_0_60px_rgba(16,185,129,0.5)]",
    (state === "idle" || state === "thinking") &&
      "shadow-[0_0_40px_rgba(30,42,110,0.25)]",
  );

  return (
    <div
      className={cn(
        "relative flex items-center justify-center",
        className,
      )}
      style={{ width: actualSize, height: actualSize }}
    >
    <div style={{ transform: `scale(${sizeScale})`, transformOrigin: "center center", width: OUTER_SIZE, height: OUTER_SIZE, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
      {/* Background radial glow */}
      <div
        className="absolute inset-0 -m-[50px] rounded-full"
        style={{
          width: 300,
          height: 300,
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          background:
            state === "success"
              ? "radial-gradient(circle, rgba(16,185,129,0.2) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(30,42,110,0.2) 0%, transparent 70%)",
        }}
      >
        {/* Glow pulse for idle/thinking */}
        {(state === "idle" || state === "thinking") && (
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              background:
                "radial-gradient(circle, rgba(30,42,110,0.15) 0%, transparent 70%)",
            }}
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
      </div>

      {/* Ripple rings for listening */}
      {state === "listening" && (
        <>
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute rounded-full border-2 border-primary/30"
              style={{ width: MAIN_CIRCLE, height: MAIN_CIRCLE }}
              animate={{ scale: [1, 2.2], opacity: [0.5, 0] }}
              transition={{
                duration: 2,
                repeat: Infinity,
                delay: i * 0.6,
                ease: "easeOut",
              }}
            />
          ))}
        </>
      )}

      {/* Main animated circle */}
      <motion.div
        animate={controls}
        className={cn(
          "relative rounded-full transition-shadow duration-500",
          glowShadowClass,
        )}
        style={{ width: MAIN_CIRCLE, height: MAIN_CIRCLE }}
      >
        <svg
          viewBox={`0 0 ${OUTER_SIZE} ${OUTER_SIZE}`}
          width={MAIN_CIRCLE}
          height={MAIN_CIRCLE}
          className="overflow-visible"
          style={{ marginLeft: -20, marginTop: -20 }}
        >
          <defs>
            {/* Main gradient — animates via key change on state */}
            <linearGradient
              id={gradientId}
              x1="0%"
              y1="0%"
              x2="100%"
              y2="100%"
            >
              <motion.stop
                offset="0%"
                animate={{ stopColor: stops[0] }}
                transition={{ duration: 0.6 }}
              />
              <motion.stop
                offset="50%"
                animate={{ stopColor: stops[1] }}
                transition={{ duration: 0.6 }}
              />
              <motion.stop
                offset="100%"
                animate={{ stopColor: stops[2] }}
                transition={{ duration: 0.6 }}
              />
            </linearGradient>

            {/* Inner gradient */}
            <linearGradient
              id={gradientInnerId}
              x1="0%"
              y1="0%"
              x2="100%"
              y2="100%"
            >
              <motion.stop
                offset="0%"
                animate={{ stopColor: innerStops[0] }}
                transition={{ duration: 0.6 }}
              />
              <motion.stop
                offset="100%"
                animate={{ stopColor: innerStops[1] }}
                transition={{ duration: 0.6 }}
              />
            </linearGradient>

            {/* Glow filter */}
            <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Main outer circle */}
          <circle
            cx={OUTER_SIZE / 2}
            cy={OUTER_SIZE / 2}
            r={MAIN_CIRCLE / 2}
            fill={`url(#${gradientId})`}
            filter={`url(#${glowId})`}
          />

          {/* Inner lighter circle */}
          <circle
            cx={OUTER_SIZE / 2}
            cy={OUTER_SIZE / 2}
            r={INNER_CIRCLE / 2}
            fill={`url(#${gradientInnerId})`}
            opacity={0.35}
          />

          {/* Circular waveform when speaking */}
          {state === "speaking" && (
            <CircularWaveform audioData={audioData} />
          )}

          {/* Inner highlight (glass reflection effect) — no face */}
          {state !== "success" && !showSuccess && (
            <ellipse
              cx={OUTER_SIZE / 2 - 15}
              cy={OUTER_SIZE / 2 - 20}
              rx={25}
              ry={18}
              fill="white"
              opacity={0.12}
              style={{
                animation: "gradient-shift 12s ease infinite",
              }}
            />
          )}

          {/* Success checkmark */}
          <AnimatePresence>
            {showSuccess && <SuccessOverlay />}
          </AnimatePresence>
        </svg>
      </motion.div>

      {/* Sound wave bars for listening */}
      <SoundBars
        active={state === "listening"}
        audioData={audioData}
      />

      {/* Thinking dots */}
      <AnimatePresence>
        {state === "thinking" && (
          <motion.div
            className="absolute -bottom-10 left-1/2 flex -translate-x-1/2 items-center gap-2"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
          >
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="block h-2.5 w-2.5 rounded-full bg-primary"
                animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
                transition={{
                  duration: 0.8,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: "easeInOut",
                }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
    </div>
  );
}
