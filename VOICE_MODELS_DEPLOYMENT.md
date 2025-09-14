# Voice Models Deployment Guide

## 🎤 Automatic Voice Model Download System

The SHCI voice system automatically handles voice model files on the server without requiring manual installation.

### ✅ **How It Works**

1. **Automatic Detection**: When a voice is selected, the system checks if the model files exist
2. **Automatic Download**: If files are missing, they are downloaded from Hugging Face
3. **Caching**: Downloaded files are cached locally for future use
4. **No Manual Setup**: No need to pre-install voice models on the server

### 📁 **Voice Model Files**

The system uses 4 voice models:

#### **Male Voices**:
- `en_US-hfc_male-medium.onnx` (60.27 MB) - Ryan (Male) Medium
- `en_US-ryan-high.onnx` (115.19 MB) - Ryan (Male) High

#### **Female Voices**:
- `en_US-libritts_r-medium.onnx` (60.27 MB) - Sarah (Female) Medium  
- `en_US-ljspeech-high.onnx` (108.91 MB) - David (Female) High

#### **Configuration Files**:
- `*.onnx.json` - Model configuration files (~1-2 KB each)

### 🔄 **Download Process**

```python
def _download_if_missing(self, path: str, url: str):
    """Download model files if missing."""
    if os.path.exists(path):
        log.info(f"[SKIP] {path} already exists")
        return
    
    log.info(f"[DOWNLOAD] {path} downloading...")
    # Downloads from Hugging Face automatically
```

### 🌐 **Download Sources**

All models are downloaded from Hugging Face:
- **Base URL**: `https://huggingface.co/rhasspy/piper-voices/resolve/main/`
- **Reliable**: Hugging Face provides stable, fast downloads
- **Automatic**: No manual intervention required

### 🚀 **Server Deployment**

#### **What Happens During Deployment**:

1. **Code Deployment**: Only code changes are pushed to git
2. **Dependencies**: `piper-tts` and `requests` are installed via requirements.txt
3. **First Voice Use**: When a voice is first selected, models are downloaded automatically
4. **Caching**: Models are cached in the `fastapi-backend/` directory
5. **Subsequent Uses**: No re-downloading needed

#### **Deployment Commands**:
```bash
# The deploy.sh script handles everything automatically
./deploy.sh
```

### 📊 **Performance Impact**

#### **First Time Setup**:
- **Download Time**: 2-5 minutes (depending on server speed)
- **Storage**: ~400 MB total for all 4 voices
- **Memory**: Models loaded into memory when active

#### **Subsequent Uses**:
- **Instant**: No download time
- **Fast**: Models already cached locally
- **Efficient**: Only active voice loaded in memory

### 🛡️ **Error Handling**

#### **Download Failures**:
- **Retry Logic**: Automatic retry on network issues
- **Fallback**: System falls back to available voices
- **Logging**: Detailed error logs for debugging

#### **Missing Dependencies**:
- **Requirements**: `piper-tts==1.3.0` and `requests==2.32.5`
- **Installation**: Handled by deployment script
- **Verification**: Deployment script verifies TTS system status

### 🔧 **Configuration**

#### **Environment Variables**:
```bash
# Optional: Override default voice
PIPER_VOICE=en_US-libritts_r-medium

# Optional: Override speech speed
PIPER_LENGTH_SCALE=0.8

# Optional: Force CPU usage
PIPER_FORCE_CPU=true
```

#### **Default Settings**:
- **Default Voice**: Sarah (Female) - `en_US-libritts_r-medium`
- **Speech Speed**: 0.8 (faster than default 1.5)
- **Device**: Auto-detects GPU/CPU

### ✅ **Verification Commands**

#### **Check TTS Status**:
```bash
cd /root/shci-app/fastapi-backend
python -c "from tts_factory import TTSFactory; print(TTSFactory().get_info())"
```

#### **Test Voice Generation**:
```bash
python -c "
from tts_factory import synthesize_text
audio = synthesize_text('Hello world!', 'en', 'en_US-libritts_r-medium')
print(f'Generated {len(audio)} bytes of audio')
"
```

### 🎯 **Summary**

✅ **No Manual Setup Required**: Voice models download automatically
✅ **Server Ready**: Works on any server with internet access  
✅ **Fast Deployment**: Only code changes need to be pushed
✅ **Reliable**: Hugging Face provides stable model hosting
✅ **Efficient**: Models cached locally after first download
✅ **Error Handling**: Robust error handling and fallbacks

The voice system is fully automated and server-ready! 🚀
