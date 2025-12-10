#!/usr/bin/env python3
"""Interactive configuration tool for FilamentBox.

Provides a CLI interface for managing encrypted configuration database.
This is the primary way to update configuration after migration.
"""

import argparse
import getpass
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filamentbox.config_db import ConfigDB, CONFIG_DB_PATH, CONFIG_DB_KEY_ENV


# Configuration schema: defines allowed configuration keys
CONFIG_SCHEMA = {
    "database": {
        "influxdb": {
            "enabled": {"type": "bool", "desc": "Enable InfluxDB data storage"},
            "url": {
                "type": "str",
                "desc": "InfluxDB server URL",
                "example": "http://192.168.1.100:8086",
            },
            "token": {
                "type": "str",
                "desc": "InfluxDB authentication token",
                "sensitive": True,
                "example": "your-token-here",
            },
            "org": {
                "type": "str",
                "desc": "InfluxDB organization name",
                "example": "myorg",
            },
            "bucket": {
                "type": "str",
                "desc": "InfluxDB bucket name",
                "example": "sensors",
            },
            "measurement": {
                "type": "str",
                "desc": "InfluxDB measurement name",
                "example": "environment",
            },
            "tags": {},  # Flexible tags - any key-value pairs allowed
        },
        "sqlite": {
            "enabled": {"type": "bool", "desc": "Enable SQLite data storage"},
            "path": {
                "type": "str",
                "desc": "Path to SQLite database file",
                "example": "/var/lib/filamentbox/data.db",
            },
        },
    },
    "sensors": {
        "bme280": {
            "enabled": {"type": "bool", "desc": "Enable BME280 sensor"},
            "i2c_address": {
                "type": "str",
                "desc": "I2C address",
                "example": "0x76",
            },
        },
        "dht22": {
            "enabled": {"type": "bool", "desc": "Enable DHT22 sensor"},
            "gpio_pin": {
                "type": "int",
                "desc": "GPIO pin number",
                "example": "4",
            },
        },
    },
    "bluetooth": {
        "enabled": {"type": "bool", "desc": "Enable Bluetooth scanning"},
        "scan_interval": {
            "type": "int",
            "desc": "Scan interval in seconds",
            "example": "60",
        },
        "device_timeout": {
            "type": "int",
            "desc": "Device timeout in seconds",
            "example": "300",
        },
    },
    "webui": {
        "enabled": {"type": "bool", "desc": "Enable web UI"},
        "host": {
            "type": "str",
            "desc": "Web UI host address",
            "example": "0.0.0.0",
        },
        "port": {
            "type": "int",
            "desc": "Web UI port number",
            "example": "5000",
        },
    },
    "notifications": {
        "telegram": {
            "enabled": {"type": "bool", "desc": "Enable Telegram notifications"},
            "bot_token": {
                "type": "str",
                "desc": "Telegram bot token",
                "sensitive": True,
                "example": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            },
            "chat_id": {
                "type": "str",
                "desc": "Telegram chat ID",
                "example": "123456789",
            },
        },
        "email": {
            "enabled": {"type": "bool", "desc": "Enable email notifications"},
            "smtp_host": {
                "type": "str",
                "desc": "SMTP server host",
                "example": "smtp.gmail.com",
            },
            "smtp_port": {
                "type": "int",
                "desc": "SMTP server port",
                "example": "587",
            },
            "username": {
                "type": "str",
                "desc": "SMTP username",
                "example": "user@example.com",
            },
            "password": {
                "type": "str",
                "desc": "SMTP password",
                "sensitive": True,
                "example": "app-password",
            },
            "from_addr": {
                "type": "str",
                "desc": "From email address",
                "example": "alerts@example.com",
            },
            "to_addr": {
                "type": "str",
                "desc": "To email address",
                "example": "admin@example.com",
            },
        },
    },
    "monitoring": {
        "interval": {
            "type": "int",
            "desc": "Data collection interval in seconds",
            "example": "60",
        },
        "log_level": {
            "type": "str",
            "desc": "Logging level",
            "example": "INFO",
        },
    },
}


