# 🔐 Private Repository Setup Guide

## 📋 Options for Private Repository Access

### **Option 1: Personal Access Token (Recommended)**

#### **Step 1: Create Personal Access Token**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (Full control of private repositories)
4. Copy the token (save it securely!)

#### **Step 2: Clone with Token**
```bash
# Method 1: Direct clone with token
git clone https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git

# Method 2: Clone then set remote
git clone https://github.com/arafatkhairul/shci-app.git
cd shci-app
git remote set-url origin https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git
```

#### **Step 3: Update Deployment Script**
```bash
# Edit deploy.sh to use token
nano deploy.sh

# Find this line:
git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME

# Change to:
git clone https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
```

### **Option 2: SSH Key (Most Secure)**

#### **Step 1: Generate SSH Key**
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub
```

#### **Step 2: Add SSH Key to GitHub**
1. Go to GitHub → Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste your public key
4. Save

#### **Step 3: Clone with SSH**
```bash
# Clone using SSH
git clone git@github.com:arafatkhairul/shci-app.git

# Update deployment script
nano deploy.sh
# Change to:
git clone git@github.com:arafatkhairul/shci-app.git /opt/$PROJECT_NAME
```

### **Option 3: GitHub CLI (Easiest)**

#### **Step 1: Install GitHub CLI**
```bash
# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

#### **Step 2: Authenticate**
```bash
# Login to GitHub
gh auth login

# Select: GitHub.com → HTTPS → Yes → Login with web browser
```

#### **Step 3: Clone**
```bash
# Clone using GitHub CLI
gh repo clone arafatkhairul/shci-app

# Update deployment script
nano deploy.sh
# Change to:
gh repo clone arafatkhairul/shci-app /opt/$PROJECT_NAME
```

## 🔧 **Update Deployment Scripts**

### **Method 1: Token-based (Quick Fix)**
```bash
# Edit deploy.sh
nano deploy.sh

# Find and replace:
git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME

# With:
git clone https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME
```

### **Method 2: SSH-based (Secure)**
```bash
# Edit deploy.sh
nano deploy.sh

# Find and replace:
git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME

# With:
git clone git@github.com:arafatkhairul/shci-app.git /opt/$PROJECT_NAME
```

### **Method 3: GitHub CLI (Modern)**
```bash
# Edit deploy.sh
nano deploy.sh

# Find and replace:
git clone https://github.com/arafatkhairul/shci-app.git /opt/$PROJECT_NAME

# With:
gh repo clone arafatkhairul/shci-app /opt/$PROJECT_NAME
```

## 🚀 **Updated Server Setup Commands**

### **Option 1: Personal Access Token**
```bash
# SSH to server
ssh username@nodecel.cloud

# Clone with token
git clone https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git
cd shci-app

# Run deployment
./deploy.sh
```

### **Option 2: SSH Key**
```bash
# SSH to server
ssh username@nodecel.cloud

# Clone with SSH
git clone git@github.com:arafatkhairul/shci-app.git
cd shci-app

# Run deployment
./deploy.sh
```

### **Option 3: GitHub CLI**
```bash
# SSH to server
ssh username@nodecel.cloud

# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Authenticate
gh auth login

# Clone
gh repo clone arafatkhairul/shci-app
cd shci-app

# Run deployment
./deploy.sh
```

## 🔐 **Security Best Practices**

### **Personal Access Token**
- ✅ **Expiration**: Set token expiration (90 days recommended)
- ✅ **Scopes**: Only give `repo` scope
- ✅ **Storage**: Store token securely
- ✅ **Rotation**: Rotate tokens regularly

### **SSH Key**
- ✅ **Passphrase**: Use strong passphrase
- ✅ **Key Type**: Use ed25519 (more secure)
- ✅ **Backup**: Backup private key securely
- ✅ **Multiple Keys**: Use different keys for different purposes

### **GitHub CLI**
- ✅ **Authentication**: Use web-based auth
- ✅ **Scopes**: Minimal required scopes
- ✅ **Updates**: Keep GitHub CLI updated

## 🛠️ **Troubleshooting**

### **Token Issues**
```bash
# Test token
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Check repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/arafatkhairul/shci-app
```

### **SSH Issues**
```bash
# Test SSH connection
ssh -T git@github.com

# Check SSH agent
ssh-add -l

# Add key to agent
ssh-add ~/.ssh/id_ed25519
```

### **GitHub CLI Issues**
```bash
# Check authentication
gh auth status

# Re-authenticate
gh auth login

# Check repository access
gh repo view arafatkhairul/shci-app
```

## 📋 **Quick Setup Commands**

### **For Personal Access Token:**
```bash
# 1. Create token on GitHub
# 2. Clone with token
git clone https://YOUR_TOKEN@github.com/arafatkhairul/shci-app.git
cd shci-app
./deploy.sh
```

### **For SSH Key:**
```bash
# 1. Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. Add to GitHub
cat ~/.ssh/id_ed25519.pub

# 3. Clone with SSH
git clone git@github.com:arafatkhairul/shci-app.git
cd shci-app
./deploy.sh
```

### **For GitHub CLI:**
```bash
# 1. Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# 2. Authenticate
gh auth login

# 3. Clone
gh repo clone arafatkhairul/shci-app
cd shci-app
./deploy.sh
```

## 🎯 **Recommendation**

**For Production Server:**
1. **SSH Key** (most secure, no token exposure)
2. **Personal Access Token** (quick setup)
3. **GitHub CLI** (modern, user-friendly)

**Choose based on your security requirements!** 🔐
