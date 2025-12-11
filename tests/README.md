# Filament Storage Environmental Manager Tests

This directory contains the test suite for the Filament Storage Environmental Manager.

## Overview

The test suite uses **pytest** and includes comprehensive unit tests for all major components including the web UI API server. All tests use mocked hardware to enable CI/CD testing without physical sensors.

**Test Count**: 25 tests
- 9 core application tests
- 16 web UI server tests

## Running Tests

### All Tests
```bash
# Activate virtual environment
source filamentcontrol/bin/activate

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=filamentbox --cov=webui_server
```

### Specific Test Files
```bash
# Data point and tag handling
pytest tests/test_data_point_tags.py -v

# InfluxDB failure scenarios
pytest tests/test_influx_failure.py -v

# Tag serialization through queue
pytest tests/test_tags_through_queue.py -v

# Web UI API server
pytest tests/test_webui_server.py -v
```

## Test Structure

### Core Application Tests

#### `test_data_point_tags.py`
Tests for tag formatting and inclusion in data points:
- **`test_tag_format_json_compatible`**: Ensures tags are JSON-compatible
- **`test_tags_included_when_present`**: Verifies tags are included when configured
- **`test_tags_omitted_when_not_present`**: Confirms tags are omitted when not configured

#### `test_influx_failure.py`
Tests for failure handling and persistence:
- **`test_influx_writer_alert_and_persist`**: Tests exponential backoff, alert threshold, and SQLite persistence when InfluxDB writes fail

#### `test_tags_through_queue.py`
Tests for tag preservation through the queue system:
- **`test_tags_survive_queue_cycle`**: Ensures tags survive queue operations
- **`test_tags_in_batch_list`**: Verifies tags in batch lists
- **`test_tags_in_batch_serialization`**: Tests tag serialization
- **`test_empty_batch_without_tags`**: Handles empty batches correctly
- **`test_mixed_batch_with_and_without_tags`**: Tests mixed tag scenarios

### Web UI Server Tests

#### `test_webui_server.py`
Comprehensive tests for the Flask REST API:

**GET Endpoints**:
- **`test_get_sensor`**: Tests `/api/sensor` endpoint
- **`test_get_controls`**: Tests `/api/controls` endpoint
- **`test_get_status`**: Tests `/api/status` combined endpoint
- **`test_get_sensor_with_none_timestamp`**: Edge case for None timestamp
- **`test_get_controls_manual_mode`**: Tests manual mode display

**POST Endpoints (Heater Control)**:
- **`test_control_heater_on`**: Turn heater ON via API
- **`test_control_heater_off`**: Turn heater OFF via API
- **`test_control_heater_auto`**: Set heater to AUTO mode
- **`test_control_heater_missing_state`**: Error handling for missing state
- **`test_control_heater_invalid_json`**: Error handling for invalid JSON

**POST Endpoints (Fan Control)**:
- **`test_control_fan_on`**: Turn fan ON via API
- **`test_control_fan_off`**: Turn fan OFF via API
- **`test_control_fan_auto`**: Set fan to AUTO mode
- **`test_control_fan_missing_state`**: Error handling for missing state

**Frontend & CORS**:
- **`test_serve_frontend`**: Tests static file serving
- **`test_cors_headers`**: Verifies CORS headers are present

## Test Utilities

### `simulate_influx_failure.py`
Utility script for manually testing InfluxDB failure scenarios during development. Not run as part of the automated test suite.

## Mocking Strategy

All tests use mocked hardware to avoid requiring physical sensors:

```python
# Example from test_webui_server.py
@pytest.fixture
def mock_sensor_data() -> Dict[str, Any]:
    """Mock sensor data for testing."""
    return {
        "temperature_c": 23.5,
        "temperature_f": 74.3,
        "humidity": 45.2,
        "timestamp": datetime.now().timestamp(),
    }

with patch("webui_server.get_sensor_data", return_value=mock_sensor_data):
    response = client.get("/api/sensor")
```

This approach allows:
- CI/CD testing without hardware
- Fast test execution
- Reliable, repeatable tests
- Easy edge case testing

## CI/CD Integration

Tests run automatically on GitHub Actions for:
- Python 3.11, 3.12, 3.13
- Ubuntu latest
- Every push and pull request

### GitHub Actions Workflow
```yaml
- name: Run tests
  run: |
    pytest tests/ -v
```

## Writing New Tests

### Guidelines

1. **Use pytest fixtures** for reusable test data
2. **Mock all hardware dependencies** (sensors, GPIO, InfluxDB)
3. **Test both success and failure paths**
4. **Include edge cases** (None values, empty data, etc.)
5. **Use descriptive test names** that explain what is being tested
6. **Add docstrings** explaining the test purpose

### Example Test Structure

```python
def test_feature_name(mock_dependency: MockType) -> None:
    """Test that feature works correctly under normal conditions.
    
    This test verifies that when X happens, Y should occur.
    """
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

## Code Coverage

To generate a coverage report:

```bash
pytest tests/ --cov=filamentbox --cov=webui_server --cov-report=html
```

View the report:
```bash
open htmlcov/index.html
```

## Continuous Improvement

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure all new code paths are tested
3. Run the full test suite before committing
4. Update this README if adding new test files

## Related Documentation

- [Main README](../README.md) - Project overview and setup
- [FilamentBox Module README](../filamentbox/README.md) - Core module documentation
- [Web UI README](../webui/README.md) - Web interface documentation
