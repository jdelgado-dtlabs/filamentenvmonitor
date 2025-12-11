# Filament Storage Environmental Manager

<p align="center">
  <img src="images/filament.jpeg" alt="Filament Storage Environment" width="600" />
</p>

![CI](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/ci.yml/badge.svg)
![Release](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/release.yml/badge.svg)
[![Latest Release](https://img.shields.io/github/v/release/jdelgado-dtlabs/filamentenvmonitor?label=latest%20release)](https://github.com/jdelgado-dtlabs/filamentenvmonitor/releases/latest)

A Python 3.13 application for monitoring and controlling temperature and humidity in 3D printer filament storage environments. Supports multiple sensor types (BME280, DHT22) and multiple time-series databases with encrypted configuration, optional HashiCorp Vault integration, robust data collection, batching, active environment control, and both CLI and Web UI interfaces.

## Highlights (v2.0)
- **🔐 Encrypted Configuration**: SQLCipher-based encrypted database with 256-bit AES encryption
- **🔑 HashiCorp Vault Integration**: Optional enterprise-grade secret management for encryption keys
- **📊 Multi-Database Support**: InfluxDB (v1/v2/v3), Prometheus, TimescaleDB, VictoriaMetrics, or sensor-only mode
- **⚙️ Interactive Configuration Tool**: Menu-driven CLI for secure configuration management
- **🚀 Auto-Generated Service Files**: Systemd services automatically configured for your installation
- **📍 Portable Installation**: Install anywhere - dynamic path and user detection
- **🔄 Auto-Migration**: Seamless upgrade from v1.x YAML/env files to encrypted database
- **💾 Auto-Generated Encryption Keys**: Cryptographically secure 64-character keys
- **Web UI**: Modern, responsive browser-based interface with real-time monitoring and control
- Multi-sensor support: BME280 (I2C) and DHT22 (GPIO)
- Temperature and humidity control with GPIO relay support

## Features
- **🔐 Security & Configuration**:
  - Encrypted configuration database (SQLCipher with 256-bit AES)
  - Auto-generated cryptographically secure encryption keys
  - HashiCorp Vault integration for enterprise deployments
  - Interactive configuration tool with menu-based selection
  - Automatic migration from legacy YAML/.env files
  - No plain-text passwords or credentials
  
- **📊 Database Flexibility**:
  - **InfluxDB v1.x**: Traditional HTTP API with username/password
  - **InfluxDB v2.x**: Modern API with token/bucket/org authentication
  - **InfluxDB v3.x**: Cloud/serverless with database/token
  - **Prometheus**: Pushgateway integration with job/instance/grouping keys
  - **TimescaleDB**: PostgreSQL extension with hypertables
  - **VictoriaMetrics**: High-performance metrics database
  - **None**: Sensor-only mode without database storage
  
- **Multi-sensor support**: BME280 (I2C) and DHT22 (GPIO) with automatic detection
- **Temperature control**: Optional GPIO relay control for heating with configurable thresholds
- **Humidity control**: Optional GPIO relay control for exhaust fan with configurable thresholds
- **Web UI**: Modern, responsive web interface accessible from any browser
- **CLI interface**: Real-time monitoring and manual control of heater/fan with curses-based UI
- **Reliable data collection**: Configurable intervals with graceful error handling
- **Batched writes**: Optimized database writes with size and time-based flush triggers
- **Automatic recovery**: SQLite persistence of unsent batches across restarts
- **Smart retry logic**: Exponential backoff with jitter on write failures
- **Alert system**: Configurable failure threshold with optional persistence
- **Queue management**: Overflow handling that prioritizes fresh data
- **Production ready**: Auto-generated systemd services with Vault support
- **Portable installation**: Works in any directory with dynamic path detection
- **Code quality**: Full type hints, pre-commit hooks, automated CI/CD

## Documentation

- **[Encryption Key Security](docs/ENCRYPTION_KEY_SECURITY.md)** - Key storage, loading priority, and security best practices
- **[Vault Integration](docs/VAULT_INTEGRATION.md)** - HashiCorp Vault setup and configuration guide
- **[Service Auto-Generation](docs/SERVICE_AUTO_GENERATION.md)** - Systemd service file generation
- **[Installation Guide](install/INSTALL.md)** ([PDF](install/INSTALL.pdf)) - Complete installation and configuration guide
- **[FilamentBox Core Module](filamentbox/README.md)** - Detailed module architecture and component documentation
- **[Tests](tests/README.md)** - Complete testing documentation and guidelines
- **[Web UI](webui/README.md)** - Web interface API documentation
- **[CHANGELOG](CHANGELOG.md)** - Version history and release notes

## Quick Start

### Requirements
- Python 3.13+ (virtual environment recommended)
- One of: InfluxDB, Prometheus, TimescaleDB, VictoriaMetrics, or none (sensor-only)
- Raspberry Pi with BME280 (I2C) or DHT22 (GPIO) sensor

### Installation

```bash
# Clone the repository
git clone https://github.com/jdelgado-dtlabs/filamentenvmonitor.git
cd filamentenvmonitor

# Run the installer (handles everything: venv, dependencies, config, services)
sudo ./install/install.sh
```

The installer will:
1. Prompt for installation directory
2. Create Python virtual environment and install dependencies
3. Run configuration setup (encryption key, Vault, database, sensor)
4. Generate systemd service files
5. Install and start services

**To reconfigure an existing installation**:
```bash
cd /opt/filamentcontrol
sudo ./install/setup.sh
```

**For detailed installation instructions, see the [Installation Guide](install/INSTALL.md)**

## Configuration

Configuration is managed through an **encrypted SQLCipher database** with the `setup.sh` script providing interactive configuration management.

### Configuration Management

```bash
cd /opt/filamentcontrol
sudo ./install/setup.sh
```

**Options**:
- **Reconfigure everything** - Regenerate encryption keys, Vault, database, sensor settings
- **Modify specific settings** - Interactive menu for individual configuration changes

### Key Configuration Areas
- Database type and connection settings (7 database options)
- Encryption key and HashiCorp Vault integration
- Data collection intervals and batching
- Sensor type and GPIO pins
- Temperature and humidity control thresholds
- Retry and persistence behavior
- Custom tags for database measurements

### Encryption Key Storage

The encryption key can be stored in:
1. **HashiCorp Vault** (recommended for production)
2. **Local file** (`.config_key` with 600 permissions)
3. **Environment variable** (`FILAMENTBOX_CONFIG_KEY`)

**For complete configuration details, see [Encryption Key Security](docs/ENCRYPTION_KEY_SECURITY.md)**

## Running the Application

### Service Mode (Recommended)
```bash
# Start services
sudo systemctl start filamentbox.service
sudo systemctl start filamentbox-webui.service

# Check status
sudo systemctl status filamentbox.service

# View logs
sudo journalctl -u filamentbox.service -f
```

### Interactive Mode
```bash
source filamentcontrol/bin/activate
python -m filamentbox.main           # Normal run
python -m filamentbox.main --debug   # Enable verbose debug logging
```

### Configuration Management
```bash
# Modify configuration settings
sudo ./install/setup.sh
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
```bash
# Configure using setup script
sudo ./install/setup.sh

# Navigate to heating_control or humidity_control section
# Set: enabled = true, gpio_pin = 16, min_temp_c = 18.0, max_temp_c = 22.0
```

## Common Issues

Quick troubleshooting reference:

| Symptom | Resolution |
|--------|------------|
| Database not found | Configure database with `sudo ./install/setup.sh` |
| Sensor read errors | Verify `sensor.type` in encrypted config matches hardware |
| Service won't start | Check encryption key is available and config database exists |
| Relay cycling rapidly | Increase gap between min/max thresholds in config |
| Missing encryption key | Run setup again or check `.config_key` file permissions |

**For comprehensive troubleshooting, hardware setup, and debugging, see the [Installation Guide](install/INSTALL.md#troubleshooting)**

## Quick Reference Commands
```bash
# Run application
python -m filamentbox.main
python -m filamentbox.main --debug

# Configuration management
sudo ./install/setup.sh                      # Interactive config

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
- `sensor.py` - Multi-sensor abstraction (BME280/DHT22/DHT11), lazy initialization, error handling
- `database_writer.py` - Multi-backend support (InfluxDB v1/v2/v3, Prometheus, TimescaleDB, VictoriaMetrics)
- `persistence.py` - SQLite-based batch recovery, pruning, error resilience
- `config_db.py` - Encrypted SQLCipher configuration with HashiCorp Vault integration
- `logging_config.py` - Dual-stream logging (stdout/stderr split)

### Configuration Architecture
- **Encrypted Storage**: SQLCipher database with 256-bit AES encryption
- **Key Management**: Auto-generated 64-character keys stored securely in `.config_key` or HashiCorp Vault
- **Interactive Tool**: Letter-based menu system for browsing and editing all settings
- **Type Safety**: Automatic type inference and preservation
- **Migration**: Automatic import from legacy YAML/environment variable configs

### Data Flow
```
Sensor → Read Loop → Validation → Queue → Batch Writer → Database Backend
                                     ↓                    (InfluxDB/Prometheus/
                              Persistence Layer           TimescaleDB/etc)
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
- **Encrypted Configuration**: All sensitive data stored in SQLCipher database with 256-bit AES encryption
- **Key Management**: Auto-generated cryptographically strong keys (384 bits entropy)
- **Vault Integration**: Optional HashiCorp Vault support for enterprise deployments
- **Service Isolation**: Systemd services run with hardening flags (`ProtectSystem=strict`, `PrivateTmp=true`)
- **File Permissions**: Encryption key file restricted to 600 (owner read/write only)
- **GPIO Access**: Service runs as `root` for GPIO/I2C access; consider dedicated service user with `gpio`, `i2c` groups
- **Migration Security**: Legacy YAML/environment variable configs automatically imported and removed

See [Encryption Key Security](docs/ENCRYPTION_KEY_SECURITY.md) and [Vault Integration](docs/VAULT_INTEGRATION.md) for detailed security documentation.

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

**Current Version**: v2.0

**Recent Releases**:
- **v2.0** - Encrypted configuration, HashiCorp Vault integration, multi-database support, auto-generated service files
- **v1.6.0** - Master installer, version control, smart updates
- **v1.5.0** - Web UI, Flask REST API, enhanced deployment
- **v1.1.0** - Environment control (heating/humidity), CLI interface
- **v1.0.0** - Stable release with multi-sensor support


