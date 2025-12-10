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
KEY_FILE="$INSTALL_ROOT/.config_key"

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
            echo -e "${YELLOW}Or the key file will be created automatically during setup.${NC}"
            echo ""
            exit 1
        fi
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
        
        # Save encryption key to secure file
        save_encryption_key
        
        echo -e "${YELLOW}IMPORTANT - Encryption Key Security:${NC}"
        echo ""
        echo -e "${GREEN}Encryption key saved to:${NC}"
        echo -e "${GREEN}  $KEY_FILE${NC}"
        echo -e "${GREEN}  (Permissions: 600 - owner read/write only)${NC}"
        echo ""
        echo -e "${YELLOW}The application will automatically use this key file.${NC}"
        echo ""
        echo -e "${YELLOW}For additional security, you can also set environment variable:${NC}"
        echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
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

# Prompt for encryption key
prompt_encryption_key

# Save encryption key to secure file
save_encryption_key

echo -e "${YELLOW}IMPORTANT - Encryption Key Security:${NC}"
echo ""
echo -e "${GREEN}Encryption key saved to:${NC}"
echo -e "${GREEN}  $KEY_FILE${NC}"
echo -e "${GREEN}  (Permissions: 600 - owner read/write only)${NC}"
echo ""
echo -e "${YELLOW}The application will automatically use this key file.${NC}"
echo ""
echo -e "${YELLOW}For additional security, you can also set environment variable:${NC}"
echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
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

# Function to generate a strong encryption key
generate_encryption_key() {
    # Generate a 64-character random key using /dev/urandom
    # Uses base64 encoding for URL-safe characters
    ENCRYPTION_KEY=$(head -c 48 /dev/urandom | base64 | tr -d '\n' | tr -d '=' | head -c 64)
}

# Function to prompt for encryption key
prompt_encryption_key() {
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Encryption Key Setup${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo -e "${CYAN}A strong encryption key is required for your configuration database.${NC}"
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
    echo -e "  3. You'll need this key if you ever need to recover"
    echo ""
    echo -e "${RED}WARNING:${NC}"
    echo -e "${RED}  - If you lose this key, you CANNOT recover your configuration${NC}"
    echo -e "${RED}  - The key will be saved to $KEY_FILE${NC}"
    echo -e "${RED}  - Keep backups of both the key file and the key itself${NC}"
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

# Function to save encryption key to secure file
save_encryption_key() {
    echo -e "${CYAN}Saving encryption key to secure storage...${NC}"
    
    # Write key to file
    echo "$ENCRYPTION_KEY" > "$KEY_FILE"
    
    # Set restrictive permissions (owner read/write only)
    chmod 600 "$KEY_FILE"
    
    echo -e "${GREEN}Encryption key saved securely.${NC}"
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
