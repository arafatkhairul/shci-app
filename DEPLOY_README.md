# SHCI Voice Assistant - Single Deployment Script

## Overview

This project now uses a single deployment script (`deploy.sh`) that handles everything automatically.

## ⚠️ Important Warning

**This script will remove existing Python versions and install only Python 3.11.9**

## Quick Deployment

### 1. Clone Repository
```bash
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
```

### 2. Run Deployment Script
```bash
chmod +x deploy.sh
./deploy.sh
```

## What the Script Does

### 🔧 System Setup
- Fixes `apt_pkg` module issues
- Updates system packages
- Installs required dependencies (Node.js, Nginx, etc.)

### 🐍 Python Management
- **Removes existing Python versions** (python3, python3.12, etc.)
- **Installs only Python 3.11.9** specifically
- Creates symlinks: `python` → `python3.11`
- Installs pip for Python 3.11.9

### 🚀 Application Deployment
- Sets up backend (FastAPI) with Python 3.11.9
- Sets up frontend (Next.js) 
- Creates systemd services for auto-start
- Configures Nginx reverse proxy
- Sets up SSL certificates with Let's Encrypt

### 🔒 Security & Networking
- Configures UFW firewall
- Protects SSH port 22
- Sets up SSL/TLS encryption

## Prerequisites

- Ubuntu 24.04.3 LTS server
- Root access or sudo privileges
- Domain name pointing to server (`nodecel.cloud`)
- Minimum 4GB RAM, 20GB storage

## After Deployment

### Access URLs
- **Frontend**: https://nodecel.cloud
- **Backend API**: https://nodecel.cloud/api/
- **WebSocket**: wss://nodecel.cloud/ws
- **Health Check**: https://nodecel.cloud/health

### Service Management
```bash
# Check status
sudo systemctl status shci-backend.service
sudo systemctl status shci-frontend.service

# View logs
sudo journalctl -u shci-backend.service -f
sudo journalctl -u shci-frontend.service -f

# Restart services
sudo systemctl restart shci-backend.service shci-frontend.service
```

### Update Application
```bash
cd /opt/shci-app
git pull origin main
sudo systemctl restart shci-backend.service shci-frontend.service
```

## Troubleshooting

If you encounter issues:

1. **Check logs**: `sudo journalctl -u shci-backend.service -f`
2. **Verify Python**: `python --version` (should show 3.11.9)
3. **Check services**: `sudo systemctl status shci-backend.service`
4. **Test connectivity**: `curl https://nodecel.cloud/health`

## Files Removed

The following extra deployment files have been removed to simplify the process:
- `deploy-direct.sh` ❌
- `quick-deploy.sh` ❌  
- `install-python-3.11.9.sh` ❌

**Only `deploy.sh` remains** ✅

## Support

For detailed troubleshooting, see `TROUBLESHOOTING.md`

---

**Note**: This is a production-ready deployment that runs all services directly on the host system without Docker.
