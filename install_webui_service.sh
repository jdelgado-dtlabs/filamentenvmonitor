#!/bin/bash
# Installer script for FilamentBox Web UI systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}FilamentBox Web UI Service Installer${NC}"
echo "======================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install_webui_service.sh"
    exit 1
fi

# Check if main service is installed
if [ ! -f "/etc/systemd/system/filamentbox.service" ]; then
    echo -e "${YELLOW}Warning: Main filamentbox.service not found${NC}"
    echo "The web UI requires the main application to be running."
    echo "Consider installing it first with: sudo ./install_service.sh"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if Flask is installed
VENV_PYTHON="/opt/filamentcontrol/filamentcontrol/bin/python"
if ! $VENV_PYTHON -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}Flask is not installed in the virtual environment${NC}"
    echo "Installing Flask and Flask-CORS..."
    /opt/filamentcontrol/filamentcontrol/bin/pip install Flask Flask-CORS
    echo -e "${GREEN}✓ Flask dependencies installed${NC}"
    echo
fi

# Copy service file
echo "Installing systemd service file..."
cp filamentbox-webui.service /etc/systemd/system/
echo -e "${GREEN}✓ Service file copied to /etc/systemd/system/${NC}"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Enable service
echo "Enabling filamentbox-webui service..."
systemctl enable filamentbox-webui.service
echo -e "${GREEN}✓ Service enabled${NC}"

echo
echo -e "${GREEN}Installation complete!${NC}"
echo
echo "Service Management Commands:"
echo "  Start:   sudo systemctl start filamentbox-webui.service"
echo "  Stop:    sudo systemctl stop filamentbox-webui.service"
echo "  Restart: sudo systemctl restart filamentbox-webui.service"
echo "  Status:  sudo systemctl status filamentbox-webui.service"
echo "  Logs:    sudo journalctl -u filamentbox-webui.service -f"
echo
echo "Web UI will be available at:"
echo "  http://localhost:5000"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo
echo -e "${YELLOW}Note: The main filamentbox.service must be running for the web UI to display data.${NC}"
echo
read -p "Would you like to start the service now? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    systemctl start filamentbox-webui.service
    echo -e "${GREEN}✓ Service started${NC}"
    echo
    echo "Checking service status..."
    sleep 2
    systemctl status filamentbox-webui.service --no-pager
fi
