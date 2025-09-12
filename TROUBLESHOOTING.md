# SHCI Voice Assistant - Troubleshooting Guide

## Common Issues and Solutions

### 1. apt_pkg ModuleNotFoundError

**Problem**: `ModuleNotFoundError: No module named 'apt_pkg'`

**Symptoms**:
- `add-apt-repository` commands fail
- Package management scripts fail
- Python scripts that interact with APT fail

**Solution**:

#### Quick Fix:
```bash
# Run the fix script
sudo ./fix-apt-pkg.sh
```

#### Manual Fix:
```bash
# Install python3-apt
sudo apt update
sudo apt install -y python3-apt software-properties-common

# Verify fix
python3 -c "import apt_pkg; print('apt_pkg working!')"
```

#### Alternative Method:
```bash
# If above doesn't work, try:
sudo apt --fix-broken install
sudo apt autoremove
sudo apt autoclean
sudo apt update
sudo apt install -y python3-apt
```

### 2. Python 3.11 Installation Issues

**Problem**: Cannot install Python 3.11.9 on Ubuntu 24.04

**Solution**:

#### Method 1: Using deadsnakes PPA
```bash
# Fix apt_pkg first
sudo apt install -y python3-apt software-properties-common

# Add deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils

# Create symlinks
sudo ln -sf /usr/bin/python3.11 /usr/bin/python
sudo ln -sf /usr/bin/python3.11 /usr/bin/python3

# Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
```

#### Method 2: Manual Installation
```bash
# Download and compile Python 3.11.9
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xzf Python-3.11.9.tgz
cd Python-3.11.9

# Configure and install
./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall

# Create symlinks
sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python
```

### 3. NVIDIA Driver Installation Issues

**Problem**: NVIDIA drivers fail to install

**Solution**:

#### Check GPU Detection:
```bash
# Check if NVIDIA GPU is detected
lspci | grep -i nvidia

# Check current driver status
nvidia-smi
```

#### Install Drivers:
```bash
# Method 1: Specific version
sudo apt update
sudo apt install -y nvidia-driver-550 nvidia-dkms-550

# Method 2: Auto-install
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Method 3: Manual selection
ubuntu-drivers devices
sudo apt install -y nvidia-driver-XXX  # Replace XXX with recommended version
```

#### After Installation:
```bash
# Reboot system
sudo reboot

# Verify installation
nvidia-smi
```

### 4. Service Startup Issues

**Problem**: Backend or frontend services fail to start

**Solution**:

#### Check Service Status:
```bash
# Check backend status
sudo systemctl status shci-backend.service

# Check frontend status
sudo systemctl status shci-frontend.service

# Check logs
sudo journalctl -u shci-backend.service -f
sudo journalctl -u shci-frontend.service -f
```

#### Common Fixes:
```bash
# Restart services
sudo systemctl restart shci-backend.service
sudo systemctl restart shci-frontend.service

# Reload systemd
sudo systemctl daemon-reload

# Check file permissions
sudo chown -R $USER:$USER /opt/shci-app

# Check environment file
sudo cat /opt/shci-app/.env.production
```

### 5. Port Conflicts

**Problem**: Ports 3000 or 8000 already in use

**Solution**:

#### Check Port Usage:
```bash
# Check what's using the ports
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :8000

# Alternative command
sudo lsof -i :3000
sudo lsof -i :8000
```

#### Kill Conflicting Processes:
```bash
# Kill process using port 3000
sudo kill -9 $(sudo lsof -t -i:3000)

# Kill process using port 8000
sudo kill -9 $(sudo lsof -t -i:8000)
```

#### Change Ports (if needed):
```bash
# Edit backend service
sudo systemctl edit shci-backend.service

# Add override:
[Service]
Environment="PORT=8001"

# Edit frontend service
sudo systemctl edit shci-frontend.service

# Add override:
[Service]
Environment="PORT=3001"
```

### 6. SSL Certificate Issues

**Problem**: Let's Encrypt SSL certificate fails

**Solution**:

#### Check Domain Configuration:
```bash
# Verify domain points to server
nslookup nodecel.cloud
ping nodecel.cloud
```

#### Manual SSL Setup:
```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Get certificate
sudo certbot certonly --standalone -d nodecel.cloud -d www.nodecel.cloud

# Update nginx config
sudo nano /etc/nginx/sites-available/shci-app

# Add SSL configuration:
server {
    listen 443 ssl;
    server_name nodecel.cloud www.nodecel.cloud;
    
    ssl_certificate /etc/letsencrypt/live/nodecel.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nodecel.cloud/privkey.pem;
    
    # ... rest of configuration
}

# Test and reload nginx
sudo nginx -t
sudo systemctl start nginx
```

### 7. Firewall Issues

