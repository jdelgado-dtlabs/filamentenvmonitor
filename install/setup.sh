#!/bin/bash
# FilamentBox Configuration Setup Script
# Supports encrypted configuration database (v2.0+) and legacy .env files (v1.x)
# Automatically migrates from legacy configuration to encrypted database

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
ENV_FILE="$INSTALL_ROOT/.env"
CONFIG_YAML="$INSTALL_ROOT/config.yaml"
CONFIG_DB="$INSTALL_ROOT/filamentbox_config.db"
MIGRATE_SCRIPT="$SCRIPT_DIR/migrate_config.py"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FilamentBox Configuration Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ========================================
# Detect Configuration Mode and Handle Migration
# ========================================

# Check if encrypted database exists
if [ -f "$CONFIG_DB" ]; then
    echo -e "${GREEN}Encrypted configuration database detected.${NC}"
    echo -e "${GREEN}Using config_tool.py for configuration management.${NC}"
    echo ""
    
    # Check if encryption key is set
    if [ -z "$FILAMENTBOX_CONFIG_KEY" ]; then
        echo -e "${RED}ERROR: FILAMENTBOX_CONFIG_KEY environment variable not set!${NC}"
        echo -e "${YELLOW}Please set your encryption key:${NC}"
        echo -e "${YELLOW}  export FILAMENTBOX_CONFIG_KEY='your-encryption-key'${NC}"
        echo ""
        echo -e "${YELLOW}To make it permanent, add to your shell profile:${NC}"
        echo -e "${YELLOW}  echo \"export FILAMENTBOX_CONFIG_KEY='your-encryption-key'\" >> ~/.bashrc${NC}"
        echo ""
        exit 1
    fi
    
    # Use config_tool.py for interactive configuration
    launch_config_tool
fi

# Check for legacy configuration files
LEGACY_ENV_EXISTS=false
LEGACY_YAML_EXISTS=false

if [ -f "$ENV_FILE" ]; then
    LEGACY_ENV_EXISTS=true
fi

if [ -f "$CONFIG_YAML" ]; then
    LEGACY_YAML_EXISTS=true
fi

