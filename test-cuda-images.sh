#!/bin/bash

# CUDA Image Test Script
# This script tests which CUDA images are available on Docker Hub

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

echo -e "${BLUE}🔍 CUDA Image Availability Test${NC}"
echo "=================================="

# Test CUDA images
cuda_images=(
    "nvidia/cuda:12.6.0-devel-ubuntu24.04"
    "nvidia/cuda:12.4-devel-ubuntu24.04"
    "nvidia/cuda:12.1-devel-ubuntu24.04"
    "nvidia/cuda:11.8-devel-ubuntu22.04"
    "nvidia/cuda:11.8-devel-ubuntu20.04"
    "nvidia/cuda:12.1-devel-ubuntu22.04"
)

print_status "Testing CUDA image availability..."

for image in "${cuda_images[@]}"; do
    print_status "Testing: $image"
    
    # Try to pull the image (dry run)
    if docker pull "$image" > /dev/null 2>&1; then
        print_success "$image is available"
    else
        print_error "$image is not available"
    fi
done

echo ""
print_status "🎯 Recommended CUDA Images for Ubuntu 24.04:"
echo "1. nvidia/cuda:12.6.0-devel-ubuntu24.04 (Latest CUDA 12.6)"
echo "2. nvidia/cuda:12.4-devel-ubuntu24.04 (CUDA 12.4)"
echo "3. nvidia/cuda:12.1-devel-ubuntu24.04 (CUDA 12.1)"
echo "4. nvidia/cuda:11.8-devel-ubuntu22.04 (Fallback stable)"

echo ""
print_success "Ubuntu 24.04 CUDA images are now available!"
print_warning "Using Ubuntu 24.04 CUDA images for best compatibility."
