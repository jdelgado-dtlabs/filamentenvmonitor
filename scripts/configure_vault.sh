#!/bin/bash
# Helper script to configure HashiCorp Vault for FilamentBox
# This script helps set up Vault environment variables for encryption key storage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FilamentBox Vault Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if hvac is installed
if ! python -c "import hvac" 2>/dev/null; then
    echo -e "${YELLOW}HashiCorp Vault Python library (hvac) not installed.${NC}"
    echo ""
    read -p "Install hvac? (y/n): " install_hvac
    if [[ "$install_hvac" =~ ^[Yy]$ ]]; then
        pip install hvac
        echo ""
    else
        echo -e "${RED}Cannot configure Vault without hvac library.${NC}"
        exit 1
    fi
fi

# Get Vault address
echo -e "${CYAN}Vault Server Configuration${NC}"
echo ""
read -p "Vault server address (e.g., https://vault.example.com:8200): " vault_addr

if [ -z "$vault_addr" ]; then
    echo -e "${RED}Vault address is required.${NC}"
    exit 1
fi

# Get authentication method
echo ""
echo -e "${CYAN}Authentication Method${NC}"
echo ""
echo "1. Token authentication (simple, for testing)"
echo "2. AppRole authentication (recommended for production)"
echo ""
read -p "Select method (1 or 2): " auth_method

vault_token=""
vault_role_id=""
vault_secret_id=""

if [ "$auth_method" = "1" ]; then
    read -s -p "Enter Vault token: " vault_token
    echo ""
elif [ "$auth_method" = "2" ]; then
    read -p "Enter Role ID: " vault_role_id
    read -s -p "Enter Secret ID: " vault_secret_id
    echo ""
else
    echo -e "${RED}Invalid selection.${NC}"
    exit 1
fi

# Optional namespace (Vault Enterprise)
echo ""
read -p "Vault namespace (optional, press Enter to skip): " vault_namespace

# Generate environment variable exports
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Configuration Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Add these environment variables to your shell profile:${NC}"
echo ""
echo "export VAULT_ADDR='$vault_addr'"

if [ -n "$vault_token" ]; then
    echo "export VAULT_TOKEN='$vault_token'"
fi

if [ -n "$vault_role_id" ]; then
    echo "export VAULT_ROLE_ID='$vault_role_id'"
fi

if [ -n "$vault_secret_id" ]; then
    echo "export VAULT_SECRET_ID='$vault_secret_id'"
fi

if [ -n "$vault_namespace" ]; then
    echo "export VAULT_NAMESPACE='$vault_namespace'"
fi

echo ""
echo -e "${CYAN}To apply now:${NC}"
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
echo -e "${YELLOW}For systemd service, add to EnvironmentFile or [Service] section:${NC}"
echo ""
echo "Environment=\"VAULT_ADDR=$vault_addr\""

if [ -n "$vault_token" ]; then
    echo "Environment=\"VAULT_TOKEN=$vault_token\""
fi

if [ -n "$vault_role_id" ]; then
    echo "Environment=\"VAULT_ROLE_ID=$vault_role_id\""
    echo "Environment=\"VAULT_SECRET_ID=$vault_secret_id\""
fi

if [ -n "$vault_namespace" ]; then
    echo "Environment=\"VAULT_NAMESPACE=$vault_namespace\""
fi

echo ""
echo -e "${GREEN}After setting environment variables, run setup.sh to configure FilamentBox.${NC}"
echo -e "${GREEN}The encryption key will be automatically stored in Vault.${NC}"
echo ""
