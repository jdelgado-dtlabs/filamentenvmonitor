#!/bin/bash
# install_service.sh - Install FilamentBox as a systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/filamentbox.service"
SERVICE_NAME="filamentbox.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "FilamentBox Service Installer"
echo "=============================="
echo

# Check if running with sudo/root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run with sudo or as root."
    echo "Usage: sudo ./install_service.sh"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Check if run_filamentbox.py is executable
if [ ! -x "$SCRIPT_DIR/run_filamentbox.py" ]; then
    echo "Making run_filamentbox.py executable..."
    chmod +x "$SCRIPT_DIR/run_filamentbox.py"
fi

# Copy service file
echo "Installing service file to $SYSTEMD_DIR/$SERVICE_NAME..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

echo
echo "Service installed successfully!"
echo
echo "To start the service now:"
echo "  sudo systemctl start $SERVICE_NAME"
echo
echo "To check service status:"
echo "  sudo systemctl status $SERVICE_NAME"
echo
echo "To view logs:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo
echo "To stop the service:"
echo "  sudo systemctl stop $SERVICE_NAME"
echo
echo "To disable service from starting on boot:"
echo "  sudo systemctl disable $SERVICE_NAME"
echo
