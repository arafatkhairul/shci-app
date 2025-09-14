#!/bin/bash

# ===================================================================
# SHCI Voice Assistant - Environment Setup Script
# ===================================================================
# 
# This script helps you quickly switch between development and production
# environments by copying the appropriate configuration file to .env
# 
# Usage:
#   ./setup-environment.sh dev     # Development environment
#   ./setup-environment.sh prod    # Production environment
#   ./setup-environment.sh local   # Local environment
# ===================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo -e "${BLUE}SHCI Voice Assistant - Environment Setup${NC}"
    echo "=============================================="
    echo ""
    echo "Usage: $0 [environment]"
    echo ""
    echo "Environments:"
    echo "  dev     - Development environment (CPU optimized)"
    echo "  prod    - Production environment (GPU optimized)"
    echo "  local   - Local environment (same as dev)"
    echo ""
    echo "Examples:"
    echo "  $0 dev     # Setup for development"
    echo "  $0 prod    # Setup for production/live server"
    echo "  $0 local   # Setup for local development"
    echo ""
    echo "Current environment files:"
    ls -la env.* 2>/dev/null || echo "No environment files found"
}

# Function to setup development environment
setup_dev() {
    print_info "Setting up DEVELOPMENT environment..."
    
    if [ -f "env.professional" ]; then
        cp env.professional .env
        print_status "Development environment configured"
        print_info "Environment: local (development)"
        print_info "Device: CPU optimized"
        print_info "Concurrency: Low (1 STT, 1 TTS)"
    else
        print_error "env.professional not found"
        exit 1
    fi
}

# Function to setup production environment
setup_prod() {
    print_info "Setting up PRODUCTION environment..."
    
    if [ -f "env.production" ]; then
        cp env.production .env
        print_status "Production environment configured"
        print_info "Environment: production"
        print_info "Device: GPU optimized"
        print_info "Concurrency: High (2 STT, 2 TTS)"
        print_warning "Make sure GPU is available for optimal performance"
    else
        print_error "env.production not found"
        exit 1
    fi
}

# Function to test configuration
test_config() {
    print_info "Testing configuration..."
    
    if python -c "from main import app; print('✅ Configuration loaded successfully')" 2>/dev/null; then
        print_status "Configuration test passed"
    else
        print_error "Configuration test failed"
        exit 1
    fi
}

# Function to show current environment
show_current() {
    print_info "Current environment configuration:"
    
    if [ -f ".env" ]; then
        echo ""
        echo "Environment Variables:"
        grep -E "^(TTS_ENVIRONMENT|ENVIRONMENT|NODE_ENV)=" .env || echo "No environment variables found"
        echo ""
        echo "TTS Configuration:"
        grep -E "^(TTS_SYSTEM|PIPER_)=" .env || echo "No TTS configuration found"
        echo ""
        echo "Concurrency:"
        grep -E "^(STT_CONCURRENCY|TTS_CONCURRENCY)=" .env || echo "No concurrency settings found"
    else
        print_warning "No .env file found"
    fi
}

# Main script logic
case "${1:-}" in
    "dev"|"development")
        setup_dev
        test_config
        show_current
        ;;
    "prod"|"production")
        setup_prod
        test_config
        show_current
        ;;
    "local")
        setup_dev
        test_config
        show_current
        ;;
    "test")
        test_config
        ;;
    "show"|"status")
        show_current
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    "")
        print_error "No environment specified"
        echo ""
        show_usage
        exit 1
        ;;
    *)
        print_error "Unknown environment: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac

print_status "Environment setup complete!"
echo ""
print_info "To start the server:"
echo "  python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo ""
print_info "To check configuration:"
echo "  python -c \"from tts_factory import get_tts_info; print(get_tts_info()['environment'])\""
