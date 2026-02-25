/**
 * AudioWorklet processor for capturing microphone PCM samples.
 *
 * Runs on the audio thread — zero impact on main-thread performance.
 * Posts Float32Array chunks to the main thread via port.postMessage().
 *
 * The main thread controls recording state via port.postMessage({ command }).
 */
class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._recording = false;
    this._buffer = [];
    this._bufferLength = 0;
    // Flush every ~4096 samples (~85ms at 48kHz, ~256ms at 16kHz)
    this._flushThreshold = 4096;

    this.port.onmessage = (event) => {
      const { command } = event.data;
      if (command === "start") {
        this._recording = true;
        this._buffer = [];
        this._bufferLength = 0;
      } else if (command === "stop") {
        // Flush remaining buffer
        if (this._bufferLength > 0) {
          this._flush();
        }
        this._recording = false;
      }
    };
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const channelData = input[0];
    if (!channelData || channelData.length === 0) return true;

    if (this._recording) {
      // Copy the samples (input buffer is reused by the engine)
      this._buffer.push(new Float32Array(channelData));
      this._bufferLength += channelData.length;

      if (this._bufferLength >= this._flushThreshold) {
        this._flush();
      }
    }

    return true; // Keep processor alive
  }

  _flush() {
    // Merge all buffered chunks into one Float32Array
    const merged = new Float32Array(this._bufferLength);
    let offset = 0;
    for (const chunk of this._buffer) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    this.port.postMessage({ audioData: merged }, [merged.buffer]);
    this._buffer = [];
    this._bufferLength = 0;
  }
}

registerProcessor("audio-capture-processor", AudioCaptureProcessor);
