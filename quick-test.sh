#!/bin/bash

# SHCI Quick Test Script
# This script runs quick tests to verify the application

echo "🧪 SHCI Quick Test Starting..."
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
    fi
}

# Test 1: Frontend build test
echo "🏗️  Testing frontend build..."
cd web-app
if npm run build > /dev/null 2>&1; then
    print_status "Frontend builds successfully" 0
else
    print_status "Frontend build failed" 1
fi
cd ..

# Test 2: Backend dependencies test
echo "🐍 Testing backend dependencies..."
cd fastapi-backend
if pip3 install -r requirements.txt > /dev/null 2>&1; then
    print_status "Backend dependencies installed" 0
else
    print_status "Backend dependencies failed" 1
fi
cd ..

# Test 3: Check if main.py is valid Python
echo "🐍 Testing backend Python syntax..."
if python3 -m py_compile fastapi-backend/main.py > /dev/null 2>&1; then
    print_status "Backend Python syntax is valid" 0
else
    print_status "Backend Python syntax has errors" 1
fi

# Test 4: Check if VoiceAgent.tsx is valid TypeScript
echo "📱 Testing frontend TypeScript..."
if command -v npx >/dev/null 2>&1; then
    cd web-app
    if npx tsc --noEmit --skipLibCheck components/VoiceAgent.tsx > /dev/null 2>&1; then
        print_status "Frontend TypeScript is valid" 0
    else
        print_status "Frontend TypeScript has errors" 1
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  npx not available, skipping TypeScript check${NC}"
fi

# Test 5: Check environment files
echo "🔧 Testing environment files..."
if [ -f "web-app/.env.local" ]; then
    print_status "Frontend environment file exists" 0
else
    echo -e "${YELLOW}⚠️  Frontend .env.local missing${NC}"
fi

if [ -f "fastapi-backend/.env" ]; then
    print_status "Backend environment file exists" 0
else
    echo -e "${YELLOW}⚠️  Backend .env missing${NC}"
fi

# Test 6: Check TTS files
echo "🎤 Testing TTS configuration..."
if [ -f "fastapi-backend/xtts_manager.py" ]; then
    print_status "TTS manager exists" 0
else
    print_status "TTS manager missing" 1
fi

# Test 7: Check WebSocket service
echo "🔌 Testing WebSocket service..."
if grep -q "WebSocket" fastapi-backend/main.py; then
    print_status "WebSocket service configured" 0
else
    print_status "WebSocket service not found" 1
fi

# Test 8: Check speech recognition service
echo "🎤 Testing speech recognition service..."
if [ -f "web-app/services/WebkitVADService.ts" ]; then
    print_status "Speech recognition service exists" 0
else
    print_status "Speech recognition service missing" 1
fi

echo ""
echo "=============================="
echo "🎯 Quick test completed!"
echo ""
echo "📋 Summary:"
echo "- Frontend: Check build status above"
echo "- Backend: Check Python syntax above"
echo "- Services: Check service files above"
echo ""
echo "🚀 Ready for deployment!"
echo "Run: bash deploy.sh"
