"""Web API server for Filament Storage Environmental Manager.

Provides REST API endpoints for sensor data and control states,
plus serves the React frontend.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Tuple, Union

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from filamentbox.config import get
from filamentbox.config_db import ConfigDB
from filamentbox.config_schema import CONFIG_SCHEMA, get_key_info, validate_value
from filamentbox.shared_state import (
    get_control_states,
    get_database_status,
    get_sensor_data,
    get_thread_status,
    request_thread_restart,
    request_thread_start,
    request_thread_stop,
    set_fan_manual_override,
    set_heater_manual_override,
)
from filamentbox.notification_publisher import get_recent_notifications, clear_notifications

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Serve React build if it exists, otherwise fallback to legacy HTML
REACT_BUILD_DIR = os.path.join(BASE_DIR, "webui-react", "dist")
WEBUI_DIR = REACT_BUILD_DIR if os.path.exists(REACT_BUILD_DIR) else BASE_DIR

# Disable Flask's default static file handling - we'll handle it ourselves
app = Flask(__name__, static_folder=None)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Disable caching during development
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/api/sensor")
def get_sensor() -> Response:
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
def get_controls() -> Response:
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


@app.route("/api/database")
def get_database() -> Response:
    """Get current database writer status.

    Returns:
        JSON with database type, enabled status, writer health, and metrics.
    """
    status = get_database_status()

    # Calculate age of last write
    last_write_age = None
    if status["last_write_time"]:
        last_write_age = datetime.now().timestamp() - status["last_write_time"]

    return jsonify(
        {
            "type": status["database_type"],
            "enabled": status["enabled"],
            "writer_alive": status["writer_alive"],
            "last_write_time": status["last_write_time"],
            "last_write_age": last_write_age,
            "write_failures": status["write_failures"],
            "storing_data": status["enabled"] and status["database_type"] != "none",
        }
    )


@app.route("/api/controls/heater", methods=["POST"])
def control_heater() -> Union[Response, Tuple[Response, int]]:
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
def control_fan() -> Union[Response, Tuple[Response, int]]:
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


@app.route("/api/threads")
def get_threads() -> Response:
    """Get status of all worker threads.

    Returns:
        JSON with thread status information.
    """
    status = get_thread_status()
    return jsonify(status)


@app.route("/api/threads/<thread_name>/restart", methods=["POST"])
def restart_thread_endpoint(thread_name: str) -> Union[Response, Tuple[Response, int]]:
    """Restart a specific worker thread.

    Args:
        thread_name: Name of the thread to restart

    Returns:
        JSON with success status and message.
    """
    # Get current thread status to validate the request
    threads = get_thread_status()

    if thread_name not in threads:
        return jsonify({"success": False, "error": f"Unknown thread: {thread_name}"}), 400

    if not threads[thread_name].get("restartable", False):
        return (
            jsonify({"success": False, "error": f"Thread '{thread_name}' is not restartable"}),
            400,
        )

    # Signal the main process to restart the thread
    request_thread_restart(thread_name)
    logger.info(f"Thread restart requested via API: {thread_name}")

    return jsonify({"success": True, "message": f"Restart requested for thread '{thread_name}'"})


@app.route("/api/threads/<thread_name>/start", methods=["POST"])
def start_thread_endpoint(thread_name: str) -> Union[Response, Tuple[Response, int]]:
    """Start a specific worker thread.

    Args:
        thread_name: Name of the thread to start

    Returns:
        JSON with success status and message.
    """
    threads = get_thread_status()

    if thread_name not in threads:
        return jsonify({"success": False, "error": f"Unknown thread: {thread_name}"}), 400

    if threads[thread_name].get("running", False):
        return jsonify(
            {"success": False, "error": f"Thread '{thread_name}' is already running"}
        ), 400

    request_thread_start(thread_name)
    logger.info(f"Thread start requested via API: {thread_name}")

    return jsonify({"success": True, "message": f"Start requested for thread '{thread_name}'"})


@app.route("/api/threads/<thread_name>/stop", methods=["POST"])
def stop_thread_endpoint(thread_name: str) -> Union[Response, Tuple[Response, int]]:
    """Stop a specific worker thread.

    Args:
        thread_name: Name of the thread to stop

    Returns:
        JSON with success status and message.
    """
    threads = get_thread_status()

    if thread_name not in threads:
        return jsonify({"success": False, "error": f"Unknown thread: {thread_name}"}), 400

    if not threads[thread_name].get("running", False):
        return jsonify({"success": False, "error": f"Thread '{thread_name}' is not running"}), 400

    request_thread_stop(thread_name)
    logger.info(f"Thread stop requested via API: {thread_name}")

    return jsonify({"success": True, "message": f"Stop requested for thread '{thread_name}'"})


@app.route("/api/config/<path:key>")
def get_config_value(key: str) -> Response:
    """Get a specific configuration value with metadata.

    Args:
        key: Configuration key path (e.g., 'heating_control.min_temp_c')

    Returns:
        JSON with value, description, type, and validation info.
    """
    try:
        value = get(key)
        key_info = get_key_info(key)

        return jsonify(
            {
                "key": key,
                "value": value,
                "type": key_info.get("type", "str"),
                "description": key_info.get("desc", ""),
                "example": key_info.get("example", ""),
                "required": key_info.get("required", False),
                "choices": key_info.get("choices"),
                "min": key_info.get("min"),
                "max": key_info.get("max"),
            }
        )
    except Exception as e:
        logger.error(f"Error getting config value for {key}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/config/<path:key>", methods=["PUT"])
def set_config_value(key: str) -> Union[Response, Tuple[Response, int]]:
    """Set a configuration value with validation.

    Args:
        key: Configuration key path

    Request body:
        {"value": <new_value>}

    Returns:
        JSON with success status and validation errors if any.
    """
    try:
        data = request.get_json()
        if data is None or "value" not in data:
            return jsonify({"error": "Missing 'value' in request body"}), 400

        new_value = data["value"]
        key_info = get_key_info(key)

        if not key_info:
            return jsonify({"error": f"Unknown configuration key: {key}"}), 400

        # Validate the value
        is_valid, error_message, converted_value = validate_value(key, new_value, key_info)

        if not is_valid:
            return jsonify({"error": error_message, "valid": False}), 400

        # Save to database
        db = ConfigDB()
        try:
            description = key_info.get("desc", "")
            db.set(key, converted_value, description)

            # Touch database file to trigger hot-reload
            import time
            from filamentbox.config_db import CONFIG_DB_PATH

            os.utime(CONFIG_DB_PATH, (time.time(), time.time()))

            logger.info(f"Configuration updated via API: {key} = {converted_value}")
            return jsonify({"success": True, "value": converted_value, "valid": True})
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error setting config value for {key}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/config/section/<section>")
def get_config_section(section: str) -> Response:
    """Get all configuration values for a section.

    Args:
        section: Section name (e.g., 'heating_control', 'database')

    Returns:
        JSON with all keys in the section with their values and metadata.
    """
    try:
        result = {}

        # Get schema for the section
        if section not in CONFIG_SCHEMA:
            return jsonify({"error": f"Unknown section: {section}"}), 404

        section_schema = CONFIG_SCHEMA[section]

        def collect_values(schema_node, prefix=""):
            """Recursively collect configuration values."""
            for key, value in schema_node.items():
                if isinstance(value, dict) and "type" in value:
                    # This is a leaf configuration item
                    full_key = f"{prefix}.{key}" if prefix else key
                    config_value = get(full_key)

                    result[full_key] = {
                        "value": config_value,
                        "type": value.get("type", "str"),
                        "description": value.get("desc", ""),
                        "example": value.get("example", ""),
                        "required": value.get("required", False),
                        "default": value.get("default"),
                        "choices": value.get("choices"),
                        "min": value.get("min"),
                        "max": value.get("max"),
                    }
                elif isinstance(value, dict):
                    # Recurse into subsection
                    full_key = f"{prefix}.{key}" if prefix else key
                    collect_values(value, full_key)

        collect_values(section_schema, section)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting config section {section}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def get_status() -> Response:
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


@app.route("/api/notifications")
def get_notifications() -> Response:
    """Get recent notifications.

    Query params:
        limit: Maximum number of notifications to return (default: 10)

    Returns:
        JSON array of recent notifications with message, type, timestamp
    """
    limit = request.args.get("limit", 10, type=int)
    limit = max(1, min(limit, 50))  # Clamp between 1 and 50

    notifications = get_recent_notifications(limit)
    return jsonify({"notifications": notifications})


@app.route("/api/notifications", methods=["DELETE"])
def delete_notifications() -> Response:
    """Clear all stored notifications.

    Returns:
        JSON success message
    """
    clear_notifications()
    return jsonify({"message": "Notifications cleared", "success": True})


@app.route("/api/stream")
def stream_updates() -> Response:
    """Server-Sent Events endpoint for real-time updates.

    Streams combined sensor, control, database, and thread status updates
    to the client every second. Clients should use EventSource API to connect.

    Returns:
        SSE stream with JSON data events
    """

    def generate():
        """Generate SSE events with system status updates."""
        while True:
            try:
                # Get all status data
                sensor_data = get_sensor_data()
                control_states = get_control_states()
                db_status = get_database_status()
                threads = get_thread_status()

                # Calculate sensor age
                sensor_age = None
                if sensor_data["timestamp"]:
                    sensor_age = datetime.now().timestamp() - sensor_data["timestamp"]

                # Calculate database last write age
                db_last_write_age = None
                if db_status["last_write_time"]:
                    db_last_write_age = datetime.now().timestamp() - db_status["last_write_time"]

                # Combine all data into one update
                update = {
                    "sensor": {
                        "temperature_c": sensor_data["temperature_c"],
                        "temperature_f": sensor_data["temperature_f"],
                        "humidity": sensor_data["humidity"],
                        "timestamp": sensor_data["timestamp"],
                        "age": sensor_age,
                    },
                    "controls": {
                        "heater": {
                            "on": control_states["heater_on"],
                            "manual": control_states["heater_manual"],
                            "mode": "manual"
                            if control_states["heater_manual"] is not None
                            else "auto",
                        },
                        "fan": {
                            "on": control_states["fan_on"],
                            "manual": control_states["fan_manual"],
                            "mode": "manual"
                            if control_states["fan_manual"] is not None
                            else "auto",
                        },
                    },
                    "database": {
                        "type": db_status.get("database_type", "none"),
                        "enabled": db_status.get("enabled", False),
                        "storing_data": db_status.get("enabled", False)
                        and db_status.get("database_type", "none") != "none",
                        "last_write_time": db_status.get("last_write_time"),
                        "last_write_age": db_last_write_age,
                        "writer_alive": db_status.get("writer_alive", False),
                        "write_failures": db_status.get("write_failures", 0),
                    },
                    "threads": threads,
                }

                # Send SSE formatted message
                yield f"data: {json.dumps(update)}\n\n"

                # Wait 1 second before next update
                time.sleep(1)

            except GeneratorExit:
                # Client disconnected
                logger.info("SSE client disconnected")
                break
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                # Send error event and continue
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@app.route("/")
def serve_frontend() -> Response:
    """Serve React frontend."""
    return send_from_directory(WEBUI_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path: str) -> Response:
    """Serve static files from React build or index.html for client-side routes."""
    # Don't intercept API routes - they're handled by other routes
    if path.startswith("api/"):
        # This shouldn't happen as API routes are defined separately
        logger.warning(f"API route {path} hit catch-all handler")
        return jsonify({"error": "Not found"}), 404

    file_path = os.path.join(WEBUI_DIR, path)

    # If the file exists and is a file (not directory), serve it
    if os.path.exists(file_path) and os.path.isfile(file_path):
        logger.info(f"Serving static file: {path}")
        return send_from_directory(WEBUI_DIR, path)

    # For all other paths (including /kiosk), serve index.html for client-side routing
    logger.info(f"Serving index.html for client-side route: {path}")
    return send_from_directory(WEBUI_DIR, "index.html")


def main() -> None:
    """Start the web server."""
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
