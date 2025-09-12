#!/bin/bash

# SHCI Voice Assistant - Complete Deployment Script
# ================================================
# This script removes existing Python versions and installs only Python 3.11.9
# Then deploys the complete SHCI Voice Assistant application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="shci-app"
DOMAIN_NAME="nodecel.cloud"  # Your main domain
EMAIL="office.khairul@gmail.com"  # Your email

echo -e "${BLUE}🚀 Starting SHCI Complete Deployment${NC}"
echo "============================================="
echo -e "${YELLOW}⚠️  WARNING: This script will remove existing Python versions${NC}"
echo -e "${YELLOW}   and install only Python 3.11 (latest available)${NC}"
echo ""

# Function to print status
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

# SSH Safety Function
ensure_ssh_safety() {
    print_warning "🔒 Ensuring SSH port 22 is protected..."
    
    if [ "$EUID" -eq 0 ]; then
        # Allow SSH with multiple methods for redundancy
        ufw allow 22/tcp
        ufw allow ssh
        ufw allow out 22/tcp
        
        # Verify SSH is allowed
        if ufw status | grep -q "22/tcp.*ALLOW"; then
            print_status "✅ SSH port 22 is protected"
        else
            print_error "❌ SSH port not protected! Adding again..."
            ufw allow 22/tcp
            ufw allow ssh
        fi
    else
        # Allow SSH with multiple methods for redundancy
        sudo ufw allow 22/tcp
        sudo ufw allow ssh
        sudo ufw allow out 22/tcp
        
        # Verify SSH is allowed
        if sudo ufw status | grep -q "22/tcp.*ALLOW"; then
            print_status "✅ SSH port 22 is protected"
        else
            print_error "❌ SSH port not protected! Adding again..."
            sudo ufw allow 22/tcp
            sudo ufw allow ssh
        fi
    fi
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root user. This is supported but not recommended for security."
    print_warning "Consider using a regular user with sudo privileges for better security."
    read -p "Continue as root? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled. Please run as a regular user with sudo privileges."
        exit 1
    fi
    USER_HOME="/root"
else
    USER_HOME="$HOME"
fi

# Fix apt_pkg issue first
print_status "Checking and fixing apt_pkg module issue..."
if [ "$EUID" -eq 0 ]; then
    # Disable command-not-found to prevent apt_pkg errors
    echo 'APT::Update::Post-Invoke-Success {"true";};' > /etc/apt/apt.conf.d/99disable-command-not-found
    # Install python3-apt to fix apt_pkg module
    apt update 2>/dev/null || true
    apt install -y python3-apt software-properties-common 2>/dev/null || true
    # Fix command-not-found database issue
    rm -f /var/lib/command-not-found/commands.db 2>/dev/null || true
    # Remove problematic cnf-update-db script
    rm -f /usr/lib/cnf-update-db 2>/dev/null || true
else
    # Disable command-not-found to prevent apt_pkg errors
    echo 'APT::Update::Post-Invoke-Success {"true";};' | sudo tee /etc/apt/apt.conf.d/99disable-command-not-found
    sudo apt update 2>/dev/null || true
    sudo apt install -y python3-apt software-properties-common 2>/dev/null || true
    # Fix command-not-found database issue
    sudo rm -f /var/lib/command-not-found/commands.db 2>/dev/null || true
    # Remove problematic cnf-update-db script
    sudo rm -f /usr/lib/cnf-update-db 2>/dev/null || true
fi

# Update system packages
print_status "Updating system packages..."
if [ "$EUID" -eq 0 ]; then
    apt update 2>/dev/null || true
    apt upgrade -y 2>/dev/null || true
else
    sudo apt update 2>/dev/null || true
    sudo apt upgrade -y 2>/dev/null || true
fi

# Install required packages
print_status "Installing required packages..."
if [ "$EUID" -eq 0 ]; then
    apt install -y curl wget git nginx certbot python3-certbot-nginx ufw 2>/dev/null || true
else
    sudo apt install -y curl wget git nginx certbot python3-certbot-nginx ufw 2>/dev/null || true
fi

# Install pyenv and Python 3.11.9
print_status "Installing pyenv and Python 3.11.9..."
if [ "$EUID" -eq 0 ]; then
    # Install dependencies for pyenv
    apt update 2>/dev/null || true
    apt install -y make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
        libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git 2>/dev/null || true
    
    # Install pyenv
    curl https://pyenv.run | bash 2>/dev/null || true
    
    # Add pyenv to PATH
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> /root/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> /root/.bashrc
    echo 'eval "$(pyenv init -)"' >> /root/.bashrc
    
    # Source bashrc
    source /root/.bashrc 2>/dev/null || true
    
    # Install Python 3.11.9
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
    
    pyenv install 3.11.9 2>/dev/null || true
    pyenv global 3.11.9 2>/dev/null || true
    
    # Create symlinks
    ln -sf /root/.pyenv/versions/3.11.9/bin/python /usr/local/bin/python
    ln -sf /root/.pyenv/versions/3.11.9/bin/python3 /usr/local/bin/python3
    ln -sf /root/.pyenv/versions/3.11.9/bin/python3.11 /usr/local/bin/python3.11
    ln -sf /root/.pyenv/versions/3.11.9/bin/pip /usr/local/bin/pip
    ln -sf /root/.pyenv/versions/3.11.9/bin/pip3 /usr/local/bin/pip3
else
    # Install dependencies for pyenv
    sudo apt update 2>/dev/null || true
    sudo apt install -y make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
        libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git 2>/dev/null || true
    
    # Install pyenv
    curl https://pyenv.run | bash 2>/dev/null || true
    
    # Add pyenv to PATH
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc
    
    # Source bashrc
    source ~/.bashrc 2>/dev/null || true
    
    # Install Python 3.11.9
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
    
    pyenv install 3.11.9 2>/dev/null || true
    pyenv global 3.11.9 2>/dev/null || true
    
    # Create symlinks
    sudo ln -sf $HOME/.pyenv/versions/3.11.9/bin/python /usr/local/bin/python
    sudo ln -sf $HOME/.pyenv/versions/3.11.9/bin/python3 /usr/local/bin/python3
    sudo ln -sf $HOME/.pyenv/versions/3.11.9/bin/python3.11 /usr/local/bin/python3.11
    sudo ln -sf $HOME/.pyenv/versions/3.11.9/bin/pip /usr/local/bin/pip
    sudo ln -sf $HOME/.pyenv/versions/3.11.9/bin/pip3 /usr/local/bin/pip3
fi

# Verify Python installation
print_status "Verifying Python 3.11.9 installation..."
python --version
python3 --version
python3.11 --version
pip --version

# Install Node.js and npm
print_status "Installing Node.js and npm..."
if ! command -v node &> /dev/null; then
    if [ "$EUID" -eq 0 ]; then
        apt install -y nodejs npm 2>/dev/null || true
    else
        sudo apt install -y nodejs npm 2>/dev/null || true
    fi
fi

# Python 3.11.9 is now installed via pyenv above
print_status "Python 3.11.9 installed via pyenv - skipping system Python installation"
# Skip system Python installation - using pyenv Python 3.11.9

# pip is already installed with pyenv Python 3.11.9
print_status "pip is already installed with pyenv Python 3.11.9"

# Check for Ollama service
print_status "Checking for Ollama LLM service..."
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_status "Ollama service detected and running!"
    print_status "LLM will use external Ollama service"
else
    print_warning "Ollama service not detected on localhost:11434"
    print_warning "Please ensure Ollama is running for LLM functionality"
fi

# Check for GPU and install NVIDIA Docker support
print_status "Checking for GPU support..."
if lspci | grep -i nvidia &> /dev/null; then
    print_status "NVIDIA GPU detected! Installing NVIDIA Docker support..."
    
    # Install NVIDIA drivers for Ubuntu 24.04 with CUDA 12.6
    if [ "$EUID" -eq 0 ]; then
        apt update 2>/dev/null || true
        
        # Try to install available NVIDIA drivers
        if apt install -y nvidia-driver-550 nvidia-dkms-550 2>/dev/null; then
            print_success "NVIDIA driver 550 installed successfully"
        elif apt install -y nvidia-driver-545 nvidia-dkms-545 2>/dev/null; then
            print_success "NVIDIA driver 545 installed successfully"
        elif apt install -y nvidia-driver-535 nvidia-dkms-535 2>/dev/null; then
            print_success "NVIDIA driver 535 installed successfully"
        else
            print_warning "Specific NVIDIA drivers not found, using ubuntu-drivers"
            apt install -y ubuntu-drivers-common
            ubuntu-drivers autoinstall
        fi
        
        # Install NVIDIA Container Toolkit
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
        
        apt update 2>/dev/null || true
        apt install -y nvidia-container-toolkit 2>/dev/null || true
        systemctl restart docker 2>/dev/null || true
    else
        sudo apt update 2>/dev/null || true
        
        # Try to install available NVIDIA drivers
        if sudo apt install -y nvidia-driver-550 nvidia-dkms-550 2>/dev/null; then
            print_success "NVIDIA driver 550 installed successfully"
        elif sudo apt install -y nvidia-driver-545 nvidia-dkms-545 2>/dev/null; then
            print_success "NVIDIA driver 545 installed successfully"
        elif sudo apt install -y nvidia-driver-535 nvidia-dkms-535 2>/dev/null; then
            print_success "NVIDIA driver 535 installed successfully"
        else
            print_warning "Specific NVIDIA drivers not found, using ubuntu-drivers"
            sudo apt install -y ubuntu-drivers-common
            sudo ubuntu-drivers autoinstall
        fi
        
        # Install NVIDIA Container Toolkit
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt update
        sudo apt install -y nvidia-container-toolkit
        sudo systemctl restart docker
    fi
    
    print_status "NVIDIA Docker support installed successfully!"
    print_warning "GPU will be used for TTS/STT processing in production"
    
    # Set GPU Dockerfile
    export BACKEND_DOCKERFILE="Dockerfile"
    print_status "Using GPU-enabled Dockerfile"
else
    print_warning "No NVIDIA GPU detected. Will use CPU for processing."
    
    # Set CPU Dockerfile
    export BACKEND_DOCKERFILE="Dockerfile.cpu"
    print_status "Using CPU-only Dockerfile"
fi

# Configure firewall
print_status "Configuring firewall..."

# Ensure SSH safety first
ensure_ssh_safety

if [ "$EUID" -eq 0 ]; then
    # Allow web ports
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Enable firewall
    ufw --force enable
    
    # Final SSH verification
    ensure_ssh_safety
else
    # Allow web ports
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Enable firewall
    sudo ufw --force enable
    
    # Final SSH verification
    ensure_ssh_safety
fi

# Show firewall status
print_status "Firewall status:"
if [ "$EUID" -eq 0 ]; then
    ufw status numbered
else
    sudo ufw status numbered
fi

# Create project directory
print_status "Setting up project directory..."
if [ "$EUID" -eq 0 ]; then
    mkdir -p /opt/$PROJECT_NAME
    chown root:root /opt/$PROJECT_NAME
else
    sudo mkdir -p /opt/$PROJECT_NAME
    sudo chown $USER:$USER /opt/$PROJECT_NAME
fi

# Clone or update repository
if [ -d "/opt/$PROJECT_NAME/.git" ]; then
    print_status "Updating existing repository..."
    cd /opt/$PROJECT_NAME
    git pull origin main
else
    print_status "Cloning repository..."
    
    # Check if repository is private and needs authentication
    if curl -s -o /dev/null -w "%{http_code}" https://github.com/arafatkhairul/shci-app | grep -q "404"; then
        print_warning "Repository appears to be private. Please choose authentication method:"
        echo "1. Personal Access Token"
        echo "2. SSH Key"
        echo "3. GitHub CLI"
        echo ""
        read -p "Enter your choice (1-3): " auth_choice
        
        case $auth_choice in
            1)
                read -p "Enter your GitHub Personal Access Token: " github_token
                git clone https://$github_token@github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
                ;;
            2)
                print_status "Using SSH authentication..."
                git clone git@github.com:arafatkhairul/shci-app.git /opt/$PROJECT_NAME
                ;;
            3)
                print_status "Using GitHub CLI..."
                if ! command -v gh &> /dev/null; then
                    print_status "Installing GitHub CLI..."
                    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
                    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
                    sudo apt update
                    sudo apt install gh
                fi
                gh auth login
                gh repo clone arafatkhairul/shci-app /opt/$PROJECT_NAME
                ;;
            *)
                print_error "Invalid choice. Please run the script again."
                exit 1
                ;;
        esac
    else
        print_status "Repository is public, cloning normally..."
        git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
    fi
    
    cd /opt/$PROJECT_NAME
