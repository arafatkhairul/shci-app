#!/bin/bash

# ===================================================================
# SHCI Voice Assistant - Backend Runner Script
# ===================================================================
# 
# This script sets up the environment and runs the FastAPI backend
# with proper FFmpeg library paths for torchaudio compatibility
# ===================================================================

set -e

# Set up FFmpeg library path for torchaudio compatibility
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/ffmpeg@6/lib:$DYLD_LIBRARY_PATH"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting SHCI Voice Assistant Backend...${NC}"
echo -e "${GREEN}✅ FFmpeg library path configured${NC}"

# Activate virtual environment
source venv/bin/activate

# Run the backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

