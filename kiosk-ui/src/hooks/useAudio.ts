import { useRef, useCallback, useState } from "react";

export function useAudio() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const getContext = useCallback(() => {
    if (!audioContextRef.current || audioContextRef.current.state === "closed") {
      audioContextRef.current = new AudioContext();
    }
    return audioContextRef.current;
  }, []);

  const playBase64 = useCallback(
    async (base64Audio: string) => {
      try {
        const ctx = getContext();
        if (ctx.state === "suspended") await ctx.resume();

        const binaryString = atob(base64Audio);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }

        // Use slice() to get a standalone ArrayBuffer — avoids issues
        // where decodeAudioData detaches the underlying buffer.
        const cleanBuffer = bytes.buffer.slice(
          bytes.byteOffset,
          bytes.byteOffset + bytes.byteLength,
        );

        const audioBuffer = await ctx.decodeAudioData(cleanBuffer);

        // Skip playback if the buffer is effectively empty (< 50ms)
        if (audioBuffer.duration < 0.05) {
          if (import.meta.env.DEV) console.warn("[useAudio] audio buffer too short, skipping playback");
          setIsPlaying(false);
          return;
        }

        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);

        sourceRef.current = source;
        setIsPlaying(true);

        source.onended = () => {
          setIsPlaying(false);
          sourceRef.current = null;
        };

        source.start();
      } catch (err) {
        if (import.meta.env.DEV) console.error("[useAudio] playBase64 failed:", err);
        setIsPlaying(false);
      }
    },
    [getContext],
  );

  const playUrl = useCallback(
    async (url: string) => {
      try {
        const ctx = getContext();
        if (ctx.state === "suspended") await ctx.resume();

        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);

        sourceRef.current = source;
        setIsPlaying(true);

        source.onended = () => {
          setIsPlaying(false);
          sourceRef.current = null;
        };

        source.start();
      } catch (err) {
        if (import.meta.env.DEV) console.error("[useAudio] playUrl failed:", err);
        setIsPlaying(false);
      }
    },
    [getContext],
  );

  const stop = useCallback(() => {
    sourceRef.current?.stop();
    sourceRef.current = null;
    setIsPlaying(false);
  }, []);

  return { isPlaying, playBase64, playUrl, stop };
}
