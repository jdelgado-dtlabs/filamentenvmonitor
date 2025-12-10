"""Main entry point for FilamentBox environment data logger."""

import argparse
import logging
import queue
import threading
import time
from typing import Any

from .config import get
from .config_watcher import start_watcher, stop_watcher, watch
from .heating_control import (
    get_heating_thread,
    start_heating_control,
    stop_heating_control,
    update_temperature,
)
from .humidity_control import (
    get_humidity_thread,
    start_humidity_control,
    stop_humidity_control,
    update_humidity,
)
from .database_writer import enqueue_data_point, database_writer, wait_for_queue_empty
from .logging_config import configure_logging
from .persistence import recover_persisted_batches
from .sensor import convert_c_to_f, log_data, read_sensor_data
from .shared_state import update_sensor_data
from .thread_control import register_thread, register_restart_callback

# Global stop event shared by all threads
_stop_event = threading.Event()

# Global thread references for restart capability
_writer_thread: threading.Thread | None = None
_collector_thread: threading.Thread | None = None

# Global variable for read interval (can be updated by config watcher)
_read_interval: float = 5.0


def _on_read_interval_changed(key: str, value: Any) -> None:
    """Handle changes to data_collection.read_interval."""
    global _read_interval
    try:
        new_interval = float(value) if value is not None else 5.0
        if new_interval != _read_interval:
            logging.info(f"Read interval changed from {_read_interval}s to {new_interval}s")
            _read_interval = new_interval
    except (ValueError, TypeError):
        logging.warning(f"Invalid read_interval value: {value}, keeping {_read_interval}s")


def _on_sensor_type_changed(key: str, value: Any) -> None:
    """Handle changes to sensor.type."""
    logging.info(f"Sensor type changed to: {value}")
    logging.info("Note: Sensor re-initialization will occur on next reading")
    # The sensor module will reinitialize automatically on next read_sensor_data() call


def data_collection_cycle() -> None:
    """Continuously read sensor data, validate types, build point, and enqueue.

    Converts raw sensor output to floats, filters out None values, attaches
    configured tags (if any), and skips points with no valid numeric fields.
    """
    global _read_interval
    _read_interval = get("data_collection.read_interval", 5.0)

    while not _stop_event.is_set():
        temperature_c, humidity = read_sensor_data()
        temperature_f = convert_c_to_f(temperature_c) if temperature_c is not None else None

        # Constrain values to float types
        try:
            temperature_c = float(temperature_c) if temperature_c is not None else None
        except (ValueError, TypeError):
            logging.warning(f"Invalid temperature_c value: {temperature_c}; skipping")
            temperature_c = None

        try:
            temperature_f = float(temperature_f) if temperature_f is not None else None
        except (ValueError, TypeError):
            logging.warning(f"Invalid temperature_f value: {temperature_f}; skipping")
            temperature_f = None

        try:
            humidity = float(humidity) if humidity is not None else None
        except (ValueError, TypeError):
            logging.warning(f"Invalid humidity value: {humidity}; skipping")
            humidity = None

        # Use measurement and tags from InfluxDB config, with sensible defaults
        measurement = get("database.influxdb.measurement", "environment")
        tags = get("database.influxdb.tags", {})

        # Warn if any sensor values are None (visibility for intermittent issues)
        if temperature_c is None or temperature_f is None or humidity is None:
            logging.warning(
                f"Sensor data incomplete: temperature_c={temperature_c}, temperature_f={temperature_f}, humidity={humidity}"
            )

        # Explicitly type fields dict for mypy (only numeric values retained)
        fields: dict[str, float | int] = {}
        if temperature_c is not None:
            fields["temperature_c"] = float(temperature_c)
        if temperature_f is not None:
            fields["temperature_f"] = float(temperature_f)
        if humidity is not None:
            fields["humidity"] = float(humidity)
        db_json_body: dict[str, object] = {
            "measurement": measurement,
            "fields": fields,
        }
        # Ensure we have at least one field (InfluxDB requirement)
        if not fields:
            logging.warning("No valid field values; skipping data point")
            time.sleep(_read_interval)
            continue

        # Add tags only if they exist
        if tags:
            db_json_body["tags"] = tags

        try:
            enqueue_data_point(db_json_body)
            log_data(temperature_c, temperature_f, humidity)
            # Update shared state for monitoring
            update_sensor_data(temperature_c, temperature_f, humidity, time.time())
            # Update heating control with current temperature
            if temperature_c is not None:
                update_temperature(temperature_c)
            # Update humidity control with current humidity
            if humidity is not None:
                update_humidity(humidity)
        except queue.Full:
            # Dropping data is notable; record as a warning so it's visible on stdout
            logging.warning("Write queue is full. Dropping data point.")
        time.sleep(_read_interval)


def cleanup_and_exit() -> None:
    """Perform final shutdown steps after queue drains and threads stop."""
    logging.debug("Queue is empty. Exiting.")
    logging.debug("Done.")
    time.sleep(1)  # Ensure the writer thread has time to finish before the script exits


