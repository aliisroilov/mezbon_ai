/**
 * Audio feedback sounds using Web Audio API (OscillatorNode).
 * No external files needed — generates tones programmatically.
 */

let sharedCtx: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!sharedCtx || sharedCtx.state === "closed") {
    sharedCtx = new AudioContext();
  }
  return sharedCtx;
}

function playTone(
  freq: number,
  duration: number,
  type: OscillatorType,
  volume: number,
) {
  try {
    const ctx = getAudioContext();
    if (ctx.state === "suspended") ctx.resume();

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch {
    // Audio not available — fail silently
  }
}

export const sounds = {
  /** Mic activated — soft high-pitched ding */
  micOn: () => playTone(880, 0.08, "sine", 0.15),

  /** Mic deactivated / audio sent — soft whoosh */
  micOff: () => playTone(440, 0.12, "sine", 0.1),

  /** Success (check-in, booking confirmed) — pleasant ascending chime */
  success: () => {
    playTone(523, 0.15, "sine", 0.2);  // C5
    setTimeout(() => playTone(659, 0.15, "sine", 0.2), 100); // E5
    setTimeout(() => playTone(784, 0.2, "sine", 0.2), 200);  // G5
  },

  /** Error — gentle low tone */
  error: () => playTone(220, 0.2, "sine", 0.15),

  /** Button tap — subtle click */
  tap: () => playTone(600, 0.03, "sine", 0.08),
};
