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
        elif choice == "Q":
            print("\nGoodbye!")
            break
        else:
            print("Invalid option. Please select B, N, S, V, or Q.")
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
            # Get new value
            if is_sensitive:
                new_value = getpass.getpass("Enter new value: ")
            else:
                new_value = input("Enter new value: ")

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
    """Add a new configuration value."""
    print_header("Add New Configuration")

    key = input("Enter configuration key (e.g., database.influxdb.host): ").strip()
    if not key:
        print("Key cannot be empty")
        input("\nPress Enter to continue...")
        return

    # Check if key already exists
    if db.get(key) is not None:
        print(f"\nWarning: Key '{key}' already exists")
        overwrite = input("Overwrite? (yes/no): ").strip().lower()
        if overwrite != "yes":
            print("Cancelled")
            input("\nPress Enter to continue...")
            return

    is_sensitive = any(
        sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
    )

    if is_sensitive:
        value = getpass.getpass("Enter value: ")
    else:
        value = input("Enter value: ")

    if not value:
        print("Value cannot be empty")
        input("\nPress Enter to continue...")
        return

    description = input("Enter description (optional): ").strip()

    # Type inference
    if value.lower() in ["true", "false"]:
        value = value.lower() == "true"
    elif value.isdigit():
        value = int(value)
    elif value.replace(".", "", 1).replace("-", "", 1).isdigit():
        try:
            value = float(value)
        except ValueError:
            pass  # keep as string

    db.set(key, value, description)
    print(f"\n✓ Added {key} = {value}")
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
