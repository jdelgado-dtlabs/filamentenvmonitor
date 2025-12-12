"""Generic database writer thread with batching, retry backoff, alerting, and persistence.

This module replaces the influx_writer module with a database-agnostic implementation
that works with any TimeSeriesDB adapter.

Public functions:
        register_alert_handler: set callback for repeated failure alerts.
        enqueue_data_point: queue a single measurement dict for later write.
        database_writer: thread target performing batched writes with backoff.
        wait_for_queue_empty: helper to block until queue drains.
"""

import json
import logging
import queue
import random
import time
import threading
from typing import Any, Callable, Optional

from .config import get
from .databases import create_database_adapter
from .notification_publisher import notify_error, notify_success
from .persistence import persist_batch
from .shared_state import update_database_status

# Configuration with sensible defaults for missing keys
# Use `database.enabled` to control whether the database writer runs
DATABASE_ENABLED = get("database.enabled", True)  # Default: enabled
DB_TYPE = get("database.type", "none")  # Default: no database (sensor-only mode)
BATCH_SIZE = get("database.batch_size", 10)
FLUSH_INTERVAL = get("database.flush_interval", 60)
WRITE_QUEUE_MAXSIZE = get("queue.max_size", 10000)  # Legacy key, not in schema
BACKOFF_BASE = get("retry.backoff_base", 2)  # Legacy key, not in schema
BACKOFF_MAX = get("retry.backoff_max", 300)  # Legacy key, not in schema (5 minutes)
ALERT_FAILURE_THRESHOLD = get("retry.alert_threshold", 5)  # Legacy key, not in schema
PERSIST_UNSENT_ON_ALERT = get("retry.persist_on_alert", True)  # Legacy key, not in schema

# Global queue and alert handler
write_queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=WRITE_QUEUE_MAXSIZE)
alert_handler: Optional[Callable[[dict[str, Any]], None]] = None


def get_database_config(db_type: str) -> dict[str, Any]:
    """Get database configuration for the specified database type.

    Args:
        db_type: Database type (influxdb, prometheus, timescaledb, victoriametrics, none)

    Returns:
        Dictionary with database-specific configuration parameters.
    """
    if db_type == "influxdb":
        # Unified InfluxDB configuration with version selector
        version = get("database.influxdb.version", "2")
        url = get("database.influxdb.url")

        # Parse URL to extract host and port for v1 adapter
        host = "localhost"
        port = 8086
        if url:
            import re

            match = re.match(r"^https?://([\w\.\-]+):(\d+)$", url)
            if match:
                host = match.group(1)
                port = int(match.group(2))

        config = {
            "version": version,
            "url": url,
            "token": get("database.influxdb.token"),
            "org": get("database.influxdb.org"),
            "bucket": get("database.influxdb.bucket"),
            "username": get("database.influxdb.username"),
            # For v1 compatibility
            "host": host,
            "port": port,
            "password": get("database.influxdb.token"),  # Use token as password for v1
            "database": get("database.influxdb.bucket"),  # Use bucket as database for v1
        }
        return config

    elif db_type == "prometheus":
        return {
            "pushgateway_url": get("database.prometheus.pushgateway_url"),
            "job": get("database.prometheus.job"),
            "instance": get("database.prometheus.instance"),
            "grouping_keys": get("database.prometheus.grouping_keys", {}),
            "username": get("database.prometheus.username"),
            "password": get("database.prometheus.password"),
        }
    elif db_type == "timescaledb":
        return {
            "host": get("database.timescaledb.host"),
            "port": get("database.timescaledb.port", 5432),
            "database": get("database.timescaledb.database"),
            "username": get("database.timescaledb.username"),
            "password": get("database.timescaledb.password"),
            "table": get("database.timescaledb.table", "environment_data"),
            "ssl_mode": get("database.timescaledb.ssl_mode", "prefer"),
        }
    elif db_type == "victoriametrics":
        return {
            "url": get("database.victoriametrics.url"),
            "username": get("database.victoriametrics.username"),
            "password": get("database.victoriametrics.password"),
            "timeout": get("database.victoriametrics.timeout", 10),
        }
    else:  # none or unknown
        return {}


def register_alert_handler(fn: Callable[[dict[str, Any]], None]) -> None:
    """Register callback invoked after reaching repeated failure alert threshold.

    Callback receives a dict containing 'failure_count' and 'message'.
    """
    global alert_handler
    alert_handler = fn