# Legacy key mappings: maps old keys to new schema keys
LEGACY_KEY_MAPPINGS = {
    # Old InfluxDB keys → new database.influxdb keys
    "influxdb.host": "database.influxdb.url",
    "influxdb.port": "database.influxdb.url",  # Will need special handling to combine
    "influxdb.database": "database.influxdb.bucket",
    "influxdb.username": "database.influxdb.org",  # Username often maps to org
    "influxdb.password": "database.influxdb.token",
    "influxdb.token": "database.influxdb.token",
    "influxdb.org": "database.influxdb.org",
    "influxdb.bucket": "database.influxdb.bucket",
    "influxdb.url": "database.influxdb.url",
    # Data collection keys
    "data.collection.measurement": "database.influxdb.measurement",
    "data.collection.tags": "database.influxdb.tags",  # Special handling needed for JSON
    # Sensor keys (old flat structure → new nested)
    "sensor.bme280.enabled": "sensors.bme280.enabled",
    "sensor.bme280.address": "sensors.bme280.i2c_address",
    "sensor.dht22.enabled": "sensors.dht22.enabled",
    "sensor.dht22.pin": "sensors.dht22.gpio_pin",
    # Bluetooth keys
    "bluetooth.scan_interval": "bluetooth.scan_interval",
    "bluetooth.timeout": "bluetooth.device_timeout",
    # Web UI keys
    "webui.host": "webui.host",
    "webui.port": "webui.port",
}


def get_all_valid_keys(schema: dict, prefix: str = "") -> set[str]:
    """Recursively get all valid keys from schema."""
    valid_keys = set()

    for key, value in schema.items():
        if prefix:
            full_key = f"{prefix}.{key}"
        else:
            full_key = key

        if isinstance(value, dict):
            # Check if this is a leaf node (has 'type' key) or intermediate node
            if "type" in value:
                # Leaf node - this is a valid configuration key
                valid_keys.add(full_key)
            else:
                # Intermediate node - recurse
                valid_keys.update(get_all_valid_keys(value, full_key))

    return valid_keys


def get_key_info_from_schema(key: str) -> dict:
    """Get key information (type, desc, example) from schema."""
    parts = key.split(".")
    schema_node = CONFIG_SCHEMA

    try:
        for part in parts:
            if part in schema_node:
                schema_node = schema_node[part]
            else:
                return {}

        # If we found a leaf node with 'type', return it
        if isinstance(schema_node, dict) and "type" in schema_node:
            return schema_node
    except (KeyError, TypeError):
        pass

    return {}


def find_similar_key(invalid_key: str, valid_keys: set[str]) -> str | None:
    """Find the most similar valid key for an invalid key."""
    # First check if it's a known legacy key
    if invalid_key in LEGACY_KEY_MAPPINGS:
        return LEGACY_KEY_MAPPINGS[invalid_key]

    # Try simple transformations
    parts = invalid_key.split(".")

    # Common mistakes to check
    transformations = [
        invalid_key.lower(),
        invalid_key.upper(),
        invalid_key.replace("_", "."),
        invalid_key.replace("-", "."),
    ]

    # Check if any transformation matches a valid key
    for transform in transformations:
        if transform in valid_keys:
            return transform

    # Check for partial matches (same ending)
    if len(parts) >= 2:
        suffix = ".".join(parts[-2:])
        for valid_key in valid_keys:
            if valid_key.endswith(suffix):
                return valid_key

    # Check for keys with similar structure
    for valid_key in valid_keys:
        valid_parts = valid_key.split(".")
        if len(valid_parts) == len(parts):
            # Check if last part matches
            if valid_parts[-1] == parts[-1]:
                return valid_key

    return None


def validate_and_fix_keys(db: ConfigDB, auto_fix: bool = False) -> dict[str, str]:
    """Validate all keys in database against schema and optionally fix them.

    Returns:
        Dictionary mapping invalid keys to their suggested replacements
    """
    valid_keys = get_all_valid_keys(CONFIG_SCHEMA)
    all_db_keys = [key for key, _ in db.list_keys("")]

    invalid_keys = {}

    for db_key in all_db_keys:
        # Skip tags (they have flexible structure)
        if ".tags." in db_key:
            continue

        if db_key not in valid_keys:
            similar = find_similar_key(db_key, valid_keys)
            invalid_keys[db_key] = similar

    if auto_fix and invalid_keys:
        print_header("Auto-fixing Invalid Keys")
        for invalid_key, suggested_key in invalid_keys.items():
            if suggested_key:
                value = db.get(invalid_key)
                print(f"Migrating: {invalid_key} → {suggested_key}")
                db.set(suggested_key, value)
                db.delete(invalid_key)
                print(f"  ✓ Migrated value: {value}")
            else:
                print(f"⚠ No suggestion for: {invalid_key} (keeping as-is)")
        print()

    return invalid_keys


