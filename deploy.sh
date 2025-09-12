#!/bin/bash

# SHCI Voice Assistant - Complete Deployment Script
# ================================================
# This script removes existing Python versions and installs only Python 3.11.9
# Then deploys the complete SHCI Voice Assistant application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="shci-app"
DOMAIN_NAME="nodecel.cloud"  # Your main domain
EMAIL="office.khairul@gmail.com"  # Your email

echo -e "${BLUE}🚀 Starting SHCI Complete Deployment${NC}"
echo "============================================="
echo -e "${YELLOW}⚠️  WARNING: This script will remove existing Python versions${NC}"
echo -e "${YELLOW}   and install only Python 3.11 (latest available)${NC}"
echo ""

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

# SSH Safety Function
ensure_ssh_safety() {
    print_warning "🔒 Ensuring SSH port 22 is protected..."
    
    if [ "$EUID" -eq 0 ]; then
        # Allow SSH with multiple methods for redundancy
        ufw allow 22/tcp
        ufw allow ssh
        ufw allow out 22/tcp
        
        # Verify SSH is allowed
        if ufw status | grep -q "22/tcp.*ALLOW"; then
            print_status "✅ SSH port 22 is protected"
        else
            print_error "❌ SSH port not protected! Adding again..."
            ufw allow 22/tcp
            ufw allow ssh
        fi
    else
        # Allow SSH with multiple methods for redundancy
        sudo ufw allow 22/tcp
        sudo ufw allow ssh
        sudo ufw allow out 22/tcp
        
        # Verify SSH is allowed
        if sudo ufw status | grep -q "22/tcp.*ALLOW"; then
            print_status "✅ SSH port 22 is protected"
        else
            print_error "❌ SSH port not protected! Adding again..."
            sudo ufw allow 22/tcp
            sudo ufw allow ssh
        fi
    fi
}

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
    apt install -y curl wget git nginx certbot python3-certbot-nginx ufw
else
    sudo apt install -y curl wget git nginx certbot python3-certbot-nginx ufw
fi

# Install Node.js and npm
print_status "Installing Node.js and npm..."
if ! command -v node &> /dev/null; then
    if [ "$EUID" -eq 0 ]; then
        apt install -y nodejs npm
    else
        sudo apt install -y nodejs npm
    fi
fi

# Remove existing Python versions and install only Python 3.11.9
print_status "Removing existing Python versions and installing only Python 3.11..."
if [ "$EUID" -eq 0 ]; then
    # Remove existing Python versions
    print_status "Removing existing Python installations..."
    apt remove -y python3 python3.12 python3.12-dev python3.12-venv python3.12-distutils python3-pip python3-venv 2>/dev/null || true
    apt autoremove -y
    
    # Add deadsnakes PPA
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    
    # Check available Python 3.11 versions
    print_status "Checking available Python 3.11 versions..."
    apt-cache policy python3.11 | grep -E "Installed|Candidate|Version table"
    
    # Install latest available Python 3.11 (not specific version)
    print_status "Installing latest available Python 3.11..."
    apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    
    # Verify Python 3.11 installation
    PYTHON_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
    print_success "Python 3.11 installed successfully: $PYTHON_VERSION"
    
    # Create symlinks
    if command -v python3.11 &> /dev/null; then
        ln -sf /usr/bin/python3.11 /usr/bin/python
        ln -sf /usr/bin/python3.11 /usr/bin/python3
        print_success "Python symlinks created: python -> python3.11"
        
        # Verify symlinks
        echo "Python version verification:"
        echo "python --version: $(python --version)"
        echo "python3 --version: $(python3 --version)"
        echo "python3.11 --version: $(python3.11 --version)"
    else
        print_error "Python 3.11 installation failed"
        exit 1
    fi
