"""InfluxDB 3.x adapter for time series data storage.

Implements the TimeSeriesDB interface for InfluxDB 3.x (Cloud/Serverless) using the influxdb3-python library.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from influxdb_client_3 import InfluxDBClient3, Point
else:
    try:
        from influxdb_client_3 import InfluxDBClient3, Point
    except ImportError:
        InfluxDBClient3 = None  # type: ignore[assignment,misc]
        Point = None  # type: ignore[assignment,misc]

from .base import TimeSeriesDB


class InfluxDB3Adapter(TimeSeriesDB):
    """InfluxDB 3.x adapter implementing TimeSeriesDB interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize InfluxDB 3.x client with configuration.

        Args:
            config: InfluxDB 3.x configuration with keys:
                - host: InfluxDB Cloud/Serverless host (e.g., us-east-1-1.aws.cloud2.influxdata.com)
                - token: API token for authentication
                - database: Database name
                - org: Organization name (optional for InfluxDB Cloud)
        """
        if InfluxDBClient3 is None:
            raise ImportError(
                "InfluxDB 3.x client library not installed. Install with: pip install influxdb3-python"
            )

        self.config = config
        self.database = config.get("database")

        # InfluxDB 3.x uses a simplified client
        self.client = InfluxDBClient3(
            host=config.get("host"),
            token=config.get("token"),
            database=self.database,
            org=config.get("org", ""),  # Optional for Cloud
        )

        logging.info(f"Initialized InfluxDB 3.x adapter: {config.get('host')}/{self.database}")

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to InfluxDB 3.x.

        Args:
            points: List of data point dictionaries.
                    Expected format: {'measurement': str, 'tags': dict, 'fields': dict, 'time': int}

        Raises:
            Exception: If write operation fails.
        """
        # Convert points to InfluxDB 3.x Point objects
        point_objects = []
        for point_data in points:
            point = Point(point_data["measurement"])

            # Add tags
            if "tags" in point_data:
                for key, value in point_data["tags"].items():
                    point.tag(key, value)

            # Add fields
            if "fields" in point_data:
                for key, value in point_data["fields"].items():
                    point.field(key, value)

            # Add timestamp if present
            if "time" in point_data:
                point.time(point_data["time"])

            point_objects.append(point)

        # Write to database
        self.client.write(record=point_objects, database=self.database)

    def test_connection(self) -> bool:
        """Test the InfluxDB 3.x connection.

        Returns:
            bool: True if connection works, False otherwise.
        """
        try:
            # Try a simple query to test connection
            self.client.query("SELECT * FROM _measurement LIMIT 1", database=self.database)
            return True
        except Exception as e:
            logging.error(f"InfluxDB 3.x connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the InfluxDB 3.x client connection."""
        if self.client:
            self.client.close()
            logging.debug("InfluxDB 3.x connection closed")
