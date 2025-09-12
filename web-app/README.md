# SHCI Voice Assistant

A professional, self-hosted voice assistant with real-time speech transcription and intelligent conversation output featuring a **typing animation effect**.

## Features

### 🎤 **Real-time Speech Transcription**
- Live microphone input processing
- WebRTC VAD (Voice Activity Detection)
- Whisper-based speech-to-text
- Multi-language support (English & Italian)

### 🤖 **Intelligent Conversation Output**
- **NEW: Typing Animation Effect** - Watch AI responses appear character by character
- LLM-powered intelligent responses
- Context-aware conversations
- Memory persistence across sessions

### 🔊 **Text-to-Speech**
- Server-side TTS (gTTS)
- Local TTS fallback
- Multi-language voice synthesis
- Natural voice interruption support

### 🌐 **Multi-language Support**
- **English** - Full interface and voice support
- **Italian** - Complete localization
- Easy language switching

### 💾 **Memory & Persistence**
- User preferences storage
- Conversation history
- Personal facts and traits
- Cross-session memory

## Typing Animation Feature

The AI response panel now features a realistic typing animation that:

- **Shows text appearing character by character** for a more engaging experience
- **Adjustable typing speed** (currently set to 30ms per character)
- **Smooth cursor animation** with blinking effect
- **Maintains the same visual style** as the rest of the interface
- **Works seamlessly** with the existing AI response system

### How It Works

1. When an AI response is received via WebSocket
2. The `isTyping` state is activated
3. Text appears gradually using `setTimeout` with configurable delays
4. A blinking cursor (`|`) shows the typing progress
5. Once complete, the full response is displayed in the styled panels

## Getting Started

### Prerequisites
- Node.js 18+ and Yarn
- Python 3.8+ with virtual environment
- Microphone access

### Installation

1. **Frontend (Next.js)**
   ```bash
   cd web-app
   yarn install
   yarn dev
   ```

2. **Backend (FastAPI)**
   ```bash
   cd fastapi-backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

3. **Environment Setup**
   - Set `LLM_API_URL` for your LLM service
   - Configure `WHISPER_MODEL` and device settings
   - Set `DEFAULT_LANGUAGE` (en/it)

### Usage

1. Open `http://localhost:3000` in your browser
2. Allow microphone permissions
3. Click "Start Conversation"
4. Speak naturally - watch your words appear in real-time
5. **Experience the typing animation** as AI responds
6. Switch languages using the language toggle

## Architecture

- **Frontend**: Next.js 15 + React 19 + Tailwind CSS
- **Backend**: FastAPI + WebSocket + Whisper + gTTS
- **Audio Processing**: WebRTC VAD + PCM16 downsampling
- **AI Integration**: REST API + WebSocket streaming
- **Memory**: JSON-based persistent storage

## Customization

### Typing Speed
Modify the typing speed in `VoiceAgent.tsx`:
```typescript
typingTimerRef.current = setTimeout(typeNextChar, 30); // 30ms = fast, 50ms = medium, 80ms = slow
```

### Language Support
Add new languages in the `languages` object with proper translations.

### Styling
Customize the typing animation appearance using Tailwind CSS classes.

## Testing

- **Typing Animation Demo**: `test-typing.html` - Standalone demo of the typing effect
- **Voice Testing**: Use the "Test AI Response" and "Test Server TTS" buttons
- **Language Testing**: Switch between English and Italian

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Professional • Self-Hosted • Intelligent

---

**Note**: This is a professional voice assistant system designed for self-hosting. Ensure proper security measures when deploying in production environments.
