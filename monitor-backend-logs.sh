#!/bin/bash
# ===================================================================
# SHCI Backend Log Monitor
# ===================================================================
# This script provides multiple ways to monitor backend logs
# ===================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BACKEND_SERVICE="shci-backend.service"
FRONTEND_SERVICE="shci-frontend.service"
PROJECT_DIR="/var/www/shci-app/fastapi-backend"
LOG_DIR="$PROJECT_DIR/logs"

print_header() {
    echo -e "\n${PURPLE}================================================================================${NC}"
    echo -e "${PURPLE}🔍 $1${NC}"
    echo -e "${PURPLE}================================================================================${NC}\n"
}

print_option() {
    echo -e "${BLUE}$1${NC} ${CYAN}$2${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if service exists
check_service() {
    local service_name="$1"
    if systemctl list-unit-files | grep -q "$service_name"; then
        return 0
    else
        return 1
    fi
}

# Function to show service status
show_service_status() {
    print_header "SERVICE STATUS"
    
    echo "Backend Service:"
    if check_service "$BACKEND_SERVICE"; then
        print_success "Service $BACKEND_SERVICE found"
        systemctl status "$BACKEND_SERVICE" --no-pager
    else
        print_error "Service $BACKEND_SERVICE not found"
    fi
    
    echo ""
    echo "Frontend Service:"
    if check_service "$FRONTEND_SERVICE"; then
        print_success "Service $FRONTEND_SERVICE found"
        systemctl status "$FRONTEND_SERVICE" --no-pager
    else
        print_error "Service $FRONTEND_SERVICE not found"
    fi
    
    echo ""
    echo "All SHCI services:"
    systemctl list-unit-files | grep -E "(shci|fastapi|backend|frontend)" || echo "No related services found"
}

# Function to show real-time logs
show_realtime_logs() {
    print_header "REAL-TIME LOGS"
    
    if check_service "$BACKEND_SERVICE"; then
        print_option "1" "Backend service logs (recommended)"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -f"
        echo ""
        
        print_option "2" "Backend logs with timestamps"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -f --since 'now'"
        echo ""
        
        print_option "3" "Backend error logs only"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -f -p err"
        echo ""
    else
        print_error "Backend service not found, trying alternative methods..."
    fi
    
    if check_service "$FRONTEND_SERVICE"; then
        print_option "4" "Frontend service logs"
        echo "   Command: sudo journalctl -u $FRONTEND_SERVICE -f"
        echo ""
    fi
    
    if [ -d "$PROJECT_DIR" ]; then
        print_option "5" "Application log files"
        echo "   Command: tail -f $PROJECT_DIR/*.log"
        echo ""
        
        if [ -d "$LOG_DIR" ]; then
            print_option "6" "Log directory files"
            echo "   Command: tail -f $LOG_DIR/*.log"
            echo ""
        fi
    fi
}

# Function to show recent logs
show_recent_logs() {
    print_header "RECENT LOGS"
    
    if check_service "$BACKEND_SERVICE"; then
        print_option "1" "Backend - Last 50 lines"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -n 50"
        echo ""
        
        print_option "2" "Backend - Last 100 lines"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -n 100"
        echo ""
        
        print_option "3" "Backend - Last 1 hour"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE --since '1 hour ago'"
        echo ""
        
        print_option "4" "Backend - Last 24 hours"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE --since '24 hours ago'"
        echo ""
    fi
    
    if check_service "$FRONTEND_SERVICE"; then
        print_option "5" "Frontend - Last 50 lines"
        echo "   Command: sudo journalctl -u $FRONTEND_SERVICE -n 50"
        echo ""
    fi
}

# Function to show error logs
show_error_logs() {
    print_header "ERROR LOGS"
    
    if check_service "$BACKEND_SERVICE"; then
        print_option "1" "Backend error level logs only"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -p err"
        echo ""
        
        print_option "2" "Backend error logs with timestamps"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE -p err --since '1 hour ago'"
        echo ""
        
        print_option "3" "Search for specific errors in backend"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'error\\|exception\\|failed'"
        echo ""
    fi
    
    if check_service "$FRONTEND_SERVICE"; then
        print_option "4" "Frontend error logs"
        echo "   Command: sudo journalctl -u $FRONTEND_SERVICE -p err"
        echo ""
    fi
}

# Function to show TTS specific logs
show_tts_logs() {
    print_header "TTS SPECIFIC LOGS"
    
    if check_service "$BACKEND_SERVICE"; then
        print_option "1" "TTS related logs"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'tts\\|piper\\|voice\\|audio'"
        echo ""
        
        print_option "2" "GPU/CPU usage logs"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'gpu\\|cpu\\|device\\|cuda'"
        echo ""
        
        print_option "3" "Model loading logs"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'model\\|load\\|init'"
        echo ""
    fi
}

# Function to show LLM specific logs
show_llm_logs() {
    print_header "LLM SPECIFIC LOGS"
    
    if check_service "$BACKEND_SERVICE"; then
        print_option "1" "LLM request logs"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'llm\\|api\\|request\\|response'"
        echo ""
        
        print_option "2" "Timeout and error logs"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'timeout\\|error\\|exception'"
        echo ""
        
        print_option "3" "Connection logs"
        echo "   Command: sudo journalctl -u $BACKEND_SERVICE | grep -i 'connect\\|disconnect\\|websocket'"
        echo ""
    fi
}

# Function to show performance logs
show_performance_logs() {
    print_header "PERFORMANCE LOGS"
    
    if check_service; then
        print_option "1" "Memory usage logs"
        echo "   Command: sudo journalctl -u $SERVICE_NAME | grep -i 'memory\\|ram\\|gb\\|mb'"
        echo ""
        
        print_option "2" "CPU usage logs"
        echo "   Command: sudo journalctl -u $SERVICE_NAME | grep -i 'cpu\\|core\\|thread'"
        echo ""
        
        print_option "3" "Response time logs"
        echo "   Command: sudo journalctl -u $SERVICE_NAME | grep -i 'time\\|duration\\|ms\\|seconds'"
        echo ""
    fi
}

# Main menu
show_menu() {
    print_header "SHCI BACKEND LOG MONITOR"
    
    echo "Select an option:"
    echo ""
    print_option "1" "Show service status"
    print_option "2" "Real-time logs"
    print_option "3" "Recent logs"
    print_option "4" "Error logs"
    print_option "5" "TTS specific logs"
    print_option "6" "LLM specific logs"
    print_option "7" "Performance logs"
    print_option "8" "All available commands"
    print_option "9" "Exit"
    echo ""
}

# Main script
main() {
    while true; do
        show_menu
        read -p "Enter your choice (1-9): " choice
        
        case $choice in
            1)
                show_service_status
                ;;
            2)
                show_realtime_logs
                ;;
            3)
                show_recent_logs
                ;;
            4)
                show_error_logs
                ;;
            5)
                show_tts_logs
                ;;
            6)
                show_llm_logs
                ;;
            7)
                show_performance_logs
                ;;
            8)
                show_all_commands
                ;;
            9)
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

