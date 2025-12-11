"""Temperature-controlled heating relay module.

This module monitors temperature and controls a relay on GPIO pin 16
to maintain temperature within configured thresholds.
"""

import logging
import threading
import time
from typing import Optional

from filamentbox.config import get
from filamentbox.shared_state import (
    get_heater_manual_override,
    update_heater_state,
)
from filamentbox.notification_publisher import notify_info, notify_warning

logger = logging.getLogger(__name__)

# Current temperature reading (shared across threads)
_current_temperature: Optional[float] = None
_temperature_lock = threading.Lock()

# Heating control thread
_heating_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# GPIO setup flag to track if we've initialized
_gpio_initialized = False


def update_temperature(temperature_c: float) -> None:
    """Update the current temperature reading.

    This function is called by the main data collection loop to provide
    the latest temperature reading to the heating control thread.

    Args:
        temperature_c: Temperature in Celsius.
    """
    global _current_temperature
    with _temperature_lock:
        _current_temperature = temperature_c


def _init_gpio() -> bool:
    """Initialize GPIO for heating control.

    Returns:
        True if GPIO initialized successfully, False otherwise.
    """
    global _gpio_initialized

    if _gpio_initialized:
        return True

    try:
        import board
        import digitalio

        heating_pin = get("heating_control.gpio_pin", 16)
        pin = getattr(board, f"D{heating_pin}", None)
        if pin is None:
            logger.error(f"GPIO pin {heating_pin} not available on this board")
            return False

        relay = digitalio.DigitalInOut(pin)
        relay.direction = digitalio.Direction.OUTPUT
        relay.value = False  # Start with heater off

        _gpio_initialized = True
        logger.info(f"Heating control initialized on GPIO pin {heating_pin}")
        return True

    except (ImportError, NotImplementedError, RuntimeError) as e:
        logger.warning(
            f"Failed to initialize GPIO for heating control: {e}. "
            "Heating control will not function."
        )
        return False


def _heating_control_loop() -> None:
    """Main heating control loop (runs in separate thread).

    Monitors temperature and controls relay based on configured thresholds.
    Uses hysteresis to prevent rapid on/off cycling.
    """
    if not _init_gpio():
        logger.error("Cannot start heating control: GPIO initialization failed")
        return

    try:
        import board
        import digitalio

        heating_pin = get("heating_control.gpio_pin", 16)
        pin = getattr(board, f"D{heating_pin}")
        relay = digitalio.DigitalInOut(pin)
        relay.direction = digitalio.Direction.OUTPUT

    except Exception as e:
        logger.error(f"Failed to setup GPIO in heating loop: {e}")
        return

    # Get configuration
    enabled = get("heating_control.enabled", False)
    if not enabled:
        logger.info("Heating control is disabled in configuration")
        return

    min_temp = get("heating_control.min_temp_c")
    max_temp = get("heating_control.max_temp_c")
    check_interval = get("heating_control.check_interval", 1.0)

    if min_temp is None or max_temp is None:
        logger.error("Heating control requires min_temp_c and max_temp_c in configuration")
        return

    if min_temp >= max_temp:
        logger.error(
            f"Invalid temperature thresholds: min={min_temp}, max={max_temp}. "
            "min_temp_c must be less than max_temp_c"
        )
        return

    logger.info(
        f"Heating control active: ON below {min_temp}°C, OFF above {max_temp}°C (check interval: {check_interval}s)"
    )

    heater_state = False  # Track current state

    while not _stop_event.is_set():
        try:
            # Check for manual override first
            manual_override = get_heater_manual_override()

            if manual_override is not None:
                # Manual control mode
                desired_state = manual_override
                if desired_state != heater_state:
                    relay.value = desired_state
                    heater_state = desired_state
                    update_heater_state(heater_state)
                    mode = "MANUAL"
                    logger.info(f"Heater {'ON' if heater_state else 'OFF'} ({mode})")
                    # Send notification
                    if heater_state:
                        notify_info("🔥 Heater turned ON (manual override)")
                    else:
                        notify_info("🔥 Heater turned OFF (manual override)")
                    # Send notification
                    if heater_state:
                        notify_info("🔥 Heater turned ON (manual override)")
                    else:
                        notify_info("🔥 Heater turned OFF (manual override)")
            else:
                # Automatic control mode
                # Get current temperature
                with _temperature_lock:
                    temp = _current_temperature

                if temp is None:
                    # No temperature reading yet, wait
                    time.sleep(check_interval)
                    continue

                # Implement hysteresis control
                # Turn on if below min, turn off if above max
                if temp < min_temp and not heater_state:
                    relay.value = True
                    heater_state = True
                    update_heater_state(heater_state)
                    logger.info(f"Heater ON: temperature {temp:.2f}°C < {min_temp}°C")
                    notify_info(f"🔥 Heater turned ON (temperature {temp:.1f}°C < {min_temp}°C)")
                elif temp > max_temp and heater_state:
                    relay.value = False
                    heater_state = False
                    update_heater_state(heater_state)
                    logger.info(f"Heater OFF: temperature {temp:.2f}°C > {max_temp}°C")
                    notify_warning(
                        f"⚠️ Temperature too high: {temp:.1f}°C (max: {max_temp}°C) - Heater turned OFF"
                    )

            time.sleep(check_interval)

        except Exception as e:
            logger.error(f"Error in heating control loop: {e}", exc_info=True)
            time.sleep(check_interval)

    # Cleanup: ensure heater is off when stopping
    try:
        relay.value = False
        logger.info("Heating control stopped, heater turned off")
    except Exception as e:
        logger.error(f"Error turning off heater during shutdown: {e}")


def get_heating_thread() -> Optional[threading.Thread]:
    """Get the heating control thread instance.

    Returns:
        The heating control thread if it exists, None otherwise.
    """
    logger.debug(
        f"get_heating_thread() called, _heating_thread={_heating_thread}, alive={_heating_thread.is_alive() if _heating_thread else 'N/A'}"
    )
    return _heating_thread


def start_heating_control() -> None:
    """Start the heating control thread.

    Should be called once at application startup if heating control is enabled.
    """
    global _heating_thread

    enabled = get("heating_control.enabled", False)
    if not enabled:
        logger.info("Heating control is disabled")
        return

    if _heating_thread is not None and _heating_thread.is_alive():
        logger.warning("Heating control thread already running")
        return

    _stop_event.clear()
    _heating_thread = threading.Thread(
        target=_heating_control_loop, name="HeatingControl", daemon=True
    )
    _heating_thread.start()
    logger.info(
        f"Heating control thread started (alive={_heating_thread.is_alive()}, id={id(_heating_thread)})"
    )


def stop_heating_control() -> None:
    """Stop the heating control thread gracefully.

    Should be called during application shutdown.
    """
    global _heating_thread

    if _heating_thread is None or not _heating_thread.is_alive():
        logger.debug("Heating control thread not running")
        return

    logger.info("Stopping heating control thread...")
    _stop_event.set()
    _heating_thread.join(timeout=5.0)

    if _heating_thread.is_alive():
        logger.warning("Heating control thread did not stop gracefully")
    else:
        logger.info("Heating control thread stopped")

    _heating_thread = None


def is_heating_control_active() -> bool:
    """Check if heating control thread is active.

    Returns:
        True if the heating control thread is running, False otherwise.
    """
    return _heating_thread is not None and _heating_thread.is_alive()
