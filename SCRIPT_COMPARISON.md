# 🔧 Script Comparison: quick-setup.sh vs deploy.sh

## 📋 **quick-setup.sh** - Quick & Simple

### **কি করে:**
- ✅ **Basic checks**: Ollama, GPU, Docker
- ✅ **Simple setup**: Minimal configuration
- ✅ **User-friendly**: Interactive prompts
- ✅ **Fast**: Quick deployment

### **কখন ব্যবহার করবেন:**
- 🚀 **First time setup**
- 🔧 **Development/testing**
- ⚡ **Quick deployment**
- 👤 **Beginners**

### **Command:**
```bash
./quick-setup.sh
```

### **Process:**
1. Check Ollama service
2. Check GPU availability
3. Install Docker (if needed)
4. Install Docker Compose (if needed)
5. Run deployment script
6. Verify services

---

## 🚀 **deploy.sh** - Complete & Production

### **কি করে:**
- ✅ **Full setup**: Complete production environment
- ✅ **GPU support**: NVIDIA drivers + Docker GPU
- ✅ **Security**: Firewall, SSL certificates
- ✅ **Production**: Auto-start, monitoring
- ✅ **Private repo**: Authentication support

### **কখন ব্যবহার করবেন:**
- 🏭 **Production deployment**
- 🔐 **Private repository**
- 🛡️ **Security requirements**
- 🔄 **Complete automation**

### **Command:**
```bash
./deploy.sh
```

### **Process:**
1. Update system packages
2. Install Docker & Docker Compose
3. Check Ollama service
4. Install NVIDIA drivers & Docker GPU support
5. Configure firewall
6. Clone/update repository (with private repo support)
7. Create production environment
8. Update Nginx configuration
9. Build and start services
10. Setup SSL certificates
11. Configure auto-start service
12. Setup SSL auto-renewal

---

## 📊 **Detailed Comparison**

| Feature | quick-setup.sh | deploy.sh |
|---------|----------------|-----------|
| **Purpose** | Quick setup | Production deployment |
| **Time** | 5-10 minutes | 15-30 minutes |
| **Complexity** | Simple | Complete |
| **GPU Support** | Basic check | Full installation |
| **SSL Certificates** | No | Yes (Let's Encrypt) |
| **Firewall** | No | Yes (UFW) |
| **Auto-start** | No | Yes (systemd) |
| **Private Repo** | No | Yes (3 methods) |
| **Security** | Basic | Production-grade |
| **Monitoring** | Basic | Complete |

---

## 🎯 **When to Use Which?**

### **Use quick-setup.sh when:**
- ✅ **First time** setting up
- ✅ **Testing** the application
- ✅ **Development** environment
- ✅ **Quick** deployment needed
- ✅ **Learning** the system
- ✅ **Simple** requirements

### **Use deploy.sh when:**
- ✅ **Production** deployment
- ✅ **Private repository** access needed
- ✅ **Security** is important
- ✅ **SSL certificates** required
- ✅ **Auto-start** on boot needed
- ✅ **Complete** automation required
- ✅ **GPU optimization** needed

---

## 🚀 **Recommended Workflow**

### **Step 1: Development/Testing**
```bash
# Quick setup for testing
./quick-setup.sh
```

### **Step 2: Production Deployment**
```bash
# Complete production setup
./deploy.sh
```

---

## 📋 **What Happens After Each Script**

### **After quick-setup.sh:**
```bash
# Services running
docker-compose ps

# Access URLs
http://localhost:3000  # Frontend
http://localhost:8000  # Backend
http://localhost:8000/docs  # API docs

# Management
docker-compose logs -f
docker-compose restart
```

### **After deploy.sh:**
```bash
# Services running
docker-compose ps

# Access URLs
https://nodecel.cloud  # Frontend (SSL)
https://nodecel.cloud/api/  # Backend API (SSL)
https://nodecel.cloud/docs  # API docs (SSL)
https://nodecel.cloud/health  # Health check (SSL)

# Management
docker-compose logs -f
docker-compose restart
systemctl status shci-app  # Auto-start service
```

---

## 🔧 **Script Features Breakdown**

### **quick-setup.sh Features:**
- ✅ Ollama service check
- ✅ GPU detection
- ✅ Docker installation
- ✅ Docker Compose installation
- ✅ Basic deployment
- ✅ Service verification
- ✅ User-friendly prompts

### **deploy.sh Features:**
- ✅ System updates
- ✅ Docker installation
- ✅ Docker Compose installation
- ✅ Ollama service check
- ✅ NVIDIA drivers installation
- ✅ NVIDIA Docker support
- ✅ Firewall configuration
- ✅ Private repository support
- ✅ Production environment setup
- ✅ Nginx configuration
- ✅ SSL certificate setup
- ✅ Auto-start service
- ✅ SSL auto-renewal
- ✅ Complete monitoring

---

## 🎯 **Quick Decision Guide**

### **Choose quick-setup.sh if:**
- 🚀 You want **fast setup**
- 🔧 You're **testing/developing**
- 👤 You're a **beginner**
- ⚡ You need **quick results**
- 🏠 You're setting up **locally**

### **Choose deploy.sh if:**
- 🏭 You're deploying to **production**
- 🔐 You have a **private repository**
- 🛡️ You need **security features**
- 🌐 You need **SSL certificates**
- 🔄 You want **complete automation**
- 🖥️ You're using **GPU servers**

---

## 📞 **Support**

### **If quick-setup.sh fails:**
- Check Docker installation
- Verify Ollama service
- Check GPU availability
- Review logs: `docker-compose logs -f`

### **If deploy.sh fails:**
- Check system permissions
- Verify network connectivity
- Check GPU drivers
- Review logs: `docker-compose logs -f`
- Check systemd service: `systemctl status shci-app`

---

## 🎉 **Summary**

**quick-setup.sh**: Fast, simple, development-focused
**deploy.sh**: Complete, production-ready, enterprise-grade

**Choose based on your needs!** 🚀
