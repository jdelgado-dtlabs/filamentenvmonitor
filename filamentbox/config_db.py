"""Encrypted configuration database using SQLCipher.

Provides secure storage for application configuration including sensitive credentials.
Replaces YAML + .env configuration with encrypted SQLite database.
"""

import json
import logging
import os
from typing import Any, Optional

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    try:
        # Try sqlcipher3 (modern package, Python 3.13+ compatible)
        from sqlcipher3 import dbapi2 as sqlcipher
    except ImportError:
        sqlcipher = None

try:
    import hvac
except ImportError:
    hvac = None

# Configuration database path
CONFIG_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "config.db")

# Encryption key file path
CONFIG_DB_KEY_FILE = os.path.join(os.path.dirname(__file__), "..", ".config_key")

# Encryption key environment variable
CONFIG_DB_KEY_ENV = "FILAMENTBOX_CONFIG_KEY"

# HashiCorp Vault configuration
VAULT_ADDR_ENV = "VAULT_ADDR"
VAULT_TOKEN_ENV = "VAULT_TOKEN"
VAULT_ROLE_ID_ENV = "VAULT_ROLE_ID"
VAULT_SECRET_ID_ENV = "VAULT_SECRET_ID"
VAULT_NAMESPACE_ENV = "VAULT_NAMESPACE"
VAULT_KEY_PATH = "secret/data/filamentbox/config_key"  # KV v2 path

# Default encryption key (MUST be changed in production)
DEFAULT_ENCRYPTION_KEY = "CHANGE_ME_IN_PRODUCTION_USE_STRONG_KEY"


def _get_vault_client() -> Optional[Any]:
    """Initialize and authenticate HashiCorp Vault client.

    Supports authentication methods:
    1. Token authentication (VAULT_TOKEN)
    2. AppRole authentication (VAULT_ROLE_ID + VAULT_SECRET_ID)

    Returns:
        Authenticated hvac.Client or None if Vault is not available/configured
    """
    if hvac is None:
        return None

    vault_addr = os.environ.get(VAULT_ADDR_ENV)
    if not vault_addr:
        return None

    try:
        client = hvac.Client(url=vault_addr)

        # Set namespace if provided (Vault Enterprise feature)
        namespace = os.environ.get(VAULT_NAMESPACE_ENV)
        if namespace:
            client.namespace = namespace

        # Try token authentication first
        vault_token = os.environ.get(VAULT_TOKEN_ENV)
        if vault_token:
            client.token = vault_token
            if client.is_authenticated():
                logging.info("Vault: Authenticated using token")
                return client

        # Try AppRole authentication
        role_id = os.environ.get(VAULT_ROLE_ID_ENV)
        secret_id = os.environ.get(VAULT_SECRET_ID_ENV)
        if role_id and secret_id:
            auth_response = client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            client.token = auth_response["auth"]["client_token"]
            if client.is_authenticated():
                logging.info("Vault: Authenticated using AppRole")
                return client

        logging.warning("Vault: No valid authentication method found")
        return None

    except Exception as e:
        logging.warning(f"Vault: Failed to initialize client: {e}")
        return None


def _load_key_from_vault() -> Optional[str]:
    """Load encryption key from HashiCorp Vault.

    Returns:
        Encryption key string or None if not available
    """
    client = _get_vault_client()
    if not client:
        return None

    try:
        # Read secret from KV v2 engine
        secret_response = client.secrets.kv.v2.read_secret_version(
            path="filamentbox/config_key", mount_point="secret"
        )

        key = secret_response["data"]["data"].get("key")
        if key:
            logging.info("Vault: Successfully retrieved encryption key")
            return key
        else:
            logging.warning("Vault: Key not found in secret data")
            return None

    except Exception as e:
        logging.warning(f"Vault: Failed to read encryption key: {e}")
        return None


def _save_key_to_vault(key: str) -> bool:
    """Save encryption key to HashiCorp Vault.

    Args:
        key: Encryption key to save

    Returns:
        True if successful, False otherwise
    """
    client = _get_vault_client()
    if not client:
        return False

    try:
        # Write secret to KV v2 engine
        client.secrets.kv.v2.create_or_update_secret(
            path="filamentbox/config_key", secret={"key": key}, mount_point="secret"
        )
        logging.info("Vault: Successfully saved encryption key")
        return True

    except Exception as e:
        logging.error(f"Vault: Failed to save encryption key: {e}")
        return False


def _load_encryption_key() -> str:
    """Load encryption key from available sources.

    Priority:
    1. FILAMENTBOX_CONFIG_KEY environment variable
    2. HashiCorp Vault (if configured)
    3. .config_key file in application root
    4. Default key (with warning)

    Returns:
        Encryption key string
    """
    # Try environment variable first
    key = os.environ.get(CONFIG_DB_KEY_ENV)
    if key:
        logging.info("Using encryption key from environment variable")
        return key

    # Try HashiCorp Vault
    key = _load_key_from_vault()
    if key:
        return key

    # Try key file
    if os.path.exists(CONFIG_DB_KEY_FILE):
        try:
            with open(CONFIG_DB_KEY_FILE, "r") as f:
                key = f.read().strip()
                if key:
                    logging.info("Using encryption key from local file")
                    return key
        except Exception as e:
            logging.warning(f"Failed to read key file {CONFIG_DB_KEY_FILE}: {e}")

    # Fall back to default (with warning)
    logging.warning("Using default encryption key - not suitable for production!")
    return DEFAULT_ENCRYPTION_KEY


