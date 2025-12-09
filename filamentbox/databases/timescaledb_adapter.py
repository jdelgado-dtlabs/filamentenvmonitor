"""TimescaleDB adapter for time series data storage.

Implements the TimeSeriesDB interface for TimescaleDB (PostgreSQL extension).
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg2
    from psycopg2 import sql
else:
    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        psycopg2 = None  # type: ignore[assignment]
        sql = None  # type: ignore[assignment]

from .base import TimeSeriesDB


class TimescaleDBAdapter(TimeSeriesDB):
    """TimescaleDB (PostgreSQL) adapter implementing TimeSeriesDB interface."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize TimescaleDB client with configuration.

        Args:
            config: TimescaleDB configuration with keys:
                - host: PostgreSQL host address
                - port: PostgreSQL port number (default: 5432)
                - database: Database name
                - username: Database username
                - password: Database password
                - table_name: Table name for measurements (default: 'environment')
                - ssl_mode: SSL mode (optional, e.g., 'require')
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 library not installed. Install with: pip install psycopg2-binary"
            )

        self.config = config
        self.table_name = config.get("table_name", "environment")

        # Connect to PostgreSQL
        conn_params = {
            "host": config.get("host", "localhost"),
            "port": config.get("port", 5432),
            "database": config.get("database"),
            "user": config.get("username"),
            "password": config.get("password"),
        }

        if config.get("ssl_mode"):
            conn_params["sslmode"] = config["ssl_mode"]

        self.connection = psycopg2.connect(**conn_params)
        self.connection.autocommit = True

        logging.info(
            f"Initialized TimescaleDB adapter: {config.get('host')}:{config.get('port')}/{config.get('database')}"
        )

        # Ensure table exists
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """Create hypertable if it doesn't exist."""
        with self.connection.cursor() as cursor:
            # Create table
            cursor.execute(
                sql.SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                    time TIMESTAMPTZ NOT NULL,
                    measurement TEXT,
                    temperature_c DOUBLE PRECISION,
                    temperature_f DOUBLE PRECISION,
                    humidity DOUBLE PRECISION,
                    tags JSONB
                );
            """
                ).format(sql.Identifier(self.table_name))
            )

            # Convert to hypertable if not already
            cursor.execute(
                sql.SQL(
                    """
                SELECT create_hypertable(%s, 'time', if_not_exists => TRUE);
            """
                ),
                (self.table_name,),
            )

            logging.debug(f"TimescaleDB table '{self.table_name}' ready")

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to TimescaleDB.

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

        with self.connection.cursor() as cursor:
            # Prepare batch insert
            insert_query = sql.SQL(
                """
                INSERT INTO {} (time, measurement, temperature_c, temperature_f, humidity, tags)
                VALUES (%s, %s, %s, %s, %s, %s);
            """
            ).format(sql.Identifier(self.table_name))

            for point in points:
                timestamp = point.get("time")
                measurement = point.get("measurement", "environment")
                fields = point.get("fields", {})
                tags = point.get("tags", {})

                # Import json for JSONB conversion
                import json

                cursor.execute(
                    insert_query,
                    (
                        timestamp,
                        measurement,
                        fields.get("temperature_c"),
                        fields.get("temperature_f"),
                        fields.get("humidity"),
                        json.dumps(tags) if tags else None,
                    ),
                )

        logging.debug(f"Wrote {len(points)} points to TimescaleDB")

    def test_connection(self) -> bool:
        """Test the TimescaleDB connection.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                return cursor.fetchone()[0] == 1
        except Exception as e:
            logging.error(f"TimescaleDB connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the TimescaleDB connection."""
        if self.connection:
            self.connection.close()
            logging.debug("TimescaleDB connection closed")
