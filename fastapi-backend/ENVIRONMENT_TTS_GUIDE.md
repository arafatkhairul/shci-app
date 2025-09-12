# Environment-Based TTS Configuration Guide

## Overview

This system provides intelligent TTS (Text-to-Speech) configuration that automatically selects the appropriate TTS system based on your environment:

- **Local/Development**: Uses gTTS (Google Text-to-Speech) for fast, lightweight synthesis
- **Production/Live**: Uses Coqui TTS with reference audio support for high-quality voice cloning

## Quick Setup

### 1. Environment Configuration

Create a `.env` file based on your environment:

#### For Local Development:
```bash
# Copy from tts_config.env
cp tts_config.env .env

# Local development settings
TTS_ENVIRONMENT=local
ENVIRONMENT=development
DEV_MODE=true
```

#### For Production/Live:
```bash
# Production settings
TTS_ENVIRONMENT=production
ENVIRONMENT=production
TTS_SYSTEM=coqui
DEV_MODE=false
```

### 2. Install Dependencies

#### For Local Development (gTTS):
```bash
pip install gtts pygame pydub
```

#### For Production (Coqui TTS):
```bash
pip install TTS torch torchaudio soundfile numpy
```

### 3. Start the Server

```bash
python main.py
```

The system will automatically detect your environment and initialize the appropriate TTS system.

## Environment Detection

The system automatically detects your environment using these methods:

1. **Explicit Configuration**: `TTS_ENVIRONMENT` environment variable
2. **Standard Environment Variables**: `ENVIRONMENT`, `NODE_ENV`
3. **Auto-detection**: Falls back to local if not specified

### Environment Types

| Environment | TTS System | Use Case |
|-------------|------------|----------|
| `local` | gTTS | Development, testing |
| `development` | gTTS | Development, testing |
| `production` | Coqui TTS | Live deployment |
| `live` | Coqui TTS | Live deployment |

## TTS Systems

### 1. gTTS (Local/Development)

**Advantages:**
- ✅ Fast setup and initialization
- ✅ No model downloads required
- ✅ Good quality for development
- ✅ Multiple language support
- ✅ Lightweight

**Configuration:**
```bash
# gTTS settings
GTTS_ENABLED=true
GTTS_LANG=en
GTTS_SLOW=false
GTTS_TLD=com
```

**Usage:**
```python
from tts_factory import synthesize_text, TTSSystem

# Use gTTS explicitly
audio = synthesize_text("Hello world", system=TTSSystem.GTTS)
```

### 2. Coqui TTS (Production/Live)

**Advantages:**
- ✅ High-quality voice synthesis
- ✅ Voice cloning with reference audio
- ✅ Offline operation
- ✅ Customizable voices
- ✅ Professional quality

**Configuration:**
```bash
# Coqui TTS settings
TTS_MODEL_NAME=tts_models/multilingual/multi-dataset/xtts_v2
TTS_SPEAKER_WAV=00005.wav
TTS_LANGUAGE=en
TTS_SPEED=1.0
```

**Usage:**
```python
from tts_factory import synthesize_text, TTSSystem

# Use Coqui TTS with reference audio
audio = synthesize_text(
    "Hello world", 
    system=TTSSystem.COQUI,
    speaker_wav="path/to/speaker.wav"
)
```

### 3. Fallback TTS

**Use Case:**
- System TTS when other options fail
- Emergency fallback
- Basic functionality

## API Endpoints

### Get TTS Information
```bash
GET /tts-info
```

Response:
```json
{
  "status": "success",
  "tts_info": {
    "environment": "local",
    "preferred_system": "gtts",
    "available_providers": ["gtts", "fallback"],
    "providers": {
      "gtts": {
        "name": "Google Text-to-Speech (gTTS)",
        "available": true,
        "system_type": "gTTS",
        "environment": "local/development"
      }
    }
  }
}
```

### Test TTS System
```bash
POST /tts-test
Content-Type: application/json

{
  "text": "Hello, world!",
  "language": "en",
  "speaker_wav": "path/to/speaker.wav",
  "tts_system": "gtts"
}
```

### Test TTS Streaming
```bash
POST /tts-streaming-test
Content-Type: application/json

{
  "text": "Hello, world!",
  "language": "en",
  "speaker_wav": "path/to/speaker.wav"
}
```

## Configuration Examples

### Local Development Setup

```bash
# .env file for local development
TTS_ENVIRONMENT=local
ENVIRONMENT=development
DEV_MODE=true

# gTTS configuration
GTTS_ENABLED=true
GTTS_LANG=en

# Optional: Override to use Coqui TTS locally
# TTS_SYSTEM=coqui
```

### Production Setup

