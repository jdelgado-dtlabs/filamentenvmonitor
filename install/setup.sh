#!/bin/bash
# FilamentBox Configuration Management Script
# v2.0+ - Encrypted Configuration Database
#
# This script manages encrypted configuration setup and updates.
# Run install.sh for fresh installations or updates.
# Run this script directly to reconfigure an existing installation.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory and installation root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DB="$INSTALL_ROOT/filamentbox_config.db"
CONFIG_YAML="$INSTALL_ROOT/config.yaml"
ENV_FILE="$INSTALL_ROOT/.env"
KEY_FILE="$INSTALL_ROOT/.config_key"

# ========================================
# Function Definitions
# ========================================

ask_yes_no() {
    local prompt="$1"
    local default="${2:-Y}" # Default to Yes if not specified
    
    if [[ "$default" =~ ^[Yy]$ ]]; then
        read -p "$prompt [Y/n]: " response
        [[ ! "$response" =~ ^[Nn]$ ]]
    else
        read -p "$prompt [y/N]: " response
        [[ "$response" =~ ^[Yy]$ ]]
    fi
}

# Function to generate a strong encryption key
generate_encryption_key() {
    # Generate a 64-character random key using /dev/urandom
    # Uses base64 encoding for URL-safe characters
    ENCRYPTION_KEY=$(head -c 48 /dev/urandom | base64 | tr -d '\n' | tr -d '=' | head -c 64)
}

# Function to check if Vault is available and configured
check_vault_available() {
    # Check if hvac (Vault Python library) is installed
    if ! "$INSTALL_ROOT/filamentcontrol/bin/python" -c "import hvac" 2>/dev/null; then
        return 1
    fi
    
    # Check if VAULT_ADDR is set
    if [ -z "$VAULT_ADDR" ]; then
        return 1
    fi
    
    # Check if authentication is configured (token or approle)
    if [ -n "$VAULT_TOKEN" ] || ([ -n "$VAULT_ROLE_ID" ] && [ -n "$VAULT_SECRET_ID" ]); then
        return 0
    fi
    
    return 1
}

