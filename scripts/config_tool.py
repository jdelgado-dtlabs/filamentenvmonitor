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
    """Interactive configuration menu."""
    while True:
        print_header("FilamentBox Configuration Manager")
        print("1. List all configuration")
        print("2. List specific section (e.g., database)")
        print("3. Get configuration value")
        print("4. Set configuration value")
        print("5. Delete configuration value")
        print("6. Exit")
        print()

        choice = input("Select option (1-6): ").strip()

        if choice == "1":
            list_config(db)
        elif choice == "2":
            prefix = input("Enter section name (e.g., database, sensor): ").strip()
            list_config(db, prefix)
        elif choice == "3":
            key = input("Enter configuration key: ").strip()
            get_value(db, key)
        elif choice == "4":
            key = input("Enter configuration key: ").strip()
            description = input("Enter description (optional): ").strip()
            set_value(db, key, description=description)
        elif choice == "5":
            key = input("Enter configuration key: ").strip()
            delete_value(db, key)
        elif choice == "6":
            print("\nGoodbye!")
            break
        else:
            print("Invalid option")

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
