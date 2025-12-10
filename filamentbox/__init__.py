"""FilamentBox Environment Data Logger.

Modular data collection, batching, persistence, and InfluxDB write system for
environmental sensor data.
"""

from typing import Any, Callable, Optional

from .config import get, load_config
from .logging_config import configure_logging

# Import influx_writer conditionally - may not be available during migration
try:
    from .influx_writer import enqueue_data_point, register_alert_handler, wait_for_queue_empty

    _has_influx_writer = True
except ImportError:
    # Provide stub functions if influxdb is not installed
    def enqueue_data_point(data_point: dict[str, Any]) -> None:
        """Stub function when influxdb is not available."""
        pass

    def register_alert_handler(fn: Callable[[dict[str, Any]], None]) -> None:
        """Stub function when influxdb is not available."""
        pass

    def wait_for_queue_empty() -> None:
        """Stub function when influxdb is not available."""
        pass

    _has_influx_writer = False

# Import other modules that may have dependencies
try:
    from .persistence import load_and_flush_persisted_batches
except ImportError:

    def load_and_flush_persisted_batches(db_adapter: Any) -> tuple[int, int]:
        """Stub function when dependencies are not available."""
        return (0, 0)


try:
    from .sensor import convert_c_to_f, log_data, read_sensor_data
except ImportError:

    def convert_c_to_f(temperature_c: float) -> float:
        """Stub function when dependencies are not available."""
        return (temperature_c * 9 / 5) + 32

    def log_data(
        temperature_c: Optional[float], temperature_f: Optional[float], humidity: Optional[float]
    ) -> None:
        """Stub function when dependencies are not available."""
        pass

    def read_sensor_data() -> tuple[Optional[float], Optional[float]]:
        """Stub function when dependencies are not available."""
        return (None, None)


__all__ = [
    "configure_logging",
    "register_alert_handler",
    "enqueue_data_point",
    "wait_for_queue_empty",
    "load_and_flush_persisted_batches",
    "read_sensor_data",
    "convert_c_to_f",
    "log_data",
    "load_config",
    "get",
]
