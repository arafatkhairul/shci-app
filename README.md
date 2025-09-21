# 🚀 SHCI Voice Assistant - Nodecel.com Production Deployment

## 📋 Quick Deploy

### One Command Deployment
```bash
curl -fsSL https://raw.githubusercontent.com/arafatkhairul/shci-app/tts-medium-variants/deploy-nodecel.sh | bash
```

### Manual Deployment
```bash
# Clone repository
cd /var/www
git clone -b tts-medium-variants https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Run deployment
chmod +x deploy-nodecel.sh
./deploy-nodecel.sh
```

## ✨ What's Included

- ✅ **Domain**: nodecel.com (with SSL)
- ✅ **GPU**: NVIDIA RTX 5090 acceleration
- ✅ **Node.js**: v24.1.0
- ✅ **Python**: 3.11 with virtual environment
- ✅ **Backend**: FastAPI with TTS
- ✅ **Frontend**: Next.js
- ✅ **Proxy**: Nginx with SSL
- ✅ **Services**: Systemd auto-restart

## 🌐 Access URLs

- **Frontend**: https://nodecel.com
- **Backend API**: https://nodecel.com/api
- **Health Check**: https://nodecel.com/health
- **TTS Info**: https://nodecel.com/tts/info

## 🔧 Management

```bash
# Check status
systemctl status shci-backend shci-frontend nginx

# View logs
journalctl -u shci-backend -f

# Restart services
systemctl restart shci-backend shci-frontend

# Check GPU
nvidia-smi

# Check SSL
certbot certificates
```

## 📝 Configuration

- **Project Directory**: `/var/www/shci-app`
- **Environment File**: `/var/www/shci-app/fastapi-backend/.env`
- **Nginx Config**: `/etc/nginx/sites-available/shci`

## 🎯 Requirements

- Ubuntu 20.04+ server
- NVIDIA RTX 5090 GPU
- Root access
- Domain: nodecel.com (DNS pointing to server)

---

**Ready to deploy!** 🚀
