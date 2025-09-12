#!/bin/bash

# SHCI Voice Assistant - Ubuntu VPS Deployment Script
# ===================================================

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

echo -e "${BLUE}🚀 Starting SHCI Voice Assistant Deployment${NC}"
echo "================================================"

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
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

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    if [ "$EUID" -eq 0 ]; then
        sh get-docker.sh
        # For root user, no need to add to docker group
    else
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_warning "Docker installed. Please log out and log back in for group changes to take effect."
    fi
fi

# Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    if [ "$EUID" -eq 0 ]; then
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    else
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
fi

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
    
    # Install NVIDIA drivers
    if [ "$EUID" -eq 0 ]; then
        apt update
        apt install -y nvidia-driver-535 nvidia-dkms-535
        
        # Install NVIDIA Container Toolkit
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
        
        apt update
        apt install -y nvidia-container-toolkit
        systemctl restart docker
    else
        sudo apt update
        sudo apt install -y nvidia-driver-535 nvidia-dkms-535
        
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
else
    print_warning "No NVIDIA GPU detected. Will use CPU for processing."
fi

# Configure firewall
print_status "Configuring firewall..."
if [ "$EUID" -eq 0 ]; then
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
else
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
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

# Build and start services
print_status "Building and starting services..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    print_status "Services are running successfully!"
else
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Setup SSL certificate (optional)
read -p "Do you want to setup SSL certificate with Let's Encrypt? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Setting up SSL certificate..."
    
    # Stop nginx container temporarily
    docker-compose stop nginx
    
    # Install certificate
    if [ "$EUID" -eq 0 ]; then
        certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
    else
        sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
    fi
    
    # Update docker-compose to use SSL
    sed -i 's/# Same location blocks as above/    location \/ {\n        proxy_pass http:\/\/frontend;\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection '\''upgrade'\'';\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_cache_bypass $http_upgrade;\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 75s;\n    }\n\n    location \/api\/ {\n        limit_req zone=api burst=20 nodelay;\n        proxy_pass http:\/\/backend;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 75s;\n    }\n\n    location \/ws {\n        limit_req zone=ws burst=10 nodelay;\n        proxy_pass http:\/\/backend;\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection "upgrade";\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 86400s;\n        proxy_send_timeout 86400s;\n    }\n\n    location \/roleplay\/ {\n        proxy_pass http:\/\/backend;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 75s;\n    }\n\n    location \/health {\n        proxy_pass http:\/\/backend;\n        access_log off;\n    }/' nginx/conf.d/shci.conf
    
    # Restart nginx
    docker-compose up -d nginx
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

# Create systemd service for auto-start
print_status "Creating systemd service..."
if [ "$EUID" -eq 0 ]; then
    tee /etc/systemd/system/shci-app.service > /dev/null << EOF
else
    sudo tee /etc/systemd/system/shci-app.service > /dev/null << EOF
fi
[Unit]
Description=SHCI Voice Assistant
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/$PROJECT_NAME
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

if [ "$EUID" -eq 0 ]; then
    systemctl enable shci-app.service
else
    sudo systemctl enable shci-app.service
fi

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
echo "• View logs: docker-compose logs -f"
echo "• Restart: docker-compose restart"
echo "• Stop: docker-compose down"
echo "• Start: docker-compose up -d"
echo "• Update: git pull && docker-compose up -d --build"
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
