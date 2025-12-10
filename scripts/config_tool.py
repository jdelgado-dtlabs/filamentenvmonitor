#!/usr/bin/env python3
"""Interactive configuration tool for FilamentBox.

Provides a CLI interface for managing encrypted configuration database.
This is the primary way to update configuration after migration.
"""

import argparse
import getpass
import json
import logging
import os
import subprocess
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filamentbox.config_db import ConfigDB, CONFIG_DB_PATH, CONFIG_DB_KEY_ENV
from filamentbox.config_schema import (
    CONFIG_SCHEMA,
    get_all_keys,
    get_key_info,
    validate_value,
)


class ConfigCache:
    """In-memory cache of configuration with change tracking."""

    def __init__(self, db: ConfigDB):
        """Initialize cache by loading all configuration from database.

        Args:
            db: ConfigDB instance to load from
        """
        self.db = db
        self.cache: dict[str, Any] = {}
        self.descriptions: dict[str, str] = {}
        self.changes: dict[str, tuple[Any, Any]] = {}  # key -> (old_value, new_value)
        self.deletions: set[str] = set()
        self.additions: set[str] = set()

        # Load all configuration into memory
        print("Loading configuration into memory...")
        all_data = db.get_all_with_descriptions()
        for key, value, desc in all_data:
            self.cache[key] = value
            self.descriptions[key] = desc
        print(f"Loaded {len(self.cache)} configuration value(s)")

        # If database was opened read-only, we need to be able to switch to read-write
        # Store db parameters for creating read-write connection when needed
        self._db_path = db.db_path
        self._encryption_key = db.encryption_key
        print()

    def get(self, key: str) -> Any:
        """Get a configuration value from cache.

        Args:
            key: Configuration key

        Returns:
            Value or None if not found
        """
        return self.cache.get(key)

    def set(self, key: str, value: Any, description: str = ""):
        """Set a configuration value in cache.

        Args:
            key: Configuration key
            value: New value
            description: Optional description
        """
        old_value = self.cache.get(key)

        # Track the change
        if key not in self.cache:
            # New key
            self.additions.add(key)
        elif old_value != value:
            # Modified existing key
            if key not in self.changes:
                # First modification - store original value
                self.changes[key] = (old_value, value)
            else:
                # Subsequent modification - keep original, update new
                self.changes[key] = (self.changes[key][0], value)

        # Update cache
        self.cache[key] = value
        if description:
            self.descriptions[key] = description

    def delete(self, key: str) -> bool:
        """Delete a configuration value from cache.

        Args:
            key: Configuration key

        Returns:
            True if key existed and was deleted
        """
        if key in self.cache:
            # Track deletion
            self.deletions.add(key)

            # Remove from cache
            del self.cache[key]
            if key in self.descriptions:
                del self.descriptions[key]

            # Remove from additions if it was just added this session
            if key in self.additions:
                self.additions.remove(key)

            # Remove from changes if it was modified this session
            if key in self.changes:
                del self.changes[key]

            return True
        return False

    def list_keys(self, prefix: str = "") -> list[tuple[str, str]]:
        """List all keys in cache with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of (key, description) tuples
        """
        if prefix:
            return [
                (key, self.descriptions.get(key, ""))
                for key in sorted(self.cache.keys())
                if key.startswith(prefix)
            ]
        else:
            return [(key, self.descriptions.get(key, "")) for key in sorted(self.cache.keys())]

    def has_changes(self) -> bool:
        """Check if any changes have been made.

        Returns:
            True if there are pending changes
        """
        return bool(self.changes or self.deletions or self.additions)

    def get_change_summary(self) -> str:
        """Get a summary of all pending changes.

        Returns:
            Formatted string describing all changes
        """
        lines = []

        if self.additions:
            lines.append(f"\nAdded ({len(self.additions)}):")
            for key in sorted(self.additions):
                value = self.cache[key]
                # Mask sensitive values
                if any(s in key.lower() for s in ["password", "token", "secret", "key"]):
                    display_value = "********"
                else:
                    display_value = value
                lines.append(f"  + {key} = {display_value}")

        if self.changes:
            lines.append(f"\nModified ({len(self.changes)}):")
            for key in sorted(self.changes.keys()):
                old_value, new_value = self.changes[key]
                # Mask sensitive values
                if any(s in key.lower() for s in ["password", "token", "secret", "key"]):
                    display_old = "********"
                    display_new = "********"
                else:
                    display_old = old_value
                    display_new = new_value
                lines.append(f"  ~ {key}")
                lines.append(f"    Old: {display_old}")
                lines.append(f"    New: {display_new}")

        if self.deletions:
            lines.append(f"\nDeleted ({len(self.deletions)}):")
            for key in sorted(self.deletions):
                lines.append(f"  - {key}")

        return "\n".join(lines) if lines else "\nNo changes made."

    def commit(self) -> bool:
        """Commit all pending changes to the database.

        Returns:
            True if changes were committed successfully
        """
        if not self.has_changes():
            return True

        try:
            # If database was opened read-only, create a new read-write connection
            if self.db.read_only:
                # Create new read-write database instance for committing
                write_db = ConfigDB(
                    db_path=self._db_path, encryption_key=self._encryption_key, read_only=False
                )
            else:
                write_db = self.db

            # Apply additions and modifications
            for key in self.additions:
                value = self.cache[key]
                desc = self.descriptions.get(key, "")
                write_db.set(key, value, desc)

            for key in self.changes.keys():
                value = self.cache[key]
                desc = self.descriptions.get(key, "")
                write_db.set(key, value, desc)

            # Apply deletions
            for key in self.deletions:
                write_db.delete(key)

            # Clear change tracking
            self.changes.clear()
            self.deletions.clear()
            self.additions.clear()

            return True
        except Exception as e:
            print(f"\n⚠️  Error committing changes: {e}")
            return False

    def discard_changes(self):
        """Discard all pending changes and reload from database."""
        print("\nDiscarding changes and reloading from database...")
        self.cache.clear()
        self.descriptions.clear()
        self.changes.clear()
        self.deletions.clear()
        self.additions.clear()

        # Reload from database in one bulk query
        all_data = self.db.get_all_with_descriptions()
        for key, value, desc in all_data:
            self.cache[key] = value
            self.descriptions[key] = desc
        print(f"Reloaded {len(self.cache)} configuration value(s)")


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


