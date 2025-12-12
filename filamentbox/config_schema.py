"""Configuration schema for FilamentBox.

Defines all valid configuration keys, their types, descriptions, examples,
and validation rules. Used by both the config tool and the application.
"""

import re
from typing import Any


# Configuration schema: defines allowed configuration keys
CONFIG_SCHEMA = {
    "database": {
        "enabled": {
            "type": "bool",
            "desc": "Enable database writes (database writer thread)",
            "default": True,
        },
        "type": {
            "type": "str",
            "desc": "Active database backend (only one can be active at a time)",
            "example": "influxdb",
            "choices": ["influxdb", "prometheus", "timescaledb", "victoriametrics", "none"],
            "required": True,
            "default": "none",
        },
        "influxdb": {
            "version": {
                "type": "str",
                "desc": "InfluxDB version (1.x, 2.x, or 3.x)",
                "example": "2",
                "choices": ["1", "2", "3"],
                "default": "2",
            },
            "url": {
                "type": "str",
                "desc": "InfluxDB server URL",
                "example": "http://192.168.1.100:8086",
                "pattern": r"^https?://[\w\.\-]+:\d+$",
                "required": True,
            },
            "token": {
                "type": "str",
                "desc": "InfluxDB authentication token (v2/v3) or password (v1)",
                "sensitive": True,
                "example": "your-token-here",
                "min_length": 1,
                "required": True,
            },
            "org": {
                "type": "str",
                "desc": "InfluxDB organization name (v2 only)",
                "example": "myorg",
                "min_length": 1,
                "required": False,
            },
            "bucket": {
                "type": "str",
                "desc": "InfluxDB bucket name (v2) or database name (v1/v3)",
                "example": "sensors",
                "min_length": 1,
                "required": True,
            },
            "measurement": {
                "type": "str",
                "desc": "InfluxDB measurement name",
                "example": "environment",
                "default": "environment",
            },
            "tags": {},  # Flexible tags - any key-value pairs allowed
            "username": {
                "type": "str",
                "desc": "InfluxDB username (v1 only)",
                "example": "admin",
                "required": False,
            },
        },
        "prometheus": {
            "pushgateway_url": {
                "type": "str",
                "desc": "Prometheus Pushgateway URL",
                "example": "http://192.168.1.100:9091",
                "pattern": r"^https?://[\w\.\-]+:\d+$",
                "required": True,
            },
            "job": {
                "type": "str",
                "desc": "Prometheus job name",
                "example": "filamentbox",
                "min_length": 1,
                "required": True,
            },
            "instance": {
                "type": "str",
                "desc": "Prometheus instance identifier",
                "example": "garage-sensor-01",
                "required": False,
            },
            "grouping_keys": {},  # Flexible grouping keys - any key-value pairs allowed
            "username": {
                "type": "str",
                "desc": "Prometheus basic auth username",
                "example": "admin",
                "required": False,
            },
            "password": {
                "type": "str",
                "desc": "Prometheus basic auth password",
                "example": "secretpassword",
                "sensitive": True,
                "required": False,
            },
        },
        "timescaledb": {
            "host": {
                "type": "str",
                "desc": "TimescaleDB (PostgreSQL) host",
                "example": "192.168.1.100",
                "required": True,
            },
            "port": {
                "type": "int",
                "desc": "TimescaleDB (PostgreSQL) port",
                "example": "5432",
                "min": 1024,
                "max": 65535,
                "default": 5432,
            },
            "database": {
                "type": "str",
                "desc": "TimescaleDB database name",
                "example": "filamentbox",
                "min_length": 1,
                "required": True,
            },
            "username": {
                "type": "str",
                "desc": "TimescaleDB username",
                "example": "postgres",
                "min_length": 1,
                "required": True,
            },
            "password": {
                "type": "str",
                "desc": "TimescaleDB password",
                "example": "secretpassword",
                "sensitive": True,
                "min_length": 1,
                "required": True,
            },
            "table": {
                "type": "str",
                "desc": "TimescaleDB hypertable name",
                "example": "environment_data",
                "default": "environment_data",
            },
            "ssl_mode": {
                "type": "str",
                "desc": "PostgreSQL SSL mode",
                "example": "prefer",
                "choices": ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
                "default": "prefer",
            },
        },
        "victoriametrics": {
            "url": {
                "type": "str",
                "desc": "VictoriaMetrics server URL",
                "example": "http://192.168.1.100:8428",
                "pattern": r"^https?://[\w\.\-]+:\d+$",
                "required": True,
            },
            "username": {
                "type": "str",
                "desc": "VictoriaMetrics basic auth username",
                "example": "admin",
                "required": False,
            },
            "password": {
                "type": "str",
                "desc": "VictoriaMetrics basic auth password",
                "example": "secretpassword",
                "sensitive": True,
                "required": False,
            },
            "tenant": {
                "type": "str",
                "desc": "VictoriaMetrics tenant ID (multi-tenant mode)",
                "example": "0",
                "required": False,
            },
        },
        "batch_size": {
            "type": "int",
            "desc": "Data points per batch before write",
            "example": "10",
            "min": 1,
            "max": 10000,
            "default": 10,
        },
        "flush_interval": {
            "type": "int",
            "desc": "Maximum seconds before forced flush",
            "example": "60",
            "min": 1,
            "max": 3600,
            "default": 60,
        },
    },
    "sensors": {
        "type": {
            "type": "str",
            "desc": "Active sensor type",
            "example": "bme280",
            "choices": ["bme280", "dht22"],
            "required": True,
            "default": "bme280",
        },
        "read_interval": {
            "type": "float",
            "desc": "Seconds between sensor reads",
            "example": "5.0",
            "min": 0.1,
            "max": 3600.0,
            "default": 5.0,
        },
        "bme280": {
            "i2c_address": {
                "type": "str",
                "desc": "I2C address",
                "example": "0x76",
                "pattern": r"^0x[0-9a-fA-F]{2}$",
                "choices": ["0x76", "0x77"],
                "default": "0x76",
            },
            "sea_level_pressure": {
                "type": "float",
                "desc": "Sea level pressure for altitude calculation (hPa)",
                "example": "1013.25",
                "min": 900.0,
                "max": 1100.0,
                "default": 1013.25,
            },
        },
        "dht22": {
            "gpio_pin": {
                "type": "int",
                "desc": "GPIO pin number (BCM numbering)",
                "example": "4",
                "min": 0,
                "max": 27,
                "default": 4,
            },
        },
    },
    "data_collection": {
        "gauge_temp_min": {
            "type": "float",
            "desc": "Minimum value for temperature gauge display (°C)",
            "example": "0.0",
            "default": 0.0,
        },
        "gauge_temp_max": {
            "type": "float",
            "desc": "Maximum value for temperature gauge display (°C)",
            "example": "50.0",
            "default": 50.0,
        },
        "gauge_humidity_min": {
            "type": "float",
            "desc": "Minimum value for humidity gauge display (%)",
            "example": "0.0",
            "default": 0.0,
        },
        "gauge_humidity_max": {
            "type": "float",
            "desc": "Maximum value for humidity gauge display (%)",
            "example": "100.0",
            "default": 100.0,
        },
        "gauge_temp_color_red_high": {
            "type": "float",
            "desc": "Temperature gauge: percentage threshold for red zone (high)",
            "example": "90.0",
            "default": 90.0,
        },
        "gauge_temp_color_yellow_high": {
            "type": "float",
            "desc": "Temperature gauge: percentage threshold for yellow zone (high)",
            "example": "60.0",
            "default": 60.0,
        },
        "gauge_temp_color_green_high": {
            "type": "float",
            "desc": "Temperature gauge: percentage threshold for green zone (high)",
            "example": "30.0",
            "default": 30.0,
        },
        "gauge_temp_color_yellow_low": {
            "type": "float",
            "desc": "Temperature gauge: percentage threshold for yellow zone (low)",
            "example": "10.0",
            "default": 10.0,
        },
        "gauge_humidity_color_red_high": {
            "type": "float",
            "desc": "Humidity gauge: percentage threshold for red zone (high)",
            "example": "90.0",
            "default": 90.0,
        },
        "gauge_humidity_color_yellow_high": {
            "type": "float",
            "desc": "Humidity gauge: percentage threshold for yellow zone (high)",
            "example": "60.0",
            "default": 60.0,
        },
        "gauge_humidity_color_green_high": {
            "type": "float",
            "desc": "Humidity gauge: percentage threshold for green zone (high)",
            "example": "30.0",
            "default": 30.0,
        },
        "gauge_humidity_color_yellow_low": {
            "type": "float",
            "desc": "Humidity gauge: percentage threshold for yellow zone (low)",
            "example": "10.0",
            "default": 10.0,
        },
    },
    "heating_control": {
        "enabled": {
            "type": "bool",
            "desc": "Enable temperature control with heating relay",
            "default": False,
        },
        "gpio_pin": {
            "type": "int",
            "desc": "GPIO pin for heating relay (BCM numbering)",
            "example": "16",
            "min": 0,
            "max": 27,
            "default": 16,
        },
        "min_temp_c": {
            "type": "float",
            "desc": "Minimum temperature threshold (°C) - heater turns off below this",
            "example": "18.0",
            "min": 0.0,
            "max": 50.0,
            "default": 18.0,
        },
        "max_temp_c": {
            "type": "float",
            "desc": "Maximum temperature threshold (°C) - heater turns on above this",
            "example": "22.0",
            "min": 0.0,
            "max": 50.0,
            "default": 22.0,
        },
        "check_interval": {
            "type": "float",
            "desc": "Seconds between control checks",
            "example": "10.0",
            "min": 0.1,
            "max": 3600.0,
            "default": 10.0,
        },
    },
    "humidity_control": {
        "enabled": {
            "type": "bool",
            "desc": "Enable humidity control with fan relay",
            "default": False,
        },
        "gpio_pin": {
            "type": "int",
            "desc": "GPIO pin for fan relay (BCM numbering)",
            "example": "20",
            "min": 0,
            "max": 27,
            "default": 20,
        },
        "min_humidity": {
            "type": "float",
            "desc": "Minimum humidity threshold (%) - fan turns off below this",
            "example": "40.0",
            "min": 0.0,
            "max": 100.0,
            "default": 40.0,
        },
        "max_humidity": {
            "type": "float",
            "desc": "Maximum humidity threshold (%) - fan turns on above this",
            "example": "60.0",
            "min": 0.0,
            "max": 100.0,
            "default": 60.0,
        },
        "check_interval": {
            "type": "float",
            "desc": "Seconds between control checks",
            "example": "10.0",
            "min": 0.1,
            "max": 3600.0,
            "default": 10.0,
        },
    },
    "webui": {
        "enabled": {
            "type": "bool",
            "desc": "Enable web UI",
            "default": True,
        },
        "host": {
            "type": "str",
            "desc": "Web UI host address",
            "example": "0.0.0.0",
            "pattern": r"^(\d{1,3}\.){3}\d{1,3}$|^0\.0\.0\.0$|^localhost$",
            "default": "0.0.0.0",
        },
        "port": {
            "type": "int",
            "desc": "Web UI port number",
            "example": "5000",
            "min": 1024,
            "max": 65535,
            "default": 5000,
        },
    },
    "ui": {
        "show_database_card": {
            "type": "bool",
            "desc": "Show database card on dashboard",
            "default": True,
        },
        "show_heater_card": {
            "type": "bool",
            "desc": "Show heater card on dashboard",
            "default": True,
        },
        "show_fan_card": {
            "type": "bool",
            "desc": "Show fan card on dashboard",
            "default": True,
        },
    },
}


