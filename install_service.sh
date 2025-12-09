#!/bin/bash
# install_service.sh - Install 3D Printer Filament Storage Environment Monitor as a systemd service

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/filamentbox.service"
SERVICE_NAME="filamentbox.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=============================="
echo "3D Printer Filament Storage Environment Monitor"
echo "Service Installer"
echo "=============================="
echo

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

# Check if run_filamentbox.py is executable
if [ ! -x "$SCRIPT_DIR/run_filamentbox.py" ]; then
    echo "Making run_filamentbox.py executable..."
    chmod +x "$SCRIPT_DIR/run_filamentbox.py"
    echo -e "${GREEN}✓ Made run_filamentbox.py executable${NC}"
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

# Copy service file
echo "Installing service file to $SYSTEMD_DIR/$SERVICE_NAME..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME"
echo -e "${GREEN}✓ Service file installed${NC}"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Enable service
echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"
echo -e "${GREEN}✓ Service enabled${NC}"

echo
echo -e "${GREEN}=============================="
echo "Installation Complete!"
echo "==============================${NC}"
echo
echo "Service Management Commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo
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
echo
