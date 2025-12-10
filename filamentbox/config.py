"""Configuration loader for FilamentBox.

Provides encrypted database configuration (preferred) with fallback to YAML + environment variables.
"""

import json
import logging
import os
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# Try to import encrypted config database
try:
    from .config_db import CONFIG_DB_PATH, ConfigDB

    HAS_CONFIG_DB = True
except ImportError:
    HAS_CONFIG_DB = False
    ConfigDB = None  # type: ignore[assignment,misc]
    CONFIG_DB_PATH = None  # type: ignore[assignment]


def _find_config_file() -> Optional[str]:
    """Return path to `config.yaml` in current directory if present, else None."""
    # Check current directory only
    if os.path.isfile("config.yaml"):
        return "config.yaml"
    return None


def _find_env_file() -> Optional[str]:
    """Return path to `.env` in current or parent directory if present, else None."""
    # Check current directory first
    if os.path.isfile(".env"):
        return ".env"
    # Check parent directory (if running from filamentbox subdir)
    if os.path.isfile("../.env"):
        return "../.env"
    return None


def _load_env_file() -> None:
    """Load environment variables from a discovered .env file (best-effort)."""
    env_file = _find_env_file()
    if env_file:
        try:
            load_dotenv(env_file)
            logging.debug(f"Loaded environment from {env_file}")
        except Exception as e:
            logging.warning(f"Failed to load {env_file}: {e}")


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """Load configuration from required YAML file, merging environment overrides.

    The YAML file must exist in the application directory (./config.yaml).

    Sensitive credentials (DB password, username) are loaded from environment
    variables, which can be set via a .env file or system environment.

    Args:
            config_path: Optional path to config.yaml. If not provided, searches application directory.

    Returns:
            Dict with config from YAML file, with env vars overriding sensitive fields.

    Raises:
            FileNotFoundError: If config.yaml is not found.
            ValueError: If YAML file is invalid or missing required fields.
    """
    # Load .env file first (if available) so environment variables are populated
    _load_env_file()

    if config_path is None:
        config_path = _find_config_file()

    if not config_path or not os.path.isfile(config_path):
        raise FileNotFoundError("config.yaml is required in the application directory")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ValueError("config.yaml must contain a YAML dictionary")
        # Validate required fields
        if "influxdb" not in config or not isinstance(config["influxdb"], dict):
            raise ValueError(
                "config.yaml must contain an 'influxdb' mapping with connection settings"
            )
        if not config["influxdb"].get("database"):
            raise ValueError(
                "config.yaml must specify 'influxdb.database' (the target InfluxDB database name)"
            )
        logging.info(f"Loaded configuration from {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load config from {config_path}: {e}")

    # Override sensitive credentials from environment variables
    # This ensures secrets are never stored in YAML or code
    if os.environ.get("INFLUXDB_USERNAME"):
        if "influxdb" not in config:
            config["influxdb"] = {}
        config["influxdb"]["username"] = os.environ["INFLUXDB_USERNAME"]
    if os.environ.get("INFLUXDB_PASSWORD"):
        if "influxdb" not in config:
            config["influxdb"] = {}
        config["influxdb"]["password"] = os.environ["INFLUXDB_PASSWORD"]
    if os.environ.get("INFLUXDB_HOST"):
        if "influxdb" not in config:
            config["influxdb"] = {}
        config["influxdb"]["host"] = os.environ["INFLUXDB_HOST"]
    if os.environ.get("INFLUXDB_PORT"):
        if "influxdb" not in config:
            config["influxdb"] = {}
        try:
            config["influxdb"]["port"] = int(os.environ["INFLUXDB_PORT"])
        except ValueError:
            logging.warning(f"Invalid INFLUXDB_PORT value: {os.environ['INFLUXDB_PORT']}")

    # Override data collection settings from environment variables
    if os.environ.get("DATA_COLLECTION_MEASUREMENT"):
        if "data_collection" not in config:
            config["data_collection"] = {}
        config["data_collection"]["measurement"] = os.environ["DATA_COLLECTION_MEASUREMENT"]

    # Parse DATA_COLLECTION_TAGS from environment (JSON format)
    if os.environ.get("DATA_COLLECTION_TAGS"):
        if "data_collection" not in config:
            config["data_collection"] = {}
        try:
            tags_json = os.environ["DATA_COLLECTION_TAGS"]
            config["data_collection"]["tags"] = json.loads(tags_json)
            logging.debug(
                f"Loaded tags from DATA_COLLECTION_TAGS: {config['data_collection']['tags']}"
            )
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse DATA_COLLECTION_TAGS as JSON: {e}")

    return config


