"""Prometheus adapter for time series data storage.

Implements the TimeSeriesDB interface for Prometheus using the Pushgateway.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
    from prometheus_client.exposition import basic_auth_handler
else:
    try:
        from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
        from prometheus_client.exposition import basic_auth_handler
    except ImportError:
        CollectorRegistry = None  # type: ignore[assignment,misc]
        Gauge = None  # type: ignore[assignment,misc]
        push_to_gateway = None  # type: ignore[assignment,misc]
        basic_auth_handler = None  # type: ignore[assignment,misc]

from .base import TimeSeriesDB


class PrometheusAdapter(TimeSeriesDB):
    """Prometheus Pushgateway adapter implementing TimeSeriesDB interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Prometheus Pushgateway client with configuration.

        Args:
            config: Prometheus configuration with keys:
                - gateway_url: Pushgateway URL (e.g., 'http://pushgateway:9091')
                - job_name: Job name for pushed metrics
                - username: Basic auth username (optional)
                - password: Basic auth password (optional)
                - grouping_key: Additional labels for grouping (optional dict)
        """
        if CollectorRegistry is None:
            raise ImportError(
                "Prometheus client library not installed. Install with: pip install prometheus-client"
            )

        self.config = config
        self.gateway_url = config.get("gateway_url", "http://localhost:9091")
        self.job_name = config.get("job_name", "filamentbox")
        self.username = config.get("username")
        self.password = config.get("password")
        self.grouping_key = config.get("grouping_key", {})
        self.registry = CollectorRegistry()

        # Create gauges for metrics
        self.temperature_gauge = Gauge(
            "environment_temperature_celsius",
            "Temperature in Celsius",
            labelnames=list(self.grouping_key.keys()),
            registry=self.registry,
        )
        self.humidity_gauge = Gauge(
            "environment_humidity_percent",
            "Humidity percentage",
            labelnames=list(self.grouping_key.keys()),
            registry=self.registry,
        )

        logging.info(f"Initialized Prometheus adapter: {self.gateway_url}, job={self.job_name}")

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to Prometheus Pushgateway.

        Args:
            points: List of data point dictionaries. Expected format:
                {
                    "measurement": "environment",
                    "tags": {...},
                    "fields": {"temperature_c": ..., "humidity": ...},
                    "time": ...
                }

        Raises:
            Exception: If push operation fails.
        """
        if not points:
            return

        # Use the most recent point for each metric
        # (Prometheus is pull-based, so we push latest state)
        latest_point = points[-1]
        fields = latest_point.get("fields", {})
        tags = latest_point.get("tags", {})

        # Merge tags with grouping_key
        labels = {**self.grouping_key, **tags}

        # Set gauge values
        if "temperature_c" in fields:
            if labels:
                self.temperature_gauge.labels(**labels).set(fields["temperature_c"])
            else:
                # If no labels, use the gauge without labels
                Gauge(
                    "environment_temperature_celsius",
                    "Temperature in Celsius",
                    registry=self.registry,
                ).set(fields["temperature_c"])

        if "humidity" in fields:
            if labels:
                self.humidity_gauge.labels(**labels).set(fields["humidity"])
            else:
                Gauge(
                    "environment_humidity_percent",
                    "Humidity percentage",
                    registry=self.registry,
                ).set(fields["humidity"])

        # Push to gateway
        try:
            if self.username and self.password:

                def auth_handler(
                    url: str, method: str, timeout: float, headers: dict, data: bytes
                ) -> Any:
                    return basic_auth_handler(
                        url, method, timeout, headers, data, self.username, self.password
                    )

                push_to_gateway(
                    self.gateway_url,
                    job=self.job_name,
                    registry=self.registry,
                    handler=auth_handler,
                )
            else:
                push_to_gateway(self.gateway_url, job=self.job_name, registry=self.registry)

            logging.debug(f"Pushed {len(points)} points to Prometheus Pushgateway")
        except Exception as e:
            logging.error(f"Failed to push to Prometheus Pushgateway: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the Prometheus Pushgateway connection.

        Returns:
            bool: True if push successful, False otherwise.
        """
        try:
            # Try to push empty metrics as a test
            push_to_gateway(
                self.gateway_url, job=f"{self.job_name}_test", registry=CollectorRegistry()
            )
            return True
        except Exception as e:
            logging.error(f"Prometheus connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the Prometheus adapter (no persistent connection to close)."""
        logging.debug("Prometheus adapter closed (no persistent connection)")
