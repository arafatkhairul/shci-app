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

echo ""
print_success "Deployment completed successfully!"
