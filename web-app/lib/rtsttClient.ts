// lib/rtsttClient.ts
export interface RSEvents {
  onPartial?: (text: string) => void;
  onStabilized?: (text: string) => void;
  onFinal?: (text: string) => void;
  onStatus?: (status: string) => void;
  onError?: (error: string) => void;
}

export class RSStream {
  private ws: WebSocket | null = null;
  private ac: AudioContext | null = null;
  private node: AudioWorkletNode | null = null;
  private src: MediaStreamAudioSourceNode | null = null;
  private sink: GainNode | null = null;
  private connected = false;
  private ready = false;
  private events: RSEvents;

  constructor(events: RSEvents = {}) {
    this.events = events;
  }

  async connect(wsUrl: string, language: string = "en"): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);
        this.ws.binaryType = "arraybuffer";

        this.ws.onopen = () => { 
          this.connected = true; 
          // Send language parameter immediately after connection
          this.ws?.send(JSON.stringify({ language: language }));
          resolve(); 
        };
        this.ws.onerror = (e) => { this.events.onError?.("ws error"); reject(e); };

        this.ws.onmessage = (ev) => {
          // server always sends JSON control (status/partial/stabilized/final)
          try {
            const data = JSON.parse(ev.data);
            switch (data.type) {
              case "status":
                this.events.onStatus?.(data.text);
                if (data.text === "ready") this.ready = true;
                break;
              case "partial": this.events.onPartial?.(data.text); break;
              case "stabilized": this.events.onStabilized?.(data.text); break;
              case "final": this.events.onFinal?.(data.text); break;
              case "error": this.events.onError?.(data.text); break;
            }
          } catch { /* ignore non-JSON (e.g., future audio bytes) */ }
        };

        this.ws.onclose = () => { this.connected = false; this.ready = false; };
      } catch (e) { reject(e); }
    });
  }

  async startAudio(): Promise<void> {
    if (!this.connected) throw new Error("WS not connected");

    // Wait for 'ready' (server finished model init)
    if (!this.ready) {
      // passive wait up to 5s
      const started = await new Promise<boolean>(res => {
        const t = setTimeout(() => res(false), 5000);
        const off = this.onStatus((s) => {
          if (s === "ready") { clearTimeout(t); off(); res(true); }
        });
      });
      if (!started) throw new Error("Server not ready");
    }

    // iOS/Safari: don't force 16k; keep default (usually 48k) and downsample in worklet
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: { ideal: 1 },
        echoCancellation: { ideal: true },
        noiseSuppression: { ideal: true },
        autoGainControl: { ideal: true }
      }
    });

    const AC: any = (window as any).webkitAudioContext || AudioContext;
    this.ac = new AC();
    if (!this.ac) throw new Error("Failed to create AudioContext");
    if (this.ac.state === "suspended") await this.ac.resume();

    await this.ac!.audioWorklet.addModule("/pcm-worklet.js"); // <-- keep name consistent
    this.src = new MediaStreamAudioSourceNode(this.ac!, { mediaStream: stream });
    this.node = new AudioWorkletNode(this.ac!, "pcm-worklet", {
      processorOptions: { targetSampleRate: 16000, frameSize: 320 } // 20ms @16k
    });

    // sink to keep graph alive but silent
    this.sink = new GainNode(this.ac!, { gain: 0 });
    this.node.connect(this.sink).connect(this.ac!.destination);
    this.src.connect(this.node);

    this.node.port.onmessage = (e) => {
      // EXPECT: { type: 'audio-16k', pcm: Int16Array }
      if (e.data?.type === "audio-16k" && this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(e.data.pcm.buffer); // raw 16-bit mono @16k
      }
    };
  }

  stopAudio(): void {
    try { this.src?.disconnect(); } catch { }
    try { this.node?.disconnect(); } catch { }
    try { this.sink?.disconnect(); } catch { }
    try { this.ac?.close(); } catch { }
    this.src = this.node = this.sink = this.ac = null;
  }

  disconnect(): void {
    this.stopAudio();
    try { this.ws?.close(); } catch { }
    this.ws = null;
    this.connected = this.ready = false;
  }

  // utility: subscribe to status
  onStatus(fn: (s: string) => void) {
    const prev = this.events.onStatus;
    this.events.onStatus = (s) => { prev?.(s); fn(s); };
    return () => { this.events.onStatus = prev; };
  }
}
