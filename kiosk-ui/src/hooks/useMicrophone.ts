import { useRef, useCallback, useState } from "react";

/**
 * Mic states:
 *   IDLE       – mic is off
 *   WAITING    – mic open, monitoring energy, NOT buffering audio
 *   RECORDING  – speech detected, buffering audio
 *   PROCESSING – audio sent, waiting for AI response
 */
type MicState = "IDLE" | "WAITING" | "RECORDING" | "PROCESSING";

interface UseMicrophoneOptions {
  /** RMS threshold to consider as speech (default 0.02) */
  silenceThreshold?: number;
  /** ms of silence after speech to auto-stop recording (default 1500) */
  silenceDuration?: number;
  onAudioReady?: (blob: Blob) => void;
  /** Target sample rate for the output WAV (default 16000) */
  sampleRate?: number;
  /** Max seconds of ACTIVE SPEECH before auto-stop (default 15) */
  maxSpeechDuration?: number;
}

/**
 * Records microphone audio with Voice Activity Detection (VAD).
 *
 * Key behaviour:
 *  - WAITING state: mic is open but no audio is buffered or sent.
 *    Waits indefinitely for speech (energy above threshold).
 *  - RECORDING state: speech detected, buffers audio.
 *    Stops when silence returns for silenceDuration ms.
 *  - NEVER sends audio if no speech was detected.
 *  - Safety cap: maxSpeechDuration of ACTIVE speech.
 *
 * Uses AudioWorkletNode (modern) with ScriptProcessorNode fallback.
 */