def validate_and_fix_keys(cache: ConfigCache, auto_fix: bool = False) -> dict[str, str]:
    """Validate all keys in cache against schema and optionally fix them.

    Returns:
        Dictionary mapping invalid keys to their suggested replacements
    """
    valid_keys = get_all_keys(CONFIG_SCHEMA)
    all_db_keys = [key for key, _ in cache.list_keys("")]

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
                value = cache.get(invalid_key)
                print(f"Migrating: {invalid_key} → {suggested_key}")
                cache.set(suggested_key, value)
                cache.delete(invalid_key)
                print(f"  ✓ Migrated value: {value}")
            else:
                print(f"⚠ No suggestion for: {invalid_key} (keeping as-is)")
        print()

    return invalid_keys


def fix_invalid_keys_menu(cache: ConfigCache):
    """Interactive menu to fix invalid configuration keys."""
    print_header("Fix Invalid Configuration Keys")

    valid_keys = get_all_keys(CONFIG_SCHEMA)
    all_db_keys = [key for key, _ in cache.list_keys("")]

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
        value = cache.get(invalid_key)
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
            host = cache.get("influxdb.host")
            port = cache.get("influxdb.port")
            if host and port:
                url = f"http://{host}:{port}"
                cache.set("database.influxdb.url", url)
                cache.delete("influxdb.host")
                cache.delete("influxdb.port")
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

            tags_value = cache.get("data.collection.tags")
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
                        cache.set(tag_key, tag_value)
                        print(f"✓ Migrated tag: {tag_name} → {tag_key} = {tag_value}")
                        migrated += 1

                    cache.delete("data.collection.tags")
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
                value = cache.get(invalid_key)

                # Special handling for certain conversions
                if invalid_key == "influxdb.username" and suggested_key == "database.influxdb.org":
                    # Username might not be the org, ask user or use as-is
                    cache.set(
                        suggested_key, value, "InfluxDB organization (migrated from username)"
                    )
                elif (
                    invalid_key == "influxdb.database"
                    and suggested_key == "database.influxdb.bucket"
                ):
                    # Database → Bucket naming
                    cache.set(suggested_key, value, "InfluxDB bucket (migrated from database)")
                elif (
                    invalid_key == "influxdb.password"
                    and suggested_key == "database.influxdb.token"
                ):
                    # Password → Token (might need regeneration)
                    cache.set(suggested_key, value, "InfluxDB token (migrated from password)")
                    print(
                        "⚠ Note: influxdb.password migrated to token - may need to regenerate token"
                    )
                else:
                    cache.set(suggested_key, value)

                cache.delete(invalid_key)
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
            value = cache.get(invalid_key)
            print(f"\nInvalid key: {invalid_key}")
            print(f"Value: {value}")

            if suggested_key:
                print(f"Suggested: {suggested_key}")
                action = input("Action (M=migrate, D=delete, S=skip): ").strip().upper()
            else:
                print("No suggestion available")
                action = input("Action (D=delete, S=skip): ").strip().upper()

            if action == "M" and suggested_key:
                cache.set(suggested_key, value)
                cache.delete(invalid_key)
                print(f"✓ Migrated to: {suggested_key}")
            elif action == "D":
                cache.delete(invalid_key)
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
                cache.delete(invalid_key)
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


def list_config(cache: ConfigCache, prefix: str = ""):
    """List configuration values."""
    print_header("Configuration Settings")

    keys = cache.list_keys(prefix)
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
            value = cache.get(key)
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


def get_value(cache: ConfigCache, key: str):
    """Get a single configuration value."""

    value = cache.get(key)
    if value is None:
        print(f"Configuration key '{key}' not found")
        return

    # Pretty-print dicts as JSON
    if isinstance(value, dict):
        print(f"\n{key} = {json.dumps(value, indent=2)}")
    else:
        print(f"\n{key} = {value}")


