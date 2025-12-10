#!/bin/bash
# FilamentBox Complete Installation Script
# Interactive installer with menu system for install, update, and configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Default installation directory
DEFAULT_INSTALL_DIR="/opt/filamentcontrol"

# Installation directory (will be set by user)
INSTALL_DIR=""

# Temporary directory for modified files
TEMP_DIR=""

# Service status flags
MAIN_SERVICE_EXISTS=false
MAIN_SERVICE_RUNNING=false
WEBUI_SERVICE_EXISTS=false
WEBUI_SERVICE_RUNNING=false

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install/install.sh"
    exit 1
fi

# Function to clean up on exit
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Function to update file paths
update_paths_in_file() {
    local file=$1
    local install_dir=$2
    
    # Escape forward slashes for sed
    local escaped_dir=$(echo "$install_dir" | sed 's/\//\\\//g')
    local escaped_default=$(echo "$DEFAULT_INSTALL_DIR" | sed 's/\//\\\//g')
    
    # Replace all occurrences of default path with new path
    sed -i "s/${escaped_default}/${escaped_dir}/g" "$file"
}

# Function to check if services exist and are running
detect_services() {
    if systemctl list-unit-files | grep -q "filamentbox.service"; then
        MAIN_SERVICE_EXISTS=true
        if systemctl is-active --quiet filamentbox.service 2>/dev/null; then
            MAIN_SERVICE_RUNNING=true
        fi
    fi
    
    if systemctl list-unit-files | grep -q "filamentbox-webui.service"; then
        WEBUI_SERVICE_EXISTS=true
        if systemctl is-active --quiet filamentbox-webui.service 2>/dev/null; then
            WEBUI_SERVICE_RUNNING=true
        fi
    fi
}

# Function to get installation directory from service file
get_install_dir_from_service() {
    if [ -f "/etc/systemd/system/filamentbox.service" ]; then
        grep "^WorkingDirectory=" /etc/systemd/system/filamentbox.service | cut -d'=' -f2
    else
        echo ""
    fi
}

# Function to show header
show_header() {
    clear
    echo
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║         FilamentBox Environment Monitor Installer          ║${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Function to show service status
show_service_status() {
    echo -e "${BLUE}Current Service Status:${NC}"
    echo "─────────────────────────"
    
    if [ "$MAIN_SERVICE_EXISTS" = true ]; then
        if [ "$MAIN_SERVICE_RUNNING" = true ]; then
            echo -e "  Main Service:   ${GREEN}✓ Installed and Running${NC}"
        else
            echo -e "  Main Service:   ${YELLOW}✓ Installed but Stopped${NC}"
        fi
    else
        echo -e "  Main Service:   ${RED}✗ Not Installed${NC}"
    fi
    
    if [ "$WEBUI_SERVICE_EXISTS" = true ]; then
        if [ "$WEBUI_SERVICE_RUNNING" = true ]; then
            echo -e "  Web UI Service: ${GREEN}✓ Installed and Running${NC}"
        else
            echo -e "  Web UI Service: ${YELLOW}✓ Installed but Stopped${NC}"
        fi
    else
        echo -e "  Web UI Service: ${RED}✗ Not Installed${NC}"
    fi
    
    if [ "$MAIN_SERVICE_EXISTS" = true ]; then
        local detected_dir=$(get_install_dir_from_service)
        if [ -n "$detected_dir" ]; then
            echo -e "  Install Dir:    ${CYAN}$detected_dir${NC}"
        fi
    fi
    
    echo
}

# Function to show main menu
show_main_menu() {
    show_header
    show_service_status
    
    echo -e "${GREEN}Installation Options:${NC}"
    echo "══════════════════════════"
    echo
    
    if [ "$MAIN_SERVICE_EXISTS" = false ] && [ "$WEBUI_SERVICE_EXISTS" = false ]; then
        echo "  1) Fresh Installation (Install all services)"
        echo "  2) Configure Environment (Encrypted database setup)"
        echo "  3) Exit"
        echo
        read -p "Enter choice (1-3): " MENU_CHOICE
        
        case ${MENU_CHOICE} in
            1) do_fresh_install ;;
            2) do_configure_only ;;
            3) exit 0 ;;
            *) 
                echo -e "${RED}Invalid choice${NC}"
                sleep 2
                show_main_menu
                ;;
        esac
    else
        echo "  1) Update Configuration (Encrypted database)"
        echo "  2) Update Services (Refresh code and restart)"
        echo "  3) Reinstall Services (Fresh installation)"
        echo "  4) View Service Logs"
        echo "  5) Exit"
        echo
        read -p "Enter choice (1-5): " MENU_CHOICE
        
        case ${MENU_CHOICE} in
            1) do_configure_only ;;
            2) do_service_update ;;
            3) do_fresh_install ;;
            4) do_view_logs ;;
            5) exit 0 ;;
            *) 
                echo -e "${RED}Invalid choice${NC}"
                sleep 2
                show_main_menu
                ;;
        esac
    fi
}

