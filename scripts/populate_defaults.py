#!/usr/bin/env python3
"""
Populate Configuration Database with Default Values

This script reads the configuration schema and populates the encrypted
configuration database with default values for all keys that have defaults
defined in the schema.

Usage:
    python populate_defaults.py --db <db_path> --key <encryption_key>

Arguments:
    --db: Path to the SQLCipher configuration database
    --key: Encryption key for the database

Features:
    - Only sets defaults for keys that don't already exist (preserves user settings)
    - Supports nested configuration keys (e.g., database.influxdb.url)
    - Provides detailed output showing what defaults were set
    - Safe to run multiple times (idempotent)
"""

import sys
import argparse
from pathlib import Path

# Add the filamentbox directory to the Python path
SCRIPT_DIR = Path(__file__).parent.resolve()
INSTALL_ROOT = SCRIPT_DIR.parent
FILAMENTBOX_DIR = INSTALL_ROOT / "filamentbox"
sys.path.insert(0, str(FILAMENTBOX_DIR))

from config_schema import CONFIG_SCHEMA
from config_db import ConfigDB


def flatten_schema(schema, prefix=""):
    """
    Flatten the nested schema dictionary into a flat dictionary of key-value pairs.

    Args:
        schema: The configuration schema (nested dictionary)
        prefix: Current key prefix for nested keys

    Yields:
        Tuples of (key, default_value) for all keys with defaults
    """
    for key, value in schema.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Check if this is a configuration item (has 'type' field as a string)
            # vs a nested section (has 'type' as a dict or no 'type' field)
            if "type" in value and isinstance(value["type"], str):
                # This is a configuration item - check for default value
                if "default" in value:
                    yield (full_key, value["default"])
            else:
                # This is a nested section - recurse into it
                yield from flatten_schema(value, full_key)


def populate_defaults(db_path, encryption_key, verbose=True):
    """
    Populate the configuration database with default values from the schema.

    Args:
        db_path: Path to the SQLCipher database
        encryption_key: Encryption key for the database
        verbose: Whether to print detailed output

    Returns:
        Tuple of (success_count, skip_count, error_count)
    """
    # Initialize database connection
    try:
        db = ConfigDB(db_path, encryption_key)
    except Exception as e:
        print(f"ERROR: Failed to open database: {e}", file=sys.stderr)
        return (0, 0, 1)

    success_count = 0
    skip_count = 0
    error_count = 0

    # Get all defaults from schema
    defaults = list(flatten_schema(CONFIG_SCHEMA))

    if verbose:
        print(f"Found {len(defaults)} configuration keys with default values")
        print("")

    # Set defaults for keys that don't exist
    for key, default_value in defaults:
        try:
            # Check if key already exists
            existing_value = db.get(key)

            if existing_value is not None:
                # Key already has a value - skip
                if verbose:
                    print(f"  SKIP: {key} (already set to: {existing_value})")
                skip_count += 1
            else:
                # Set default value
                db.set(key, default_value, f"Default value for {key}")
                if verbose:
                    print(f"  SET:  {key} = {default_value}")
                success_count += 1

        except Exception as e:
            print(f"  ERROR: Failed to set {key}: {e}", file=sys.stderr)
            error_count += 1

    # Initialize empty dicts for tags/grouping keys (these don't have defaults in schema)
    dict_keys = {
        "database.influxdb.tags": "InfluxDB tags",
        "database.prometheus.grouping_keys": "Prometheus grouping keys (labels)",
    }

    if verbose:
        print("\nInitializing empty dicts for tags/grouping keys:")

    for key, description in dict_keys.items():
        try:
            existing_value = db.get(key)
            if existing_value is not None:
                if verbose:
                    print(f"  SKIP: {key} (already set)")
                skip_count += 1
            else:
                db.set(key, {}, description)
                if verbose:
                    print(f"  SET:  {key} = {{}}")
                success_count += 1
        except Exception as e:
            print(f"  ERROR: Failed to set {key}: {e}", file=sys.stderr)
            error_count += 1

    if verbose:
        print("")
        print("=" * 60)
        print(f"Defaults populated: {success_count}")
        print(f"Already configured: {skip_count}")
        print(f"Errors: {error_count}")
        print("=" * 60)

    return (success_count, skip_count, error_count)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Populate configuration database with default values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --db filamentbox_config.db --key "my-secret-key"
  %(prog)s --db /opt/filamentcontrol/filamentbox_config.db --key "$FILAMENTBOX_CONFIG_KEY" --quiet
        """,
    )

    parser.add_argument("--db", required=True, help="Path to the SQLCipher configuration database")

    parser.add_argument("--key", required=True, help="Encryption key for the database")

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress detailed output (only show summary)"
    )

    args = parser.parse_args()

    # Validate database path
    db_path = Path(args.db)
    if not db_path.parent.exists():
        print(f"ERROR: Database directory does not exist: {db_path.parent}", file=sys.stderr)
        sys.exit(1)

    # Populate defaults
    success, skip, errors = populate_defaults(args.db, args.key, verbose=not args.quiet)

    # Exit with error code if any errors occurred
    if errors > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