def set_value(cache: ConfigCache, key: str, value: str = None, description: str = ""):
    """Set a configuration value interactively."""

    # Determine value type from existing config or ask user
    existing = cache.get(key)

    if value is None:
        # Interactive mode
        if existing is not None:
            if isinstance(existing, dict):
                print(f"Current value: {json.dumps(existing, indent=2)}")
            else:
                print(f"Current value: {existing}")

        # Check if this is a sensitive value
        is_sensitive = any(
            sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
        )

        if is_sensitive:
            value = getpass.getpass(f"Enter new value for '{key}': ")
        else:
            # Check if this should be a dict/JSON value based on key name
            if "tags" in key.lower() or (existing is not None and isinstance(existing, dict)):
                print('(Enter JSON object, e.g., {"location": "garage", "device": "pi1"})')
            value = input(f"Enter new value for '{key}': ")

    # Type conversion
    # First try to parse as JSON (for dicts, lists, etc.)
    try:
        parsed_value = json.loads(value)
        # Successfully parsed JSON - use it
        cache.set(key, parsed_value, description)
        if isinstance(parsed_value, dict):
            print(f"✓ Set {key} = {json.dumps(parsed_value)}")
        else:
            print(f"✓ Set {key} = {parsed_value}")
        return
    except (json.JSONDecodeError, TypeError):
        # Not JSON, continue with type inference
        pass

    if existing is not None:
        # Use same type as existing value
        if isinstance(existing, bool):
            value = value.lower() == "true"
        elif isinstance(existing, int):
            value = int(value)
        elif isinstance(existing, float):
            value = float(value)
        elif isinstance(existing, dict):
            # Already tried JSON parsing above, this shouldn't happen
            print(f"Error: Expected JSON object for {key}")
            return
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

    cache.set(key, value, description)
    print(f"✓ Set {key} = {value}")


def delete_value(cache: ConfigCache, key: str):
    """Delete a configuration value."""
    confirm = input(f"Are you sure you want to delete '{key}'? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled")
        return

    if cache.delete(key):
        print(f"✓ Deleted {key}")
    else:
        print(f"Configuration key '{key}' not found")


def show_database_status(cache: ConfigCache):
    """Display current database configuration status."""
    print_header("Database Configuration Status")

    # Get active database type
    active_db = cache.get("database.type")

    db_info = {
        "influxdb": {
            "name": "InfluxDB",
            "keys": ["version", "url", "token", "org", "bucket", "measurement"],
        },
        "prometheus": {
            "name": "Prometheus Pushgateway",
            "keys": ["pushgateway_url", "job", "instance", "username", "password"],
        },
        "timescaledb": {
            "name": "TimescaleDB (PostgreSQL)",
            "keys": ["host", "port", "database", "username", "password", "table", "ssl_mode"],
        },
        "victoriametrics": {
            "name": "VictoriaMetrics",
            "keys": ["url", "username", "password", "tenant"],
        },
        "none": {
            "name": "None (sensor-only mode)",
            "keys": [],
        },
    }

    if not active_db:
        print("⚠ No database type configured!")
        print("\nSet 'database.type' to activate a database backend.")
        return

    if active_db not in db_info:
        print(f"⚠ Unknown database type: {active_db}")
        return

    # Display active database
    info = db_info[active_db]
    print(f"Active Database: {info['name']}")
    print(f"Database Type:   database.type = {active_db}")
    print()

    if active_db == "none":
        print("Status: No database writes will occur.")
        print("        Application will collect sensor data only.")
        return

    # Display configuration for active database
    print(f"{info['name']} Configuration:")
    print("-" * 60)

    required_keys = []
    optional_keys = []
    missing_keys = []

    for key in info["keys"]:
        full_key = f"database.{active_db}.{key}"
        value = cache.get(full_key)
        key_info = get_key_info(full_key)
        is_required = key_info.get("required", False)
        is_sensitive = key_info.get("sensitive", False)

        if is_required:
            if value is None:
                missing_keys.append(key)
            else:
                required_keys.append((key, value, is_sensitive))
        else:
            if value is not None:
                optional_keys.append((key, value, is_sensitive))

    # Display required settings
    if required_keys or missing_keys:
        print("\nRequired Settings:")
        for key, value, is_sensitive in required_keys:
            display_value = "********" if is_sensitive else value
            print(f"  ✓ {key:<20} = {display_value}")

        for key in missing_keys:
            print(f"  ✗ {key:<20} = (NOT SET)")

    # Display optional settings
    if optional_keys:
        print("\nOptional Settings:")
        for key, value, is_sensitive in optional_keys:
            display_value = "********" if is_sensitive else value
            print(f"  • {key:<20} = {display_value}")

    # Status summary
    print("\n" + "-" * 60)
    if missing_keys:
        print(f"Status: ⚠ INCOMPLETE - {len(missing_keys)} required setting(s) missing")
        print(f"\nMissing: {', '.join(missing_keys)}")
    else:
        print("Status: ✓ READY - All required settings configured")

    # Show other configured databases
    print("\n" + "=" * 60)
    print("Other Database Configurations (inactive):")
    print("-" * 60)

    other_dbs = [
        db_type for db_type in db_info.keys() if db_type != active_db and db_type != "none"
    ]
    has_other_configs = False

    for db_type in other_dbs:
        # Check if any keys are set for this database
        configured_keys = []
        for key in db_info[db_type]["keys"]:
            full_key = f"database.{db_type}.{key}"
            if cache.get(full_key) is not None:
                configured_keys.append(key)

        if configured_keys:
            has_other_configs = True
            print(f"\n{db_info[db_type]['name']}: {len(configured_keys)} setting(s) configured")
            print(f"  Keys: {', '.join(configured_keys)}")

    if not has_other_configs:
        print("\nNone - No other databases configured")
        print("You can configure multiple databases and switch between them")
        print("by changing the 'database.type' setting.")


