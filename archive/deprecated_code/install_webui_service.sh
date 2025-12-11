#!/bin/bash
# Installer script for FilamentBox Web UI systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# File paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/filamentbox-webui.service"
INSTALLED_SERVICE="/etc/systemd/system/filamentbox-webui.service"

# Extract version from service file
get_service_version() {
    local file=$1
    grep "^# Version:" "$file" 2>/dev/null | awk '{print $3}'
}

# Compare version numbers (returns 0 if v1 > v2, 1 if v1 <= v2)
version_greater() {
    local v1=$1
    local v2=$2
    
    # If either version is empty, assume update needed
    [ -z "$v1" ] && return 1
    [ -z "$v2" ] && return 0
    
    # Compare versions using sort -V
    if [ "$(printf '%s\n' "$v1" "$v2" | sort -V | head -n1)" = "$v2" ] && [ "$v1" != "$v2" ]; then
        return 0
    else
        return 1
    fi
}

echo -e "${GREEN}FilamentBox Web UI Service Installer${NC}"
echo "======================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install_webui_service.sh"
    exit 1
fi

# Check for existing service and version
SERVICE_RUNNING=false
NEED_UPDATE=false
CURRENT_VERSION=""
NEW_VERSION=$(get_service_version "$SERVICE_FILE")

if [ -f "$INSTALLED_SERVICE" ]; then
    CURRENT_VERSION=$(get_service_version "$INSTALLED_SERVICE")
    echo -e "${BLUE}Existing service found${NC}"
    echo "  Installed version: ${CURRENT_VERSION:-unknown}"
    echo "  New version:       ${NEW_VERSION:-unknown}"
    echo
    
    if systemctl is-active --quiet filamentbox-webui.service; then
        SERVICE_RUNNING=true
        echo -e "${GREEN}Service is currently running${NC}"
    else
        echo -e "${YELLOW}Service is installed but not running${NC}"
    fi
    
    if version_greater "$NEW_VERSION" "$CURRENT_VERSION"; then
        NEED_UPDATE=true
        echo -e "${YELLOW}Update available!${NC}"
        echo
        read -p "Would you like to update the service? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
            echo "Update cancelled."
            exit 0
        fi
    else
        echo -e "${GREEN}Service is up to date${NC}"
        echo
        read -p "Reinstall anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
    fi
    echo
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

# Stop service if running and updating
if [ "$SERVICE_RUNNING" = true ] && [ "$NEED_UPDATE" = true ]; then
    echo "Stopping service for update..."
    systemctl stop filamentbox-webui.service
    echo -e "${GREEN}✓ Service stopped${NC}"
    echo
fi

# Copy service file
echo "Installing systemd service file..."
cp "$SERVICE_FILE" "$INSTALLED_SERVICE"
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
if [ "$NEED_UPDATE" = true ]; then
    echo -e "${GREEN}Update complete!${NC}"
else
    echo -e "${GREEN}Installation complete!${NC}"
fi
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

# Handle service restart for updates or initial start
if [ "$NEED_UPDATE" = true ] && [ "$SERVICE_RUNNING" = true ]; then
    echo "Service was running before update."
    read -p "Would you like to restart the service now? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        systemctl restart filamentbox-webui.service
        echo -e "${GREEN}✓ Service restarted${NC}"
        echo
        echo "Checking service status..."
        sleep 2
        systemctl status filamentbox-webui.service --no-pager
    else
        echo
        echo -e "${YELLOW}Service not restarted. To apply changes, run:${NC}"
        echo "  sudo systemctl restart filamentbox-webui.service"
    fi
elif [ "$SERVICE_RUNNING" = false ]; then
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
fi

