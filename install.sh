#!/bin/bash
# FilamentBox Complete Installation Script
# Handles directory setup, service installation, and verification

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default installation directory
DEFAULT_INSTALL_DIR="/opt/filamentcontrol"

# Installation directory (will be set by user)
INSTALL_DIR=""

# Temporary directory for modified files
TEMP_DIR=""

echo
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║         FilamentBox Environment Monitor Installer          ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install.sh"
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

# Function to check service status and show logs if failed
check_service_status() {
    local service_name=$1
    
    echo
    echo -e "${BLUE}Checking $service_name status...${NC}"
    
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}✓ $service_name is running${NC}"
        return 0
    else
        echo -e "${RED}✗ $service_name failed to start${NC}"
        echo
        echo -e "${YELLOW}Last 20 lines of logs:${NC}"
        journalctl -u "$service_name" -n 20 --no-pager
        return 1
    fi
}

# Ask user for installation directory
echo -e "${GREEN}Installation Directory Selection${NC}"
echo "════════════════════════════════"
echo
echo "Where would you like to install FilamentBox?"
echo
echo "  1) Default location: $DEFAULT_INSTALL_DIR"
echo "  2) Current directory: $SCRIPT_DIR"
echo "  3) Custom directory"
echo
read -p "Enter choice (1-3) [1]: " DIR_CHOICE

case ${DIR_CHOICE:-1} in
    1)
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        echo -e "${GREEN}Using default directory: $INSTALL_DIR${NC}"
        ;;
    2)
        INSTALL_DIR="$SCRIPT_DIR"
        echo -e "${GREEN}Using current directory: $INSTALL_DIR${NC}"
        ;;
    3)
        read -p "Enter custom directory path: " CUSTOM_DIR
        INSTALL_DIR="${CUSTOM_DIR%/}"  # Remove trailing slash
        echo -e "${GREEN}Using custom directory: $INSTALL_DIR${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Using default.${NC}"
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        ;;
esac

echo

# Ensure installation directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Installation directory doesn't exist${NC}"
    read -p "Create directory $INSTALL_DIR? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        mkdir -p "$INSTALL_DIR"
        echo -e "${GREEN}✓ Directory created: $INSTALL_DIR${NC}"
    else
        echo -e "${RED}Installation cancelled.${NC}"
        exit 1
    fi
    echo
fi

# If not installing to script directory, ask to copy files
if [ "$INSTALL_DIR" != "$SCRIPT_DIR" ]; then
    echo -e "${YELLOW}Files will be copied from:${NC} $SCRIPT_DIR"
    echo -e "${YELLOW}                       to:${NC} $INSTALL_DIR"
    echo
    
    # Check if directory is empty or has files
    if [ "$(ls -A $INSTALL_DIR 2>/dev/null)" ]; then
        echo -e "${YELLOW}Warning: Directory is not empty${NC}"
        read -p "Continue and overwrite files? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
    fi
    
    echo
    echo -e "${BLUE}Copying files to installation directory...${NC}"
    
    # Copy all files except .git directory
    rsync -av --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' \
          --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.ruff_cache' \
          "$SCRIPT_DIR/" "$INSTALL_DIR/"
    
    echo -e "${GREEN}✓ Files copied${NC}"
fi

# Create temporary directory for modified service files
TEMP_DIR=$(mktemp -d)
echo
echo -e "${BLUE}Preparing installation files...${NC}"

# Copy and update service files
cp "$INSTALL_DIR/filamentbox.service" "$TEMP_DIR/"
cp "$INSTALL_DIR/filamentbox-webui.service" "$TEMP_DIR/"
cp "$INSTALL_DIR/nginx-filamentbox.conf" "$TEMP_DIR/"
cp "$INSTALL_DIR/install_service.sh" "$TEMP_DIR/"
cp "$INSTALL_DIR/install_webui_service.sh" "$TEMP_DIR/"

# Update paths in all files
update_paths_in_file "$TEMP_DIR/filamentbox.service" "$INSTALL_DIR"
update_paths_in_file "$TEMP_DIR/filamentbox-webui.service" "$INSTALL_DIR"
update_paths_in_file "$TEMP_DIR/nginx-filamentbox.conf" "$INSTALL_DIR"
update_paths_in_file "$TEMP_DIR/install_service.sh" "$INSTALL_DIR"
update_paths_in_file "$TEMP_DIR/install_webui_service.sh" "$INSTALL_DIR"

# Copy modified files back
cp "$TEMP_DIR/filamentbox.service" "$INSTALL_DIR/"
cp "$TEMP_DIR/filamentbox-webui.service" "$INSTALL_DIR/"
cp "$TEMP_DIR/nginx-filamentbox.conf" "$INSTALL_DIR/"
cp "$TEMP_DIR/install_service.sh" "$INSTALL_DIR/"
cp "$TEMP_DIR/install_webui_service.sh" "$INSTALL_DIR/"

