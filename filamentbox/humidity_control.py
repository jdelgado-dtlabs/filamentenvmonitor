"""Humidity control via GPIO relay for exhaust fan management.

Controls an exhaust fan via relay to maintain humidity within configured range.
Uses hysteresis to prevent rapid relay cycling.
"""

import logging
import threading
import time
from typing import Optional

from .config import get
from .shared_state import get_fan_manual_override, update_fan_state

# Current humidity value (updated by main thread, read by control thread)
_current_humidity: Optional[float] = None
_humidity_lock = threading.Lock()

# Control thread management
_control_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# GPIO hardware (initialized on first use if enabled)
_relay_pin = None
_gpio_available = False


def _init_gpio() -> bool:
    """Initialize GPIO hardware for relay control.

    Returns:
        True if GPIO initialized successfully, False otherwise.
    """
    global _relay_pin, _gpio_available

    if _relay_pin is not None:
        return _gpio_available

    try:
        import board
        import digitalio

        gpio_pin_num = get("humidity_control.gpio_pin", 20)
        # Map GPIO pin number to board pin
        pin_map = {
            20: board.D20,
            # Add other pins as needed
        }

        if gpio_pin_num not in pin_map:
            logging.warning(
                f"GPIO pin {gpio_pin_num} not in pin_map. Fan control will be disabled."
            )
            _gpio_available = False
            return False

        _relay_pin = digitalio.DigitalInOut(pin_map[gpio_pin_num])
        _relay_pin.direction = digitalio.Direction.OUTPUT
        _relay_pin.value = False  # Start with fan OFF
        _gpio_available = True
        logging.info(f"Initialized humidity control relay on GPIO pin {gpio_pin_num}")
        return True

    except Exception:
        logging.warning(
            "GPIO hardware not available for humidity control. Fan control will be disabled.",
            exc_info=True,
        )
        _gpio_available = False
        return False


def update_humidity(humidity: float) -> None:
    """Update current humidity value for fan control thread.

    Args:
        humidity: Current humidity percentage (0-100).
    """
    global _current_humidity
    with _humidity_lock:
        _current_humidity = humidity


def _humidity_control_loop() -> None:
    """Main control loop for humidity-based fan management.

    Uses hysteresis control:
    - Fan turns ON when humidity > max_humidity
    - Fan turns OFF when humidity < min_humidity
    - Stays in current state when between thresholds
    """
    if not _init_gpio():
        logging.warning("Humidity control disabled due to GPIO initialization failure")
        return

    min_humidity = get("humidity_control.min_humidity", 40.0)
    max_humidity = get("humidity_control.max_humidity", 60.0)
    check_interval = get("humidity_control.check_interval", 1.0)

    logging.info(
        f"Humidity control active: min={min_humidity}%, max={max_humidity}%, "
        f"check_interval={check_interval}s"
    )

    fan_state = False  # Track current fan state

    while not _stop_event.is_set():
        try:
            # Check for manual override first
            manual_override = get_fan_manual_override()

            if manual_override is not None:
                # Manual control mode
                desired_state = manual_override
                if desired_state != fan_state:
                    if _relay_pin:
                        _relay_pin.value = desired_state
                    fan_state = desired_state
                    update_fan_state(fan_state)
                    mode = "MANUAL"
                    logging.info(f"Fan {'ON' if fan_state else 'OFF'} ({mode})")
            else:
                # Automatic control mode
                with _humidity_lock:
                    humidity = _current_humidity

                if humidity is not None:
                    # Hysteresis control logic
                    if humidity > max_humidity and not fan_state:
                        # Humidity too high - turn fan ON
                        if _relay_pin:
                            _relay_pin.value = True  # Pin HIGH = relay closed = fan ON
                        fan_state = True
                        update_fan_state(fan_state)
                        logging.info(f"Fan ON: humidity {humidity:.1f}% > {max_humidity}%")

                    elif humidity < min_humidity and fan_state:
                        # Humidity acceptable - turn fan OFF
                        if _relay_pin:
                            _relay_pin.value = False  # Pin LOW = relay open = fan OFF
                        fan_state = False
                        update_fan_state(fan_state)
                        logging.info(f"Fan OFF: humidity {humidity:.1f}% < {min_humidity}%")

                    else:
                        # Within hysteresis range - maintain current state
                        logging.debug(
                            f"Humidity {humidity:.1f}% in range, fan state: "
                            f"{'ON' if fan_state else 'OFF'}"
                        )
                else:
                    logging.debug("No humidity data available for fan control")

            time.sleep(check_interval)

        except Exception:
            logging.exception("Error in humidity control loop")
            time.sleep(check_interval)

    # Ensure fan is OFF when stopping
    if _relay_pin and _gpio_available:
        _relay_pin.value = False
        logging.info("Fan turned OFF (humidity control stopped)")


def start_humidity_control() -> None:
    """Start the humidity control thread if enabled in configuration."""
    global _control_thread

    enabled = get("humidity_control.enabled", False)
    if not enabled:
        logging.info("Humidity control is disabled in configuration")
        return

    if _control_thread is not None and _control_thread.is_alive():
        logging.warning("Humidity control thread already running")
        return

    _stop_event.clear()
    _control_thread = threading.Thread(
        target=_humidity_control_loop, daemon=True, name="HumidityControl"
    )
    _control_thread.start()
    logging.info("Humidity control thread started")


def stop_humidity_control() -> None:
    """Stop the humidity control thread gracefully."""
    global _control_thread

    if _control_thread is None or not _control_thread.is_alive():
        logging.debug("Humidity control thread not running")
        return

    logging.info("Stopping humidity control thread...")
    _stop_event.set()

    # Wait for thread to finish (with timeout)
    _control_thread.join(timeout=5.0)

    if _control_thread.is_alive():
        logging.warning("Humidity control thread did not stop gracefully")
    else:
        logging.info("Humidity control thread stopped")

    # Ensure fan is OFF
    if _relay_pin and _gpio_available:
        _relay_pin.value = False
        logging.info("Fan ensured OFF on shutdown")

    _control_thread = None