# Function to show all commands
show_all_commands() {
    print_header "ALL AVAILABLE COMMANDS"
    
    echo "=== SERVICE MANAGEMENT ==="
    echo "sudo systemctl status $SERVICE_NAME"
    echo "sudo systemctl restart $SERVICE_NAME"
    echo "sudo systemctl stop $SERVICE_NAME"
    echo "sudo systemctl start $SERVICE_NAME"
    echo ""
    
    echo "=== LOG VIEWING ==="
    echo "sudo journalctl -u $SERVICE_NAME -f                    # Real-time logs"
    echo "sudo journalctl -u $SERVICE_NAME -n 100               # Last 100 lines"
    echo "sudo journalctl -u $SERVICE_NAME --since '1 hour ago' # Last 1 hour"
    echo "sudo journalctl -u $SERVICE_NAME -p err               # Error logs only"
    echo ""
    
    echo "=== FILTERED LOGS ==="
    echo "sudo journalctl -u $SERVICE_NAME | grep -i 'error'     # Error messages"
    echo "sudo journalctl -u $SERVICE_NAME | grep -i 'tts'       # TTS related"
    echo "sudo journalctl -u $SERVICE_NAME | grep -i 'llm'       # LLM related"
    echo "sudo journalctl -u $SERVICE_NAME | grep -i 'memory'    # Memory related"
    echo ""
    
    echo "=== APPLICATION LOGS ==="
    echo "tail -f $PROJECT_DIR/*.log                             # Application logs"
    echo "tail -f $LOG_DIR/*.log                                 # Log directory"
    echo ""
    
    echo "=== SYSTEM MONITORING ==="
    echo "htop                                                   # System resources"
    echo "free -h                                                # Memory usage"
    echo "df -h                                                  # Disk usage"
    echo "ps aux | grep python                                   # Python processes"
}

# Run the script
main
