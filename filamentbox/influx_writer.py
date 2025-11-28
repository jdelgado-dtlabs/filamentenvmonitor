"""InfluxDB writer thread with batching, retry backoff, alerting, and persistence.

Public functions:
        register_alert_handler: set callback for repeated failure alerts.
        enqueue_data_point: queue a single measurement dict for later write.
        influxdb_writer: thread target performing batched writes with backoff.
        wait_for_queue_empty: helper to block until queue drains.
"""

import json
import logging
import queue
import random
import time
import threading
from typing import Any, Callable, Optional

from influxdb import InfluxDBClient
from .config import get
from .persistence import persist_batch

DB_HOST = get("influxdb.host")
DB_PORT = get("influxdb.port")
DB_USERNAME = get("influxdb.username")
DB_PASSWORD = get("influxdb.password")
DB_DATABASE = get("influxdb.database")
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
    """
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


def influxdb_writer(stop_event: Optional[threading.Event] = None) -> None:
    """Thread target: batch queued points and write to InfluxDB with retries.

    Flush triggers: batch size or elapsed flush interval. Implements exponential
    backoff with jitter, persistence of unsent batches on alert condition, and
    optional external alert callback.
    """
    # Create a dummy event if None provided to simplify type handling.
    if stop_event is None:
        stop_event = threading.Event()
    client = InfluxDBClient(
        host=DB_HOST, port=DB_PORT, username=DB_USERNAME, password=DB_PASSWORD, database=DB_DATABASE
    )
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
                    logging.debug(f"Batch ready for write ({len(batch)} points):")
                    for i, point in enumerate(batch):
                        logging.debug(f"  Point {i+1}: {json.dumps(point)}")
                    client.write_points(batch)
                    logging.debug(f"Wrote {len(batch)} points to InfluxDB.")
                    batch.clear()
                    last_flush_time = current_time
                    if failure_count != 0:
                        failure_count = 0
                        alerted = False
                except Exception as e:
                    # Increment failure counter and log the exception
                    failure_count += 1
                    logging.exception(f"Error writing to InfluxDB: {e}")
                    # If failures exceed threshold, emit a persistent error to stderr
                    if failure_count >= ALERT_FAILURE_THRESHOLD and not alerted:
                        logging.error(
                            f"InfluxDB write failed {failure_count} times in a row; check {DB_HOST}:{DB_PORT}"
                        )
                        # Call registered alert handler if present
                        if alert_handler is not None:
                            try:
                                alert_handler({"failure_count": failure_count, "message": str(e)})
                            except Exception:
                                logging.exception("Alert handler raised an exception")
                        # Persist the unsent batch if configured
                        if PERSIST_UNSENT_ON_ALERT:
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

    logging.debug("InfluxDB writer thread exiting.")


def wait_for_queue_empty() -> None:
    """Block until write queue empties (helper for graceful shutdown)."""
    while not write_queue.empty():
        logging.debug("Waiting for queue to empty...")
        time.sleep(1)
