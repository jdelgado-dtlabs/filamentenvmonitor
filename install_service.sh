#!/bin/bash
# install_service.sh - Install 3D Printer Filament Storage Environment Monitor as a systemd service

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/filamentbox.service"
SERVICE_NAME="filamentbox.service"
SYSTEMD_DIR="/etc/systemd/system"
INSTALLED_SERVICE="$SYSTEMD_DIR/$SERVICE_NAME"

echo "=============================="
echo "3D Printer Filament Storage Environment Monitor"
echo "Service Installer"
echo "=============================="
echo

# Get version from service file comment or WorkingDirectory
get_service_version() {
    local service_file=$1
    # Try to extract version from a comment in the service file
    # Format: # Version: x.y.z
    if [ -f "$service_file" ]; then
        version=$(grep -oP '(?<=# Version: )[\d.]+' "$service_file" 2>/dev/null || echo "")
        if [ -z "$version" ]; then
            # Fallback: use file modification time as version indicator
            stat -c %Y "$service_file" 2>/dev/null || echo "0"
        else
            echo "$version"
        fi
    else
        echo "0"
    fi
}

# Compare service files
files_differ() {
    if [ ! -f "$INSTALLED_SERVICE" ]; then
        return 0  # No installed service, so they differ
    fi
    
    # Compare files ignoring comments and whitespace
    diff -wB <(grep -v '^#' "$SERVICE_FILE" | grep -v '^$') \
             <(grep -v '^#' "$INSTALLED_SERVICE" | grep -v '^$') &>/dev/null
    return $?
}

# Detect OS type
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME=$NAME
        OS_ID=$ID
        OS_ID_LIKE=$ID_LIKE
    elif [ -f /etc/redhat-release ]; then
        OS_NAME="RedHat/CentOS"
        OS_ID="rhel"
    elif [ -f /etc/debian_version ]; then
        OS_NAME="Debian/Ubuntu"
        OS_ID="debian"
    else
        OS_NAME="Unknown"
        OS_ID="unknown"
    fi
    
    echo -e "${GREEN}Detected OS: $OS_NAME${NC}"
    echo
}

# Check if running with sudo/root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run with sudo or as root.${NC}"
    echo "Usage: sudo ./install_service.sh"
    exit 1
fi

# Detect operating system
detect_os

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}Error: Service file not found at $SERVICE_FILE${NC}"
    exit 1
fi

# Check Python virtual environment
VENV_PATH="$SCRIPT_DIR/filamentcontrol"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Warning: Python virtual environment not found at $VENV_PATH${NC}"
    echo "Make sure to set up the virtual environment before starting the service."
    echo
fi

# Check for required Python packages based on OS
check_system_packages() {
    echo "Checking system dependencies..."
    
    case "$OS_ID" in
        debian|ubuntu|raspbian)
            MISSING_PACKAGES=()
            
            # Check for Python development headers
            if ! dpkg -l | grep -q python3-dev; then
                MISSING_PACKAGES+=("python3-dev")
            fi
            
            # Check for GPIO libraries (for Raspberry Pi)
            if ! dpkg -l | grep -q python3-lgpio 2>/dev/null; then
                if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
                    MISSING_PACKAGES+=("python3-lgpio")
                fi
            fi
            
            if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
                echo -e "${YELLOW}Missing system packages: ${MISSING_PACKAGES[*]}${NC}"
                read -p "Would you like to install missing packages now? (Y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                    apt update
                    apt install -y "${MISSING_PACKAGES[@]}"
                    echo -e "${GREEN}✓ System packages installed${NC}"
                else
                    echo -e "${YELLOW}Warning: Missing packages may cause issues. Install manually:${NC}"
                    echo "  sudo apt install ${MISSING_PACKAGES[*]}"
                fi
            else
                echo -e "${GREEN}✓ All required system packages are installed${NC}"
            fi
            ;;
            
        rhel|centos|fedora)
            MISSING_PACKAGES=()
            
            # Check for Python development headers
            if ! rpm -q python3-devel &>/dev/null; then
                MISSING_PACKAGES+=("python3-devel")
            fi
            
            if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
                echo -e "${YELLOW}Missing system packages: ${MISSING_PACKAGES[*]}${NC}"
                read -p "Would you like to install missing packages now? (Y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                    if command -v dnf &>/dev/null; then
                        dnf install -y "${MISSING_PACKAGES[@]}"
                    else
                        yum install -y "${MISSING_PACKAGES[@]}"
                    fi
                    echo -e "${GREEN}✓ System packages installed${NC}"
                else
                    echo -e "${YELLOW}Warning: Missing packages may cause issues. Install manually:${NC}"
                    echo "  sudo yum install ${MISSING_PACKAGES[*]}"
                fi
            else
                echo -e "${GREEN}✓ All required system packages are installed${NC}"
            fi
            ;;
            
        *)
            echo -e "${YELLOW}Unknown OS type. Skipping system package checks.${NC}"
            echo "Make sure you have Python development headers installed."
            ;;
    esac
    echo
}