**Problem**: Cannot access services after firewall setup

**Solution**:

#### Check Firewall Status:
```bash
# Check UFW status
sudo ufw status verbose

# Check iptables
sudo iptables -L
```

#### Fix Firewall Rules:
```bash
# Reset UFW
sudo ufw --force reset

# Allow necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8000/tcp   # Backend
sudo ufw allow 3000/tcp    # Frontend

# Enable firewall
sudo ufw --force enable
```

### 8. Ollama Integration Issues

**Problem**: Backend cannot connect to Ollama LLM service

**Solution**:

#### Check Ollama Status:
```bash
# Check if Ollama is running
curl -s http://localhost:11434/api/tags

# Check Ollama service
sudo systemctl status ollama
```

#### Fix Ollama Connection:
```bash
# Start Ollama service
sudo systemctl start ollama

# Check environment variables
grep LLM_API_URL /opt/shci-app/.env.production

# Test connection from backend container
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-14b-gpu", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 9. Memory Issues

**Problem**: Services crash due to memory issues

**Solution**:

#### Check Memory Usage:
```bash
# Check system memory
free -h
htop

# Check service memory usage
sudo systemctl status shci-backend.service
sudo systemctl status shci-frontend.service
```

#### Optimize Memory:
```bash
# Reduce backend workers
sudo systemctl edit shci-backend.service

# Add override:
[Service]
Environment="WORKERS=2"

# Restart service
sudo systemctl restart shci-backend.service
```

### 10. Database Issues

**Problem**: SQLite database errors

**Solution**:

#### Check Database:
```bash
# Check database file
ls -la /opt/shci-app/fastapi-backend/roleplay.db

# Check permissions
sudo chown $USER:$USER /opt/shci-app/fastapi-backend/roleplay.db

# Backup and recreate if corrupted
cp /opt/shci-app/fastapi-backend/roleplay.db /opt/shci-app/fastapi-backend/roleplay.db.backup
rm /opt/shci-app/fastapi-backend/roleplay.db
```

## Diagnostic Commands

### System Information:
```bash
# OS version
lsb_release -a

# Kernel version
uname -r

# Python version
python3 --version

# Node version
node --version
npm --version

# GPU information
nvidia-smi
lspci | grep -i nvidia
```

### Service Diagnostics:
```bash
# All service status
sudo systemctl status shci-backend.service shci-frontend.service nginx

# Service logs
sudo journalctl -u shci-backend.service --since "1 hour ago"
sudo journalctl -u shci-frontend.service --since "1 hour ago"

# Network connectivity
curl -I https://nodecel.cloud
curl -I https://nodecel.cloud/api/
curl -I https://nodecel.cloud/health
```

### Performance Monitoring:
```bash
# System resources
htop
iotop
nvidia-smi -l 1

# Disk usage
df -h
du -sh /opt/shci-app/*

# Network connections
ss -tulpn | grep :3000
ss -tulpn | grep :8000
```

## Emergency Recovery

### Complete Reset:
```bash
# Stop all services
sudo systemctl stop shci-backend.service shci-frontend.service nginx

# Backup current setup
sudo tar -czf shci-backup-$(date +%Y%m%d).tar.gz /opt/shci-app /etc/systemd/system/shci-*.service /etc/nginx/sites-available/shci-app

# Remove services
sudo systemctl disable shci-backend.service shci-frontend.service
sudo rm /etc/systemd/system/shci-backend.service /etc/systemd/system/shci-frontend.service

# Remove nginx config
sudo rm /etc/nginx/sites-available/shci-app /etc/nginx/sites-enabled/shci-app

# Clean up
sudo systemctl daemon-reload
sudo systemctl start nginx
```

### Restore from Backup:
```bash
# Restore application
sudo tar -xzf shci-backup-YYYYMMDD.tar.gz -C /

# Restore services
sudo systemctl daemon-reload
sudo systemctl enable shci-backend.service shci-frontend.service
sudo systemctl start shci-backend.service shci-frontend.service
```

## Getting Help

### Log Collection:
```bash
# Collect all relevant logs
sudo journalctl -u shci-backend.service > backend.log
sudo journalctl -u shci-frontend.service > frontend.log
sudo journalctl -u nginx > nginx.log
sudo nginx -t > nginx-test.log
systemctl status shci-backend.service shci-frontend.service nginx > services-status.log
```

### System Information:
```bash
# Collect system info
uname -a > system-info.log
lsb_release -a >> system-info.log
python3 --version >> system-info.log
node --version >> system-info.log
npm --version >> system-info.log
nvidia-smi >> system-info.log 2>&1 || echo "No NVIDIA GPU" >> system-info.log
```

---

**Note**: Always backup your configuration before making changes, and test fixes in a non-production environment when possible.
