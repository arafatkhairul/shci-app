// public/pcm16-worklet.js
class PCMWorkletProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const in32 = inputs[0][0];
    if (in32) {
      // convert Float32 → Int16 in the worklet
      const int16 = new Int16Array(in32.length);
      for (let i = 0; i < in32.length; i++) {
        let s = in32[i];
        s = s < -1 ? -1 : s > 1 ? 1 : s;
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      // send raw ArrayBuffer, transferable
      this.port.postMessage(int16.buffer, [int16.buffer]);
    }
    return true;
  }
}

class TTSPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferQueue = [];
    this.readOffset = 0;
    this.samplesRemaining = 0;
    this.isPlaying = false;

    // Listen for incoming messages
    this.port.onmessage = (event) => {
      // Check if this is a control message (object with a "type" property).
      if (event.data && typeof event.data === "object" && event.data.type === "clear") {
        // Clear the TTS buffer and reset playback state.
        this.bufferQueue = [];
        this.readOffset = 0;
        this.samplesRemaining = 0;
        this.isPlaying = false;
        return;
      }
      
      // Otherwise assume it's a PCM chunk (e.g., an Int16Array)
      // (You may also check here if event.data instanceof Int16Array if needed)
      this.bufferQueue.push(event.data);
      this.samplesRemaining += event.data.length;
    };
  }

  process(inputs, outputs) {
    const outputChannel = outputs[0][0];

    if (this.samplesRemaining === 0) {
      outputChannel.fill(0);
      if (this.isPlaying) {
        this.isPlaying = false;
        this.port.postMessage({ type: 'ttsPlaybackStopped' });
      }
      return true;
    }

    if (!this.isPlaying) {
      this.isPlaying = true;
      this.port.postMessage({ type: 'ttsPlaybackStarted' });
    }

    let outIdx = 0;
    while (outIdx < outputChannel.length && this.bufferQueue.length > 0) {
      const currentBuffer = this.bufferQueue[0];
      const sampleValue = currentBuffer[this.readOffset] / 32768;
      outputChannel[outIdx++] = sampleValue;

      this.readOffset++;
      this.samplesRemaining--;

      if (this.readOffset >= currentBuffer.length) {
        this.bufferQueue.shift();
        this.readOffset = 0;
      }
    }

    while (outIdx < outputChannel.length) {
      outputChannel[outIdx++] = 0;
    }

    return true;
  }
}

registerProcessor('pcm-worklet-processor', PCMWorkletProcessor);
registerProcessor('tts-playback-processor', TTSPlaybackProcessor);