else
    # Remove existing Python versions
    print_status "Removing existing Python installations..."
    sudo apt remove -y python3 python3.12 python3.12-dev python3.12-venv python3.12-distutils python3-pip python3-venv 2>/dev/null || true
    sudo apt autoremove -y
    
    # Add deadsnakes PPA
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    
    # Check available Python 3.11 versions
    print_status "Checking available Python 3.11 versions..."
    apt-cache policy python3.11 | grep -E "Installed|Candidate|Version table"
    
    # Install latest available Python 3.11 (not specific version)
    print_status "Installing latest available Python 3.11..."
    sudo apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    
    # Verify Python 3.11 installation
    PYTHON_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
    print_success "Python 3.11 installed successfully: $PYTHON_VERSION"
    
    # Create symlinks
    if command -v python3.11 &> /dev/null; then
        sudo ln -sf /usr/bin/python3.11 /usr/bin/python
        sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
        print_success "Python symlinks created: python -> python3.11"
        
        # Verify symlinks
        echo "Python version verification:"
        echo "python --version: $(python --version)"
        echo "python3 --version: $(python3 --version)"
        echo "python3.11 --version: $(python3.11 --version)"
    else
        print_error "Python 3.11 installation failed"
        exit 1
    fi
fi

# Install pip for Python 3.11
print_status "Installing pip for Python 3.11..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Check for Ollama service
print_status "Checking for Ollama LLM service..."
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_status "Ollama service detected and running!"
    print_status "LLM will use external Ollama service"
else
    print_warning "Ollama service not detected on localhost:11434"
    print_warning "Please ensure Ollama is running for LLM functionality"
fi

# Check for GPU and install NVIDIA Docker support
print_status "Checking for GPU support..."
if lspci | grep -i nvidia &> /dev/null; then
    print_status "NVIDIA GPU detected! Installing NVIDIA Docker support..."
    
    # Install NVIDIA drivers for Ubuntu 24.04 with CUDA 12.6
    if [ "$EUID" -eq 0 ]; then
        apt update
        
        # Try to install available NVIDIA drivers
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
        
        # Install NVIDIA Container Toolkit
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
        
        apt update
        apt install -y nvidia-container-toolkit
        systemctl restart docker
    else
        sudo apt update
        
        # Try to install available NVIDIA drivers
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
        
        # Install NVIDIA Container Toolkit
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt update
        sudo apt install -y nvidia-container-toolkit
        sudo systemctl restart docker
    fi
    
    print_status "NVIDIA Docker support installed successfully!"
    print_warning "GPU will be used for TTS/STT processing in production"
    
    # Set GPU Dockerfile
    export BACKEND_DOCKERFILE="Dockerfile"
    print_status "Using GPU-enabled Dockerfile"
else
    print_warning "No NVIDIA GPU detected. Will use CPU for processing."
    
    # Set CPU Dockerfile
    export BACKEND_DOCKERFILE="Dockerfile.cpu"
    print_status "Using CPU-only Dockerfile"
fi

# Configure firewall
print_status "Configuring firewall..."

# Ensure SSH safety first
ensure_ssh_safety

if [ "$EUID" -eq 0 ]; then
    # Allow web ports
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Enable firewall
    ufw --force enable
    
    # Final SSH verification
    ensure_ssh_safety
else
    # Allow web ports
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Enable firewall
    sudo ufw --force enable
    
    # Final SSH verification
    ensure_ssh_safety
fi

# Show firewall status
print_status "Firewall status:"
if [ "$EUID" -eq 0 ]; then
    ufw status numbered
else
    sudo ufw status numbered
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
    
    # Check if repository is private and needs authentication
    if curl -s -o /dev/null -w "%{http_code}" https://github.com/arafatkhairul/shci-app | grep -q "404"; then
        print_warning "Repository appears to be private. Please choose authentication method:"
        echo "1. Personal Access Token"
        echo "2. SSH Key"
        echo "3. GitHub CLI"
        echo ""
        read -p "Enter your choice (1-3): " auth_choice
        
        case $auth_choice in
            1)
                read -p "Enter your GitHub Personal Access Token: " github_token
                git clone https://$github_token@github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
                ;;
            2)
                print_status "Using SSH authentication..."
                git clone git@github.com:arafatkhairul/shci-app.git /opt/$PROJECT_NAME
                ;;
            3)
                print_status "Using GitHub CLI..."
                if ! command -v gh &> /dev/null; then
                    print_status "Installing GitHub CLI..."
                    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
                    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
                    sudo apt update
                    sudo apt install gh
                fi
                gh auth login
                gh repo clone arafatkhairul/shci-app /opt/$PROJECT_NAME
                ;;
            *)
                print_error "Invalid choice. Please run the script again."
                exit 1
                ;;
        esac
    else
        print_status "Repository is public, cloning normally..."
        git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
    fi
    
    cd /opt/$PROJECT_NAME
