#!/bin/bash
# Helper script to load encryption key for FilamentBox services
# Source this script in systemd service files or startup scripts

# Get the installation root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(dirname "$SCRIPT_DIR")"
KEY_FILE="$INSTALL_ROOT/.config_key"

# Check if key is already set in environment
if [ -n "$FILAMENTBOX_CONFIG_KEY" ]; then
    echo "Encryption key already set in environment"
    exit 0
fi

# Load key from file
if [ -f "$KEY_FILE" ]; then
    export FILAMENTBOX_CONFIG_KEY=$(cat "$KEY_FILE")
    echo "Encryption key loaded from $KEY_FILE"
else
    echo "ERROR: Key file not found at $KEY_FILE"
    echo "Please run install/setup.sh to configure encryption key"
    exit 1
fi
