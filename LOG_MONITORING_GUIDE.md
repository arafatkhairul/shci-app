# Backend Service Log Monitoring Guide

## 🔍 Quick Commands

### Service Status
```bash
# Check if service is running
sudo systemctl status fastapi-app.service

# Check service status with our script
./monitor-logs.sh status
```

### View Logs
```bash
# Recent logs (last 50 lines)
sudo journalctl -u fastapi-app.service -n 50

# Today's logs
sudo journalctl -u fastapi-app.service --since today

# Follow logs in real-time
sudo journalctl -u fastapi-app.service -f

# Using our script
./monitor-logs.sh logs      # Recent logs
./monitor-logs.sh follow    # Real-time logs
./monitor-logs.sh today     # Today's logs
```

### Error Monitoring
```bash
# Show only errors
sudo journalctl -u fastapi-app.service --since today | grep -i "error\|exception\|failed"

# Using our script
./monitor-logs.sh errors
```

### Service Control
```bash
# Restart service
sudo systemctl restart fastapi-app.service

# Stop service
sudo systemctl stop fastapi-app.service

# Start service
sudo systemctl start fastapi-app.service

# Using our script
./monitor-logs.sh restart
./monitor-logs.sh stop
./monitor-logs.sh start
```

## 📊 Log Analysis

### Filter by Time
```bash
# Last hour
sudo journalctl -u fastapi-app.service --since "1 hour ago"

# Last 10 minutes
sudo journalctl -u fastapi-app.service --since "10 minutes ago"

# Specific date
sudo journalctl -u fastapi-app.service --since "2024-01-01" --until "2024-01-02"
```

### Filter by Priority
```bash
# Only errors and critical messages
sudo journalctl -u fastapi-app.service -p err

# Errors and warnings
sudo journalctl -u fastapi-app.service -p warning
```

### Search in Logs
```bash
# Search for specific text
sudo journalctl -u fastapi-app.service | grep "TTS"

# Search for startup logs
sudo journalctl -u fastapi-app.service | grep "STARTING UP"

# Search for GPU/CPU detection
sudo journalctl -u fastapi-app.service | grep "DEVICE CONFIGURATION"
```

## 🚀 Beautiful Startup Logs

Your service now shows comprehensive startup information:

```
================================================================================
🚀 SHCI VOICE ASSISTANT - STARTING UP
================================================================================

📊 SYSTEM STATUS:
   Environment: LOCAL/PRODUCTION
   TTS System: PIPER
   Available Providers: piper, fallback

🖥️  DEVICE CONFIGURATION:
   Device Type: CPU/GPU
   Device Name: CPU/NVIDIA GeForce RTX 3080
   CUDA Available: ✅ YES / ❌ NO
   CUDA Devices: 0/1/2
   Using CUDA: ✅ YES / ❌ NO
   Performance: 🚀 GPU ACCELERATED / 💻 CPU OPTIMIZED

🎵 TTS CONFIGURATION:
   Model: en_US-ljspeech-high
   Sample Rate: 22050 Hz
   Length Scale: 1.5
   Noise Scale: 0.667
   Noise W: 0.8

📈 PERFORMANCE SUMMARY:
   🚀 GPU ACCELERATION: ENABLED/DISABLED
   ⚡ Performance: HIGH/OPTIMIZED
   🎯 Optimization: PRODUCTION/DEVELOPMENT
```

## 🔧 Troubleshooting

### Service Not Starting
```bash
# Check service status
sudo systemctl status fastapi-app.service

# Check detailed logs
sudo journalctl -u fastapi-app.service --no-pager

# Check for errors
sudo journalctl -u fastapi-app.service --since today | grep -i error
```

### Performance Issues
```bash
# Check GPU detection
sudo journalctl -u fastapi-app.service | grep "CUDA"

# Check TTS system
sudo journalctl -u fastapi-app.service | grep "TTS System"

# Check environment
sudo journalctl -u fastapi-app.service | grep "Environment"
```

### Configuration Issues
```bash
# Check configuration loading
sudo journalctl -u fastapi-app.service | grep "Configuration"

# Check environment variables
sudo journalctl -u fastapi-app.service | grep "Environment:"
```

## 📱 Monitoring Script Usage

### Available Commands
```bash
./monitor-logs.sh status     # Check service status
./monitor-logs.sh logs       # Show recent logs
./monitor-logs.sh follow     # Follow logs in real-time
./monitor-logs.sh today      # Show today's logs
./monitor-logs.sh errors     # Show only errors
./monitor-logs.sh restart    # Restart service
./monitor-logs.sh stop       # Stop service
./monitor-logs.sh start      # Start service
./monitor-logs.sh summary    # Show log summary
```

### Examples
```bash
# Quick status check
./monitor-logs.sh status

# Watch logs in real-time
./monitor-logs.sh follow

# Check for errors
./monitor-logs.sh errors

# Restart if needed
./monitor-logs.sh restart
```

## 🎯 Key Information to Look For

### Successful Startup
- ✅ TTS system initialization complete
- 🎉 SERVER READY TO ACCEPT CONNECTIONS!
- Environment: LOCAL/PRODUCTION
- Device Type: CPU/GPU
- Performance: GPU ACCELERATED/CPU OPTIMIZED

### Common Issues
- ❌ TTS startup error
- ❌ CUDA not available
- ❌ Model loading failed
- ❌ Configuration error

### Performance Indicators
- 🚀 GPU ACCELERATION: ENABLED (Production)
- 💻 CPU PROCESSING: ENABLED (Development)
- ⚡ Performance: HIGH (GPU) / OPTIMIZED (CPU)

---

**Log Monitoring Guide Updated**: September 14, 2025  
**Status**: ✅ Comprehensive monitoring tools ready
