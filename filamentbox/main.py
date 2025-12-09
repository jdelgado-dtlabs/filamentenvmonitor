"""Main entry point for FilamentBox environment data logger."""

import argparse
import logging
import queue
import threading
import time

from .config import get
from .heating_control import (
    start_heating_control,
    stop_heating_control,
    update_temperature,
)
from .humidity_control import (
    start_humidity_control,
    stop_humidity_control,
    update_humidity,
)
from .database_writer import enqueue_data_point, database_writer, wait_for_queue_empty
from .logging_config import configure_logging
from .persistence import load_and_flush_persisted_batches
from .sensor import convert_c_to_f, log_data, read_sensor_data
from .shared_state import update_sensor_data

# Global stop event shared by all threads
_stop_event = threading.Event()


def data_collection_cycle() -> None:
    """Continuously read sensor data, validate types, build point, and enqueue.

    Converts raw sensor output to floats, filters out None values, attaches
    configured tags (if any), and skips points with no valid numeric fields.
    """
    read_interval = get("data_collection.read_interval")
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

        measurement = get("data_collection.measurement") or "environment"
        tags = get("data_collection.tags")

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
            time.sleep(read_interval)
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
        time.sleep(read_interval)


def cleanup_and_exit() -> None:
    """Perform final shutdown steps after queue drains and threads stop."""
    logging.debug("Queue is empty. Exiting.")
    logging.debug("Done.")
    time.sleep(1)  # Ensure the writer thread has time to finish before the script exits


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

    # Attempt to flush any persisted batches from previous runs before starting fresh data collection.
    # This ensures data durability across reboots.
    try:
        logging.info("Loading persisted batches from previous runs...")
        from .databases import create_database_adapter

        # Create database adapter for persistence recovery
        db_type = get("database.type")
        db_config = {}

        if db_type == "influxdb":
            db_config = {
                "host": get("influxdb.host"),
                "port": get("influxdb.port"),
                "username": get("influxdb.username"),
                "password": get("influxdb.password"),
                "database": get("influxdb.database"),
                "ssl": get("influxdb.ssl"),
                "verify_ssl": get("influxdb.verify_ssl"),
            }
            # Ensure the InfluxDB database exists
            try:
                from influxdb import InfluxDBClient

                temp_client = InfluxDBClient(
                    host=db_config["host"],
                    port=db_config["port"],
                    username=db_config["username"],
                    password=db_config["password"],
                    database=db_config["database"],
                )
                temp_client.create_database(db_config["database"])
                temp_client.close()
                logging.info(f"Ensured InfluxDB database exists: {db_config['database']}")
            except Exception:
                logging.debug("Could not create/ensure InfluxDB database (may already exist)")
        elif db_type == "prometheus":
            db_config = {
                "gateway_url": get("prometheus.gateway_url"),
                "job_name": get("prometheus.job_name"),
                "username": get("prometheus.username"),
                "password": get("prometheus.password"),
                "grouping_key": get("prometheus.grouping_key"),
            }
        elif db_type == "timescaledb":
            db_config = {
                "host": get("timescaledb.host"),
                "port": get("timescaledb.port"),
                "database": get("timescaledb.database"),
                "username": get("timescaledb.username"),
                "password": get("timescaledb.password"),
                "table_name": get("timescaledb.table_name"),
                "ssl_mode": get("timescaledb.ssl_mode"),
            }
        elif db_type == "victoriametrics":
            db_config = {
                "url": get("victoriametrics.url"),
                "username": get("victoriametrics.username"),
                "password": get("victoriametrics.password"),
                "timeout": get("victoriametrics.timeout"),
            }

        if get("data_collection.enabled") and db_type != "none":
            db_adapter = create_database_adapter(db_type, db_config)
            success, failure = load_and_flush_persisted_batches(db_adapter)
            logging.info(f"Persisted batch recovery: {success} flushed, {failure} failed/pending")
            db_adapter.close()
        else:
            logging.info(
                "Data collection disabled or database type is 'none' - skipping persistence recovery"
            )
    except Exception as e:
        logging.exception(f"Error during persisted batch recovery: {e}")

    # Start all threads
    threads = []

    # Start database writer thread
    writer_thread = threading.Thread(
        target=database_writer, args=(_stop_event,), daemon=True, name="DatabaseWriter"
    )
    writer_thread.start()
    threads.append(writer_thread)

    # Data collection thread
    collector_thread = threading.Thread(
        target=data_collection_cycle, daemon=True, name="DataCollector"
    )
    collector_thread.start()
    threads.append(collector_thread)

    # Heating control thread (if enabled in config)
    start_heating_control()

    # Humidity control thread (if enabled in config)
    start_humidity_control()

    try:
        logging.info("Data collection started. Press Ctrl+C to stop.")
        while True:
            # Monitor thread health for core threads
            if not writer_thread.is_alive():
                logging.critical("Database writer thread has exited unexpectedly!")
            if not collector_thread.is_alive():
                logging.critical("Data collector thread has exited unexpectedly!")
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Stopping...")

        # Signal all threads to stop
        _stop_event.set()

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
