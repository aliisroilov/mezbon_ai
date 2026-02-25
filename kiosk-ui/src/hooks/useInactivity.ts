import { useEffect, useRef, useState, useCallback } from "react";

interface UseInactivityOptions {
  warningMs?: number;
  resetMs?: number;
  enabled?: boolean;
  onWarning?: () => void;
  onReset?: () => void;
}

export function useInactivity({
  warningMs = 90_000,
  resetMs = 120_000,
  enabled = true,
  onWarning,
  onReset,
}: UseInactivityOptions = {}) {
  const [showWarning, setShowWarning] = useState(false);
  const lastActivityRef = useRef(Date.now());
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetTimers = useCallback(() => {
    lastActivityRef.current = Date.now();
    setShowWarning(false);

    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (resetTimerRef.current) clearTimeout(resetTimerRef.current);

    if (!enabled) return;

    warningTimerRef.current = setTimeout(() => {
      setShowWarning(true);
      onWarning?.();
    }, warningMs);

    resetTimerRef.current = setTimeout(() => {
      onReset?.();
    }, resetMs);
  }, [enabled, warningMs, resetMs, onWarning, onReset]);

  const recordActivity = useCallback(() => {
    resetTimers();
  }, [resetTimers]);

  useEffect(() => {
    if (!enabled) {
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
      setShowWarning(false);
      return;
    }

    resetTimers();

    const events = ["touchstart", "mousedown", "keydown", "scroll"] as const;
    events.forEach((evt) => document.addEventListener(evt, recordActivity));

    // Also listen for custom events from screen navigation and touch handlers
    const customHandler = () => recordActivity();
    window.addEventListener("user-interaction", customHandler);
    window.addEventListener("screen-navigated", customHandler);

    return () => {
      events.forEach((evt) => document.removeEventListener(evt, recordActivity));
      window.removeEventListener("user-interaction", customHandler);
      window.removeEventListener("screen-navigated", customHandler);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
    };
  }, [enabled, resetTimers, recordActivity]);

  return { showWarning, recordActivity };
}
