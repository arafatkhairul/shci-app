#!/bin/bash

# ===================================================================
# SHCI Backend Service Log Monitor
# ===================================================================
# 
# This script provides various ways to monitor backend service logs
# 
# Usage:
#   ./monitor-logs.sh status     # Check service status
#   ./monitor-logs.sh logs       # Show recent logs
#   ./monitor-logs.sh follow     # Follow logs in real-time
#   ./monitor-logs.sh today      # Show today's logs
#   ./monitor-logs.sh restart    # Restart service
#   ./monitor-logs.sh errors     # Show only errors
# ===================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Service name
SERVICE_NAME="fastapi-app.service"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# Function to show usage
show_usage() {
    print_header "SHCI Backend Service Log Monitor"
    echo "=============================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  status    - Check service status"
    echo "  logs      - Show recent logs (last 50 lines)"
    echo "  follow    - Follow logs in real-time"
    echo "  today     - Show today's logs"
    echo "  errors    - Show only error logs"
    echo "  restart   - Restart the service"
    echo "  stop      - Stop the service"
    echo "  start     - Start the service"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 status     # Check if service is running"
    echo "  $0 follow     # Watch logs in real-time"
    echo "  $0 errors     # Show only errors"
    echo "  $0 restart    # Restart service"
}

# Function to check service status
check_status() {
    print_header "🔍 Service Status Check"
    echo "=========================="
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Service is RUNNING"
    else
        print_error "Service is NOT RUNNING"
    fi
    
    echo ""
    print_info "Detailed Status:"
    sudo systemctl status $SERVICE_NAME --no-pager -l
    
    echo ""
    print_info "Service Configuration:"
    sudo systemctl show $SERVICE_NAME --property=MainPID,ExecStart,WorkingDirectory,Environment
}

# Function to show recent logs
show_logs() {
    print_header "📋 Recent Logs (Last 50 lines)"
    echo "===================================="
    
    sudo journalctl -u $SERVICE_NAME --no-pager -n 50
}

# Function to follow logs in real-time
follow_logs() {
    print_header "👀 Following Logs in Real-time"
    echo "=================================="
    print_info "Press Ctrl+C to stop following logs"
    echo ""
    
    sudo journalctl -u $SERVICE_NAME -f
}

# Function to show today's logs
show_today_logs() {
    print_header "📅 Today's Logs"
    echo "================"
    
    sudo journalctl -u $SERVICE_NAME --since today --no-pager
}

# Function to show only errors
show_errors() {
    print_header "🚨 Error Logs Only"
    echo "==================="
    
    sudo journalctl -u $SERVICE_NAME --since today --no-pager | grep -i "error\|exception\|failed\|critical" || echo "No errors found in today's logs"
}

# Function to restart service
restart_service() {
    print_header "🔄 Restarting Service"
    echo "======================"
    
    print_info "Stopping service..."
    sudo systemctl stop $SERVICE_NAME
    
    print_info "Starting service..."
    sudo systemctl start $SERVICE_NAME
    
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Service restarted successfully"
    else
        print_error "Service failed to restart"
    fi
    
    echo ""
    print_info "Recent logs after restart:"
    sudo journalctl -u $SERVICE_NAME --since "1 minute ago" --no-pager
}

# Function to stop service
stop_service() {
    print_header "⏹️  Stopping Service"
    echo "==================="
    
    sudo systemctl stop $SERVICE_NAME
    
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Service stopped successfully"
    else
        print_error "Failed to stop service"
    fi
}

# Function to start service
start_service() {
    print_header "▶️  Starting Service"
    echo "==================="
    
    sudo systemctl start $SERVICE_NAME
    
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Service started successfully"
    else
        print_error "Failed to start service"
    fi
    
    echo ""
    print_info "Recent logs after start:"
    sudo journalctl -u $SERVICE_NAME --since "1 minute ago" --no-pager
}

# Function to show log summary
show_log_summary() {
    print_header "📊 Log Summary"
    echo "==============="
    
    echo ""
    print_info "Service Status:"
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "  ✅ Running"
    else
        echo "  ❌ Not Running"
    fi
    
    echo ""
    print_info "Recent Activity (Last 10 lines):"
    sudo journalctl -u $SERVICE_NAME --no-pager -n 10
    
    echo ""
    print_info "Error Count (Today):"
    ERROR_COUNT=$(sudo journalctl -u $SERVICE_NAME --since today --no-pager | grep -i "error\|exception\|failed\|critical" | wc -l)
    echo "  Errors: $ERROR_COUNT"
    
    echo ""
    print_info "Service Uptime:"
    sudo systemctl show $SERVICE_NAME --property=ActiveEnterTimestamp --value
}

# Main script logic
case "${1:-}" in
    "status")
        check_status
        ;;
    "logs")
        show_logs
        ;;
    "follow")
        follow_logs
        ;;
    "today")
        show_today_logs
        ;;
    "errors")
        show_errors
        ;;
    "restart")
        restart_service
        ;;
    "stop")
        stop_service
        ;;
    "start")
        start_service
        ;;
    "summary")
        show_log_summary
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    "")
        print_error "No command specified"
        echo ""
        show_usage
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac

echo ""
print_status "Log monitoring complete!"
