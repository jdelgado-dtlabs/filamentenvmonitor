# Changelog

All notable changes to the FilamentBox Environment Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Installation Workflow Clarification**
  - `install.sh` is now clearly the main entry point for all installations and updates
  - `setup.sh` focused on configuration management (can be run independently)
  - Updated documentation to reflect proper usage patterns
- **Configuration Management Consolidation**
  - `setup.sh` is now the single interface for all configuration management
  - Provides menu for full reconfiguration or modifying specific settings
  - `config_tool.py` available for read-only operations and programmatic access
  - Simplified user experience with one tool for configuration

## [2.0.0] - 2025-01-XX

### 🔐 Security Overhaul
**Breaking Changes**: Configuration system completely redesigned for security

- **Encrypted Configuration Database**
  - Migrated from plain-text YAML to SQLCipher encrypted database
  - 256-bit AES encryption for all configuration data
  - Automatic type inference and preservation
  - No more sensitive credentials in version control
  - Interactive configuration tool with letter-based menu navigation
  - Browse, search, view, edit configuration with `scripts/config_tool.py`
  - Automatic migration from legacy YAML and .env files

- **Auto-Generated Encryption Keys**
  - Cryptographically strong 64-character keys (384 bits entropy)
  - Generated from `/dev/urandom` with base64 encoding
  - Displayed during setup for user to save securely
  - Stored in `.config_key` file with 600 permissions (owner read/write only)
  - No more weak user-chosen passwords

- **HashiCorp Vault Integration**
  - Optional enterprise secret management support
  - Token and AppRole authentication methods
  - Automatic key retrieval with priority: env var > Vault > local file > default
  - Interactive Vault configuration during setup
  - `configure_vault.sh` helper script for Vault setup
  - Comprehensive documentation in `docs/VAULT_INTEGRATION.md`

### 📊 Multi-Database Support
- **7 Database Backend Options**
  - InfluxDB v1 (legacy)
  - InfluxDB v2 (modern with organizations and buckets)
  - InfluxDB v3 (latest with Apache Arrow)
  - Prometheus (push gateway)
  - TimescaleDB (PostgreSQL-based time-series)
  - VictoriaMetrics (high-performance metrics)
  - None (local-only mode)
- **Database Abstraction Layer**
  - Unified interface for all backends in `database_writer.py`
  - Easy switching between backends via configuration
  - Backend-specific optimizations and batching
  - Menu-selectable database type in config tool

### 🚀 Installation & Deployment Improvements
- **Auto-Generated Service Files**
  - Dynamic systemd service generation during setup
  - Automatic Vault environment variable embedding
  - No manual service file editing required
  - `generate_service_files()` in setup.sh
  - Documentation in `docs/SERVICE_AUTO_GENERATION.md`

- **Portable Installation Support**
  - Install in any directory: `/opt`, `/home`, `/srv`, etc.
  - Auto-detection of installation path ($INSTALL_ROOT)
  - Auto-detection of user/group (${SUDO_USER:-$USER})
  - Dynamic service file generation with correct paths
  - Works seamlessly across different deployment scenarios

- **Interactive Setup Enhancements**
  - Vault availability check during setup
  - Optional hvac library installation
  - Interactive Vault server and authentication configuration
  - Graceful fallback to local file storage
  - Clear status messages for Vault vs local storage

### ⚙️ Configuration Management
- **Interactive Configuration Tool** (`scripts/config_tool.py`)
  - Letter-based menu commands (B/N/S/V/Q/E/D/C)
  - Browse by section with hierarchical navigation
  - Search by key name with fuzzy matching
  - Menu selection for predefined values (database types, sensor types)
  - Special tag editor for key-value pairs
  - Sensitive value masking in display
  - Type-safe value editing with validation

- **Migration Tools**
  - `scripts/migrate_config.py` - Automated YAML + .env → encrypted DB migration
  - Preserves all settings during migration
  - Automatic backup of legacy configuration files
  - One-time migration with legacy file removal

