"use client";

import VoiceAgent from "@/components/VoiceAgent";
import PushToTalk from "@/components/PushToTalk";


export default function Home() {
  return (
    <main style={{ padding: '20px' }}>
      <h1>SHCI Voice Assistant</h1>
      <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: '1fr 1fr' }}>
        <div>
          <h2>Voice Agent (Original)</h2>
          <VoiceAgent />
        </div>
        <div>
          <h2>Real-time STT (New)</h2>
          <PushToTalk />
        </div>
      </div>
    </main>
  );
}