# Function to configure Vault interactively
configure_vault_interactive() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}HashiCorp Vault Configuration${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${CYAN}HashiCorp Vault provides enterprise-grade secret management.${NC}"
    echo ""
    
    # Ask if user wants to use Vault
    if ! ask_yes_no "Do you have a HashiCorp Vault server available?" "N"; then
        echo ""
        echo -e "${YELLOW}⚠ Vault not configured${NC}"
        echo -e "${YELLOW}The encryption key will be stored in a local file:${NC}"
        echo -e "${YELLOW}  $KEY_FILE${NC}"
        echo -e "${YELLOW}  (Permissions: 600 - owner read/write only)${NC}"
        echo ""
        echo -e "${CYAN}For enhanced security in production, consider using HashiCorp Vault.${NC}"
        echo -e "${CYAN}See: docs/VAULT_INTEGRATION.md${NC}"
        echo ""
        return 1
    fi
    
    echo ""
    echo -e "${GREEN}Great! Let's configure Vault access.${NC}"
    echo ""
    
    # Check if hvac is installed
    if ! "$INSTALL_ROOT/filamentcontrol/bin/python" -c "import hvac" 2>/dev/null; then
        echo -e "${YELLOW}HashiCorp Vault Python library (hvac) not installed.${NC}"
        echo ""
        if ask_yes_no "Install hvac library now?" "Y"; then
            "$INSTALL_ROOT/filamentcontrol/bin/pip" install hvac
            echo ""
        else
            echo -e "${RED}Cannot use Vault without hvac library.${NC}"
            echo -e "${YELLOW}Falling back to local file storage.${NC}"
            echo ""
            return 1
        fi
    fi
    
    # Get Vault address
    echo -e "${CYAN}Vault Server Configuration${NC}"
    echo ""
    read -p "Vault server address (e.g., https://vault.example.com:8200): " vault_addr
    
    if [ -z "$vault_addr" ]; then
        echo -e "${RED}Vault address is required.${NC}"
        echo -e "${YELLOW}Falling back to local file storage.${NC}"
        echo ""
        return 1
    fi
    
    export VAULT_ADDR="$vault_addr"
    
    # Get authentication method
    echo ""
    echo -e "${CYAN}Authentication Method${NC}"
    echo ""
    echo "1. Token authentication (simple, for testing)"
    echo "2. AppRole authentication (recommended for production)"
    echo ""
    read -p "Select method (1 or 2): " auth_method
    
    if [ "$auth_method" = "1" ]; then
        read -s -p "Enter Vault token: " vault_token
        echo ""
        if [ -z "$vault_token" ]; then
            echo -e "${RED}Token is required.${NC}"
            echo -e "${YELLOW}Falling back to local file storage.${NC}"
            echo ""
            unset VAULT_ADDR
            return 1
        fi
        export VAULT_TOKEN="$vault_token"
        
    elif [ "$auth_method" = "2" ]; then
        read -p "Enter Role ID: " vault_role_id
        read -s -p "Enter Secret ID: " vault_secret_id
        echo ""
        
        if [ -z "$vault_role_id" ] || [ -z "$vault_secret_id" ]; then
            echo -e "${RED}Both Role ID and Secret ID are required.${NC}"
            echo -e "${YELLOW}Falling back to local file storage.${NC}"
            echo ""
            unset VAULT_ADDR
            return 1
        fi
        
        export VAULT_ROLE_ID="$vault_role_id"
        export VAULT_SECRET_ID="$vault_secret_id"
    else
        echo -e "${RED}Invalid selection.${NC}"
        echo -e "${YELLOW}Falling back to local file storage.${NC}"
        echo ""
        unset VAULT_ADDR
        return 1
    fi
    
    # Optional namespace
    echo ""
    read -p "Vault namespace (optional, press Enter to skip): " vault_namespace
    if [ -n "$vault_namespace" ]; then
        export VAULT_NAMESPACE="$vault_namespace"
    fi
    
    echo ""
    echo -e "${GREEN}✓ Vault configuration complete${NC}"
    echo ""
    
    # Save Vault config for future use
    echo -e "${CYAN}Saving Vault configuration for persistence...${NC}"
    echo ""
    echo -e "${YELLOW}Add these to your shell profile (~/.bashrc or ~/.bash_profile):${NC}"
    echo ""
    echo "export VAULT_ADDR='$vault_addr'"
    if [ -n "$vault_token" ]; then
        echo "export VAULT_TOKEN='$vault_token'"
    fi
    if [ -n "$vault_role_id" ]; then
        echo "export VAULT_ROLE_ID='$vault_role_id'"
        echo "export VAULT_SECRET_ID='$vault_secret_id'"
    fi
    if [ -n "$vault_namespace" ]; then
        echo "export VAULT_NAMESPACE='$vault_namespace'"
    fi
    echo ""
    
    return 0
}

# Function to save encryption key to HashiCorp Vault
save_key_to_vault() {
    echo -e "${CYAN}Attempting to save key to HashiCorp Vault...${NC}"
    
    # Use Python to save to Vault
    python - <<EOF
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

# Set the encryption key in environment for the save function
os.environ['FILAMENTBOX_TEMP_KEY'] = '$ENCRYPTION_KEY'

# Import the vault save function
sys.path.insert(0, '$INSTALL_ROOT')
from filamentbox.config_db import _save_key_to_vault

# Attempt to save
if _save_key_to_vault(os.environ['FILAMENTBOX_TEMP_KEY']):
    sys.exit(0)
else:
    sys.exit(1)
EOF
    
    return $?
}