def reset_to_defaults(cache: ConfigCache):
    """Reset all configuration to default values with confirmation."""
    print_header("Reset Configuration to Defaults")
    print()
    print("⚠️  WARNING: This will DELETE ALL existing configuration!")
    print()
    print("This action will:")
    print("  • Delete all current configuration values")
    print("  • Restore all settings to their default values")
    print("  • Cannot be undone")
    print()
    print("Default values include:")
    print("  • Database type: none (sensor-only mode)")
    print("  • All sensors: disabled")
    print("  • Heating/humidity control: disabled")
    print("  • Web UI: enabled on 0.0.0.0:5000")
    print("  • Data collection intervals: 5 seconds")
    print()

    # First confirmation
    confirm1 = input("Are you sure you want to reset to defaults? (yes/no): ").strip().lower()
    if confirm1 != "yes":
        print("\nReset cancelled.")
        input("\nPress Enter to continue...")
        return

    # Second confirmation
    print()
    print("⚠️  FINAL WARNING: All configuration will be permanently deleted!")
    print()
    confirm2 = input("Type 'DELETE ALL CONFIG' to confirm: ").strip()
    if confirm2 != "DELETE ALL CONFIG":
        print("\nReset cancelled.")
        input("\nPress Enter to continue...")
        return

    print()
    print("Deleting all configuration...")

    # Delete all existing configuration
    all_keys = cache.list_keys("")
    deleted_count = 0
    for key, _ in all_keys:  # list_keys returns (key, description) tuples
        try:
            cache.delete(key)
            deleted_count += 1
        except Exception as e:
            print(f"  Warning: Failed to delete {key}: {e}")

    print(f"  Deleted {deleted_count} configuration value(s)")
    print()
    print("Restoring default values...")
    print()

    # Call populate_defaults.py to restore defaults
    script_dir = os.path.dirname(os.path.abspath(__file__))
    populate_script = os.path.join(script_dir, "populate_defaults.py")

    # Get database path and encryption key from the ConfigCache's db instance
    db_path = cache.db.db_path
    encryption_key = cache.db.encryption_key

    try:
        # Run populate_defaults.py
        result = subprocess.run(
            [sys.executable, populate_script, "--db", db_path, "--key", encryption_key],
            capture_output=True,
            text=True,
            check=True,
        )

        # Show output
        print(result.stdout)

        # Reload cache from database
        cache.discard_changes()

        print("✓ Configuration reset to defaults successfully!")
        print()
        print("All settings have been restored to their default values.")
        print("You can now configure the application for your environment.")

    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Error restoring defaults: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        print("\nThe database may be in an inconsistent state.")
        print("Please run setup.sh again or manually configure settings.")
    except Exception as e:
        print(f"\n⚠️  Unexpected error: {e}")
        print("\nThe database may be in an inconsistent state.")

    input("\nPress Enter to continue...")


def interactive_menu(cache: ConfigCache):
    """Interactive configuration menu with letter-based commands."""
    while True:
        print_header("FilamentBox Configuration Manager")

        # Show pending changes indicator
        if cache.has_changes():
            changes_count = len(cache.additions) + len(cache.changes) + len(cache.deletions)
            print(f"⚠️  {changes_count} pending change(s) - not yet saved to database\n")

        print("B - Browse and edit configuration")
        print("N - Add new configuration value")
        print("D - Database status and configuration")
        print("S - Search for a configuration key")
        print("V - View all configuration")
        print("F - Fix invalid configuration keys")
        print("R - Reset to defaults (⚠️  deletes all config)")
        if cache.has_changes():
            print("C - Commit changes to database")
            print("X - Discard all changes")
        print("Q - Quit")
        print()

        choice = input("Select option: ").strip().upper()

        if choice == "B":
            browse_and_edit_menu(cache)
        elif choice == "N":
            add_new_value(cache)
        elif choice == "D":
            show_database_status(cache)
            input("\nPress Enter to continue...")
        elif choice == "S":
            search_config(cache)
        elif choice == "V":
            list_config(cache)
            input("\nPress Enter to continue...")
        elif choice == "F":
            fix_invalid_keys_menu(cache)
        elif choice == "R":
            reset_to_defaults(cache)
        elif choice == "C" and cache.has_changes():
            # Commit changes
            print_header("Commit Changes to Database")
            print(cache.get_change_summary())
            print()
            confirm = input("Commit these changes to database? (yes/no): ").strip().lower()
            if confirm == "yes":
                if cache.commit():
                    print("\n✓ Changes committed successfully!")
                else:
                    print("\n✗ Failed to commit changes")
            else:
                print("\nCommit cancelled")
            input("\nPress Enter to continue...")
        elif choice == "X" and cache.has_changes():
            # Discard changes
            print_header("Discard Changes")
            print(cache.get_change_summary())
            print()
            confirm = input("Discard all these changes? (yes/no): ").strip().lower()
            if confirm == "yes":
                cache.discard_changes()
                print("\n✓ Changes discarded, configuration reloaded")
            else:
                print("\nDiscard cancelled")
            input("\nPress Enter to continue...")
        elif choice == "Q":
            # Exit - check for pending changes
            if cache.has_changes():
                print_header("Exit Configuration Tool")
                print(cache.get_change_summary())
                print()
                print("Options:")
                print("1 - Commit changes and exit")
                print("2 - Discard changes and exit")
                print("3 - Cancel (return to menu)")
                print()
                exit_choice = input("Select option: ").strip()

                if exit_choice == "1":
                    # Commit and exit
                    if cache.commit():
                        print("\n✓ Changes committed successfully!")
                        print("\nGoodbye!")
                        break
                    else:
                        print("\n✗ Failed to commit changes")
                        input("\nPress Enter to return to menu...")
                elif exit_choice == "2":
                    # Discard and exit
                    print("\nDiscarding changes...")
                    print("\nGoodbye!")
                    break
                elif exit_choice == "3":
                    # Cancel exit
                    continue
                else:
                    print("Invalid option. Returning to menu...")
                    input("\nPress Enter to continue...")
            else:
                print("\nGoodbye!")
                break
        else:
            print("Invalid option. Please select a valid option.")
            input("\nPress Enter to continue...")
            input("\nPress Enter to continue...")