# Run system package checks
check_system_packages

# Check if service is already installed
SERVICE_RUNNING=false
SERVICE_EXISTS=false

if [ -f "$INSTALLED_SERVICE" ]; then
    SERVICE_EXISTS=true
    echo -e "${BLUE}Existing service detected${NC}"
    
    # Check if service is running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        SERVICE_RUNNING=true
        echo -e "${YELLOW}Service is currently running${NC}"
    else
        echo "Service is not running"
    fi
    
    # Check if files differ
    if files_differ; then
        echo -e "${YELLOW}Service file has changes${NC}"
        
        # Show what changed
        echo
        echo "Changes detected:"
        diff -u <(grep -v '^#' "$INSTALLED_SERVICE" | grep -v '^$') \
                <(grep -v '^#' "$SERVICE_FILE" | grep -v '^$') || true
        echo
        
        read -p "Would you like to update the service? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
        
        UPDATING=true
    else
        echo -e "${GREEN}Service file is up to date${NC}"
        UPDATING=false
        
        read -p "Service is already installed and up to date. Reinstall anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
        UPDATING=true
    fi
else
    echo "No existing service found. Performing fresh installation."
    UPDATING=false
fi

echo

# Copy service file
if [ "$UPDATING" = true ] && [ "$SERVICE_RUNNING" = true ]; then
    echo "Updating service file..."
else
    echo "Installing service file to $SYSTEMD_DIR/$SERVICE_NAME..."
fi

cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME"
echo -e "${GREEN}✓ Service file installed${NC}"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Enable service if not already enabled
if ! systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "Enabling service to start on boot..."
    systemctl enable "$SERVICE_NAME"
    echo -e "${GREEN}✓ Service enabled${NC}"
else
    echo -e "${GREEN}✓ Service already enabled${NC}"
fi

echo
echo -e "${GREEN}=============================="
if [ "$SERVICE_EXISTS" = true ]; then
    echo "Update Complete!"
else
    echo "Installation Complete!"
fi
echo "==============================${NC}"
echo
echo "Service Management Commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo

# Handle service restart/start
if [ "$SERVICE_RUNNING" = true ]; then
    echo -e "${YELLOW}Service is currently running and needs to be restarted to apply changes.${NC}"
    read -p "Would you like to gracefully restart the service now? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        echo "Gracefully restarting service..."
        systemctl restart "$SERVICE_NAME"
        echo -e "${GREEN}✓ Service restarted${NC}"
        echo
        echo "Checking service status..."
        sleep 2
        systemctl status "$SERVICE_NAME" --no-pager
    else
        echo
        echo -e "${YELLOW}Service not restarted.${NC}"
        echo "To apply changes, restart the service:"
        echo "  sudo systemctl restart $SERVICE_NAME"
    fi
elif [ "$SERVICE_EXISTS" = true ]; then
    read -p "Would you like to start the service now? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        systemctl start "$SERVICE_NAME"
        echo -e "${GREEN}✓ Service started${NC}"
        echo
        echo "Checking service status..."
        sleep 2
        systemctl status "$SERVICE_NAME" --no-pager
    else
        echo
        echo "Service not started."
        echo "To start it later, run:"
        echo "  sudo systemctl start $SERVICE_NAME"
    fi
else
    read -p "Would you like to start the service now? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        systemctl start "$SERVICE_NAME"
        echo -e "${GREEN}✓ Service started${NC}"
        echo
        echo "Checking service status..."
        sleep 2
        systemctl status "$SERVICE_NAME" --no-pager
    else
        echo
        echo "Service installed but not started."
        echo "To start it later, run:"
        echo "  sudo systemctl start $SERVICE_NAME"
    fi
fi
echo
