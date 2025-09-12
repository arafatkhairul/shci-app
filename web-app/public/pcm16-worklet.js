// public/pcm16-worklet.js
class PCM16DownsamplerProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.buffer = new Float32Array(0);
        this.decim = 3; // 48k -> 16k
        this.tmp = new Float32Array(0);
        this.muted = false;           // hard gate while agent speaks
        this.userHotFrames = 0;       // for barge-in help (optional)
        this.playbackActive = false;  // set from main thread

        this.port.onmessage = (ev) => {
            const { type, value } = ev.data || {};
            if (type === "mute") this.muted = !!value;
            if (type === "playback") this.playbackActive = !!value; // analyser hint
        };
    }

    downsample(input) {
        const inLen = input.length;
        const outLen = Math.floor(inLen / this.decim);
        const out = new Float32Array(outLen);
        let j = 0;
        for (let i = 0; i + (this.decim - 1) < inLen; i += this.decim) out[j++] = input[i];
        return out;
    }

    floatTo16(f32) {
        const out = new Int16Array(f32.length);
        for (let i = 0; i < f32.length; i++) {
            let s = Math.max(-1, Math.min(1, f32[i]));
            out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        return out;
    }

    rms(x) {
        let s = 0;
        for (let i = 0; i < x.length; i++) s += x[i] * x[i];
        return Math.sqrt(s / Math.max(1, x.length));
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        // mono mix
        const ch0 = input[0] || new Float32Array(128);
        let mono;
        if (input.length === 1) mono = ch0;
        else {
            const n = ch0.length;
            mono = new Float32Array(n);
            for (let i = 0; i < n; i++) {
                let sum = 0;
                for (let c = 0; c < input.length; c++) sum += input[c][i] || 0;
                mono[i] = sum / input.length;
            }
        }

        // append
        const joined = new Float32Array(this.buffer.length + mono.length);
        joined.set(this.buffer, 0);
        joined.set(mono, this.buffer.length);
        this.buffer = joined;

        // decimation-aligned processing
        const processLen = this.buffer.length - (this.buffer.length % this.decim);
        if (processLen > 0) {
            const block = this.buffer.subarray(0, processLen);
            const ds = this.downsample(block);

            // accumulate
            if (this.tmp.length) {
                const merged = new Float32Array(this.tmp.length + ds.length);
                merged.set(this.tmp, 0);
                merged.set(ds, this.tmp.length);
                this.tmp = merged;
            } else this.tmp = ds;

            const FRAME = 480; // 30ms @ 16k
            let off = 0;
            while (this.tmp.length - off >= FRAME) {
                const slice = this.tmp.subarray(off, off + FRAME);
                const level = this.rms(slice);
                // Enhanced RMS calculation with better sensitivity
                const enhancedLevel = Math.min(level * 2, 1.0); // Amplify signal for better detection
                this.port.postMessage({ type: "rms", value: enhancedLevel });

                // HARD RULES:
                // 1) if muted -> drop
                // 2) if playbackActive and level is low -> likely just speaker tail -> drop
                // 3) else send
                const LOW = 0.015; // tweak if environment noisy
                if (!this.muted) {
                    if (!(this.playbackActive && level < LOW)) {
                        const i16 = this.floatTo16(slice);
                        const ab = i16.buffer;
                        this.port.postMessage({ type: "frame", buffer: ab }, [ab]);
                    }
                }

                off += FRAME;
            }
            if (off > 0) this.tmp = this.tmp.subarray(off);
            this.buffer = this.buffer.subarray(processLen);
        }

        return true;
    }
}
registerProcessor("pcm16-downsampler", PCM16DownsamplerProcessor);
