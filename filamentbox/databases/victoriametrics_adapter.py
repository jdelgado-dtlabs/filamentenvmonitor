"""VictoriaMetrics adapter for time series data storage.

Implements the TimeSeriesDB interface for VictoriaMetrics.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import requests
else:
    try:
        import requests
    except ImportError:
        requests = None  # type: ignore[assignment]

from .base import TimeSeriesDB


class VictoriaMetricsAdapter(TimeSeriesDB):
    """VictoriaMetrics adapter implementing TimeSeriesDB interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize VictoriaMetrics client with configuration.

        Args:
            config: VictoriaMetrics configuration with keys:
                - url: VictoriaMetrics API URL (e.g., 'http://victoriametrics:8428')
                - username: Basic auth username (optional)
                - password: Basic auth password (optional)
                - timeout: Request timeout in seconds (default: 10)
        """
        if requests is None:
            raise ImportError("requests library not installed. Install with: pip install requests")

        self.config = config
        self.url = config.get("url", "http://localhost:8428")
        self.username = config.get("username")
        self.password = config.get("password")
        self.timeout = config.get("timeout", 10)

        # Setup authentication
        self.auth = None
        if self.username and self.password:
            self.auth = (self.username, self.password)

        logging.info(f"Initialized VictoriaMetrics adapter: {self.url}")

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to VictoriaMetrics.

        Uses InfluxDB line protocol format via /api/v1/import/influx endpoint.

        Args:
            points: List of data point dictionaries. Expected format:
                {
                    "measurement": "environment",
                    "tags": {...},
                    "fields": {"temperature_c": ..., "humidity": ...},
                    "time": "2024-01-01T00:00:00Z"
                }

        Raises:
            Exception: If write operation fails.
        """
        if not points:
            return

        # Convert points to InfluxDB line protocol
        lines = []
        for point in points:
            measurement = point.get("measurement", "environment")
            tags = point.get("tags", {})
            fields = point.get("fields", {})
            timestamp = point.get("time")

            # Build tag string
            tag_str = ""
            if tags:
                tag_pairs = [f"{k}={v}" for k, v in tags.items()]
                tag_str = "," + ",".join(tag_pairs)

            # Build field string
            field_pairs = []
            for k, v in fields.items():
                if isinstance(v, str):
                    field_pairs.append(f'{k}="{v}"')
                else:
                    field_pairs.append(f"{k}={v}")
            field_str = ",".join(field_pairs)

            # Parse timestamp to nanoseconds
            if timestamp:
                # Convert ISO8601 to Unix nanoseconds
                from datetime import datetime

                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp_ns = int(dt.timestamp() * 1e9)
            else:
                import time

                timestamp_ns = int(time.time() * 1e9)

            # Format: measurement[,tag=value,...] field=value[,field=value,...] timestamp
            line = f"{measurement}{tag_str} {field_str} {timestamp_ns}"
            lines.append(line)

        # Join all lines
        payload = "\n".join(lines)

        # Write to VictoriaMetrics using InfluxDB compatibility endpoint
        url = f"{self.url}/api/v1/import/influx"

        try:
            response = requests.post(
                url,
                data=payload,
                auth=self.auth,
                timeout=self.timeout,
                headers={"Content-Type": "text/plain"},
            )
            response.raise_for_status()
            logging.debug(f"Wrote {len(points)} points to VictoriaMetrics")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to write to VictoriaMetrics: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the VictoriaMetrics connection.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            url = f"{self.url}/health"
            response = requests.get(url, auth=self.auth, timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            logging.error(f"VictoriaMetrics connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the VictoriaMetrics adapter (no persistent connection to close)."""
        logging.debug("VictoriaMetrics adapter closed (no persistent connection)")
