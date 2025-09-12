# 🚀 SHCI - সহজ Deployment Guide (nodecel.cloud)

## 📋 আপনার জন্য সহজ উত্তর

**❌ আলাদা domain লাগবে না!**  
**✅ একই domain (`nodecel.cloud`) দিয়ে সব কিছু চলবে!**

## 🏗️ কিভাবে কাজ করবে

```
https://nodecel.cloud → Nginx → Docker Containers
                              ├── Frontend (Next.js)
                              ├── Backend (FastAPI) 
                              └── Database
```

### 🔄 URL Structure:
- **Frontend**: `https://nodecel.cloud/` (মূল ওয়েবসাইট)
- **API**: `https://nodecel.cloud/api/` (Backend API)
- **WebSocket**: `wss://nodecel.cloud/ws` (Real-time communication)

## 🚀 Deployment Steps

### 1. VPS এ Repository Clone করুন
```bash
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
```

### 2. Email ঠিক করুন
```bash
nano deploy.sh
# EMAIL="your-actual-email@example.com" লিখুন
```

### 3. Deployment চালান
```bash
./deploy.sh
```

## ✅ কি হবে?

1. **Docker containers** build হবে
2. **Nginx** reverse proxy setup হবে  
3. **SSL certificate** install হবে
4. **Firewall** configure হবে
5. **Auto-start** service setup হবে

## 🌐 Access URLs

Deployment এর পর:
- **Main App**: https://nodecel.cloud
- **API Health**: https://nodecel.cloud/health
- **WebSocket**: wss://nodecel.cloud/ws

## 🔧 Management Commands

```bash
# Services দেখুন
docker-compose ps

# Logs দেখুন  
docker-compose logs -f

# Restart করুন
docker-compose restart

# Update করুন
git pull && docker-compose up -d --build
```

## ❓ FAQ

**Q: Backend এর জন্য আলাদা domain লাগবে?**  
**A: না! সব কিছু `nodecel.cloud` দিয়ে চলবে।**

**Q: Docker containers কিভাবে communicate করে?**  
**A: Internal network দিয়ে, local URLs ব্যবহার করে।**

**Q: SSL certificate কিভাবে কাজ করবে?**  
**A: Let's Encrypt automatically install করবে।**

**Q: যদি কোনো সমস্যা হয়?**  
**A: `docker-compose logs -f` দিয়ে logs দেখুন।**

## 🎯 Summary

- ✅ **এক domain**: `nodecel.cloud`
- ✅ **Auto SSL**: Let's Encrypt
- ✅ **Docker**: সব services containerized
- ✅ **Nginx**: Reverse proxy
- ✅ **Auto-start**: Server restart হলে auto start

**সব কিছু ready! শুধু `./deploy.sh` চালান!** 🚀
