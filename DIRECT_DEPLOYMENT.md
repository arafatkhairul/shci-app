# SHCI Voice Assistant - Direct Deployment Guide (No Docker)

## Overview

This guide provides instructions for deploying the SHCI Voice Assistant directly on Ubuntu 24.04.3 LTS without Docker. The deployment uses systemd services for process management and Nginx as a reverse proxy.

## Prerequisites

- Ubuntu 24.04.3 LTS server
- Root access or sudo privileges
- Domain name pointing to your server (e.g., `nodecel.cloud`)
- Minimum 4GB RAM, 20GB storage
- NVIDIA GPU (optional, for TTS/STT acceleration)

## Quick Deployment

### Option 1: Automated Script (Recommended)

```bash
# Clone the repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Make scripts executable
chmod +x deploy-direct.sh deploy.sh

# Run the deployment script
./deploy-direct.sh
```

### Option 2: Original Script (Updated for Direct Deployment)

```bash
# Clone the repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Run the updated deployment script
./deploy.sh
```

## Manual Deployment Steps

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl wget git nginx certbot python3-certbot-nginx ufw \
    software-properties-common build-essential gcc g++ make \
    portaudio19-dev libasound2-dev ffmpeg libsndfile1 \
    nodejs npm python3-pip python3-venv
```

### 2. Python 3.11.9 Installation

```bash
# Add deadsnakes PPA for Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11.9
sudo apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils

# Create symlinks
sudo ln -sf /usr/bin/python3.11 /usr/bin/python
sudo ln -sf /usr/bin/python3.11 /usr/bin/python3

# Install pip for Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
```

### 3. NVIDIA GPU Setup (Optional)

```bash
# Check for NVIDIA GPU
lspci | grep -i nvidia

# Install NVIDIA drivers (if GPU detected)
sudo apt update
sudo apt install -y nvidia-driver-550 nvidia-dkms-550
# OR use ubuntu-drivers for automatic selection
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Reboot after driver installation
sudo reboot
```

### 4. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8000/tcp   # Backend API
sudo ufw allow 3000/tcp    # Frontend (if needed)
sudo ufw --force enable
```

### 5. Project Setup

```bash
# Create project directory
sudo mkdir -p /opt/shci-app
sudo chown $USER:$USER /opt/shci-app

# Clone repository
cd /opt
git clone https://github.com/arafatkhairul/shci-app.git shci-app
cd shci-app
```

### 6. Backend Setup

```bash
cd /opt/shci-app/fastapi-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install PyTorch (GPU or CPU)
if lspci | grep -i nvidia &> /dev/null; then
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi
```

### 7. Frontend Setup

```bash
cd /opt/shci-app/web-app

# Install dependencies
npm install

# Build for production
npm run build
```

### 8. Environment Configuration

```bash
cd /opt/shci-app

# Create production environment file
cat > .env.production << EOF
# Production Environment Configuration
NEXT_PUBLIC_API_BASE_URL=https://nodecel.cloud
NEXT_PUBLIC_WS_BASE_URL=wss://nodecel.cloud
NEXT_PUBLIC_WS_PRODUCTION_URL=wss://nodecel.cloud
NEXT_PUBLIC_DEV_MODE=false
NEXT_PUBLIC_APP_NAME=SHCI Voice Assistant
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENABLE_ROLEPLAY=true
NEXT_PUBLIC_ENABLE_TTS=true
NEXT_PUBLIC_ENABLE_STT=true

# Backend Environment Variables
ENVIRONMENT=production
PYTHONPATH=/opt/shci-app/fastapi-backend

# LLM Configuration (External Ollama)
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu
LLM_API_KEY=
LLM_TIMEOUT=10.0
LLM_RETRIES=1

# GPU Configuration for Production
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
WHISPER_DEVICE=cuda

# Model Configuration
TTS_MODEL_PATH=/opt/shci-app/Models
TTS_OUTPUT_PATH=/opt/shci-app/fastapi-backend/outputs
TTS_CACHE_PATH=/opt/shci-app/fastapi-backend/memdb
TTS_BATCH_SIZE=4
TTS_MAX_LENGTH=500

# Database Configuration
DATABASE_URL=sqlite:///./roleplay.db

# Security Configuration
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://nodecel.cloud,https://www.nodecel.cloud

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
EOF
```

### 9. Systemd Services

#### Backend Service

```bash
sudo tee /etc/systemd/system/shci-backend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Backend
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/shci-app/fastapi-backend
Environment=PATH=/opt/shci-app/fastapi-backend/venv/bin
EnvironmentFile=/opt/shci-app/.env.production
ExecStart=/opt/shci-app/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

#### Frontend Service

```bash
sudo tee /etc/systemd/system/shci-frontend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Frontend
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/shci-app/web-app
Environment=NODE_ENV=production
EnvironmentFile=/opt/shci-app/.env.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

#### Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable shci-backend.service
sudo systemctl enable shci-frontend.service
sudo systemctl start shci-backend.service
sudo systemctl start shci-frontend.service
```

### 10. Nginx Configuration

```bash
sudo tee /etc/nginx/sites-available/shci-app > /dev/null << EOF
server {
    listen 80;
    server_name nodecel.cloud www.nodecel.cloud;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Roleplay API
    location /roleplay/ {
        proxy_pass http://localhost:8000/roleplay/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/shci-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 11. SSL Certificate Setup

```bash
# Install SSL certificate
sudo certbot --nginx -d nodecel.cloud -d www.nodecel.cloud --email office.khairul@gmail.com --agree-tos --non-interactive

# Setup auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo tee /etc/cron.d/certbot
```

## Service Management

### Check Service Status

```bash
# Check backend status
sudo systemctl status shci-backend.service

# Check frontend status
sudo systemctl status shci-frontend.service

# Check nginx status
sudo systemctl status nginx
```

### View Logs

```bash
# Backend logs
sudo journalctl -u shci-backend.service -f

# Frontend logs
sudo journalctl -u shci-frontend.service -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Services

```bash
# Restart backend
sudo systemctl restart shci-backend.service

# Restart frontend
sudo systemctl restart shci-frontend.service

# Restart nginx
sudo systemctl restart nginx

# Restart all services
sudo systemctl restart shci-backend.service shci-frontend.service nginx
```

### Stop/Start Services

```bash
# Stop services
sudo systemctl stop shci-backend.service shci-frontend.service

# Start services
sudo systemctl start shci-backend.service shci-frontend.service
```

## Updates and Maintenance

### Update Application

```bash
cd /opt/shci-app
git pull origin main

# Restart services to apply changes
sudo systemctl restart shci-backend.service shci-frontend.service
```

### Update Dependencies

```bash
# Backend dependencies
cd /opt/shci-app/fastapi-backend
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Frontend dependencies
cd /opt/shci-app/web-app
npm update
npm run build

# Restart services
sudo systemctl restart shci-backend.service shci-frontend.service
```

## Troubleshooting

### Common Issues

1. **Service fails to start**
   ```bash
   sudo journalctl -u shci-backend.service -f
   sudo journalctl -u shci-frontend.service -f
   ```

2. **Port conflicts**
   ```bash
   sudo netstat -tlnp | grep :8000
   sudo netstat -tlnp | grep :3000
   ```

3. **Permission issues**
   ```bash
   sudo chown -R $USER:$USER /opt/shci-app
   ```

4. **Nginx configuration errors**
   ```bash
   sudo nginx -t
   ```

5. **SSL certificate issues**
   ```bash
   sudo certbot certificates
   sudo certbot renew --dry-run
   ```

### Performance Monitoring

```bash
# Check system resources
htop
nvidia-smi  # If GPU available

# Check service resource usage
sudo systemctl status shci-backend.service
sudo systemctl status shci-frontend.service
```

## Security Considerations

1. **Firewall**: UFW is configured to allow only necessary ports
2. **SSL**: Let's Encrypt certificates with auto-renewal
3. **User permissions**: Services run as non-root user (if not using root)
4. **Security headers**: Nginx configured with security headers
5. **Regular updates**: Keep system and dependencies updated

## Backup and Recovery

### Backup

```bash
# Backup application
sudo tar -czf shci-backup-$(date +%Y%m%d).tar.gz /opt/shci-app

# Backup configuration
sudo tar -czf shci-config-$(date +%Y%m%d).tar.gz /etc/systemd/system/shci-*.service /etc/nginx/sites-available/shci-app
```

### Recovery

```bash
# Restore application
sudo tar -xzf shci-backup-YYYYMMDD.tar.gz -C /

# Restore configuration
sudo tar -xzf shci-config-YYYYMMDD.tar.gz -C /
sudo systemctl daemon-reload
sudo systemctl restart shci-backend.service shci-frontend.service nginx
```

## Access URLs

After successful deployment:

- **Frontend**: https://nodecel.cloud
- **Backend API**: https://nodecel.cloud/api/
- **WebSocket**: wss://nodecel.cloud/ws
- **Health Check**: https://nodecel.cloud/health
- **Roleplay API**: https://nodecel.cloud/roleplay/

## Support

For issues and support:
- Check service logs: `journalctl -u shci-backend.service -f`
- Verify configuration: `sudo nginx -t`
- Test connectivity: `curl https://nodecel.cloud/health`

---

**Note**: This deployment method runs all services directly on the host system without Docker containers, providing better performance and easier debugging.
