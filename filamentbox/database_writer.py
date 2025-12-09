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
from .persistence import persist_batch
from .shared_state import update_database_status

# Configuration
DATA_COLLECTION_ENABLED = get("data_collection.enabled")
DB_TYPE = get("database.type")
BATCH_SIZE = get("data_collection.batch_size")
FLUSH_INTERVAL = get("data_collection.flush_interval")
WRITE_QUEUE_MAXSIZE = get("queue.max_size")
BACKOFF_BASE = get("retry.backoff_base")
BACKOFF_MAX = get("retry.backoff_max")
ALERT_FAILURE_THRESHOLD = get("retry.alert_threshold")
PERSIST_UNSENT_ON_ALERT = get("retry.persist_on_alert")

# Global queue and alert handler
write_queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=WRITE_QUEUE_MAXSIZE)
alert_handler: Optional[Callable[[dict[str, Any]], None]] = None


def register_alert_handler(fn: Callable[[dict[str, Any]], None]) -> None:
    """Register callback invoked after reaching repeated failure alert threshold.

    Callback receives a dict containing 'failure_count' and 'message'.
    """
    global alert_handler
    alert_handler = fn


def enqueue_data_point(data_point: dict[str, Any]) -> None:
    """Enqueue single measurement dict for a later batched write.

    Drops oldest item if queue is full to prioritize fresh data.
    When data collection is disabled, data points are silently discarded.
    When database is 'none', data points are accepted but not persisted.
    """
    if not DATA_COLLECTION_ENABLED:
        logging.debug("Data collection disabled, discarding data point")
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
    if not DATA_COLLECTION_ENABLED:
        logging.info("Data collection is disabled - database writer thread will not start")
        update_database_status(DB_TYPE, False, False)
        return

    # Create a dummy event if None provided to simplify type handling.
    if stop_event is None:
        stop_event = threading.Event()

    # Initialize database status
    update_database_status(DB_TYPE, True, True)

    # Get database-specific configuration
    db_config = {}
    if DB_TYPE == "influxdb":
        db_config = {
            "host": get("influxdb.host"),
            "port": get("influxdb.port"),
            "username": get("influxdb.username"),
            "password": get("influxdb.password"),
            "database": get("influxdb.database"),
            "ssl": get("influxdb.ssl"),
            "verify_ssl": get("influxdb.verify_ssl"),
        }
    elif DB_TYPE == "prometheus":
        db_config = {
            "gateway_url": get("prometheus.gateway_url"),
            "job_name": get("prometheus.job_name"),
            "username": get("prometheus.username"),
            "password": get("prometheus.password"),
            "grouping_key": get("prometheus.grouping_key"),
        }
    elif DB_TYPE == "timescaledb":
        db_config = {
            "host": get("timescaledb.host"),
            "port": get("timescaledb.port"),
            "database": get("timescaledb.database"),
            "username": get("timescaledb.username"),
            "password": get("timescaledb.password"),
            "table_name": get("timescaledb.table_name"),
            "ssl_mode": get("timescaledb.ssl_mode"),
        }
    elif DB_TYPE == "victoriametrics":
        db_config = {
            "url": get("victoriametrics.url"),
            "username": get("victoriametrics.username"),
            "password": get("victoriametrics.password"),
            "timeout": get("victoriametrics.timeout"),
        }

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
                    if failure_count != 0:
                        failure_count = 0
                        alerted = False
                    # Update database status with successful write
                    update_database_status(DB_TYPE, True, True, current_time, 0)
                except Exception as e:
                    # Increment failure counter and log the exception
                    failure_count += 1
                    logging.exception(f"Error writing to {DB_TYPE}: {e}")
                    # Update database status with failure count
                    update_database_status(DB_TYPE, True, True, None, failure_count)
                    # If failures exceed threshold, emit a persistent error
                    if failure_count >= ALERT_FAILURE_THRESHOLD and not alerted:
                        logging.error(
                            f"{DB_TYPE} write failed {failure_count} times in a row; check connection"
                        )
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
    update_database_status(DB_TYPE, DATA_COLLECTION_ENABLED, False)

    logging.debug(f"Database writer thread ({DB_TYPE}) exiting.")


def wait_for_queue_empty() -> None:
    """Block until write queue empties (helper for graceful shutdown)."""
    while not write_queue.empty():
        logging.debug("Waiting for queue to empty...")
        time.sleep(1)
