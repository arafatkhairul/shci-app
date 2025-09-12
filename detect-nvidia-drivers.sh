#!/bin/bash

# NVIDIA Driver Detection Script
# This script detects available NVIDIA driver versions for Ubuntu 24.04

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

echo -e "${BLUE}🔍 NVIDIA Driver Detection${NC}"
echo "============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

print_status "Detecting available NVIDIA driver versions..."

# Update package list
apt update > /dev/null 2>&1

# Check available NVIDIA driver versions
print_status "Checking available NVIDIA driver packages..."

# List of driver versions to check (from newest to oldest)
driver_versions=(
    "nvidia-driver-560"
    "nvidia-driver-555"
    "nvidia-driver-550"
    "nvidia-driver-545"
    "nvidia-driver-535"
    "nvidia-driver-525"
    "nvidia-driver-520"
)

available_drivers=()

for driver in "${driver_versions[@]}"; do
    if apt-cache search "^$driver$" | grep -q "$driver"; then
        available_drivers+=("$driver")
        print_success "$driver is available"
    else
        print_warning "$driver is not available"
    fi
done

echo ""
if [ ${#available_drivers[@]} -gt 0 ]; then
    print_success "Available NVIDIA drivers:"
    for driver in "${available_drivers[@]}"; do
        echo "  - $driver"
    done
    
    # Recommend the newest available driver
    recommended_driver="${available_drivers[0]}"
    print_status "Recommended driver: $recommended_driver"
    
    # Extract version number
    driver_version=$(echo "$recommended_driver" | sed 's/nvidia-driver-//')
    
    echo ""
    print_status "🎯 Installation commands:"
    echo "apt install -y $recommended_driver nvidia-dkms-$driver_version"
    
    # Create environment variable for use in other scripts
    echo ""
    print_status "Environment variable for scripts:"
    echo "export NVIDIA_DRIVER_VERSION=$driver_version"
    echo "export NVIDIA_DRIVER_PACKAGE=$recommended_driver"
    
else
    print_error "No NVIDIA drivers found in repositories"
    print_status "Trying alternative installation methods..."
    
    # Check if ubuntu-drivers is available
    if command -v ubuntu-drivers &> /dev/null; then
        print_status "Using ubuntu-drivers to detect available drivers..."
        ubuntu-drivers list
    else
        print_warning "ubuntu-drivers not available"
    fi
fi

echo ""
print_status "🔧 Manual Installation Options:"
echo "1. Use ubuntu-drivers: ubuntu-drivers autoinstall"
echo "2. Check NVIDIA website for latest drivers"
echo "3. Use CUDA toolkit installation (includes drivers)"

echo ""
print_warning "Note: After installing drivers, reboot the system"