export function useMicrophone({
  silenceThreshold = 0.02,
  silenceDuration = 1500,
  onAudioReady,
  sampleRate: targetSampleRate = 16000,
  maxSpeechDuration = 15,
}: UseMicrophoneOptions = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const samplesRef = useRef<Float32Array[]>([]);
  const micStateRef = useRef<MicState>("IDLE");
  const rafRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  // AudioWorklet refs
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  // ScriptProcessor fallback ref
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  // VAD tracking
  const speechFrameCountRef = useRef(0);
  const silenceFrameCountRef = useRef(0);
  const speechStartTimeRef = useRef(0);

  // Frames needed for speech start detection (~300ms at ~30fps RAF)
  const SPEECH_START_FRAMES = 10;
  // Frames of silence after speech to trigger stop
  const SILENCE_END_FRAMES = Math.round((silenceDuration / 1000) * 30);

  const cleanup = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    // Stop AudioWorklet
    if (workletNodeRef.current) {
      try {
        workletNodeRef.current.port.postMessage({ command: "stop" });
        workletNodeRef.current.disconnect();
      } catch { /* already disconnected */ }
      workletNodeRef.current = null;
    }

    // Stop ScriptProcessor fallback
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }

    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;

    const ctx = audioCtxRef.current;
    if (ctx && ctx.state !== "closed") {
      ctx.close().catch(() => {});
    }
    audioCtxRef.current = null;
    analyserRef.current = null;
  }, []);

  const buildAndSendWAV = useCallback(() => {
    const ctx = audioCtxRef.current;
    const nativeSR = ctx?.sampleRate ?? 44100;

    const chunks = samplesRef.current;
    samplesRef.current = [];

    if (chunks.length === 0) {
      return;
    }

    // Merge all chunks
    const totalLen = chunks.reduce((sum, c) => sum + c.length, 0);
    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Downsample if needed
    const resampled =
      nativeSR === targetSampleRate
        ? merged
        : downsample(merged, nativeSR, targetSampleRate);

    const wavBlob = encodeWAV(resampled, targetSampleRate);
    const durationMs = Math.round((resampled.length / targetSampleRate) * 1000);

    if (wavBlob.size > 44 && durationMs > 500) {
      if (import.meta.env.DEV) console.log(`[mic] Sending audio: ${durationMs}ms, ${wavBlob.size} bytes`);
      onAudioReady?.(wavBlob);
    } else {
      if (import.meta.env.DEV) console.log(`[mic] Audio too short (${durationMs}ms), discarding`);
    }
  }, [onAudioReady, targetSampleRate]);

  const stopRecording = useCallback(() => {
    const wasMicState = micStateRef.current;
    micStateRef.current = "IDLE";
    setIsRecording(false);

    // Tell worklet to stop buffering
    if (workletNodeRef.current) {
      try {
        workletNodeRef.current.port.postMessage({ command: "stop" });
      } catch { /* ok */ }
    }

    // Only send audio if we were actually recording speech
    if (wasMicState === "RECORDING") {
      buildAndSendWAV();
    } else {
      samplesRef.current = [];
    }

    cleanup();

    // Reset VAD state
    speechFrameCountRef.current = 0;
    silenceFrameCountRef.current = 0;
    speechStartTimeRef.current = 0;
  }, [cleanup, buildAndSendWAV]);

  const startingRef = useRef(false);
  const startRecording = useCallback(async () => {
    if (micStateRef.current !== "IDLE" || startingRef.current) return;
    startingRef.current = true;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      streamRef.current = stream;
      setHasPermission(true);

      // Create AudioContext — use native sample rate, downsample later
      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;

      // CRITICAL: Resume AudioContext if suspended (browser autoplay policy)
      if (audioCtx.state === "suspended") {
        if (import.meta.env.DEV) console.log("[mic] AudioContext suspended, resuming...");
        await audioCtx.resume();
        if (import.meta.env.DEV) console.log("[mic] AudioContext resumed:", audioCtx.state);
      }

      const source = audioCtx.createMediaStreamSource(stream);

      // AnalyserNode for VAD energy detection (used regardless of capture method)
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      analyserRef.current = analyser;
      source.connect(analyser);

      samplesRef.current = [];

      // Try AudioWorklet first (modern, no deprecation warnings)
      let useWorklet = false;
      if (typeof audioCtx.audioWorklet !== "undefined") {
        try {
          await audioCtx.audioWorklet.addModule("/audio-processor.worklet.js");

          const workletNode = new AudioWorkletNode(audioCtx, "audio-capture-processor", {
            numberOfInputs: 1,
            numberOfOutputs: 1,
            channelCount: 1,
          });
          workletNodeRef.current = workletNode;

          // Receive audio chunks from worklet
          workletNode.port.onmessage = (event: MessageEvent) => {
            const { audioData } = event.data;
            if (audioData && micStateRef.current === "RECORDING") {
              samplesRef.current.push(new Float32Array(audioData));
            }
          };

          source.connect(workletNode);
          // Connect to destination to keep the audio graph alive
          workletNode.connect(audioCtx.destination);

          useWorklet = true;
          if (import.meta.env.DEV) console.log("[mic] Using AudioWorkletNode (modern)");
        } catch (err) {
          if (import.meta.env.DEV) console.warn("[mic] AudioWorklet failed, falling back to ScriptProcessor:", err);
        }
      }

      // Fallback: ScriptProcessorNode (deprecated but widely supported)
      if (!useWorklet) {
        const bufferSize = 4096;
        const processor = audioCtx.createScriptProcessor(bufferSize, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e: AudioProcessingEvent) => {
          if (micStateRef.current === "RECORDING") {
            const input = e.inputBuffer.getChannelData(0);
            samplesRef.current.push(new Float32Array(input));
          }
        };

        source.connect(processor);
        processor.connect(audioCtx.destination);

        if (import.meta.env.DEV) console.log("[mic] Using ScriptProcessorNode (fallback)");
      }

      // Start in WAITING state — listening for speech
      micStateRef.current = "WAITING";
      startingRef.current = false;
      setIsRecording(true);
      speechFrameCountRef.current = 0;
      silenceFrameCountRef.current = 0;
      speechStartTimeRef.current = 0;

      if (import.meta.env.DEV) {
        console.log(
          `[mic] Ready — WAITING for speech (threshold: ${silenceThreshold}, sampleRate: ${audioCtx.sampleRate}Hz)`
        );
      }

      // Tell worklet we're NOT recording yet (VAD decides when to start)
      // We'll send "start" when speech is detected

      // VAD loop using requestAnimationFrame
      const dataArray = new Float32Array(analyser.fftSize);

      const checkAudioLevel = () => {
        if (micStateRef.current === "IDLE") return;

        analyser.getFloatTimeDomainData(dataArray);
        const rms = Math.sqrt(
          dataArray.reduce((sum, v) => sum + v * v, 0) / dataArray.length
        );

        if (rms > silenceThreshold) {
          speechFrameCountRef.current++;
          silenceFrameCountRef.current = 0;
        } else {
          silenceFrameCountRef.current++;
          if (micStateRef.current === "WAITING") {
            speechFrameCountRef.current = 0;
          }
        }

        // WAITING → RECORDING: speech detected for ~300ms
        if (
          micStateRef.current === "WAITING" &&
          speechFrameCountRef.current > SPEECH_START_FRAMES
        ) {
          micStateRef.current = "RECORDING";
          speechStartTimeRef.current = Date.now();
          if (import.meta.env.DEV) console.log("[mic] Speech detected — RECORDING started");

          // Tell worklet to start buffering
          if (workletNodeRef.current) {
            workletNodeRef.current.port.postMessage({ command: "start" });
          }
        }

        // RECORDING → stop: silence after speech for configured duration
        if (
          micStateRef.current === "RECORDING" &&
          silenceFrameCountRef.current > SILENCE_END_FRAMES
        ) {
          const recordingDuration = Date.now() - speechStartTimeRef.current;
          if (import.meta.env.DEV) console.log(`[mic] Silence detected after ${recordingDuration}ms of speech — stopping`);
          stopRecording();
          return;
        }

        // RECORDING → stop: max speech duration safety cap
        if (
          micStateRef.current === "RECORDING" &&
          speechStartTimeRef.current > 0 &&
          Date.now() - speechStartTimeRef.current > maxSpeechDuration * 1000
        ) {
          if (import.meta.env.DEV) console.warn("[mic] Max speech duration reached, stopping");
          stopRecording();
          return;
        }

        rafRef.current = requestAnimationFrame(checkAudioLevel);
      };

      rafRef.current = requestAnimationFrame(checkAudioLevel);
    } catch (err) {
      startingRef.current = false;
      setHasPermission(false);
      if (import.meta.env.DEV) console.error("[mic] Failed to start:", err);
    }
  }, [silenceThreshold, maxSpeechDuration, stopRecording, cleanup, SILENCE_END_FRAMES, SPEECH_START_FRAMES]);

  return { isRecording, hasPermission, startRecording, stopRecording };
}

// ─── WAV Encoding Helpers ────────────────────────────────────

/** Downsample Float32 PCM from srcRate to dstRate using linear interpolation. */
function downsample(
  samples: Float32Array,
  srcRate: number,
  dstRate: number,
): Float32Array {
  if (srcRate === dstRate) return samples;
  const ratio = srcRate / dstRate;
  const newLength = Math.round(samples.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const low = Math.floor(srcIndex);
    const high = Math.min(low + 1, samples.length - 1);
    const frac = srcIndex - low;
    result[i] = samples[low]! * (1 - frac) + samples[high]! * frac;
  }
  return result;
}

/** Encode Float32 mono PCM samples as a 16-bit WAV Blob. */
function encodeWAV(samples: Float32Array, sampleRate: number): Blob {
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = samples.length * (bitsPerSample / 8);
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");

  // fmt chunk
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data chunk
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  // Write PCM samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]!));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function writeString(view: DataView, offset: number, s: string): void {
  for (let i = 0; i < s.length; i++) {
    view.setUint8(offset + i, s.charCodeAt(i));
  }
}