# Offer migration if legacy files exist
if [ "$LEGACY_ENV_EXISTS" = true ] || [ "$LEGACY_YAML_EXISTS" = true ]; then
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Legacy Configuration Detected${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    
    if [ "$LEGACY_ENV_EXISTS" = true ]; then
        echo -e "${CYAN}Found: .env file${NC}"
    fi
    if [ "$LEGACY_YAML_EXISTS" = true ]; then
        echo -e "${CYAN}Found: config.yaml file${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}FilamentBox v2.0 uses encrypted configuration database for secure credential storage.${NC}"
    echo ""
    echo -e "${YELLOW}Benefits:${NC}"
    echo "  - Encrypted storage of passwords and sensitive data"
    echo "  - Centralized configuration management"
    echo "  - Better security than plain text files"
    echo "  - Interactive configuration tool"
    echo ""
    
    if ask_yes_no "Migrate to encrypted configuration database?"; then
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}Encryption Key Setup${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        
        # Prompt for encryption key
        prompt_encryption_key
        
        # Export the key for migration script
        export FILAMENTBOX_CONFIG_KEY="$ENCRYPTION_KEY"
        
        # Ensure pysqlcipher3 is installed
        ensure_pysqlcipher3
        
        echo -e "${CYAN}Running migration...${NC}"
        echo ""
        
        # Run migration script
        python "$MIGRATE_SCRIPT" --yaml "$CONFIG_YAML" --db "$CONFIG_DB" --key "$ENCRYPTION_KEY"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}Migration Successful!${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""
            echo -e "${GREEN}Your configuration has been migrated to encrypted database:${NC}"
            echo -e "${GREEN}  $CONFIG_DB${NC}"
            echo ""
            echo -e "${YELLOW}IMPORTANT - Save Your Encryption Key:${NC}"
            echo ""
            echo -e "${YELLOW}Add this to your shell profile (~/.bashrc or ~/.bash_profile):${NC}"
            echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
            echo ""
            echo -e "${YELLOW}Or add to systemd service file if running as service.${NC}"
            echo ""
            
            # Ask about backing up old files
            echo -e "${YELLOW}Legacy Configuration Files:${NC}"
            if ask_yes_no "Create backup and remove legacy .env and config.yaml files?" "N"; then
                BACKUP_DIR="$INSTALL_ROOT/config_backup_$(date +%Y%m%d_%H%M%S)"
                mkdir -p "$BACKUP_DIR"
                
                if [ "$LEGACY_ENV_EXISTS" = true ]; then
                    mv "$ENV_FILE" "$BACKUP_DIR/"
                    echo -e "${GREEN}  Moved .env to $BACKUP_DIR/${NC}"
                fi
                
                if [ "$LEGACY_YAML_EXISTS" = true ]; then
                    mv "$CONFIG_YAML" "$BACKUP_DIR/"
                    echo -e "${GREEN}  Moved config.yaml to $BACKUP_DIR/${NC}"
                fi
                
                echo ""
                echo -e "${GREEN}Legacy files backed up to: $BACKUP_DIR${NC}"
            else
                echo -e "${YELLOW}Legacy files retained. You can remove them manually when ready.${NC}"
            fi
            
            echo ""
            echo -e "${CYAN}You can now manage your configuration using:${NC}"
            echo -e "${CYAN}  python scripts/config_tool.py --interactive${NC}"
            echo ""
            exit 0
        else
            echo ""
            echo -e "${RED}Migration failed. Please check the error messages above.${NC}"
            echo -e "${YELLOW}Your original configuration files were not modified.${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${YELLOW}Continuing with legacy configuration mode (.env file).${NC}"
        echo -e "${YELLOW}You can migrate to encrypted database later by running this script again.${NC}"
        echo ""
    fi
else
    # No existing configuration - start fresh with encrypted database
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
    
    echo -e "${YELLOW}Add this to your shell profile (~/.bashrc or ~/.bash_profile):${NC}"
    echo -e "${CYAN}  export FILAMENTBOX_CONFIG_KEY='$ENCRYPTION_KEY'${NC}"
    echo ""
    
    # Use config_tool.py for interactive setup
    launch_config_tool
fi

# ========================================
# Legacy Mode - Continue with .env configuration
# ========================================
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Legacy Configuration Mode (.env)${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# ========================================
# Legacy Mode - Continue with .env configuration
# ========================================
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Legacy Configuration Mode (.env)${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Function to read existing .env value
get_env_value() {
    local key="$1"
    local default="$2"
    
    if [ -f "$ENV_FILE" ]; then
        # Extract value from .env file, handling comments and empty lines
        local value=$(grep "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")
        if [ -n "$value" ]; then
            echo "$value"
            return
        fi
    fi
    echo "$default"
}

# Function to check if category exists in .env
category_exists_in_env() {
    local category="$1"
    
    if [ ! -f "$ENV_FILE" ]; then
        return 1
    fi
    
    # Check if any variable from this category exists
    case "$category" in
        "influxdb")
            grep -q "^INFLUXDB_" "$ENV_FILE" 2>/dev/null
            ;;
        "data_collection")
            grep -q "^DATA_COLLECTION_" "$ENV_FILE" 2>/dev/null
            ;;
        "queue")
            grep -q "^QUEUE_" "$ENV_FILE" 2>/dev/null
            ;;
        "retry")
            grep -q "^RETRY_" "$ENV_FILE" 2>/dev/null
            ;;
        "persistence")
            grep -q "^PERSISTENCE_" "$ENV_FILE" 2>/dev/null
            ;;
        "sensor")
            grep -q "^SENSOR_" "$ENV_FILE" 2>/dev/null
            ;;
        "heating_control")
            grep -q "^HEATING_" "$ENV_FILE" 2>/dev/null
            ;;
        "humidity_control")
            grep -q "^HUMIDITY_" "$ENV_FILE" 2>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

