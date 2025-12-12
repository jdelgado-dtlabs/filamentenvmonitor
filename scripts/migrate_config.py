#!/usr/bin/env python3
"""Migrate configuration from YAML/.env to encrypted SQLCipher database.

This script converts config.yaml and .env to an encrypted configuration database.
Run once during upgrade to v2.0.
"""

import argparse
import logging
import os
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filamentbox.config import load_config
from filamentbox.config_db import ConfigDB


def load_env_file(env_path: str) -> dict[str, Any]:
    """Load .env file and return as nested dictionary.

    Args:
        env_path: Path to .env file

    Returns:
        Nested dictionary with configuration values
    """
    from dotenv import dotenv_values

    env_vars = dotenv_values(env_path)
    config: dict[str, Any] = {}

    # Convert flat env vars to nested structure
    # Example: DATABASE_INFLUXDB_HOST -> database.influxdb.host
    for key, value in env_vars.items():
        if not value:
            continue

        # Split on underscore and convert to lowercase
        parts = key.lower().split("_")

        # Navigate/create nested structure
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value, converting types
        last_key = parts[-1]
        if value.lower() == "true":
            current[last_key] = True
        elif value.lower() == "false":
            current[last_key] = False
        elif value.replace(".", "", 1).isdigit():
            # Try to parse as number
            try:
                if "." in value:
                    current[last_key] = float(value)
                else:
                    current[last_key] = int(value)
            except ValueError:
                current[last_key] = value
        else:
            current[last_key] = value

    return config


def merge_configs(base: dict, override: dict) -> dict:
    """Recursively merge override into base.

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def migrate_yaml_to_db(
    yaml_path: str = "config.yaml",
    env_path: str = ".env",
    db_path: str | None = None,
    encryption_key: str | None = None,
    force: bool = False,
) -> bool:
    """Migrate YAML and .env configuration to encrypted database.

    Args:
        yaml_path: Path to config.yaml file
        env_path: Path to .env file
        db_path: Path to config.db (default: auto-detect)
        encryption_key: Encryption key (default: from environment)
        force: Force migration even if database exists

    Returns:
        True if successful, False otherwise
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Check if database already exists
    if db_path is None:
        from filamentbox.config_db import CONFIG_DB_PATH

        db_path = CONFIG_DB_PATH

    if os.path.exists(db_path) and not force:
        logging.error(f"Database already exists at {db_path}")
        logging.error("Use --force to overwrite existing database")
        return False

    # Load YAML configuration
    config: dict[str, Any] = {}
    if os.path.exists(yaml_path):
        try:
            logging.info(f"Loading configuration from {yaml_path}")
            yaml_config = load_config(yaml_path)
            config = merge_configs(config, yaml_config)
            logging.info(f"Loaded {len(yaml_config)} top-level sections from YAML")
        except Exception as e:
            logging.error(f"Failed to load YAML configuration: {e}")
            return False
    else:
        logging.warning(f"YAML file not found: {yaml_path}")

    # Load .env configuration (overrides YAML)
    if os.path.exists(env_path):
        try:
            logging.info(f"Loading configuration from {env_path}")
            env_config = load_env_file(env_path)
            config = merge_configs(config, env_config)
            logging.info(
                f"Loaded {sum(len(v) if isinstance(v, dict) else 1 for v in env_config.values())} values from .env"
            )
        except Exception as e:
            logging.error(f"Failed to load .env configuration: {e}")
            return False
    else:
        logging.warning(f".env file not found: {env_path}")

    if not config:
        logging.error("No configuration loaded from YAML or .env files")
        return False

    # Initialize encrypted database
    try:
        logging.info(f"Initializing encrypted database at {db_path}")
        config_db = ConfigDB(db_path=db_path, encryption_key=encryption_key)

        # Import configuration
        logging.info("Migrating configuration to encrypted database...")
        count = config_db.import_from_dict(config)
        logging.info(f"Successfully migrated {count} configuration values")

        # Verify migration
        logging.info("Verifying migration...")
        db_config = config_db.get_nested()

        # Sample verification
        sample_keys = [
            "database.type",
            "sensor.pin",
        ]
        for key in sample_keys:
            yaml_val = config
            db_val = db_config
            for k in key.split("."):
                yaml_val = yaml_val.get(k) if isinstance(yaml_val, dict) else None
                db_val = db_val.get(k) if isinstance(db_val, dict) else None

            if yaml_val != db_val:
                logging.warning(f"Mismatch for {key}: YAML={yaml_val}, DB={db_val}")
            else:
                logging.debug(f"Verified {key} = {db_val}")

        logging.info("✓ Migration completed successfully!")
        logging.info("")
        logging.info("IMPORTANT: Set the encryption key environment variable:")
        logging.info("  export FILAMENTBOX_CONFIG_KEY='your-strong-encryption-key'")
        logging.info("")
        logging.info("You can now remove config.yaml and .env files")
        logging.info(f"Configuration is stored encrypted in: {os.path.abspath(db_path)}")

        return True

    except Exception as e:
        logging.error(f"Failed to migrate configuration: {e}")
        logging.exception("Migration error details:")
        return False


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate YAML and .env configuration to encrypted database"
    )
    parser.add_argument(
        "--yaml",
        default="config.yaml",
        help="Path to config.yaml file (default: config.yaml)",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument("--db", default=None, help="Path to config.db file (default: auto-detect)")
    parser.add_argument(
        "--key",
        default=None,
        help="Encryption key (default: from FILAMENTBOX_CONFIG_KEY env var)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if database exists",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    success = migrate_yaml_to_db(
        yaml_path=args.yaml,
        env_path=args.env,
        db_path=args.db,
        encryption_key=args.key,
        force=args.force,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
