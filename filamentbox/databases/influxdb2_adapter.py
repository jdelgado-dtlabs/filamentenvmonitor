"""InfluxDB 2.x adapter for time series data storage.

Implements the TimeSeriesDB interface for InfluxDB 2.x using the influxdb-client library.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
else:
    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError:
        InfluxDBClient = None  # type: ignore[assignment,misc]
        Point = None  # type: ignore[assignment,misc]
        SYNCHRONOUS = None  # type: ignore[assignment,misc]

from .base import TimeSeriesDB


class InfluxDB2Adapter(TimeSeriesDB):
    """InfluxDB 2.x adapter implementing TimeSeriesDB interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize InfluxDB 2.x client with configuration.

        Args:
            config: InfluxDB 2.x configuration with keys:
                - url: InfluxDB server URL (e.g., http://localhost:8086)
                - token: API token for authentication
                - org: Organization name
                - bucket: Bucket name (replaces database in v1.x)
                - verify_ssl: Verify SSL certificate (optional, default: True)
        """
        if InfluxDBClient is None:
            raise ImportError(
                "InfluxDB 2.x client library not installed. Install with: pip install influxdb-client"
            )

        self.config = config
        self.org = config.get("org")
        self.bucket = config.get("bucket")

        self.client = InfluxDBClient(
            url=config.get("url", "http://localhost:8086"),
            token=config.get("token"),
            org=self.org,
            verify_ssl=config.get("verify_ssl", True),
        )

        # Get write API with synchronous mode for consistency
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

        logging.info(
            f"Initialized InfluxDB 2.x adapter: {config.get('url')}/{self.org}/{self.bucket}"
        )

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to InfluxDB 2.x.

        Args:
            points: List of data point dictionaries in InfluxDB Line Protocol format.
                    Expected format: {'measurement': str, 'tags': dict, 'fields': dict, 'time': int}

        Raises:
            Exception: If write operation fails.
        """
        # Convert points to InfluxDB 2.x Point objects
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

        # Write to bucket
        self.write_api.write(bucket=self.bucket, org=self.org, record=point_objects)

    def test_connection(self) -> bool:
        """Test the InfluxDB 2.x connection by pinging the server.

        Returns:
            bool: True if ping successful, False otherwise.
        """
        try:
            health = self.client.health()
            return health.status == "pass"
        except Exception as e:
            logging.error(f"InfluxDB 2.x connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the InfluxDB 2.x client connection."""
        if self.write_api:
            self.write_api.close()
        if self.client:
            self.client.close()
            logging.debug("InfluxDB 2.x connection closed")