# Nginx configuration section
echo
echo "======================================="
echo -e "${GREEN}Nginx Reverse Proxy Configuration${NC}"
echo "======================================="
echo
read -p "Is nginx installed on this machine? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo
    echo "How is nginx installed?"
    echo "  1) Bare metal (native installation)"
    echo "  2) Docker container"
    read -p "Enter choice (1 or 2): " -n 1 -r NGINX_TYPE
    echo
    echo

    if [[ $NGINX_TYPE == "2" ]]; then
        # Docker installation
        echo -e "${YELLOW}Docker nginx detected${NC}"
        echo
        read -p "Enter the path to nginx config folder (e.g., /path/to/nginx/conf.d): " NGINX_CONFIG_PATH
        
        if [ ! -d "$NGINX_CONFIG_PATH" ]; then
            echo -e "${RED}Error: Directory $NGINX_CONFIG_PATH does not exist${NC}"
            echo "Skipping nginx configuration."
        else
            NGINX_CONF_FILE="$NGINX_CONFIG_PATH/filamentbox.conf"
            
            echo "Installing nginx configuration to: $NGINX_CONF_FILE"
            cp "$SCRIPT_DIR/nginx-filamentbox.conf" "$NGINX_CONF_FILE"
            echo -e "${GREEN}✓ Nginx configuration copied${NC}"
            echo
            
            read -p "Would you like to modify the configuration now? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "Opening configuration in editor..."
                ${EDITOR:-nano} "$NGINX_CONF_FILE"
                echo -e "${GREEN}✓ Configuration edited${NC}"
            fi
            
            echo
            echo -e "${YELLOW}Docker nginx configuration installed.${NC}"
            echo "To apply changes, restart your nginx container:"
            echo "  docker restart <nginx-container-name>"
            echo "Or if using docker-compose:"
            echo "  docker-compose restart nginx"
        fi
        
    elif [[ $NGINX_TYPE == "1" ]]; then
        # Bare metal installation
        echo -e "${YELLOW}Bare metal nginx detected${NC}"
        echo
        
        # Check for default nginx directories
        SITES_AVAILABLE="/etc/nginx/sites-available"
        SITES_ENABLED="/etc/nginx/sites-enabled"
        CONF_D="/etc/nginx/conf.d"
        
        NGINX_INSTALL_PATH=""
        
        if [ -d "$SITES_AVAILABLE" ]; then
            echo "Found nginx sites-available directory: $SITES_AVAILABLE"
            read -p "Install configuration to $SITES_AVAILABLE? (Y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                NGINX_INSTALL_PATH="$SITES_AVAILABLE"
            fi
        elif [ -d "$CONF_D" ]; then
            echo "Found nginx conf.d directory: $CONF_D"
            read -p "Install configuration to $CONF_D? (Y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                NGINX_INSTALL_PATH="$CONF_D"
            fi
        fi
        
        # If no default found or user declined, ask for custom path
        if [ -z "$NGINX_INSTALL_PATH" ]; then
            echo "No default nginx directory found or declined."
            read -p "Enter the path where nginx configuration should be placed: " NGINX_INSTALL_PATH
            
            if [ ! -d "$NGINX_INSTALL_PATH" ]; then
                echo -e "${RED}Error: Directory $NGINX_INSTALL_PATH does not exist${NC}"
                echo "Skipping nginx configuration."
                NGINX_INSTALL_PATH=""
            fi
        fi
        
        if [ -n "$NGINX_INSTALL_PATH" ]; then
            NGINX_CONF_FILE="$NGINX_INSTALL_PATH/filamentbox.conf"
            
            echo "Installing nginx configuration to: $NGINX_CONF_FILE"
            cp "$SCRIPT_DIR/nginx-filamentbox.conf" "$NGINX_CONF_FILE"
            echo -e "${GREEN}✓ Nginx configuration copied${NC}"
            
            # Enable site if using sites-available structure
            if [[ "$NGINX_INSTALL_PATH" == "$SITES_AVAILABLE" ]] && [ -d "$SITES_ENABLED" ]; then
                if [ ! -L "$SITES_ENABLED/filamentbox.conf" ]; then
                    echo "Enabling site..."
                    ln -s "$NGINX_CONF_FILE" "$SITES_ENABLED/filamentbox.conf"
                    echo -e "${GREEN}✓ Site enabled${NC}"
                else
                    echo -e "${YELLOW}Site already enabled${NC}"
                fi
            fi
            
            echo
            read -p "Would you like to modify the configuration now? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "Opening configuration in editor..."
                ${EDITOR:-nano} "$NGINX_CONF_FILE"
                echo -e "${GREEN}✓ Configuration edited${NC}"
            fi
            
            # Test nginx configuration
            echo
            echo "Testing nginx configuration..."
            if nginx -t 2>/dev/null; then
                echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
                
                echo
                read -p "Would you like to gracefully restart nginx now? (Y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                    echo "Restarting nginx..."
                    systemctl reload nginx
                    echo -e "${GREEN}✓ Nginx reloaded successfully${NC}"
                    echo
                    echo "Web UI should now be accessible at:"
                    echo "  http://$(hostname -I | awk '{print $1}')"
                else
                    echo
                    echo -e "${YELLOW}Nginx not restarted.${NC}"
                    echo "To apply changes, run:"
                    echo "  sudo systemctl reload nginx"
                fi
            else
                echo -e "${RED}Nginx configuration test failed!${NC}"
                echo "Please check the configuration and run:"
                echo "  sudo nginx -t"
                echo "To reload nginx after fixing:"
                echo "  sudo systemctl reload nginx"
            fi
        fi
    else
        echo -e "${YELLOW}Invalid choice. Skipping nginx configuration.${NC}"
    fi
else
    echo
    echo -e "${YELLOW}Nginx not installed or declined.${NC}"
    echo "You can manually configure a reverse proxy later using nginx-filamentbox.conf"
fi