def fix_invalid_keys_menu(db: ConfigDB):
    """Interactive menu to fix invalid configuration keys."""
    print_header("Fix Invalid Configuration Keys")

    valid_keys = get_all_valid_keys(CONFIG_SCHEMA)
    all_db_keys = [key for key, _ in db.list_keys("")]

    invalid_keys = {}
    for db_key in all_db_keys:
        # Skip flexible tag keys (database.influxdb.tags.*)
        if db_key.startswith("database.influxdb.tags."):
            continue
        if db_key not in valid_keys:
            similar = find_similar_key(db_key, valid_keys)
            invalid_keys[db_key] = similar

    if not invalid_keys:
        print("✓ All configuration keys are valid!")
        input("\nPress Enter to continue...")
        return

    print(f"Found {len(invalid_keys)} invalid key(s):\n")

    for i, (invalid_key, suggested_key) in enumerate(invalid_keys.items(), 1):
        value = db.get(invalid_key)
        # Mask sensitive values
        if any(s in invalid_key.lower() for s in ["password", "token", "secret", "key"]):
            display_value = "********"
        else:
            display_value = value

        print(f"{i}. Invalid: {invalid_key}")
        print(f"   Value: {display_value}")
        if suggested_key:
            print(f"   Suggested: {suggested_key}")
        else:
            print("   Suggested: (no match found)")
        print()

    print("Options:")
    print("A - Auto-fix all (migrate to suggested keys)")
    print("M - Manual fix (choose for each key)")
    print("D - Delete all invalid keys")
    print("B - Back (keep invalid keys)")
    print()

    choice = input("Select option: ").strip().upper()

    if choice == "A":
        # Auto-fix all with special handling for certain key combinations
        migrated = 0
        skipped = []

        # Special handling for influxdb.host + influxdb.port → database.influxdb.url
        if "influxdb.host" in invalid_keys and "influxdb.port" in invalid_keys:
            host = db.get("influxdb.host")
            port = db.get("influxdb.port")
            if host and port:
                url = f"http://{host}:{port}"
                db.set("database.influxdb.url", url)
                db.delete("influxdb.host")
                db.delete("influxdb.port")
                print(f"✓ Combined: influxdb.host + influxdb.port → database.influxdb.url ({url})")
                migrated += 2
                # Remove from invalid_keys so we don't process them again
                invalid_keys = {
                    k: v
                    for k, v in invalid_keys.items()
                    if k not in ["influxdb.host", "influxdb.port"]
                }

        # Special handling for data.collection.tags → database.influxdb.tags.*
        if "data.collection.tags" in invalid_keys:
            import json

            tags_value = db.get("data.collection.tags")
            if tags_value:
                try:
                    # Parse JSON tags
                    if isinstance(tags_value, str):
                        tags_dict = json.loads(tags_value)
                    elif isinstance(tags_value, dict):
                        tags_dict = tags_value
                    else:
                        tags_dict = {}

                    # Create individual tag keys
                    for tag_name, tag_value in tags_dict.items():
                        tag_key = f"database.influxdb.tags.{tag_name}"
                        db.set(tag_key, tag_value)
                        print(f"✓ Migrated tag: {tag_name} → {tag_key} = {tag_value}")
                        migrated += 1

                    db.delete("data.collection.tags")
                    # Remove from invalid_keys
                    invalid_keys = {
                        k: v for k, v in invalid_keys.items() if k != "data.collection.tags"
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"⚠ Warning: Could not parse tags JSON: {e}")
                    skipped.append("data.collection.tags (invalid JSON)")

        # Process remaining keys
        for invalid_key, suggested_key in invalid_keys.items():
            if suggested_key is None:
                skipped.append(f"{invalid_key} (no suggestion)")
            else:
                value = db.get(invalid_key)

                # Special handling for certain conversions
                if invalid_key == "influxdb.username" and suggested_key == "database.influxdb.org":
                    # Username might not be the org, ask user or use as-is
                    db.set(suggested_key, value, "InfluxDB organization (migrated from username)")
                elif (
                    invalid_key == "influxdb.database"
                    and suggested_key == "database.influxdb.bucket"
                ):
                    # Database → Bucket naming
                    db.set(suggested_key, value, "InfluxDB bucket (migrated from database)")
                elif (
                    invalid_key == "influxdb.password"
                    and suggested_key == "database.influxdb.token"
                ):
                    # Password → Token (might need regeneration)
                    db.set(suggested_key, value, "InfluxDB token (migrated from password)")
                    print(
                        "⚠ Note: influxdb.password migrated to token - may need to regenerate token"
                    )
                else:
                    db.set(suggested_key, value)

                db.delete(invalid_key)
                print(f"✓ Migrated: {invalid_key} → {suggested_key}")
                migrated += 1

        if skipped:
            print("\nSkipped keys:")
            for skip in skipped:
                print(f"  ⚠ {skip}")

        print(f"\n✓ Migrated {migrated} key(s)")
        input("\nPress Enter to continue...")

    elif choice == "M":
        # Manual fix
        for invalid_key, suggested_key in invalid_keys.items():
            value = db.get(invalid_key)
            print(f"\nInvalid key: {invalid_key}")
            print(f"Value: {value}")

            if suggested_key:
                print(f"Suggested: {suggested_key}")
                action = input("Action (M=migrate, D=delete, S=skip): ").strip().upper()
            else:
                print("No suggestion available")
                action = input("Action (D=delete, S=skip): ").strip().upper()

            if action == "M" and suggested_key:
                db.set(suggested_key, value)
                db.delete(invalid_key)
                print(f"✓ Migrated to: {suggested_key}")
            elif action == "D":
                db.delete(invalid_key)
                print(f"✓ Deleted: {invalid_key}")
            else:
                print(f"Skipped: {invalid_key}")

        print("\n✓ Manual fix complete")
        input("\nPress Enter to continue...")

    elif choice == "D":
        # Delete all
        confirm = input(f"Delete all {len(invalid_keys)} invalid key(s)? (yes/no): ")
        if confirm.lower() == "yes":
            for invalid_key in invalid_keys.keys():
                db.delete(invalid_key)
            print(f"\n✓ Deleted {len(invalid_keys)} key(s)")
        else:
            print("\nCancelled")
        input("\nPress Enter to continue...")

    # else: choice == "B" or invalid, just return


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def list_config(db: ConfigDB, prefix: str = ""):
    """List configuration values."""
    print_header("Configuration Settings")

    keys = db.list_keys(prefix)
    if not keys:
        print("No configuration found.")
        return

    # Group by top-level section
    sections = {}
    for key, desc in keys:
        section = key.split(".")[0]
        if section not in sections:
            sections[section] = []
        sections[section].append((key, desc))

    for section, items in sorted(sections.items()):
        print(f"\n[{section.upper()}]")
        for key, desc in items:
            value = db.get(key)
            # Mask sensitive values
            if any(
                sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
            ):
                display_value = "********"
            else:
                display_value = value

            print(f"  {key:<40} = {display_value}")
            if desc:
                print(f"  {'':<40}   ({desc})")