# Function to save encryption key to secure file
save_encryption_key() {
    local vault_saved=false
    
    # Check if Vault is available
    if check_vault_available; then
        echo -e "${CYAN}HashiCorp Vault detected.${NC}"
        echo ""
        
        if save_key_to_vault; then
            echo -e "${GREEN}✓ Encryption key saved to HashiCorp Vault${NC}"
            echo -e "${GREEN}  Path: secret/data/filamentbox/config_key${NC}"
            vault_saved=true
        else
            echo -e "${YELLOW}⚠ Failed to save to Vault, falling back to local file${NC}"
        fi
        echo ""
    fi
    
    # Always save to local file as backup/fallback
    echo -e "${CYAN}Saving encryption key to local file...${NC}"
    
    # Write key to file
    echo "$ENCRYPTION_KEY" > "$KEY_FILE"
    
    # Set restrictive permissions (owner read/write only)
    chmod 600 "$KEY_FILE"
    
    if [ "$vault_saved" = true ]; then
        echo -e "${GREEN}✓ Encryption key also saved to local file (backup)${NC}"
        echo -e "${GREEN}  Path: $KEY_FILE${NC}"
        echo -e "${GREEN}  Permissions: 600 (owner read/write only)${NC}"
    else
        echo -e "${GREEN}✓ Encryption key saved to local file${NC}"
        echo -e "${GREEN}  Path: $KEY_FILE${NC}"
        echo -e "${GREEN}  Permissions: 600 (owner read/write only)${NC}"
    fi
    echo ""
}