fi

# Create production environment file
print_status "Creating production environment configuration..."
if [ -f "env.production" ]; then
    print_status "Using existing env.production file..."
    cp env.production .env.production
else
    print_status "Creating new .env.production file..."
    cat > .env.production << EOF
# Production Environment Configuration
NEXT_PUBLIC_API_BASE_URL=https://$DOMAIN_NAME
NEXT_PUBLIC_WS_BASE_URL=wss://$DOMAIN_NAME
NEXT_PUBLIC_WS_PRODUCTION_URL=wss://$DOMAIN_NAME
NEXT_PUBLIC_DEV_MODE=false
NEXT_PUBLIC_APP_NAME=SHCI Voice Assistant
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENABLE_ROLEPLAY=true
NEXT_PUBLIC_ENABLE_TTS=true
NEXT_PUBLIC_ENABLE_STT=true

# Backend Environment Variables
ENVIRONMENT=production
PYTHONPATH=/app

# LLM Configuration (External Ollama)
LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu
LLM_API_KEY=
LLM_TIMEOUT=10.0
LLM_RETRIES=1

# GPU Configuration for Production
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
WHISPER_DEVICE=cuda

# Model Configuration
TTS_MODEL_PATH=/app/Models
TTS_OUTPUT_PATH=/app/outputs
TTS_CACHE_PATH=/app/memdb
TTS_BATCH_SIZE=4
TTS_MAX_LENGTH=500