def get_value(db: ConfigDB, key: str):
    """Get a single configuration value."""
    value = db.get(key)
    if value is None:
        print(f"Configuration key '{key}' not found")
        return

    print(f"\n{key} = {value}")


def set_value(db: ConfigDB, key: str, value: str = None, description: str = ""):
    """Set a configuration value interactively."""
    # Determine value type from existing config or ask user
    existing = db.get(key)

    if value is None:
        # Interactive mode
        if existing is not None:
            print(f"Current value: {existing}")

        # Check if this is a sensitive value
        is_sensitive = any(
            sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
        )

        if is_sensitive:
            value = getpass.getpass(f"Enter new value for '{key}': ")
        else:
            value = input(f"Enter new value for '{key}': ")

    # Type conversion
    if existing is not None:
        # Use same type as existing value
        if isinstance(existing, bool):
            value = value.lower() == "true"
        elif isinstance(existing, int):
            value = int(value)
        elif isinstance(existing, float):
            value = float(value)
        # else keep as string
    else:
        # Try to infer type
        if value.lower() in ["true", "false"]:
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "", 1).isdigit():
            value = float(value)
        # else keep as string

    db.set(key, value, description)
    print(f"✓ Set {key} = {value}")


def delete_value(db: ConfigDB, key: str):
    """Delete a configuration value."""
    confirm = input(f"Are you sure you want to delete '{key}'? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled")
        return

    if db.delete(key):
        print(f"✓ Deleted {key}")
    else:
        print(f"Configuration key '{key}' not found")


def interactive_menu(db: ConfigDB):
    """Interactive configuration menu with letter-based commands."""
    while True:
        print_header("FilamentBox Configuration Manager")
        print("B - Browse and edit configuration")
        print("N - Add new configuration value")
        print("S - Search for a configuration key")
        print("V - View all configuration")
        print("F - Fix invalid configuration keys")
        print("Q - Quit")
        print()

        choice = input("Select option: ").strip().upper()

        if choice == "B":
            browse_and_edit_menu(db)
        elif choice == "N":
            add_new_value(db)
        elif choice == "S":
            search_config(db)
        elif choice == "V":
            list_config(db)
            input("\nPress Enter to continue...")
        elif choice == "F":
            fix_invalid_keys_menu(db)
        elif choice == "Q":
            print("\nGoodbye!")
            break
        else:
            print("Invalid option. Please select B, N, S, V, F, or Q.")
            input("\nPress Enter to continue...")


def browse_and_edit_menu(db: ConfigDB):
    """Browse configuration by section and edit values."""
    while True:
        # Get all sections
        all_keys = db.list_keys("")
        if not all_keys:
            print("\nNo configuration found.")
            input("\nPress Enter to continue...")
            return

        sections = {}
        for key, desc in all_keys:
            section = key.split(".")[0]
            if section not in sections:
                sections[section] = []
            sections[section].append((key, desc))

        # Display section menu
        print_header("Configuration Sections")
        section_list = sorted(sections.keys())
        for i, section in enumerate(section_list, 1):
            count = len(sections[section])
            print(f"{i}. {section.upper()} ({count} settings)")
        print("B - Back to main menu")
        print()

        choice = input("Select section (number or B): ").strip().upper()

        if choice == "B":
            return

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(section_list):
                selected_section = section_list[choice_num - 1]
                edit_section_menu(db, selected_section, sections[selected_section])
            else:
                print(f"Invalid option. Please select 1-{len(section_list)} or B.")
                input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input. Please enter a number or B.")
            input("\nPress Enter to continue...")


