#!/bin/bash

# SHCI Voice Assistant - Direct Deployment Script (No Docker)
# ==========================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="shci-app"
DOMAIN_NAME="nodecel.cloud"
EMAIL="office.khairul@gmail.com"
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Function to print status
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo -e "${BLUE}🚀 Starting SHCI Direct Deployment (No Docker)${NC}"
echo "=================================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root user. This is supported but not recommended for security."
    print_warning "Consider using a regular user with sudo privileges for better security."
    read -p "Continue as root? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled. Please run as a regular user with sudo privileges."
        exit 1
    fi
    USER_HOME="/root"
else
    USER_HOME="$HOME"
fi

# Fix apt_pkg issue first
print_status "Checking and fixing apt_pkg module issue..."
if [ "$EUID" -eq 0 ]; then
    # Install python3-apt to fix apt_pkg module
    apt update
    apt install -y python3-apt software-properties-common
else
    sudo apt update
    sudo apt install -y python3-apt software-properties-common
fi

# Update system packages
print_status "Updating system packages..."
if [ "$EUID" -eq 0 ]; then
    apt update && apt upgrade -y
else
    sudo apt update && sudo apt upgrade -y
fi

# Install required packages
print_status "Installing required packages..."
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

# Install Python 3.11.9 specifically
print_status "Installing Python 3.11.9 specifically..."
if [ "$EUID" -eq 0 ]; then
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    
    # Install only Python 3.11.9 specific packages
    apt install -y python3.11=3.11.9-1+build1 python3.11-dev=3.11.9-1+build1 python3.11-venv=3.11.9-1+build1 python3.11-distutils=3.11.9-1+build1
    
    # Verify Python 3.11.9 installation
    PYTHON_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
    if [[ "$PYTHON_VERSION" == "3.11.9" ]]; then
        print_success "Python 3.11.9 installed successfully: $PYTHON_VERSION"
    else
        print_warning "Python 3.11.9 not found, installing latest 3.11..."
        apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    fi
    
    # Create symlinks only if Python 3.11.9 is available
    if command -v python3.11 &> /dev/null; then
        ln -sf /usr/bin/python3.11 /usr/bin/python
        ln -sf /usr/bin/python3.11 /usr/bin/python3
        print_success "Python symlinks created: python -> python3.11"
    else
        print_error "Python 3.11 installation failed"
        exit 1
    fi
else
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    
    # Install only Python 3.11.9 specific packages
    sudo apt install -y python3.11=3.11.9-1+build1 python3.11-dev=3.11.9-1+build1 python3.11-venv=3.11.9-1+build1 python3.11-distutils=3.11.9-1+build1
    
    # Verify Python 3.11.9 installation
    PYTHON_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
    if [[ "$PYTHON_VERSION" == "3.11.9" ]]; then
        print_success "Python 3.11.9 installed successfully: $PYTHON_VERSION"
    else
        print_warning "Python 3.11.9 not found, installing latest 3.11..."
        sudo apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    fi
    
    # Create symlinks only if Python 3.11.9 is available
    if command -v python3.11 &> /dev/null; then
        sudo ln -sf /usr/bin/python3.11 /usr/bin/python
        sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
        print_success "Python symlinks created: python -> python3.11"
    else
        print_error "Python 3.11 installation failed"
        exit 1
    fi
fi