# Database Configuration
DATABASE_URL=sqlite:///./roleplay.db

# Security Configuration
CORS_ORIGINS=["https://$DOMAIN_NAME", "https://www.$DOMAIN_NAME"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Performance Configuration
WORKERS=4
MAX_CONNECTIONS=1000

# SSL Configuration
SSL_VERIFY=true
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
EOF
fi

# Update Nginx configuration with domain
print_status "Updating Nginx configuration..."
if [ -f "/opt/$PROJECT_NAME/nginx/conf.d/shci.conf" ]; then
    sed -i "s/your-domain.com/$DOMAIN_NAME/g" /opt/$PROJECT_NAME/nginx/conf.d/shci.conf
elif [ -f "/etc/nginx/sites-available/shci" ]; then
    sed -i "s/your-domain.com/$DOMAIN_NAME/g" /etc/nginx/sites-available/shci
else
    print_status "Creating nginx configuration..."
    # Create nginx configuration directory
    mkdir -p /opt/$PROJECT_NAME/nginx/conf.d
    
    # Create nginx configuration file
    cat > /opt/$PROJECT_NAME/nginx/conf.d/shci.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
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
    
    # Backend API
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # WebSocket
    location /ws {
        limit_req zone=ws burst=10 nodelay;
        proxy_pass http://localhost:8000;
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
    
    # Roleplay endpoints
    location /roleplay/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8000;
        access_log off;
    }
}
EOF
    
    # Update domain in the created file
    sed -i "s/your-domain.com/$DOMAIN_NAME/g" /opt/$PROJECT_NAME/nginx/conf.d/shci.conf
    
    # Copy to nginx sites-available
    cp /opt/$PROJECT_NAME/nginx/conf.d/shci.conf /etc/nginx/sites-available/shci
    ln -sf /etc/nginx/sites-available/shci /etc/nginx/sites-enabled/shci
