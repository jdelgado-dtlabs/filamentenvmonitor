# 3D Printer Filament Storage Environment Monitor

<p align="center">
  <img src="images/filament.jpeg" alt="Filament Storage Environment" width="600" />
</p>

![CI](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/ci.yml/badge.svg)
![Release](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/release.yml/badge.svg)
[![Latest Release](https://img.shields.io/github/v/release/jdelgado-dtlabs/filamentenvmonitor?label=latest%20release)](https://github.com/jdelgado-dtlabs/filamentenvmonitor/releases/latest)

A Python 3.13 application for monitoring temperature and humidity in 3D printer filament storage environments. Supports multiple sensor types (BME280, DHT22) with robust data collection, batching, InfluxDB integration, active environment control, and both CLI and Web UI interfaces.

## Highlights (v1.6)
- **Master Installer**: Interactive installation with directory selection and automatic configuration
- **Version Control**: Smart update system with automatic version detection and graceful upgrades
- **Web UI**: Modern, responsive browser-based interface with real-time monitoring and control
- **Production deployment**: Automated installers with OS detection (Debian/Ubuntu, RedHat/CentOS)
- **Nginx integration**: Automated reverse proxy configuration for Docker and bare metal
- Multi-sensor support: BME280 (I2C) and DHT22 (GPIO)
- Temperature-controlled heating: GPIO relay control with hysteresis
- Humidity-controlled exhaust fan: GPIO relay control with hysteresis
- CLI interface: Real-time terminal-based monitoring and control
- Reliable batching, exponential backoff with jitter, SQLite persistence
- YAML config with env overrides and lazy loading
- Full CI/CD: Ruff, Mypy, pytest (25 tests) on Python 3.11–3.13; automated Releases

## Features
- **Multi-sensor support**: BME280 (I2C) and DHT22 (GPIO) with automatic detection
- **Temperature control**: Optional GPIO relay control for heating with configurable thresholds
- **Humidity control**: Optional GPIO relay control for exhaust fan with configurable thresholds
- **Web UI**: Modern, responsive web interface accessible from any browser
- **CLI interface**: Real-time monitoring and manual control of heater/fan with curses-based UI
- **Reliable data collection**: Configurable intervals with graceful error handling
- **Batched writes**: Optimized InfluxDB writes with size and time-based flush triggers
- **Automatic recovery**: SQLite persistence of unsent batches across restarts
- **Smart retry logic**: Exponential backoff with jitter on write failures
- **Alert system**: Configurable failure threshold with optional persistence
- **Queue management**: Overflow handling that prioritizes fresh data
- **Flexible configuration**: YAML-based with environment variable overrides
- **Debug visibility**: Structured logging with batch preview before writes
- **Production ready**: Systemd service integration with automated installer
- **Code quality**: Full type hints, pre-commit hooks, automated CI/CD
- **Remote InfluxDB**: Designed for network-based database deployments

## Documentation

- **[Installation Guide](install/INSTALL.md)** ([PDF](install/INSTALL.pdf)) - Complete installation and configuration guide
- **[FilamentBox Core Module](filamentbox/README.md)** - Detailed module architecture and component documentation
- **[Tests](tests/README.md)** - Complete testing documentation and guidelines
- **[Web UI](webui/README.md)** - Web interface API documentation
- **[Web UI Deployment](webui/WEBUI_DEPLOYMENT.md)** - Production deployment guide with nginx and HTTPS
- **[CHANGELOG](CHANGELOG.md)** - Version history and release notes

## Quick Start

### Requirements
- Python 3.13+ (virtual environment recommended)
- InfluxDB 1.x HTTP API
- Raspberry Pi with BME280 (I2C) or DHT22 (GPIO) sensor

### Installation

```bash
# Clone the repository
git clone https://github.com/jdelgado-dtlabs/filamentenvmonitor.git
cd filamentenvmonitor

# Optional: Run comprehensive configuration setup (creates .env file)
# Supports all config.yaml options: InfluxDB, sensors, heating, humidity control, etc.
./install/setup.sh

# Run the master installer
sudo ./install/install.sh
```

The installer handles everything: directory setup, service installation, and verification.

**For detailed installation instructions, hardware setup, configuration options, and troubleshooting, see the [Installation Guide](install/INSTALL.md)** ([PDF version](install/INSTALL.pdf))

## Configuration

Configuration is managed through `config.yaml` with optional environment variable overrides.

**Key configuration areas**:
- InfluxDB connection settings
- Data collection intervals and batching
- Sensor type and GPIO pins
- Temperature and humidity control thresholds
- Retry and persistence behavior

**For complete configuration details, examples, and best practices, see the [Installation Guide](install/INSTALL.md#configuration-guide)**

## Running the Application

### Interactive Mode
```bash
source filamentcontrol/bin/activate
python -m filamentbox.main           # Normal run
python -m filamentbox.main --debug   # Enable verbose debug logging
```

### CLI Monitoring & Control Interface
A real-time CLI interface for monitoring sensor readings and controlling heater/fan:

```bash
source filamentcontrol/bin/activate
python filamentbox_cli.py
```

**Features**:
- Real-time sensor readings (temperature, humidity)
- Control status display (heater/fan on/off, auto/manual mode)
- Manual override controls:
  - `H` - Turn heater ON (manual)
  - `h` - Turn heater OFF (manual)
  - `Ctrl+H` - Return heater to AUTO mode
  - `F` - Turn fan ON (manual)
  - `f` - Turn fan OFF (manual)
  - `Ctrl+F` - Return fan to AUTO mode
  - `R` - Refresh display
  - `Q` - Quit

**Note**: The main application must be running for the CLI to display data and control devices.

### Web UI Interface
A modern, responsive web interface for monitoring and controlling from any browser:

```bash
# Install web dependencies
source filamentcontrol/bin/activate
pip install Flask Flask-CORS

# Start the web server (main application must be running)
python webui/webui_server.py
```

Access the web interface at `http://localhost:5000` or `http://YOUR_PI_IP:5000` from any device on your network.

**Features**:
- Real-time sensor readings with auto-refresh
- Visual indicators for heater/fan status (ON/OFF)
- AUTO/MANUAL mode badges
- One-click controls for manual override
- Mobile-friendly responsive design
- No build tools or Node.js required

**Production Deployment**:
```bash
# Install as systemd service
sudo ./install_webui_service.sh

# Access at http://YOUR_PI_IP:5000
# Or configure nginx reverse proxy for standard HTTP/HTTPS ports
```

See `webui/README.md` for API documentation and `install/INSTALL.md` for complete deployment guide including nginx configuration, HTTPS setup, and troubleshooting.

## Production Deployment

### Systemd Service Installation

```bash
# Master installer (recommended)
sudo ./install/install.sh

# Or install services individually
sudo ./install/install_service.sh          # Main application
sudo ./install/install_webui_service.sh    # Web UI
```

### Service Management

```bash
# Check status
sudo systemctl status filamentbox.service
sudo systemctl status filamentbox-webui.service

# View logs
sudo journalctl -u filamentbox.service -f
```

**For complete service management, updating, nginx configuration, and troubleshooting, see the [Installation Guide](install/INSTALL.md#service-management)**

## Temperature and Humidity Control

The application supports optional GPIO relay control for both heating and humidity management. See the [FilamentBox Core Module documentation](filamentbox/README.md#heating_controlpy) for detailed information on:
- Configuration options
- Hysteresis control logic
- Wiring and safety considerations
- Manual override capabilities

**Quick Setup**:
```yaml
# In config.yaml
heating_control:
  enabled: true
  gpio_pin: 16
  min_temp_c: 18.0
  max_temp_c: 22.0

humidity_control:
  enabled: true
  gpio_pin: 20
  min_humidity: 40.0
  max_humidity: 60.0
```

## Common Issues

Quick troubleshooting reference:

| Symptom | Resolution |
|--------|------------|
| Database not found | Set `INFLUXDB_DATABASE` in config or environment |
| Sensor read errors | Verify `sensor.type` in config matches hardware |
| Service won't start | Check `config.yaml` exists and is valid |
| Relay cycling rapidly | Increase gap between min/max thresholds |

**For comprehensive troubleshooting, hardware setup, and debugging, see the [Installation Guide](install/INSTALL.md#troubleshooting)**

## Quick Reference Commands
```bash
# Run application
python -m filamentbox.main
python -m filamentbox.main --debug

# Service management
sudo systemctl status filamentbox.service
sudo systemctl restart filamentbox.service
sudo journalctl -u filamentbox.service -f

# Web UI service
sudo systemctl status filamentbox-webui.service
sudo journalctl -u filamentbox-webui.service -f

# Development
ruff check .
mypy filamentbox
pytest tests/
```

For more detailed technical information, see:
- [FilamentBox Core Module](filamentbox/README.md) - Architecture and component details
- [Tests Documentation](tests/README.md) - Testing guide and coverage


### Module Responsibilities
- `main.py` - Application entry point, thread orchestration, data collection loop
- `sensor.py` - Multi-sensor abstraction (BME280/DHT22), lazy initialization, error handling
- `influx_writer.py` - Batched InfluxDB writes, retry logic, alerting, queue management
- `persistence.py` - SQLite-based batch recovery, pruning, error resilience
- `config.py` - YAML + environment variable configuration with lazy loading
- `logging_config.py` - Dual-stream logging (stdout/stderr split)

### Configuration Hierarchy
1. `config.yaml` - Base configuration (checked into version control)
2. `.env` - Local overrides for credentials and host-specific settings (gitignored)
3. Environment variables - Runtime overrides (highest priority)

### Data Flow
```
Sensor → Read Loop → Validation → Queue → Batch Writer → InfluxDB
                                     ↓
                              Persistence Layer (on failures)
                                     ↓
                              Recovery on Restart
```

## Development

### Setup
```bash
## Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Run linting and type checking
ruff check .
mypy filamentbox
```

See [Tests Documentation](tests/README.md) for detailed testing information and [FilamentBox Core Module](filamentbox/README.md) for architecture details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the full test suite and linters
5. Submit a pull request

## CI/CD

GitHub Actions runs automated checks on every push:
- Python 3.11, 3.12, 3.13 on Ubuntu
- Linting with Ruff
- Type checking with Mypy
- Full test suite with pytest

Releases are automatically created when tags are pushed.

## Security Considerations
- The systemd unit runs as `root` to ensure GPIO access and proper file management. 
- Consider using a dedicated service user with appropriate group memberships (`gpio`, `i2c`) if your environment permits.
- Hardening flags enabled: `ProtectSystem=strict`, `PrivateTmp=true`, `ReadWritePaths=/opt/filamentcontrol`

## Support

For issues or feature requests, please open an issue on GitHub:
https://github.com/jdelgado-dtlabs/filamentenvmonitor/issues

When filing issues, include:
- Reproduction steps
- Relevant logs (use `--debug` mode)
- Environment details (OS, Python version)
- Configuration (sanitized)

## Version History

For detailed version history, release notes, and changelog, see [CHANGELOG.md](CHANGELOG.md).

**Current Version**: v1.6.0

**Recent Releases**:
- **v1.6.0** - Master installer, version control, smart updates
- **v1.5.0** - Web UI, Flask REST API, enhanced deployment
- **v1.1.0** - Environment control (heating/humidity), CLI interface
- **v1.0.0** - Stable release with multi-sensor support


