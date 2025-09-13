# 🚀 SHCI Deployment Guide

## Overview
This document provides comprehensive information about deploying the SHCI Voice Agent application.

## 🏗️ Architecture
- **Frontend**: Next.js React application
- **Backend**: FastAPI Python application
- **TTS**: XTTS v2 with multiple voice options
- **Deployment**: Automated via GitHub Actions

## 📋 Prerequisites
- Node.js 18+
- Python 3.11+
- Docker (optional)
- Server with SSH access

## 🔧 Environment Setup

### Frontend Environment Variables
```bash
# web-app/.env.local
NEXT_PUBLIC_API_URL=http://your-domain.com/api
NEXT_PUBLIC_WS_URL=ws://your-domain.com/ws
```

### Backend Environment Variables
```bash
# fastapi-backend/.env
TTS_MODEL_PATH=/path/to/xtts/model
SPEAKER_WAV_PATH=/path/to/speaker/wav
OPENAI_API_KEY=your_openai_key
```

## 🚀 Deployment Process

### Automated Deployment (GitHub Actions)
1. Push to `main` branch
2. GitHub Actions automatically:
   - Builds frontend
   - Installs backend dependencies
   - Runs tests
   - Deploys to server

### Manual Deployment
```bash
# 1. Build frontend
cd web-app
npm install
npm run build

# 2. Setup backend
cd ../fastapi-backend
pip install -r requirements.txt

# 3. Run deployment script
bash deploy.sh
```

## 🔐 Required Secrets
Configure these in GitHub repository settings:

- `SSH_HOST`: Your server IP/domain
- `SSH_USER`: SSH username
- `SSH_PRIVATE_KEY`: SSH private key

## 📱 Mobile Compatibility
- ✅ Android Chrome (speech-to-text optimized)
- ✅ iOS Safari
- ✅ Desktop browsers

## 🛠️ Troubleshooting

### Speech Recognition Issues
- Check microphone permissions
- Verify HTTPS connection
- Test on different browsers

### TTS Issues
- Verify model files exist
- Check speaker WAV files
- Monitor server resources

## 📊 Monitoring
- Check GitHub Actions logs
- Monitor server resources
- Test voice functionality regularly

## 🔄 Updates
- Push changes to `main` branch
- Monitor deployment status
- Test functionality after deployment

## 📞 Support
For issues or questions, please check:
1. GitHub Issues
2. Deployment logs
3. Server logs

---
**Last Updated**: $(date)
**Version**: 1.0.0
