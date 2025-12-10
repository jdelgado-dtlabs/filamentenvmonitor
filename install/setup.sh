#!/bin/bash
# FilamentBox Configuration Setup Script
# v2.0+ - Encrypted Configuration Database Only
# All configuration is stored in encrypted SQLCipher database

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

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FilamentBox Configuration Setup${NC}"
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
        echo -e "${RED}ERROR: FILAMENTBOX_CONFIG_KEY environment variable not set!${NC}"
        echo ""
        echo -e "${YELLOW}Please set your encryption key before managing configuration:${NC}"
        echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='your-encryption-key'${NC}"
        echo ""
        echo -e "${YELLOW}To make it permanent, add to your shell profile:${NC}"
        echo -e "${CYAN}  echo \"export FILAMENTBOX_CONFIG_KEY='your-encryption-key'\" >> ~/.bashrc${NC}"
        echo ""
        echo -e "${YELLOW}Then restart this script to manage your configuration.${NC}"
        echo ""
        exit 1
    fi
    
    echo -e "${CYAN}Use the interactive configuration tool to manage settings:${NC}"
    echo -e "${CYAN}  python scripts/config_tool.py --interactive${NC}"
    echo ""
    
    # Launch config tool
    launch_config_tool
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
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Encryption Key Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    prompt_encryption_key
    
    # Ensure pysqlcipher3 is installed
    ensure_pysqlcipher3
    
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
        echo -e "${YELLOW}IMPORTANT - Save Your Encryption Key:${NC}"
        echo ""
        echo -e "${YELLOW}Add this to your shell profile (~/.bashrc or ~/.bash_profile):${NC}"
        echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
        echo ""
        echo -e "${YELLOW}Or add to systemd service file if running as a service.${NC}"
        echo ""
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

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Encryption Key Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Prompt for encryption key
prompt_encryption_key

echo -e "${YELLOW}IMPORTANT - Save Your Encryption Key:${NC}"
echo ""
echo -e "${YELLOW}Add this to your shell profile (~/.bashrc or ~/.bash_profile):${NC}"
echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
echo ""
echo -e "${YELLOW}Or add to systemd service file if running as a service.${NC}"
echo ""

# Use config_tool.py for interactive setup
launch_config_tool

# ========================================
# Helper Functions
# ========================================

# Function to ask yes/no question
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

# Function to prompt for encryption key
prompt_encryption_key() {
    echo ""
    echo -e "${YELLOW}You need to create a strong encryption key for your configuration database.${NC}"
    echo -e "${YELLOW}This key will be used to encrypt/decrypt your configuration.${NC}"
    echo ""
    echo -e "${RED}IMPORTANT:${NC}"
    echo -e "${RED}  - Choose a strong, unique key (32+ characters recommended)${NC}"
    echo -e "${RED}  - Store this key securely - you'll need it to access your config${NC}"
    echo -e "${RED}  - If you lose this key, you CANNOT recover your configuration${NC}"
    echo ""
    
    while true; do
        read -s -p "Enter encryption key: " ENCRYPTION_KEY
        echo ""
        
        if [ -z "$ENCRYPTION_KEY" ]; then
            echo -e "${RED}Encryption key cannot be empty. Please try again.${NC}"
            echo ""
            continue
        fi
        
        if [ ${#ENCRYPTION_KEY} -lt 16 ]; then
            echo -e "${YELLOW}Warning: Key is short (${#ENCRYPTION_KEY} chars). Recommend 32+ characters.${NC}"
            if ! ask_yes_no "Use this key anyway?" "N"; then
                echo ""
                continue
            fi
        fi
        
        read -s -p "Confirm encryption key: " ENCRYPTION_KEY_CONFIRM
        echo ""
        
        if [ "$ENCRYPTION_KEY" != "$ENCRYPTION_KEY_CONFIRM" ]; then
            echo -e "${RED}Keys don't match. Please try again.${NC}"
            echo ""
            continue
        fi
        
        break
    done
    
    echo ""
    echo -e "${GREEN}Encryption key set successfully.${NC}"
    echo ""
    
    # Export the key for use by migration/config scripts
    export FILAMENTBOX_CONFIG_KEY="$ENCRYPTION_KEY"
}

# Function to ensure pysqlcipher3 is installed
ensure_pysqlcipher3() {
    echo -e "${CYAN}Checking for pysqlcipher3...${NC}"
    cd "$INSTALL_ROOT"
    
    if ! python -c "import pysqlcipher3" 2>/dev/null; then
        echo -e "${YELLOW}pysqlcipher3 not found. Installing...${NC}"
        pip install pysqlcipher3
    else
        echo -e "${GREEN}pysqlcipher3 already installed.${NC}"
    fi
    echo ""
}

# Function to launch interactive config tool
launch_config_tool() {
    echo -e "${CYAN}Starting interactive configuration tool...${NC}"
    echo ""
    cd "$INSTALL_ROOT"
    python scripts/config_tool.py --interactive
    exit 0
}
