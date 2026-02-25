import { useCallback, useEffect, useMemo, useRef } from "react";
import { useSessionStore } from "../store/sessionStore";
import { useMicrophone } from "./useMicrophone";
import { emitSpeechAudio, emitChatText } from "../services/socket";
import { sounds } from "../utils/sounds";
import type { AvatarState } from "../components/ai/AIAvatar";
import type { VoiceState } from "../components/ai/VoiceIndicator";

/**
 * Shared voice chat hook for ALL interactive screens.
 *
 * Encapsulates:
 *  - Microphone recording (WAV, 16kHz, VAD-based silence detection)
 *  - Browser Web Speech API fallback (when VITE_USE_BROWSER_STT=true)
 *  - Auto-restart after AI response (with or without TTS audio)
 *  - Audio/text sending via Socket.IO
 *  - Avatar + voice indicator state derivation
 *  - Mic toggle (tap to start/stop)
 *
 * Usage in any screen:
 *   const voice = useVoiceChat();
 *   <AIAvatar state={voice.avatarState} />
 *   <VoiceIndicator state={voice.voiceState} onClick={voice.toggleMic} />
 */

/**
 * Whether to use the browser's Web Speech API for STT instead of
 * sending raw audio to the backend. Enable this when the backend STT
 * (Muxlisa) is down. Set VITE_USE_BROWSER_STT=true in .env.
 */
const USE_BROWSER_STT = import.meta.env.VITE_USE_BROWSER_STT === "true";

interface UseVoiceChatOptions {
  /** Auto-start mic on mount (default true) */
  autoStart?: boolean;
  /** Delay before auto-start on mount, ms (default 1000) */
  autoStartDelay?: number;
  /** Silence threshold for VAD (default 0.02) */
  silenceThreshold?: number;
  /** Silence duration before auto-stop, ms (default 1500) */
  silenceDuration?: number;
}