fi

# Create SSL directory
sudo mkdir -p /opt/$PROJECT_NAME/ssl

# Setup backend environment
print_status "Setting up backend environment..."
cd /opt/$PROJECT_NAME/fastapi-backend

# ========================================
# VIRTUAL ENVIRONMENT SETUP
# ========================================
print_status "Setting up organized virtual environment..."

# Remove existing virtual environment if exists
if [ -d "venv" ]; then
    print_status "Removing existing 'venv' directory..."
    rm -rf venv
fi

if [ -d "shci_env" ]; then
    print_status "Removing existing 'shci_env' directory..."
    rm -rf shci_env
fi

# Create virtual environment with organized naming
print_status "Creating virtual environment 'shci_env'..."
python3.11 -m venv shci_env

# Activate virtual environment
print_status "Activating virtual environment..."
source shci_env/bin/activate

# Verify virtual environment activation
print_status "Verifying virtual environment activation..."
which python
which pip
python --version
pip --version

# Show virtual environment info
print_status "Virtual environment details:"
echo "• Virtual Environment: shci_env"
echo "• Python Path: $(which python)"
echo "• Pip Path: $(which pip)"
echo "• Python Version: $(python --version)"
echo "• Pip Version: $(pip --version)"
echo "• Virtual Environment Location: $(pwd)/shci_env"

# Install Python dependencies
pip install --upgrade pip

