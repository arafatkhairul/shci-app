#!/bin/bash

# Quick Python 3.11.9 Fix Script
echo "🔧 Fixing Python version issue..."

# Stop services first
echo "⏹️  Stopping services..."
systemctl stop shci-backend shci-frontend

# Remove Python 3.12
echo "🗑️  Removing Python 3.12..."
apt remove -y python3.12 python3.12-venv python3.12-dev python3.12-distutils python3.12-minimal 2>/dev/null || true
apt autoremove -y 2>/dev/null || true

# Install Python 3.11.9
echo "📦 Installing Python 3.11.9..."
apt update
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils python3.11-minimal python3.11-pip

# Set Python 3.11 as default
echo "⚙️  Setting Python 3.11 as default..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Go to project directory
cd /var/www/shci-app/fastapi-backend

# Remove old virtual environment
echo "🗑️  Removing old virtual environment..."
rm -rf venv

# Create new virtual environment with Python 3.11
echo "🆕 Creating new virtual environment with Python 3.11..."
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip wheel setuptools

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# Test imports
echo "🧪 Testing imports..."
python3.11 test_imports.py

# Update systemd service to use Python 3.11
echo "⚙️  Updating systemd service..."
sed -i 's|python -m uvicorn|python3.11 -m uvicorn|g' /etc/systemd/system/shci-backend.service

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Start services
echo "▶️  Starting services..."
systemctl start shci-backend shci-frontend

# Check status
echo "✅ Checking service status..."
systemctl status shci-backend --no-pager -l

echo "🎉 Python fix completed!"
echo "🌐 Test your website: https://nodecel.com"