export function useVoiceChat({
  autoStart = true,
  autoStartDelay = 1000,
  silenceThreshold = 0.02,
  silenceDuration = 1500,
}: UseVoiceChatOptions = {}) {
  const deviceId = useSessionStore((s) => s.deviceId);
  const sessionId = useSessionStore((s) => s.sessionId);
  const isListening = useSessionStore((s) => s.isListening);
  const isSpeaking = useSessionStore((s) => s.isSpeaking);
  const isProcessing = useSessionStore((s) => s.isProcessing);
  const shouldListen = useSessionStore((s) => s.shouldListen);
  const setIsListening = useSessionStore((s) => s.setIsListening);
  const setIsProcessing = useSessionStore((s) => s.setIsProcessing);
  const setShouldListen = useSessionStore((s) => s.setShouldListen);

  // Cooldown: minimum 2s between audio sends to prevent rapid-fire loop
  const lastSendRef = useRef(0);

  // Web Speech API recognition instance (reused across recordings)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  // Send recorded audio to backend — VAD already ensures only real speech arrives here
  const handleAudioReady = useCallback(
    (blob: Blob) => {
      // If using browser STT, don't send audio — the Web Speech API handles it
      if (USE_BROWSER_STT) return;

      const now = Date.now();
      if (now - lastSendRef.current < 2000) {
        console.log("[voice] Audio send throttled (cooldown)");
        return;
      }
      lastSendRef.current = now;
      console.log(`[voice] Sending audio to backend: ${blob.size} bytes`);
      setIsListening(false);
      setIsProcessing(true);
      if (deviceId) {
        emitSpeechAudio(deviceId, sessionId ?? "", blob, "wav");
      } else {
        console.warn("[voice] No deviceId — cannot send audio");
        setIsProcessing(false);
      }
    },
    [deviceId, sessionId, setIsListening, setIsProcessing],
  );

  const { isRecording, startRecording: startMicRecording, stopRecording: stopMicRecording } = useMicrophone({
    onAudioReady: handleAudioReady,
    silenceThreshold,
    silenceDuration,
  });

  // Browser Web Speech API for client-side STT
  const startBrowserSTT = useCallback(() => {
    if (!USE_BROWSER_STT) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const W = window as any;
    const SpeechRecognitionAPI = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      console.error("[voice] Web Speech API not supported in this browser");
      return;
    }

    // Stop previous if active
    if (recognitionRef.current) {
      try { (recognitionRef.current as any).abort(); } catch {}
    }

    const recognition = new SpeechRecognitionAPI();
    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "uz-UZ"; // Primary: Uzbek
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      if (!transcript) return;

      const now = Date.now();
      if (now - lastSendRef.current < 2000) {
        console.log("[voice] Browser STT throttled");
        return;
      }
      lastSendRef.current = now;

      // Detect language heuristically
      const hasCyrillic = /[\u0400-\u04FF]/.test(transcript);
      const hasLatin = /[a-zA-Z]/.test(transcript);
      const uzMarkers = ["o'", "g'", "sh", "ch", "ng"];
      const hasUzMarkers = uzMarkers.some((m: string) => transcript.toLowerCase().includes(m));
      let language = "uz";
      if (hasCyrillic) language = "ru";
      else if (hasLatin && !hasUzMarkers) language = "en";

      console.log(`[voice] Browser STT: "${transcript}" (${language})`);
      setIsListening(false);
      setIsProcessing(true);

      if (deviceId) {
        emitChatText(deviceId, sessionId ?? "", transcript, language);
      } else {
        console.warn("[voice] No deviceId — cannot send text");
        setIsProcessing(false);
      }
    };

    recognition.onerror = (event: any) => {
      if (event.error === "no-speech" || event.error === "aborted") {
        // Normal — user didn't speak, just restart
        return;
      }
      console.warn("[voice] Browser STT error:", event.error);
    };

    recognition.onend = () => {
      // Auto-restart if still listening
      const state = useSessionStore.getState();
      if (state.isListening && !state.isProcessing && !state.isSpeaking && USE_BROWSER_STT) {
        try { recognition.start(); } catch {}
      }
    };

    try {
      recognition.start();
      console.log("[voice] Browser STT started");
    } catch (e) {
      console.error("[voice] Failed to start browser STT:", e);
    }
  }, [deviceId, sessionId, setIsListening, setIsProcessing]);

  const stopBrowserSTT = useCallback(() => {
    if (recognitionRef.current) {
      try { (recognitionRef.current as any).abort(); } catch {}
      recognitionRef.current = null;
    }
  }, []);

  // Unified start/stop that handles both modes
  const startRecording = useCallback(() => {
    if (USE_BROWSER_STT) {
      startBrowserSTT();
    }
    startMicRecording(); // Always start mic (for VAD silence detection even in browser STT mode)
  }, [startBrowserSTT, startMicRecording]);

  const stopRecording = useCallback(() => {
    if (USE_BROWSER_STT) {
      stopBrowserSTT();
    }
    stopMicRecording();
  }, [stopBrowserSTT, stopMicRecording]);

  // Toggle mic on/off (used by VoiceIndicator tap)
  const toggleMic = useCallback(() => {
    if (isRecording) {
      sounds.micOff();
      stopRecording();
      setIsListening(false);
    } else if (!isProcessing && !isSpeaking) {
      sounds.micOn();
      setIsListening(true);
      startRecording();
    }
  }, [isRecording, isProcessing, isSpeaking, startRecording, stopRecording, setIsListening]);

  // Auto-restart mic when shouldListen becomes true (after AI response)
  useEffect(() => {
    if (shouldListen && !isRecording && !isSpeaking && !isProcessing) {
      setShouldListen(false);
      setIsListening(true);
      startRecording();
    }
  }, [shouldListen, isRecording, isSpeaking, isProcessing, setShouldListen, setIsListening, startRecording]);

  // Auto-start mic on mount
  useEffect(() => {
    if (!autoStart) return;
    const timer = setTimeout(() => {
      if (!isRecording && !isSpeaking && !isProcessing) {
        setIsListening(true);
        startRecording();
      }
    }, autoStartDelay);
    return () => clearTimeout(timer);
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Safety timeout: if isProcessing stays true for >15s, something went wrong.
  // Reset processing flag and re-enable mic so the user isn't stuck.
  const processingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (isProcessing) {
      processingTimerRef.current = setTimeout(() => {
        const s = useSessionStore.getState();
        if (s.isProcessing) {
          s.setIsProcessing(false);
          s.setAIMessage(
            s.aiMessage || "Kechirasiz, texnik xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
          );
          s.setShouldListen(true);
        }
      }, 15000);
    } else if (processingTimerRef.current) {
      clearTimeout(processingTimerRef.current);
      processingTimerRef.current = null;
    }
    return () => {
      if (processingTimerRef.current) {
        clearTimeout(processingTimerRef.current);
      }
    };
  }, [isProcessing]);

  // Derived states for UI components
  const avatarState: AvatarState = useMemo(() => {
    if (isProcessing) return "thinking";
    if (isSpeaking) return "speaking";
    if (isListening) return "listening";
    return "idle";
  }, [isProcessing, isSpeaking, isListening]);

  const voiceState: VoiceState = useMemo(() => {
    if (isSpeaking) return "speaking";
    if (isProcessing) return "processing";
    if (isListening) return "listening";
    return "inactive";
  }, [isSpeaking, isProcessing, isListening]);

  return {
    isRecording,
    isListening,
    isSpeaking,
    isProcessing,
    avatarState,
    voiceState,
    toggleMic,
    startRecording,
    stopRecording,
  };
}