# Check if .env already exists (in legacy mode)
ENV_EXISTS=false
if [ -f "$ENV_FILE" ]; then
    ENV_EXISTS=true
    echo -e "${GREEN}Existing .env file found. Current values will be shown as defaults.${NC}"
    echo -e "${GREEN}Press Enter to keep existing values, or type new values to update.${NC}"
    echo ""
else
    echo -e "${GREEN}This script will create a .env file with your configuration.${NC}"
    echo -e "${GREEN}Press Enter to accept default values shown in [brackets].${NC}"
    echo ""
fi

# Function to read input with default (preserving existing values)
read_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_secret="${4:-false}"
    
    if [ "$is_secret" = "true" ]; then
        # For secrets, show masked default
        local display_default="$default"
        if [ ${#default} -gt 0 ] && [ "$ENV_EXISTS" = true ]; then
            display_default="********"
        fi
        read -s -p "$prompt [$display_default]: " value
        echo "" # New line after secret input
    else
        read -p "$prompt [$default]: " value
    fi
    
    if [ -z "$value" ]; then
        eval "$var_name=\"$default\""
    else
        eval "$var_name=\"$value\""
    fi
}

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

# Track which categories to configure
CONFIGURE_INFLUXDB=false
CONFIGURE_DATA_COLLECTION=false
CONFIGURE_QUEUE=false
CONFIGURE_RETRY=false
CONFIGURE_PERSISTENCE=false
CONFIGURE_SENSOR=false
CONFIGURE_HEATING=false
CONFIGURE_HUMIDITY=false

# ========================================
# Category Selection
# ========================================

# InfluxDB (always required)
CONFIGURE_INFLUXDB=true

# Data Collection
if category_exists_in_env "data_collection"; then
    CONFIGURE_DATA_COLLECTION=true
    echo -e "${CYAN}Data collection settings found in .env${NC}"
else
    echo -e "${YELLOW}Data Collection Settings${NC}"
    echo "Configure data collection intervals, batch sizes, and measurement settings."
    if ask_yes_no "Configure data collection settings?"; then
        CONFIGURE_DATA_COLLECTION=true
    fi
    echo ""
fi

# Queue
if category_exists_in_env "queue"; then
    CONFIGURE_QUEUE=true
    echo -e "${CYAN}Queue settings found in .env${NC}"
else
    echo -e "${YELLOW}Queue Settings${NC}"
    echo "Configure in-memory write queue size."
    if ask_yes_no "Configure queue settings?" "N"; then
        CONFIGURE_QUEUE=true
    fi
    echo ""
fi

# Retry
if category_exists_in_env "retry"; then
    CONFIGURE_RETRY=true
    echo -e "${CYAN}Retry settings found in .env${NC}"
else
    echo -e "${YELLOW}Retry Settings${NC}"
    echo "Configure exponential backoff, retry thresholds, and alert settings."
    if ask_yes_no "Configure retry settings?" "N"; then
        CONFIGURE_RETRY=true
    fi
    echo ""
fi

# Persistence
if category_exists_in_env "persistence"; then
    CONFIGURE_PERSISTENCE=true
    echo -e "${CYAN}Persistence settings found in .env${NC}"
else
    echo -e "${YELLOW}Persistence Settings${NC}"
    echo "Configure database path and batch limits for unsent data."
    if ask_yes_no "Configure persistence settings?" "N"; then
        CONFIGURE_PERSISTENCE=true
    fi
    echo ""
fi

# Sensor
if category_exists_in_env "sensor"; then
    CONFIGURE_SENSOR=true
    echo -e "${CYAN}Sensor settings found in .env${NC}"
else
    CONFIGURE_SENSOR=true
    echo -e "${CYAN}Sensor configuration is required${NC}"
fi

# Heating Control
if category_exists_in_env "heating_control"; then
    CONFIGURE_HEATING=true
    echo -e "${CYAN}Heating control settings found in .env${NC}"
else
    echo -e "${YELLOW}Heating Control Settings${NC}"
    echo "Enable and configure automatic heating control with temperature thresholds."
    if ask_yes_no "Configure heating control?" "N"; then
        CONFIGURE_HEATING=true
    fi
    echo ""
fi

# Humidity Control
if category_exists_in_env "humidity_control"; then
    CONFIGURE_HUMIDITY=true
    echo -e "${CYAN}Humidity control settings found in .env${NC}"
else
    echo -e "${YELLOW}Humidity Control Settings${NC}"
    echo "Enable and configure automatic humidity control (exhaust fan)."
    if ask_yes_no "Configure humidity control?" "N"; then
        CONFIGURE_HUMIDITY=true
    fi
    echo ""
fi

# ========================================
# Configuration Collection
# ========================================

# InfluxDB Configuration (Required)
echo -e "${BLUE}--- InfluxDB Configuration ---${NC}"
echo ""

INFLUXDB_HOST=$(get_env_value "INFLUXDB_HOST" "192.168.1.10")
INFLUXDB_PORT=$(get_env_value "INFLUXDB_PORT" "8086")
INFLUXDB_DATABASE=$(get_env_value "INFLUXDB_DATABASE" "filamentbox")
INFLUXDB_USERNAME=$(get_env_value "INFLUXDB_USERNAME" "admin")
INFLUXDB_PASSWORD=$(get_env_value "INFLUXDB_PASSWORD" "changeme")

read_with_default "InfluxDB Host" "$INFLUXDB_HOST" INFLUXDB_HOST
read_with_default "InfluxDB Port" "$INFLUXDB_PORT" INFLUXDB_PORT
read_with_default "InfluxDB Database Name" "$INFLUXDB_DATABASE" INFLUXDB_DATABASE
read_with_default "InfluxDB Username" "$INFLUXDB_USERNAME" INFLUXDB_USERNAME
read_with_default "InfluxDB Password" "$INFLUXDB_PASSWORD" INFLUXDB_PASSWORD true

# Data Collection Configuration
if [ "$CONFIGURE_DATA_COLLECTION" = true ]; then
    echo ""
    echo -e "${BLUE}--- Data Collection Configuration ---${NC}"
    echo ""
    
    DATA_COLLECTION_READ_INTERVAL=$(get_env_value "DATA_COLLECTION_READ_INTERVAL" "0.25")
    DATA_COLLECTION_BATCH_SIZE=$(get_env_value "DATA_COLLECTION_BATCH_SIZE" "5000")
    DATA_COLLECTION_FLUSH_INTERVAL=$(get_env_value "DATA_COLLECTION_FLUSH_INTERVAL" "2")
    DATA_COLLECTION_MEASUREMENT=$(get_env_value "DATA_COLLECTION_MEASUREMENT" "environment")
    DATA_COLLECTION_TAGS=$(get_env_value "DATA_COLLECTION_TAGS" "")
    
    read_with_default "Sensor read interval (seconds)" "$DATA_COLLECTION_READ_INTERVAL" DATA_COLLECTION_READ_INTERVAL
    read_with_default "Batch size threshold for writes" "$DATA_COLLECTION_BATCH_SIZE" DATA_COLLECTION_BATCH_SIZE
    read_with_default "Flush interval (seconds)" "$DATA_COLLECTION_FLUSH_INTERVAL" DATA_COLLECTION_FLUSH_INTERVAL
    read_with_default "Measurement name" "$DATA_COLLECTION_MEASUREMENT" DATA_COLLECTION_MEASUREMENT
    read_with_default "Custom tags (JSON format, e.g., {\"location\":\"workshop\"})" "$DATA_COLLECTION_TAGS" DATA_COLLECTION_TAGS
fi

# Queue Configuration
if [ "$CONFIGURE_QUEUE" = true ]; then
    echo ""
    echo -e "${BLUE}--- Queue Configuration ---${NC}"
    echo ""
    
    QUEUE_MAX_SIZE=$(get_env_value "QUEUE_MAX_SIZE" "10000")
    
    read_with_default "Maximum queue size" "$QUEUE_MAX_SIZE" QUEUE_MAX_SIZE
fi

# Retry Configuration
if [ "$CONFIGURE_RETRY" = true ]; then
    echo ""
    echo -e "${BLUE}--- Retry Configuration ---${NC}"
    echo ""
    
    RETRY_BACKOFF_BASE=$(get_env_value "RETRY_BACKOFF_BASE" "1")
    RETRY_BACKOFF_MAX=$(get_env_value "RETRY_BACKOFF_MAX" "300")
    RETRY_ALERT_THRESHOLD=$(get_env_value "RETRY_ALERT_THRESHOLD" "5")
    RETRY_PERSIST_ON_ALERT=$(get_env_value "RETRY_PERSIST_ON_ALERT" "true")
    
    read_with_default "Base backoff delay (seconds)" "$RETRY_BACKOFF_BASE" RETRY_BACKOFF_BASE
    read_with_default "Maximum backoff delay (seconds)" "$RETRY_BACKOFF_MAX" RETRY_BACKOFF_MAX
    read_with_default "Alert threshold (failures)" "$RETRY_ALERT_THRESHOLD" RETRY_ALERT_THRESHOLD
    read_with_default "Persist on alert (true/false)" "$RETRY_PERSIST_ON_ALERT" RETRY_PERSIST_ON_ALERT
fi

# Persistence Configuration
if [ "$CONFIGURE_PERSISTENCE" = true ]; then
    echo ""
    echo -e "${BLUE}--- Persistence Configuration ---${NC}"
    echo ""
    
    PERSISTENCE_DB_PATH=$(get_env_value "PERSISTENCE_DB_PATH" "unsent_batches.db")
    PERSISTENCE_MAX_BATCHES=$(get_env_value "PERSISTENCE_MAX_BATCHES" "50000")
    
    read_with_default "Database path for unsent batches" "$PERSISTENCE_DB_PATH" PERSISTENCE_DB_PATH
    read_with_default "Maximum batches to keep" "$PERSISTENCE_MAX_BATCHES" PERSISTENCE_MAX_BATCHES
fi

# Sensor Configuration
if [ "$CONFIGURE_SENSOR" = true ]; then
    echo ""
    echo -e "${BLUE}--- Sensor Configuration ---${NC}"
    echo ""
    
    SENSOR_TYPE=$(get_env_value "SENSOR_TYPE" "bme280")
    SENSOR_SEA_LEVEL_PRESSURE=$(get_env_value "SENSOR_SEA_LEVEL_PRESSURE" "1013.25")
    SENSOR_GPIO_PIN=$(get_env_value "SENSOR_GPIO_PIN" "4")
    
    read_with_default "Sensor type (bme280/dht22)" "$SENSOR_TYPE" SENSOR_TYPE
    if [ "$SENSOR_TYPE" = "bme280" ]; then
        read_with_default "Sea level pressure (hPa)" "$SENSOR_SEA_LEVEL_PRESSURE" SENSOR_SEA_LEVEL_PRESSURE
    fi
    if [ "$SENSOR_TYPE" = "dht22" ]; then
        read_with_default "GPIO pin number" "$SENSOR_GPIO_PIN" SENSOR_GPIO_PIN
    fi
fi

# Heating Control Configuration
if [ "$CONFIGURE_HEATING" = true ]; then
    echo ""
    echo -e "${BLUE}--- Heating Control Configuration ---${NC}"
    echo ""
    
    HEATING_ENABLED=$(get_env_value "HEATING_ENABLED" "false")
    HEATING_GPIO_PIN=$(get_env_value "HEATING_GPIO_PIN" "16")
    HEATING_MIN_TEMP_C=$(get_env_value "HEATING_MIN_TEMP_C" "18.0")
    HEATING_MAX_TEMP_C=$(get_env_value "HEATING_MAX_TEMP_C" "22.0")
    HEATING_CHECK_INTERVAL=$(get_env_value "HEATING_CHECK_INTERVAL" "1.0")
    
    read_with_default "Enable heating control (true/false)" "$HEATING_ENABLED" HEATING_ENABLED
    if [ "$HEATING_ENABLED" = "true" ]; then
        read_with_default "GPIO pin for heating relay" "$HEATING_GPIO_PIN" HEATING_GPIO_PIN
        read_with_default "Minimum temperature (°C)" "$HEATING_MIN_TEMP_C" HEATING_MIN_TEMP_C
        read_with_default "Maximum temperature (°C)" "$HEATING_MAX_TEMP_C" HEATING_MAX_TEMP_C
        read_with_default "Check interval (seconds)" "$HEATING_CHECK_INTERVAL" HEATING_CHECK_INTERVAL
    fi
fi

# Humidity Control Configuration
if [ "$CONFIGURE_HUMIDITY" = true ]; then
    echo ""
    echo -e "${BLUE}--- Humidity Control Configuration ---${NC}"
    echo ""
    
    HUMIDITY_ENABLED=$(get_env_value "HUMIDITY_ENABLED" "false")
    HUMIDITY_GPIO_PIN=$(get_env_value "HUMIDITY_GPIO_PIN" "20")
    HUMIDITY_MIN=$(get_env_value "HUMIDITY_MIN" "40.0")
    HUMIDITY_MAX=$(get_env_value "HUMIDITY_MAX" "60.0")
    HUMIDITY_CHECK_INTERVAL=$(get_env_value "HUMIDITY_CHECK_INTERVAL" "1.0")
    
    read_with_default "Enable humidity control (true/false)" "$HUMIDITY_ENABLED" HUMIDITY_ENABLED
    if [ "$HUMIDITY_ENABLED" = "true" ]; then
        read_with_default "GPIO pin for fan relay" "$HUMIDITY_GPIO_PIN" HUMIDITY_GPIO_PIN
        read_with_default "Minimum humidity (%)" "$HUMIDITY_MIN" HUMIDITY_MIN
        read_with_default "Maximum humidity (%)" "$HUMIDITY_MAX" HUMIDITY_MAX
        read_with_default "Check interval (seconds)" "$HUMIDITY_CHECK_INTERVAL" HUMIDITY_CHECK_INTERVAL
    fi
fi

# ========================================
# Configuration Summary
# ========================================

echo ""
echo -e "${BLUE}--- Configuration Summary ---${NC}"
echo ""
echo -e "${CYAN}InfluxDB:${NC}"
echo "  Host:     $INFLUXDB_HOST"
echo "  Port:     $INFLUXDB_PORT"
echo "  Database: $INFLUXDB_DATABASE"
echo "  Username: $INFLUXDB_USERNAME"
echo "  Password: ********"

if [ "$CONFIGURE_DATA_COLLECTION" = true ]; then
    echo ""
    echo -e "${CYAN}Data Collection:${NC}"
    echo "  Read Interval:   $DATA_COLLECTION_READ_INTERVAL s"
    echo "  Batch Size:      $DATA_COLLECTION_BATCH_SIZE"
    echo "  Flush Interval:  $DATA_COLLECTION_FLUSH_INTERVAL s"
    echo "  Measurement:     $DATA_COLLECTION_MEASUREMENT"
    [ -n "$DATA_COLLECTION_TAGS" ] && echo "  Tags:            $DATA_COLLECTION_TAGS"
fi

if [ "$CONFIGURE_QUEUE" = true ]; then
    echo ""
    echo -e "${CYAN}Queue:${NC}"
    echo "  Max Size: $QUEUE_MAX_SIZE"
fi

if [ "$CONFIGURE_RETRY" = true ]; then
    echo ""
    echo -e "${CYAN}Retry:${NC}"
    echo "  Backoff Base:     $RETRY_BACKOFF_BASE s"
    echo "  Backoff Max:      $RETRY_BACKOFF_MAX s"
    echo "  Alert Threshold:  $RETRY_ALERT_THRESHOLD"
    echo "  Persist on Alert: $RETRY_PERSIST_ON_ALERT"
fi

if [ "$CONFIGURE_PERSISTENCE" = true ]; then
    echo ""
    echo -e "${CYAN}Persistence:${NC}"
    echo "  DB Path:      $PERSISTENCE_DB_PATH"
    echo "  Max Batches:  $PERSISTENCE_MAX_BATCHES"
fi

if [ "$CONFIGURE_SENSOR" = true ]; then
    echo ""
    echo -e "${CYAN}Sensor:${NC}"
    echo "  Type: $SENSOR_TYPE"
    [ "$SENSOR_TYPE" = "bme280" ] && echo "  Sea Level Pressure: $SENSOR_SEA_LEVEL_PRESSURE hPa"
    [ "$SENSOR_TYPE" = "dht22" ] && echo "  GPIO Pin: $SENSOR_GPIO_PIN"
fi

if [ "$CONFIGURE_HEATING" = true ]; then
    echo ""
    echo -e "${CYAN}Heating Control:${NC}"
    echo "  Enabled: $HEATING_ENABLED"
    if [ "$HEATING_ENABLED" = "true" ]; then
        echo "  GPIO Pin:      $HEATING_GPIO_PIN"
        echo "  Min Temp:      $HEATING_MIN_TEMP_C °C"
        echo "  Max Temp:      $HEATING_MAX_TEMP_C °C"
        echo "  Check Interval: $HEATING_CHECK_INTERVAL s"
    fi
fi

if [ "$CONFIGURE_HUMIDITY" = true ]; then
    echo ""
    echo -e "${CYAN}Humidity Control:${NC}"
    echo "  Enabled: $HUMIDITY_ENABLED"
    if [ "$HUMIDITY_ENABLED" = "true" ]; then
        echo "  GPIO Pin:       $HUMIDITY_GPIO_PIN"
        echo "  Min Humidity:   $HUMIDITY_MIN %"
        echo "  Max Humidity:   $HUMIDITY_MAX %"
        echo "  Check Interval: $HUMIDITY_CHECK_INTERVAL s"
    fi
fi

echo ""
if ! ask_yes_no "Save this configuration?"; then
    echo -e "${YELLOW}Setup cancelled. No changes made.${NC}"
    exit 0
fi

# ========================================
# Save Configuration
# ========================================

# Backup existing .env if it exists
if [ "$ENV_EXISTS" = true ]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    echo ""
    echo -e "${GREEN}Existing .env backed up to:${NC}"
    echo -e "${GREEN}$BACKUP_FILE${NC}"
fi

# Create .env file
echo ""
if [ "$ENV_EXISTS" = true ]; then
    echo -e "${GREEN}Updating .env file...${NC}"
else
    echo -e "${GREEN}Creating .env file...${NC}"
fi

# Start building the .env file
cat > "$ENV_FILE" << EOF
# FilamentBox Environment Configuration
# Generated on: $(date)
# 
# This file contains sensitive configuration that overrides values in config.yaml
# DO NOT commit this file to version control!

# ========================================
# InfluxDB Connection
# ========================================
INFLUXDB_HOST=$INFLUXDB_HOST
INFLUXDB_PORT=$INFLUXDB_PORT
INFLUXDB_DATABASE=$INFLUXDB_DATABASE
INFLUXDB_USERNAME=$INFLUXDB_USERNAME
INFLUXDB_PASSWORD=$INFLUXDB_PASSWORD
EOF

# Data Collection
if [ "$CONFIGURE_DATA_COLLECTION" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Data Collection
# ========================================
DATA_COLLECTION_READ_INTERVAL=$DATA_COLLECTION_READ_INTERVAL
DATA_COLLECTION_BATCH_SIZE=$DATA_COLLECTION_BATCH_SIZE
DATA_COLLECTION_FLUSH_INTERVAL=$DATA_COLLECTION_FLUSH_INTERVAL
DATA_COLLECTION_MEASUREMENT=$DATA_COLLECTION_MEASUREMENT
EOF
    [ -n "$DATA_COLLECTION_TAGS" ] && echo "DATA_COLLECTION_TAGS=$DATA_COLLECTION_TAGS" >> "$ENV_FILE"
fi

# Queue
if [ "$CONFIGURE_QUEUE" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Queue
# ========================================
QUEUE_MAX_SIZE=$QUEUE_MAX_SIZE
EOF
fi

# Retry
if [ "$CONFIGURE_RETRY" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Retry
# ========================================
RETRY_BACKOFF_BASE=$RETRY_BACKOFF_BASE
RETRY_BACKOFF_MAX=$RETRY_BACKOFF_MAX
RETRY_ALERT_THRESHOLD=$RETRY_ALERT_THRESHOLD
RETRY_PERSIST_ON_ALERT=$RETRY_PERSIST_ON_ALERT
EOF
fi

# Persistence
if [ "$CONFIGURE_PERSISTENCE" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Persistence
# ========================================
PERSISTENCE_DB_PATH=$PERSISTENCE_DB_PATH
PERSISTENCE_MAX_BATCHES=$PERSISTENCE_MAX_BATCHES
EOF
fi

# Sensor
if [ "$CONFIGURE_SENSOR" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Sensor
# ========================================
SENSOR_TYPE=$SENSOR_TYPE
EOF
    [ "$SENSOR_TYPE" = "bme280" ] && echo "SENSOR_SEA_LEVEL_PRESSURE=$SENSOR_SEA_LEVEL_PRESSURE" >> "$ENV_FILE"
    [ "$SENSOR_TYPE" = "dht22" ] && echo "SENSOR_GPIO_PIN=$SENSOR_GPIO_PIN" >> "$ENV_FILE"
fi

# Heating Control
if [ "$CONFIGURE_HEATING" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Heating Control
# ========================================
HEATING_ENABLED=$HEATING_ENABLED
EOF
    if [ "$HEATING_ENABLED" = "true" ]; then
        cat >> "$ENV_FILE" << EOF
HEATING_GPIO_PIN=$HEATING_GPIO_PIN
HEATING_MIN_TEMP_C=$HEATING_MIN_TEMP_C
HEATING_MAX_TEMP_C=$HEATING_MAX_TEMP_C
HEATING_CHECK_INTERVAL=$HEATING_CHECK_INTERVAL
EOF
    fi
fi

# Humidity Control
if [ "$CONFIGURE_HUMIDITY" = true ]; then
    cat >> "$ENV_FILE" << EOF

# ========================================
# Humidity Control
# ========================================
HUMIDITY_ENABLED=$HUMIDITY_ENABLED
EOF
    if [ "$HUMIDITY_ENABLED" = "true" ]; then
        cat >> "$ENV_FILE" << EOF
HUMIDITY_GPIO_PIN=$HUMIDITY_GPIO_PIN
HUMIDITY_MIN=$HUMIDITY_MIN
HUMIDITY_MAX=$HUMIDITY_MAX
HUMIDITY_CHECK_INTERVAL=$HUMIDITY_CHECK_INTERVAL
EOF
    fi
fi

# Set proper permissions
chmod 600 "$ENV_FILE"

echo ""
echo -e "${GREEN}========================================${NC}"
if [ "$ENV_EXISTS" = true ]; then
    echo -e "${GREEN}Configuration Updated!${NC}"
else
    echo -e "${GREEN}Configuration Complete!${NC}"
fi
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}.env file saved at:${NC}"
echo -e "${GREEN}$ENV_FILE${NC}"
echo ""
echo -e "${YELLOW}Important Security Notes:${NC}"
echo -e "${YELLOW}1. The .env file contains sensitive credentials${NC}"
echo -e "${YELLOW}2. File permissions set to 600 (owner read/write only)${NC}"
echo -e "${YELLOW}3. DO NOT commit this file to version control${NC}"
echo -e "${YELLOW}4. Ensure .env is in your .gitignore${NC}"
if [ "$ENV_EXISTS" = true ]; then
    echo ""
    echo -e "${BLUE}A backup of your previous .env was created.${NC}"
fi
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Upgrade to Encrypted Configuration${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}FilamentBox v2.0 supports encrypted configuration database for better security.${NC}"
echo -e "${YELLOW}Run this script again to migrate from .env to encrypted database.${NC}"
echo ""
echo -e "${CYAN}Benefits of encrypted configuration:${NC}"
echo "  - Passwords encrypted at rest (256-bit AES)"
echo "  - Centralized configuration management"
echo "  - Interactive configuration tool"
echo "  - Better security than plain text files"
echo ""
