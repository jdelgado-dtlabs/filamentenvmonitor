"""Master orchestrator for thread lifecycle management.

Centralizes thread creation, monitoring, restart handling, and data distribution.
Eliminates file-based communication in favor of direct thread communication via queues.
"""

import logging
import queue
import threading
import time
from typing import Optional

from .config import get
from .database_writer import database_writer, enqueue_data_point
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
from .sensor import convert_c_to_f, log_data, read_sensor_data
from .shared_state import (
    clear_thread_restart_request,
    clear_thread_start_request,
    clear_thread_stop_request,
    get_thread_restart_requests,
    get_thread_start_requests,
    get_thread_stop_requests,
    update_sensor_data,
)
from .thread_control import (
    get_thread_status,
    register_restart_callback,
    register_start_callback,
    register_stop_callback,
    register_thread,
    restart_thread,
    start_thread,
    stop_thread,
)


class ThreadOrchestrator:
    """Master orchestrator managing all worker threads and their lifecycle."""

    def __init__(self):
        """Initialize the orchestrator."""
        self._stop_event = threading.Event()
        self._writer_stop_event = threading.Event()
        self._threads: dict[str, threading.Thread] = {}
        self._read_interval: float = 5.0

        # Thread references
        self._writer_thread: Optional[threading.Thread] = None
        self._collector_thread: Optional[threading.Thread] = None
        self._webui_thread: Optional[threading.Thread] = None

        logging.info("Thread orchestrator initialized")

    def start(self) -> None:
        """Start all configured threads."""
        logging.info("Starting thread orchestrator...")

        # Register restart callbacks
        register_restart_callback("database_writer", self._restart_database_writer)
        register_restart_callback("data_collector", self._restart_data_collector)
        register_restart_callback("heating_control", self._restart_heating_control)
        register_restart_callback("humidity_control", self._restart_humidity_control)

        # Register start callbacks
        register_start_callback("database_writer", self._start_database_writer_control)
        register_start_callback("heating_control", self._start_heating_control)
        register_start_callback("humidity_control", self._start_humidity_control)

        # Register stop callbacks
        register_stop_callback("database_writer", self._stop_database_writer)
        register_stop_callback("heating_control", self._stop_heating_control)
        register_stop_callback("humidity_control", self._stop_humidity_control)

        # Start core threads
        self._start_database_writer()
        self._start_data_collector()

        # Start control threads if enabled
        start_heating_control()
        heating_thread = get_heating_thread()
        if heating_thread:
            register_thread("heating_control", heating_thread)
            self._threads["heating_control"] = heating_thread

        start_humidity_control()
        humidity_thread = get_humidity_thread()
        if humidity_thread:
            register_thread("humidity_control", humidity_thread)
            self._threads["humidity_control"] = humidity_thread

        # Start web UI if enabled
        if get("webui.enabled", True):
            self._start_webui()

        logging.info("All threads started successfully")

    def _start_database_writer(self) -> None:
        """Start the database writer thread."""
        self._writer_stop_event.clear()
        self._writer_thread = threading.Thread(
            target=database_writer,
            args=(self._writer_stop_event,),
            daemon=True,
            name="DatabaseWriter",
        )
        self._writer_thread.start()
        register_thread("database_writer", self._writer_thread)
        self._threads["database_writer"] = self._writer_thread
        logging.debug("Database writer thread started")

    def _start_data_collector(self) -> None:
        """Start the data collection thread."""
        self._collector_thread = threading.Thread(
            target=self._data_collection_cycle, daemon=True, name="DataCollector"
        )
        self._collector_thread.start()
        register_thread("data_collector", self._collector_thread)
        self._threads["data_collector"] = self._collector_thread
        logging.debug("Data collector thread started")

    def _start_webui(self) -> None:
        """Start the web UI thread."""
        try:
            from .webui_thread import start_webui_thread

            host = get("webui.host", "0.0.0.0")
            port = get("webui.port", 5000)

            self._webui_thread = threading.Thread(
                target=start_webui_thread,
                args=(host, port, self._stop_event),
                daemon=True,
                name="WebUI",
            )
            self._webui_thread.start()
            register_thread("webui", self._webui_thread)
            self._threads["webui"] = self._webui_thread
            logging.info(f"Web UI thread started on {host}:{port}")
        except ImportError as e:
            logging.warning(f"Failed to start web UI thread: {e}")
        except Exception as e:
            logging.error(f"Error starting web UI thread: {e}")

    def _data_collection_cycle(self) -> None:
        """Continuously read sensor data and distribute to consumers.

        This is the data collector thread target that reads sensors,
        validates data, and distributes it to:
        - Database writer (via queue)
        - Heating control (via update function)
        - Humidity control (via update function)
        - Shared state (for web UI)
        """
        self._read_interval = get("sensors.read_interval", 5.0)

        while not self._stop_event.is_set():
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

            # Get measurement and tags from config
            measurement = get("database.influxdb.measurement", "environment")
            tags = get("database.influxdb.tags", {})

            # Warn if any sensor values are None
            if temperature_c is None or temperature_f is None or humidity is None:
                logging.warning(
                    f"Sensor data incomplete: temperature_c={temperature_c}, "
                    f"temperature_f={temperature_f}, humidity={humidity}"
                )

            # Build fields dict (only numeric values)
            fields: dict[str, float | int] = {}
            if temperature_c is not None:
                fields["temperature_c"] = float(temperature_c)
            if temperature_f is not None:
                fields["temperature_f"] = float(temperature_f)
            if humidity is not None:
                fields["humidity"] = float(humidity)

            # Skip if no valid fields
            if not fields:
                logging.warning("No valid field values; skipping data point")
                time.sleep(self._read_interval)
                continue

            # Build database point
            db_json_body: dict[str, object] = {
                "measurement": measurement,
                "fields": fields,
            }
            if tags:
                db_json_body["tags"] = tags

            try:
                # Distribute data to all consumers
                enqueue_data_point(db_json_body)  # Database writer
                log_data(temperature_c, temperature_f, humidity)  # Console logging

                # Update shared state (for web UI)
                update_sensor_data(temperature_c, temperature_f, humidity, time.time())

                # Update control threads
                if temperature_c is not None:
                    update_temperature(temperature_c)
                if humidity is not None:
                    update_humidity(humidity)

            except queue.Full:
                logging.warning("Write queue is full. Dropping data point.")

            time.sleep(self._read_interval)

    def _start_database_writer_control(self) -> None:
        """Start database writer via control callback."""
        logging.info("Starting database writer...")
        self._start_database_writer()
        logging.info("Database writer started")

    def _stop_database_writer(self) -> None:
        """Stop database writer thread."""
        logging.info("Stopping database writer...")
        self._writer_stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=5.0)
        self._threads["database_writer"] = None  # type: ignore[assignment]
        logging.info("Database writer stopped")

    def _restart_database_writer(self) -> None:
        """Restart the database writer thread."""
        logging.info("Restarting database writer thread...")
        self._writer_stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)
        self._writer_stop_event.clear()
        new_thread = threading.Thread(
            target=database_writer,
            args=(self._writer_stop_event,),
            daemon=True,
            name="DatabaseWriter",
        )
        new_thread.start()
        self._writer_thread = new_thread
        register_thread("database_writer", new_thread)
        self._threads["database_writer"] = new_thread
        logging.info("Database writer thread restarted")

    def _restart_data_collector(self) -> None:
        """Restart the data collection thread."""
        logging.info("Restarting data collector thread...")
        # Just start a new thread - the old one will naturally exit when orphaned
        new_thread = threading.Thread(
            target=self._data_collection_cycle, daemon=True, name="DataCollector"
        )
        new_thread.start()
        self._collector_thread = new_thread
        register_thread("data_collector", new_thread)
        self._threads["data_collector"] = new_thread
        logging.info("Data collector thread restarted")

    def _restart_heating_control(self) -> None:
        """Restart heating control thread."""
        logging.info("Restarting heating control...")
        stop_heating_control()
        time.sleep(0.5)
        start_heating_control()
        heating_thread = get_heating_thread()
        if heating_thread:
            register_thread("heating_control", heating_thread)
            self._threads["heating_control"] = heating_thread
        logging.info("Heating control restarted")

    def _restart_humidity_control(self) -> None:
        """Restart humidity control thread."""
        logging.info("Restarting humidity control...")
        stop_humidity_control()
        time.sleep(0.5)
        start_humidity_control()
        humidity_thread = get_humidity_thread()
        if humidity_thread:
            register_thread("humidity_control", humidity_thread)
            self._threads["humidity_control"] = humidity_thread
        logging.info("Humidity control restarted")

    def _start_heating_control(self) -> None:
        """Start heating control thread."""
        logging.info("Starting heating control...")
        start_heating_control()
        time.sleep(0.1)  # Give thread a moment to start
        heating_thread = get_heating_thread()
        if heating_thread:
            register_thread("heating_control", heating_thread)
            self._threads["heating_control"] = heating_thread
            logging.info(f"Heating control started (thread alive: {heating_thread.is_alive()})")
        else:
            logging.error("Failed to get heating control thread after starting")

    def _stop_heating_control(self) -> None:
        """Stop heating control thread."""
        logging.info("Stopping heating control...")
        stop_heating_control()
        self._threads["heating_control"] = None  # type: ignore[assignment]
        logging.info("Heating control stopped")

    def _start_humidity_control(self) -> None:
        """Start humidity control thread."""
        logging.info("Starting humidity control...")
        start_humidity_control()
        time.sleep(0.1)  # Give thread a moment to start
        humidity_thread = get_humidity_thread()
        if humidity_thread:
            register_thread("humidity_control", humidity_thread)
            self._threads["humidity_control"] = humidity_thread
            logging.info(f"Humidity control started (thread alive: {humidity_thread.is_alive()})")
        else:
            logging.error("Failed to get humidity control thread after starting")

    def _stop_humidity_control(self) -> None:
        """Stop humidity control thread."""
        logging.info("Stopping humidity control...")
        stop_humidity_control()
        self._threads["humidity_control"] = None  # type: ignore[assignment]
        logging.info("Humidity control stopped")

    def monitor(self) -> None:
        """Monitor thread health and handle restart requests.

        This is the main monitoring loop that should be called from main().
        """
        logging.info("Thread monitoring started")

        try:
            while True:
                # Update thread status in shared state
                get_thread_status()

                # Check for thread restart requests from web UI
                restart_requests = get_thread_restart_requests()
                for thread_name in restart_requests:
                    logging.info(f"Processing restart request for thread: {thread_name}")
                    success, message = restart_thread(thread_name)
                    if success:
                        logging.info(f"Successfully restarted thread: {thread_name}")
                    else:
                        logging.error(f"Failed to restart thread {thread_name}: {message}")
                    clear_thread_restart_request(thread_name)

                # Check for thread start requests from web UI
                start_requests = get_thread_start_requests()
                for thread_name in start_requests:
                    logging.info(f"Processing start request for thread: {thread_name}")
                    success, message = start_thread(thread_name)
                    if success:
                        logging.info(f"Successfully started thread: {thread_name}")
                    else:
                        logging.error(f"Failed to start thread {thread_name}: {message}")
                    clear_thread_start_request(thread_name)

                # Check for thread stop requests from web UI
                stop_requests = get_thread_stop_requests()
                for thread_name in stop_requests:
                    logging.info(f"Processing stop request for thread: {thread_name}")
                    success, message = stop_thread(thread_name)
                    if success:
                        logging.info(f"Successfully stopped thread: {thread_name}")
                    else:
                        logging.error(f"Failed to stop thread {thread_name}: {message}")
                    clear_thread_stop_request(thread_name)

                # Monitor core thread health
                if self._writer_thread and not self._writer_thread.is_alive():
                    logging.critical("Database writer thread has exited unexpectedly!")
                if self._collector_thread and not self._collector_thread.is_alive():
                    logging.critical("Data collector thread has exited unexpectedly!")

                # Monitor control threads
                heating_thread = get_heating_thread()
                if heating_thread is not None and not heating_thread.is_alive():
                    logging.critical("Heating control thread has exited unexpectedly!")

                humidity_thread = get_humidity_thread()
                if humidity_thread is not None and not humidity_thread.is_alive():
                    logging.critical("Humidity control thread has exited unexpectedly!")

                # Monitor web UI thread
                if self._webui_thread is not None and not self._webui_thread.is_alive():
                    logging.critical("Web UI thread has exited unexpectedly!")

                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received. Stopping...")
            self.stop()

    def stop(self) -> None:
        """Gracefully stop all threads."""
        logging.info("Stopping all threads...")

        # Signal all threads to stop
        self._stop_event.set()

        # Stop control threads
        stop_heating_control()
        stop_humidity_control()

        # Wait for threads to finish (with timeout)
        for name, thread in self._threads.items():
            if thread.is_alive():
                logging.debug(f"Waiting for {name} thread to stop...")
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logging.warning(f"Thread {name} did not stop gracefully")

        logging.info("All threads stopped")

    def update_read_interval(self, interval: float) -> None:
        """Update the data collection read interval.

        Args:
            interval: New read interval in seconds
        """
        old_interval = self._read_interval
        self._read_interval = interval
        logging.info(f"Read interval changed from {old_interval}s to {interval}s")
