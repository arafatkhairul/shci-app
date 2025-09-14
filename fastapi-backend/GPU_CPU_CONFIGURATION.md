# GPU/CPU Configuration for Piper TTS

এই প্রজেক্টে **Piper TTS** এর জন্য স্বয়ংক্রিয় GPU/CPU detection এবং configuration যোগ করা হয়েছে।

## 🎯 Auto-Detection Logic

### Environment-Based Detection:
- **Local Environment**: CPU ব্যবহার করে (দ্রুত startup)
- **Production Environment**: GPU ব্যবহার করে (উচ্চ performance)

### Manual Override Options:
- **Force CPU**: যেকোনো environment এ CPU ব্যবহার করুন
- **Force GPU**: যেকোনো environment এ GPU ব্যবহার করুন

## 🔧 Configuration Options

### Environment Variables:

```bash
# Environment Detection
TTS_ENVIRONMENT=local          # CPU ব্যবহার করবে
TTS_ENVIRONMENT=production    # GPU ব্যবহার করবে (যদি available হয়)

# Manual Device Selection
PIPER_DEVICE=cuda            # Force GPU
PIPER_DEVICE=cpu             # Force CPU

# Force Override
PIPER_FORCE_CUDA=true        # Force GPU even in local
PIPER_FORCE_CPU=true         # Force CPU even in production
```

### Configuration Examples:

#### Local Development (CPU):
```bash
export TTS_ENVIRONMENT=local
# Auto-detected: CPU ব্যবহার করবে
```

#### Production Server (GPU):
```bash
export TTS_ENVIRONMENT=production
# Auto-detected: GPU ব্যবহার করবে (যদি available হয়)
```

#### Force CPU in Production:
```bash
export TTS_ENVIRONMENT=production
export PIPER_FORCE_CPU=true
# Force: CPU ব্যবহার করবে
```

#### Force GPU in Local:
```bash
export TTS_ENVIRONMENT=local
export PIPER_FORCE_CUDA=true
# Force: GPU ব্যবহার করবে (যদি available হয়)
```

## 📊 Device Information

### TTS Info API:
```bash
curl http://localhost:8000/tts/info
```

Response:
```json
{
  "tts_system": "Piper TTS",
  "info": {
    "providers": {
      "piper": {
        "device_config": {
          "use_cuda": false,
          "device_type": "CPU",
          "device_name": "CPU",
          "cuda_available": false,
          "cuda_device_count": 0
        }
      }
    }
  }
}
```

### Health Check API:
```bash
curl http://localhost:8000/tts/health
```

Response:
```json
{
  "status": "healthy",
  "tts_system": "piper",
  "available_providers": ["piper", "fallback"],
  "environment": "local"
}
```

## 🚀 Performance Comparison

### CPU Mode (Local):
- **Startup Time**: দ্রুত
- **Memory Usage**: কম
- **Synthesis Speed**: মাঝারি
- **Best For**: Development, testing

### GPU Mode (Production):
- **Startup Time**: ধীর (model loading)
- **Memory Usage**: বেশি
- **Synthesis Speed**: দ্রুত
- **Best For**: Production, high load

## 🔍 CUDA Detection

### Automatic Detection:
1. **PyTorch Check**: `torch.cuda.is_available()`
2. **Device Count**: `torch.cuda.device_count()`
3. **Device Name**: `torch.cuda.get_device_name(0)`

### Fallback Behavior:
- CUDA unavailable → CPU ব্যবহার করবে
- GPU loading failed → CPU fallback
- Manual override → নির্দিষ্ট device ব্যবহার করবে

## 📝 Logging

### Device Detection Logs:
```
🔧 Device: CPU (CPU)
🔧 CUDA: Disabled
[DEVICE] Using CPU
[OK] Model loaded successfully with CPU
```

### GPU Mode Logs:
```
🔧 Device: GPU (NVIDIA GeForce RTX 3080)
🔧 CUDA: Enabled
[DEVICE] Using GPU
[OK] Model loaded successfully with GPU acceleration
```

## 🛠️ Troubleshooting

### Common Issues:

1. **CUDA Not Available**:
   ```
   ⚠️ CUDA not available - using CPU
   ```
   **Solution**: Install CUDA toolkit or use CPU mode

2. **GPU Loading Failed**:
   ```
   GPU loading failed, falling back to CPU
   ```
   **Solution**: Check GPU memory or use CPU mode

3. **Manual Override Not Working**:
   ```
   🔧 Force CPU enabled
   ```
   **Solution**: Check environment variables

### Debug Commands:

```bash
# Check CUDA availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Check device info
python -c "from tts_factory import get_tts_info; import json; print(json.dumps(get_tts_info()['providers']['piper']['device_config'], indent=2))"

# Test synthesis
python -c "from tts_factory import synthesize_text; audio = synthesize_text('Test', 'en'); print(f'Synthesis: {len(audio)} bytes')"
```

## 🎯 Best Practices

### Development:
```bash
export TTS_ENVIRONMENT=local
# Fast startup, CPU usage
```

### Production:
```bash
export TTS_ENVIRONMENT=production
# High performance, GPU usage (if available)
```

### Docker:
```bash
# CPU-only container
export PIPER_FORCE_CPU=true

# GPU-enabled container
export PIPER_FORCE_CUDA=true
```

## 📈 Monitoring

### Performance Metrics:
- **Synthesis Time**: Monitor via logs
- **Memory Usage**: Check system resources
- **GPU Utilization**: Use `nvidia-smi`

### Health Checks:
- **TTS Health**: `/tts/health`
- **Device Status**: `/tts/info`
- **Synthesis Test**: `/test-tts`

---

**Note**: এই configuration system স্বয়ংক্রিয়ভাবে আপনার environment detect করে এবং optimal device select করে। Manual override options দিয়ে আপনি যেকোনো সময় device change করতে পারেন।
