"""Main entry point for FilamentBox environment data logger."""

import argparse
import logging
import queue
import threading
import time

from influxdb import InfluxDBClient

from .config import get
from .heating_control import start_heating_control, stop_heating_control, update_temperature
from .humidity_control import (
    start_humidity_control,
    stop_humidity_control,
    update_humidity,
)
from .influx_writer import enqueue_data_point, influxdb_writer, wait_for_queue_empty
from .logging_config import configure_logging
from .persistence import load_and_flush_persisted_batches
from .sensor import convert_c_to_f, log_data, read_sensor_data


def data_collection_cycle() -> None:
    """Continuously read sensor data, validate types, build point, and enqueue.

    Converts raw sensor output to floats, filters out None values, attaches
    configured tags (if any), and skips points with no valid numeric fields.
    """
    read_interval = get("data_collection.read_interval")
    while True:
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

    Sets up the writer and producer threads, performs one-time persisted batch
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
        client = InfluxDBClient(
            host=get("influxdb.host"),
            port=get("influxdb.port"),
            username=get("influxdb.username"),
            password=get("influxdb.password"),
            database=get("influxdb.database"),
        )
        # Ensure the InfluxDB database exists. If it doesn't, try to create it.
        try:
            db_name = get("influxdb.database")
            if db_name:
                client.create_database(db_name)
                logging.info(f"Ensured InfluxDB database exists: {db_name}")
        except Exception:
            logging.debug(
                "Could not create/ensure InfluxDB database (may already exist or permissions missing)"
            )

        success, failure = load_and_flush_persisted_batches(client)
        logging.info(f"Persisted batch recovery: {success} flushed, {failure} failed/pending")
    except Exception as e:
        logging.exception(f"Error during persisted batch recovery: {e}")

    stop_event = threading.Event()
    writer_thread = threading.Thread(
        target=influxdb_writer, args=(stop_event,), daemon=True, name="InfluxDBWriter"
    )
    writer_thread.start()

    producer_thread = threading.Thread(
        target=data_collection_cycle, daemon=True, name="DataCollector"
    )
    producer_thread.start()

    # Start heating control thread (if enabled in config)
    start_heating_control()

    # Start humidity control thread (if enabled in config)
    start_humidity_control()

    try:
        logging.info("Data collection started. Press Ctrl+C to stop.")
        while True:
            # Monitor thread health
            if not writer_thread.is_alive():
                logging.critical("InfluxDB writer thread has exited unexpectedly!")
            if not producer_thread.is_alive():
                logging.critical("Data collector thread has exited unexpectedly!")
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Stopping...")
        stop_event.set()
        stop_heating_control()
        stop_humidity_control()
        wait_for_queue_empty()
        cleanup_and_exit()
        logging.info("Exiting main thread.")


if __name__ == "__main__":
    main()