# Function to select installation directory
select_install_directory() {
    echo -e "${GREEN}Installation Directory Selection${NC}"
    echo "════════════════════════════════"
    echo
    
    # If services exist, use detected directory
    local detected_dir=$(get_install_dir_from_service)
    if [ -n "$detected_dir" ] && [ -d "$detected_dir" ]; then
        echo -e "Existing installation detected at: ${CYAN}$detected_dir${NC}"
        read -p "Use this directory? (Y/n): " USE_EXISTING
        if [[ $USE_EXISTING =~ ^[Yy]$ ]] || [[ -z $USE_EXISTING ]]; then
            INSTALL_DIR="$detected_dir"
            echo -e "${GREEN}Using existing directory: $INSTALL_DIR${NC}"
            echo
            return
        fi
    fi
    
    echo "Where would you like to install FilamentBox?"
    echo
    echo "  1) Default location: $DEFAULT_INSTALL_DIR"
    echo "  2) Parent directory: $PARENT_DIR"
    echo "  3) Custom directory"
    echo
    read -p "Enter choice (1-3) [1]: " DIR_CHOICE

    case ${DIR_CHOICE:-1} in
        1)
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
            ;;
        2)
            INSTALL_DIR="$PARENT_DIR"
            ;;
        3)
            read -p "Enter custom directory path: " CUSTOM_DIR
            INSTALL_DIR="${CUSTOM_DIR%/}"
            ;;
        *)
            echo -e "${RED}Invalid choice. Using default.${NC}"
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
            ;;
    esac
    
    echo -e "${GREEN}Selected directory: $INSTALL_DIR${NC}"
    echo

    # Ensure installation directory exists
    if [ ! -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Directory doesn't exist${NC}"
        read -p "Create directory $INSTALL_DIR? (Y/n): " CREATE_DIR
        if [[ $CREATE_DIR =~ ^[Yy]$ ]] || [[ -z $CREATE_DIR ]]; then
            mkdir -p "$INSTALL_DIR"
            echo -e "${GREEN}✓ Directory created${NC}"
        else
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
    fi
    echo
}

# Function to copy files to installation directory
copy_installation_files() {
    if [ "$INSTALL_DIR" = "$PARENT_DIR" ]; then
        echo -e "${GREEN}✓ Using source directory, no file copy needed${NC}"
        return
    fi
    
    echo -e "${BLUE}Copying files to installation directory...${NC}"
    
    # Check if directory has files
    if [ "$(ls -A $INSTALL_DIR 2>/dev/null)" ]; then
        echo -e "${YELLOW}Warning: Directory is not empty${NC}"
        read -p "Continue and overwrite files? (y/N): " OVERWRITE
        if [[ ! $OVERWRITE =~ ^[Yy]$ ]]; then
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
    fi
    
    # Copy all files except .git directory
    rsync -av --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' \
          --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.ruff_cache' \
          "$PARENT_DIR/" "$INSTALL_DIR/" > /dev/null 2>&1
    
    echo -e "${GREEN}✓ Files copied${NC}"
    echo
}