# Global config instance (loaded on first use, not at import)
config: Optional[dict[str, Any]] = None
config_db: Optional[Any] = None  # ConfigDB instance if available
using_encrypted_db: bool = False
_config_cache: dict[str, Any] = {}  # Cache for encrypted DB values
_config_cache_loaded: bool = False


def reload_config() -> None:
    """Reload configuration from encrypted database or YAML file.

    This should be called when the configuration database has been updated
    to refresh the in-memory cache.
    """
    global config, config_db, using_encrypted_db, _config_cache, _config_cache_loaded

    logging.info("Reloading configuration...")

    if using_encrypted_db and config_db is not None:
        # Reload all values from encrypted database into cache
        try:
            _config_cache = config_db.get_all()
            _config_cache_loaded = True
            logging.info(f"Reloaded {len(_config_cache)} configuration values from database")
        except Exception as e:
            logging.error(f"Failed to reload config from database: {e}")
    elif config is not None:
        # Reload YAML configuration
        try:
            config = load_config()
            logging.info("Reloaded YAML configuration")
        except Exception as e:
            logging.error(f"Failed to reload YAML config: {e}")


def _try_load_encrypted_config() -> bool:
    """Try to load configuration from encrypted database.

    Returns:
        True if encrypted database was loaded successfully, False otherwise
    """
    global config_db, using_encrypted_db, _config_cache, _config_cache_loaded

    if not HAS_CONFIG_DB:
        logging.debug("Encrypted config database not available (SQLCipher not installed)")
        return False

    if not os.path.exists(CONFIG_DB_PATH):
        logging.debug(f"Config database not found at {CONFIG_DB_PATH}")
        return False

    try:
        # Open in read-only mode with cached connection for performance
        config_db = ConfigDB(read_only=True)
        # Load all config into cache
        _config_cache = config_db.get_all()
        _config_cache_loaded = True
        using_encrypted_db = True
        logging.info(f"Using encrypted configuration database: {CONFIG_DB_PATH}")
        logging.info(f"Loaded {len(_config_cache)} configuration values into cache")
        return True
    except Exception as e:
        logging.warning(f"Failed to load encrypted config database: {e}")
        logging.warning("Falling back to YAML configuration")
        config_db = None
        _config_cache_loaded = False
        return False


def _ensure_config_loaded():
    """Load config if not already loaded (tries encrypted DB first, then YAML)."""
    global config, using_encrypted_db

    if config is not None or config_db is not None:
        return  # Already loaded

    # Try encrypted database first
    if _try_load_encrypted_config():
        # Encrypted database is loaded, config_db is set
        return

    # Fall back to YAML configuration
    using_encrypted_db = False
    config = load_config()
    logging.info("Using YAML configuration (consider migrating to encrypted database)")


def get(key_path: str, default: Any = None) -> Any:
    """Return config value at dot-separated path or `default` if missing.

    Tries encrypted database first, falls back to YAML configuration.
    Uses in-memory cache for encrypted database for performance.

    Examples:
            get('database.influxdb.host') -> '192.168.99.2'
            get('queue.max_size') -> 10000
            get('nonexistent', 'fallback') -> 'fallback'
    """
    _ensure_config_loaded()

    # Use encrypted database cache if available
    if using_encrypted_db and _config_cache_loaded:
        return _config_cache.get(key_path, default)

    # Fall back to YAML
    keys = key_path.split(".")
    val: Any = config
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val