# Create constraints file to enforce numpy version
print_status "Creating pip constraints file to enforce numpy version..."
cat > /tmp/constraints.txt << 'EOF'
numpy>=1.24.0,<2.0.0
EOF

# Install dependencies with complete conflict resolution
print_status "Installing Python dependencies with complete conflict resolution..."
pip install --upgrade pip setuptools wheel

# Clean install approach - remove conflicting packages first
print_status "Cleaning up conflicting packages..."
pip uninstall -y numpy networkx thinc torch torchvision torchaudio 2>/dev/null || true

# Install core dependencies first
print_status "Installing core dependencies..."
pip install fastapi uvicorn python-dotenv requests -c /tmp/constraints.txt

# Install compatible numpy version first
print_status "Installing compatible numpy version..."
pip uninstall -y numpy 2>/dev/null || true
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall --no-deps

# Verify numpy version immediately
print_status "Verifying numpy version after installation..."
python3.11 -c "
import numpy
version = numpy.__version__
major, minor = map(int, version.split('.')[:2])
if major >= 2:
    print(f'ERROR: numpy {version} is incompatible!')
    exit(1)
else:
    print(f'SUCCESS: numpy {version} is compatible')
"

# Install compatible networkx version
print_status "Installing compatible networkx version..."
pip install "networkx>=2.5.0,<3.0.0" --force-reinstall

# Install audio processing dependencies
print_status "Installing audio processing dependencies..."
pip install soundfile librosa pydub scipy -c /tmp/constraints.txt

# Install TTS dependencies step by step with compatible versions
print_status "Installing TTS dependencies..."
pip install aiohttp anyascii bangla bnnumerizer -c /tmp/constraints.txt

# Install numba with compatible numpy version
print_status "Installing numba with compatible numpy..."
pip uninstall -y numba 2>/dev/null || true
pip install "numba>=0.57.0,<0.62.0" --force-reinstall

# Skip bnunicodenormalizer - Bengali text processing not needed
print_status "Skipping bnunicodenormalizer - Bengali text processing not required"

# Install packages that might conflict with numpy using --no-deps
print_status "Installing TTS packages with numpy protection..."
pip install coqpit cython einops encodec flask g2pkk --no-deps
pip install "gruut[de,es,fr]==2.2.3" --no-deps
pip install hangul-romanize inflect jamo jieba --no-deps
pip install matplotlib nltk num2words packaging --no-deps
pip install "pandas<2.0,>=1.4" pypinyin pysbd pyyaml --no-deps
pip install scikit-learn "spacy[ja]>=3" tqdm trainer transformers --no-deps
pip install umap-learn unidecode --no-deps

# Install their dependencies separately with constraints
print_status "Installing TTS package dependencies with numpy constraints..."
pip install coqpit cython einops encodec flask g2pkk -c /tmp/constraints.txt --force-reinstall
pip install "gruut[de,es,fr]==2.2.3" -c /tmp/constraints.txt --force-reinstall
pip install hangul-romanize inflect jamo jieba -c /tmp/constraints.txt --force-reinstall
pip install matplotlib nltk num2words packaging -c /tmp/constraints.txt --force-reinstall
pip install "pandas<2.0,>=1.4" pypinyin pysbd pyyaml -c /tmp/constraints.txt --force-reinstall
pip install scikit-learn "spacy[ja]>=3" tqdm trainer transformers -c /tmp/constraints.txt --force-reinstall
pip install umap-learn unidecode -c /tmp/constraints.txt --force-reinstall

# Install compatible thinc version
print_status "Installing compatible thinc version..."
pip install "thinc>=8.3.0,<8.4.0" --force-reinstall

# Check numpy version after TTS dependencies
print_status "Checking numpy version after TTS dependencies installation..."
python3.11 -c "
import numpy
version = numpy.__version__
major, minor = map(int, version.split('.')[:2])
if major >= 2:
    print(f'ERROR: numpy {version} is incompatible after TTS dependencies!')
    print('Reinstalling compatible numpy...')
    exit(1)
else:
    print(f'SUCCESS: numpy {version} is still compatible')
" || {
    print_error "Numpy version conflict detected! Fixing..."
    pip uninstall -y numpy 2>/dev/null || true
    pip install "numpy>=1.24.0,<2.0.0" --force-reinstall --no-deps
    print_status "Numpy version fixed, continuing..."
}

# Skip bnunicodenormalizer before TTS installation
print_status "Skipping bnunicodenormalizer before TTS - Bengali processing not needed"

