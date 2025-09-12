#!/bin/bash

# Fix apt_pkg ModuleNotFoundError on Ubuntu
# ========================================

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

echo -e "${BLUE}🔧 Fixing apt_pkg ModuleNotFoundError${NC}"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

print_status "Diagnosing apt_pkg issue..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
print_status "Current Python version: $PYTHON_VERSION"

# Check if apt_pkg module exists
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg module is working correctly"
    exit 0
else
    print_warning "apt_pkg module not found, fixing..."
fi

# Method 1: Install python3-apt
print_status "Method 1: Installing python3-apt..."
apt update
apt install -y python3-apt

# Check if it's fixed
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg fixed with python3-apt installation"
    exit 0
fi

# Method 2: Reinstall python3-apt
print_status "Method 2: Reinstalling python3-apt..."
apt remove -y python3-apt
apt autoremove -y
apt update
apt install -y python3-apt

# Check if it's fixed
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg fixed with python3-apt reinstallation"
    exit 0
fi

# Method 3: Install python3-apt with specific version
print_status "Method 3: Installing specific python3-apt version..."
apt install -y python3-apt=2.8.0ubuntu1

# Check if it's fixed
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg fixed with specific version"
    exit 0
fi

# Method 4: Fix broken packages
print_status "Method 4: Fixing broken packages..."
apt --fix-broken install -y
apt autoremove -y
apt autoclean
apt update

# Check if it's fixed
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg fixed with package repair"
    exit 0
fi

# Method 5: Manual symlink creation
print_status "Method 5: Creating manual symlinks..."

# Find apt_pkg files
APT_PKG_FILES=$(find /usr/lib/python3/dist-packages -name "*apt_pkg*" 2>/dev/null || true)

if [ -n "$APT_PKG_FILES" ]; then
    print_status "Found apt_pkg files: $APT_PKG_FILES"
    
    # Create symlinks for apt_pkg
    for file in $APT_PKG_FILES; do
        if [[ "$file" == *".so" ]]; then
            filename=$(basename "$file")
            target="/usr/lib/python3/dist-packages/$filename"
            if [ ! -f "$target" ]; then
                ln -sf "$file" "$target"
                print_status "Created symlink: $target -> $file"
            fi
        fi
    done
fi

# Check if it's fixed
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg fixed with manual symlinks"
    exit 0
fi

# Method 6: Install python3-dev and rebuild
print_status "Method 6: Installing python3-dev and rebuilding..."
apt install -y python3-dev python3-distutils python3-setuptools
pip3 install --upgrade pip setuptools wheel

# Check if it's fixed
if python3 -c "import apt_pkg" 2>/dev/null; then
    print_success "apt_pkg fixed with dev packages"
    exit 0
fi

# Method 7: Alternative approach - use apt directly
print_status "Method 7: Testing alternative approach..."
if command -v apt &> /dev/null; then
    print_success "apt command is available, trying alternative method..."
    
    # Update package lists
    apt update
    
    # Install essential packages
    apt install -y software-properties-common apt-transport-https ca-certificates
    
    # Try to add deadsnakes PPA using apt directly
    print_status "Adding deadsnakes PPA using alternative method..."
    
    # Add PPA key
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776
    
    # Add PPA repository
    echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu $(lsb_release -cs) main" > /etc/apt/sources.list.d/deadsnakes.list
    
    # Update package lists
    apt update
    
    print_success "PPA added successfully using alternative method"
    
    # Now install Python 3.11.9 specifically
    print_status "Installing Python 3.11.9 specifically..."
    apt install -y python3.11=3.11.9-1+build1 python3.11-dev=3.11.9-1+build1 python3.11-venv=3.11.9-1+build1 python3.11-distutils=3.11.9-1+build1
    
    # Verify installation
    PYTHON_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
    if [[ "$PYTHON_VERSION" == "3.11.9" ]]; then
        print_success "Python 3.11.9 installed successfully: $PYTHON_VERSION"
        
        # Create symlinks
        ln -sf /usr/bin/python3.11 /usr/bin/python
        ln -sf /usr/bin/python3.11 /usr/bin/python3
        print_success "Python symlinks created: python -> python3.11"
        
        # Install pip
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
        print_success "pip installed for Python 3.11.9"
    else
        print_warning "Python 3.11.9 not found, installed version: $PYTHON_VERSION"
    fi
    
    exit 0
fi

# If all methods fail
print_error "Could not fix apt_pkg issue with standard methods"
print_warning "Manual intervention may be required"

# Show diagnostic information
print_status "Diagnostic information:"
echo "Python version: $(python3 --version)"
echo "Python path: $(python3 -c 'import sys; print(sys.path)')"
echo "Available apt_pkg files:"
find /usr/lib/python3* -name "*apt_pkg*" 2>/dev/null || echo "None found"

exit 1