def edit_section_menu(db: ConfigDB, section: str, keys: list):
    """Edit values within a specific section."""
    while True:
        print_header(f"{section.upper()} Configuration")

        # Display keys with current values
        for i, (key, desc) in enumerate(keys, 1):
            value = db.get(key)

            # Mask sensitive values
            if any(
                sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
            ):
                display_value = "********" if value else "(not set)"
            else:
                display_value = value if value is not None else "(not set)"

            # Show simplified key (remove section prefix for clarity)
            simple_key = key.replace(f"{section}.", "", 1)
            print(f"{i}. {simple_key:<35} = {display_value}")
            if desc:
                print(f"   {'':<35}   {desc}")

        print("B - Back to sections")
        print()

        choice = input("Select setting to edit (number or B): ").strip().upper()

        if choice == "B":
            return

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(keys):
                selected_key, selected_desc = keys[choice_num - 1]
                edit_value_menu(db, selected_key, selected_desc)
            else:
                print(f"Invalid option. Please select 1-{len(keys)} or B.")
                input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input. Please enter a number or B.")
            input("\nPress Enter to continue...")


def get_menu_options_for_key(key: str) -> list[tuple[str, str]] | None:
    """Get menu options for keys that should use menu selection.

    Returns list of (value, description) tuples, or None if key should use text input.
    """
    # Database type selection
    if key == "database.type":
        return [
            ("influxdb", "InfluxDB 1.x (username/password)"),
            ("influxdb2", "InfluxDB 2.x (token/bucket/org)"),
            ("influxdb3", "InfluxDB 3.x (cloud/serverless)"),
            ("prometheus", "Prometheus Pushgateway"),
            ("timescaledb", "TimescaleDB (PostgreSQL)"),
            ("victoriametrics", "VictoriaMetrics"),
            ("none", "No database (sensor only mode)"),
        ]

    # Sensor type selection
    if key == "sensor.type":
        return [
            ("bme280", "BME280 (I2C temperature/humidity/pressure)"),
            ("dht22", "DHT22 (GPIO temperature/humidity)"),
        ]

    # Boolean values (enabled/disabled, true/false, ssl, etc.)
    if any(pattern in key.lower() for pattern in ["enabled", ".ssl", "verify_ssl", "persist_on"]):
        return [
            ("true", "Enabled / Yes"),
            ("false", "Disabled / No"),
        ]

    # TimescaleDB SSL mode
    if key == "timescaledb.ssl_mode":
        return [
            ("disable", "Disable SSL"),
            ("allow", "Allow SSL (try SSL, fallback to non-SSL)"),
            ("prefer", "Prefer SSL (try SSL first)"),
            ("require", "Require SSL"),
            ("verify-ca", "Verify CA certificate"),
            ("verify-full", "Verify CA and hostname"),
        ]

    return None


def edit_value_with_menu(
    db: ConfigDB, key: str, description: str, options: list[tuple[str, str]]
) -> str | None:
    """Present a menu for selecting from predefined options.

    Returns selected value or None if user cancels.
    """
    current_value = db.get(key)

    print_header(f"Edit: {key}")
    if description:
        print(f"Description: {description}\n")

    print(f"Current value: {current_value}\n")
    print("Select new value:\n")

    for i, (value, desc) in enumerate(options, 1):
        marker = " ←" if str(current_value) == value else ""
        print(f"{i}. {value:<20} {desc}{marker}")

    print("C - Cancel")
    print()

    choice = input("Select option (number or C): ").strip().upper()

    if choice == "C":
        return None

    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(options):
            selected_value = options[choice_num - 1][0]
            # Convert to boolean if needed
            if selected_value in ["true", "false"]:
                return selected_value == "true"
            return selected_value
        else:
            print("Invalid option.")
            input("\nPress Enter to continue...")
            return None
    except ValueError:
        print("Invalid input.")
        input("\nPress Enter to continue...")
        return None


def is_text_input_key(key: str) -> bool:
    """Check if key should use text input (IP, port, password, etc.)."""
    text_input_patterns = [
        "host",
        "url",
        "port",
        "password",
        "token",
        "secret",
        "username",
        "database",
        "bucket",
        "org",
        "gateway_url",
        "job_name",
        "table_name",
        "db_path",
        "measurement",
        "read_interval",
        "batch_size",
        "flush_interval",
        "max_size",
        "backoff_base",
        "backoff_max",
        "alert_threshold",
        "max_batches",
        "sea_level_pressure",
        "gpio_pin",
        "min_temp",
        "max_temp",
        "min_humidity",
        "max_humidity",
        "check_interval",
        "timeout",
        "instance",
        "grouping_key",
    ]

    return any(pattern in key.lower() for pattern in text_input_patterns)


