"""Shared state for monitoring and control across modules.

Provides thread-safe access to current sensor readings and control states.
All data is kept in-memory with thread locks - no file I/O.
"""

import threading
from typing import Optional

# Shared state with thread-safe access
_state_lock = threading.Lock()

# Current sensor readings
_temperature_c: Optional[float] = None
_temperature_f: Optional[float] = None
_humidity: Optional[float] = None
_last_reading_time: Optional[float] = None

# Control states
_heater_state: bool = False
_fan_state: bool = False
_heater_manual_override: Optional[bool] = None
_fan_manual_override: Optional[bool] = None

# Database status
_database_type: str = "unknown"
_database_enabled: bool = False
_database_writer_alive: bool = False
_database_last_write_time: Optional[float] = None
_database_write_failures: int = 0

# Thread status (updated from thread_control module)
_threads_status: dict = {}

# Thread restart requests (for orchestrator signaling)
_thread_restart_requests: dict[str, float] = {}  # thread_name -> timestamp

# Thread start/stop requests (for orchestrator signaling)
_thread_start_requests: dict[str, float] = {}  # thread_name -> timestamp
_thread_stop_requests: dict[str, float] = {}  # thread_name -> timestamp


def update_sensor_data(
    temperature_c: Optional[float],
    temperature_f: Optional[float],
    humidity: Optional[float],
    timestamp: float,
) -> None:
    """Update current sensor readings.

    Args:
        temperature_c: Temperature in Celsius.
        temperature_f: Temperature in Fahrenheit.
        humidity: Humidity percentage.
        timestamp: Unix timestamp of reading.
    """
    global _temperature_c, _temperature_f, _humidity, _last_reading_time
    with _state_lock:
        _temperature_c = temperature_c
        _temperature_f = temperature_f
        _humidity = humidity
        _last_reading_time = timestamp


def get_sensor_data() -> dict:
    """Get current sensor readings.

    Returns:
        Dictionary with temperature_c, temperature_f, humidity, and timestamp.
    """
    with _state_lock:
        return {
            "temperature_c": _temperature_c,
            "temperature_f": _temperature_f,
            "humidity": _humidity,
            "timestamp": _last_reading_time,
        }


def update_heater_state(state: bool) -> None:
    """Update heater state.

    Args:
        state: True if heater is ON, False if OFF.
    """
    global _heater_state
    with _state_lock:
        _heater_state = state


def get_heater_state() -> bool:
    """Get current heater state.

    Returns:
        True if heater is ON, False if OFF.
    """
    with _state_lock:
        return _heater_state


def update_fan_state(state: bool) -> None:
    """Update fan state.

    Args:
        state: True if fan is ON, False if OFF.
    """
    global _fan_state
    with _state_lock:
        _fan_state = state


def get_fan_state() -> bool:
    """Get current fan state.

    Returns:
        True if fan is ON, False if OFF.
    """
    with _state_lock:
        return _fan_state


def set_heater_manual_override(state: Optional[bool]) -> None:
    """Set heater manual override.

    Args:
        state: True to force ON, False to force OFF, None for automatic control.
    """
    global _heater_manual_override
    with _state_lock:
        _heater_manual_override = state


def get_heater_manual_override() -> Optional[bool]:
    """Get heater manual override state.

    Returns:
        True if forced ON, False if forced OFF, None if automatic.
    """
    with _state_lock:
        return _heater_manual_override


def set_fan_manual_override(state: Optional[bool]) -> None:
    """Set fan manual override.

    Args:
        state: True to force ON, False to force OFF, None for automatic control.
    """
    global _fan_manual_override
    with _state_lock:
        _fan_manual_override = state


def get_fan_manual_override() -> Optional[bool]:
    """Get fan manual override state.

    Returns:
        True if forced ON, False if forced OFF, None if automatic.
    """
    with _state_lock:
        return _fan_manual_override


def get_control_states() -> dict:
    """Get all control states.

    Returns:
        Dictionary with heater and fan states and manual overrides.
    """
    with _state_lock:
        return {
            "heater_on": _heater_state,
            "fan_on": _fan_state,
            "heater_manual": _heater_manual_override,
            "fan_manual": _fan_manual_override,
        }


