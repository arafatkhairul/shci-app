# 🔐 Root User Setup Guide

## ⚠️ **Security Warning**

**Root user setup is supported but NOT recommended for security reasons.**

### **Why Not Recommended:**
- 🚨 **Security Risk**: Root has unlimited system access
- 🚨 **Accidental Damage**: Can accidentally delete/modify system files
- 🚨 **Attack Surface**: Larger attack surface for malicious actors
- 🚨 **Best Practice**: Production systems should use regular users

### **When Root is Acceptable:**
- ✅ **Development/Testing**: Local development environments
- ✅ **Dedicated Servers**: Single-purpose servers
- ✅ **Quick Setup**: Temporary setups for testing
- ✅ **Learning**: Educational purposes

---

## 🚀 **Root User Setup Process**

### **Step 1: Connect as Root**
```bash
# SSH as root
ssh root@your-server-ip

# Or if using domain
ssh root@nodecel.cloud
```

### **Step 2: Clone Repository**
```bash
# Clone repository (choose method based on your setup)
git clone https://github.com/arafatkhairul/shci-app.git
# OR
git clone https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git
# OR
git clone git@github.com:arafatkhairul/shci-app.git

cd shci-app
```

### **Step 3: Run Setup Script**
```bash
# Quick setup (recommended for root)
./quick-setup.sh

# OR Full deployment
./deploy.sh
```

### **Step 4: Confirm Root Usage**
When prompted:
```
⚠️  Running as root user. This is supported but not recommended for security.
⚠️  Consider using a regular user with sudo privileges for better security.
Continue as root? (y/n): y
```

---

## 🔧 **What's Different for Root User**

### **Automatic Optimizations:**
- ✅ **No sudo commands**: Direct system commands
- ✅ **No user groups**: No need to add to docker group
- ✅ **Direct permissions**: Full system access
- ✅ **Simplified setup**: Fewer permission issues

### **Commands Automatically Adjusted:**
```bash
# Regular user
sudo apt update
sudo systemctl enable service

# Root user (automatic)
apt update
systemctl enable service
```

---

## 📋 **Root User Commands**

### **Quick Setup:**
```bash
# SSH as root
ssh root@nodecel.cloud

# Clone repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Run quick setup
./quick-setup.sh
```

### **Full Deployment:**
```bash
# SSH as root
ssh root@nodecel.cloud

# Clone repository
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app

# Run full deployment
./deploy.sh
```

---

## 🛡️ **Security Recommendations**

### **If You Must Use Root:**

#### **1. Limit Network Access**
```bash
# Configure firewall
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Disable root SSH (after setup)
# Edit /etc/ssh/sshd_config
PermitRootLogin no
```

#### **2. Regular Updates**
```bash
# Keep system updated
apt update && apt upgrade -y

# Monitor security updates
apt list --upgradable
```

#### **3. Monitor System**
```bash
# Check system logs
journalctl -f

# Monitor resource usage
htop
df -h
```

#### **4. Backup Important Data**
```bash
# Backup configuration
tar -czf shci-backup-$(date +%Y%m%d).tar.gz /opt/shci-app

# Backup database
cp /opt/shci-app/fastapi-backend/roleplay.db /backup/
```

---

## 🔄 **Migration to Regular User (Recommended)**

### **After Root Setup, Create Regular User:**
```bash
# Create regular user
adduser shci-user

# Add to sudo group
usermod -aG sudo shci-user

# Transfer ownership
chown -R shci-user:shci-user /opt/shci-app

# Switch to regular user
su - shci-user
```

### **Update Service Permissions:**
```bash
# Edit systemd service
nano /etc/systemd/system/shci-app.service

# Change user
User=shci-user
Group=shci-user
```

---

## 📊 **Root vs Regular User Comparison**

| Feature | Root User | Regular User |
|---------|-----------|--------------|
| **Security** | ❌ High Risk | ✅ Secure |
| **Setup Speed** | ✅ Fast | ⚠️ Slower |
| **Permission Issues** | ✅ None | ⚠️ Some |
| **System Safety** | ❌ Dangerous | ✅ Safe |
| **Best Practice** | ❌ Not Recommended | ✅ Recommended |
| **Production Use** | ❌ Avoid | ✅ Recommended |

---

## 🎯 **Quick Decision**

### **Use Root If:**
- ✅ **Development/Testing** only
- ✅ **Quick setup** needed
- ✅ **Single-purpose** server
- ✅ **Temporary** deployment

### **Use Regular User If:**
- ✅ **Production** deployment
- ✅ **Security** is important
- ✅ **Long-term** usage
- ✅ **Best practices** matter

---

## 🚨 **Important Notes**

1. **Root Access**: Full system control - use carefully
2. **No Sudo**: Commands run directly without sudo
3. **File Permissions**: All files owned by root
4. **Service Management**: Direct systemctl commands
5. **Security Risk**: Higher attack surface

---

## 🎉 **Summary**

**Root user setup is supported but not recommended.**

**For production:**
1. Use root for initial setup
2. Create regular user
3. Transfer ownership
4. Use regular user for daily operations

**For development/testing:**
- Root setup is acceptable
- Quick and easy
- No permission issues

**Choose based on your security requirements!** 🔐