def browse_and_edit_menu(cache: ConfigCache):
    """Browse configuration by hierarchical navigation."""
    navigate_config_menu(cache, "", "Browse Configuration")


def navigate_config_menu(cache: ConfigCache, path: str = "", title: str = "Configuration"):
    """Unified hierarchical navigation menu for configuration.

    Args:
        cache: Configuration cache
        path: Current path in the configuration (e.g., "database.influxdb")
        title: Display title for current level
    """
    while True:
        print_header(title)

        # Show context info at top level
        if not path and path == "":
            active_db = cache.get("database.type")
            if active_db:
                db_names = {
                    "influxdb": "InfluxDB",
                    "prometheus": "Prometheus",
                    "timescaledb": "TimescaleDB",
                    "victoriametrics": "VictoriaMetrics",
                    "none": "None (sensor-only mode)",
                }
                db_name = db_names.get(active_db, active_db)
                print(f"Active Database: {db_name}\n")

        # Show database context in database section
        if path == "database":
            active_db = cache.get("database.type")
            if active_db and active_db != "none":
                db_names = {
                    "influxdb": "InfluxDB",
                    "prometheus": "Prometheus",
                    "timescaledb": "TimescaleDB",
                    "victoriametrics": "VictoriaMetrics",
                }
                db_name = db_names.get(active_db, active_db)
                print(f"Active: {db_name}\n")
            elif active_db == "none":
                print("Active: None (sensor-only mode)\n")

        # Get all items at current level
        items = get_config_items_at_path(cache, path)

        if not items:
            print("No items at this level.\n")
            print("B - Back")
            print("Q - Quit")
            print()
            choice = input("Select option: ").strip().upper()
            if choice == "B":
                return
            elif choice == "Q":
                print("\nGoodbye!")
                sys.exit(0)
            continue

        # Display items
        for i, item in enumerate(items, 1):
            if item["type"] == "subcategory":
                # Show folder icon for subcategories
                marker = ""
                if path == "database" and item["name"] in [
                    "influxdb",
                    "prometheus",
                    "timescaledb",
                    "victoriametrics",
                ]:
                    active_db = cache.get("database.type")
                    if item["name"] != active_db:
                        marker = " [inactive]"
                print(f"{i}. {item['name']:<35} → {item.get('desc', 'Subcategory')}{marker}")
            else:
                # Show key with value
                value = item["value"]
                # Mask sensitive values
                if any(s in item["key"].lower() for s in ["password", "token", "secret", "key"]):
                    display_value = "********" if value is not None else "(not set)"
                else:
                    display_value = value if value is not None else "(not set)"

                desc_text = f"({item.get('desc', '')})" if item.get("desc") else ""
                print(f"{i}. {item['name']:<35} = {display_value}")
                if desc_text:
                    print(f"   {'':<35}   {desc_text}")

        print()
        print("B - Back")
        print("Q - Quit")
        print()

        choice = input("Select item (number, B, or Q): ").strip().upper()

        if choice == "B":
            return
        elif choice == "Q":
            print("\nGoodbye!")
            sys.exit(0)

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(items):
                selected = items[choice_num - 1]

                if selected["type"] == "subcategory":
                    # Navigate deeper
                    new_path = f"{path}.{selected['name']}" if path else selected["name"]
                    new_title = f"{title} → {selected['name'].upper()}"
                    navigate_config_menu(cache, new_path, new_title)
                else:
                    # Edit the value
                    edit_value_menu(cache, selected["key"], selected.get("desc", ""))
            else:
                print(f"Invalid option. Please select 1-{len(items)} or B.")
                input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input. Please enter a number or B.")
            input("\nPress Enter to continue...")


