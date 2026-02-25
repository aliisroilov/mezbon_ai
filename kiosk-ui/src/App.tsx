import { Component, type ReactNode, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";
import { useSession } from "./hooks/useSession";
import { useInactivity } from "./hooks/useInactivity";
import { useSessionStore } from "./store/sessionStore";
import { ScreenRouter } from "./router/ScreenRouter";
import { Button } from "./components/ui/Button";
import { DegradationBanner } from "./components/ui/DegradationBanner";
import { PrintStatus } from "./components/feedback/PrintStatus";

// ── Connection status indicator ─────────────────────────────

function ConnectionStatus() {
  const isConnected = useSessionStore((s) => s.isConnected);

  // Only show when disconnected — no visible indicator when connected
  if (isConnected) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="fixed bottom-[108px] left-1/2 z-50 -translate-x-1/2"
    >
      <div className="flex items-center gap-2 rounded-full bg-amber-50/90 backdrop-blur-sm px-4 py-1.5 text-[13px] font-medium text-amber-700 shadow-sm border border-amber-200/50">
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        <span>Qayta ulanmoqda...</span>
      </div>
    </motion.div>
  );
}

// ── Inactivity timeout overlay ──────────────────────────────

interface TimeoutOverlayProps {
  onContinue: () => void;
  onEnd: () => void;
}

function TimeoutOverlay({ onContinue, onEnd }: TimeoutOverlayProps) {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onContinue}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: "spring" as const, stiffness: 300, damping: 25 }}
        className="mx-8 w-full max-w-md rounded-modal bg-white p-8 shadow-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
            <AlertTriangle className="h-8 w-8 text-amber-500" />
          </div>

          <h2 className="text-h2 tracking-heading text-text-primary">
            {t("session.timeoutWarning")}
          </h2>

          <div className="mt-8 flex w-full flex-col gap-3">
            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={onContinue}
            >
              {t("session.continueButton")}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-text-muted"
              onClick={onEnd}
            >
              {t("common.cancel")}
            </Button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Error boundary ──────────────────────────────────────────

interface ErrorBoundaryProps {
  children: ReactNode;
  onReset: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  handleReset = () => {
    this.setState({ hasError: false });
    this.props.onReset();
  };

  render() {
    if (this.state.hasError) {
      return <ErrorFallback onReset={this.handleReset} />;
    }
    return this.props.children;
  }
}

function ErrorFallback({ onReset }: { onReset: () => void }) {
  const { t } = useTranslation();

  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-surface">
      <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-amber-50">
        <AlertTriangle className="h-12 w-12 text-amber-500" />
      </div>
      <h1 className="text-h1 tracking-heading text-text-primary">
        {t("error.title")}
      </h1>
      <p className="mt-3 max-w-md text-center text-body text-text-muted">
        {t("error.unknown")}
      </p>
      <Button
        variant="primary"
        size="lg"
        className="mt-8"
        onClick={onReset}
      >
        {t("common.retry")}
      </Button>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────

function App() {
  // Initialize socket session listener
  useSession();

  // Request fullscreen on first user interaction (kiosk mode)
  const fullscreenRequested = useRef(false);
  useEffect(() => {
    const enterFullscreen = () => {
      if (fullscreenRequested.current) return;
      fullscreenRequested.current = true;
      document.documentElement.requestFullscreen?.().catch(() => {
        // Fullscreen not available or denied — continue normally
      });
      document.removeEventListener("pointerdown", enterFullscreen);
    };
    document.addEventListener("pointerdown", enterFullscreen, { once: true });
    return () => document.removeEventListener("pointerdown", enterFullscreen);
  }, []);

  const visitorState = useSessionStore((s) => s.state);
  const resetSession = useSessionStore((s) => s.resetSession);

  // Inactivity timeout — only active when NOT idle
  const isActive = visitorState !== "IDLE";

  const handleTimeoutReset = useCallback(() => {
    resetSession();
  }, [resetSession]);

  const { showWarning, recordActivity } = useInactivity({
    warningMs: 240_000,   // 4 min before warning
    resetMs: 360_000,     // 6 min before auto-reset
    enabled: isActive,
    onReset: handleTimeoutReset,
  });

  // Reset inactivity timer on AI responses, state changes, voice activity,
  // and processing changes — these indicate active interaction even without
  // touch/mouse events.
  const aiMessage = useSessionStore((s) => s.aiMessage);
  const isSpeaking = useSessionStore((s) => s.isSpeaking);
  const isProcessing = useSessionStore((s) => s.isProcessing);
  const isListening = useSessionStore((s) => s.isListening);

  useEffect(() => {
    if (isActive) {
      recordActivity();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiMessage, visitorState, isSpeaking, isProcessing, isListening]);

  // Also reset inactivity on custom events from voice/socket pipeline
  useEffect(() => {
    if (!isActive) return;
    const handler = () => recordActivity();
    window.addEventListener("ai-response-received", handler);
    window.addEventListener("speech-sent", handler);
    return () => {
      window.removeEventListener("ai-response-received", handler);
      window.removeEventListener("speech-sent", handler);
    };
  }, [isActive, recordActivity]);

  const handleContinue = useCallback(() => {
    recordActivity();
  }, [recordActivity]);

  const handleEndSession = useCallback(() => {
    resetSession();
  }, [resetSession]);

  const handleErrorReset = useCallback(() => {
    resetSession();
  }, [resetSession]);

  return (
    <ErrorBoundary onReset={handleErrorReset}>
      <div className="relative h-screen w-screen overflow-hidden">
        {/* Background gradient layer */}
        <div
          className="absolute inset-0 -z-30"
          style={{
            background:
              "linear-gradient(135deg, #EEF0F7 0%, #F8FAFC 30%, #E8ECF5 60%, #F0F2FA 100%)",
          }}
        />

        {/* Screen content */}
        <ScreenRouter />

        {/* Connection status (top left) */}
        <ConnectionStatus />

        {/* Degradation banner (voice/AI unavailable) */}
        <DegradationBanner />

        {/* Print status toast */}
        <PrintStatus />

        {/* Inactivity timeout overlay */}
        <AnimatePresence>
          {showWarning && (
            <TimeoutOverlay
              onContinue={handleContinue}
              onEnd={handleEndSession}
            />
          )}
        </AnimatePresence>
      </div>
    </ErrorBoundary>
  );
}

export default App;
