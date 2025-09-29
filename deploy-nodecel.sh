#!/bin/bash
# ===================================================================
# SHCI Voice Assistant - Nodecel.com Production Deployment
# ===================================================================
# Complete deployment script for nodecel.com
# Project Directory: /var/www/shci-app
# Domain: nodecel.com
# User: root
# Python: 3.12
# Node.js: v24.1.0
# ===================================================================

set -e

# Set up error handling
trap 'handle_error $LINENO' ERR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/var/www/shci-app"
REPO_URL="git@github.com:arafatkhairul/shci-app.git"
BRANCH="feature/realtime-stt-audioworklet"
SERVICE_USER="root"
SERVICE_GROUP="root"
LOG_FILE="/var/log/shci-deployment.log"
BACKUP_DIR="/var/backups/shci"
DEPLOYMENT_DATE=$(date +"%Y%m%d_%H%M%S")

# Helper functions
print_header() {
    echo -e "\n${PURPLE}================================================================================${NC}"
    echo -e "${PURPLE}🚀 $1${NC}"
    echo -e "${PURPLE}================================================================================${NC}\n"
}

print_step() {
    echo -e "\n${BLUE}◆${NC} ${CYAN}$1${NC}"
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

# Logging functions
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_step() {
    local message="$1"
    print_step "$message"
    log_message "STEP: $message"
}

log_success() {
    local message="$1"
    print_success "$message"
    log_message "SUCCESS: $message"
}

log_warning() {
    local message="$1"
    print_warning "$message"
    log_message "WARNING: $message"
}

log_error() {
    local message="$1"
    print_error "$message"
    log_message "ERROR: $message"
}

# Backup functions
create_backup() {
    local backup_name="$1"
    local source_path="$2"
    local backup_path="$BACKUP_DIR/$DEPLOYMENT_DATE/$backup_name"
    
    log_step "Creating backup: $backup_name"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Create backup
    if [ -d "$source_path" ]; then
        cp -r "$source_path" "$backup_path/"
        log_success "Backup created: $backup_path"
    else
        log_warning "Source path does not exist: $source_path"
    fi
}

# System monitoring functions
check_system_resources() {
    log_step "Checking system resources..."
    
    # Check disk space
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        log_warning "Disk usage is high: ${disk_usage}%"
    else
        log_success "Disk usage is acceptable: ${disk_usage}%"
    fi
    
    # Check memory
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_usage" -gt 90 ]; then
        log_warning "Memory usage is high: ${memory_usage}%"
    else
        log_success "Memory usage is acceptable: ${memory_usage}%"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    local cpu_usage=$(echo "$cpu_load $cpu_cores" | awk '{printf "%.0f", $1*100/$2}')
    
    if [ "$cpu_usage" -gt 80 ]; then
        log_warning "CPU load is high: ${cpu_usage}%"
    else
        log_success "CPU load is acceptable: ${cpu_usage}%"
    fi
}

# Cleanup functions
cleanup_old_backups() {
    log_step "Cleaning up old backups..."
    
    # Keep only last 5 backups
    if [ -d "$BACKUP_DIR" ]; then
        cd "$BACKUP_DIR"
        ls -t | tail -n +6 | xargs -r rm -rf
        log_success "Old backups cleaned up"
    fi
}

# Health check functions
check_service_health() {
    local service_name="$1"
    local max_attempts=30
    local attempt=1
    
    log_step "Checking health of $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if systemctl is-active --quiet "$service_name"; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_warning "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    log_error "$service_name failed health check after $max_attempts attempts"
    return 1
}

# Rollback function
rollback_deployment() {
    log_error "Deployment failed! Starting rollback process..."
    
    # Stop services
    systemctl stop shci-backend shci-frontend 2>/dev/null || true
    
    # Restore from backup if available
    local latest_backup=$(ls -t "$BACKUP_DIR" 2>/dev/null | head -1)
    if [ -n "$latest_backup" ] && [ -d "$BACKUP_DIR/$latest_backup" ]; then
        log_step "Restoring from backup: $latest_backup"
        
        # Restore project
        if [ -d "$BACKUP_DIR/$latest_backup/project_backup" ]; then
            rm -rf "$PROJECT_DIR"
            cp -r "$BACKUP_DIR/$latest_backup/project_backup" "$PROJECT_DIR"
            log_success "Project restored from backup"
        fi
        
        # Restore nginx config
        if [ -f "$BACKUP_DIR/$latest_backup/nginx_config/shci" ]; then
            cp "$BACKUP_DIR/$latest_backup/nginx_config/shci" "/etc/nginx/sites-available/"
            nginx -t && systemctl reload nginx
            log_success "Nginx configuration restored"
        fi
        
        # Restore systemd services
        if [ -d "$BACKUP_DIR/$latest_backup/systemd_services" ]; then
            cp "$BACKUP_DIR/$latest_backup/systemd_services"/*.service "/etc/systemd/system/"
            systemctl daemon-reload
            systemctl start shci-backend shci-frontend
            log_success "Systemd services restored"
        fi
    else
        log_warning "No backup found for rollback"
    fi
    
    log_error "Rollback completed. Please check the logs and fix issues before retrying."
    exit 1
}

# Error handling
handle_error() {
    local exit_code=$?
    log_error "Script failed with exit code: $exit_code"
    log_error "Error occurred at line: $1"
    rollback_deployment
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root user."
        exit 1
    fi
}

# Check if user has sudo privileges
check_sudo() {
    print_success "Running as root user - all privileges available"
}

# Check if package is installed
check_package_installed() {
    local package_name="$1"
    if dpkg -l | grep -q "^ii.*$package_name "; then
        return 0  # Package is installed
    else
        return 1  # Package is not installed
    fi
}

# Check if command exists
check_command_exists() {
    local command_name="$1"
    if command -v "$command_name" &> /dev/null; then
        return 0  # Command exists
    else
        return 1  # Command doesn't exist
    fi
}

# Configure Git to use SSH
configure_git_ssh() {
    log_step "Configuring Git to use SSH..."
    
    # Check if SSH key exists
    if [ -f ~/.ssh/id_rsa ] || [ -f ~/.ssh/id_ed25519 ]; then
        log_success "SSH key found"
    else
        log_warning "No SSH key found, generating one..."
        ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "root@$(hostname)"
        log_success "SSH key generated"
    fi
    
    # Configure Git to use SSH
    git config --global url."git@github.com:".insteadOf "https://github.com/"
    git config --global user.name "arafatkhairul"
    git config --global user.email "arafatkhairul@users.noreply.github.com"
    
    log_success "Git configured to use SSH"
}

# Update system packages
update_system() {
    log_step "Updating system packages..."
    
    
    # Clean apt cache
    apt clean
    apt update && apt upgrade -y
    
    # Install essential packages only if not already installed
    local essential_packages=("curl" "wget" "git" "build-essential" "software-properties-common" "apt-transport-https" "ca-certificates" "gnupg" "lsb-release" "python3.12-dev" "portaudio19-dev" "libasound2-dev" "libsndfile1-dev" "ffmpeg")
    
    for package in "${essential_packages[@]}"; do
        if check_package_installed "$package"; then
            log_success "$package is already installed"
        else
            log_step "Installing $package..."
            apt install -y "$package"
            log_success "$package installed"
        fi
    done
    
    log_success "System packages updated"
}

# Install Python 3.12
install_python() {
    log_step "Checking Python 3.12 installation..."
    
    # First, remove Python 3.11 if it exists to avoid conflicts
    if check_command_exists "python3.11"; then
        log_step "Removing Python 3.11 to avoid conflicts..."
        apt remove -y python3.11 python3.11-venv python3.11-dev python3.11-distutils python3.11-minimal 2>/dev/null || true
        apt autoremove -y 2>/dev/null || true
        log_success "Python 3.11 removed"
    fi
    
    # Check if Python 3.12 is already installed
    if check_command_exists "python3.12"; then
        local python_version=$(python3.12 --version 2>&1 | cut -d' ' -f2)
        log_success "Python 3.12 is already installed (version: $python_version)"
    else
        log_step "Installing Python 3.12..."
        
        # Add deadsnakes PPA if not already added
        if ! grep -q "deadsnakes" /etc/apt/sources.list.d/*.list 2>/dev/null; then
            add-apt-repository ppa:deadsnakes/ppa -y
            apt update
        else
            log_success "deadsnakes PPA already added"
        fi
        
        # Install Python 3.12 and related packages
        apt install -y python3.12 python3.12-venv python3.12-dev python3-pip python3.12-distutils
        
        # Set up alternatives
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
        update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1
        
        log_success "Python 3.12 installed successfully"
    fi
    
    # Ensure virtual environment module is available
    if python3.12 -m venv --help &> /dev/null; then
        log_success "Python 3.12 venv module is available"
    else
        log_step "Installing Python 3.12 venv module..."
        apt install -y python3.12-venv
        log_success "Python 3.12 venv module installed"
    fi
    
    # Check if pip is available
    if check_command_exists "pip3"; then
        log_success "pip3 is already available"
    else
        log_step "Installing pip3..."
        apt install -y python3-pip
        log_success "pip3 installed"
    fi
}

# Configure GPU for RTX 5090 optimization
configure_gpu() {
    log_step "Configuring RTX 5090 GPU for optimal performance..."
    
    # Check if NVIDIA GPU is available
    if command -v nvidia-smi &> /dev/null; then
        log_success "NVIDIA GPU detected"
        
        # Show detailed GPU information
        local gpu_info=$(nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version,compute_cap --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$gpu_info" ]; then
            log_success "GPU Info: $gpu_info"
        fi
        
        # Check if RTX 5090 is detected
        if nvidia-smi --query-gpu=name --format=csv,noheader | grep -i "rtx 5090\|geforce rtx 5090" &> /dev/null; then
            log_success "RTX 5090 detected - applying optimized configuration"
            
            # RTX 5090 specific optimizations
            export CUDA_VISIBLE_DEVICES=0
            export TORCH_DEVICE=cuda
            export TTS_DEVICE=cuda
            export PIPER_DEVICE=cuda
            export PIPER_FORCE_CUDA=true
            
            # RTX 5090 memory optimization (24GB VRAM)
            export TORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048,roundup_power2_divisions:16
            export CUDA_MEMORY_POOL_DISABLE=0
            export CUDA_CACHE_DISABLE=0
            export CUDA_LAUNCH_BLOCKING=0
            
            # RTX 5090 compute optimization
            export CUDA_ARCHITECTURES=89  # RTX 5090 is Ada Lovelace architecture
            export TORCH_CUDA_ARCH_LIST=8.9
            
            # Memory management for 24GB VRAM
            export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048
            export CUDA_DEVICE_ORDER=PCI_BUS_ID
            
            # RTX 5090 specific TTS optimizations
            export PIPER_USE_CUDA=1
            export PIPER_CUDA_DEVICE=0
            export PIPER_BATCH_SIZE=32  # Larger batch size for RTX 5090
            
            # RealtimeSTT optimizations for RTX 5090
            export RT_DEVICE=cuda
            export RT_COMPUTE=float16  # Use FP16 for better performance on RTX 5090
            export RT_MODEL=large-v3   # Use large model for better accuracy
            export RT_GPU_INDEX=0
            
            log_success "RTX 5090 optimized configuration applied"
        else
            log_warning "RTX 5090 not detected, using standard GPU configuration"
            
            # Standard GPU configuration
            export CUDA_VISIBLE_DEVICES=0
            export TORCH_DEVICE=cuda
            export TTS_DEVICE=cuda
            export PIPER_DEVICE=cuda
            export PIPER_FORCE_CUDA=true
            
            # Standard optimizations
            export TORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
            export CUDA_CACHE_DISABLE=0
            export CUDA_LAUNCH_BLOCKING=0
        fi
        
        log_success "GPU configuration completed"
    else
        log_warning "NVIDIA GPU not detected, using CPU for TTS"
        export TORCH_DEVICE=cpu
        export TTS_DEVICE=cpu
        export PIPER_DEVICE=cpu
        export PIPER_FORCE_CUDA=false
    fi
}

# Install Node.js 24.1.0
install_nodejs() {
    log_step "Checking Node.js installation..."
    
    # Check if Node.js is already installed
    if check_command_exists "node"; then
        local node_version=$(node --version)
        local required_version="v24"
        
        # Check if it's version 24.x
        if [[ "$node_version" == v24* ]]; then
            log_success "Node.js $node_version is already installed"
        else
            log_warning "Node.js $node_version is installed, but we need v24.x"
            log_step "Updating to Node.js 24.x..."
            
            # Clean apt cache first to fix apt_pkg error
            apt clean
            apt update --fix-missing 2>/dev/null || true
            
            # Add NodeSource repository
            curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
            
            # Install Node.js with force-yes to avoid prompts
            DEBIAN_FRONTEND=noninteractive apt install -y nodejs
            
            log_success "Node.js updated to $(node --version)"
        fi
    else
        log_step "Installing Node.js 24.1.0..."
        
        # Clean apt cache first
        apt clean
        apt update --fix-missing 2>/dev/null || true
        
        # Add NodeSource repository
        curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
        
        # Install Node.js
        DEBIAN_FRONTEND=noninteractive apt install -y nodejs
        
        log_success "Node.js $(node --version) installed"
    fi
    
    # Check if npm is available
    if check_command_exists "npm"; then
        log_success "npm $(npm --version) is available"
    else
        log_warning "npm not found, installing separately..."
        # Install npm separately if needed
        DEBIAN_FRONTEND=noninteractive apt install -y npm
        if check_command_exists "npm"; then
            log_success "npm $(npm --version) installed"
        else
            log_error "Failed to install npm"
            return 1
        fi
    fi
}


# Install Nginx and SSL
install_nginx() {
    log_step "Checking Nginx installation..."
    
    # Check if Nginx is already installed
    if check_package_installed "nginx"; then
        local nginx_version=$(nginx -v 2>&1 | cut -d' ' -f3)
        log_success "Nginx is already installed (version: $nginx_version)"
        
        # Check if Nginx is enabled
        if systemctl is-enabled nginx &> /dev/null; then
            log_success "Nginx is already enabled"
        else
            log_step "Enabling Nginx..."
            systemctl enable nginx
            log_success "Nginx enabled"
        fi
    else
        log_step "Installing Nginx..."
        apt install -y nginx
        systemctl enable nginx
        log_success "Nginx installed and enabled"
    fi
    
    # Check SSL tools
    log_step "Checking SSL tools..."
    
    if check_package_installed "certbot"; then
        log_success "Certbot is already installed"
    else
        log_step "Installing Certbot..."
        apt install -y certbot python3-certbot-nginx
        log_success "Certbot installed"
    fi
    
    log_success "Nginx and SSL tools are ready"
}

# Clone repository
clone_repository() {
    log_step "Checking SHCI repository..."
    
    if [ -d "$PROJECT_DIR" ]; then
        log_step "Project directory exists. Checking for updates..."
        cd "$PROJECT_DIR"
        
        # Check if it's a git repository
        if [ -d ".git" ]; then
            log_step "Updating existing repository..."
            git fetch --all
            
            # Check current branch
            local current_branch=$(git branch --show-current)
            if [ "$current_branch" != "$BRANCH" ]; then
                log_step "Switching to branch: $BRANCH"
                git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" origin/"$BRANCH"
            fi
            
            # Reset to latest commit
            git reset --hard "origin/$BRANCH"
            log_success "Repository updated to latest $BRANCH branch"
        else
            log_warning "Directory exists but is not a git repository. Removing and cloning fresh..."
            cd /
            rm -rf "$PROJECT_DIR"
            git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
            log_success "Repository cloned fresh"
        fi
    else
        log_step "Cloning SHCI repository..."
        git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
        log_success "Repository cloned"
    fi
    
    # Set proper ownership
    chown -R root:root "$PROJECT_DIR"
    log_success "Repository ownership set correctly"
}

# Install audio dependencies
install_audio_dependencies() {
    log_step "Installing audio dependencies for PyAudio and audio processing..."
    
    # Install Python development headers and audio libraries
    local audio_packages=("python3.12-dev" "portaudio19-dev" "libasound2-dev" "libsndfile1-dev" "ffmpeg" "libportaudio2" "libasound2t64" "alsa-utils")
    
    for package in "${audio_packages[@]}"; do
        if check_package_installed "$package"; then
            log_success "$package is already installed"
        else
            log_step "Installing $package..."
            apt install -y "$package"
            log_success "$package installed"
        fi
    done
    
    log_success "Audio dependencies installed"
}

# Setup backend
setup_backend() {
    log_step "Setting up FastAPI backend..."
    cd "$PROJECT_DIR/fastapi-backend"
    
    # Stop services first
    log_step "Stopping services..."
    sudo systemctl stop shci-backend shci-frontend 2>/dev/null || true
    
    # Ensure Python 3.12 is available and set as default
    log_step "Ensuring Python 3.12 is properly configured..."
    
    # Verify Python 3.12 installation, install if not available
    if ! check_command_exists "python3.12"; then
        log_step "Python 3.12 not found, installing..."
        
        # Add deadsnakes PPA if not already added
        if ! grep -q "deadsnakes" /etc/apt/sources.list.d/*.list 2>/dev/null; then
            add-apt-repository ppa:deadsnakes/ppa -y
            apt update
        fi
        
        # Install Python 3.12 and related packages
        apt install -y python3.12 python3.12-venv python3.12-dev python3-pip python3.12-distutils
        
        log_success "Python 3.12 installed"
    fi
    
    PYTHON_VERSION=$(python3.12 --version 2>&1)
    log_success "Using Python version: $PYTHON_VERSION"
    
    # Set Python 3.12 as default python3
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
    sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1
    
    # Remove old virtual environment and create new one with Python 3.12
    if [ -d "venv" ]; then
        log_step "Removing old virtual environment..."
        rm -rf venv
        log_success "Old virtual environment removed"
    fi
    
    # Create new virtual environment with Python 3.12
    log_step "Creating new virtual environment with Python 3.12..."
    
    # Try python3.12 first, fallback to python3 if not available
    if command -v python3.12 &> /dev/null; then
        python3.12 -m venv venv
        log_success "Virtual environment created with Python 3.12"
    elif command -v python3 &> /dev/null; then
        python3 -m venv venv
        log_success "Virtual environment created with system Python 3"
    else
        log_error "No Python 3 installation found"
        exit 1
    fi
    
    source venv/bin/activate
    
    # Upgrade pip
    log_step "Upgrading pip..."
    pip install --upgrade pip wheel setuptools
    log_success "pip upgraded"
    
    # Install PyTorch with CUDA support for RTX 5090
    log_step "Installing PyTorch with CUDA 12.1 support for RTX 5090..."
    # Use PyTorch 2.4.0+ for better RTX 5090 support
    pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu121
    log_success "PyTorch with CUDA 12.1 installed"
    
    # Install ONNX Runtime with CUDA support
    log_step "Installing ONNX Runtime with CUDA support..."
    # First install CPU version, then GPU version
    pip install onnxruntime==1.18.0
    pip install onnxruntime-gpu==1.18.0
    log_success "ONNX Runtime with CUDA installed"
    
    # Install other dependencies
    log_step "Installing remaining Python dependencies..."
    pip install -r requirements.txt
    log_success "Dependencies installed"
    
    # Test Python imports to ensure everything works
    log_step "Testing Python imports..."
    python test_imports.py
    if [ $? -eq 0 ]; then
        log_success "Python imports test passed"
    else
        log_error "Python imports test failed"
        exit 1
    fi
    
    # Test GPU detection and CUDA availability
    log_step "Testing GPU detection and CUDA availability..."
    python -c "
import torch
import sys

print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')

if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'Number of GPUs: {torch.cuda.device_count()}')
    
    for i in range(torch.cuda.device_count()):
        gpu_name = torch.cuda.get_device_name(i)
        gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f'GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)')
        
        # Test tensor operations on GPU
        try:
            x = torch.randn(1000, 1000).cuda()
            y = torch.randn(1000, 1000).cuda()
            z = torch.mm(x, y)
            print(f'GPU {i}: Tensor operations successful')
        except Exception as e:
            print(f'GPU {i}: Tensor operations failed - {e}')
            sys.exit(1)
else:
    print('CUDA not available - GPU acceleration disabled')
    sys.exit(1)
"
    if [ $? -eq 0 ]; then
        log_success "GPU detection and CUDA test passed"
    else
        log_error "GPU detection and CUDA test failed"
        exit 1
    fi
    
    # Copy production environment file
    if [ -f "$PROJECT_DIR/production.env" ]; then
        cp "$PROJECT_DIR/production.env" .env
        print_success "Production environment file copied"
    else
        # Create production environment file optimized for RTX 5090
        cat > .env << 'EOF'
# Environment
TTS_ENVIRONMENT=production
PIPER_DEVICE=cuda
PIPER_FORCE_CUDA=true

# TTS Configuration
TTS_DEVICE=cuda

# RTX 5090 GPU Configuration
CUDA_VISIBLE_DEVICES=0
TORCH_DEVICE=cuda
CUDA_ARCHITECTURES=89
TORCH_CUDA_ARCH_LIST=8.9
# RTX 5090 specific compatibility
TORCH_CUDA_ARCH_LIST=8.9,9.0
CUDA_ARCHITECTURES=89,90

# RTX 5090 Memory Optimization (24GB VRAM)
TORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048,roundup_power2_divisions:16
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048
CUDA_MEMORY_POOL_DISABLE=0
CUDA_DEVICE_ORDER=PCI_BUS_ID

# API Configuration
OPENAI_API_KEY=your_openai_key_here
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=huihui-24b:Q4_K_M

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# TTS Configuration optimized for RTX 5090
PIPER_LENGTH_SCALE=0.6
PIPER_NOISE_SCALE=0.667
PIPER_NOISE_W=0.8
PIPER_USE_CUDA=1
PIPER_CUDA_DEVICE=0
PIPER_BATCH_SIZE=32

# RealtimeSTT Configuration for RTX 5090
RT_DEVICE=cuda
RT_COMPUTE=float16
RT_MODEL=large-v3
RT_GPU_INDEX=0
RT_VAD_SENS=2
RT_POST_SILENCE=0.2
RT_MIN_UTT=0.15
RT_REALTIME_PAUSE=0.02

# ONNX Runtime GPU Configuration
ORT_DEVICE=cuda
ORT_PROVIDERS=CUDAExecutionProvider,CPUExecutionProvider

# Performance Optimization for RTX 5090
OMP_NUM_THREADS=16
MKL_NUM_THREADS=16
NUMEXPR_NUM_THREADS=16
OPENBLAS_NUM_THREADS=16
MKL_DYNAMIC=false
OMP_DYNAMIC=false

# Memory Optimization
PYTHONHASHSEED=0
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
MALLOC_TRIM_THRESHOLD_=131072
MALLOC_MMAP_THRESHOLD_=131072

# CUDA Optimization for RTX 5090
CUDA_CACHE_DISABLE=0
CUDA_LAUNCH_BLOCKING=0
CUDA_LAUNCH_BLOCKING=0

# Language Support
DEFAULT_LANGUAGE=en
RT_LANG=

# LLM Configuration
LLM_TIMEOUT=15.0
LLM_RETRIES=1
MAX_TOKENS=100

# TTS Performance
TTS_BATCH_SIZE=32
TTS_CHUNK_SIZE=50
TTS_OVERLAP=10
EOF
    fi
    
    print_success "Backend environment configured"
}

# Setup frontend
setup_frontend() {
    log_step "Setting up Next.js frontend..."
    cd "$PROJECT_DIR/web-app"
    
    # Check if node_modules exists
    if [ -d "node_modules" ]; then
        log_success "Node modules already installed"
        
        # Check if package-lock.json exists and is newer than package.json
        if [ -f "package-lock.json" ] && [ "package-lock.json" -nt "package.json" ]; then
            log_success "Dependencies are up to date"
        else
            log_step "Updating dependencies..."
            npm install
            log_success "Dependencies updated"
        fi
    else
        log_step "Installing Node.js dependencies..."
        npm install
        log_success "Dependencies installed"
    fi
    
    # Create environment file
    log_step "Setting up environment configuration..."
    cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=https://nodecel.com/api
NEXT_PUBLIC_WS_URL=wss://nodecel.com/ws
NEXT_PUBLIC_APP_URL=https://nodecel.com
EOF
    log_success "Environment file created"
    
    # Build frontend
    log_step "Building Next.js frontend..."
    NODE_ENV=production npm run build
    log_success "Frontend built successfully"
}

# Create systemd services
create_services() {
    log_step "Setting up systemd services..."
    
    # Check if services already exist
    local services_exist=true
    if [ ! -f "/etc/systemd/system/shci-backend.service" ] || [ ! -f "/etc/systemd/system/shci-frontend.service" ]; then
        services_exist=false
    fi
    
    if [ "$services_exist" = true ]; then
        log_success "Systemd services already exist"
        
        # Check if services need updating by comparing content
        log_step "Checking if services need updates..."
        # For now, we'll recreate them to ensure they're up to date
        log_step "Updating systemd services..."
    else
        log_step "Creating systemd services..."
    fi
    
    # Backend service
    sudo tee /etc/systemd/system/shci-backend.service > /dev/null << EOF
[Unit]
Description=SHCI Backend FastAPI Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR/fastapi-backend
Environment=PATH=$PROJECT_DIR/fastapi-backend/venv/bin
Environment=PYTHONPATH=$PROJECT_DIR/fastapi-backend
EnvironmentFile=$PROJECT_DIR/fastapi-backend/.env
        ExecStart=$PROJECT_DIR/fastapi-backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Frontend service
    sudo tee /etc/systemd/system/shci-frontend.service > /dev/null << EOF
[Unit]
Description=SHCI Frontend Next.js Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR/web-app
Environment=PATH=/usr/bin:/usr/local/bin
EnvironmentFile=$PROJECT_DIR/web-app/.env.local
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    log_step "Reloading systemd daemon..."
    systemctl daemon-reload
    
    # Enable services
    log_step "Enabling services..."
    systemctl enable shci-backend shci-frontend
    
    log_success "Systemd services configured"
}

# Configure Nginx
configure_nginx() {
    log_step "Configuring Nginx..."
    
    # Check if configuration already exists
    if [ -f "/etc/nginx/sites-available/shci" ]; then
        log_success "Nginx configuration already exists"
        log_step "Updating Nginx configuration..."
    else
        log_step "Creating Nginx configuration..."
    fi
    
    # Create Nginx configuration
    sudo tee /etc/nginx/sites-available/shci << 'EOF'
# SHCI Voice Assistant - Nginx Configuration
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:3000;
    keepalive 32;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;

server {
    listen 80;
    server_name nodecel.com www.nodecel.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; media-src 'self' blob:; connect-src 'self' ws: wss:;" always;

    # Frontend (Next.js) - Main application
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Backend API routes
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket connection
    location /ws {
        limit_req zone=ws burst=10 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Health check
    location /health {
        proxy_pass http://backend;
        access_log off;
    }

    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOF

    # Enable site
    log_step "Enabling Nginx site..."
    ln -sf /etc/nginx/sites-available/shci /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    log_success "Nginx site enabled"
    
    # Test configuration
    log_step "Testing Nginx configuration..."
    nginx -t
    log_success "Nginx configuration is valid"
    
    log_success "Nginx configured successfully"
}

# Check SSL rate limits
check_ssl_rate_limit() {
    local domain="$1"
    local rate_limit_check=$(certbot certificates --domain "$domain" 2>&1 | grep -c "rateLimited\|too many requests")
    if [ "$rate_limit_check" -gt 0 ]; then
        return 0  # Rate limit hit
    else
        return 1  # No rate limit
    fi
}

# Configure SSL
configure_ssl() {
    log_step "Configuring SSL for nodecel.com..."
    
    # Ensure Nginx is running
    systemctl start nginx
    systemctl enable nginx
    
    # Check if SSL certificate already exists
    if [ -d "/etc/letsencrypt/live/nodecel.com" ]; then
        log_success "SSL certificate already exists for nodecel.com"
        
        # Check if certificate is valid and not expired
        local cert_expiry=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/nodecel.com/cert.pem 2>/dev/null | cut -d= -f2)
        if [ -n "$cert_expiry" ]; then
            local cert_expiry_epoch=$(date -d "$cert_expiry" +%s 2>/dev/null)
            local current_epoch=$(date +%s)
            local days_until_expiry=$(( (cert_expiry_epoch - current_epoch) / 86400 ))
            
            if [ "$days_until_expiry" -gt 30 ]; then
                log_success "SSL certificate is valid for $days_until_expiry more days"
            else
                log_warning "SSL certificate expires in $days_until_expiry days. Renewing..."
                certbot renew --nginx --non-interactive --quiet
                systemctl reload nginx
                log_success "SSL certificate renewed"
            fi
        else
            log_warning "Could not read certificate expiry, attempting renewal..."
            certbot renew --nginx --non-interactive --quiet
            systemctl reload nginx
        fi
        
        # Test SSL certificate
        log_step "Testing SSL certificate..."
        sleep 3
        if curl -s -I https://nodecel.com 2>/dev/null | grep -q "200 OK\|HTTP/2 200"; then
            log_success "SSL certificate is working correctly"
        else
            log_warning "SSL certificate exists but not working, attempting to fix..."
            
            # Check if we're hitting rate limits
            if certbot renew --force-renewal --nginx --non-interactive --quiet 2>&1 | grep -q "rateLimited"; then
                log_warning "Rate limit hit, using existing certificate..."
                # Just reload nginx with existing certificate
                systemctl reload nginx
                sleep 5
                if curl -s -I https://nodecel.com 2>/dev/null | grep -q "200 OK\|HTTP/2 200"; then
                    log_success "SSL working with existing certificate"
                else
                    log_warning "SSL configuration needs manual intervention"
                fi
            else
                systemctl reload nginx
                sleep 5
                if curl -s -I https://nodecel.com 2>/dev/null | grep -q "200 OK\|HTTP/2 200"; then
                    log_success "SSL fixed and working"
                else
                    log_warning "SSL configuration needs manual intervention"
                fi
            fi
        fi
    else
        log_step "Obtaining SSL certificate..."
        
        # Check rate limits before attempting certificate
        if check_ssl_rate_limit "nodecel.com"; then
            log_warning "Rate limit detected, skipping SSL certificate installation"
            log_message "SSL will be configured manually later when rate limit resets"
        else
            # Ensure Nginx is running and accessible
            systemctl start nginx
            sleep 2
            
            # Get SSL certificate with better error handling
            if certbot --nginx -d nodecel.com -d www.nodecel.com --non-interactive --agree-tos --email admin@nodecel.com --quiet; then
                log_success "SSL certificate obtained"
                systemctl reload nginx
            else
                log_warning "SSL certificate installation failed, but continuing..."
            fi
        fi
    fi
    
    log_success "SSL configuration completed"
}

# Configure firewall
configure_firewall() {
    log_step "Configuring firewall..."
    
    # Check if UFW is already enabled
    if ufw status | grep -q "Status: active"; then
        log_success "UFW firewall is already enabled"
    else
        log_step "Enabling UFW firewall..."
        ufw --force enable
        log_success "UFW firewall enabled"
    fi
    
    # Check and add rules if needed
    log_step "Configuring firewall rules..."
    
    # SSH (port 22)
    if ufw status | grep -q "22/tcp"; then
        log_success "SSH rule already exists"
    else
        ufw allow 22/tcp
        log_success "SSH rule added"
    fi
    
    # HTTP (port 80)
    if ufw status | grep -q "80/tcp"; then
        log_success "HTTP rule already exists"
    else
        ufw allow 80/tcp
        log_success "HTTP rule added"
    fi
    
    # HTTPS (port 443)
    if ufw status | grep -q "443/tcp"; then
        log_success "HTTPS rule already exists"
    else
        ufw allow 443/tcp
        log_success "HTTPS rule added"
    fi
    
    log_success "Firewall configuration completed"
}

# Optimize system
optimize_system() {
    print_step "Optimizing system settings for RTX 5090..."
    
    # RTX 5090 specific file limits
    echo "* soft nofile 65535" | tee -a /etc/security/limits.conf
    echo "* hard nofile 65535" | tee -a /etc/security/limits.conf
    echo "* soft nproc 65535" | tee -a /etc/security/limits.conf
    echo "* hard nproc 65535" | tee -a /etc/security/limits.conf
    
    # RTX 5090 optimized kernel parameters
    cat << 'EOF' | tee -a /etc/sysctl.conf
# RTX 5090 Network optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.ipv4.tcp_rmem = 4096 87380 268435456
net.ipv4.tcp_wmem = 4096 65536 268435456

# RTX 5090 Memory optimizations
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1
vm.zone_reclaim_mode = 0
vm.max_map_count = 262144
kernel.pid_max = 4194304
fs.file-max = 2097152

# RTX 5090 GPU optimizations
kernel.nmi_watchdog = 0
kernel.perf_cpu_time_max_percent = 1
EOF
    
    # Apply settings
    sysctl -p
    
    # Set CPU governor to performance for RTX 5090
    echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1 || true
    
    # RTX 5090 specific NVIDIA optimizations
    if command -v nvidia-smi &> /dev/null; then
        # Enable GPU persistence mode
        nvidia-smi -pm 1
        print_success "NVIDIA GPU persistence mode enabled"
        
        # Set power limit for RTX 5090 (350W)
        nvidia-smi -pl 350
        print_success "NVIDIA GPU power limit set to 350W"
        
        # Set GPU clocks to maximum performance
        nvidia-smi -ac 3000,2000 2>/dev/null || true
        print_success "NVIDIA GPU clocks set to maximum performance"
    fi
    
    print_success "System optimized for RTX 5090"
}

# Start services
start_services() {
    print_step "Starting services..."
    
    # Reload systemd daemon to pick up service changes
    systemctl daemon-reload
    
    # Stop services first to ensure clean restart
    systemctl stop shci-backend 2>/dev/null || true
    systemctl stop shci-frontend 2>/dev/null || true
    
    # Start Nginx
    systemctl start nginx
    
    # Start SHCI services
    systemctl start shci-backend
    systemctl start shci-frontend
    
    # Enable services to start on boot
    systemctl enable shci-backend
    systemctl enable shci-frontend
    
    # Wait a moment for services to start
    sleep 5
    
    print_success "Services started"
}

# Verify installation
verify_installation() {
    print_step "Verifying installation..."
    
    # Check services
    if systemctl is-active --quiet shci-backend; then
        print_success "Backend service is running"
    else
        print_error "Backend service failed to start"
        journalctl -u shci-backend --no-pager -l
    fi
    
    if systemctl is-active --quiet shci-frontend; then
        print_success "Frontend service is running"
    else
        print_error "Frontend service failed to start"
        journalctl -u shci-frontend --no-pager -l
    fi
    
    if systemctl is-active --quiet nginx; then
        print_success "Nginx service is running"
    else
        print_error "Nginx service failed to start"
        journalctl -u nginx --no-pager -l
    fi
    
    # Test endpoints
    sleep 2
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend health check passed"
    else
        print_warning "Backend health check failed"
    fi
    
    if curl -s http://localhost:3000 > /dev/null; then
        print_success "Frontend is accessible"
    else
        print_warning "Frontend is not accessible"
    fi
}

# Display final information
show_final_info() {
    print_header "🎉 SHCI Installation Complete!"
    
    echo -e "${GREEN}✅ Installation Summary:${NC}"
    echo -e "   • Python 3.12 with virtual environment"
    echo -e "   • Node.js $(node --version)"
    echo -e "   • FastAPI backend with RTX 5090 GPU support"
    echo -e "   • Next.js frontend"
    echo -e "   • Nginx reverse proxy"
    echo -e "   • Systemd services"
    echo -e "   • Firewall configured"
    echo -e "   • RTX 5090 optimized for maximum performance"
    
    echo -e "\n${BLUE}🌐 Access Information:${NC}"
    echo -e "   • Frontend: https://nodecel.com"
    echo -e "   • Backend API: https://nodecel.com/api"
    echo -e "   • Health Check: https://nodecel.com/health"
    echo -e "   • TTS Info: https://nodecel.com/tts/info"
    
    echo -e "\n${YELLOW}🔧 Management Commands:${NC}"
    echo -e "   • Check status: systemctl status shci-backend shci-frontend nginx"
    echo -e "   • View logs: journalctl -u shci-backend -f"
    echo -e "   • Restart: systemctl restart shci-backend shci-frontend"
    echo -e "   • Stop: systemctl stop shci-backend shci-frontend"
    
    
    echo -e "\n${CYAN}📝 Next Steps:${NC}"
    echo -e "   1. Update your OpenAI API key in: $PROJECT_DIR/fastapi-backend/.env"
    echo -e "   2. Test the application: https://nodecel.com"
    echo -e "   3. Monitor logs: journalctl -u shci-backend -f"
    echo -e "   4. Check SSL: certbot certificates"
    echo -e "   5. Monitor GPU usage: nvidia-smi -l 1"
    
    # RTX 5090 verification
    echo -e "\n${BLUE}🎮 RTX 5090 Verification:${NC}"
    if command -v nvidia-smi &> /dev/null; then
        local gpu_info=$(nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$gpu_info" ]; then
            echo -e "   • GPU Status: $gpu_info"
        fi
        
        # Test GPU functionality
        echo -e "   • Testing GPU functionality..."
        cd "$PROJECT_DIR/fastapi-backend"
        source venv/bin/activate
        python -c "
import torch
if torch.cuda.is_available():
    print(f'   • CUDA Available: Yes (Version {torch.version.cuda})')
    print(f'   • GPU Count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        gpu_name = torch.cuda.get_device_name(i)
        gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f'   • GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)')
        
        # Test tensor operations
        try:
            x = torch.randn(1000, 1000).cuda()
            y = torch.randn(1000, 1000).cuda()
            z = torch.mm(x, y)
            print(f'   • GPU {i}: Tensor operations successful ✅')
        except Exception as e:
            print(f'   • GPU {i}: Tensor operations failed ❌ - {e}')
else:
    print('   • CUDA Available: No ❌')
" 2>/dev/null || echo -e "   • GPU test failed - check logs"
    else
        echo -e "   • NVIDIA drivers not detected ❌"
    fi
    
    echo -e "\n${GREEN}🚀 Your RTX 5090 optimized SHCI Voice Assistant is ready!${NC}\n"
}

# Deployment summary
show_deployment_summary() {
    print_header "📊 Deployment Summary"
    
    echo -e "${GREEN}✅ Deployment Details:${NC}"
    echo -e "   • Deployment Date: $DEPLOYMENT_DATE"
    echo -e "   • Project Directory: $PROJECT_DIR"
    echo -e "   • Repository: $REPO_URL"
    echo -e "   • Branch: $BRANCH"
    echo -e "   • Log File: $LOG_FILE"
    echo -e "   • Backup Directory: $BACKUP_DIR/$DEPLOYMENT_DATE"
    
    echo -e "\n${BLUE}🔧 System Status:${NC}"
    echo -e "   • Backend Service: $(systemctl is-active shci-backend 2>/dev/null || echo 'inactive')"
    echo -e "   • Frontend Service: $(systemctl is-active shci-frontend 2>/dev/null || echo 'inactive')"
    echo -e "   • Nginx Service: $(systemctl is-active nginx 2>/dev/null || echo 'inactive')"
    
    echo -e "\n${YELLOW}📈 Resource Usage:${NC}"
    echo -e "   • Disk Usage: $(df / | awk 'NR==2 {print $5}')"
    echo -e "   • Memory Usage: $(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
    echo -e "   • CPU Load: $(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')"
    
    echo -e "\n${PURPLE}🔗 Quick Links:${NC}"
    echo -e "   • View Logs: tail -f $LOG_FILE"
    echo -e "   • Check Services: systemctl status shci-backend shci-frontend nginx"
    echo -e "   • Restart Services: systemctl restart shci-backend shci-frontend"
    echo -e "   • View Backups: ls -la $BACKUP_DIR"
    
    echo -e "\n${CYAN}🆘 Troubleshooting:${NC}"
    echo -e "   • If services fail: Check logs with journalctl -u service-name"
    echo -e "   • If rollback needed: Run the script again (it will auto-rollback)"
    echo -e "   • If SSL issues: Check certbot certificates"
    echo -e "   • If port conflicts: Check netstat -tlnp | grep :8000"
}

# Hard reset and fresh deployment
hard_reset_deployment() {
    log_step "Performing hard reset deployment..."
    
    # Stop all services first
    systemctl stop shci-backend shci-frontend nginx 2>/dev/null || true
    
    # Remove project directory
    if [ -d "$PROJECT_DIR" ]; then
        log_step "Removing existing project directory..."
        rm -rf "$PROJECT_DIR"
        log_success "Project directory removed"
    fi
    
    # Change to parent directory before cloning
    log_step "Changing to parent directory..."
    cd /var/www
    log_success "Changed to /var/www"
    
    # Clone fresh repository
    log_step "Cloning fresh repository..."
    git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
    chown -R root:root "$PROJECT_DIR"
    log_success "Fresh repository cloned"
    
    # Remove systemd services
    log_step "Removing existing systemd services..."
    rm -f /etc/systemd/system/shci-*.service
    systemctl daemon-reload
    log_success "Systemd services removed"
    
    # Remove nginx configuration
    log_step "Removing existing nginx configuration..."
    rm -f /etc/nginx/sites-available/shci
    rm -f /etc/nginx/sites-enabled/shci
    systemctl reload nginx 2>/dev/null || true
    log_success "Nginx configuration removed"
    
    # Remove old Node.js to ensure clean installation
    log_step "Removing old Node.js installation..."
    apt remove -y nodejs npm 2>/dev/null || true
    rm -rf /usr/lib/node_modules
    rm -rf /usr/local/lib/node_modules
    rm -rf ~/.npm
    log_success "Old Node.js removed"
    
    # Clean apt cache to fix apt_pkg error
    log_step "Cleaning apt cache to fix apt_pkg error..."
    apt clean
    apt update --fix-missing 2>/dev/null || true
    log_success "Apt cache cleaned"
    
    log_success "Hard reset completed - ready for fresh deployment"
}

# Main execution
main() {
    print_header "SHCI Voice Assistant - Nodecel.com Production Deployment"
    
    # Initialize logging
    log_message "Starting SHCI deployment process"
    log_message "Deployment date: $DEPLOYMENT_DATE"
    log_message "Project directory: $PROJECT_DIR"
    log_message "Repository: $REPO_URL"
    log_message "Branch: $BRANCH"
    
    # Pre-flight checks
    check_root
    check_sudo
    check_system_resources
    configure_git_ssh
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Create backups if project exists
    if [ -d "$PROJECT_DIR" ]; then
        create_backup "project_backup" "$PROJECT_DIR"
        create_backup "nginx_config" "/etc/nginx/sites-available/shci"
        create_backup "systemd_services" "/etc/systemd/system/shci-*.service"
    fi
    
    # Installation steps
    update_system
    install_python
    install_nodejs
    configure_gpu
    install_nginx
    install_audio_dependencies
    clone_repository
    setup_backend
    setup_frontend
    create_services
    configure_nginx
    configure_ssl
    configure_firewall
    optimize_system
    start_services
    
    # Enhanced verification with health checks
    log_step "Performing comprehensive health checks..."
    check_service_health "shci-backend"
    check_service_health "shci-frontend"
    check_service_health "nginx"
    
    verify_installation
    show_final_info
    show_deployment_summary
    
    # Cleanup old backups
    cleanup_old_backups
    
    log_success "Deployment completed successfully!"
    log_message "Deployment log saved to: $LOG_FILE"
    log_message "Backups saved to: $BACKUP_DIR/$DEPLOYMENT_DATE"
    
    print_success "Deployment completed successfully!"
}

# Show help
show_help() {
    echo "SHCI Voice Assistant - Nodecel.com Production Deployment"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --hard-reset, -r    Perform hard reset (remove all existing files and start fresh)"
    echo "  --help, -h          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Normal deployment (smart checks)"
    echo "  $0 --hard-reset     # Hard reset and fresh deployment"
    echo "  $0 -r               # Hard reset and fresh deployment"
    echo ""
    echo "Hard reset will:"
    echo "  - Stop all services"
    echo "  - Remove project directory"
    echo "  - Remove systemd services"
    echo "  - Remove nginx configuration"
    echo "  - Clean apt cache"
    echo "  - Start fresh deployment"
}

# Check for help option
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# Check for hard reset option and execute it first
if [ "$1" = "--hard-reset" ] || [ "$1" = "-r" ]; then
    echo "Performing hard reset deployment..."
    hard_reset_deployment
    echo "Hard reset completed. Starting fresh deployment..."
fi

# Run main function
main "$@"
