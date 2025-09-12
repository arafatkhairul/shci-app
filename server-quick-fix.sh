#!/bin/bash

# Server Quick Fix Script
# This script fixes common deployment issues on the server

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo -e "${BLUE}🔧 Server Quick Fix${NC}"
echo "====================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Fix 1: Create .env.production from env.production if it doesn't exist
print_status "Fixing environment file..."
if [ -f "env.production" ] && [ ! -f ".env.production" ]; then
    print_status "Creating .env.production from env.production..."
    cp env.production .env.production
    print_success ".env.production created"
elif [ -f ".env.production" ]; then
    print_success ".env.production already exists"
else
    print_warning "No environment file found - will be created during deployment"
fi

# Fix 2: Validate docker-compose files
print_status "Validating Docker Compose files..."

# Check docker-compose.yml
if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
    print_success "docker-compose.yml is valid"
else
    print_error "docker-compose.yml has validation errors:"
    docker-compose -f docker-compose.yml config
    exit 1
fi

# Check docker-compose.local.yml
if docker-compose -f docker-compose.local.yml config > /dev/null 2>&1; then
    print_success "docker-compose.local.yml is valid"
else
    print_error "docker-compose.local.yml has validation errors:"
    docker-compose -f docker-compose.local.yml config
    exit 1
fi

# Fix 3: Check required directories
print_status "Checking required directories..."
required_dirs=("fastapi-backend" "web-app" "nginx" "models")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_success "Directory $dir exists"
    else
        print_error "Required directory $dir not found"
        exit 1
    fi
done

# Fix 4: Check required files
print_status "Checking required files..."
required_files=("fastapi-backend/Dockerfile" "web-app/Dockerfile" "nginx/nginx.conf")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "File $file exists"
    else
        print_error "Required file $file not found"
        exit 1
    fi
done

# Fix 5: Make scripts executable
print_status "Making scripts executable..."
chmod +x deploy.sh quick-setup.sh validate-docker-compose.sh 2>/dev/null
print_success "Scripts made executable"

# Fix 6: Check Docker and Docker Compose
print_status "Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_success "Docker is installed"
else
    print_error "Docker not found. Please install Docker first."
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose is installed"
else
    print_error "Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Fix 7: Check for GPU support and set Dockerfile
print_status "Checking GPU support..."
if lspci | grep -i nvidia &> /dev/null; then
    print_success "NVIDIA GPU detected"
    if command -v nvidia-smi &> /dev/null; then
        print_success "NVIDIA drivers installed"
    else
        print_warning "NVIDIA drivers not installed - will be installed during deployment"
    fi
    
    # Set GPU Dockerfile
    export BACKEND_DOCKERFILE="Dockerfile"
    print_status "Using GPU-enabled Dockerfile"
else
    print_warning "No NVIDIA GPU detected - will use CPU"
    
    # Set CPU Dockerfile
    export BACKEND_DOCKERFILE="Dockerfile.cpu"
    print_status "Using CPU-only Dockerfile"
fi

# Fix 8: Check Ollama service
print_status "Checking Ollama service..."
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_success "Ollama service is running"
else
    print_warning "Ollama service not detected - will use external LLM"
fi

# Fix 9: Configure Git credentials
print_status "Configuring Git credentials..."
if [ -f "configure-git-credentials.sh" ]; then
    chmod +x configure-git-credentials.sh
    ./configure-git-credentials.sh
    print_success "Git credentials configured"
else
    print_warning "Git credentials script not found - manual configuration needed"
fi

# Fix 10: Check NVIDIA driver availability
print_status "Checking NVIDIA driver availability..."
if [ -f "detect-nvidia-drivers.sh" ]; then
    chmod +x detect-nvidia-drivers.sh
    ./detect-nvidia-drivers.sh
    print_success "NVIDIA driver detection completed"
else
    print_warning "NVIDIA driver detection script not found"
fi

# Fix 11: Verify Python 3.11.9 installation
print_status "Verifying Python 3.11.9 installation..."
if [ -f "verify-python-version.sh" ]; then
    chmod +x verify-python-version.sh
    ./verify-python-version.sh
    print_success "Python 3.11.9 verification completed"
else
    print_warning "Python verification script not found"
fi

echo ""
print_success "🎉 Server quick fix completed!"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Run: ./deploy.sh (for full deployment)"
echo "2. Run: ./quick-setup.sh (for quick deployment)"
echo "3. Run: docker-compose up -d (to start services)"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "- Make sure domain DNS is pointing to this server"
echo "- Check firewall allows ports 80, 443, and 22"
echo "- Verify SSL certificates are working"