def update_database_status(
    db_type: str,
    enabled: bool,
    writer_alive: bool,
    last_write_time: Optional[float] = None,
    write_failures: int = 0,
) -> None:
    """Update database writer status.

    Args:
        db_type: Type of database (influxdb, prometheus, timescaledb, victoriametrics, none).
        enabled: Whether data collection is enabled.
        writer_alive: Whether the database writer thread is running.
        last_write_time: Unix timestamp of last successful write (optional).
        write_failures: Number of consecutive write failures.
    """
    global _database_type, _database_enabled, _database_writer_alive
    global _database_last_write_time, _database_write_failures
    with _state_lock:
        _database_type = db_type
        _database_enabled = enabled
        _database_writer_alive = writer_alive
        if last_write_time is not None:
            _database_last_write_time = last_write_time
        _database_write_failures = write_failures


def get_database_status() -> dict:
    """Get current database writer status.

    Returns:
        Dictionary with database type, enabled status, writer status, and metrics.
    """
    with _state_lock:
        return {
            "database_type": _database_type,
            "enabled": _database_enabled,
            "writer_alive": _database_writer_alive,
            "last_write_time": _database_last_write_time,
            "write_failures": _database_write_failures,
        }


def update_thread_status(status: dict) -> None:
    """Update thread status information.

    Args:
        status: Dictionary mapping thread names to their status info
    """
    global _threads_status
    with _state_lock:
        _threads_status = status


def get_thread_status() -> dict:
    """Get current thread status.

    Returns:
        Dictionary mapping thread names to their status information.
    """
    with _state_lock:
        return _threads_status.copy()


def request_thread_restart(thread_name: str) -> None:
    """Request a thread restart (orchestrator signal).

    Args:
        thread_name: Name of the thread to restart
    """
    import time

    global _thread_restart_requests
    with _state_lock:
        _thread_restart_requests[thread_name] = time.time()


def get_thread_restart_requests() -> dict[str, float]:
    """Get pending thread restart requests.

    Returns:
        Dictionary mapping thread names to request timestamps
    """
    with _state_lock:
        return _thread_restart_requests.copy()


def request_thread_start(thread_name: str) -> None:
    """Request a thread start (orchestrator signal).

    Args:
        thread_name: Name of the thread to start
    """
    import time

    global _thread_start_requests
    with _state_lock:
        _thread_start_requests[thread_name] = time.time()


def request_thread_stop(thread_name: str) -> None:
    """Request a thread stop (orchestrator signal).

    Args:
        thread_name: Name of the thread to stop
    """
    import time

    global _thread_stop_requests
    with _state_lock:
        _thread_stop_requests[thread_name] = time.time()


def get_thread_start_requests() -> dict[str, float]:
    """Get pending thread start requests.

    Returns:
        Dictionary mapping thread names to request timestamps
    """
    with _state_lock:
        return _thread_start_requests.copy()


def get_thread_stop_requests() -> dict[str, float]:
    """Get pending thread stop requests.

    Returns:
        Dictionary mapping thread names to request timestamps
    """
    with _state_lock:
        return _thread_stop_requests.copy()


def clear_thread_start_request(thread_name: str) -> None:
    """Clear a thread start request after it's been processed.

    Args:
        thread_name: Name of the thread
    """
    global _thread_start_requests
    with _state_lock:
        _thread_start_requests.pop(thread_name, None)


def clear_thread_stop_request(thread_name: str) -> None:
    """Clear a thread stop request after it's been processed.

    Args:
        thread_name: Name of the thread
    """
    global _thread_stop_requests
    with _state_lock:
        _thread_stop_requests.pop(thread_name, None)


def clear_thread_restart_request(thread_name: str) -> None:
    """Clear a thread restart request after it's been processed.

    Args:
        thread_name: Name of the thread whose restart request should be cleared
    """
    global _thread_restart_requests
    with _state_lock:
        if thread_name in _thread_restart_requests:
            del _thread_restart_requests[thread_name]
