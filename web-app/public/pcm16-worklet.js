// public/pcm16-worklet.js
class PCMWorklet extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetRate = (options.processorOptions?.targetSampleRate) || 16000;
    this.frameSize  = (options.processorOptions?.frameSize) || 320; // 20ms @16k
    this._residual  = new Int16Array(0);
    this.sampleRate = sampleRate; // Store the sampleRate from the global scope
  }
  static get parameterDescriptors() { return []; }

  _downsample(float32) {
    const ratio = this.sampleRate / this.targetRate;
    const outLen = Math.floor(float32.length / ratio);
    const out = new Int16Array(outLen);
    for (let i=0;i<outLen;i++){
      const start = Math.floor(i*ratio), end = Math.floor((i+1)*ratio);
      let sum=0, cnt=0;
      for (let k=start;k<end && k<float32.length;k++){ sum+=float32[k]; cnt++; }
      const v = cnt ? (sum/cnt) : 0;
      out[i] = Math.max(-1, Math.min(1, v)) * 0x7FFF;
    }
    return out;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) return true;
    const mono = input[0];
    const ds = this._downsample(mono);

    const buf = new Int16Array(this._residual.length + ds.length);
    buf.set(this._residual, 0); buf.set(ds, this._residual.length);

    let off = 0;
    while (off + this.frameSize <= buf.length) {
      const frame = buf.subarray(off, off + this.frameSize);
      // Create a copy of the frame data before transferring to avoid detached ArrayBuffer
      const frameCopy = new Int16Array(frame);
      this.port.postMessage({ type: 'audio-16k', pcm: frameCopy }, [frameCopy.buffer]); // transfer
      off += this.frameSize;
    }
    this._residual = buf.subarray(off);
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

registerProcessor('pcm-worklet', PCMWorklet);
registerProcessor('tts-playback-processor', TTSPlaybackProcessor);