def edit_tags_menu(db: ConfigDB, base_key: str = "data_collection.tags"):
    """Special menu for editing tags (key-value pairs)."""
    while True:
        print_header("Edit Tags")

        # Get all tag keys
        all_keys = db.list_keys(base_key)
        tag_keys = [(k, d) for k, d in all_keys if k.startswith(f"{base_key}.")]

        if not tag_keys:
            print("No tags configured.\n")
        else:
            print("Current tags:\n")
            for i, (key, desc) in enumerate(tag_keys, 1):
                tag_name = key.replace(f"{base_key}.", "")
                tag_value = db.get(key)
                print(f"{i}. {tag_name:<20} = {tag_value}")

        print("\nN - Add new tag")
        print("B - Back")
        print()

        choice = input("Select option (number, N, or B): ").strip().upper()

        if choice == "B":
            return
        elif choice == "N":
            # Add new tag
            tag_name = input("\nEnter tag name: ").strip()
            if not tag_name:
                print("Tag name cannot be empty")
                input("\nPress Enter to continue...")
                continue

            tag_value = input(f"Enter value for tag '{tag_name}': ").strip()
            if not tag_value:
                print("Tag value cannot be empty")
                input("\nPress Enter to continue...")
                continue

            full_key = f"{base_key}.{tag_name}"
            db.set(full_key, tag_value, f"Tag: {tag_name}")
            print(f"\n✓ Added tag: {tag_name} = {tag_value}")
            input("\nPress Enter to continue...")
        else:
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(tag_keys):
                    # Edit existing tag
                    selected_key, selected_desc = tag_keys[choice_num - 1]
                    tag_name = selected_key.replace(f"{base_key}.", "")
                    current_value = db.get(selected_key)

                    print(f"\nEditing tag: {tag_name}")
                    print(f"Current value: {current_value}\n")
                    print("E - Change value")
                    print("D - Delete this tag")
                    print("B - Back")
                    print()

                    edit_choice = input("Select option: ").strip().upper()

                    if edit_choice == "E":
                        new_value = input(f"Enter new value for '{tag_name}': ").strip()
                        if not new_value:
                            print("Tag value cannot be empty")
                            input("\nPress Enter to continue...")
                            continue

                        db.set(selected_key, new_value, selected_desc)
                        print(f"\n✓ Updated tag: {tag_name} = {new_value}")
                        input("\nPress Enter to continue...")

                    elif edit_choice == "D":
                        confirm = input(f"Delete tag '{tag_name}'? (yes/no): ").strip().lower()
                        if confirm == "yes":
                            if db.delete(selected_key):
                                print(f"\n✓ Deleted tag: {tag_name}")
                                input("\nPress Enter to continue...")
                        else:
                            print("Cancelled")
                            input("\nPress Enter to continue...")
                    elif edit_choice == "B":
                        continue
                else:
                    print("Invalid option.")
                    input("\nPress Enter to continue...")
            except ValueError:
                print("Invalid input.")
                input("\nPress Enter to continue...")


