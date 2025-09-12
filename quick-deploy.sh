#!/bin/bash

# SHCI Voice Assistant - Quick Direct Deployment Script
# =====================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo -e "${BLUE}🚀 SHCI Quick Direct Deployment${NC}"
echo "=================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root user."
    USER_HOME="/root"
else
    USER_HOME="$HOME"
fi

# Fix apt_pkg issue first
print_status "Fixing apt_pkg module issue..."
if [ "$EUID" -eq 0 ]; then
    apt update
    apt install -y python3-apt software-properties-common
else
    sudo apt update
    sudo apt install -y python3-apt software-properties-common
fi

# Update system
print_status "Updating system..."
if [ "$EUID" -eq 0 ]; then
    apt update && apt upgrade -y
else
    sudo apt update && sudo apt upgrade -y
fi

# Install required packages
print_status "Installing packages..."
if [ "$EUID" -eq 0 ]; then
    apt install -y curl wget git nginx certbot python3-certbot-nginx ufw \
        software-properties-common build-essential gcc g++ make \
        portaudio19-dev libasound2-dev ffmpeg libsndfile1 \
        nodejs npm python3-pip python3-venv
else
    sudo apt install -y curl wget git nginx certbot python3-certbot-nginx ufw \
        software-properties-common build-essential gcc g++ make \
        portaudio19-dev libasound2-dev ffmpeg libsndfile1 \
        nodejs npm python3-pip python3-venv
fi

# Install Python 3.11.9
print_status "Installing Python 3.11.9..."
if [ "$EUID" -eq 0 ]; then
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    ln -sf /usr/bin/python3.11 /usr/bin/python
    ln -sf /usr/bin/python3.11 /usr/bin/python3
else
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    sudo ln -sf /usr/bin/python3.11 /usr/bin/python
    sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
fi

# Install pip
print_status "Installing pip..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Configure firewall
print_status "Configuring firewall..."
if [ "$EUID" -eq 0 ]; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8000/tcp
    ufw allow 3000/tcp
    ufw --force enable
else
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 8000/tcp
    sudo ufw allow 3000/tcp
    sudo ufw --force enable
fi

# Setup project
print_status "Setting up project..."
if [ "$EUID" -eq 0 ]; then
    mkdir -p /opt/shci-app
    chown root:root /opt/shci-app
else
    sudo mkdir -p /opt/shci-app
    sudo chown $USER:$USER /opt/shci-app
fi

# Clone repository
if [ -d "/opt/shci-app/.git" ]; then
    print_status "Updating repository..."
    cd /opt/shci-app
    git pull origin main
else
    print_status "Cloning repository..."
    cd /opt
    git clone https://github.com/arafatkhairul/shci-app.git shci-app
    cd shci-app
fi

# Setup backend
print_status "Setting up backend..."
cd /opt/shci-app/fastapi-backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install PyTorch
if lspci | grep -i nvidia &> /dev/null; then
    print_status "Installing PyTorch with CUDA..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    print_status "Installing PyTorch CPU version..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Setup frontend
print_status "Setting up frontend..."
cd /opt/shci-app/web-app
npm install
npm run build

# Create environment file
print_status "Creating environment configuration..."
cd /opt/shci-app
cat > .env.production << EOF
NEXT_PUBLIC_API_BASE_URL=https://nodecel.cloud
NEXT_PUBLIC_WS_BASE_URL=wss://nodecel.cloud
NEXT_PUBLIC_WS_PRODUCTION_URL=wss://nodecel.cloud
NEXT_PUBLIC_DEV_MODE=false
ENVIRONMENT=production
PYTHONPATH=/opt/shci-app/fastapi-backend
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
WHISPER_DEVICE=cuda
HOST=0.0.0.0
PORT=8000
WORKERS=4
EOF

# Create systemd services
print_status "Creating systemd services..."

# Backend service
if [ "$EUID" -eq 0 ]; then
    tee /etc/systemd/system/shci-backend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Backend
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/shci-app/fastapi-backend
Environment=PATH=/opt/shci-app/fastapi-backend/venv/bin
EnvironmentFile=/opt/shci-app/.env.production
ExecStart=/opt/shci-app/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
else
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
fi

# Frontend service
if [ "$EUID" -eq 0 ]; then
    tee /etc/systemd/system/shci-frontend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Frontend
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/shci-app/web-app
Environment=NODE_ENV=production
EnvironmentFile=/opt/shci-app/.env.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
else
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
fi

# Enable and start services
print_status "Starting services..."
if [ "$EUID" -eq 0 ]; then
    systemctl daemon-reload
    systemctl enable shci-backend.service
    systemctl enable shci-frontend.service
    systemctl start shci-backend.service
    systemctl start shci-frontend.service
else
    sudo systemctl daemon-reload
    sudo systemctl enable shci-backend.service
    sudo systemctl enable shci-frontend.service
    sudo systemctl start shci-backend.service
    sudo systemctl start shci-frontend.service
fi

# Configure Nginx
print_status "Configuring Nginx..."
if [ "$EUID" -eq 0 ]; then
    tee /etc/nginx/sites-available/shci-app > /dev/null << EOF
server {
    listen 80;
    server_name nodecel.cloud www.nodecel.cloud;

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
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /roleplay/ {
        proxy_pass http://localhost:8000/roleplay/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/shci-app /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl reload nginx
else
    sudo tee /etc/nginx/sites-available/shci-app > /dev/null << EOF
server {
    listen 80;
    server_name nodecel.cloud www.nodecel.cloud;

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
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /roleplay/ {
        proxy_pass http://localhost:8000/roleplay/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    sudo ln -sf /etc/nginx/sites-available/shci-app /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl reload nginx
fi

# Setup SSL
print_status "Setting up SSL certificate..."
if [ "$EUID" -eq 0 ]; then
    certbot --nginx -d nodecel.cloud -d www.nodecel.cloud --email office.khairul@gmail.com --agree-tos --non-interactive
else
    sudo certbot --nginx -d nodecel.cloud -d www.nodecel.cloud --email office.khairul@gmail.com --agree-tos --non-interactive
fi

# Setup auto-renewal
if [ -f "/etc/cron.d/certbot" ]; then
    print_status "SSL auto-renewal already configured"
else
    print_status "Setting up SSL auto-renewal..."
    if [ "$EUID" -eq 0 ]; then
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | tee /etc/cron.d/certbot
    else
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo tee /etc/cron.d/certbot
    fi
fi

# Final status
print_status "Deployment completed!"
echo "================================================"
echo -e "${GREEN}🎉 SHCI Voice Assistant is deployed!${NC}"
echo ""
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "Frontend: https://nodecel.cloud"
echo "Backend API: https://nodecel.cloud/api/"
echo "WebSocket: wss://nodecel.cloud/ws"
echo "Health Check: https://nodecel.cloud/health"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "• View logs: journalctl -u shci-backend.service -f"
echo "• Restart: systemctl restart shci-backend.service"
echo "• Status: systemctl status shci-backend.service"
echo ""
echo -e "${GREEN}✅ Quick deployment completed successfully!${NC}"