# Install pip for Python 3.11
print_status "Installing pip for Python 3.11..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Check for GPU and install NVIDIA drivers
print_status "Checking for GPU support..."
if lspci | grep -i nvidia &> /dev/null; then
    print_status "NVIDIA GPU detected! Installing NVIDIA drivers..."
    
    if [ "$EUID" -eq 0 ]; then
        apt update
        if apt install -y nvidia-driver-550 nvidia-dkms-550 2>/dev/null; then
            print_success "NVIDIA driver 550 installed successfully"
        elif apt install -y nvidia-driver-545 nvidia-dkms-545 2>/dev/null; then
            print_success "NVIDIA driver 545 installed successfully"
        elif apt install -y nvidia-driver-535 nvidia-dkms-535 2>/dev/null; then
            print_success "NVIDIA driver 535 installed successfully"
        else
            print_warning "Specific NVIDIA drivers not found, using ubuntu-drivers"
            apt install -y ubuntu-drivers-common
            ubuntu-drivers autoinstall
        fi
    else
        sudo apt update
        if sudo apt install -y nvidia-driver-550 nvidia-dkms-550 2>/dev/null; then
            print_success "NVIDIA driver 550 installed successfully"
        elif sudo apt install -y nvidia-driver-545 nvidia-dkms-545 2>/dev/null; then
            print_success "NVIDIA driver 545 installed successfully"
        elif sudo apt install -y nvidia-driver-535 nvidia-dkms-535 2>/dev/null; then
            print_success "NVIDIA driver 535 installed successfully"
        else
            print_warning "Specific NVIDIA drivers not found, using ubuntu-drivers"
            sudo apt install -y ubuntu-drivers-common
            sudo ubuntu-drivers autoinstall
        fi
    fi
    
    print_status "NVIDIA drivers installed successfully!"
    print_warning "GPU will be used for TTS/STT processing in production"
else
    print_warning "No NVIDIA GPU detected. Will use CPU for processing."
fi

# Configure firewall
print_status "Configuring firewall..."
if [ "$EUID" -eq 0 ]; then
    ufw allow 22/tcp
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow $BACKEND_PORT/tcp
    ufw allow $FRONTEND_PORT/tcp
    ufw --force enable
else
    sudo ufw allow 22/tcp
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow $BACKEND_PORT/tcp
    sudo ufw allow $FRONTEND_PORT/tcp
    sudo ufw --force enable
fi

# Create project directory
print_status "Setting up project directory..."
if [ "$EUID" -eq 0 ]; then
    mkdir -p /opt/$PROJECT_NAME
    chown root:root /opt/$PROJECT_NAME
else
    sudo mkdir -p /opt/$PROJECT_NAME
    sudo chown $USER:$USER /opt/$PROJECT_NAME
fi

# Clone or update repository
if [ -d "/opt/$PROJECT_NAME/.git" ]; then
    print_status "Updating existing repository..."
    cd /opt/$PROJECT_NAME
    git pull origin main
else
    print_status "Cloning repository..."
    cd /opt
    git clone https://github.com/arafatkhairul/shci-app.git $PROJECT_NAME
    cd $PROJECT_NAME
fi

# Setup backend environment
print_status "Setting up backend environment..."
cd /opt/$PROJECT_NAME/fastapi-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install PyTorch with CUDA support if GPU available
if lspci | grep -i nvidia &> /dev/null; then
    print_status "Installing PyTorch with CUDA support..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    print_status "Installing PyTorch CPU version..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Setup frontend environment
print_status "Setting up frontend environment..."
cd /opt/$PROJECT_NAME/web-app

# Install Node.js dependencies
npm install

# Build frontend for production
npm run build

# Create production environment file
print_status "Creating production environment configuration..."
cd /opt/$PROJECT_NAME
if [ -f "env.production" ]; then
    print_status "Using existing env.production file..."
    cp env.production .env.production
else
    print_status "Creating new .env.production file..."
    cat > .env.production << EOF
# Production Environment Configuration
NEXT_PUBLIC_API_BASE_URL=https://$DOMAIN_NAME
NEXT_PUBLIC_WS_BASE_URL=wss://$DOMAIN_NAME
NEXT_PUBLIC_WS_PRODUCTION_URL=wss://$DOMAIN_NAME
NEXT_PUBLIC_DEV_MODE=false
NEXT_PUBLIC_APP_NAME=SHCI Voice Assistant
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENABLE_ROLEPLAY=true
NEXT_PUBLIC_ENABLE_TTS=true
NEXT_PUBLIC_ENABLE_STT=true

