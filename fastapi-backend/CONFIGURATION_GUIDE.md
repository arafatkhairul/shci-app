# Configuration Guide

## 📋 Overview

This project now uses a **single consolidated `.env` file** for all configuration instead of multiple scattered files. This provides better organization, easier management, and reduced confusion.

## 🔧 Configuration Files

### Primary Configuration
- **`.env`** - Main configuration file (all settings)
- **`env.professional`** - Template for professional setup

### Backup Files
- **`tts_config.env.backup`** - Backup of old TTS configuration
- **`env.local`** - Local environment template
- **`env.production`** - Production environment template

## 📊 Configuration Categories

### 🌍 Application Environment
```bash
TTS_ENVIRONMENT=local          # local/development/production/live
ENVIRONMENT=development        # development/production
NODE_ENV=development          # development/production
```

### 🤖 LLM Configuration
```bash
LLM_API_URL=http://69.197.183.130:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu
LLM_API_KEY=                   # Optional API key
LLM_TIMEOUT=10.0              # Request timeout in seconds
LLM_RETRIES=1                 # Number of retries
```

### 🎵 TTS System Configuration
```bash
TTS_SYSTEM=piper              # piper/fallback
```

### 🎯 Piper TTS Configuration
```bash
PIPER_MODEL_NAME=en_GB-cori-medium
PIPER_LENGTH_SCALE=1.5        # Speech speed (1.0 = normal)
PIPER_NOISE_SCALE=3.0       # Voice clarity
PIPER_NOISE_W=0.8             # Voice stability
```

### 🔊 Audio Configuration
```bash
TTS_OUTPUT_FORMAT=wav         # Audio format
TTS_SAMPLE_RATE=22050         # Sample rate in Hz
DEFAULT_LANGUAGE=en           # Default language
```

### 🎤 Voice Activity Detection (VAD)
```bash
TRIGGER_VOICED_FRAMES=2       # Frames to trigger voice detection
END_SILENCE_MS=250            # Silence duration to end speech
MAX_UTTER_MS=7000             # Maximum utterance length
MIN_UTTER_SEC=0.25            # Minimum utterance length
MIN_RMS=0.006                 # Minimum audio level
```

### ⚡ Concurrency Configuration
```bash
STT_CONCURRENCY=1             # Speech-to-text concurrency
TTS_CONCURRENCY=1             # Text-to-speech concurrency
```

### 👤 Assistant Configuration
```bash
ASSISTANT_NAME=Self Hosted Conversational Interface
ASSISTANT_AUTHOR=NZR DEV
```

### 💾 Database Configuration
```bash
MEM_DB_DIR=memdb             # Memory database directory
```

## 🚀 Environment-Specific Configurations

### Development Environment
```bash
TTS_ENVIRONMENT=local
ENVIRONMENT=development
NODE_ENV=development
# Uses CPU for faster startup
```

### Production Environment
```bash
TTS_ENVIRONMENT=production
ENVIRONMENT=production
NODE_ENV=production
# Uses GPU for better performance (if available)
```

## 🔧 Device Configuration (Auto-Detection)

### Automatic Detection
- **Local Environment**: Uses CPU (faster startup)
- **Production Environment**: Uses GPU (better performance)

### Manual Override Options
```bash
# Force specific device
PIPER_DEVICE=cuda             # Force GPU
PIPER_DEVICE=cpu              # Force CPU

# Force device regardless of environment
PIPER_FORCE_CUDA=true         # Force GPU even in local
PIPER_FORCE_CPU=true          # Force CPU even in production
```

## 📝 Configuration Examples

### Basic Development Setup
```bash
TTS_ENVIRONMENT=local
TTS_SYSTEM=piper
PIPER_MODEL_NAME=en_GB-cori-medium
DEFAULT_LANGUAGE=en
```