class ConfigDB:
    """Encrypted configuration database manager."""

    def __init__(self, db_path: str = CONFIG_DB_PATH, encryption_key: Optional[str] = None):
        """Initialize the configuration database.

        Args:
            db_path: Path to the SQLCipher database file
            encryption_key: Encryption key (if None, loads from environment, key file, or uses default)
        """
        if sqlcipher is None:
            raise ImportError(
                "SQLCipher not installed. Install with: pip install pysqlcipher3 (Python <3.13) "
                "or pip install sqlcipher3-binary (Python 3.13+)"
            )

        self.db_path = db_path

        # Get encryption key from parameter, environment, or key file
        if encryption_key is None:
            encryption_key = _load_encryption_key()

        if encryption_key == DEFAULT_ENCRYPTION_KEY:
            logging.warning(
                "Using default encryption key! Set FILAMENTBOX_CONFIG_KEY environment variable "
                "or create .config_key file for production."
            )

        self.encryption_key = encryption_key
        self._init_db()

    def _get_connection(self):
        """Get a database connection with encryption enabled."""
        conn = sqlcipher.connect(self.db_path)
        # Set the encryption key
        conn.execute(f"PRAGMA key = '{self.encryption_key}'")
        # Use WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self) -> None:
        """Initialize the configuration database schema."""
        try:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    description TEXT,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_key ON config(key)
            """)
            conn.commit()
            conn.close()
            logging.debug(f"Initialized config database at {self.db_path}")
        except Exception as e:
            logging.error(f"Failed to initialize config database: {e}")
            raise

    def set(self, key: str, value: Any, description: str = "") -> None:
        """Set a configuration value.

        Args:
            key: Configuration key (supports dot notation like 'database.influxdb.host')
            value: Configuration value (will be JSON serialized)
            description: Optional description of the configuration option
        """
        import time

        value_type = type(value).__name__
        value_json = json.dumps(value)

        try:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO config (key, value, value_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (key, value_json, value_type, description, time.time()),
            )
            conn.commit()
            conn.close()
            logging.debug(f"Set config: {key} = {value}")
        except Exception as e:
            logging.error(f"Failed to set config {key}: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()

            if row is None:
                return default

            return json.loads(row[0])
        except Exception as e:
            logging.error(f"Failed to get config {key}: {e}")
            return default

    def delete(self, key: str) -> bool:
        """Delete a configuration value.

        Args:
            key: Configuration key to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("DELETE FROM config WHERE key = ?", (key,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            logging.error(f"Failed to delete config {key}: {e}")
            return False

    def get_all(self) -> dict[str, Any]:
        """Get all configuration values as a dictionary.

        Returns:
            Dictionary of all configuration key-value pairs
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT key, value FROM config")
            rows = cursor.fetchall()
            conn.close()

            config = {}
            for key, value_json in rows:
                config[key] = json.loads(value_json)

            return config
        except Exception as e:
            logging.error(f"Failed to get all config: {e}")
            return {}

    def get_nested(self) -> dict[str, Any]:
        """Get all configuration as a nested dictionary structure.

        Converts flat keys like 'database.influxdb.host' into nested dict:
        {'database': {'influxdb': {'host': 'value'}}}

        Returns:
            Nested dictionary of configuration
        """
        flat_config = self.get_all()
        nested_config: dict[str, Any] = {}

        for key, value in flat_config.items():
            keys = key.split(".")
            current = nested_config

            for i, k in enumerate(keys):
                if i == len(keys) - 1:
                    # Last key - set the value
                    current[k] = value
                else:
                    # Intermediate key - ensure dict exists
                    if k not in current:
                        current[k] = {}
                    current = current[k]

        return nested_config

    def list_keys(self, prefix: str = "") -> list[tuple[str, str]]:
        """List all configuration keys with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys (e.g., 'database.')

        Returns:
            List of (key, description) tuples
        """
        try:
            conn = self._get_connection()
            if prefix:
                cursor = conn.execute(
                    "SELECT key, description FROM config WHERE key LIKE ? ORDER BY key",
                    (f"{prefix}%",),
                )
            else:
                cursor = conn.execute("SELECT key, description FROM config ORDER BY key")

            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            logging.error(f"Failed to list config keys: {e}")
            return []

    def import_from_dict(self, config: dict[str, Any], prefix: str = "") -> int:
        """Import configuration from a nested dictionary.

        Args:
            config: Nested configuration dictionary
            prefix: Current key prefix for recursion

        Returns:
            Number of keys imported
        """
        count = 0
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recurse into nested dict
                count += self.import_from_dict(value, full_key)
            else:
                # Store the value
                self.set(full_key, value)
                count += 1

        return count


# Global config database instance
_config_db: Optional[ConfigDB] = None


def get_config_db() -> ConfigDB:
    """Get the global configuration database instance.

    Returns:
        ConfigDB instance
    """
    global _config_db
    if _config_db is None:
        _config_db = ConfigDB()
    return _config_db


def get(key_path: str, default: Any = None) -> Any:
    """Get configuration value from encrypted database.

    Args:
        key_path: Dot-separated configuration key path
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    db = get_config_db()
    return db.get(key_path, default)


def set_config(key_path: str, value: Any, description: str = "") -> None:
    """Set configuration value in encrypted database.

    Args:
        key_path: Dot-separated configuration key path
        value: Configuration value
        description: Optional description
    """
    db = get_config_db()
    db.set(key_path, value, description)