# Function to prompt for encryption key
prompt_encryption_key() {
    # First, ask about Vault (capture return value, don't exit on non-zero)
    set +e
    configure_vault_interactive
    VAULT_CONFIGURED=$?
    set -e
    
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Encryption Key Generation${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo -e "${CYAN}A strong encryption key will be automatically generated.${NC}"
    echo -e "${CYAN}This key will be used to encrypt/decrypt your configuration.${NC}"
    echo ""
    
    # Generate a strong random key
    generate_encryption_key
    
    echo -e "${GREEN}Auto-generated encryption key (64 characters):${NC}"
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}$ENCRYPTION_KEY${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${RED}CRITICAL - SAVE THIS KEY NOW!${NC}"
    echo ""
    echo -e "${YELLOW}Action items:${NC}"
    echo -e "  1. ${RED}Copy the key above to a secure location${NC}"
    echo -e "  2. Store it in a password manager or encrypted vault"
    echo -e "  3. Keep this backup - you'll need it if you lose access to the key"
    echo ""
    echo -e "${RED}WARNING:${NC}"
    echo -e "${RED}  - If you lose this key, you CANNOT recover your configuration${NC}"
    
    if [ $VAULT_CONFIGURED -eq 0 ]; then
        echo -e "${RED}  - The key will be saved to HashiCorp Vault${NC}"
        echo -e "${RED}  - A backup will also be saved to $KEY_FILE${NC}"
    else
        echo -e "${RED}  - The key will be saved to $KEY_FILE${NC}"
    fi
    
    echo -e "${RED}  - Keep backups of the key in a secure location${NC}"
    echo ""
    
    # Wait for user confirmation
    read -p "Press ENTER after you have saved the key to continue..."
    echo ""
    echo -e "${GREEN}Continuing with setup...${NC}"
    echo ""
    
    # Export the key for use by migration/config scripts
    export FILAMENTBOX_CONFIG_KEY="$ENCRYPTION_KEY"
}

# Function to ensure pysqlcipher3 is installed
ensure_pysqlcipher3() {
    echo -e "${CYAN}Checking for SQLCipher Python bindings...${NC}"
    cd "$INSTALL_ROOT"
    
    # Try pysqlcipher3 first (legacy), then sqlcipher3 (modern)
    if ! "$INSTALL_ROOT/filamentcontrol/bin/python" -c "from pysqlcipher3 import dbapi2" 2>/dev/null && \
       ! "$INSTALL_ROOT/filamentcontrol/bin/python" -c "from sqlcipher3 import dbapi2" 2>/dev/null; then
        echo -e "${YELLOW}SQLCipher Python bindings not found. Installing...${NC}"
        echo ""
        
        # Check for SQLCipher development libraries
        if ! pkg-config --exists sqlcipher 2>/dev/null; then
            echo -e "${YELLOW}SQLCipher development libraries not found.${NC}"
            echo -e "${YELLOW}Installing system dependencies...${NC}"
            echo ""
            
            # Detect package manager and install
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y libsqlcipher-dev
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y sqlcipher-devel
            elif command -v yum &> /dev/null; then
                sudo yum install -y sqlcipher-devel
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --noconfirm sqlcipher
            else
                echo -e "${RED}Could not detect package manager.${NC}"
                echo -e "${RED}Please install SQLCipher development libraries manually:${NC}"
                echo -e "${RED}  Debian/Ubuntu: sudo apt-get install libsqlcipher-dev${NC}"
                echo -e "${RED}  RHEL/CentOS: sudo yum install sqlcipher-devel${NC}"
                echo -e "${RED}  Fedora: sudo dnf install sqlcipher-devel${NC}"
                echo -e "${RED}  Arch: sudo pacman -S sqlcipher${NC}"
                echo ""
                return 1
            fi
            echo ""
        fi
        
        # Check Python version to determine which package to use
        PYTHON_VERSION=$("$INSTALL_ROOT/filamentcontrol/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo -e "${CYAN}Python version: $PYTHON_VERSION${NC}"
        
        # For Python 3.13+, use sqlcipher3-wheels (pre-built wheels)
        if "$INSTALL_ROOT/filamentcontrol/bin/python" -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" 2>/dev/null; then
            echo -e "${CYAN}Python 3.13+ detected. Installing sqlcipher3-wheels...${NC}"
            "$INSTALL_ROOT/filamentcontrol/bin/pip" install sqlcipher3-wheels
        else
            echo -e "${CYAN}Installing pysqlcipher3...${NC}"
            "$INSTALL_ROOT/filamentcontrol/bin/pip" install pysqlcipher3
        fi
        echo ""
        
        # Verify installation
        if ! "$INSTALL_ROOT/filamentcontrol/bin/python" -c "from pysqlcipher3 import dbapi2" 2>/dev/null && \
           ! "$INSTALL_ROOT/filamentcontrol/bin/python" -c "from sqlcipher3 import dbapi2" 2>/dev/null; then
            echo -e "${RED}Failed to install SQLCipher Python bindings.${NC}"
            echo -e "${RED}Please install manually and re-run setup.${NC}"
            echo ""
            return 1
        fi
        echo -e "${GREEN}✓ SQLCipher Python bindings installed successfully${NC}"
        echo ""
    else
        echo -e "${GREEN}SQLCipher Python bindings already installed.${NC}"
    fi
    echo ""
}

# Function to generate systemd service files
generate_service_files() {
    echo -e "${CYAN}Generating systemd service files...${NC}"
    echo ""
    
    local service_dir="$INSTALL_ROOT/install"
    local main_service="$service_dir/filamentbox.service"
    local webui_service="$service_dir/filamentbox-webui.service"
    
    # Determine current user and group
    local service_user="${SUDO_USER:-$USER}"
    local service_group=$(id -gn "$service_user")
    
    # Determine if Vault is configured
    local use_vault=false
    if [ -n "$VAULT_ADDR" ] && ([ -n "$VAULT_TOKEN" ] || ([ -n "$VAULT_ROLE_ID" ] && [ -n "$VAULT_SECRET_ID" ])); then
        use_vault=true
    fi
    
    # Generate main service file
    cat > "$main_service" << EOF
# Version: 2.0.0
# Auto-generated by setup.sh - Do not edit manually
# Installation path: $INSTALL_ROOT
[Unit]
Description=FilamentBox Environment Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$service_user
Group=$service_group
WorkingDirectory=$INSTALL_ROOT
Environment="PATH=$INSTALL_ROOT/filamentcontrol/bin"
EOF

    # Add Vault environment variables if configured
    if [ "$use_vault" = true ]; then
        cat >> "$main_service" << EOF

# HashiCorp Vault configuration for encryption key
Environment="VAULT_ADDR=$VAULT_ADDR"
EOF
        if [ -n "$VAULT_TOKEN" ]; then
            cat >> "$main_service" << EOF
Environment="VAULT_TOKEN=$VAULT_TOKEN"
EOF
        fi
        if [ -n "$VAULT_ROLE_ID" ]; then
            cat >> "$main_service" << EOF
Environment="VAULT_ROLE_ID=$VAULT_ROLE_ID"
Environment="VAULT_SECRET_ID=$VAULT_SECRET_ID"
EOF
        fi
        if [ -n "$VAULT_NAMESPACE" ]; then
            cat >> "$main_service" << EOF
Environment="VAULT_NAMESPACE=$VAULT_NAMESPACE"
EOF
        fi
    fi
    
    # Complete the service file
    cat >> "$main_service" << EOF

ExecStart=$INSTALL_ROOT/filamentcontrol/bin/python $INSTALL_ROOT/run_filamentbox.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$INSTALL_ROOT

[Install]
WantedBy=multi-user.target
EOF

    # Generate WebUI service file
    cat > "$webui_service" << EOF
# Version: 2.0.0
# Auto-generated by setup.sh - Do not edit manually
# Installation path: $INSTALL_ROOT
[Unit]
Description=FilamentBox Web UI
After=network-online.target filamentbox.service
Wants=network-online.target

[Service]
Type=simple
User=$service_user
Group=$service_group
WorkingDirectory=$INSTALL_ROOT
Environment="PATH=$INSTALL_ROOT/filamentcontrol/bin"
EOF

    # Add Vault environment variables to WebUI service if configured
    if [ "$use_vault" = true ]; then
        cat >> "$webui_service" << EOF

# HashiCorp Vault configuration for encryption key
Environment="VAULT_ADDR=$VAULT_ADDR"
EOF
        if [ -n "$VAULT_TOKEN" ]; then
            cat >> "$webui_service" << EOF
Environment="VAULT_TOKEN=$VAULT_TOKEN"
EOF
        fi
        if [ -n "$VAULT_ROLE_ID" ]; then
            cat >> "$webui_service" << EOF
Environment="VAULT_ROLE_ID=$VAULT_ROLE_ID"
Environment="VAULT_SECRET_ID=$VAULT_SECRET_ID"
EOF
        fi
        if [ -n "$VAULT_NAMESPACE" ]; then
            cat >> "$webui_service" << EOF
Environment="VAULT_NAMESPACE=$VAULT_NAMESPACE"
EOF
        fi
    fi
    
    # Complete the WebUI service file
    cat >> "$webui_service" << EOF

ExecStart=$INSTALL_ROOT/filamentcontrol/bin/python $INSTALL_ROOT/run_webui.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$INSTALL_ROOT

[Install]
WantedBy=multi-user.target
EOF

    if [ "$use_vault" = true ]; then
        echo -e "${GREEN}✓ Service files generated with HashiCorp Vault support${NC}"
        echo -e "${GREEN}  - filamentbox.service${NC}"
        echo -e "${GREEN}  - filamentbox-webui.service${NC}"
        echo ""
        echo -e "${CYAN}Configuration:${NC}"
        echo -e "${CYAN}  Installation path: $INSTALL_ROOT${NC}"
        echo -e "${CYAN}  Service user: $service_user${NC}"
        echo -e "${CYAN}  Service group: $service_group${NC}"
        echo -e "${CYAN}  Vault integration: Enabled${NC}"
    else
        echo -e "${GREEN}✓ Service files generated (local key file mode)${NC}"
        echo -e "${GREEN}  - filamentbox.service${NC}"
        echo -e "${GREEN}  - filamentbox-webui.service${NC}"
        echo ""
        echo -e "${CYAN}Configuration:${NC}"
        echo -e "${CYAN}  Installation path: $INSTALL_ROOT${NC}"
        echo -e "${CYAN}  Service user: $service_user${NC}"
        echo -e "${CYAN}  Service group: $service_group${NC}"
        echo -e "${CYAN}  Key file: $KEY_FILE${NC}"
    fi
    echo ""
    echo -e "${YELLOW}To install the services, run:${NC}"
    echo -e "${CYAN}  sudo ./install/install_service.sh${NC}"
    echo -e "${CYAN}  sudo ./install/install_webui_service.sh${NC}"
    echo ""
}

# Function to launch interactive config tool
launch_config_tool() {
    echo -e "${CYAN}Starting interactive configuration tool...${NC}"
    echo ""
    cd "$INSTALL_ROOT"
    python scripts/config_tool.py --interactive
    
    # Generate service files after configuration
    generate_service_files
    
    exit 0
}

# ========================================
# Main Script
# ========================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FilamentBox Configuration Manager${NC}"
echo -e "${BLUE}v2.0 - Encrypted Database${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ========================================
# Check Configuration Status
# ========================================

# Check if encrypted database already exists
if [ -f "$CONFIG_DB" ]; then
    echo -e "${GREEN}Encrypted configuration database found.${NC}"
    echo ""
    
    # Check if encryption key is set
    if [ -z "$FILAMENTBOX_CONFIG_KEY" ]; then
        # Try to load from key file
        if [ -f "$KEY_FILE" ]; then
            echo -e "${CYAN}Loading encryption key from secure storage...${NC}"
            FILAMENTBOX_CONFIG_KEY=$(cat "$KEY_FILE")
            export FILAMENTBOX_CONFIG_KEY
            echo ""
        else
            echo -e "${RED}ERROR: FILAMENTBOX_CONFIG_KEY environment variable not set!${NC}"
            echo -e "${RED}And key file not found at: $KEY_FILE${NC}"
            echo ""
            echo -e "${YELLOW}Please set your encryption key before managing configuration:${NC}"
            echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='your-encryption-key'${NC}"
            echo ""
            echo -e "${YELLOW}To make it permanent, add to your shell profile:${NC}"
            echo -e "${CYAN}  echo \"export FILAMENTBOX_CONFIG_KEY='your-encryption-key'\" >> ~/.bashrc${NC}"
            echo ""
            echo -e "${YELLOW}Or run setup again to regenerate keys.${NC}"
            echo ""
            exit 1
        fi
    fi
    
    # Configuration exists - offer to reconfigure or modify
    echo -e "${CYAN}Configuration Management Options:${NC}"
    echo "  1) Reconfigure everything (encryption key, Vault, database)"
    echo "  2) Modify specific settings (interactive menu)"
    echo "  3) Exit"
    echo ""
    read -p "Enter choice (1-3): " CONFIG_CHOICE
    
    case ${CONFIG_CHOICE} in
        1)
            echo -e "${YELLOW}This will regenerate encryption keys and reconfigure everything.${NC}"
            read -p "Continue? (y/N): " CONFIRM
            if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
                exit 0
            fi
            # Continue to reconfiguration below
            ;;
        2)
            # Use Python config tool for interactive editing
            cd "$INSTALL_ROOT"
            if [ -f "scripts/config_tool.py" ]; then
                source "$INSTALL_ROOT/filamentcontrol/bin/activate" 2>/dev/null || true
                python scripts/config_tool.py --interactive
            else
                echo -e "${RED}Config tool not found${NC}"
            fi
            exit 0
            ;;
        3)
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
fi

