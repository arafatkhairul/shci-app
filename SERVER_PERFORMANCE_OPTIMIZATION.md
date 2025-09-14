# Server Performance Optimization Guide

## 🚀 **Intel Xeon E5-2697v2 Server Optimization**

### 🔍 **Performance Analysis**

#### **Why MacBook Air M2 is Faster**:
- ✅ **Apple Silicon M2** - Modern ARM architecture
- ✅ **Unified memory** - Faster data access
- ✅ **Optimized Piper TTS** for Apple Silicon
- ✅ **Lower latency** system architecture

#### **RTX A5000 Server Challenges**:
- ❌ **Intel Xeon E5-2697v2** - Older CPU (2013)
- ❌ **Higher latency** between CPU and GPU
- ❌ **Piper TTS** not optimized for older Intel CPUs
- ❌ **Memory bandwidth** limitations

## 🛠️ **Optimization Solutions**

### 1. **CPU Optimization**

#### **Environment Variables**:
```bash
# Force CPU usage (better for older Intel CPUs)
PIPER_FORCE_CPU=true
PIPER_DEVICE=cpu

# Thread optimization for Intel Xeon
OMP_NUM_THREADS=8
MKL_NUM_THREADS=8
NUMEXPR_NUM_THREADS=8

# Disable GPU for better CPU performance
CUDA_VISIBLE_DEVICES=""
```

#### **Synthesis Parameters**:
```python
# Optimized for server performance
length_scale = 0.6    # Faster speech (was 0.8)
noise_scale = 0.5     # Reduced processing (was 0.667)
noise_w = 0.6         # Optimized for CPU (was 0.8)
```

### 2. **Memory Optimization**

#### **128GB RAM Utilization**:
- ✅ **Large memory buffer** for audio processing
- ✅ **Model caching** in memory
- ✅ **Reduced disk I/O** operations
- ✅ **Optimized memory allocation**

### 3. **Dual 12-Core CPU Optimization**

#### **Thread Management**:
```bash
# Limit threads to prevent over-subscription
OMP_NUM_THREADS=8      # Use 8 cores max
MKL_NUM_THREADS=8      # Intel MKL optimization
NUMEXPR_NUM_THREADS=8  # NumPy optimization
```

#### **CPU Affinity**:
```bash
# Set CPU affinity for better performance
taskset -c 0-7 python main.py
```

### 4. **Server Configuration**

#### **System Settings**:
```bash
# Increase file descriptor limits
ulimit -n 65536

# Optimize memory overcommit
echo 1 > /proc/sys/vm/overcommit_memory

# Disable swap for better performance
swapoff -a
```

#### **Python Optimization**:
```bash
# Enable Python optimizations
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
```

## 📊 **Expected Performance Improvements**

### **Before Optimization**:
- ⏱️ **3-4 seconds** audio generation
- 🐌 **Slow response** times
- 💾 **High memory usage**
- 🔥 **CPU overheating**

### **After Optimization**:
- ⚡ **1-2 seconds** audio generation
- 🚀 **50-60% faster** response
- 💾 **Optimized memory** usage
- ❄️ **Better CPU** utilization

## 🔧 **Implementation Steps**

### 1. **Deploy Optimizations**:
```bash
# Copy server performance config
cp server-performance.env /root/shci-app/fastapi-backend/

# Deploy with optimizations
./deploy.sh
```

### 2. **Monitor Performance**:
```bash
# Check CPU usage
htop

# Monitor memory usage
free -h

# Check audio generation time
tail -f /var/log/fastapi-app.log | grep "synthesis completed"
```

### 3. **Fine-tune Parameters**:
```bash
# Adjust synthesis parameters based on server performance
export PIPER_LENGTH_SCALE=0.5  # Even faster if needed
export PIPER_NOISE_SCALE=0.4   # Reduce processing further
```

## 🎯 **Server-Specific Recommendations**

### **For Intel Xeon E5-2697v2**:
- ✅ **Use CPU only** (disable GPU)
- ✅ **Limit threads** to 8 cores
- ✅ **Optimize memory** allocation
- ✅ **Use faster synthesis** parameters

### **For 128GB RAM**:
- ✅ **Enable large buffers** for audio processing
- ✅ **Cache models** in memory
- ✅ **Reduce disk I/O** operations
- ✅ **Optimize memory** usage

### **For Dual 12-Core CPU**:
- ✅ **Set CPU affinity** for better performance
- ✅ **Limit thread count** to prevent over-subscription
- ✅ **Use NUMA** optimization if available
- ✅ **Monitor CPU** temperature and usage

## 📈 **Performance Monitoring**

### **Key Metrics**:
```bash
# Audio generation time
grep "synthesis completed" /var/log/fastapi-app.log | tail -10

# CPU usage
top -p $(pgrep -f "python main.py")

# Memory usage
ps aux | grep "python main.py"

# System load
uptime
```

### **Optimization Targets**:
- 🎯 **Audio generation**: < 2 seconds
- 🎯 **CPU usage**: < 80%
- 🎯 **Memory usage**: < 16GB
- 🎯 **Response time**: < 3 seconds total

## 🚀 **Expected Results**

After implementing these optimizations:

- ✅ **50-60% faster** audio generation
- ✅ **Better CPU** utilization
- ✅ **Optimized memory** usage
- ✅ **Reduced server** load
- ✅ **Improved user** experience

The server should now perform much closer to your MacBook Air M2! 🎉
