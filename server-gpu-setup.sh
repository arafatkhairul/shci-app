#!/bin/bash
# ===================================================================
# Server GPU Setup Script
# ===================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}================================================================================${NC}"
    echo -e "${BLUE}🚀 $1${NC}"
    echo -e "${BLUE}================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Configuration
PROJECT_DIR="/var/www/shci-app"

print_header "SHCI GPU Setup Script"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

# 1. Navigate to project directory
print_header "Navigating to project directory"
cd "$PROJECT_DIR" || { print_error "Project directory not found"; exit 1; }
print_success "In project directory: $PROJECT_DIR"

# 2. Pull latest code
print_header "Pulling latest code"
git pull origin feature/tts-medium-variants
print_success "Code updated"

# 3. Enable GPU persistence mode
print_header "Enabling GPU persistence mode"
nvidia-smi -pm 1
print_success "GPU persistence mode enabled"

# 4. Install Python dependencies
print_header "Installing Python dependencies"
cd "$PROJECT_DIR/fastapi-backend"

# Try system packages first
print_warning "Trying system package manager first..."
if apt install -y python3-pynvml python3-torch 2>/dev/null; then
    print_success "Python dependencies installed via system packages"
else
    print_warning "System packages not available, trying pip with --break-system-packages..."
    pip install torch pynvml --break-system-packages
    print_success "Python dependencies installed via pip"
fi

# 5. Copy GPU-enabled environment
print_header "Setting up GPU-enabled environment"
cp env.gpu .env
print_success "GPU environment configured"

# 6. Install GPU keep-alive service
print_header "Installing GPU keep-alive service"
cp ../gpu-keepalive.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable gpu-keepalive.service
print_success "GPU keep-alive service installed"

# 7. Make scripts executable
print_header "Making scripts executable"
chmod +x ../*.sh
chmod +x ../*.py
print_success "Scripts made executable"

# 8. Restart services
print_header "Restarting services"
systemctl restart shci-backend shci-frontend nginx
print_success "Services restarted"

# 9. Start GPU keep-alive service
print_header "Starting GPU keep-alive service"
systemctl start gpu-keepalive.service
print_success "GPU keep-alive service started"

# 10. Check service status
print_header "Checking service status"
echo "Backend Service:"
systemctl is-active shci-backend.service && print_success "Backend is running" || print_error "Backend failed"

echo "Frontend Service:"
systemctl is-active shci-frontend.service && print_success "Frontend is running" || print_error "Frontend failed"

echo "GPU Keep-Alive Service:"
systemctl is-active gpu-keepalive.service && print_success "GPU keep-alive is running" || print_error "GPU keep-alive failed"

# 11. Check GPU status
print_header "GPU Status"
nvidia-smi --query-gpu=name,driver_version,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits

# 12. Show monitoring commands
print_header "Monitoring Commands"
echo "Backend logs: journalctl -u shci-backend.service -f"
echo "GPU processes: nvidia-smi pmon -c 1"
echo "GPU keep-alive logs: journalctl -u gpu-keepalive.service -f"
echo "GPU usage check: ./check-gpu-usage.sh"
echo "Real-time monitoring: watch -n 1 'nvidia-smi pmon -c 1'"

print_success "GPU setup completed successfully!"
print_warning "Monitor the services and GPU usage to ensure everything is working correctly"
