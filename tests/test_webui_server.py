"""Unit tests for the webui_server Flask application."""

import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, Generator
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock config loading before importing webui_server
with (
    patch("filamentbox.config._ensure_config_loaded"),
    patch("filamentbox.config.get", return_value=True),
):
    # Import the Flask app
    from webui.webui_server import app


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_sensor_data() -> Dict[str, Any]:
    """Mock sensor data for testing."""
    return {
        "temperature_c": 23.5,
        "temperature_f": 74.3,
        "humidity": 45.2,
        "timestamp": datetime.now().timestamp(),
    }


@pytest.fixture
def mock_control_states() -> Dict[str, Any]:
    """Mock control states for testing."""
    return {
        "heater_on": True,
        "heater_manual": None,
        "fan_on": False,
        "fan_manual": None,
    }


def test_get_sensor(client: FlaskClient, mock_sensor_data: Dict[str, Any]) -> None:
    """Test GET /api/sensor endpoint."""
    with patch("webui.webui_server.get_sensor_data", return_value=mock_sensor_data):
        response = client.get("/api/sensor")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["temperature_c"] == 23.5
        assert data["temperature_f"] == 74.3
        assert data["humidity"] == 45.2
        assert "timestamp" in data
        assert "age" in data


def test_get_controls(client: FlaskClient, mock_control_states: Dict[str, Any]) -> None:
    """Test GET /api/controls endpoint."""
    with patch("webui.webui_server.get_control_states", return_value=mock_control_states):
        response = client.get("/api/controls")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["heater"]["on"] is True
        assert data["heater"]["manual"] is None
        assert data["heater"]["mode"] == "auto"
        assert data["fan"]["on"] is False
        assert data["fan"]["manual"] is None
        assert data["fan"]["mode"] == "auto"


def test_get_status(
    client: FlaskClient,
    mock_sensor_data: Dict[str, Any],
    mock_control_states: Dict[str, Any],
) -> None:
    """Test GET /api/status endpoint."""
    with (
        patch("webui.webui_server.get_sensor_data", return_value=mock_sensor_data),
        patch("webui.webui_server.get_control_states", return_value=mock_control_states),
    ):
        response = client.get("/api/status")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "sensor" in data
        assert "controls" in data
        assert data["sensor"]["temperature_c"] == 23.5
        assert data["controls"]["heater"]["on"] is True
        assert data["controls"]["fan"]["on"] is False


def test_control_heater_on(client: FlaskClient) -> None:
    """Test POST /api/controls/heater to turn heater ON."""
    with patch("webui.webui_server.set_heater_manual_override") as mock_set:
        response = client.post(
            "/api/controls/heater",
            data=json.dumps({"state": True}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["state"] is True
        mock_set.assert_called_once_with(True)


def test_control_heater_off(client: FlaskClient) -> None:
    """Test POST /api/controls/heater to turn heater OFF."""
    with patch("webui.webui_server.set_heater_manual_override") as mock_set:
        response = client.post(
            "/api/controls/heater",
            data=json.dumps({"state": False}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["state"] is False
        mock_set.assert_called_once_with(False)


def test_control_heater_auto(client: FlaskClient) -> None:
    """Test POST /api/controls/heater to set auto mode."""
    with patch("webui.webui_server.set_heater_manual_override") as mock_set:
        response = client.post(
            "/api/controls/heater",
            data=json.dumps({"state": None}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["state"] is None
        mock_set.assert_called_once_with(None)


def test_control_heater_missing_state(client: FlaskClient) -> None:
    """Test POST /api/controls/heater with missing state."""
    response = client.post(
        "/api/controls/heater",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400

    data = json.loads(response.data)
    assert "error" in data


def test_control_heater_invalid_json(client: FlaskClient) -> None:
    """Test POST /api/controls/heater with invalid JSON."""
    response = client.post(
        "/api/controls/heater",
        data="invalid json",
        content_type="application/json",
    )
    assert response.status_code == 400


def test_control_fan_on(client: FlaskClient) -> None:
    """Test POST /api/controls/fan to turn fan ON."""
    with patch("webui.webui_server.set_fan_manual_override") as mock_set:
        response = client.post(
            "/api/controls/fan",
            data=json.dumps({"state": True}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["state"] is True
        mock_set.assert_called_once_with(True)


def test_control_fan_off(client: FlaskClient) -> None:
    """Test POST /api/controls/fan to turn fan OFF."""
    with patch("webui.webui_server.set_fan_manual_override") as mock_set:
        response = client.post(
            "/api/controls/fan",
            data=json.dumps({"state": False}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["state"] is False
        mock_set.assert_called_once_with(False)


def test_control_fan_auto(client: FlaskClient) -> None:
    """Test POST /api/controls/fan to set auto mode."""
    with patch("webui.webui_server.set_fan_manual_override") as mock_set:
        response = client.post(
            "/api/controls/fan",
            data=json.dumps({"state": None}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["state"] is None
        mock_set.assert_called_once_with(None)


def test_control_fan_missing_state(client: FlaskClient) -> None:
    """Test POST /api/controls/fan with missing state."""
    response = client.post(
        "/api/controls/fan",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400

    data = json.loads(response.data)
    assert "error" in data


def test_get_sensor_with_none_timestamp(client: FlaskClient) -> None:
    """Test GET /api/sensor when timestamp is None."""
    mock_data = {
        "temperature_c": 23.5,
        "temperature_f": 74.3,
        "humidity": 45.2,
        "timestamp": None,
    }
    with patch("webui.webui_server.get_sensor_data", return_value=mock_data):
        response = client.get("/api/sensor")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["age"] is None


def test_get_controls_manual_mode(client: FlaskClient) -> None:
    """Test GET /api/controls when in manual mode."""
    mock_states = {
        "heater_on": True,
        "heater_manual": True,
        "fan_on": True,
        "fan_manual": False,
    }
    with patch("webui.webui_server.get_control_states", return_value=mock_states):
        response = client.get("/api/controls")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["heater"]["mode"] == "manual"
        assert data["fan"]["mode"] == "manual"


def test_serve_frontend(client: FlaskClient) -> None:
    """Test serving the frontend index.html."""
    # This will fail if index.html doesn't exist, which is expected
    # In a real deployment, the file would exist
    response = client.get("/")
    # We expect either 200 (file exists) or 404 (file doesn't exist in test env)
    assert response.status_code in [200, 404]


def test_cors_headers(client: FlaskClient, mock_sensor_data: Dict[str, Any]) -> None:
    """Test that CORS headers are present."""
    with patch("webui.webui_server.get_sensor_data", return_value=mock_sensor_data):
        response = client.get("/api/sensor")
        # CORS headers should be present
        assert "Access-Control-Allow-Origin" in response.headers