### Production Setup
```bash
TTS_ENVIRONMENT=production
TTS_SYSTEM=piper
PIPER_MODEL_NAME=en_GB-cori-medium
DEFAULT_LANGUAGE=en
# GPU will be used automatically if available
```

### Custom Audio Setup
```bash
TTS_OUTPUT_FORMAT=wav
TTS_SAMPLE_RATE=22050
PIPER_LENGTH_SCALE=1.2        # Slightly faster speech
PIPER_NOISE_SCALE=3.0         # Clearer voice
```

### High-Performance Setup
```bash
STT_CONCURRENCY=2             # Allow 2 concurrent STT
TTS_CONCURRENCY=2             # Allow 2 concurrent TTS
PIPER_FORCE_CUDA=true         # Force GPU usage
```

## 🔍 Configuration Validation

### Check Current Configuration
```bash
python -c "from main import app; print('✅ Configuration loaded successfully')"
```

### Test TTS Configuration
```bash
python -c "from tts_factory import synthesize_text; audio = synthesize_text('Test', 'en'); print(f'TTS working: {len(audio)} bytes')"
```

### Check Environment Detection
```bash
python -c "from tts_factory import get_tts_info; import json; print(json.dumps(get_tts_info()['providers']['piper']['device_config'], indent=2))"
```

## 🛠️ Configuration Management

### Update Configuration
1. Edit `.env` file
2. Restart the application
3. Check logs for configuration confirmation

### Backup Configuration
```bash
cp .env .env.backup
```

### Restore Configuration
```bash
cp .env.backup .env
```

### Switch Environments
```bash
# Development
sed -i 's/TTS_ENVIRONMENT=production/TTS_ENVIRONMENT=local/' .env

# Production
sed -i 's/TTS_ENVIRONMENT=local/TTS_ENVIRONMENT=production/' .env
```

## 📊 Configuration Logging

The application logs all configuration on startup:

```
🔧 Environment: local (development)
🤖 LLM: http://69.197.183.130:11434/v1/chat/completions (model=qwen2.5-14b-gpu)
🎵 TTS System: piper
🎯 Piper TTS: en_GB-cori-medium (length=1.5, noise=0.667, w=0.8)
🔊 Audio: wav @ 22050Hz, language=en
👤 Assistant: Self Hosted Conversational Interface by NZR DEV
🎤 VAD: trigger=2, silence=250ms, max=7000ms
🔊 Audio: min_utter=0.25s, min_rms=0.006
⚡ Concurrency: STT=1, TTS=1
```

## 🚨 Troubleshooting

### Common Issues

1. **Configuration Not Loading**
   - Check `.env` file exists
   - Verify file permissions
   - Check for syntax errors

2. **TTS Not Working**
   - Verify `TTS_SYSTEM=piper`
   - Check Piper TTS model files
   - Verify device configuration

3. **GPU Not Detected**
   - Check CUDA installation
   - Verify PyTorch CUDA support
   - Use `PIPER_FORCE_CPU=true` as fallback

4. **Audio Issues**
   - Check sample rate configuration
   - Verify audio format settings
   - Test with different audio parameters

### Debug Commands

```bash
# Check environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('TTS_ENVIRONMENT:', os.getenv('TTS_ENVIRONMENT'))"

# Test TTS functionality
python -c "from tts_factory import synthesize_text; print('TTS test:', len(synthesize_text('Test', 'en')), 'bytes')"

# Check device configuration
python -c "from tts_factory import get_tts_info; print('Device:', get_tts_info()['providers']['piper']['device_config']['device_type'])"
```

## 📈 Performance Optimization

### For Development
- Use `TTS_ENVIRONMENT=local`
- Set `STT_CONCURRENCY=1`
- Use CPU for faster startup

### For Production
- Use `TTS_ENVIRONMENT=production`
- Increase concurrency limits
- Enable GPU acceleration
- Optimize audio parameters

---

**Configuration Guide Updated**: September 14, 2025  
**Status**: ✅ Consolidated and optimized
