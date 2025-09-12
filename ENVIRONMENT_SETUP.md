# 🔧 Environment Variables Setup Guide

## 📋 How Environment Variables Work

### **Automatic Loading Process:**

1. **Repository Clone**: `git clone https://github.com/arafatkhairul/shci-app.git`
2. **Environment File**: `env.production` file exists in repository
3. **Deployment Script**: Copies `env.production` → `.env.production`
4. **Docker Compose**: Loads `.env.production` automatically
5. **Containers**: Get environment variables from file

## 🔄 **Step-by-Step Process**

### **Step 1: Repository Clone**
```bash
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
```

**What happens:**
- ✅ `env.production` file is cloned
- ✅ All configuration files are available
- ✅ Environment variables are ready

### **Step 2: Deployment Script**
```bash
./deploy.sh
```

**What happens:**
```bash
# Script automatically:
if [ -f "env.production" ]; then
    print_status "Using existing env.production file..."
    cp env.production .env.production  # ← This line!
else
    print_status "Creating new .env.production file..."
    # Creates new file with default values
fi
```

### **Step 3: Docker Compose**
```yaml
# docker-compose.yml automatically loads:
env_file:
  - .env.production  # ← This loads all variables!

services:
  backend:
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-production}  # ← Uses .env.production
      - LLM_API_URL=${LLM_API_URL:-http://host.docker.internal:11434/v1/chat/completions}
      - CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0,1}
```

## 📁 **File Structure**

```
shci-app/
├── env.production          # ← Template file (in repository)
├── .env.production         # ← Active file (created by deploy.sh)
├── docker-compose.yml      # ← Loads .env.production
└── deploy.sh              # ← Copies env.production → .env.production
```

## 🔧 **Environment Variables**

### **env.production (Template)**
```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://nodecel.cloud
NEXT_PUBLIC_WS_BASE_URL=wss://nodecel.cloud

# Backend Configuration
ENVIRONMENT=production
LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu

# GPU Configuration
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
TTS_DEVICE=cuda
```

### **Docker Compose Usage**
```yaml
environment:
  - ENVIRONMENT=${ENVIRONMENT:-production}           # Uses .env.production
  - LLM_API_URL=${LLM_API_URL:-default_value}      # Uses .env.production
  - CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0,1}  # Uses .env.production
```

## ✅ **Verification**

### **Check Environment Loading**
```bash
# Check if .env.production exists
ls -la .env.production

# Check environment variables in container
docker-compose exec backend env | grep LLM_API_URL
docker-compose exec backend env | grep CUDA_VISIBLE_DEVICES

# Check logs for environment loading
docker-compose logs backend | grep "Using self-hosted LLM"
```

### **Expected Output**
```bash
# From container environment check:
LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
CUDA_VISIBLE_DEVICES=0,1
TORCH_DEVICE=cuda
ENVIRONMENT=production
```

## 🔄 **Customization**

### **Modify Environment Variables**
```bash
# Edit the template file
nano env.production

# Or edit the active file
nano .env.production

# Restart containers to apply changes
docker-compose restart
```

### **Add New Variables**
```bash
# 1. Add to env.production
echo "NEW_VARIABLE=value" >> env.production

# 2. Add to docker-compose.yml
environment:
  - NEW_VARIABLE=${NEW_VARIABLE:-default_value}

# 3. Restart containers
docker-compose up -d
```

## 🚨 **Troubleshooting**

### **Environment Not Loading**
```bash
# Check if .env.production exists
ls -la .env.production

# Check file permissions
chmod 644 .env.production

# Check file content
cat .env.production

# Recreate file
cp env.production .env.production
```

### **Variables Not Working**
```bash
# Check container environment
docker-compose exec backend env

# Check logs
docker-compose logs backend

# Restart containers
docker-compose restart
```

### **Default Values Not Working**
```bash
# Check docker-compose.yml syntax
docker-compose config

# Validate environment file
docker-compose exec backend printenv
```

## 📊 **Environment Flow**

```
Repository Clone
       ↓
env.production (template)
       ↓
deploy.sh copies to .env.production
       ↓
docker-compose.yml loads .env.production
       ↓
Containers get environment variables
       ↓
Application uses variables
```

## 🎯 **Summary**

**Your question answered:**
- ✅ **env.production** file is in repository
- ✅ **deploy.sh** automatically copies it to `.env.production`
- ✅ **docker-compose.yml** loads `.env.production` automatically
- ✅ **Containers** get all environment variables
- ✅ **No manual setup needed!**

**The system automatically:**
1. Uses `env.production` from repository
2. Copies it to `.env.production` during deployment
3. Loads variables into Docker containers
4. Makes them available to your application

**Everything is automatic!** 🚀
