# 🛠️ SHCI Voice Assistant - Development Guide

## 🖥️ Local Development (CPU-based)

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Quick Start

```bash
# Clone repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Start local development (CPU-only)
docker-compose -f docker-compose.local.yml up -d

# Or run individually:
# Backend only
cd fastapi-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend only
cd web-app
npm install
npm run dev
```

### Local Development URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🚀 Production Deployment (GPU-based)

### Server Requirements
- **GPU**: 2x NVIDIA GPUs (RTX 3080/4080 or better)
- **RAM**: 16GB+ recommended
- **Storage**: 50GB+ SSD
- **OS**: Ubuntu 22.04 LTS

### Automated Deployment

```bash
# On your GPU server
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Run deployment script (auto-detects GPU)
./deploy.sh
```

### Manual GPU Setup

```bash
# Install NVIDIA drivers
sudo apt update
sudo apt install -y nvidia-driver-535 nvidia-dkms-535

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Deploy with GPU support
docker-compose up -d --build
```

## 🔧 Configuration

### Environment Variables

**Local Development (`env.local`):**
```bash
TORCH_DEVICE=cpu
TTS_DEVICE=cpu
WHISPER_DEVICE=cpu
CUDA_VISIBLE_DEVICES=""
```

**Production (`env.production`):**
```bash
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
WHISPER_DEVICE=cuda
CUDA_VISIBLE_DEVICES=0,1
```

### Docker Compose Files

- **`docker-compose.yml`** - Production with GPU support
- **`docker-compose.local.yml`** - Local development CPU-only

### Dockerfiles

- **`Dockerfile`** - Production with CUDA support
- **`Dockerfile.local`** - Local development CPU-only

## 📊 Performance Comparison

| Environment | TTS Speed | STT Speed | Model Loading | Memory Usage |
|-------------|-----------|-----------|---------------|--------------|
| **Local (CPU)** | ~5-10s | ~2-5s | ~30s | ~2GB |
| **Production (GPU)** | ~1-2s | ~0.5-1s | ~10s | ~8GB |

## 🐛 Troubleshooting

### GPU Issues

```bash
# Check GPU status
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Check container GPU access
docker-compose exec backend nvidia-smi
```

### Performance Issues

```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Monitor container resources
docker stats

# Check logs
docker-compose logs -f backend
```

### Development Issues

```bash
# Reset local environment
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up -d --build

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

## 🔄 Switching Between Environments

### From Local to Production

```bash
# Stop local development
docker-compose -f docker-compose.local.yml down

# Start production
docker-compose up -d
```

### From Production to Local

```bash
# Stop production
docker-compose down

# Start local development
docker-compose -f docker-compose.local.yml up -d
```

## 📝 Development Workflow

1. **Local Development**: Use CPU-based setup for fast iteration
2. **Testing**: Test on local environment first
3. **Production**: Deploy to GPU server for performance
4. **Monitoring**: Use `nvidia-smi` and `docker stats` to monitor

## 🎯 Best Practices

- **Local**: Use CPU for development and testing
- **Production**: Use GPU for optimal performance
- **Models**: Keep models in `./Models` directory
- **Logs**: Monitor logs regularly for issues
- **Updates**: Use `git pull && docker-compose up -d --build` for updates

## 🚨 Important Notes

- **GPU Memory**: Ensure sufficient VRAM (8GB+ recommended)
- **CUDA Version**: Compatible with CUDA 11.8+
- **Driver Version**: NVIDIA driver 535+ required
- **Docker**: Requires Docker with GPU support
- **Models**: First run will download models (~2GB)

## 📞 Support

For development issues:
1. Check logs: `docker-compose logs -f`
2. Verify GPU: `nvidia-smi`
3. Test Docker GPU: `docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi`
4. Monitor resources: `docker stats`
