"""Sensor interaction helpers (temperature/humidity acquisition + formatting).

Supports multiple sensor types:
- BME280 (I2C)
- DHT22 (GPIO pin)
"""

import logging
import math
from typing import Optional, Tuple

from .config import get

# Global sensor instance (initialized on first read)
_sensor = None
_sensor_type = None


def _init_sensor():
    """Initialize the configured sensor on first use."""
    global _sensor, _sensor_type
    if _sensor is not None:
        return

    sensor_type = get("sensor.type", "bme280").lower()
    _sensor_type = sensor_type

    try:
        if sensor_type == "bme280":
            import board
            from adafruit_bme280 import basic as adafruit_bme280

            i2c = board.I2C()
            _sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)
            _sensor.sea_level_pressure = get("sensor.sea_level_pressure")
            logging.info("Initialized BME280 sensor on I2C")

        elif sensor_type == "dht22":
            import board
            import adafruit_dht

            pin_number = get("sensor.gpio_pin", 4)
            pin = getattr(board, f"D{pin_number}")
            _sensor = adafruit_dht.DHT22(pin, use_pulseio=False)
            logging.info(f"Initialized DHT22 sensor on GPIO pin {pin_number}")

        else:
            raise ValueError(f"Unsupported sensor type: {sensor_type}")
    except (ImportError, NotImplementedError, RuntimeError) as e:
        # Handle missing hardware libraries or unavailable hardware in CI/test environments
        logging.warning(f"Sensor initialization failed (hardware may not be available): {e}")
        _sensor = None


def read_sensor_data() -> Tuple[Optional[float], Optional[float]]:
    """Return (temperature_c, humidity) or (None, None) on invalid/NaN/error.

    Automatically detects and initializes the configured sensor type.
    """
    _init_sensor()

    try:
        if _sensor_type == "bme280" and _sensor is not None:
            temperature_c = _sensor.temperature
            humidity = _sensor.relative_humidity
        elif _sensor_type == "dht22" and _sensor is not None:
            temperature_c = _sensor.temperature
            humidity = _sensor.humidity
        else:
            return None, None

        # If either value is None, or NaN, treat as no data
        if temperature_c is None or humidity is None:
            return None, None
        # Guard against NaN values returned by some drivers
        if isinstance(temperature_c, float) and math.isnan(temperature_c):
            return None, None
        if isinstance(humidity, float) and math.isnan(humidity):
            return None, None
        return temperature_c, humidity
    except RuntimeError as e:
        # DHT sensors occasionally throw RuntimeError for timing issues
        logging.warning(f"Sensor read timeout/error: {e}")
        return None, None
    except Exception:
        # Log exception as an ERROR so it goes to stderr (handler configured in main)
        logging.exception(f"Exception while reading {_sensor_type} sensor")
        return None, None


def convert_c_to_f(temperature_c: float) -> float:
    """Convert Celsius value to Fahrenheit."""
    return temperature_c * (9 / 5) + 32


def log_data(
    temperature_c: Optional[float], temperature_f: Optional[float], humidity: Optional[float]
) -> None:
    """Emit debug line for valid readings or warning when missing."""
    if humidity is not None and temperature_f is not None:
        logging.debug(
            f"Temperature={temperature_f:.1f}°F {temperature_c:.1f}°C Humidity={humidity:.1f}%"
        )
    else:
        # Missing sensor data — warn so operators notice intermittent failures
        sensor_name = _sensor_type.upper() if _sensor_type else "sensor"
        logging.warning(f"Failed to get data from {sensor_name}")