def edit_value_menu(db: ConfigDB, key: str, description: str = ""):
    """Edit a single configuration value."""
    # Special handling for tags
    if key == "data_collection.tags":
        edit_tags_menu(db, key)
        return

    # Check if this key has predefined menu options
    menu_options = get_menu_options_for_key(key)

    if menu_options:
        # Use menu selection
        new_value = edit_value_with_menu(db, key, description, menu_options)
        if new_value is not None:
            db.set(key, new_value, description)
            print(f"\n✓ Updated {key} = {new_value}")
            input("\nPress Enter to continue...")
        return

    # Original text input flow
    while True:
        current_value = db.get(key)

        print_header(f"Edit: {key}")
        if description:
            print(f"Description: {description}\n")

        # Get example from schema
        key_info = get_key_info_from_schema(key)
        example = key_info.get("example")
        if example:
            print(f"Example: {example}\n")

        # Mask sensitive values in display
        is_sensitive = any(
            sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
        )

        if is_sensitive:
            display_value = "********" if current_value else "(not set)"
        else:
            display_value = current_value if current_value is not None else "(not set)"

        print(f"Current value: {display_value}")
        if current_value is not None:
            print(f"Value type: {type(current_value).__name__}")
        print()

        print("E - Change value")
        print("D - Delete this setting")
        print("B - Back")
        print()

        choice = input("Select option: ").strip().upper()

        if choice == "E":
            # Get new value with example in prompt
            if example and not is_sensitive:
                prompt = f"Enter new value (e.g., {example}): "
            else:
                prompt = "Enter new value: "

            if is_sensitive:
                new_value = getpass.getpass(prompt)
            else:
                new_value = input(prompt)

            if not new_value:
                print("Value cannot be empty")
                input("\nPress Enter to continue...")
                continue

            # Type conversion
            if current_value is not None:
                # Use same type as existing value
                try:
                    if isinstance(current_value, bool):
                        new_value = new_value.lower() in ["true", "1", "yes", "y"]
                    elif isinstance(current_value, int):
                        new_value = int(new_value)
                    elif isinstance(current_value, float):
                        new_value = float(new_value)
                    # else keep as string
                except ValueError:
                    print(f"Invalid value for type {type(current_value).__name__}")
                    input("\nPress Enter to continue...")
                    continue
            else:
                # Try to infer type
                if new_value.lower() in ["true", "false"]:
                    new_value = new_value.lower() == "true"
                elif new_value.isdigit():
                    new_value = int(new_value)
                elif new_value.replace(".", "", 1).replace("-", "", 1).isdigit():
                    try:
                        new_value = float(new_value)
                    except ValueError:
                        pass  # keep as string

            db.set(key, new_value, description)
            print(f"\n✓ Updated {key}")
            input("\nPress Enter to continue...")
            return

        elif choice == "D":
            confirm = input(f"Delete '{key}'? (yes/no): ").strip().lower()
            if confirm == "yes":
                if db.delete(key):
                    print(f"\n✓ Deleted {key}")
                    input("\nPress Enter to continue...")
                    return
                else:
                    print(f"\nFailed to delete {key}")
                    input("\nPress Enter to continue...")
            else:
                print("Cancelled")
                input("\nPress Enter to continue...")

        elif choice == "B":
            return

        else:
            print("Invalid option. Please select E, D, or B.")
            input("\nPress Enter to continue...")


def add_new_value(db: ConfigDB):
    """Add a new configuration value using schema-guided selection."""
    print_header("Add New Configuration")

    # Step 1: Select category
    categories = sorted(CONFIG_SCHEMA.keys())
    print("Select category:\n")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    print("Q - Cancel")
    print()

    cat_choice = input("Select category (number or Q): ").strip().upper()
    if cat_choice == "Q":
        return

    try:
        cat_idx = int(cat_choice) - 1
        if cat_idx < 0 or cat_idx >= len(categories):
            print("Invalid choice")
            input("\nPress Enter to continue...")
            return
        selected_category = categories[cat_idx]
    except ValueError:
        print("Invalid input")
        input("\nPress Enter to continue...")
        return

    # Step 2: Select subcategory (if nested)
    category_data = CONFIG_SCHEMA[selected_category]

    # Check if this category has nested subcategories or direct keys
    has_subcategories = any(
        isinstance(v, dict) and not any(k in v for k in ["type", "desc"])
        for v in category_data.values()
    )

    if has_subcategories:
        # Has subcategories
        subcategories = sorted(
            [
                k
                for k, v in category_data.items()
                if isinstance(v, dict) and not any(x in v for x in ["type", "desc"])
            ]
        )

        print(f"\nSelect {selected_category} subcategory:\n")
        for i, subcat in enumerate(subcategories, 1):
            print(f"{i}. {subcat}")
        print("B - Back")
        print()

        subcat_choice = input("Select subcategory (number or B): ").strip().upper()
        if subcat_choice == "B":
            return

        try:
            subcat_idx = int(subcat_choice) - 1
            if subcat_idx < 0 or subcat_idx >= len(subcategories):
                print("Invalid choice")
                input("\nPress Enter to continue...")
                return
            selected_subcategory = subcategories[subcat_idx]
            keys_data = category_data[selected_subcategory]
            key_prefix = f"{selected_category}.{selected_subcategory}"
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")
            return
    else:
        # Direct keys in category
        keys_data = category_data
        key_prefix = selected_category

    # Step 3: Select key
    available_keys = sorted(
        [k for k, v in keys_data.items() if isinstance(v, dict) and "type" in v]
    )

    print("\nSelect configuration key:\n")
    for i, key in enumerate(available_keys, 1):
        key_info = keys_data[key]
        desc = key_info.get("desc", "")
        full_key = f"{key_prefix}.{key}"
        existing = db.get(full_key)
        status = " (set)" if existing is not None else " (not set)"
        print(f"{i}. {key:<25} {desc}{status}")
    print("B - Back")
    print()

    key_choice = input("Select key (number or B): ").strip().upper()
    if key_choice == "B":
        return

    try:
        key_idx = int(key_choice) - 1
        if key_idx < 0 or key_idx >= len(available_keys):
            print("Invalid choice")
            input("\nPress Enter to continue...")
            return
        selected_key = available_keys[key_idx]
        key_info = keys_data[selected_key]
    except ValueError:
        print("Invalid input")
        input("\nPress Enter to continue...")
        return

    # Step 4: Enter value
    full_key = f"{key_prefix}.{selected_key}"
    existing = db.get(full_key)

    print(f"\nConfiguring: {full_key}")
    print(f"Description: {key_info.get('desc', 'No description')}")

    # Show example if available
    example = key_info.get("example")
    if example:
        print(f"Example: {example}")

    if existing is not None:
        if key_info.get("sensitive"):
            print("Current value: ********")
        else:
            print(f"Current value: {existing}")
    print()

    is_sensitive = key_info.get("sensitive", False)
    value_type = key_info.get("type", "str")

    # Get value based on type
    if value_type == "bool":
        print("Select value:")
        print("1. True")
        print("2. False")
        print()
        bool_choice = input("Select (1 or 2): ").strip()
        if bool_choice == "1":
            value = True
        elif bool_choice == "2":
            value = False
        else:
            print("Invalid choice")
            input("\nPress Enter to continue...")
            return
    else:
        # Show example in prompt for non-sensitive fields
        if example and not is_sensitive:
            prompt = f"Enter value (e.g., {example}): "
        else:
            prompt = "Enter value: "

        if is_sensitive:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)

        if not value:
            print("Value cannot be empty")
            input("\nPress Enter to continue...")
            return

        # Convert to appropriate type
        try:
            if value_type == "int":
                value = int(value)
            elif value_type == "float":
                value = float(value)
            # else keep as string
        except ValueError:
            print(f"Invalid value for type {value_type}")
            input("\nPress Enter to continue...")
            return

    # Save the value
    db.set(full_key, value, key_info.get("desc", ""))
    print(f"\n✓ Set {full_key} = {value if not is_sensitive else '********'}")
    input("\nPress Enter to continue...")


