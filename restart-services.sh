#!/bin/bash
# ===================================================================
# SHCI Services Restart Script
# ===================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Service names
BACKEND_SERVICE="shci-backend.service"
FRONTEND_SERVICE="shci-frontend.service"
NGINX_SERVICE="nginx.service"

print_header() {
    echo -e "\n${BLUE}================================================================================${NC}"
    echo -e "${BLUE}🔄 $1${NC}"
    echo -e "${BLUE}================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to restart a service
restart_service() {
    local service_name="$1"
    local service_display="$2"
    
    echo -e "\n${BLUE}Restarting $service_display...${NC}"
    
    if systemctl is-active --quiet "$service_name"; then
        echo "Stopping $service_display..."
        sudo systemctl stop "$service_name"
        sleep 2
    fi
    
    echo "Starting $service_display..."
    sudo systemctl start "$service_name"
    sleep 3
    
    if systemctl is-active --quiet "$service_name"; then
        print_success "$service_display restarted successfully"
    else
        print_error "$service_display failed to start"
        echo "Check logs with: sudo journalctl -u $service_name -n 20"
    fi
}

# Function to check service status
check_status() {
    local service_name="$1"
    local service_display="$2"
    
    if systemctl is-active --quiet "$service_name"; then
        print_success "$service_display is running"
    else
        print_error "$service_display is not running"
    fi
}

# Main menu
show_menu() {
    print_header "SHCI SERVICES RESTART MENU"
    
    echo "Select an option:"
    echo ""
    echo "1. Restart Backend Only"
    echo "2. Restart Frontend Only"
    echo "3. Restart Nginx Only"
    echo "4. Restart All Services"
    echo "5. Check Service Status"
    echo "6. Stop All Services"
    echo "7. Start All Services"
    echo "8. Reload Nginx Config"
    echo "9. Exit"
    echo ""
}

# Main script
main() {
    while true; do
        show_menu
        read -p "Enter your choice (1-9): " choice
        
        case $choice in
            1)
                print_header "RESTARTING BACKEND SERVICE"
                restart_service "$BACKEND_SERVICE" "Backend Service"
                ;;
            2)
                print_header "RESTARTING FRONTEND SERVICE"
                restart_service "$FRONTEND_SERVICE" "Frontend Service"
                ;;
            3)
                print_header "RESTARTING NGINX SERVICE"
                restart_service "$NGINX_SERVICE" "Nginx Service"
                ;;
            4)
                print_header "RESTARTING ALL SERVICES"
                restart_service "$BACKEND_SERVICE" "Backend Service"
                restart_service "$FRONTEND_SERVICE" "Frontend Service"
                restart_service "$NGINX_SERVICE" "Nginx Service"
                ;;
            5)
                print_header "SERVICE STATUS"
                check_status "$BACKEND_SERVICE" "Backend Service"
                check_status "$FRONTEND_SERVICE" "Frontend Service"
                check_status "$NGINX_SERVICE" "Nginx Service"
                ;;
            6)
                print_header "STOPPING ALL SERVICES"
                echo "Stopping services..."
                sudo systemctl stop "$BACKEND_SERVICE" "$FRONTEND_SERVICE" "$NGINX_SERVICE"
                print_success "All services stopped"
                ;;
            7)
                print_header "STARTING ALL SERVICES"
                echo "Starting services..."
                sudo systemctl start "$BACKEND_SERVICE" "$FRONTEND_SERVICE" "$NGINX_SERVICE"
                sleep 5
                check_status "$BACKEND_SERVICE" "Backend Service"
                check_status "$FRONTEND_SERVICE" "Frontend Service"
                check_status "$NGINX_SERVICE" "Nginx Service"
                ;;
            8)
                print_header "RELOADING NGINX CONFIG"
                echo "Reloading Nginx configuration..."
                sudo systemctl reload "$NGINX_SERVICE"
                if systemctl is-active --quiet "$NGINX_SERVICE"; then
                    print_success "Nginx configuration reloaded successfully"
                else
                    print_error "Nginx reload failed"
                fi
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

# Run the script
main
