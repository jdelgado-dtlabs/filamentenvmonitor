"""Web API server for FilamentBox monitoring and control.

Provides REST API endpoints for sensor data and control states,
plus serves the React frontend.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Tuple, Union

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from filamentbox.shared_state import (
    get_control_states,
    get_sensor_data,
    set_fan_manual_override,
    set_heater_manual_override,
)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBUI_DIR = os.path.join(BASE_DIR, "webui")

app = Flask(__name__, static_folder=WEBUI_DIR, static_url_path="")
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/api/sensor")
def get_sensor() -> Dict[str, Any]:
    """Get current sensor readings.

    Returns:
        JSON with temperature, humidity, and timestamp.
    """
    data = get_sensor_data()
    return jsonify(
        {
            "temperature_c": data["temperature_c"],
            "temperature_f": data["temperature_f"],
            "humidity": data["humidity"],
            "timestamp": data["timestamp"],
            "age": (datetime.now().timestamp() - data["timestamp"] if data["timestamp"] else None),
        }
    )


@app.route("/api/controls")
def get_controls() -> Dict[str, Any]:
    """Get current control states.

    Returns:
        JSON with heater/fan states and manual override flags.
    """
    states = get_control_states()
    return jsonify(
        {
            "heater": {
                "on": states["heater_on"],
                "manual": states["heater_manual"],
                "mode": "manual" if states["heater_manual"] is not None else "auto",
            },
            "fan": {
                "on": states["fan_on"],
                "manual": states["fan_manual"],
                "mode": "manual" if states["fan_manual"] is not None else "auto",
            },
        }
    )


@app.route("/api/controls/heater", methods=["POST"])
def control_heater() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Control heater state.

    Request body:
        {"state": true/false/null}
        - true: force ON
        - false: force OFF
        - null: auto mode

    Returns:
        JSON with success status.
    """
    data = request.get_json()
    if data is None or "state" not in data:
        return jsonify({"error": "Missing 'state' in request body"}), 400

    state = data["state"]
    set_heater_manual_override(state)
    logger.info(f"Heater control set to: {state}")

    return jsonify({"success": True, "state": state})


@app.route("/api/controls/fan", methods=["POST"])
def control_fan() -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Control fan state.

    Request body:
        {"state": true/false/null}
        - true: force ON
        - false: force OFF
        - null: auto mode

    Returns:
        JSON with success status.
    """
    data = request.get_json()
    if data is None or "state" not in data:
        return jsonify({"error": "Missing 'state' in request body"}), 400

    state = data["state"]
    set_fan_manual_override(state)
    logger.info(f"Fan control set to: {state}")

    return jsonify({"success": True, "state": state})


@app.route("/api/status")
def get_status() -> Dict[str, Any]:
    """Get combined sensor and control status.

    Returns:
        JSON with all sensor readings and control states.
    """
    sensor = get_sensor_data()
    controls = get_control_states()

    return jsonify(
        {
            "sensor": {
                "temperature_c": sensor["temperature_c"],
                "temperature_f": sensor["temperature_f"],
                "humidity": sensor["humidity"],
                "timestamp": sensor["timestamp"],
                "age": (
                    datetime.now().timestamp() - sensor["timestamp"]
                    if sensor["timestamp"]
                    else None
                ),
            },
            "controls": {
                "heater": {
                    "on": controls["heater_on"],
                    "manual": controls["heater_manual"],
                    "mode": ("manual" if controls["heater_manual"] is not None else "auto"),
                },
                "fan": {
                    "on": controls["fan_on"],
                    "manual": controls["fan_manual"],
                    "mode": "manual" if controls["fan_manual"] is not None else "auto",
                },
            },
        }
    )


@app.route("/")
def serve_frontend() -> Any:
    """Serve React frontend."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path: str) -> Any:
    """Serve static files from React build."""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")


def main() -> None:
    """Start the web server."""
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
