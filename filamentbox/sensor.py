"""BME280 sensor interaction helpers (temperature/humidity acquisition + formatting)."""

import logging
import math
from typing import Optional, Tuple

import board
from adafruit_bme280 import basic as adafruit_bme280

from .config import get

# Initialize sensor
i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.sea_level_pressure = get("sensor.sea_level_pressure")


def read_bme280_data() -> Tuple[Optional[float], Optional[float]]:
    """Return (temperature_c, humidity) or (None, None) on invalid/NaN/error."""
    try:
        temperature_c = bme280.temperature
        humidity = bme280.relative_humidity
        # If either value is None, or NaN, treat as no data
        if temperature_c is None or humidity is None:
            return None, None
        # Guard against NaN values returned by some drivers
        if isinstance(temperature_c, float) and math.isnan(temperature_c):
            return None, None
        if isinstance(humidity, float) and math.isnan(humidity):
            return None, None
        return temperature_c, humidity
    except Exception:
        # Log exception as an ERROR so it goes to stderr (handler configured in main)
        logging.exception("Exception while reading BME280 sensor")
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
        logging.warning("Failed to get data from BME280 sensor")
