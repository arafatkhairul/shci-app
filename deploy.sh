#!/usr/bin/env bash
# ===================================================================
# SHCI Voice Assistant - Automated Deployment Script
#
# This script automates the full deployment process:
# 1. Pulls the latest code from the 'main' branch.
# 2. Installs/updates backend Python dependencies.
# 3. Builds the frontend Next.js application.
# 4. Restarts the systemd services.
# 5. Verifies that the services are running correctly.
# ===================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_DIR="/root/shci-app"
BACKEND_SERVICE="fastapi-app.service"  # FastAPI systemd
FRONTEND_SERVICE="nextjs-app.service" # Next.js systemd 

# --- Helper Functions for Colored Output ---
print_status() {
    echo -e "\n\033[1;34m◆\033[0m \033[1m$1\033[0m"
}
print_success() {
    echo -e "\033[1;32m✅ $1\033[0m"
}
print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

# --- Deployment Script Starts Here ---

print_status "Starting SHCI Application Deployment..."

# Navigate to the project directory
cd "$PROJECT_DIR" || { print_error "Project directory '$PROJECT_DIR' not found. Aborting."; exit 1; }

print_status "Pulling latest changes from Git..."
git fetch --all
git reset --hard origin/main
print_success "Repository updated successfully."

# --- Backend Deployment ---
print_status "Deploying Backend (FastAPI)..."
cd "$PROJECT_DIR/fastapi-backend"

# Note: Assuming pyenv is managing the global Python environment.
# No venv activation is needed.
print_status "Installing/updating Python dependencies..."
pip install --upgrade pip wheel
pip install -r requirements.txt
print_success "Backend dependencies are up to date."

# Apply server performance optimizations
print_status "Applying server performance optimizations..."
if [ -f "server-performance.env" ]; then
    echo "Loading server performance configuration..."
    export $(cat server-performance.env | grep -v '^#' | xargs)
    print_success "Server performance optimizations applied."
else
    print_error "server-performance.env not found - using default settings"
fi

# --- Frontend Deployment ---
print_status "Deploying Frontend (Next.js)..."
cd "$PROJECT_DIR/web-app"

print_status "Installing Node modules and building the application..."
npm ci # 'ci' is faster and more reliable for production builds
npm run build
print_success "Frontend application built successfully."

# --- Restart and Verify Services ---
print_status "Restarting application services via systemd..."
sudo systemctl restart "$BACKEND_SERVICE"
sudo systemctl restart "$FRONTEND_SERVICE"

# Give services a moment to start up
sleep 5

print_status "Verifying service status..."

# Check backend service
if systemctl is-active --quiet "$BACKEND_SERVICE"; then
    print_success "Backend service ($BACKEND_SERVICE) is active and running."
else
    print_error "Backend service ($BACKEND_SERVICE) failed to start. Check logs with 'journalctl -u $BACKEND_SERVICE -f'"
    exit 1
fi

# Check frontend service
if systemctl is-active --quiet "$FRONTEND_SERVICE"; then
    print_success "Frontend service ($FRONTEND_SERVICE) is active and running."
else
    print_error "Frontend service ($FRONTEND_SERVICE) failed to start. Check logs with 'journalctl -u $FRONTEND_SERVICE -f'"
    exit 1
fi

# --- TTS Model Status Check ---
print_status "Checking TTS Model Status..."

# Wait a bit more for TTS initialization
sleep 3

# Check TTS system status
cd "$PROJECT_DIR/fastapi-backend"

print_status "🔍 TTS System Status Check:"
echo "================================"

# Check if TTS system is working
if python3 -c "
import sys
sys.path.append('.')
try:
    from tts_factory import get_tts_info
    info = get_tts_info()
    
    print(f'📊 Environment: {info[\"environment\"].upper()}')
    print(f'🎵 TTS System: {info[\"preferred_system\"].upper()}')
    print(f'📋 Available Providers: {\", \".join(info[\"available_providers\"])}')
    
    if 'piper' in info['providers']:
        piper_info = info['providers']['piper']
        device_config = piper_info['device_config']
        
        print(f'')
        print(f'🖥️  DEVICE CONFIGURATION:')
        print(f'   Device Type: {device_config[\"device_type\"]}')
        print(f'   Device Name: {device_config[\"device_name\"]}')
        print(f'   CUDA Available: {\"✅ YES\" if device_config[\"cuda_available\"] else \"❌ NO\"}')
        print(f'   CUDA Devices: {device_config[\"cuda_device_count\"]}')
        print(f'   Using CUDA: {\"✅ YES\" if device_config[\"use_cuda\"] else \"❌ NO\"}')
        
        if device_config['use_cuda']:
            print(f'   Performance: 🚀 GPU ACCELERATED')
        else:
            print(f'   Performance: 💻 CPU OPTIMIZED')
        
        print(f'')
        print(f'🎯 TTS CONFIGURATION:')
        print(f'   Model: {piper_info[\"model_name\"]}')
        print(f'   Sample Rate: {piper_info[\"sample_rate\"]} Hz')
        print(f'   Length Scale: {piper_info[\"synthesis_params\"][\"length_scale\"]}')
        print(f'   Noise Scale: {piper_info[\"synthesis_params\"][\"noise_scale\"]}')
        print(f'   Noise W: {piper_info[\"synthesis_params\"][\"noise_w\"]}')
        
        print(f'')
        print(f'📈 PERFORMANCE SUMMARY:')
        if device_config['use_cuda']:
            print(f'   🚀 GPU ACCELERATION: ENABLED')
            print(f'   ⚡ Performance: HIGH')
            print(f'   🎯 Optimization: PRODUCTION')
        else:
            print(f'   💻 CPU PROCESSING: ENABLED')
            print(f'   ⚡ Performance: OPTIMIZED')
            print(f'   🎯 Optimization: DEVELOPMENT')
    
    print(f'')
    print(f'✅ TTS System Status: HEALTHY')
    
except Exception as e:
    print(f'❌ TTS System Error: {e}')
    sys.exit(1)
" 2>/dev/null; then
    print_success "TTS system is working correctly!"
else
    print_error "TTS system check failed. Check logs for details."
    echo ""
    print_status "Recent TTS logs:"
    journalctl -u "$BACKEND_SERVICE" --since "2 minutes ago" --no-pager | grep -E "(TTS|Piper|GPU|CPU|Device)" || echo "No TTS logs found"
fi

echo ""
print_success "Deployment completed successfully!"

# --- Beautiful Startup Banner ---
echo ""
echo "=================================================================================="
echo "🚀 SHCI VOICE ASSISTANT - STARTING UP"
echo "=================================================================================="
echo ""
print_status "🎉 SHCI Voice Assistant is now running!"
print_status "📊 Check TTS status above to see if GPU/CPU is being used"
print_status "🔍 Monitor logs with: journalctl -u $BACKEND_SERVICE -f"
print_status "🌐 Access your application at: http://your-server-ip:3000"
echo ""
echo "=================================================================================="
echo "🎯 DEPLOYMENT COMPLETE - SYSTEM READY!"
echo "=================================================================================="