# Function to prepare installation files
prepare_installation_files() {
    TEMP_DIR=$(mktemp -d)
    echo -e "${BLUE}Preparing installation files...${NC}"

    # Note: Service files will be generated by setup.sh with Vault support if configured
    # These are fallback templates if setup.sh hasn't run yet
    
    # Copy service files from install subdirectory
    cp "$INSTALL_DIR/install/filamentbox.service" "$TEMP_DIR/"
    cp "$INSTALL_DIR/install/filamentbox-webui.service" "$TEMP_DIR/"
    cp "$INSTALL_DIR/install/nginx-filamentbox.conf" "$TEMP_DIR/"
    cp "$INSTALL_DIR/install/install_service.sh" "$TEMP_DIR/"
    cp "$INSTALL_DIR/install/install_webui_service.sh" "$TEMP_DIR/"

    # Update paths in all files
    update_paths_in_file "$TEMP_DIR/filamentbox.service" "$INSTALL_DIR"
    update_paths_in_file "$TEMP_DIR/filamentbox-webui.service" "$INSTALL_DIR"
    update_paths_in_file "$TEMP_DIR/nginx-filamentbox.conf" "$INSTALL_DIR"
    update_paths_in_file "$TEMP_DIR/install_service.sh" "$INSTALL_DIR"
    update_paths_in_file "$TEMP_DIR/install_webui_service.sh" "$INSTALL_DIR"

    # Copy modified files back to install directory
    cp "$TEMP_DIR/filamentbox.service" "$INSTALL_DIR/install/"
    cp "$TEMP_DIR/filamentbox-webui.service" "$INSTALL_DIR/install/"
    cp "$TEMP_DIR/nginx-filamentbox.conf" "$INSTALL_DIR/install/"
    cp "$TEMP_DIR/install_service.sh" "$INSTALL_DIR/install/"
    cp "$TEMP_DIR/install_webui_service.sh" "$INSTALL_DIR/install/"

    # Make scripts executable
    chmod +x "$INSTALL_DIR/install/install_service.sh"
    chmod +x "$INSTALL_DIR/install/install_webui_service.sh"
    chmod +x "$INSTALL_DIR/install/setup.sh"

    echo -e "${GREEN}✓ Installation files prepared${NC}"
    echo
}

# Function to check/setup virtual environment
setup_virtual_environment() {
    echo -e "${BLUE}Checking Python virtual environment...${NC}"
    VENV_DIR="$INSTALL_DIR/filamentcontrol"

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Virtual environment not found${NC}"
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✓ Virtual environment exists${NC}"
    fi

    echo "Installing/updating dependencies..."
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo
}