# Install TTS package with dependency resolution
print_status "Installing TTS package..."
pip install TTS==0.21.3 --no-deps || pip install TTS==0.21.3 --force-reinstall --no-deps

# Install TTS without bnunicodenormalizer (Bengali processing not needed)
print_status "Installing TTS without bnunicodenormalizer - Bengali processing not required"
pip install TTS==0.21.3 --no-deps --force-reinstall

# Final dependency check and fix
print_status "Final dependency check and fix..."
pip install --upgrade pip
pip install --no-deps -r requirements.txt || true

# Install PyTorch with CUDA support if GPU available
if lspci | grep -i nvidia &> /dev/null; then
    print_status "Installing PyTorch with CUDA support..."
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
    pip install torchvision==0.22.1+cu118 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
    pip install torchaudio --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
else
    print_status "Installing PyTorch CPU version..."
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
    pip install torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
    pip install torchaudio --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
fi

# Fix all dependency conflicts after PyTorch installation
print_status "Fixing all dependency conflicts after PyTorch installation..."
pip uninstall -y numpy 2>/dev/null || true
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall --no-deps
pip install "networkx>=2.5.0,<3.0.0" --force-reinstall
pip install "typing_extensions>=4.14.0" --force-reinstall
pip install "thinc>=8.3.0,<8.4.0" --force-reinstall

# Fix PyTorch version conflicts
print_status "Fixing PyTorch version conflicts..."
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
if lspci | grep -i nvidia &> /dev/null; then
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
    pip install torchvision==0.22.1+cu118 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
else
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
    pip install torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
fi

# Reinstall all TTS dependencies to ensure compatibility
print_status "Reinstalling TTS dependencies for compatibility..."
pip install --force-reinstall aiohttp anyascii bangla bnnumerizer coqpit cython einops encodec flask g2pkk
pip install --force-reinstall "gruut[de,es,fr]==2.2.3" hangul-romanize inflect jamo jieba
pip install --force-reinstall matplotlib nltk num2words numba packaging
pip install --force-reinstall "pandas<2.0,>=1.4" pypinyin pysbd pyyaml
pip install --force-reinstall scikit-learn "spacy[ja]>=3" tqdm trainer transformers
pip install --force-reinstall umap-learn unidecode

# Install remaining dependencies
print_status "Installing remaining dependencies..."
pip install webrtcvad_wheels websocket_client pyttsx3

# Final dependency verification and conflict resolution
print_status "Final dependency verification and conflict resolution..."
pip install --upgrade pip
pip uninstall -y numpy 2>/dev/null || true
pip install --force-reinstall "numpy>=1.24.0,<2.0.0" --no-deps
pip install --force-reinstall "networkx>=2.5.0,<3.0.0"
pip install --force-reinstall "typing_extensions>=4.14.0"
pip install --force-reinstall "thinc>=8.3.0,<8.4.0"

# Final PyTorch compatibility fix
print_status "Final PyTorch compatibility fix..."
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
if lspci | grep -i nvidia &> /dev/null; then
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
    pip install torchvision==0.22.1+cu118 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
else
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
    pip install torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
fi

# Skip final bnunicodenormalizer installation attempt
print_status "Skipping final bnunicodenormalizer installation - Bengali processing not needed"

# Force install TTS dependencies (without bnunicodenormalizer)
print_status "Force installing TTS with all dependencies (excluding bnunicodenormalizer)..."
pip install TTS==0.21.3 --force-reinstall --no-deps

# Comprehensive final fix for all conflicts
print_status "Comprehensive final fix for all conflicts..."
pip uninstall -y torch torchvision torchaudio numpy networkx 2>/dev/null || true

# Install exact compatible versions
pip uninstall -y numpy 2>/dev/null || true
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall --no-deps
pip install "networkx>=2.5.0,<3.0.0" --force-reinstall

# Install PyTorch with exact versions
if lspci | grep -i nvidia &> /dev/null; then
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
    pip install torchvision==0.22.1+cu118 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --no-deps
else
    pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
    pip install torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
fi

# Skip final bnunicodenormalizer attempt - Bengali processing not needed
print_status "Skipping final bnunicodenormalizer attempt - Bengali text processing not required"

