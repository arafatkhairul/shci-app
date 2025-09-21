#!/bin/bash
# ===================================================================
# GPU Usage Check Script for Piper TTS
# ===================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}================================================================================${NC}"
    echo -e "${BLUE}🎮 $1${NC}"
    echo -e "${BLUE}================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if nvidia-smi is available
check_nvidia_smi() {
    if command -v nvidia-smi &> /dev/null; then
        print_success "nvidia-smi is available"
        return 0
    else
        print_error "nvidia-smi not found. Install NVIDIA drivers first."
        return 1
    fi
}

# Check GPU status
check_gpu_status() {
    print_header "GPU STATUS"
    
    if check_nvidia_smi; then
        echo "GPU Information:"
        nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu --format=csv,noheader,nounits
        echo ""
    else
        print_error "Cannot check GPU status"
        return 1
    fi
}

# Check running processes on GPU
check_gpu_processes() {
    print_header "GPU PROCESSES"
    
    if check_nvidia_smi; then
        echo "Processes using GPU:"
        nvidia-smi pmon -c 1 -s u | head -20
        
        echo ""
        echo "Python processes on GPU:"
        nvidia-smi pmon -c 1 | grep python || echo "No Python processes found on GPU"
        
        echo ""
        echo "Piper/TTS related processes:"
        nvidia-smi pmon -c 1 | grep -i -E "(piper|tts|torch)" || echo "No TTS processes found on GPU"
    else
        print_error "Cannot check GPU processes"
    fi
}

# Check CUDA availability
check_cuda() {
    print_header "CUDA AVAILABILITY"
    
    if python3 -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA devices:', torch.cuda.device_count())" 2>/dev/null; then
        print_success "PyTorch CUDA is available"
    else
        print_warning "PyTorch CUDA not available or PyTorch not installed"
    fi
}

# Check environment variables
check_env_vars() {
    print_header "ENVIRONMENT VARIABLES"
    
    echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-'Not set'}"
    echo "PIPER_DEVICE: ${PIPER_DEVICE:-'Not set'}"
    echo "PIPER_FORCE_CUDA: ${PIPER_FORCE_CUDA:-'Not set'}"
    echo "TORCH_CUDA_ALLOC_CONF: ${TORCH_CUDA_ALLOC_CONF:-'Not set'}"
}

# Check TTS service logs
check_tts_logs() {
    print_header "TTS SERVICE LOGS"
    
    echo "Recent TTS logs (last 20 lines):"
    if systemctl is-active --quiet shci-backend.service; then
        sudo journalctl -u shci-backend.service -n 20 | grep -i -E "(tts|piper|gpu|cuda|device)" || echo "No TTS-related logs found"
    else
        print_warning "shci-backend.service is not running"
    fi
}

# Real-time monitoring
monitor_realtime() {
    print_header "REAL-TIME GPU MONITORING"
    echo "Press Ctrl+C to stop monitoring"
    echo ""
    
    while true; do
        clear
        echo "=== GPU Status - $(date) ==="
        nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv
        echo ""
        echo "=== GPU Processes ==="
        nvidia-smi pmon -c 1 -s u | head -10
        echo ""
        echo "Press Ctrl+C to stop"
        sleep 2
    done
}

# Main menu
show_menu() {
    print_header "GPU USAGE CHECK MENU"
    
    echo "Select an option:"
    echo ""
    echo "1. Check GPU Status"
    echo "2. Check GPU Processes"
    echo "3. Check CUDA Availability"
    echo "4. Check Environment Variables"
    echo "5. Check TTS Service Logs"
    echo "6. Real-time Monitoring"
    echo "7. All Checks"
    echo "8. Exit"
    echo ""
}

# Run all checks
run_all_checks() {
    check_gpu_status
    check_gpu_processes
    check_cuda
    check_env_vars
    check_tts_logs
}

# Main script
main() {
    while true; do
        show_menu
        read -p "Enter your choice (1-8): " choice
        
        case $choice in
            1)
                check_gpu_status
                ;;
            2)
                check_gpu_processes
                ;;
            3)
                check_cuda
                ;;
            4)
                check_env_vars
                ;;
            5)
                check_tts_logs
                ;;
            6)
                monitor_realtime
                ;;
            7)
                run_all_checks
                ;;
            8)
                print_success "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
        clear
    done
}

# Run the script
main