### 📚 Documentation
- **New Security Documentation**
  - `docs/ENCRYPTION_KEY_SECURITY.md` - Key generation, storage, loading, recovery
  - `docs/VAULT_INTEGRATION.md` - Complete Vault setup guide with examples
  - `docs/SERVICE_AUTO_GENERATION.md` - Service file generation and portable installation

- **Updated Guides**
  - README.md updated for v2.0 features and encrypted configuration
  - Installation guide updated for new setup workflow
  - Security considerations expanded with encryption and Vault

### 🔧 Developer Experience
- **Helper Scripts**
  - `scripts/configure_vault.sh` - Interactive Vault configuration wizard
  - `scripts/load_config_key.sh` - Helper for loading encryption keys in services
  - Enhanced `install/setup.sh` with Vault support and service generation

### Breaking Changes
- **Configuration Migration Required**
  - `config.yaml` and `.env` no longer supported
  - Must run `install/setup.sh` or `scripts/migrate_config.py` to migrate
  - Automatic migration preserves all settings
  - Legacy files backed up before removal

- **Environment Variables**
  - `CONFIG_ENCRYPTION_KEY` replaces individual credential variables
  - Vault environment variables added (`VAULT_ADDR`, `VAULT_TOKEN`, etc.)
  - Legacy environment variables ignored after migration

- **Service Files**
  - Service files now auto-generated during setup
  - Manual service file modifications will be overwritten
  - Use setup script to regenerate services after changes

### Removed
- Legacy YAML configuration support
- Legacy .env file support
- Manual encryption key entry (replaced with auto-generation)
- Hardcoded service file paths (replaced with dynamic generation)

### Migration Path from v1.x
1. Run `sudo ./install/setup.sh` (recommended) OR
2. Run `python scripts/migrate_config.py` (manual migration)
3. Save the displayed encryption key securely
4. Legacy config files automatically backed up and removed
5. Service files regenerated automatically
6. No manual configuration required

## [1.6.1] - 2025-12-09

### Added
- **Interactive Installation Menu System**
  - Smart detection of existing services and installation status
  - Context-aware menu options based on current system state
  - Fresh installation option for new deployments
  - Service update option with code refresh and graceful restart
  - Configuration-only updates without service reinstall
  - Service log viewer from installer menu
  - Automatic detection of installation directory from existing services
  - Color-coded status indicators (running/stopped/not installed)
  - Menu-driven workflow for better user experience
- **Comprehensive Configuration Setup Script** (`install/setup.sh`)
  - **Complete coverage of all config.yaml options**:
    - InfluxDB (required): Host, port, database, credentials
    - Data Collection: Read intervals, batch sizes, measurement names, tags
    - Queue: In-memory queue sizing
    - Retry: Exponential backoff, alert thresholds, persistence triggers
    - Persistence: Database path and batch limits
    - Sensor (required): Type selection (BME280/DHT22), GPIO pins, calibration
    - Heating Control: Enable/disable, GPIO pin, temperature thresholds, check intervals
    - Humidity Control: Enable/disable, GPIO pin, humidity thresholds, check intervals
  - **Smart category-based configuration**:
    - Automatic detection of existing .env categories
    - Opt-in prompts for new optional categories
    - Skip categories you don't need yet
    - Re-run anytime to enable new features (heating, humidity control)
  - **Intelligent value preservation**:
    - Reads existing .env values and shows them as defaults
    - Only updates values that are explicitly changed
    - Automatic timestamped backups before modifications
  - **Enhanced user experience**:
    - Color-coded output and status indicators
    - Category descriptions explain each section
    - Configuration summary before saving
    - Secure password input (masked display)
    - Proper file permissions (chmod 600)
    - Security best practices warnings
  - **Integrated into main installer workflow** with optional prompts
- **Comprehensive Installation Documentation**
  - Created `install/INSTALL.md` - Complete installation and configuration guide (1413 lines)
  - Generated `install/INSTALL.pdf` - PDF version of installation guide (221KB)
  - Hardware requirements and sensor wiring diagrams
  - Detailed configuration guide with examples
  - Production deployment instructions (systemd, nginx, HTTPS)
  - Service management documentation
  - Comprehensive troubleshooting section
  - Uninstallation procedures

