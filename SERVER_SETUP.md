# 🚀 SHCI Server Setup Guide - Step by Step

## 📋 Prerequisites

### Server Requirements
- **OS**: Ubuntu 22.04 LTS
- **RAM**: 16GB+ (recommended)
- **Storage**: 50GB+ SSD
- **GPU**: 2x NVIDIA GPUs (RTX 3080/4080 or better)
- **Domain**: nodecel.cloud pointing to server IP

### Already Setup
- ✅ Ollama running on port 11434
- ✅ qwen2.5-14b-gpu model loaded

## 🛠️ Step-by-Step Setup

### Step 1: Connect to Server
```bash
# SSH to your server
ssh username@your-server-ip

# Or if using domain
ssh username@nodecel.cloud
```

### Step 2: Update System
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git vim nano htop
```

### Step 3: Clone Repository
```bash
# Clone SHCI repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Check if files are there
ls -la
```

### Step 4: Make Script Executable
```bash
# Make deployment script executable
chmod +x deploy.sh

# Check script permissions
ls -la deploy.sh
```

### Step 5: Run Deployment Script
```bash
# Run automated deployment
./deploy.sh
```

**The script will automatically:**
- ✅ Install Docker & Docker Compose
- ✅ Install NVIDIA drivers & Docker GPU support
- ✅ Configure firewall
- ✅ Check Ollama service
- ✅ Build and start containers
- ✅ Setup SSL certificates
- ✅ Configure auto-start service

### Step 6: Monitor Deployment
```bash
# Watch deployment progress
tail -f /var/log/syslog

# Check Docker containers
docker ps

# Check GPU status
nvidia-smi
```

### Step 7: Verify Services
```bash
# Check if all services are running
docker-compose ps

# Check logs
docker-compose logs -f

# Test health endpoints
curl https://nodecel.cloud/health
curl https://nodecel.cloud/api/health
```

## 🔧 Manual Setup (Alternative)

If automated script fails, manual setup:

### Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Install NVIDIA Support
```bash
# Install NVIDIA drivers
sudo apt install -y nvidia-driver-535 nvidia-dkms-535

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Configure Firewall
```bash
# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### Deploy Application
```bash
# Build and start services
docker-compose up -d --build

# Check status
docker-compose ps
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
# Fix permissions
sudo chown -R $USER:$USER /opt/shci-app
chmod +x deploy.sh
```

#### 2. Docker Not Found
```bash
# Reinstall Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and log back in
```

#### 3. GPU Not Detected
```bash
# Check GPU
nvidia-smi
lspci | grep -i nvidia

# Install drivers
sudo apt install -y nvidia-driver-535
sudo reboot
```

#### 4. Ollama Not Running
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check models
ollama list
```

#### 5. Port Conflicts
```bash
# Check port usage
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :11434

# Kill conflicting processes
sudo kill -9 <PID>
```

### Debug Commands
```bash
# Check system resources
htop
df -h
free -h

# Check Docker
docker version
docker-compose version

# Check GPU
nvidia-smi
nvidia-settings

# Check services
systemctl status docker
systemctl status ollama
```

## 📊 Post-Deployment Verification

### 1. Check All Services
```bash
# Docker containers
docker-compose ps

# Expected output:
# shci-backend    Up (healthy)
# shci-frontend   Up
# shci-nginx      Up
```

### 2. Test Endpoints
```bash
# Health check
curl https://nodecel.cloud/health

# API health
curl https://nodecel.cloud/api/health

# Frontend
curl https://nodecel.cloud/
```

### 3. Check GPU Usage
```bash
# Monitor GPU
watch -n 1 nvidia-smi

# Check container GPU access
docker-compose exec backend nvidia-smi
```

### 4. Test LLM Integration
```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test from container
docker-compose exec backend curl http://host.docker.internal:11434/api/tags
```

## 🎯 Success Indicators

### ✅ Everything Working
- **Frontend**: https://nodecel.cloud loads
- **API**: https://nodecel.cloud/api/health returns 200
- **WebSocket**: wss://nodecel.cloud/ws connects
- **GPU**: nvidia-smi shows usage
- **Ollama**: curl localhost:11434/api/tags works
- **SSL**: Green lock icon in browser

### 📱 Access URLs
- **Main App**: https://nodecel.cloud
- **API Docs**: https://nodecel.cloud/docs
- **Health**: https://nodecel.cloud/health
- **WebSocket**: wss://nodecel.cloud/ws

## 🔄 Management Commands

### Daily Operations
```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Update application
git pull && docker-compose up -d --build

# Stop services
docker-compose down

# Start services
docker-compose up -d
```

### Monitoring
```bash
# Resource usage
docker stats

# GPU usage
watch -n 1 nvidia-smi

# Disk usage
df -h

# Memory usage
free -h
```

## 🚨 Emergency Procedures

### Service Down
```bash
# Restart all services
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs -f
```

### GPU Issues
```bash
# Restart NVIDIA drivers
sudo systemctl restart nvidia-persistenced

# Check GPU status
nvidia-smi
```

### Ollama Issues
```bash
# Restart Ollama
sudo systemctl restart ollama

# Check Ollama status
systemctl status ollama
```

## 🎉 Final Checklist

- [ ] Server connected via SSH
- [ ] Repository cloned
- [ ] Deployment script executed
- [ ] All containers running
- [ ] GPU detected and working
- [ ] Ollama service running
- [ ] SSL certificates installed
- [ ] Frontend accessible
- [ ] API endpoints working
- [ ] WebSocket connecting
- [ ] Health checks passing

**Once all items are checked, your SHCI Voice Assistant is ready!** 🚀