def enqueue_data_point(data_point: dict[str, Any]) -> None:
    """Enqueue single measurement dict for a later batched write.

    Drops oldest item if queue is full to prioritize fresh data.
    When the database writer is disabled, data points are silently discarded.
    When database is 'none', data points are accepted but not persisted.
    """
    if not DATABASE_ENABLED:
        logging.debug("Database writer disabled, discarding data point")
        return

    try:
        write_queue.put_nowait(data_point)
    except queue.Full:
        # Queue is full: drop the oldest datapoint to make room for new data.
        try:
            _ = write_queue.get_nowait()
        except queue.Empty:
            # Unlikely: queue reported full then empty; log and drop new point
            logging.error("Write queue full then empty; dropping new datapoint")
            return
        try:
            write_queue.put_nowait(data_point)
            logging.warning("Write queue full: dropped oldest datapoint to enqueue new one.")
        except queue.Full:
            # If still full, give up and drop the new datapoint
            logging.error(
                "Write queue full and unable to enqueue new data point; dropping new datapoint."
            )


def database_writer(stop_event: Optional[threading.Event] = None) -> None:
    """Thread target: batch queued points and write to configured database with retries.

    Flush triggers: batch size or elapsed flush interval. Implements exponential
    backoff with jitter, persistence of unsent batches on alert condition, and
    optional external alert callback.
    """
    if not DATABASE_ENABLED:
        logging.info("Database writer is disabled - database writer thread will not start")
        update_database_status(DB_TYPE, False, False)
        return

    # Create a dummy event if None provided to simplify type handling.
    if stop_event is None:
        stop_event = threading.Event()

    # Initialize database status
    update_database_status(DB_TYPE, DATABASE_ENABLED, True)

    # Get database-specific configuration
    db_config = get_database_config(DB_TYPE)

    # Create database adapter
    try:
        db_adapter = create_database_adapter(DB_TYPE, db_config)
        logging.info(f"Database writer initialized with {DB_TYPE} adapter")
    except Exception as e:
        logging.error(f"Failed to initialize database adapter ({DB_TYPE}): {e}")
        if DB_TYPE != "none":
            raise

    batch = []
    last_flush_time = time.time()
    failure_count = 0
    alerted = False

    while not stop_event.is_set() or not write_queue.empty():
        try:
            data_point = write_queue.get(timeout=1)
            batch.append(data_point)
            write_queue.task_done()
        except queue.Empty:
            pass

        current_time = time.time()
        if (len(batch) >= BATCH_SIZE) or (current_time - last_flush_time >= FLUSH_INTERVAL):
            if batch:
                try:
                    logging.debug(f"Batch ready for write ({len(batch)} points) to {DB_TYPE}:")
                    for i, point in enumerate(batch):
                        logging.debug(f"  Point {i + 1}: {json.dumps(point)}")
                    db_adapter.write_points(batch)
                    logging.debug(f"Wrote {len(batch)} points to {DB_TYPE}.")
                    batch.clear()
                    last_flush_time = current_time
                    # Check if we're recovering from failures
                    was_in_failure_state = alerted
                    if failure_count != 0:
                        failure_count = 0
                        alerted = False
                    # Notify if connection was restored
                    if was_in_failure_state:
                        notify_success("✓ Database connection restored")
                    # Update database status with successful write
                    update_database_status(DB_TYPE, DATABASE_ENABLED, True, current_time, 0)
                except Exception as e:
                    # Increment failure counter and log the exception
                    failure_count += 1
                    logging.exception(f"Error writing to {DB_TYPE}: {e}")
                    # Update database status with failure count
                    update_database_status(DB_TYPE, DATABASE_ENABLED, True, None, failure_count)
                    # If failures exceed threshold, emit a persistent error
                    if failure_count >= ALERT_FAILURE_THRESHOLD and not alerted:
                        logging.error(
                            f"{DB_TYPE} write failed {failure_count} times in a row; check connection"
                        )
                        notify_error("⚠️ Database connection lost, retrying...")
                        # Call registered alert handler if present
                        if alert_handler is not None:
                            try:
                                alert_handler({"failure_count": failure_count, "message": str(e)})
                            except Exception:
                                logging.exception("Alert handler raised an exception")
                        # Persist the unsent batch if configured and not using 'none' database
                        if PERSIST_UNSENT_ON_ALERT and DB_TYPE != "none":
                            persist_batch(batch)
                        alerted = True
                    # Exponential backoff with jitter to avoid thundering retries
                    backoff = min(BACKOFF_BASE * (2 ** (failure_count - 1)), BACKOFF_MAX)
                    jitter = random.uniform(0, backoff * 0.1)
                    sleep_time = backoff + jitter
                    logging.info(
                        f"Backing off {sleep_time:.1f}s before retrying (failure_count={failure_count})"
                    )
                    time.sleep(sleep_time)

    # Close database connection
    try:
        db_adapter.close()
    except Exception:
        logging.exception("Error closing database adapter")

    # Update status to indicate writer has stopped
    update_database_status(DB_TYPE, DATABASE_ENABLED, False)

    logging.debug(f"Database writer thread ({DB_TYPE}) exiting.")


def wait_for_queue_empty() -> None:
    """Block until write queue empties (helper for graceful shutdown)."""
    while not write_queue.empty():
        logging.debug("Waiting for queue to empty...")
        time.sleep(1)