# Verify critical packages
print_status "Verifying critical package versions..."
python3.11 -c "
import numpy; print(f'numpy: {numpy.__version__}')
import networkx; print(f'networkx: {networkx.__version__}')
import typing_extensions; print(f'typing_extensions: {typing_extensions.__version__}')
try:
    import numba; print(f'numba: {numba.__version__}')
except ImportError:
    print('numba: not installed')
try:
    import torch; print(f'torch: {torch.__version__}')
except ImportError:
    print('torch: not installed')
try:
    import torchvision; print(f'torchvision: {torchvision.__version__}')
except ImportError:
    print('torchvision: not installed')
try:
    import thinc; print(f'thinc: {thinc.__version__}')
except ImportError:
    print('thinc: not installed')
try:
    import TTS; print(f'TTS: {TTS.__version__}')
except ImportError:
    print('TTS: not installed')
# bnunicodenormalizer skipped - Bengali processing not needed
print('bnunicodenormalizer: skipped (Bengali processing not required)')
"

# Final numpy compatibility check
print_status "Final numpy compatibility check..."
python3.11 -c "
import numpy
version = numpy.__version__
major, minor = map(int, version.split('.')[:2])
if major >= 2:
    print(f'ERROR: numpy {version} is incompatible with numba and gruut')
    print('Expected: numpy < 2.0.0')
    exit(1)
else:
    print(f'SUCCESS: numpy {version} is compatible')
"

# Setup frontend environment
print_status "Setting up frontend environment..."
cd /opt/$PROJECT_NAME/web-app

# Install Node.js dependencies
npm install

# Build frontend for production
npm run build

# Create systemd services
print_status "Creating systemd services..."

# Backend service
if [ "$EUID" -eq 0 ]; then
    tee /etc/systemd/system/shci-backend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Backend
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/$PROJECT_NAME/fastapi-backend
Environment=PATH=/opt/$PROJECT_NAME/fastapi-backend/shci_env/bin
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/opt/$PROJECT_NAME/fastapi-backend/shci_env/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
else
    sudo tee /etc/systemd/system/shci-backend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Backend
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/$PROJECT_NAME/fastapi-backend
Environment=PATH=/opt/$PROJECT_NAME/fastapi-backend/shci_env/bin
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/opt/$PROJECT_NAME/fastapi-backend/shci_env/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

# Frontend service
if [ "$EUID" -eq 0 ]; then
    tee /etc/systemd/system/shci-frontend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Frontend
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/$PROJECT_NAME/web-app
Environment=NODE_ENV=production
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
else
    sudo tee /etc/systemd/system/shci-frontend.service > /dev/null << EOF
[Unit]
Description=SHCI Voice Assistant Frontend
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/$PROJECT_NAME/web-app
Environment=NODE_ENV=production
EnvironmentFile=/opt/$PROJECT_NAME/.env.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

# Enable and start services
print_status "Enabling and starting services..."
if [ "$EUID" -eq 0 ]; then
    systemctl daemon-reload
    systemctl enable shci-backend.service
    systemctl enable shci-frontend.service
    systemctl start shci-backend.service
    systemctl start shci-frontend.service
else
    sudo systemctl daemon-reload
    sudo systemctl enable shci-backend.service
    sudo systemctl enable shci-frontend.service
    sudo systemctl start shci-backend.service
    sudo systemctl start shci-frontend.service
fi

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Check if services are running
if systemctl is-active --quiet shci-backend.service && systemctl is-active --quiet shci-frontend.service; then
    print_status "Services are running successfully!"
else
    print_error "Some services failed to start. Check logs with: journalctl -u shci-backend.service -f"
    exit 1
fi