# Check for legacy configuration files and auto-migrate
LEGACY_FILES_EXIST=false
LEGACY_FILES_LIST=""

if [ -f "$CONFIG_YAML" ]; then
    LEGACY_FILES_EXIST=true
    LEGACY_FILES_LIST="config.yaml"
fi

if [ -f "$ENV_FILE" ]; then
    LEGACY_FILES_EXIST=true
    if [ -n "$LEGACY_FILES_LIST" ]; then
        LEGACY_FILES_LIST="$LEGACY_FILES_LIST and .env"
    else
        LEGACY_FILES_LIST=".env"
    fi
fi

if [ "$LEGACY_FILES_EXIST" = true ]; then
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Legacy Configuration Detected${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo -e "${CYAN}Found: $LEGACY_FILES_LIST${NC}"
    echo ""
    echo -e "${GREEN}FilamentBox v2.0 requires encrypted configuration database.${NC}"
    echo -e "${GREEN}Your configuration will be automatically migrated.${NC}"
    echo ""
    echo -e "${YELLOW}Benefits of encrypted configuration:${NC}"
    echo "  - Passwords encrypted at rest (256-bit AES)"
    echo "  - Centralized configuration management"
    echo "  - Interactive configuration tool"
    echo "  - Better security than plain text files"
    echo ""
    
    # Prompt for encryption key setup
    prompt_encryption_key
    
    # Ensure pysqlcipher3 is installed
    ensure_pysqlcipher3
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install SQLCipher dependencies.${NC}"
        echo -e "${RED}Cannot proceed with migration.${NC}"
        echo ""
        exit 1
    fi
    
    echo -e "${CYAN}Running migration from legacy configuration files...${NC}"
    echo ""
    
    # Run migration script
    cd "$INSTALL_ROOT"
    python scripts/migrate_config.py --yaml "$CONFIG_YAML" --env "$ENV_FILE" --db "$CONFIG_DB" --key "$ENCRYPTION_KEY"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Migration Successful!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "${GREEN}Configuration migrated to encrypted database:${NC}"
        echo -e "${GREEN}  $CONFIG_DB${NC}"
        echo ""
        
        # Backup and remove legacy files
        BACKUP_DIR="$INSTALL_ROOT/config_backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        if [ -f "$CONFIG_YAML" ]; then
            mv "$CONFIG_YAML" "$BACKUP_DIR/"
            echo -e "${GREEN}Legacy config.yaml backed up to:${NC}"
            echo -e "${GREEN}  $BACKUP_DIR/config.yaml${NC}"
        fi
        
        if [ -f "$ENV_FILE" ]; then
            mv "$ENV_FILE" "$BACKUP_DIR/"
            echo -e "${GREEN}Legacy .env backed up to:${NC}"
            echo -e "${GREEN}  $BACKUP_DIR/.env${NC}"
        fi
        
        echo ""
        
        # Save encryption key to secure file
        save_encryption_key
        
        echo -e "${YELLOW}IMPORTANT - Encryption Key Access:${NC}"
        echo ""
        if check_vault_available; then
            echo -e "${GREEN}Primary: HashiCorp Vault${NC}"
            echo -e "${GREEN}  The application will retrieve the key from Vault${NC}"
            echo ""
            echo -e "${GREEN}Backup: Local file${NC}"
            echo -e "${GREEN}  $KEY_FILE (if Vault is unavailable)${NC}"
        else
            echo -e "${GREEN}Key storage: Local file${NC}"
            echo -e "${GREEN}  $KEY_FILE${NC}"
            echo -e "${GREEN}  (Permissions: 600 - owner read/write only)${NC}"
            echo ""
            echo -e "${CYAN}For enhanced security, consider using HashiCorp Vault${NC}"
        fi
        echo ""
        echo -e "${YELLOW}The application will automatically load the key.${NC}"
        echo ""
        
        # Generate service files
        generate_service_files
        
        echo -e "${CYAN}You can now manage your configuration using:${NC}"
        echo -e "${CYAN}  python scripts/config_tool.py --interactive${NC}"
        echo ""
        exit 0
    else
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}Migration Failed${NC}"
        echo -e "${RED}========================================${NC}"
        echo ""
        echo -e "${RED}Migration failed. Please check the error messages above.${NC}"
        echo -e "${YELLOW}Your original configuration files were not modified.${NC}"
        echo ""
        echo -e "${YELLOW}You can try running the migration manually:${NC}"
        echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
        echo -e "${CYAN}  python scripts/migrate_config.py --yaml config.yaml --env .env --db filamentbox_config.db --key '$ENCRYPTION_KEY'${NC}"
        echo ""
        exit 1
    fi