# Make installers executable
chmod +x "$INSTALL_DIR/install_service.sh"
chmod +x "$INSTALL_DIR/install_webui_service.sh"

echo -e "${GREEN}✓ Installation files prepared${NC}"

# Check for virtual environment
echo
echo -e "${BLUE}Checking Python virtual environment...${NC}"
VENV_DIR="$INSTALL_DIR/filamentcontrol"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
    
    echo "Installing dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
    
    read -p "Update dependencies? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Updating dependencies..."
        "$VENV_DIR/bin/pip" install --upgrade pip
        "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
        echo -e "${GREEN}✓ Dependencies updated${NC}"
    fi
fi

# Check for configuration file
echo
echo -e "${BLUE}Checking configuration...${NC}"

if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    echo -e "${YELLOW}config.yaml not found${NC}"
    if [ -f "$INSTALL_DIR/config.yaml.example" ]; then
        echo "Creating config.yaml from example..."
        cp "$INSTALL_DIR/config.yaml.example" "$INSTALL_DIR/config.yaml"
        echo -e "${GREEN}✓ config.yaml created${NC}"
        echo -e "${YELLOW}Note: Please edit config.yaml with your settings${NC}"
    else
        echo -e "${RED}Warning: No configuration file found${NC}"
        echo "You'll need to create config.yaml before running the service"
    fi
else
    echo -e "${GREEN}✓ config.yaml exists${NC}"
fi

if [ ! -f "$INSTALL_DIR/.env" ]; then
    if [ -f "$INSTALL_DIR/.env.example" ]; then
        echo "Creating .env from example..."
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        echo -e "${GREEN}✓ .env created${NC}"
        echo -e "${YELLOW}Note: Please edit .env with your settings${NC}"
    fi
fi

# Install main service
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Installing Main Service${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo

cd "$INSTALL_DIR"
if ! ./install_service.sh; then
    echo -e "${RED}Main service installation failed${NC}"
    exit 1
fi

# Install web UI service
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Installing Web UI Service${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo

cd "$INSTALL_DIR"
if ! ./install_webui_service.sh; then
    echo -e "${RED}Web UI service installation failed${NC}"
    exit 1
fi

# Final status check
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Installation Complete - Verifying Services${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

MAIN_SERVICE_OK=false
WEBUI_SERVICE_OK=false

# Wait a moment for services to fully start
sleep 3

# Check main service
check_service_status "filamentbox.service" && MAIN_SERVICE_OK=true

# Check web UI service
check_service_status "filamentbox-webui.service" && WEBUI_SERVICE_OK=true

# Final summary
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Installation Summary${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo
echo -e "Installation Directory: ${GREEN}$INSTALL_DIR${NC}"
echo
echo "Service Status:"
if [ "$MAIN_SERVICE_OK" = true ]; then
    echo -e "  Main Service:   ${GREEN}✓ Running${NC}"
else
    echo -e "  Main Service:   ${RED}✗ Failed${NC}"
fi

if [ "$WEBUI_SERVICE_OK" = true ]; then
    echo -e "  Web UI Service: ${GREEN}✓ Running${NC}"
else
    echo -e "  Web UI Service: ${RED}✗ Failed${NC}"
fi

echo
echo "Access Points:"
echo "  Web UI (direct):  http://localhost:5000"
echo "  Web UI (network): http://$(hostname -I | awk '{print $1}'):5000"

if [ -f "/etc/nginx/sites-enabled/filamentbox.conf" ] || [ -f "/etc/nginx/conf.d/filamentbox.conf" ]; then
    echo "  Web UI (nginx):   http://$(hostname -I | awk '{print $1}')"
fi

echo
echo "Service Management:"
echo "  Main service:  sudo systemctl {start|stop|restart|status} filamentbox.service"
echo "  Web UI:        sudo systemctl {start|stop|restart|status} filamentbox-webui.service"
echo
echo "View Logs:"
echo "  Main service:  sudo journalctl -u filamentbox.service -f"
echo "  Web UI:        sudo journalctl -u filamentbox-webui.service -f"
echo
echo "Configuration Files:"
echo "  Main config:   $INSTALL_DIR/config.yaml"
echo "  Environment:   $INSTALL_DIR/.env"
echo

if [ "$MAIN_SERVICE_OK" = true ] && [ "$WEBUI_SERVICE_OK" = true ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║        Installation completed successfully! 🎉             ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                                                            ║${NC}"
    echo -e "${YELLOW}║  Installation completed with warnings                     ║${NC}"
    echo -e "${YELLOW}║  Please check the logs above for errors                   ║${NC}"
    echo -e "${YELLOW}║                                                            ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