def get_config_items_at_path(cache: ConfigCache, path: str) -> list[dict]:
    """Get configuration items (subcategories and keys) at a specific path.

    Args:
        cache: Configuration cache
        path: Current path (e.g., "database.influxdb")

    Returns:
        List of items with 'type' ('subcategory' or 'key'), 'name', 'key', 'value', 'desc'
    """
    items = []
    seen_subcats = set()

    # Get all keys from cache
    all_keys = cache.list_keys("")

    # Also get schema keys to show unset items
    schema_keys = get_all_keys(CONFIG_SCHEMA)

    # Combine both sources
    all_possible_keys = set()
    for key, _ in all_keys:
        all_possible_keys.add(key)
    for key in schema_keys:
        all_possible_keys.add(key)

    for key in sorted(all_possible_keys):
        # Check if key is at current path level
        if path:
            if not key.startswith(path + "."):
                continue
            # Remove the path prefix
            relative_key = key[len(path) + 1 :]
        else:
            relative_key = key

        # Split to get immediate child
        parts = relative_key.split(".")

        if len(parts) == 1:
            # This is a direct key at this level
            value = cache.get(key)
            key_info = get_key_info(key)
            items.append(
                {
                    "type": "key",
                    "name": parts[0],
                    "key": key,
                    "value": value,
                    "desc": key_info.get("desc", ""),
                }
            )
        else:
            # This is a subcategory
            subcat_name = parts[0]
            if subcat_name not in seen_subcats:
                seen_subcats.add(subcat_name)
                # Get description from schema if available
                subcat_path = f"{path}.{subcat_name}" if path else subcat_name
                desc = get_subcategory_description(subcat_path)
                items.append({"type": "subcategory", "name": subcat_name, "desc": desc})

    # Sort: subcategories first, then keys
    items.sort(key=lambda x: (0 if x["type"] == "subcategory" else 1, x["name"]))

    return items


def get_subcategory_description(path: str) -> str:
    """Get a friendly description for a subcategory from schema.

    Args:
        path: Path to subcategory (e.g., "database.influxdb")

    Returns:
        Description string
    """
    descriptions = {
        "database": "Database Configuration",
        "database.influxdb": "InfluxDB Settings",
        "database.prometheus": "Prometheus Pushgateway Settings",
        "database.timescaledb": "TimescaleDB (PostgreSQL) Settings",
        "database.victoriametrics": "VictoriaMetrics Settings",
        "sensors": "Sensor Configuration",
        "sensors.bme280": "BME280 Sensor Settings",
        "sensors.dht22": "DHT22 Sensor Settings",
        "bluetooth": "Bluetooth Configuration",
        "webui": "Web UI Configuration",
        "data_collection": "Data Collection Settings",
        "heating_control": "Heating Control Settings",
        "humidity_control": "Humidity Control Settings",
        "alerts": "Alert Configuration",
        "persistence": "Data Persistence Settings",
    }
    return descriptions.get(path, "Configuration")