fi

# No existing configuration - create new encrypted database
echo -e "${GREEN}No existing configuration found.${NC}"
echo -e "${GREEN}Creating new encrypted configuration database.${NC}"
echo ""

# Ensure pysqlcipher3 is installed
ensure_pysqlcipher3

# Prompt for encryption key
prompt_encryption_key

# Save encryption key to secure file
save_encryption_key

echo -e "${YELLOW}IMPORTANT - Encryption Key Access:${NC}"
echo ""
if check_vault_available; then
    echo -e "${GREEN}Primary: HashiCorp Vault${NC}"
    echo -e "${GREEN}  The application will retrieve the key from Vault${NC}"
    echo ""
    echo -e "${GREEN}Backup: Local file${NC}"
    echo -e "${GREEN}  $KEY_FILE (if Vault is unavailable)${NC}"
else
    echo -e "${GREEN}Key storage: Local file${NC}"
    echo -e "${GREEN}  $KEY_FILE${NC}"
    echo -e "${GREEN}  (Permissions: 600 - owner read/write only)${NC}"
    echo ""
    echo -e "${CYAN}For enhanced security, consider using HashiCorp Vault${NC}"
fi
echo ""
echo -e "${YELLOW}The application will automatically load the key.${NC}"
echo ""

# Use config_tool.py for interactive setup
launch_config_tool
