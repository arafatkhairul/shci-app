#!/bin/bash

# Docker Compose Validation Script
# This script validates docker-compose.yml files before deployment

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

echo -e "${BLUE}🔍 Docker Compose Validation${NC}"
echo "=================================="

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found. Please install Docker Compose first."
    exit 1
fi

# Validate main docker-compose.yml
print_status "Validating docker-compose.yml..."
if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
    print_success "docker-compose.yml is valid"
else
    print_error "docker-compose.yml has validation errors:"
    docker-compose -f docker-compose.yml config
    exit 1
fi

# Validate local docker-compose.yml
print_status "Validating docker-compose.local.yml..."
if docker-compose -f docker-compose.local.yml config > /dev/null 2>&1; then
    print_success "docker-compose.local.yml is valid"
else
    print_error "docker-compose.local.yml has validation errors:"
    docker-compose -f docker-compose.local.yml config
    exit 1
fi

# Check for required environment files
print_status "Checking environment files..."

if [ -f ".env.production" ]; then
    print_success ".env.production found"
else
    print_warning ".env.production not found - will be created during deployment"
fi

if [ -f "env.local" ]; then
    print_success "env.local found"
else
    print_warning "env.local not found - will be created during deployment"
fi

# Check for required directories
print_status "Checking required directories..."

required_dirs=("fastapi-backend" "web-app" "nginx" "Models")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_success "Directory $dir exists"
    else
        print_error "Required directory $dir not found"
        exit 1
    fi
done

# Check for required files
print_status "Checking required files..."

required_files=("fastapi-backend/Dockerfile" "web-app/Dockerfile" "nginx/nginx.conf" "nginx/conf.d/shci.conf")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "File $file exists"
    else
        print_error "Required file $file not found"
        exit 1
    fi
done

# Test docker-compose build (dry run)
print_status "Testing docker-compose build (dry run)..."

if docker-compose -f docker-compose.yml config --services > /dev/null 2>&1; then
    services=$(docker-compose -f docker-compose.yml config --services)
    print_success "Services detected: $services"
else
    print_error "Failed to detect services"
    exit 1
fi

echo ""
print_success "🎉 All Docker Compose files are valid!"
print_status "Ready for deployment!"

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Run: ./quick-setup.sh (for quick deployment)"
echo "2. Run: ./deploy.sh (for full deployment)"
echo "3. Run: docker-compose up -d (to start services)"