### Changed
- **Installation Directory Reorganization**
  - All installation files consolidated in `install/` directory
  - Moved `install.sh`, `install_service.sh`, `install_webui_service.sh` to `install/`
  - Moved `filamentbox.service`, `filamentbox-webui.service` to `install/`
  - Moved `nginx-filamentbox.conf` to `install/`
  - Updated all installer scripts to reference new file locations
  - Master installer now calls `./install/install_service.sh` and `./install/install_webui_service.sh`
  - **Master installer now prompts to run setup.sh** before service installation
  - Setup.sh can detect and preserve existing configurations during updates
- **Web UI Directory Reorganization**
  - Moved `webui_server.py` to `webui/webui_server.py`
  - Removed redundant `WEBUI_DEPLOYMENT.md` (content merged into `install/INSTALL.md`)
  - All web UI components now consolidated in `webui/` directory
  - Updated all references to point to comprehensive installation guide
- **Enhanced Configuration Setup Script**
  - Complete rewrite of `setup.sh` to support all `config.yaml` categories
  - Category-based configuration with optional sections
  - Intelligent detection of existing .env categories
  - Supports: InfluxDB, data collection, queue, retry, persistence, sensor, heating control, humidity control
  - Auto-prompts for new categories only, preserves existing configurations
  - Enables easy addition of heating/humidity control features after initial installation
- **Documentation Reorganization**
  - Simplified main README.md to reference specialized documentation
  - Removed installation details from main README (now in `install/INSTALL.md`)
  - Removed configuration details from main README (now in `install/INSTALL.md`)
  - Removed service management details from main README (now in `install/INSTALL.md`)
  - Added installation guide and setup script to documentation section
  - Main README now includes setup.sh in installation workflow
  - Main README now focuses on quick start and feature overview
  - Created specialized READMEs for different audiences:
    - `install/INSTALL.md` - Installation and configuration
    - `filamentbox/README.md` - Module architecture
    - `tests/README.md` - Testing documentation
    - `webui/README.md` - Web UI API

### Technical
- Installation guide uses ASCII characters for better PDF compatibility
- Temperature symbols changed from °C to C in documentation
- Resistor values changed from kΩ to kohm in documentation
- Unicode symbols removed for LaTeX compatibility
- Table formatting simplified for better rendering
- Setup script executable permission set automatically

## [1.6.0] - 2025-12-09

### Added
- **Master Installer** (`install.sh`)
  - Interactive directory selection (default `/opt/filamentcontrol`, current directory, or custom path)
  - Automatic directory creation if needed
  - Dynamic path configuration for all service files
  - Orchestrated installation of both main and web UI services
  - Comprehensive service verification with status checks
  - Automatic log viewing if any service fails to start
  - Virtual environment detection and setup guidance
  - Complete error handling with rollback capability
- **Version Control System**
  - Version headers in all service files
  - Automatic version comparison during updates
  - Smart update detection (only update if newer version available)
  - Graceful service restarts during updates
  - Option to skip update or force reinstall
  - Preserve service running state across updates
- **Installation Improvements**
  - Both installers now support version checking
  - Automatic detection of existing installations
  - Visual diff display when service files change
  - Intelligent service restart handling
  - OS-specific package management (apt/dnf/yum)
  - Nginx configuration with path auto-adjustment

### Changed
- Service files now use full Python interpreter paths
- Removed shebang from `run_filamentbox.py` (no longer needed)
- Removed unnecessary executable permissions
- Enhanced installer output with progress indicators
- Improved error messages and user guidance
- Updated both service installers with unified UX

### Fixed
- Code formatting in `filamentbox_cli.py` for CI compliance
- Service file path handling for custom installations
- Directory permission checks during installation

## [1.5.1] - 2025-12-09

### Fixed
- Code formatting in `filamentbox_cli.py` for CI compliance

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