def search_config(db: ConfigDB):
    """Search for configuration keys."""
    print_header("Search Configuration")

    search_term = input("Enter search term: ").strip().lower()
    if not search_term:
        print("Search term cannot be empty")
        input("\nPress Enter to continue...")
        return

    all_keys = db.list_keys("")
    matches = [(key, desc) for key, desc in all_keys if search_term in key.lower()]

    if not matches:
        print(f"\nNo matches found for '{search_term}'")
        input("\nPress Enter to continue...")
        return

    print(f"\nFound {len(matches)} match(es):\n")
    for i, (key, desc) in enumerate(matches, 1):
        value = db.get(key)

        # Mask sensitive values
        if any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]):
            display_value = "********"
        else:
            display_value = value

        print(f"{i}. {key} = {display_value}")
        if desc:
            print(f"   {desc}")

    print("\nB - Back")
    print()

    choice = input("Select setting to edit (number or B): ").strip().upper()

    if choice == "B":
        return

    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(matches):
            selected_key, selected_desc = matches[choice_num - 1]
            edit_value_menu(db, selected_key, selected_desc)
        else:
            print("Invalid option.")
            input("\nPress Enter to continue...")
    except ValueError:
        print("Invalid input.")
        input("\nPress Enter to continue...")


def main():
    """Main entry point for configuration tool."""
    parser = argparse.ArgumentParser(description="Manage FilamentBox encrypted configuration")
    parser.add_argument("--db", default=CONFIG_DB_PATH, help="Path to config database")
    parser.add_argument("--key", default=None, help="Encryption key")
    parser.add_argument("--list", action="store_true", help="List all configuration")
    parser.add_argument("--get", metavar="KEY", help="Get configuration value")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set configuration value")
    parser.add_argument("--delete", metavar="KEY", help="Delete configuration value")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    # Get encryption key
    encryption_key = args.key or os.environ.get(CONFIG_DB_KEY_ENV)
    if not encryption_key:
        print("Error: Encryption key required")
        print(f"Set {CONFIG_DB_KEY_ENV} environment variable or use --key option")
        sys.exit(1)

    # Initialize database
    try:
        db = ConfigDB(db_path=args.db, encryption_key=encryption_key)
    except Exception as e:
        print(f"Error: Failed to open configuration database: {e}")
        print(f"Make sure the encryption key is correct and database exists at: {args.db}")
        sys.exit(1)

    # Execute command
    try:
        if args.interactive or (
            not args.list and not args.get and not args.set and not args.delete
        ):
            interactive_menu(db)
        elif args.list:
            list_config(db)
        elif args.get:
            get_value(db, args.get)
        elif args.set:
            set_value(db, args.set[0], args.set[1])
        elif args.delete:
            delete_value(db, args.delete)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        logging.exception("Configuration tool error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
