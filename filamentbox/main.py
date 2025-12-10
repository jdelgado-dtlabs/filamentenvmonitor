"""Main entry point for FilamentBox environment data logger."""

import argparse
import logging
import time
from typing import Any

from .config_watcher import start_watcher, stop_watcher, watch
from .logging_config import configure_logging
from .orchestrator import ThreadOrchestrator
from .persistence import recover_persisted_batches

# Orchestrator instance
_orchestrator: ThreadOrchestrator | None = None


def _on_read_interval_changed(key: str, value: Any) -> None:
    """Handle changes to data_collection.read_interval."""
    global _orchestrator
    try:
        new_interval = float(value) if value is not None else 5.0
        if _orchestrator:
            _orchestrator.update_read_interval(new_interval)
    except (ValueError, TypeError):
        logging.warning(f"Invalid read_interval value: {value}")


def _on_sensor_type_changed(key: str, value: Any) -> None:
    """Handle changes to sensor.type."""
    logging.info(f"Sensor type changed to: {value}")
    logging.info("Note: Sensor re-initialization will occur on next reading")


def _on_database_config_changed(key: str, value: Any) -> None:
    """Handle changes to database configuration."""
    from .thread_control import restart_thread

    logging.info(f"Database configuration changed: {key} = {value}")
    logging.info("Restarting database writer thread to apply new configuration...")
    success, message = restart_thread("database_writer")
    if success:
        logging.info("Database writer thread restarted successfully")
    else:
        logging.error(f"Failed to restart database writer: {message}")


def _on_heating_config_changed(key: str, value: Any) -> None:
    """Handle changes to heating control configuration."""
    from .thread_control import restart_thread

    logging.info(f"Heating control configuration changed: {key} = {value}")
    success, message = restart_thread("heating_control")
    if success:
        logging.info("Heating control restarted successfully")
    else:
        logging.error(f"Failed to restart heating control: {message}")


def _on_humidity_config_changed(key: str, value: Any) -> None:
    """Handle changes to humidity control configuration."""
    from .thread_control import restart_thread

    logging.info(f"Humidity control configuration changed: {key} = {value}")
    success, message = restart_thread("humidity_control")
    if success:
        logging.info("Humidity control restarted successfully")
    else:
        logging.error(f"Failed to restart humidity control: {message}")


def main() -> None:
    """Program entry: configure logging, recover persisted batches, start orchestrator.

    Sets up the thread orchestrator which manages all worker threads,
    performs one-time persisted batch recovery, and monitors thread
    health until interrupted.
    """
    global _orchestrator

    parser = argparse.ArgumentParser(description="FilamentBox Environment Data Logger")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Configure logging
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

        # Watch database configuration for changes that require thread restart
        watch("database.type", _on_database_config_changed)
        watch("database.influxdb.url", _on_database_config_changed)
        watch("database.influxdb.token", _on_database_config_changed)
        watch("database.influxdb.org", _on_database_config_changed)
        watch("database.influxdb.bucket", _on_database_config_changed)
        watch("database.prometheus.pushgateway_url", _on_database_config_changed)
        watch("database.timescaledb.host", _on_database_config_changed)
        watch("database.timescaledb.port", _on_database_config_changed)
        watch("database.victoriametrics.url", _on_database_config_changed)

        # Watch heating control configuration
        watch("heating_control.enabled", _on_heating_config_changed)
        watch("heating_control.gpio_pin", _on_heating_config_changed)
        watch("heating_control.min_temp", _on_heating_config_changed)
        watch("heating_control.max_temp", _on_heating_config_changed)

        # Watch humidity control configuration
        watch("humidity_control.enabled", _on_humidity_config_changed)
        watch("humidity_control.gpio_pin", _on_humidity_config_changed)
        watch("humidity_control.min_humidity", _on_humidity_config_changed)
        watch("humidity_control.max_humidity", _on_humidity_config_changed)

        logging.info("Configuration hot-reload enabled (2s check interval)")
    except Exception as e:
        logging.warning(f"Could not start configuration watcher: {e}")
        logging.info("Configuration changes will require service restart")

    # Recover any persisted batches from previous runs
    recover_persisted_batches()

    # Create and start the orchestrator
    _orchestrator = ThreadOrchestrator()
    _orchestrator.start()

    # Monitor threads (blocks until interrupted)
    try:
        _orchestrator.monitor()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Stopping...")
    finally:
        # Stop configuration watcher
        stop_watcher()

        # Stop orchestrator and all threads
        if _orchestrator:
            _orchestrator.stop()

        # Wait for queue to drain
        from .database_writer import wait_for_queue_empty

        wait_for_queue_empty()

        time.sleep(1)
        logging.info("Exiting main thread.")


if __name__ == "__main__":
    main()
