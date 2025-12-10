#!/usr/bin/env python3
"""Migrate configuration from YAML to encrypted SQLCipher database.

This script converts config.yaml to an encrypted configuration database.
Run once during upgrade to v2.0.
"""

import argparse
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filamentbox.config import load_config
from filamentbox.config_db import ConfigDB


def migrate_yaml_to_db(
    yaml_path: str = "config.yaml",
    db_path: str = None,
    encryption_key: str = None,
    force: bool = False,
) -> bool:
    """Migrate YAML configuration to encrypted database.

    Args:
        yaml_path: Path to config.yaml file
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
    try:
        logging.info(f"Loading configuration from {yaml_path}")
        config = load_config(yaml_path)
        logging.info(f"Loaded {len(config)} top-level configuration sections")
    except Exception as e:
        logging.error(f"Failed to load YAML configuration: {e}")
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
            "data_collection.enabled",
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
    parser = argparse.ArgumentParser(description="Migrate YAML configuration to encrypted database")
    parser.add_argument(
        "--yaml",
        default="config.yaml",
        help="Path to config.yaml file (default: config.yaml)",
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
        db_path=args.db,
        encryption_key=args.key,
        force=args.force,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
