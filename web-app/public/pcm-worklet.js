// public/pcm-worklet.js
class PCMWorklet extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opt = (options && options.processorOptions) || {};
    this.targetRate = opt.targetSampleRate || 16000;
    this.frameSize = opt.frameSize || 320; // 20ms @16k
    this._residual = new Int16Array(0);
    // small ring buffer for safety
    this._tmp = new Int16Array(this.frameSize);
  }
  static get parameterDescriptors() { return []; }

  // Average-downsample mono Float32 -> Int16 @ targetRate
  _downsample(float32) {
    if (!float32 || float32.length === 0) return new Int16Array(0);
    const ratio = sampleRate / this.targetRate; // sampleRate = AudioContext rate (likely 48000)
    const outLen = Math.floor(float32.length / ratio);
    const out = new Int16Array(outLen);

    let i = 0;
    let acc = 0, count = 0, next = 0;
    for (let n = 0; n < float32.length; n++) {
      acc += float32[n];
      count++;
      if (n >= next) {
        const v = acc / count;
        out[i++] = Math.max(-1, Math.min(1, v)) * 0x7FFF;
        acc = 0; count = 0;
        next = Math.floor((i + 1) * ratio) - 1;
      }
    }
    return (i === outLen) ? out : out.subarray(0, i);
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    // Use first channel (mono). If multiple channels, average.
    let ch0 = input[0];
    if (!ch0 || ch0.length === 0) return true;

    // Downsample to 16k, convert to Int16
    const ds = this._downsample(ch0);

    // Concat residual + new
    const buf = new Int16Array(this._residual.length + ds.length);
    buf.set(this._residual, 0);
    buf.set(ds, this._residual.length);

    // Emit exact 20ms frames without transferring buf's buffer
    let off = 0;
    while (off + this.frameSize <= buf.length) {
      // COPY the slice into a fresh Int16Array so transferring won't detach buf
      this._tmp.set(buf.subarray(off, off + this.frameSize));
      const frameCopy = new Int16Array(this._tmp); // allocate its own buffer
      this.port.postMessage({ type: 'audio-16k', pcm: frameCopy }, [frameCopy.buffer]);
      off += this.frameSize;
    }

    // Keep the leftover as residual (safe: we never transferred buf.buffer)
    this._residual = buf.subarray(off);
    return true;
  }
}

registerProcessor('pcm-worklet', PCMWorklet);