def restart_database_writer() -> None:
    """Restart the database writer thread."""
    global _writer_thread

    logging.info("Restarting database writer thread...")

    # If old thread exists and is running, it will continue until stop event
    # We'll create a new thread alongside it
    new_thread = threading.Thread(
        target=database_writer, args=(_stop_event,), daemon=True, name="DatabaseWriter"
    )
    new_thread.start()
    _writer_thread = new_thread
    register_thread("database_writer", new_thread)
    logging.info("Database writer thread restarted")


def restart_data_collector() -> None:
    """Restart the data collection thread."""
    global _collector_thread

    logging.info("Restarting data collector thread...")

    new_thread = threading.Thread(target=data_collection_cycle, daemon=True, name="DataCollector")
    new_thread.start()
    _collector_thread = new_thread
    register_thread("data_collector", new_thread)
    logging.info("Data collector thread restarted")


def restart_heating_control_wrapper() -> None:
    """Restart heating control thread (wrapper for thread_control)."""
    logging.info("Restarting heating control...")
    stop_heating_control()
    time.sleep(0.5)  # Brief pause to ensure clean shutdown
    start_heating_control()
    # Register the new thread
    heating_thread = get_heating_thread()
    if heating_thread:
        register_thread("heating_control", heating_thread)
    logging.info("Heating control restarted")


def restart_humidity_control_wrapper() -> None:
    """Restart humidity control thread (wrapper for thread_control)."""
    logging.info("Restarting humidity control...")
    stop_humidity_control()
    time.sleep(0.5)  # Brief pause to ensure clean shutdown
    start_humidity_control()
    # Register the new thread
    humidity_thread = get_humidity_thread()
    if humidity_thread:
        register_thread("humidity_control", humidity_thread)
    logging.info("Humidity control restarted")


def main() -> None:
    """Program entry: configure logging, recover persisted batches, start threads.

    Sets up all worker threads, performs one-time persisted batch
    recovery, and monitors thread health until interrupted.
    """
    parser = argparse.ArgumentParser(description="FilamentBox Environment Data Logger")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Configure logging so that INFO/DEBUG go to stdout and ERROR+ go to stderr
    if args.debug:
        configure_logging(level=logging.DEBUG)
        logging.info("Debug mode is ON.")
    else:
        configure_logging(level=logging.INFO)

    # Start configuration watcher for hot-reloading
    try:
        from .config_db import CONFIG_DB_PATH

        start_watcher(CONFIG_DB_PATH, interval=2.0)

        # Register callbacks for specific configuration keys
        watch("data_collection.read_interval", _on_read_interval_changed)
        watch("sensor.type", _on_sensor_type_changed)

        logging.info("Configuration hot-reload enabled (2s check interval)")
    except Exception as e:
        logging.warning(f"Could not start configuration watcher: {e}")
        logging.info("Configuration changes will require service restart")

    # Attempt to flush any persisted batches from previous runs before starting fresh data collection.
    # This ensures data durability across reboots.
    recover_persisted_batches()

    # Register restart callbacks for thread control
    register_restart_callback("database_writer", restart_database_writer)
    register_restart_callback("data_collector", restart_data_collector)
    register_restart_callback("heating_control", restart_heating_control_wrapper)
    register_restart_callback("humidity_control", restart_humidity_control_wrapper)

    # Start all threads
    global _writer_thread, _collector_thread
    threads = []

    # Start database writer thread
    _writer_thread = threading.Thread(
        target=database_writer, args=(_stop_event,), daemon=True, name="DatabaseWriter"
    )
    _writer_thread.start()
    threads.append(_writer_thread)
    register_thread("database_writer", _writer_thread)

    # Data collection thread
    _collector_thread = threading.Thread(
        target=data_collection_cycle, daemon=True, name="DataCollector"
    )
    _collector_thread.start()
    threads.append(_collector_thread)
    register_thread("data_collector", _collector_thread)

    # Heating control thread (if enabled in config)
    start_heating_control()
    heating_thread = get_heating_thread()
    if heating_thread:
        register_thread("heating_control", heating_thread)

    # Humidity control thread (if enabled in config)
    start_humidity_control()
    humidity_thread = get_humidity_thread()
    if humidity_thread:
        register_thread("humidity_control", humidity_thread)

    try:
        logging.info("Data collection started. Press Ctrl+C to stop.")
        while True:
            # Monitor thread health for core threads
            if _writer_thread and not _writer_thread.is_alive():
                logging.critical("Database writer thread has exited unexpectedly!")
            if _collector_thread and not _collector_thread.is_alive():
                logging.critical("Data collector thread has exited unexpectedly!")

            # Monitor control threads if they're running
            heating_thread = get_heating_thread()
            if heating_thread is not None and not heating_thread.is_alive():
                logging.critical("Heating control thread has exited unexpectedly!")

            humidity_thread = get_humidity_thread()
            if humidity_thread is not None and not humidity_thread.is_alive():
                logging.critical("Humidity control thread has exited unexpectedly!")

            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Stopping...")

        # Signal all threads to stop
        _stop_event.set()

        # Stop configuration watcher
        stop_watcher()

        # Stop control threads gracefully
        stop_heating_control()
        stop_humidity_control()

        # Wait for queue to drain
        wait_for_queue_empty()

        # Wait for core threads to finish (with timeout)
        for thread in threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logging.warning(f"Thread {thread.name} did not stop gracefully")

        cleanup_and_exit()
        logging.info("Exiting main thread.")


if __name__ == "__main__":
    main()
