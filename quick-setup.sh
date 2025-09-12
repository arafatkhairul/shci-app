#!/bin/bash

# SHCI Quick Setup Script
# =======================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 SHCI Voice Assistant - Quick Setup${NC}"
echo "======================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Don't run as root. Use a regular user with sudo privileges.${NC}"
    exit 1
fi

# Check if repository exists
if [ ! -d "fastapi-backend" ] || [ ! -d "web-app" ]; then
    echo -e "${RED}❌ Repository not found. Please run this from the SHCI project directory.${NC}"
    echo "Expected: git clone https://github.com/arafatkhairul/shci-app.git"
    exit 1
fi

# Check Ollama service
echo -e "${BLUE}🔍 Checking Ollama service...${NC}"
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo -e "${GREEN}✅ Ollama service detected!${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama service not detected on localhost:11434${NC}"
    echo "Please ensure Ollama is running: ollama serve"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check GPU
echo -e "${BLUE}🔍 Checking GPU...${NC}"
if lspci | grep -i nvidia &> /dev/null; then
    echo -e "${GREEN}✅ NVIDIA GPU detected!${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
else
    echo -e "${YELLOW}⚠️  No NVIDIA GPU detected. Will use CPU.${NC}"
fi

# Check Docker
echo -e "${BLUE}🔍 Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker is installed${NC}"
else
    echo -e "${YELLOW}⚠️  Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}⚠️  Please log out and log back in for Docker group changes.${NC}"
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✅ Docker Compose is installed${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose not found. Installing...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Make deployment script executable
chmod +x deploy.sh

echo -e "${BLUE}🚀 Starting deployment...${NC}"
echo "This will:"
echo "• Install NVIDIA Docker support (if GPU detected)"
echo "• Configure firewall"
echo "• Build and start containers"
echo "• Setup SSL certificates"
echo "• Configure auto-start service"
echo ""

read -p "Continue with deployment? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./deploy.sh
else
    echo -e "${YELLOW}Deployment cancelled. Run './deploy.sh' when ready.${NC}"
fi

echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Check services: docker-compose ps"
echo "2. View logs: docker-compose logs -f"
echo "3. Test frontend: https://nodecel.cloud"
echo "4. Test API: https://nodecel.cloud/health"
echo "5. Monitor GPU: nvidia-smi"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "• Restart: docker-compose restart"
echo "• Stop: docker-compose down"
echo "• Start: docker-compose up -d"
echo "• Update: git pull && docker-compose up -d --build"
echo ""
echo -e "${GREEN}Your SHCI Voice Assistant is ready! 🚀${NC}"
