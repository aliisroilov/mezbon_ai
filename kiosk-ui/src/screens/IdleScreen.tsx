import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { useCamera } from "../hooks/useCamera";
import { useSessionStore } from "../store/sessionStore";
import { emitFaceFrame } from "../services/socket";
import { LanguageSelector } from "../components/ui/LanguageSelector";
import { NanoMedicalLogo } from "../components/ui/NanoMedicalLogo";
import type { DetectedFace } from "../types";

// ── Ambient floating orb ────────────────────────────────────

/**
 * Ambient floating orb — uses CSS animations for GPU acceleration.
 * Only animates transform and opacity (compositor-friendly properties).
 */
function FloatingOrb({
  color,
  size,
  x,
  y,
  duration,
  delay = 0,
}: {
  color: string;
  size: number;
  x: string;
  y: string;
  duration: number;
  delay?: number;
}) {
  return (
    <div
      className="absolute rounded-full will-change-transform"
      style={{
        width: size,
        height: size,
        left: x,
        top: y,
        background: color,
        filter: `blur(${Math.round(size / 2)}px)`,
        opacity: 0.3,
        animation: `float-orb ${duration}s ease-in-out ${delay}s infinite`,
      }}
    />
  );
}

// ── Clock display ───────────────────────────────────────────

function Clock() {
  const [time, setTime] = useState(() => formatTime());

  useEffect(() => {
    const interval = setInterval(() => setTime(formatTime()), 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="text-caption text-text-muted tabular-nums">{time}</span>
  );
}

function formatTime(): string {
  const now = new Date();
  return now.toLocaleTimeString("uz-UZ", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// ── Main screen ─────────────────────────────────────────────

interface IdleScreenProps {
  onFaceDetected: () => void;
  onTouchStart: () => void;
}

export function IdleScreen({ onFaceDetected, onTouchStart }: IdleScreenProps) {
  const { t } = useTranslation();
  const deviceId = useSessionStore((s) => s.deviceId);
  const faceEmittedRef = useRef(false);

  const handleFaceDetected = useCallback(
    (_faces: DetectedFace[]) => {
      // Only emit once per idle cycle to avoid flooding
      if (faceEmittedRef.current) return;
      faceEmittedRef.current = true;

      // Capture the current frame and send to backend via socket
      // This creates a real session on the backend (orchestrator.handle_face_detected)
      const frame = captureFrameRef.current?.();
      if (frame && deviceId) {
        // Strip the data:image/jpeg;base64, prefix — backend expects raw base64
        const base64 = frame.includes(",") ? frame.split(",")[1]! : frame;
        emitFaceFrame(deviceId, base64);
      }

      // Also trigger local state change immediately for responsive UI
      onFaceDetected();
    },
    [onFaceDetected, deviceId],
  );

  // Camera runs in background for face detection — no visible feed
  const { videoRef, canvasRef, captureFrame } = useCamera({
    enabled: true,
    fps: 2,
    onFaceDetected: handleFaceDetected,
  });

  // Keep a ref to captureFrame so the callback can access it without stale closures
  const captureFrameRef = useRef(captureFrame);
  captureFrameRef.current = captureFrame;

  // Reset the face-emitted flag when entering idle again
  useEffect(() => {
    faceEmittedRef.current = false;
  }, []);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col items-center justify-center overflow-hidden"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      onClick={onTouchStart}
    >
      {/* Animated gradient background */}
      <div
        className="absolute inset-0 -z-20"
        style={{
          background:
            "linear-gradient(135deg, #EEF0F7 0%, #F8FAFC 25%, #E8ECF5 50%, #F0F2FA 75%, #EEF0F7 100%)",
          backgroundSize: "400% 400%",
          animation: "gradient-shift 20s ease infinite",
        }}
      />

      {/* Floating ambient orbs */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <FloatingOrb
          color="rgba(30, 42, 110, 0.12)"
          size={200}
          x="10%"
          y="15%"
          duration={18}
        />
        <FloatingOrb
          color="rgba(30, 42, 110, 0.15)"
          size={250}
          x="65%"
          y="55%"
          duration={22}
        />
        <FloatingOrb
          color="rgba(30, 42, 110, 0.08)"
          size={180}
          x="30%"
          y="70%"
          duration={25}
        />
      </div>

      {/* Center content */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="relative z-10 flex flex-col items-center gap-6 text-center"
      >
        {/* Clinic logo — breathing glow (CSS animation for GPU perf) */}
        <div
          className="flex h-[280px] w-[280px] items-center justify-center rounded-full bg-white shadow-glow will-change-transform"
          style={{ animation: "logo-glow 3s ease-in-out infinite" }}
        >
          <NanoMedicalLogo size="lg" />
        </div>

        {/* Clinic name */}
        <div>
          <h1 className="text-h1 tracking-heading text-text-primary">
            {t("app.name")}
          </h1>
          <p className="mt-3 text-body-lg text-text-muted">
            {t("app.tagline")}
          </p>
        </div>

        {/* Approach prompt — pulsing opacity */}
        <div className="mt-12 flex flex-col items-center gap-4">
          <p
            className="text-body-lg text-text-body"
            style={{ animation: "pulse-text 3s ease-in-out infinite" }}
          >
            {t("idle.approach")}
          </p>

          {/* Approach arrow animation */}
          <motion.svg
            width="40" height="40" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            className="text-primary/60"
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <path d="M12 5v14M5 12l7 7 7-7" />
          </motion.svg>
        </div>
      </motion.div>

      {/* Bottom bar */}
      <div className="absolute bottom-8 left-8 right-8 z-10 flex items-end justify-between">
        {/* Language selector */}
        <LanguageSelector />

        {/* Touch hint */}
        <p
          className="text-caption text-text-muted"
          style={{ animation: "pulse-text 4s ease-in-out infinite" }}
        >
          {t("idle.touchToStart")}
        </p>

        {/* Clock */}
        <Clock />
      </div>

      {/* Hidden camera elements */}
      <video ref={videoRef} className="hidden" playsInline muted />
      <canvas ref={canvasRef} className="hidden" />
    </motion.div>
  );
}