```bash
# .env file for production
TTS_ENVIRONMENT=production
ENVIRONMENT=production
TTS_SYSTEM=coqui
DEV_MODE=false

# Coqui TTS configuration
TTS_MODEL_NAME=tts_models/multilingual/multi-dataset/xtts_v2
TTS_SPEAKER_WAV=00005.wav
TTS_LANGUAGE=en
TTS_DEVICE=cuda
TTS_PRECISION=fp16
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Install dependencies based on environment
ARG TTS_ENVIRONMENT=production
RUN if [ "$TTS_ENVIRONMENT" = "production" ]; then \
        pip install TTS torch torchaudio soundfile numpy; \
    else \
        pip install gtts pygame pydub; \
    fi

# Set environment
ENV TTS_ENVIRONMENT=$TTS_ENVIRONMENT

WORKDIR /app
COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

```bash
# Build for production
docker build --build-arg TTS_ENVIRONMENT=production -t tts-app .

# Build for development
docker build --build-arg TTS_ENVIRONMENT=local -t tts-app-dev .
```

## Usage Examples

### Python Code

```python
from tts_factory import (
    tts_factory, 
    synthesize_text, 
    synthesize_text_async,
    get_tts_info,
    TTSSystem
)

# Get current TTS system info
info = get_tts_info()
print(f"Using TTS system: {info['preferred_system']}")

# Synthesize text (uses preferred system)
audio = synthesize_text("Hello, world!")

# Synthesize with specific system
audio = synthesize_text("Hello, world!", system=TTSSystem.GTTS)

# Async synthesis
audio = await synthesize_text_async("Hello, world!")

# With reference audio (Coqui TTS only)
audio = synthesize_text(
    "Hello, world!", 
    speaker_wav="path/to/speaker.wav"
)
```

### WebSocket Integration

```javascript
// Frontend JavaScript
const ws = new WebSocket('ws://localhost:8000/ws');

// Start TTS stream
ws.send(JSON.stringify({
  type: 'start_tts_stream',
  stream_id: 'test_stream',
  text: 'Hello, world!',
  language: 'en',
  speaker_wav: 'path/to/speaker.wav'  // Optional
}));

// Handle responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'stream_start') {
    console.log('TTS stream started');
  } else if (data.type === 'audio_chunk') {
    console.log(`Received audio chunk ${data.chunk_index + 1}/${data.total_chunks}`);
  } else if (data.type === 'stream_complete') {
    console.log('TTS stream completed');
  }
};
```

## Troubleshooting

### Common Issues

1. **gTTS Not Working**:
   ```bash
   # Install missing dependencies
   pip install gtts pygame pydub
   
   # Check internet connection (gTTS requires internet)
   ```

2. **Coqui TTS Not Loading**:
   ```bash
   # Install Coqui TTS
   pip install TTS torch torchaudio
   
   # Check CUDA availability
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. **Environment Not Detected**:
   ```bash
   # Set explicit environment
   export TTS_ENVIRONMENT=local
   export TTS_SYSTEM=gtts
   ```

4. **Reference Audio Not Found**:
   ```bash
   # Check file path
   ls -la 00005.wav
   
   # Update configuration
   TTS_SPEAKER_WAV=/full/path/to/speaker.wav
   ```

### Debug Mode

Enable debug logging:

```bash
# Enable debug mode
DEBUG_TTS=true
TTS_VERBOSE_LOGGING=true

# Check logs
tail -f logs/tts.log
```

### Performance Monitoring

```python
# Get TTS system performance info
info = get_tts_info()
print(f"Available providers: {info['available_providers']}")
print(f"Current system: {info['preferred_system']}")

# Test different systems
for system in ['gtts', 'coqui', 'fallback']:
    try:
        audio = synthesize_text("Test", system=TTSSystem(system))
        print(f"{system}: {len(audio)} bytes")
    except Exception as e:
        print(f"{system}: Error - {e}")
```

## Migration Guide

### From Single TTS System

If you're migrating from a single TTS system:

1. **Update imports**:
   ```python
   # Old
   from xtts_manager import xtts_manager
   
   # New
   from tts_factory import synthesize_text, get_tts_info
   ```

2. **Update synthesis calls**:
   ```python
   # Old
   audio = xtts_manager.synthesize_text(text, language, speaker_wav)
   
   # New
   audio = synthesize_text(text, language, speaker_wav=speaker_wav)
   ```

3. **Add environment configuration**:
   ```bash
   # Add to .env
   TTS_ENVIRONMENT=local  # or production
   ```

### From gTTS to Coqui TTS

1. **Install Coqui TTS**:
   ```bash
   pip install TTS torch torchaudio
   ```

2. **Update environment**:
   ```bash
   TTS_ENVIRONMENT=production
   TTS_SYSTEM=coqui
   ```

3. **Add reference audio**:
   ```bash
   TTS_SPEAKER_WAV=path/to/speaker.wav
   ```

## Best Practices

### Development
- Use gTTS for fast iteration
- Test with different languages
- Use debug mode for troubleshooting

### Production
- Use Coqui TTS for quality
- Pre-load models for performance
- Monitor system resources
- Use reference audio for consistent voice

### Deployment
- Set appropriate environment variables
- Use Docker for consistent environments
- Monitor TTS system performance
- Have fallback systems ready

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review environment configuration
3. Test with different TTS systems
4. Check logs for detailed error messages

---

**Note**: This system automatically handles TTS system selection based on your environment, providing the best experience for both development and production use cases.
