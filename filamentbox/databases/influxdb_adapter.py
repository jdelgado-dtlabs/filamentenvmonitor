"""InfluxDB adapter for time series data storage.

Implements the TimeSeriesDB interface for InfluxDB 1.x.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from influxdb import InfluxDBClient
    from influxdb.exceptions import InfluxDBClientError
else:
    try:
        from influxdb import InfluxDBClient
        from influxdb.exceptions import InfluxDBClientError
    except ImportError:
        InfluxDBClient = None  # type: ignore[assignment,misc]
        InfluxDBClientError = None  # type: ignore[assignment,misc]

from .base import TimeSeriesDB


class InfluxDBAdapter(TimeSeriesDB):
    """InfluxDB 1.x adapter implementing TimeSeriesDB interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize InfluxDB client with configuration.

        Args:
            config: InfluxDB configuration with keys:
                - host: InfluxDB host address
                - port: InfluxDB port number
                - username: Database username
                - password: Database password
                - database: Database name
                - ssl: Use SSL connection (optional, default: False)
                - verify_ssl: Verify SSL certificate (optional, default: True)
        """
        if InfluxDBClient is None:
            raise ImportError(
                "InfluxDB client library not installed. Install with: pip install influxdb"
            )

        self.config = config
        self.client = InfluxDBClient(
            host=config.get("host", "localhost"),
            port=config.get("port", 8086),
            username=config.get("username", ""),
            password=config.get("password", ""),
            database=config.get("database"),
            ssl=config.get("ssl", False),
            verify_ssl=config.get("verify_ssl", True),
        )

        # Ensure database exists
        try:
            self.client.create_database(config.get("database"))
            logging.debug(f"Ensured InfluxDB database exists: {config.get('database')}")
        except Exception:
            # Database likely already exists, which is fine
            logging.debug(
                f"InfluxDB database {config.get('database')} already exists or cannot be created"
            )

        logging.info(
            f"Initialized InfluxDB adapter: {config.get('host')}:{config.get('port')}/{config.get('database')}"
        )

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to InfluxDB.

        Args:
            points: List of data point dictionaries in InfluxDB format.

        Raises:
            InfluxDBClientError: If write operation fails.
        """
        self.client.write_points(points)

    def test_connection(self) -> bool:
        """Test the InfluxDB connection by pinging the server.

        Returns:
            bool: True if ping successful, False otherwise.
        """
        try:
            return self.client.ping()
        except Exception as e:
            logging.error(f"InfluxDB connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the InfluxDB client connection."""
        if self.client:
            self.client.close()
            logging.debug("InfluxDB connection closed")
