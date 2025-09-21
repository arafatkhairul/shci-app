#!/bin/bash
# ===================================================================
# SHCI Voice Assistant - Nodecel.com Production Deployment
# ===================================================================
# Complete deployment script for nodecel.com with NVIDIA RTX 5090 GPU
# Project Directory: /var/www/shci-app
# Domain: nodecel.com
# User: root
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
REPO_URL="https://github.com/arafatkhairul/shci-app.git"
BRANCH="tts-medium-variants"
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

# Update system packages
update_system() {
    print_step "Updating system packages..."
    
    # Remove problematic NVIDIA repositories
    rm -f /etc/apt/sources.list.d/nvidia-*
    rm -f /etc/apt/sources.list.d/libnvidia-container-*
    rm -f /etc/apt/sources.list.d/nvidia-container-runtime-*
    rm -f /etc/apt/sources.list.d/nvidia-docker-*
    
    # Clean apt cache
    apt clean
    apt update && apt upgrade -y
    apt install -y curl wget git build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release
    print_success "System packages updated"
}

# Install Python 3.11
install_python() {
    print_step "Installing Python 3.11..."
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.11 python3.11-venv python3.11-dev python3-pip python3.11-distutils
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
    print_success "Python 3.11 installed"
}

# Install Node.js 24.1.0
install_nodejs() {
    print_step "Installing Node.js 24.1.0..."
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
    apt install -y nodejs
    print_success "Node.js $(node --version) installed"
}

# Skip NVIDIA - already installed
skip_nvidia() {
    print_step "Skipping NVIDIA installation - already installed on server"
    print_success "NVIDIA drivers and CUDA already available"
}

# Install Nginx and SSL
install_nginx() {
    print_step "Installing Nginx and SSL tools..."
    apt install -y nginx certbot python3-certbot-nginx
    systemctl enable nginx
    print_success "Nginx and SSL tools installed"
}

# Clone repository
clone_repository() {
    print_step "Cloning SHCI repository..."
    
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Project directory exists. Updating..."
        cd "$PROJECT_DIR"
        git fetch --all
        git reset --hard origin/$BRANCH
    else
        git clone -b $BRANCH $REPO_URL $PROJECT_DIR
    fi
    
    # Set proper ownership
    chown -R root:root $PROJECT_DIR
    print_success "Repository cloned/updated"
}

# Setup backend
setup_backend() {
    print_step "Setting up FastAPI backend..."
    cd "$PROJECT_DIR/fastapi-backend"
    
    # Create virtual environment
    python3.11 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip wheel setuptools
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Copy production environment file
    if [ -f "$PROJECT_DIR/production.env" ]; then
        cp "$PROJECT_DIR/production.env" .env
        print_success "Production environment file copied"
    else
        # Create production environment file
        cat > .env << 'EOF'
# Environment
TTS_ENVIRONMENT=production
PIPER_DEVICE=cuda
PIPER_FORCE_CUDA=true

# GPU Configuration
CUDA_VISIBLE_DEVICES=0
TORCH_DEVICE=cuda
TTS_DEVICE=cuda

# API Configuration
OPENAI_API_KEY=your_openai_key_here
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# TTS Configuration
PIPER_LENGTH_SCALE=0.6
PIPER_NOISE_SCALE=0.667
PIPER_NOISE_W=0.8

# Performance Optimization
OMP_NUM_THREADS=8
MKL_NUM_THREADS=8
NUMEXPR_NUM_THREADS=8
OPENBLAS_NUM_THREADS=8
MKL_DYNAMIC=false
OMP_DYNAMIC=false

# Memory Optimization
PYTHONHASHSEED=0
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
MALLOC_TRIM_THRESHOLD_=131072
MALLOC_MMAP_THRESHOLD_=131072

# CUDA Optimization
TORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
CUDA_CACHE_DISABLE=0
CUDA_LAUNCH_BLOCKING=0
EOF
    fi
    
    print_success "Backend environment configured"
}

# Setup frontend
setup_frontend() {
    print_step "Setting up Next.js frontend..."
    cd "$PROJECT_DIR/web-app"
    
    # Install dependencies
    npm install
    
    # Create environment file
    cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=https://nodecel.com/api
NEXT_PUBLIC_WS_URL=wss://nodecel.com/ws
NEXT_PUBLIC_APP_URL=https://nodecel.com
EOF
    
    # Build frontend
    npm run build
    
    print_success "Frontend built successfully"
}

# Create systemd services
create_services() {
    print_step "Creating systemd services..."
    
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
EnvironmentFile=$PROJECT_DIR/fastapi-backend/.env
ExecStart=$PROJECT_DIR/fastapi-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
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
    systemctl daemon-reload
    systemctl enable shci-backend shci-frontend
    
    print_success "Systemd services created"
}

# Configure Nginx
configure_nginx() {
    print_step "Configuring Nginx..."
    
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
    ln -sf /etc/nginx/sites-available/shci /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    nginx -t
    
    print_success "Nginx configured"
}

# Configure SSL
configure_ssl() {
    print_step "Configuring SSL for nodecel.com..."
    
    # Start Nginx first
    systemctl start nginx
    
    # Get SSL certificate
    certbot --nginx -d nodecel.com -d www.nodecel.com --non-interactive --agree-tos --email admin@nodecel.com
    
    print_success "SSL configured for nodecel.com"
}

# Configure firewall
configure_firewall() {
    print_step "Configuring firewall..."
    ufw --force enable
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    print_success "Firewall configured"
}

# Optimize system
optimize_system() {
    print_step "Optimizing system settings..."
    
    # Increase file limits
    echo "* soft nofile 65536" | tee -a /etc/security/limits.conf
    echo "* hard nofile 65536" | tee -a /etc/security/limits.conf
    
    # Optimize kernel parameters
    cat << 'EOF' | tee -a /etc/sysctl.conf
# Network optimizations
net.core.somaxconn = 65536
net.ipv4.tcp_max_syn_backlog = 65536
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# Memory optimizations
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF
    
    # Apply settings
    sysctl -p
    
    print_success "System optimized"
}

# Start services
start_services() {
    print_step "Starting services..."
    
    # Start Nginx
    systemctl start nginx
    
    # Start SHCI services
    systemctl start shci-backend
    systemctl start shci-frontend
    
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
    echo -e "   • Python 3.11 with virtual environment"
    echo -e "   • Node.js $(node --version)"
    echo -e "   • FastAPI backend with GPU support"
    echo -e "   • Next.js frontend"
    echo -e "   • Nginx reverse proxy"
    echo -e "   • Systemd services"
    echo -e "   • Firewall configured"
    
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
    
    echo -e "\n${PURPLE}📊 GPU Information:${NC}"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
    else
        echo -e "   GPU drivers not installed or not detected"
    fi
    
    echo -e "\n${CYAN}📝 Next Steps:${NC}"
    echo -e "   1. Update your OpenAI API key in: $PROJECT_DIR/fastapi-backend/.env"
    echo -e "   2. Test the application: https://nodecel.com"
    echo -e "   3. Monitor logs: journalctl -u shci-backend -f"
    echo -e "   4. Check SSL: certbot certificates"
    
    echo -e "\n${GREEN}🚀 Your SHCI Voice Assistant is ready!${NC}\n"
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
    skip_nvidia
    install_nginx
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
    
    print_success "Deployment completed! No reboot needed since NVIDIA was already installed."
}

# Run main function
main "$@"