def get_menu_options_for_key(key: str) -> list[tuple[str, str]] | None:
    """Get menu options for keys that should use menu selection.

    Returns list of (value, description) tuples, or None if key should use text input.
    """
    # Database type selection
    if key == "database.type":
        return [
            ("influxdb", "InfluxDB (v1/v2/v3)"),
            ("prometheus", "Prometheus Pushgateway"),
            ("timescaledb", "TimescaleDB (PostgreSQL)"),
            ("victoriametrics", "VictoriaMetrics"),
            ("none", "No database (sensor-only mode)"),
        ]

    # InfluxDB version selection
    if key == "database.influxdb.version":
        return [
            ("1", "InfluxDB 1.x (username/password)"),
            ("2", "InfluxDB 2.x (token/bucket/org)"),
            ("3", "InfluxDB 3.x (cloud/serverless)"),
        ]

    # TimescaleDB SSL mode (must come before general SSL pattern)
    if key == "database.timescaledb.ssl_mode":
        return [
            ("disable", "Disable SSL"),
            ("allow", "Allow SSL (try SSL, fallback to non-SSL)"),
            ("prefer", "Prefer SSL (try SSL first)"),
            ("require", "Require SSL"),
            ("verify-ca", "Verify CA certificate"),
            ("verify-full", "Verify CA and hostname"),
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

    return None


def edit_value_with_menu(
    cache: ConfigCache, key: str, description: str, options: list[tuple[str, str]]
) -> str | None:
    """Present a menu for selecting from predefined options.

    Returns selected value or None if user cancels.
    """
    current_value = cache.get(key)

    print_header(f"Edit: {key}")
    if description:
        print(f"Description: {description}\n")

    print(f"Current value: {current_value}\n")
    print("Select new value:\n")

    for i, (value, desc) in enumerate(options, 1):
        marker = " ←" if str(current_value) == value else ""
        print(f"{i}. {value:<20} {desc}{marker}")

    print("C - Cancel")
    print("Q - Quit")
    print()

    choice = input("Select option (number, C, or Q): ").strip().upper()

    if choice == "C":
        return None
    elif choice == "Q":
        print("\nGoodbye!")
        sys.exit(0)

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


def edit_tags_menu(cache: ConfigCache, base_key: str = "data_collection.tags"):
    """Special menu for editing tags (key-value pairs)."""
    while True:
        print_header("Edit Tags")

        # Get all tag keys
        all_keys = cache.list_keys(base_key)
        tag_keys = [(k, d) for k, d in all_keys if k.startswith(f"{base_key}.")]

        if not tag_keys:
            print("No tags configured.\n")
        else:
            print("Current tags:\n")
            for i, (key, desc) in enumerate(tag_keys, 1):
                tag_name = key.replace(f"{base_key}.", "")
                tag_value = cache.get(key)
                print(f"{i}. {tag_name:<20} = {tag_value}")

        print("\nN - Add new tag")
        print("B - Back")
        print("Q - Quit")
        print()

        choice = input("Select option (number, N, B, or Q): ").strip().upper()

        if choice == "B":
            return
        elif choice == "Q":
            print("\nGoodbye!")
            sys.exit(0)
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
            cache.set(full_key, tag_value, f"Tag: {tag_name}")
            print(f"\n✓ Added tag: {tag_name} = {tag_value}")
            input("\nPress Enter to continue...")
        else:
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(tag_keys):
                    # Edit existing tag
                    selected_key, selected_desc = tag_keys[choice_num - 1]
                    tag_name = selected_key.replace(f"{base_key}.", "")
                    current_value = cache.get(selected_key)

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

                        cache.set(selected_key, new_value, selected_desc)
                        print(f"\n✓ Updated tag: {tag_name} = {new_value}")
                        input("\nPress Enter to continue...")

                    elif edit_choice == "D":
                        confirm = input(f"Delete tag '{tag_name}'? (yes/no): ").strip().lower()
                        if confirm == "yes":
                            if cache.delete(selected_key):
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


def edit_value_menu(cache: ConfigCache, key: str, description: str = ""):
    """Edit a single configuration value."""
    # Special handling for tags and grouping keys (dict-based key-value pairs)
    if key in ["database.influxdb.tags", "database.prometheus.grouping_keys"]:
        # For dict-based tags, use submenu with individual tag management
        import json

        # Determine label based on key type
        item_label = "grouping key" if "grouping_keys" in key else "tag"
        items_label = "grouping keys" if "grouping_keys" in key else "tags"

        while True:
            current_value = cache.get(key)
            if not isinstance(current_value, dict):
                current_value = {}

            print_header(f"Edit: {key}")
            if description:
                print(f"Description: {description}\n")

            if current_value:
                print(f"Current {items_label}:\n")
                for tag_name, tag_value in sorted(current_value.items()):
                    print(f"  {tag_name:<20} = {tag_value}")
                print()
            else:
                print(f"No {items_label} configured.\n")

            print(f"A - Add/Edit {item_label}")
            print(f"D - Delete {item_label}")
            print("J - Edit as JSON (advanced)")
            print(f"C - Clear all {items_label}")
            print("B - Back")
            print("Q - Quit")
            print()

            choice = input("Select option: ").strip().upper()

            if choice == "Q":
                print("\nGoodbye!")
                sys.exit(0)
            elif choice == "B":
                return
            elif choice == "A":
                # Add or edit a tag/key
                tag_name = input(f"\nEnter {item_label} name: ").strip()
                if not tag_name:
                    print(f"{item_label.capitalize()} name cannot be empty")
                    input("\nPress Enter to continue...")
                    continue

                if tag_name in current_value:
                    print(f"Current value: {current_value[tag_name]}")

                tag_value = input(f"Enter value for '{tag_name}': ").strip()
                if not tag_value:
                    print(f"{item_label.capitalize()} value cannot be empty")
                    input("\nPress Enter to continue...")
                    continue

                current_value[tag_name] = tag_value
                cache.set(key, current_value, description)
                print(f"\n✓ Set {tag_name} = {tag_value}")
                input("\nPress Enter to continue...")

            elif choice == "D":
                # Delete a tag/key
                if not current_value:
                    print(f"\nNo {items_label} to delete")
                    input("\nPress Enter to continue...")
                    continue

                tag_name = input(f"\nEnter {item_label} name to delete: ").strip()
                if tag_name in current_value:
                    del current_value[tag_name]
                    cache.set(key, current_value, description)
                    print(f"\n✓ Deleted {item_label}: {tag_name}")
                else:
                    print(f"\n✗ {item_label.capitalize()} '{tag_name}' not found")
                input("\nPress Enter to continue...")

            elif choice == "J":
                # Edit as JSON
                print("\nEnter JSON object (or press Enter to cancel):")
                if current_value:
                    print(f"Current: {json.dumps(current_value)}")

                new_value = input("> ").strip()
                if not new_value:
                    continue

                try:
                    parsed_value = json.loads(new_value)
                    if not isinstance(parsed_value, dict):
                        print(
                            "\n✗ Error: Value must be a JSON object (dict), not a list or primitive"
                        )
                        input("\nPress Enter to continue...")
                        continue

                    cache.set(key, parsed_value, description)
                    print(f"\n✓ Updated {key}")
                    input("\nPress Enter to continue...")
                except json.JSONDecodeError as e:
                    print(f"\n✗ Invalid JSON: {e}")
                    input("\nPress Enter to continue...")

            elif choice == "C":
                # Clear all tags/keys
                confirm = input(f"Clear all {items_label}? (yes/no): ").strip().lower()
                if confirm == "yes":
                    cache.set(key, {}, description)
                    print(f"\n✓ Cleared all {items_label}")
                    input("\nPress Enter to continue...")
            else:
                print("Invalid option.")
                input("\nPress Enter to continue...")
        return

    # Check if this key has predefined menu options
    menu_options = get_menu_options_for_key(key)

    if menu_options:
        # Use menu selection
        new_value = edit_value_with_menu(cache, key, description, menu_options)
        if new_value is not None:
            cache.set(key, new_value, description)
            print(f"\n✓ Updated {key} = {new_value}")
            input("\nPress Enter to continue...")
        return

    # Original text input flow
    while True:
        current_value = cache.get(key)

        print_header(f"Edit: {key}")
        if description:
            print(f"Description: {description}\n")

        # Get example from schema
        key_info = get_key_info(key)
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
        print("Q - Quit")
        print()

        choice = input("Select option (E, D, B, or Q): ").strip().upper()

        if choice == "Q":
            print("\nGoodbye!")
            sys.exit(0)
        elif choice == "E":
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

            # Validate the value
            key_info = get_key_info(key)
            is_valid, error_msg, converted_value = validate_value(key, new_value, key_info)
            if not is_valid:
                print(f"\n✗ Validation error: {error_msg}")
                input("\nPress Enter to continue...")
                continue

            cache.set(key, converted_value, description)
            print(f"\n✓ Updated {key}")
            input("\nPress Enter to continue...")
            return

        elif choice == "D":
            confirm = input(f"Delete '{key}'? (yes/no): ").strip().lower()
            if confirm == "yes":
                if cache.delete(key):
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


def add_new_value(cache: ConfigCache):
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
        existing = cache.get(full_key)
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
    existing = cache.get(full_key)

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

    # Validate the value
    is_valid, error_msg, converted_value = validate_value(full_key, value, key_info)
    if not is_valid:
        print(f"\n✗ Validation error: {error_msg}")
        input("\nPress Enter to continue...")
        return

    # Save the validated and converted value
    cache.set(full_key, converted_value, key_info.get("desc", ""))
    print(f"\n✓ Set {full_key} = {converted_value if not is_sensitive else '********'}")
    input("\nPress Enter to continue...")


def search_config(cache: ConfigCache):
    """Search for configuration keys."""
    print_header("Search Configuration")

    search_term = input("Enter search term: ").strip().lower()
    if not search_term:
        print("Search term cannot be empty")
        input("\nPress Enter to continue...")
        return

    all_keys = cache.list_keys("")
    matches = [(key, desc) for key, desc in all_keys if search_term in key.lower()]

    if not matches:
        print(f"\nNo matches found for '{search_term}'")
        input("\nPress Enter to continue...")
        return

    print(f"\nFound {len(matches)} match(es):\n")
    for i, (key, desc) in enumerate(matches, 1):
        value = cache.get(key)

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
            edit_value_menu(cache, selected_key, selected_desc)
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

    # Determine if we need read-write access
    # Only need read-write for set/delete operations, otherwise read-only is fine
    read_only = not (args.set or args.delete)

    # Initialize database in read-only mode for reading (avoids WAL files)
    # Will create read-write connection only when committing changes
    try:
        db = ConfigDB(db_path=args.db, encryption_key=encryption_key, read_only=read_only)
    except Exception as e:
        print(f"Error: Failed to open configuration database: {e}")
        print(f"Make sure the encryption key is correct and database exists at: {args.db}")
        sys.exit(1)

    # Initialize cache
    cache = ConfigCache(db)

    # Execute command
    try:
        if args.interactive or (
            not args.list and not args.get and not args.set and not args.delete
        ):
            # Interactive mode - uses cache with exit confirmation
            interactive_menu(cache)
        elif args.list:
            # Non-interactive mode - read-only, no cache needed
            list_config(cache)
        elif args.get:
            # Non-interactive mode - read-only, no cache needed
            get_value(cache, args.get)
        elif args.set:
            # Non-interactive mode - direct write to database
            set_value(cache, args.set[0], args.set[1])
            # Auto-commit in non-interactive mode
            if cache.has_changes():
                print("\nCommitting changes to database...")
                cache.commit()
                print("✓ Changes committed")
        elif args.delete:
            # Non-interactive mode - direct write to database
            delete_value(cache, args.delete)
            # Auto-commit in non-interactive mode
            if cache.has_changes():
                print("\nCommitting changes to database...")
                cache.commit()
                print("✓ Changes committed")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        # Check for pending changes
        if cache.has_changes():
            print("\n⚠️  Warning: Uncommitted changes will be lost!")
            print(cache.get_change_summary())
            print()
            confirm = input("Commit changes before exit? (yes/no): ").strip().lower()
            if confirm == "yes":
                cache.commit()
                print("✓ Changes committed")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        logging.exception("Configuration tool error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