# Function to configure environment
configure_environment() {
    echo -e "${BLUE}Configuration Setup${NC}"
    echo "═══════════════════"
    echo
    
    # Check if configuration already exists
    if [ -f "$INSTALL_DIR/filamentbox_config.db" ] && [ -f "$INSTALL_DIR/.config_key" ]; then
        echo -e "${GREEN}✓ Encrypted configuration database exists${NC}"
        echo -e "${GREEN}✓ Encryption key file exists${NC}"
        echo
        read -p "Would you like to reconfigure? (y/N): " UPDATE_CONFIG
        if [[ ! $UPDATE_CONFIG =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Keeping existing configuration${NC}"
            echo
            echo -e "${CYAN}To modify configuration anytime, run:${NC}"
            echo -e "  ${CYAN}cd $INSTALL_DIR${NC}"
            echo -e "  ${CYAN}sudo ./install/setup.sh${NC}"
            echo
            return
        fi
    fi
    
    # Run setup script (generates encryption key, configures database, generates service files)
    echo -e "${CYAN}Running configuration setup...${NC}"
    echo
    cd "$INSTALL_DIR"
    if [ -f "$INSTALL_DIR/install/setup.sh" ]; then
        bash "$INSTALL_DIR/install/setup.sh"
    else
        echo -e "${RED}Error: Setup script not found at $INSTALL_DIR/install/setup.sh${NC}"
        echo -e "${YELLOW}You'll need to configure manually using:${NC}"
        echo -e "  ${CYAN}python scripts/config_tool.py --interactive${NC}"
    fi
    echo
}

# Function to install services
install_services() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Installing Services${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo

    # Install main service
    echo -e "${BLUE}Installing main service...${NC}"
    cd "$INSTALL_DIR"
    if ./install/install_service.sh; then
        echo -e "${GREEN}✓ Main service installed${NC}"
    else
        echo -e "${RED}✗ Main service installation failed${NC}"
        return 1
    fi
    echo

    # Install web UI service
    echo -e "${BLUE}Installing web UI service...${NC}"
    if ./install/install_webui_service.sh; then
        echo -e "${GREEN}✓ Web UI service installed${NC}"
    else
        echo -e "${RED}✗ Web UI service installation failed${NC}"
        return 1
    fi
    echo
}

# Function to update services
update_services() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Updating Services${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo

    local services_updated=false

    # Update main service
    if [ "$MAIN_SERVICE_EXISTS" = true ]; then
        echo -e "${BLUE}Updating main service...${NC}"
        
        # Stop service if running
        if [ "$MAIN_SERVICE_RUNNING" = true ]; then
            echo "Stopping service..."
            systemctl stop filamentbox.service
        fi
        
        # Reinstall service
        cd "$INSTALL_DIR"
        if ./install/install_service.sh; then
            echo -e "${GREEN}✓ Main service updated${NC}"
            services_updated=true
            
            # Restart if it was running
            if [ "$MAIN_SERVICE_RUNNING" = true ]; then
                echo "Restarting service..."
                systemctl start filamentbox.service
                sleep 2
                if systemctl is-active --quiet filamentbox.service; then
                    echo -e "${GREEN}✓ Service restarted successfully${NC}"
                else
                    echo -e "${RED}✗ Service failed to restart${NC}"
                    echo "Check logs: sudo journalctl -u filamentbox.service -n 50"
                fi
            fi
        else
            echo -e "${RED}✗ Main service update failed${NC}"
        fi
        echo
    fi

    # Update web UI service
    if [ "$WEBUI_SERVICE_EXISTS" = true ]; then
        echo -e "${BLUE}Updating web UI service...${NC}"
        
        # Stop service if running
        if [ "$WEBUI_SERVICE_RUNNING" = true ]; then
            echo "Stopping service..."
            systemctl stop filamentbox-webui.service
        fi
        
        # Reinstall service
        if ./install/install_webui_service.sh; then
            echo -e "${GREEN}✓ Web UI service updated${NC}"
            services_updated=true
            
            # Restart if it was running
            if [ "$WEBUI_SERVICE_RUNNING" = true ]; then
                echo "Restarting service..."
                systemctl start filamentbox-webui.service
                sleep 2
                if systemctl is-active --quiet filamentbox-webui.service; then
                    echo -e "${GREEN}✓ Service restarted successfully${NC}"
                else
                    echo -e "${RED}✗ Service failed to restart${NC}"
                    echo "Check logs: sudo journalctl -u filamentbox-webui.service -n 50"
                fi
            fi
        else
            echo -e "${RED}✗ Web UI service update failed${NC}"
        fi
        echo
    fi

    if [ "$services_updated" = true ]; then
        echo -e "${GREEN}✓ Services updated successfully${NC}"
    else
        echo -e "${YELLOW}No services were updated${NC}"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

# Function to check service status
check_service_status() {
    local service_name=$1
    
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}✓ $service_name is running${NC}"
        return 0
    else
        echo -e "${RED}✗ $service_name is not running${NC}"
        echo
        echo -e "${YELLOW}Last 20 lines of logs:${NC}"
        journalctl -u "$service_name" -n 20 --no-pager
        return 1
    fi
}

# Function to verify installation
verify_installation() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Verifying Installation${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo

    local main_ok=false
    local webui_ok=false

    check_service_status "filamentbox.service" && main_ok=true
    echo
    check_service_status "filamentbox-webui.service" && webui_ok=true
    echo

    if [ "$main_ok" = true ] && [ "$webui_ok" = true ]; then
        echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ Installation Successful!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo
        echo -e "${BLUE}Service Commands:${NC}"
        echo "  View logs:     sudo journalctl -u filamentbox.service -f"
        echo "                 sudo journalctl -u filamentbox-webui.service -f"
        echo "  Restart:       sudo systemctl restart filamentbox.service"
        echo "                 sudo systemctl restart filamentbox-webui.service"
        echo "  Stop:          sudo systemctl stop filamentbox.service"
        echo "                 sudo systemctl stop filamentbox-webui.service"
        echo
        echo -e "${BLUE}Web UI:${NC}"
        echo "  Access at: http://$(hostname -I | awk '{print $1}'):5000"
        echo
    else
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}Installation completed with errors${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo
        echo "Please check the logs above for details."
    fi
    
    echo
    read -p "Press Enter to continue..."
}

# Function for fresh installation
do_fresh_install() {
    show_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Fresh Installation${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo
    
    select_install_directory
    copy_installation_files
    prepare_installation_files
    setup_virtual_environment
    configure_environment
    install_services
    
    # Reload service detection
    detect_services
    verify_installation
    show_main_menu
}

# Function for configuration only
do_configure_only() {
    show_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Configuration Setup${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo
    
    # Determine installation directory
    if [ "$MAIN_SERVICE_EXISTS" = true ]; then
        INSTALL_DIR=$(get_install_dir_from_service)
        if [ -z "$INSTALL_DIR" ]; then
            select_install_directory
        else
            echo -e "Using installation directory: ${CYAN}$INSTALL_DIR${NC}"
            echo
        fi
    else
        select_install_directory
    fi
    
    configure_environment
    
    echo -e "${GREEN}✓ Configuration complete${NC}"
    echo
    
    if [ "$MAIN_SERVICE_RUNNING" = true ] || [ "$WEBUI_SERVICE_RUNNING" = true ]; then
        read -p "Would you like to restart services to apply changes? (y/N): " RESTART
        if [[ $RESTART =~ ^[Yy]$ ]]; then
            if [ "$MAIN_SERVICE_RUNNING" = true ]; then
                systemctl restart filamentbox.service
                echo -e "${GREEN}✓ Main service restarted${NC}"
            fi
            if [ "$WEBUI_SERVICE_RUNNING" = true ]; then
                systemctl restart filamentbox-webui.service
                echo -e "${GREEN}✓ Web UI service restarted${NC}"
            fi
        fi
    fi
    
    echo
    read -p "Press Enter to continue..."
    show_main_menu
}

# Function for service update
do_service_update() {
    show_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Service Update${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo
    
    INSTALL_DIR=$(get_install_dir_from_service)
    if [ -z "$INSTALL_DIR" ]; then
        echo -e "${RED}Could not detect installation directory${NC}"
        read -p "Press Enter to continue..."
        show_main_menu
        return
    fi
    
    echo -e "Installation directory: ${CYAN}$INSTALL_DIR${NC}"
    echo
    
    copy_installation_files
    prepare_installation_files
    setup_virtual_environment
    update_services
    
    # Reload service detection
    detect_services
    show_main_menu
}

# Function to view logs
do_view_logs() {
    show_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Service Logs${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo
    echo "Which logs would you like to view?"
    echo
    echo "  1) Main Service (filamentbox)"
    echo "  2) Web UI Service (filamentbox-webui)"
    echo "  3) Both"
    echo "  4) Back to menu"
    echo
    read -p "Enter choice (1-4): " LOG_CHOICE
    
    case ${LOG_CHOICE} in
        1)
            echo
            echo -e "${BLUE}Last 50 lines of main service:${NC}"
            journalctl -u filamentbox.service -n 50 --no-pager
            ;;
        2)
            echo
            echo -e "${BLUE}Last 50 lines of web UI service:${NC}"
            journalctl -u filamentbox-webui.service -n 50 --no-pager
            ;;
        3)
            echo
            echo -e "${BLUE}Last 50 lines of main service:${NC}"
            journalctl -u filamentbox.service -n 50 --no-pager
            echo
            echo -e "${BLUE}Last 50 lines of web UI service:${NC}"
            journalctl -u filamentbox-webui.service -n 50 --no-pager
            ;;
        4)
            show_main_menu
            return
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
    show_main_menu
}

# Main execution
detect_services
show_main_menu
