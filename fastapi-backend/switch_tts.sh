#!/bin/bash

# TTS System Switcher Script
# Usage: ./switch_tts.sh [gtts|coqui|fallback]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/tts_config.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "TTS System Switcher"
    echo "Usage: $0 [piper|fallback]"
    echo ""
    echo "Options:"
    echo "  piper    - Switch to Piper TTS (high quality, local, fast)"
    echo "  fallback - Switch to fallback TTS system"
    echo ""
    echo "Examples:"
    echo "  $0 piper"
    echo "  $0 fallback"
}

# Function to validate TTS system
validate_tts_system() {
    local system=$1
    case $system in
        piper|fallback)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to switch TTS system
switch_tts_system() {
    local new_system=$1
    
    print_status "Switching TTS system to: $new_system"
    
    # Check if config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Config file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Backup original config
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
    print_status "Backup created: $CONFIG_FILE.backup"
    
    # Update TTS_SYSTEM in config file
    if grep -q "^TTS_SYSTEM=" "$CONFIG_FILE"; then
        sed -i '' "s/^TTS_SYSTEM=.*/TTS_SYSTEM=$new_system/" "$CONFIG_FILE"
    else
        echo "TTS_SYSTEM=$new_system" >> "$CONFIG_FILE"
    fi
    
    print_success "TTS system switched to: $new_system"
    
    # Show current configuration
    print_status "Current TTS configuration:"
    grep "^TTS_SYSTEM=" "$CONFIG_FILE" || echo "TTS_SYSTEM not found in config"
    
    # Show restart instructions
    echo ""
    print_warning "To apply changes, restart the server:"
    echo "  pkill -f uvicorn"
    echo "  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
}

# Function to show current TTS system
show_current_system() {
    print_status "Current TTS system:"
    if [ -f "$CONFIG_FILE" ]; then
        grep "^TTS_SYSTEM=" "$CONFIG_FILE" || echo "TTS_SYSTEM not configured"
    else
        print_error "Config file not found: $CONFIG_FILE"
    fi
}

# Function to run performance test
run_performance_test() {
    print_status "Running performance test..."
    
    if [ -f "$SCRIPT_DIR/test_gtts_performance.py" ]; then
        cd "$SCRIPT_DIR"
        python test_gtts_performance.py
    else
        print_error "Performance test script not found: test_gtts_performance.py"
    fi
}

# Main script logic
main() {
    # Check if no arguments provided
    if [ $# -eq 0 ]; then
        show_current_system
        echo ""
        show_usage
        exit 0
    fi
    
    # Check for help flag
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    # Check for test flag
    if [ "$1" = "test" ]; then
        run_performance_test
        exit 0
    fi
    
    # Validate TTS system
    if ! validate_tts_system "$1"; then
        print_error "Invalid TTS system: $1"
        echo ""
        show_usage
        exit 1
    fi
    
    # Switch TTS system
    switch_tts_system "$1"
}

# Run main function with all arguments
main "$@"
