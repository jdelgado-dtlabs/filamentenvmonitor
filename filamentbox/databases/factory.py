"""Factory for creating time series database adapters.

Provides a unified interface for instantiating database adapters based on configuration.
"""

from typing import Any

from .base import TimeSeriesDB


def create_database_adapter(db_type: str, config: dict[str, Any]) -> TimeSeriesDB:
    """Create and return the appropriate database adapter.

    Args:
        db_type: Type of database ('influxdb', 'prometheus', 'timescaledb',
                                    'victoriametrics', or 'none')
        config: Database-specific configuration dictionary. For InfluxDB, must include
                'version' key ('1', '2', or '3') to select the appropriate adapter.

    Returns:
        TimeSeriesDB: Initialized database adapter instance

    Raises:
        ValueError: If database type is unknown or unsupported
        ImportError: If required dependencies for the adapter are not installed
    """
    db_type = db_type.lower()

    if db_type == "none" or db_type == "disabled":
        from .none_adapter import NoneAdapter

        return NoneAdapter(config)

    if db_type == "influxdb":
        # Use version from config to select the appropriate InfluxDB adapter
        version = config.get("version", "2")

        if version == "1":
            from .influxdb_adapter import InfluxDBAdapter

            return InfluxDBAdapter(config)
        elif version == "2":
            from .influxdb2_adapter import InfluxDB2Adapter

            return InfluxDB2Adapter(config)
        elif version == "3":
            from .influxdb3_adapter import InfluxDB3Adapter

            return InfluxDB3Adapter(config)
        else:
            raise ValueError(f"Unknown InfluxDB version: {version}. Supported versions: 1, 2, 3")

    if db_type == "prometheus":
        from .prometheus_adapter import PrometheusAdapter

        return PrometheusAdapter(config)

    if db_type == "timescaledb":
        from .timescaledb_adapter import TimescaleDBAdapter

        return TimescaleDBAdapter(config)

    if db_type == "victoriametrics":
        from .victoriametrics_adapter import VictoriaMetricsAdapter

        return VictoriaMetricsAdapter(config)

    raise ValueError(
        f"Unknown database type: {db_type}. "
        f"Supported types: influxdb, prometheus, timescaledb, victoriametrics, none"
    )
