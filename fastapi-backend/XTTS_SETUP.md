# XTTS (Coqui TTS) Setup Guide

## Overview
XTTS (Coqui TTS) is now the default text-to-speech system for this application. It provides professional-quality multilingual speech synthesis with voice cloning capabilities.

## Features
- ✅ **Multilingual Support**: 16+ languages including English, Spanish, French, German, etc.
- ✅ **Voice Cloning**: Use custom speaker audio files for personalized voices
- ✅ **High Quality**: Professional-grade speech synthesis
- ✅ **Real-time**: Fast synthesis for live conversations
- ✅ **Configurable**: Adjustable speed, temperature, and other parameters

## Installation

### 1. Install Dependencies
```bash
cd fastapi-backend
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy and configure environment variables:
```bash
cp env_example.txt .env
```

Key XTTS settings in `.env`:
```env
# XTTS Configuration
XTTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2
XTTS_LANGUAGE=en
XTTS_SPEAKER_WAV=
XTTS_SPEED=1.0
XTTS_TEMPERATURE=0.75
TTS_OUTPUT_FORMAT=wav
TTS_SAMPLE_RATE=22050
TTS_USE_CUDA=true
```

### 3. Test Installation
```bash
python test_xtts.py
```

## API Endpoints

### Core TTS Endpoints
- `GET /test-tts` - Test TTS synthesis
- `GET /tts/info` - Get system information
- `GET /tts/health` - Health check

### XTTS Management
- `GET /tts/models` - List available models
- `POST /tts/load-model` - Load specific model
- `POST /tts/set-language` - Set synthesis language
- `POST /tts/set-speaker` - Set speaker reference file
- `POST /tts/set-params` - Update synthesis parameters
- `POST /tts/synthesize` - Synthesize text to speech

## Usage Examples

### Basic Synthesis
```python
from xtts_wrapper import xtts_wrapper

# Initialize
await xtts_wrapper.initialize()

# Synthesize text
audio_bytes = await xtts_wrapper.synthesize_async("Hello world", "en")
```

### Voice Cloning
```python
# Set speaker reference
await xtts_wrapper.set_speaker_async("path/to/speaker.wav")

# Synthesize with cloned voice
audio_bytes = await xtts_wrapper.synthesize_async("Hello world", "en")
```

### Parameter Tuning
```python
# Update synthesis parameters
params = {
    "speed": 1.2,
    "temperature": 0.8,
    "length_penalty": 1.1
}
await xtts_wrapper.update_params_async(**params)
```

## Supported Languages
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `pl` - Polish
- `tr` - Turkish
- `ru` - Russian
- `nl` - Dutch
- `cs` - Czech
- `ar` - Arabic
- `zh` - Chinese
- `ja` - Japanese
- `hu` - Hungarian
- `ko` - Korean

## Performance Tips

### GPU Acceleration
- Set `TTS_USE_CUDA=true` for GPU acceleration
- Requires CUDA-compatible GPU and PyTorch with CUDA support

### Memory Optimization
- XTTS automatically manages memory
- First synthesis may be slower due to model loading
- Subsequent syntheses are faster

### Quality Settings
- **Speed**: 0.5-2.0 (default: 1.0)
- **Temperature**: 0.1-1.0 (default: 0.75)
- **Length Penalty**: 0.1-2.0 (default: 1.0)
- **Repetition Penalty**: 1.0-5.0 (default: 2.0)

## Troubleshooting

### Common Issues

1. **Model Loading Failed**
   - Check internet connection (model downloads automatically)
   - Verify CUDA installation if using GPU
   - Check available disk space

2. **Audio Quality Issues**
   - Adjust temperature parameter (lower = more stable)
   - Try different speed settings
   - Use higher quality speaker reference files

3. **Language Not Supported**
   - Check supported languages list
   - Verify language code format (e.g., "en", not "english")

### Logs
Check application logs for detailed error information:
```bash
tail -f logs/app.log
```

## Migration from StyleTTS2

XTTS has completely replaced StyleTTS2. The migration includes:
- ✅ Automatic model loading
- ✅ Improved multilingual support
- ✅ Better voice cloning capabilities
- ✅ Enhanced API endpoints
- ✅ Professional error handling

## Support

For issues or questions:
1. Check the logs for error details
2. Verify environment configuration
3. Test with the provided test script
4. Review this documentation

---

**XTTS is now your professional text-to-speech solution!** 🎉
