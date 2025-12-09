# Changelog

All notable changes to the FilamentBox Environment Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2025-12-09

### Added
- **Web UI**: Modern, responsive web interface for monitoring and control
  - Real-time sensor data display (temperature °C/°F, humidity %)
  - Visual status indicators with pulsing animations
  - Manual control interface for heater and fan
  - AUTO/MANUAL mode badges
  - Auto-refresh every 2 seconds
  - Vanilla HTML/CSS/JavaScript (no build tools required)
- **Flask REST API Server** (`webui_server.py`)
  - GET `/api/sensor` - Current sensor readings
  - GET `/api/controls` - Control states
  - GET `/api/status` - Combined sensor and control data
  - POST `/api/controls/heater` - Heater control (ON/OFF/Auto)
  - POST `/api/controls/fan` - Fan control (ON/OFF/Auto)
  - Flask-CORS for cross-origin requests
- **Deployment Infrastructure**
  - Systemd service for web UI (`filamentbox-webui.service`)
  - Automated web UI installer (`install_webui_service.sh`)
  - Nginx reverse proxy configuration (`nginx-filamentbox.conf`)
  - Comprehensive deployment guide (`WEBUI_DEPLOYMENT.md`)
  - Support for both Docker and bare metal nginx installations
- **Intelligent Installation**
  - OS detection (Debian/Ubuntu, RedHat/CentOS/Fedora)
  - Automatic system package detection and installation
  - Python development headers (`python3-dev`/`python3-devel`)
  - Raspberry Pi GPIO library detection (`python3-lgpio`)
  - Interactive nginx configuration with auto-detection
  - Configuration testing and graceful service reloads
- **Comprehensive Testing**
  - 16 new unit tests for web UI server (25 total tests)
  - API endpoint testing (all routes covered)
  - Error handling tests (invalid JSON, missing parameters)
  - Edge case testing (None values, manual mode)
  - CORS header validation
  - All tests passing with full type checking

### Changed
- Enhanced `install_service.sh` with OS detection and package management
- Updated `requirements.txt` with pinned Flask dependencies
- Improved type hints in `webui_server.py` for mypy compatibility
- Color-coded installer output for better user experience

### Documentation
- Added Web UI section to main README
- Created comprehensive WEBUI_DEPLOYMENT.md guide
- Updated service management documentation
- Added API documentation in webui/README.md

## [1.1.0] - 2024

### Added
- **Temperature Control**: Automated heating with relay on GPIO pin 16
  - Hysteresis control to prevent rapid cycling
  - Configurable temperature thresholds
  - Manual override support
- **Humidity Control**: Automated fan/exhaust with relay on GPIO pin 20
  - Hysteresis control for humidity management
  - Configurable humidity thresholds
  - Manual override support
- **CLI Interface**: Curses-based terminal UI (`filamentbox_cli.py`)
  - Real-time sensor data display
  - Current control states (heater/fan)
  - Manual override controls via keyboard
  - Interactive monitoring interface
- **Shared State Management** (`shared_state.py`)
  - Thread-safe state management for sensor readings
  - Thread-safe control state tracking
  - Manual override flags for heater and fan
- **Thread Management**
  - Global `_stop_event` for coordinated shutdown
  - Standardized thread startup/shutdown sequence
  - Improved shutdown with timeout protection
  - Separate threads for heating and humidity control

### Changed
- Refactored thread lifecycle management
- Removed deprecated `read_bme280_data()` function
- Updated all code to use `read_sensor_data()`

### Documentation
- Updated README with control features
- Added CLI interface documentation
- Updated configuration examples

## [1.0.0] - 2024

### Added
- **Multi-Sensor Support**
  - BME280 sensor (I2C)
  - DHT22 sensor (GPIO with configurable pin)
  - Lazy sensor initialization with auto-detection
  - Configurable via `sensor.type` and `sensor.gpio_pin`
- **Systemd Service Integration**
  - Service file (`filamentbox.service`)
  - Automated installer (`install_service.sh`)
  - Runs as root for GPIO access
  - Security hardening flags
  - Auto-restart on failure
- **GitHub Repository and CI/CD**
  - GitHub Actions workflow for Python 3.11-3.13
  - Automated testing on Ubuntu
  - Release workflow with Release Drafter
  - Labels synchronization
  - Public repository visibility

### Changed
- CI/CD fixes for hardware dependency failures
- Implemented try-except for hardware imports
- Lazy config loading via `_ensure_config_loaded()`
- Allowed hardware modules to fail gracefully in CI

### Documentation
- Changed branding to "3D Printer Filament Storage Environment Monitor"
- Comprehensive README with badges and features
- Added hero image (`images/filament.jpeg`)
- Service management documentation

## [0.3.0] - 2024

### Added
- **Code Quality Tools**
  - Ruff linter integration (`ruff check`, `ruff format`)
  - Mypy type checking with `ignore_missing_imports`
  - Pre-commit hooks for automated checks
  - `pyproject.toml` configuration
  - Type stubs for PyYAML (`types-PyYAML`)
- **Type Safety**
  - Added type hints to all functions
  - Comprehensive docstrings
  - Type checking in CI/CD pipeline

### Changed
- Removed unused imports across codebase
- Fixed all linting and type checking errors
- Code formatting with Ruff

## [0.2.0] - 2024

### Added
- **Robustness Features**
  - Thread health monitoring for data collection and writer
  - SQLite persistence for failed batches (`unsent_batches.db`)
  - Exponential backoff with jitter for retries
  - Queue overflow strategy (drop oldest)
  - Batch preview logging in debug mode
- **Testing Infrastructure**
  - pytest test suite
  - Tests for tag handling
  - Tests for InfluxDB failure scenarios
  - Tests for queue operations
  - Mocked hardware for CI/CD

### Changed
- Enhanced error handling throughout
- Improved logging with dual streams (stdout ≤WARNING, stderr ERROR+)
- Better retry logic with configurable thresholds

## [0.1.0] - 2024

### Added
- **Core Functionality**
  - BME280 sensor reading (temperature, humidity, pressure)
  - InfluxDB 1.x client integration
  - Batch writing with configurable intervals
  - Data collection in separate thread
  - InfluxDB writer in separate thread
- **Configuration System**
  - YAML configuration (`config.yaml`)
  - Environment variable overrides (`.env`)
  - Python-dotenv integration
  - Configurable measurement names and tags
- **Tag Support**
  - Flexible tag configuration
  - Tag validation and formatting
  - JSON-compatible tag serialization
- **Field Validation**
  - Numeric field validation
  - Removed invalid "time" field
  - Type checking for all measurements

### Fixed
- Database not found errors
- Invalid field format issues
- Tag handling in line protocol
- Numeric validation for InfluxDB fields

## [Unreleased]

### Planned
- MQTT integration for remote monitoring
- Additional sensor support (SHT31, AM2302)
- Grafana dashboard templates
- Email/SMS alerting
- Historical data visualization in web UI
- Mobile-responsive improvements
- Authentication for web UI

---

## Version Format

Version numbers follow Semantic Versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

## Links

- [Repository](https://github.com/jdelgado-dtlabs/filamentenvmonitor)
- [Issues](https://github.com/jdelgado-dtlabs/filamentenvmonitor/issues)
- [Releases](https://github.com/jdelgado-dtlabs/filamentenvmonitor/releases)
