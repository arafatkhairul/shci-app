#!/bin/bash

# Python Version Verification Script
# This script verifies Python 3.11.9 installation

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

echo -e "${BLUE}🐍 Python Version Verification${NC}"
echo "=============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

print_status "Checking Python installation..."

# Check if Python 3.11 is installed
if command -v python3.11 &> /dev/null; then
    python_version=$(python3.11 --version 2>&1)
    print_success "Python 3.11 found: $python_version"
    
    # Check if it's version 3.11.9
    if echo "$python_version" | grep -q "3.11.9"; then
        print_success "Perfect! Python 3.11.9 is installed"
    else
        print_warning "Python 3.11 found but not version 3.11.9"
        print_status "Current version: $python_version"
    fi
else
    print_error "Python 3.11 not found"
    print_status "Installing Python 3.11.9..."
    
    # Install Python 3.11.9
    apt update
    apt install -y software-properties-common
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.11 python3.11-dev python3.11-venv python3-pip
    
    # Verify installation
    if command -v python3.11 &> /dev/null; then
        python_version=$(python3.11 --version 2>&1)
        print_success "Python 3.11 installed: $python_version"
    else
        print_error "Failed to install Python 3.11"
        exit 1
    fi
fi

# Check Python symlink
if [ -L "/usr/bin/python" ]; then
    python_link=$(readlink /usr/bin/python)
    print_success "Python symlink exists: /usr/bin/python -> $python_link"
else
    print_warning "Python symlink not found, creating..."
    ln -s /usr/bin/python3.11 /usr/bin/python
    print_success "Python symlink created"
fi

# Check pip installation
if command -v pip3 &> /dev/null; then
    pip_version=$(pip3 --version 2>&1)
    print_success "pip3 found: $pip_version"
else
    print_warning "pip3 not found, installing..."
    apt install -y python3-pip
    print_success "pip3 installed"
fi

# Test Python functionality
print_status "Testing Python functionality..."

# Test basic Python import
if python3.11 -c "import sys; print(f'Python {sys.version}')" 2>/dev/null; then
    print_success "Python 3.11 is working correctly"
else
    print_error "Python 3.11 is not working correctly"
    exit 1
fi

# Test pip functionality
if pip3 --version > /dev/null 2>&1; then
    print_success "pip3 is working correctly"
else
    print_error "pip3 is not working correctly"
    exit 1
fi

echo ""
print_success "🎉 Python 3.11.9 verification completed!"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "Python Version: $(python3.11 --version)"
echo "Python Path: $(which python3.11)"
echo "pip Version: $(pip3 --version)"
echo "Symlink: $(readlink /usr/bin/python 2>/dev/null || echo 'Not found')"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. Run: ./deploy.sh (to deploy with Python 3.11.9)"
echo "2. Run: docker-compose up -d (to start services)"
echo "3. Check: python3.11 --version (to verify)"
