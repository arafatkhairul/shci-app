# 🤖 SHCI + Ollama Integration Guide

## 📋 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Ollama LLM    │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (External)    │
│   Docker        │    │   Docker        │    │   Host System   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ✅ **No Issues! Perfect Integration**

Your setup is **perfectly compatible**:
- ✅ **Backend & Frontend**: Docker containers
- ✅ **Ollama LLM**: External service (no Docker needed)
- ✅ **Communication**: Docker containers → External Ollama

## 🔧 **Configuration**

### **Production Server**
```bash
# Ollama (External Service)
LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu

# Backend (Docker Container)
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
```

### **Local Development**
```bash
# Ollama (External Service)
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu

# Backend (Docker Container)
TORCH_DEVICE=cpu
TTS_DEVICE=cpu
```

## 🚀 **Deployment Process**

### **1. Server Setup**
```bash
# Your Ubuntu server already has:
# ✅ Ollama running on port 11434
# ✅ qwen2.5-14b-gpu model loaded

# Deploy SHCI with Docker
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
./deploy.sh
```

### **2. What Happens**
1. **Docker containers** start (Backend + Frontend)
2. **Backend container** connects to **external Ollama**
3. **GPU processing** for TTS/STT
4. **LLM processing** via Ollama service

## 🔄 **Communication Flow**

```
User Speech → Frontend → Backend → Ollama LLM
                ↓           ↓         ↓
            WebSocket   FastAPI   HTTP API
                ↓           ↓         ↓
            Real-time   Process   Generate
            Audio       Audio     Response
```

## 📊 **Resource Usage**

| Service | Location | GPU Usage | Memory |
|---------|----------|-----------|---------|
| **Ollama LLM** | Host System | ✅ GPU | ~8GB |
| **TTS/STT** | Docker Container | ✅ GPU | ~4GB |
| **Frontend** | Docker Container | ❌ CPU | ~1GB |
| **Backend** | Docker Container | ✅ GPU | ~2GB |

## 🛠️ **Ollama Management**

### **Check Ollama Status**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check loaded models
ollama list

# Check GPU usage
nvidia-smi
```

### **Ollama Commands**
```bash
# Start Ollama service
ollama serve

# Load model
ollama pull qwen2.5-14b-gpu

# Check model status
ollama show qwen2.5-14b-gpu
```

## 🔧 **Troubleshooting**

### **Connection Issues**
```bash
# Test Ollama connection from container
docker-compose exec backend curl http://host.docker.internal:11434/api/tags

# Test from host
curl http://localhost:11434/api/tags
```

### **Performance Issues**
```bash
# Monitor Ollama GPU usage
watch -n 1 nvidia-smi

# Monitor Docker containers
docker stats

# Check Ollama logs
journalctl -u ollama -f
```

### **Model Loading**
```bash
# Ensure model is loaded
ollama pull qwen2.5-14b-gpu

# Check model size
du -sh ~/.ollama/models/
```

## 🎯 **Benefits of This Setup**

### **✅ Advantages**
- **Separation of Concerns**: LLM separate from TTS/STT
- **Resource Optimization**: Ollama uses GPU for LLM, Docker for TTS/STT
- **Easy Updates**: Update SHCI without affecting Ollama
- **Model Management**: Easy Ollama model switching
- **Scalability**: Can run multiple SHCI instances with one Ollama

### **🔧 Flexibility**
- **Model Switching**: Change LLM model without rebuilding containers
- **Version Control**: Update SHCI code independently
- **Resource Allocation**: Fine-tune GPU usage per service

## 📝 **Environment Variables**

### **Production**
```bash
# Ollama Configuration
LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu
LLM_TIMEOUT=10.0
LLM_RETRIES=1

# GPU Configuration
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
```

### **Local Development**
```bash
# Ollama Configuration
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu

# CPU Configuration
TORCH_DEVICE=cpu
TTS_DEVICE=cpu
```

## 🚨 **Important Notes**

1. **Ollama Must Be Running**: Ensure Ollama service is active
2. **Model Must Be Loaded**: qwen2.5-14b-gpu should be available
3. **Port Access**: Port 11434 must be accessible
4. **GPU Memory**: Ensure sufficient VRAM for both services
5. **Network**: Docker containers can access host services

## 🎉 **Summary**

**Your setup is perfect!** 
- ✅ **Ollama**: External service (no Docker needed)
- ✅ **SHCI**: Docker containers (Backend + Frontend)
- ✅ **Communication**: Seamless integration
- ✅ **Performance**: GPU acceleration for both
- ✅ **Flexibility**: Easy model and service management

**No issues, ready to deploy!** 🚀
