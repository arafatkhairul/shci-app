# 🎯 Which Script Should You Run?

## 🚀 **Quick Decision**

### **Use `./quick-setup.sh` if:**
- ✅ **First time** setting up
- ✅ **Testing** the application  
- ✅ **Development** environment
- ✅ **Quick** deployment needed
- ✅ **Learning** the system

### **Use `./deploy.sh` if:**
- ✅ **Production** deployment
- ✅ **Private repository** access
- ✅ **SSL certificates** needed
- ✅ **Security** requirements
- ✅ **Complete** automation

---

## 📋 **What Each Script Does**

### **quick-setup.sh (5-10 minutes)**
```
1. Check Ollama service
2. Check GPU availability  
3. Install Docker (if needed)
4. Install Docker Compose (if needed)
5. Run deployment script
6. Verify services
```

### **deploy.sh (15-30 minutes)**
```
1. Update system packages
2. Install Docker & Docker Compose
3. Check Ollama service
4. Install NVIDIA drivers & Docker GPU support
5. Configure firewall
6. Clone repository (with private repo support)
7. Create production environment
8. Update Nginx configuration
9. Build and start services
10. Setup SSL certificates
11. Configure auto-start service
12. Setup SSL auto-renewal
```

---

## 🎯 **Simple Decision Tree**

```
Are you deploying to production server?
├── YES → Use ./deploy.sh
│   ├── Private repository? → deploy.sh handles it
│   ├── Need SSL certificates? → deploy.sh sets up Let's Encrypt
│   ├── Need security? → deploy.sh configures firewall
│   └── Need auto-start? → deploy.sh creates systemd service
│
└── NO → Use ./quick-setup.sh
    ├── Testing/development? → quick-setup.sh is perfect
    ├── First time setup? → quick-setup.sh is user-friendly
    └── Quick deployment? → quick-setup.sh is fast
```

---

## 🚀 **Commands**

### **For Quick Setup:**
```bash
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
./quick-setup.sh
```

### **For Production Deployment:**
```bash
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
./deploy.sh
```

---

## 📊 **Results After Each Script**

### **After quick-setup.sh:**
- ✅ Services running locally
- ✅ Access: http://localhost:3000
- ✅ API: http://localhost:8000
- ✅ Basic management commands

### **After deploy.sh:**
- ✅ Services running on production
- ✅ Access: https://nodecel.cloud (SSL)
- ✅ API: https://nodecel.cloud/api/ (SSL)
- ✅ Auto-start on boot
- ✅ SSL certificates
- ✅ Firewall configured
- ✅ Complete monitoring

---

## 🎯 **Recommendation**

**For most users:**
1. **Start with** `./quick-setup.sh` (test locally)
2. **Then use** `./deploy.sh` (deploy to production)

**This gives you the best of both worlds!** 🚀
