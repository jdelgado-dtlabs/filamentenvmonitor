"""Shared state for monitoring and control across modules.

Provides thread-safe access to current sensor readings and control states.
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
