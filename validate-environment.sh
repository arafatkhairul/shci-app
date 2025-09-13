#!/bin/bash

# SHCI Environment Validation Script
# This script validates the deployment environment

echo "🔍 SHCI Environment Validation Starting..."
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
    fi
}

# Check Node.js
echo "📦 Checking Node.js..."
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_status "Node.js installed: $NODE_VERSION" 0
else
    print_status "Node.js not installed" 1
fi

# Check npm
echo "📦 Checking npm..."
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_status "npm installed: $NPM_VERSION" 0
else
    print_status "npm not installed" 1
fi

# Check Python
echo "🐍 Checking Python..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python3 installed: $PYTHON_VERSION" 0
else
    print_status "Python3 not installed" 1
fi

# Check pip
echo "🐍 Checking pip..."
if command_exists pip3; then
    PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
    print_status "pip3 installed: $PIP_VERSION" 0
else
    print_status "pip3 not installed" 1
fi

# Check if frontend directory exists
echo "📁 Checking frontend directory..."
if [ -d "web-app" ]; then
    print_status "Frontend directory exists" 0
else
    print_status "Frontend directory missing" 1
fi

# Check if backend directory exists
echo "📁 Checking backend directory..."
if [ -d "fastapi-backend" ]; then
    print_status "Backend directory exists" 0
else
    print_status "Backend directory missing" 1
fi

# Check frontend package.json
echo "📦 Checking frontend package.json..."
if [ -f "web-app/package.json" ]; then
    print_status "Frontend package.json exists" 0
else
    print_status "Frontend package.json missing" 1
fi

# Check backend requirements.txt
echo "📦 Checking backend requirements.txt..."
if [ -f "fastapi-backend/requirements.txt" ]; then
    print_status "Backend requirements.txt exists" 0
else
    print_status "Backend requirements.txt missing" 1
fi

# Check environment files
echo "🔧 Checking environment files..."
if [ -f "web-app/.env.local" ]; then
    print_status "Frontend .env.local exists" 0
else
    echo -e "${YELLOW}⚠️  Frontend .env.local missing (create from .env.example)${NC}"
fi

if [ -f "fastapi-backend/.env" ]; then
    print_status "Backend .env exists" 0
else
    echo -e "${YELLOW}⚠️  Backend .env missing (create from env_example.txt)${NC}"
fi

# Check deployment script
echo "🚀 Checking deployment script..."
if [ -f "deploy.sh" ]; then
    if [ -x "deploy.sh" ]; then
        print_status "Deploy script exists and is executable" 0
    else
        echo -e "${YELLOW}⚠️  Deploy script exists but not executable (run: chmod +x deploy.sh)${NC}"
    fi
else
    print_status "Deploy script missing" 1
fi

# Check GitHub Actions workflow
echo "🔄 Checking GitHub Actions workflow..."
if [ -f ".github/workflows/deploy.yml" ]; then
    print_status "GitHub Actions workflow exists" 0
else
    print_status "GitHub Actions workflow missing" 1
fi

# Check disk space
echo "💾 Checking disk space..."
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_status "Disk space OK: ${DISK_USAGE}% used" 0
else
    echo -e "${YELLOW}⚠️  Disk space low: ${DISK_USAGE}% used${NC}"
fi

# Check memory
echo "🧠 Checking memory..."
if command_exists free; then
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$MEMORY_USAGE" -lt 80 ]; then
        print_status "Memory OK: ${MEMORY_USAGE}% used" 0
    else
        echo -e "${YELLOW}⚠️  Memory usage high: ${MEMORY_USAGE}% used${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Cannot check memory (free command not available)${NC}"
fi

echo ""
echo "=========================================="
echo "🎯 Environment validation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Fix any ❌ errors above"
echo "2. Address any ⚠️  warnings"
echo "3. Run deployment: bash deploy.sh"
echo "4. Test the application"
echo ""
echo "📚 For more help, see DEPLOYMENT.md"