class ValidationError(Exception):
    """Raised when configuration value validation fails."""

    pass


def validate_value(key: str, value: Any, key_info: dict) -> tuple[bool, str, Any]:
    """Validate a configuration value against its schema definition.

    Args:
        key: Configuration key
        value: Value to validate
        key_info: Schema information for the key

    Returns:
        Tuple of (is_valid, error_message, converted_value)
    """
    value_type = key_info.get("type", "str")

    # Declare converted with Union type to allow different types based on value_type
    converted: bool | int | float | str

    # Type conversion and validation
    try:
        if value_type == "bool":
            if isinstance(value, bool):
                converted = value
            elif isinstance(value, str):
                if value.lower() in ["true", "1", "yes", "y", "on"]:
                    converted = True
                elif value.lower() in ["false", "0", "no", "n", "off"]:
                    converted = False
                else:
                    return False, "Invalid boolean value. Use: true/false, yes/no, 1/0", None
            else:
                converted = bool(value)

        elif value_type == "int":
            if isinstance(value, str) and not value.strip().lstrip("-").isdigit():
                return False, f"Invalid integer value: {value}", None
            converted_int: int = int(value)

            # Check min/max
            if "min" in key_info and converted_int < key_info["min"]:
                return False, f"Value must be >= {key_info['min']}", None
            if "max" in key_info and converted_int > key_info["max"]:
                return False, f"Value must be <= {key_info['max']}", None

            # Check choices
            if "choices" in key_info and converted_int not in key_info["choices"]:
                return False, f"Value must be one of: {key_info['choices']}", None

            converted = converted_int

        elif value_type == "float":
            converted_float: float = float(value)

            # Check min/max
            if "min" in key_info and converted_float < key_info["min"]:
                return False, f"Value must be >= {key_info['min']}", None
            if "max" in key_info and converted_float > key_info["max"]:
                return False, f"Value must be <= {key_info['max']}", None

            converted = converted_float

        else:  # str
            converted_str: str = str(value)

            # Check min_length
            if "min_length" in key_info and len(converted_str) < key_info["min_length"]:
                return False, f"Value must be at least {key_info['min_length']} characters", None

            # Check max_length
            if "max_length" in key_info and len(converted_str) > key_info["max_length"]:
                return False, f"Value must be at most {key_info['max_length']} characters", None

            # Check pattern
            if "pattern" in key_info:
                pattern = key_info["pattern"]
                if not re.match(pattern, converted_str):
                    example = key_info.get("example", "")
                    return (
                        False,
                        f"Value does not match required format. Example: {example}",
                        None,
                    )

            converted = converted_str

            # Check choices
            if "choices" in key_info and converted not in key_info["choices"]:
                return False, f"Value must be one of: {key_info['choices']}", None

    except (ValueError, TypeError) as e:
        return False, f"Invalid {value_type} value: {e}", None

    return True, "", converted


