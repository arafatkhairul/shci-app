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
EMAIL="your-email@example.com"  # Change this to your email

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
    print_error "Please don't run this script as root. Use a regular user with sudo privileges."
    exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "Installing required packages..."
sudo apt install -y curl wget git nginx certbot python3-certbot-nginx ufw

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_warning "Docker installed. Please log out and log back in for group changes to take effect."
fi

# Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Configure firewall
print_status "Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Create project directory
print_status "Setting up project directory..."
sudo mkdir -p /opt/$PROJECT_NAME
sudo chown $USER:$USER /opt/$PROJECT_NAME

# Clone or update repository
if [ -d "/opt/$PROJECT_NAME/.git" ]; then
    print_status "Updating existing repository..."
    cd /opt/$PROJECT_NAME
    git pull origin main
else
    print_status "Cloning repository..."
    git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
    cd /opt/$PROJECT_NAME
fi

# Create production environment file
print_status "Creating production environment configuration..."
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
EOF

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
    sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive
    
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
    echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo tee /etc/cron.d/certbot
fi

# Create systemd service for auto-start
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/shci-app.service > /dev/null << EOF
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

sudo systemctl enable shci-app.service

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