# Setup SSL certificate (optional)
read -p "Do you want to setup SSL certificate with Let's Encrypt? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Setting up SSL certificate..."
    
    # Fix cffi backend issue
    print_status "Fixing cffi backend issue..."
    if [ "$EUID" -eq 0 ]; then
        apt update 2>/dev/null || true
        apt install -y python3-cffi python3-cryptography python3-openssl 2>/dev/null || true
        pip3 install --upgrade cffi cryptography pyopenssl 2>/dev/null || true
    else
        sudo apt update 2>/dev/null || true
        sudo apt install -y python3-cffi python3-cryptography python3-openssl 2>/dev/null || true
        sudo pip3 install --upgrade cffi cryptography pyopenssl 2>/dev/null || true
    fi
    
    # Stop nginx temporarily
    if [ "$EUID" -eq 0 ]; then
        systemctl stop nginx
    else
        sudo systemctl stop nginx
    fi
    
    # Install certificate with error handling
    print_status "Installing SSL certificate..."
    if [ "$EUID" -eq 0 ]; then
        certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive 2>/dev/null || {
            print_error "SSL certificate installation failed. Continuing without SSL..."
            print_status "You can manually setup SSL later using: certbot --nginx -d $DOMAIN_NAME"
        }
    else
        sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive 2>/dev/null || {
            print_error "SSL certificate installation failed. Continuing without SSL..."
            print_status "You can manually setup SSL later using: sudo certbot --nginx -d $DOMAIN_NAME"
        }
    fi
    
    # Update nginx configuration for SSL (if SSL was successful)
    if [ -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
        print_status "Updating nginx configuration for SSL..."
        if [ -f "/etc/nginx/sites-available/shci" ]; then
            # SSL configuration will be automatically added by certbot
            print_status "SSL configuration updated by certbot"
        else
            print_status "Creating SSL-enabled nginx configuration..."
            cat > /etc/nginx/sites-available/shci << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL configuration (will be updated by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
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
    
    # Backend API
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # WebSocket
    location /ws {
        limit_req zone=ws burst=10 nodelay;
        proxy_pass http://localhost:8000;
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
    
    # Roleplay endpoints
    location /roleplay/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8000;
        access_log off;
    }
}
EOF
            sed -i "s/your-domain.com/$DOMAIN_NAME/g" /etc/nginx/sites-available/shci
            ln -sf /etc/nginx/sites-available/shci /etc/nginx/sites-enabled/shci
        fi
    else
        print_status "SSL certificate not found, keeping HTTP configuration"
    fi
    
    # Restart nginx
    print_status "Restarting nginx..."
    if [ "$EUID" -eq 0 ]; then
        systemctl start nginx 2>/dev/null || true
        systemctl reload nginx 2>/dev/null || true
    else
        sudo systemctl start nginx 2>/dev/null || true
        sudo systemctl reload nginx 2>/dev/null || true
    fi
else
    print_status "Skipping SSL setup. You can setup SSL later manually."
fi

# Setup auto-renewal for SSL (only if SSL was successfully installed)
if [ -f "/etc/cron.d/certbot" ]; then
    print_status "SSL auto-renewal already configured"
elif [ -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
    print_status "Setting up SSL auto-renewal..."
    if [ "$EUID" -eq 0 ]; then
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | tee /etc/cron.d/certbot 2>/dev/null || true
    else
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo tee /etc/cron.d/certbot 2>/dev/null || true
    fi
else
    print_status "SSL not installed, skipping auto-renewal setup"
fi

# Services are already created and enabled above
print_status "Systemd services already created and enabled"

# Final status check
print_status "Deployment completed successfully!"
echo "================================================"
echo -e "${GREEN}🎉 SHCI Voice Assistant is now deployed!${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo "• Domain: https://$DOMAIN_NAME"
echo "• Frontend: Next.js (Port 3000)"
echo "• Backend: FastAPI (Port 8000)"
echo "• Proxy: Nginx (Port 80/443)"
echo "• SSL: Let's Encrypt (if configured)"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "• View logs: journalctl -u shci-backend.service -f"
echo "• View logs: journalctl -u shci-frontend.service -f"
echo "• Restart backend: systemctl restart shci-backend.service"
echo "• Restart frontend: systemctl restart shci-frontend.service"
echo "• Stop services: systemctl stop shci-backend.service shci-frontend.service"
echo "• Start services: systemctl start shci-backend.service shci-frontend.service"
echo "• Update: git pull && systemctl restart shci-backend.service shci-frontend.service"
echo ""
echo -e "${BLUE}🐍 Virtual Environment Commands:${NC}"
echo "• Activate venv: cd /opt/$PROJECT_NAME/fastapi-backend && source shci_env/bin/activate"
echo "• Deactivate venv: deactivate"
echo "• Install packages: pip install package_name"
echo "• Update packages: pip install --upgrade package_name"
echo "• List packages: pip list"
echo "• Check venv: which python && which pip"
echo ""
echo -e "${BLUE}📁 Project Location:${NC}"
echo "/opt/$PROJECT_NAME"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "• Change DOMAIN_NAME and EMAIL in this script before running"
echo "• Make sure your domain points to this server's IP"
echo "• Check firewall settings if services are not accessible"
echo "• Monitor logs regularly for any issues"
echo ""
print_status "Deployment script completed!"
