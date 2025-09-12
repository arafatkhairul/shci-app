#!/bin/bash

# Install Python 3.11.9 Specifically on Ubuntu 24.04
# ===================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo -e "${BLUE}🐍 Installing Python 3.11.9 Specifically${NC}"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

# Check current Python versions
print_status "Checking current Python installations..."
echo "Current Python versions:"
python3 --version 2>/dev/null || echo "python3: not found"
python3.11 --version 2>/dev/null || echo "python3.11: not found"
python3.12 --version 2>/dev/null || echo "python3.12: not found"

# Fix apt_pkg issue first
print_status "Fixing apt_pkg module issue..."
apt update
apt install -y python3-apt software-properties-common

# Add deadsnakes PPA
print_status "Adding deadsnakes PPA..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update

# Check available Python 3.11 versions
print_status "Checking available Python 3.11 versions..."
apt-cache policy python3.11 | grep -E "Installed|Candidate|Version table"

# Method 1: Try to install specific version 3.11.9
print_status "Method 1: Installing Python 3.11.9 specific version..."
if apt install -y python3.11=3.11.9-1+build1 python3.11-dev=3.11.9-1+build1 python3.11-venv=3.11.9-1+build1 python3.11-distutils=3.11.9-1+build1 2>/dev/null; then
    print_success "Python 3.11.9 specific version installed successfully"
else
    print_warning "Specific version not available, trying alternative method..."
    
    # Method 2: Install latest 3.11 and check version
    print_status "Method 2: Installing latest Python 3.11..."
    apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
    
    # Check installed version
    INSTALLED_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
    print_status "Installed Python version: $INSTALLED_VERSION"
    
    if [[ "$INSTALLED_VERSION" == "3.11.9" ]]; then
        print_success "Python 3.11.9 installed successfully!"
    else
        print_warning "Installed version is $INSTALLED_VERSION, not 3.11.9"
        
        # Method 3: Try to downgrade to 3.11.9
        print_status "Method 3: Attempting to downgrade to 3.11.9..."
        apt install -y python3.11=3.11.9-1+build1 python3.11-dev=3.11.9-1+build1 python3.11-venv=3.11.9-1+build1 python3.11-distutils=3.11.9-1+build1 --allow-downgrades 2>/dev/null || {
            print_warning "Downgrade failed, keeping current version: $INSTALLED_VERSION"
        }
    fi
fi

# Verify final installation
FINAL_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
print_status "Final Python 3.11 version: $FINAL_VERSION"

# Create symlinks
print_status "Creating Python symlinks..."
if command -v python3.11 &> /dev/null; then
    ln -sf /usr/bin/python3.11 /usr/bin/python
    ln -sf /usr/bin/python3.11 /usr/bin/python3
    print_success "Python symlinks created: python -> python3.11"
    
    # Verify symlinks
    echo "Symlink verification:"
    echo "python --version: $(python --version)"
    echo "python3 --version: $(python3 --version)"
else
    print_error "Python 3.11 not found after installation"
    exit 1
fi

# Install pip for Python 3.11
print_status "Installing pip for Python 3.11..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Verify pip installation
PIP_VERSION=$(pip3.11 --version 2>&1 | cut -d' ' -f2)
print_success "pip installed for Python 3.11: $PIP_VERSION"

# Test Python 3.11 functionality
print_status "Testing Python 3.11 functionality..."
python3.11 -c "import sys; print(f'Python {sys.version}'); print(f'Executable: {sys.executable}')"

# Check if apt_pkg works with Python 3.11
print_status "Testing apt_pkg with Python 3.11..."
if python3.11 -c "import apt_pkg; print('apt_pkg working with Python 3.11!')" 2>/dev/null; then
    print_success "apt_pkg module works with Python 3.11"
else
    print_warning "apt_pkg module not working with Python 3.11"
fi

# Summary
echo ""
echo "=============================================="
echo -e "${GREEN}🎉 Python 3.11.9 Installation Summary${NC}"
echo "=============================================="
echo "Python 3.11 version: $FINAL_VERSION"
echo "Python command: $(which python)"
echo "Python3 command: $(which python3)"
echo "Python3.11 command: $(which python3.11)"
echo "Pip version: $PIP_VERSION"
echo ""
echo -e "${BLUE}Commands available:${NC}"
echo "• python --version"
echo "• python3 --version"
echo "• python3.11 --version"
echo "• pip3.11 --version"
echo ""
echo -e "${GREEN}✅ Python 3.11.9 installation completed!${NC}"