fi

# Create production environment file
print_status "Creating production environment configuration..."
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
PYTHONPATH=/app

# LLM Configuration (External Ollama)
LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
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
TTS_MODEL_PATH=/app/Models
TTS_OUTPUT_PATH=/app/outputs
TTS_CACHE_PATH=/app/memdb
TTS_BATCH_SIZE=4
TTS_MAX_LENGTH=500

# Database Configuration
DATABASE_URL=sqlite:///./roleplay.db

# Security Configuration
CORS_ORIGINS=["https://$DOMAIN_NAME", "https://www.$DOMAIN_NAME"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Performance Configuration
WORKERS=4
MAX_CONNECTIONS=1000

# SSL Configuration
SSL_VERIFY=true
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
EOF
fi

# Update Nginx configuration with domain
print_status "Updating Nginx configuration..."
sed -i "s/your-domain.com/$DOMAIN_NAME/g" nginx/conf.d/shci.conf

# Create SSL directory
sudo mkdir -p /opt/$PROJECT_NAME/ssl

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
ExecStart=/opt/$PROJECT_NAME/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
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
ExecStart=/opt/$PROJECT_NAME/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
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

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Check if services are running
if systemctl is-active --quiet shci-backend.service && systemctl is-active --quiet shci-frontend.service; then
    print_status "Services are running successfully!"
else
    print_error "Some services failed to start. Check logs with: journalctl -u shci-backend.service -f"
    exit 1
fi

# Setup SSL certificate (optional)
read -p "Do you want to setup SSL certificate with Let's Encrypt? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Setting up SSL certificate..."
    
    # Stop nginx temporarily
    if [ "$EUID" -eq 0 ]; then
        systemctl stop nginx
    else
        sudo systemctl stop nginx
    fi
    
    # Install certificate
    if [ "$EUID" -eq 0 ]; then
        certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
    else
        sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
    fi
    
    # Update docker-compose to use SSL
    sed -i 's/# Same location blocks as above/    location \/ {\n        proxy_pass http:\/\/frontend;\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection '\''upgrade'\'';\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_cache_bypass $http_upgrade;\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 75s;\n    }\n\n    location \/api\/ {\n        limit_req zone=api burst=20 nodelay;\n        proxy_pass http:\/\/backend;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 75s;\n    }\n\n    location \/ws {\n        limit_req zone=ws burst=10 nodelay;\n        proxy_pass http:\/\/backend;\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection "upgrade";\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 86400s;\n        proxy_send_timeout 86400s;\n    }\n\n    location \/roleplay\/ {\n        proxy_pass http:\/\/backend;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 75s;\n    }\n\n    location \/health {\n        proxy_pass http:\/\/backend;\n        access_log off;\n    }/' nginx/conf.d/shci.conf
    
    # Restart nginx
    if [ "$EUID" -eq 0 ]; then
        systemctl start nginx
    else
        sudo systemctl start nginx
    fi
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

# Services are already created and enabled above
print_status "Systemd services already created and enabled"

# Final status check
print_status "Deployment completed successfully!"
echo "================================================"
echo -e "${GREEN}🎉 SHCI Voice Assistant is now deployed!${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo "• Domain: https://$DOMAIN_NAME"
echo "• Frontend: Next.js (Port 3000)"
echo "• Backend: FastAPI (Port 8000)"
echo "• Proxy: Nginx (Port 80/443)"
echo "• SSL: Let's Encrypt (if configured)"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "• View logs: journalctl -u shci-backend.service -f"
echo "• View logs: journalctl -u shci-frontend.service -f"
echo "• Restart backend: systemctl restart shci-backend.service"
echo "• Restart frontend: systemctl restart shci-frontend.service"
echo "• Stop services: systemctl stop shci-backend.service shci-frontend.service"
echo "• Start services: systemctl start shci-backend.service shci-frontend.service"
echo "• Update: git pull && systemctl restart shci-backend.service shci-frontend.service"
echo ""
echo -e "${BLUE}📁 Project Location:${NC}"
echo "/opt/$PROJECT_NAME"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "• Change DOMAIN_NAME and EMAIL in this script before running"
echo "• Make sure your domain points to this server's IP"
echo "• Check firewall settings if services are not accessible"
echo "• Monitor logs regularly for any issues"
echo ""
print_status "Deployment script completed!"