# Backend Environment Variables
ENVIRONMENT=production
PYTHONPATH=/opt/$PROJECT_NAME/fastapi-backend

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
TTS_MODEL_PATH=/opt/$PROJECT_NAME/Models
TTS_OUTPUT_PATH=/opt/$PROJECT_NAME/fastapi-backend/outputs
TTS_CACHE_PATH=/opt/$PROJECT_NAME/fastapi-backend/memdb
TTS_BATCH_SIZE=4
TTS_MAX_LENGTH=500

# Database Configuration
DATABASE_URL=sqlite:///./roleplay.db

# Security Configuration
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://$DOMAIN_NAME,https://www.$DOMAIN_NAME

# Server Configuration
HOST=0.0.0.0
PORT=$BACKEND_PORT
WORKERS=4
EOF
fi

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
WorkingDirectory=/opt/$PROJECT_NAME/fastapi-backend
Environment=PATH=/opt/$PROJECT_NAME/fastapi-backend/venv/bin
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/opt/$PROJECT_NAME/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --workers 4
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
WorkingDirectory=/opt/$PROJECT_NAME/fastapi-backend
Environment=PATH=/opt/$PROJECT_NAME/fastapi-backend/venv/bin
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/opt/$PROJECT_NAME/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --workers 4
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
WorkingDirectory=/opt/$PROJECT_NAME/web-app
Environment=NODE_ENV=production
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
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
WorkingDirectory=/opt/$PROJECT_NAME/web-app
Environment=NODE_ENV=production
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

# Enable and start services
print_status "Enabling and starting services..."
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
    tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Frontend
    location / {
        proxy_pass http://localhost:$FRONTEND_PORT;
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
        proxy_pass http://localhost:$BACKEND_PORT/;
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
        proxy_pass http://localhost:$BACKEND_PORT/ws;
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
        proxy_pass http://localhost:$BACKEND_PORT/roleplay/;
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
        proxy_pass http://localhost:$BACKEND_PORT/health;
        access_log off;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl reload nginx
else
    sudo tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Frontend
    location / {
        proxy_pass http://localhost:$FRONTEND_PORT;
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
        proxy_pass http://localhost:$BACKEND_PORT/;
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
        proxy_pass http://localhost:$BACKEND_PORT/ws;
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
        proxy_pass http://localhost:$BACKEND_PORT/roleplay/;
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
        proxy_pass http://localhost:$BACKEND_PORT/health;
        access_log off;
    }
}
EOF

    sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl reload nginx
fi

# Setup SSL certificate
print_status "Setting up SSL certificate..."
if [ "$EUID" -eq 0 ]; then
    certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
else
    sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
fi

# Setup auto-renewal for SSL
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

# Final status check
print_status "Deployment completed successfully!"
echo "================================================"
echo -e "${GREEN}🎉 SHCI Voice Assistant is now deployed!${NC}"
echo ""
echo -e "${BLUE}📋 Service Status:${NC}"
if [ "$EUID" -eq 0 ]; then
    systemctl status shci-backend.service --no-pager -l
    systemctl status shci-frontend.service --no-pager -l
else
    sudo systemctl status shci-backend.service --no-pager -l
    sudo systemctl status shci-frontend.service --no-pager -l
fi

echo ""
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "Frontend: https://$DOMAIN_NAME"
echo "Backend API: https://$DOMAIN_NAME/api/"
echo "WebSocket: wss://$DOMAIN_NAME/ws"
echo "Health Check: https://$DOMAIN_NAME/health"

echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "Backend: systemctl start/stop/restart shci-backend.service"
echo "Frontend: systemctl start/stop/restart shci-frontend.service"
echo "Nginx: systemctl start/stop/restart nginx"
echo "Logs: journalctl -u shci-backend.service -f"
echo "Logs: journalctl -u shci-frontend.service -f"

echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "1. Services will auto-start on system boot"
echo "2. SSL certificates will auto-renew"
echo "3. Check logs if services fail to start"
echo "4. Reboot system if NVIDIA drivers were installed"
echo ""
echo -e "${GREEN}✅ Direct deployment completed successfully!${NC}"