def get_key_info(key: str) -> dict:
    """Get schema information for a configuration key.

    Args:
        key: Configuration key (e.g., 'database.influxdb.url')

    Returns:
        Dictionary with schema info or empty dict if not found
    """
    parts = key.split(".")
    schema_node: dict[str, object] = CONFIG_SCHEMA

    try:
        for part in parts:
            if part in schema_node:
                node_value = schema_node[part]
                if isinstance(node_value, dict):
                    schema_node = node_value
                else:
                    return {}
            else:
                return {}

        # If we found a leaf node with 'type', return it
        if isinstance(schema_node, dict) and "type" in schema_node:
            return schema_node
    except (KeyError, TypeError):
        pass

    return {}


def get_all_keys(schema: dict[str, object] | None = None, prefix: str = "") -> set[str]:
    """Recursively get all valid keys from schema.

    Args:
        schema: Schema dictionary (defaults to CONFIG_SCHEMA)
        prefix: Key prefix for recursion

    Returns:
        Set of all valid configuration keys
    """
    if schema is None:
        schema = CONFIG_SCHEMA

    valid_keys = set()

    for key, value in schema.items():
        if prefix:
            full_key = f"{prefix}.{key}"
        else:
            full_key = key

        if isinstance(value, dict):
            # Check if this is a leaf node (has 'type' key)
            is_leaf = "type" in value

            # Check if there are nested configuration keys (sub-dictionaries)
            has_nested_configs = any(
                isinstance(v, dict)
                and ("type" in v or any(isinstance(vv, dict) for vv in v.values()))
                for k, v in value.items()
                if k != "type"  # Exclude the type field itself
            )

            if is_leaf and not has_nested_configs:
                # Pure leaf node - add it
                valid_keys.add(full_key)
            elif is_leaf and has_nested_configs:
                # Mixed node (has both 'type' and nested configs) - add it and recurse
                valid_keys.add(full_key)
                valid_keys.update(get_all_keys(value, full_key))
            else:
                # Intermediate node - just recurse
                valid_keys.update(get_all_keys(value, full_key))

    return valid_keys


def is_flexible_key(key: str) -> bool:
    """Check if a key is allowed to be flexible (like tags).

    Args:
        key: Configuration key

    Returns:
        True if the key can have arbitrary sub-keys
    """
    # Allow flexible keys for tags and grouping keys
    flexible_prefixes = [
        "database.influxdb.tags.",
        "database.prometheus.grouping_keys.",
    ]
    return any(key.startswith(prefix) for prefix in flexible_prefixes)
