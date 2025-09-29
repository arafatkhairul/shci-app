"use client";
import { useRef, useState } from "react";
import { RSStream } from "../lib/rtsttClient";

export default function PushToTalk() {
  const [status, setStatus] = useState("idle");
  const [partial, setPartial] = useState("");
  const [stab, setStab] = useState("");
  const [finals, setFinals] = useState<string[]>([]);
  const ref = useRef<RSStream|null>(null);

  const start = async () => {
    try {
      setStatus("connecting");
      const url = process.env.NEXT_PUBLIC_STT_WS ?? "ws://localhost:8000/ws/stt";
      const cli = new RSStream({
        onStatus: setStatus,
        onPartial: setPartial,
        onStabilized: setStab,
        onFinal: (t) => setFinals(f => [...f, t]),
        onError: (e) => setStatus(`error: ${e}`)
      });
      ref.current = cli;
      await cli.connect(url);
      // NOTE: RSStream.startAudio() এখন server 'ready' পাওয়া পর্যন্ত ওয়েট করবে
      await cli.startAudio();
    } catch (error) {
      console.error("Failed to start STT:", error);
      setStatus(`error: ${error.message}`);
    }
  };
  
  const stop = () => ref.current?.stop();

  return (
    <div style={{display:'grid', gap:8, padding: '20px', border: '1px solid #ccc', borderRadius: '8px', maxWidth: '500px'}}>
      <h3>Real-time Speech-to-Text</h3>
      <button 
        onClick={start}
        style={{
          padding: '10px 20px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        🎙 Start Recording
      </button>
      <button 
        onClick={stop}
        style={{
          padding: '10px 20px',
          backgroundColor: '#dc3545',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        ⏹ Stop Recording
      </button>
      <div><b>Status:</b> {status}</div>
      <div><b>Partial:</b> {partial}</div>
      <div><b>Stabilized:</b> {stab}</div>
      <div><b>Final:</b> {finals.join(" | ")}</div>
    </div>
  );
}
