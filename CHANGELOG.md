# Changelog

All notable changes to the Filament Storage Environmental Manager will be documented in this file.

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

### Fixed
- **SSE Database Status Bug** - Fixed database type showing "none" in SSE stream
  - Corrected key transformation from `database_type` to `type` in `/api/stream` endpoint
  - Added `storing_data` calculation to match REST API behavior
  - Database card now displays correct type (e.g., "InfluxDB" instead of "None")

### Removed
- **Deprecated Code Cleanup**
  - Moved `influx_writer.py` to archive (superseded by `database_writer.py`)
  - Archived deprecated test files (`test_data_point_tags.py`, `simulate_influx_failure.py`)
  - Archived legacy HTML UI files (`index.html.legacy`)
  - Removed unused React hook (`useTheme.js`)
  - Removed console.log statements from production code
  - Updated `filamentbox/__init__.py` to import from `database_writer` instead of deprecated `influx_writer`

## [2.0.0-rc] - 2025-12-10

*Note: Final v2.0.0 stable release planned for January 2026*

### 🎉 Major Release - Complete Architectural Overhaul
Version 2.0 represents a comprehensive redesign focused on security, scalability, modern web experience, and real-time capabilities. This release includes **10 major features**, **7 database backends**, and complete **React-based web UI** with **~125 commits** since v1.x.

---

### 🌐 Modern Web UI & Real-Time Updates

- **React-Based Progressive Web App (PWA)**
  - Complete rewrite from vanilla HTML to React + Vite
  - Component-based architecture with modern UX patterns
  - Progressive Web App with offline support via service workers
  - Install as native app on mobile and desktop devices
  - Responsive design for all screen sizes
  - Hot module replacement for development
  - Production build optimization with code splitting
  - ~3000 lines of modern React code in `webui/webui-react/`

- **Server-Sent Events (SSE) for Real-Time Updates**
  - NEW endpoint: `GET /api/stream` - SSE stream with combined system status
  - Real-time sensor readings (no polling needed)
  - Live control state synchronization
  - Database health monitoring
  - Thread status updates
  - Notification delivery via SSE
  - EventSource API client implementation
  - Automatic reconnection on connection loss
  - Updates pushed every second from server

- **Comprehensive Notification System**
  - **Backend**: `filamentbox/notification_publisher.py` - Thread-safe notification publisher
    - Publish from any thread: `notify_success()`, `notify_error()`, `notify_warning()`, `notify_info()`
    - 50-message circular buffer for recent notifications
    - Callback system for web delivery
    - Thread-safe with proper locking
  - **API Endpoints**:
    - `GET /api/notifications` - Retrieve recent notifications
    - `DELETE /api/notifications` - Clear notification history
  - **Browser Notifications**: OS-level desktop/mobile toaster notifications
    - Permission request flow with user consent
    - LocalStorage persistence for preferences
    - Automatic fallback if not supported
    - Smart auto-request logic (one-time prompt)
  - **In-App Notification Panel**:
    - Sliding panel with notification history
    - Color-coded by type (success/error/warning/info)
    - Dismissible messages with timestamps
    - Real-time updates via SSE
  - **Use Cases**: Thread restarts, config updates, errors, control changes

- **Dark Mode Theme Support**
  - Three theme modes: Light, Dark, Auto
  - Auto mode follows OS `prefers-color-scheme`
  - LocalStorage persistence across sessions
  - Dynamic switching without page reload
  - CSS custom properties for theming
  - Smooth transitions between themes
  - Respects system theme changes in real-time
  - Implementation: `webui/webui-react/src/utils/theme.js`

---

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

---

### 🏗️ Architecture & Infrastructure Improvements

- **Master Thread Orchestrator** (`filamentbox/orchestrator.py`)
  - Centralized thread lifecycle management for all worker threads
  - Eliminates file-based IPC (replaced with direct queue communication)
  - Automatic thread registration and health monitoring
  - Graceful shutdown coordination across all threads
  - Direct data distribution to control threads
  - Manages: sensor reader, database writer, heating control, humidity control, web UI
  - Simplified architecture with clean separation of concerns
  - Better error recovery and coordinated restarts

- **Hot-Reload Configuration Changes** (`filamentbox/config_watcher.py`)
  - Background watcher monitors config database for changes
  - Automatic reload when configuration is updated via config tool
  - Callback system for configuration-dependent components
  - Key-specific and global change notifications
  - Thread-safe callback execution
  - Checks database mtime every 2 seconds
  - No service restart needed for most configuration changes
  - Supported: database settings, thresholds, intervals, tags, and more
  - Register callbacks: `register_callback('key', on_change_func)`

- **Thread Restart Controls in Web UI**
  - Shared state mechanism for cross-process communication
  - REST API endpoints for thread control:
    - `GET /api/threads` - Get status of all threads
    - `POST /api/threads/{name}/restart` - Restart specific thread
    - `POST /api/threads/{name}/start` - Start stopped thread
    - `POST /api/threads/{name}/stop` - Stop running thread
  - React components for thread management UI
  - Remote troubleshooting without SSH access
  - Graceful thread restarts without full service restart
  - Real-time status updates via SSE
  - Supported threads: sensor_reader, database_writer, heating_control, humidity_control, webui
  - Notifications on thread state changes

---

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

- **Universal Tag Management Support**
  - Tag support across all database backends
  - Interactive tag editor in configuration tool (`scripts/config_tool.py`)
  - JSON/dict storage in encrypted config database
  - Database-specific tag handling:
    - **InfluxDB**: Native tag support in line protocol
    - **Prometheus**: Labels on all metrics
    - **TimescaleDB**: JSONB column for tags
    - **VictoriaMetrics**: Tags in query parameters
  - Use cases: multi-sensor deployments, location tracking, device identification
  - Configuration: `database.influxdb.tags = {"location": "filament_room", "sensor_id": "bme280_01"}`
  - Documentation: `docs/configuration_tags.md`

---

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

---

### 📚 Documentation
- **New Security Documentation**
  - `docs/ENCRYPTION_KEY_SECURITY.md` - Key generation, storage, loading, recovery
  - `docs/VAULT_INTEGRATION.md` - Complete Vault setup guide with examples
  - `docs/SERVICE_AUTO_GENERATION.md` - Service file generation and portable installation
  - `docs/configuration_tags.md` - Tag management guide for all database backends
  - `docs/V2.0_FEATURES_SUMMARY.md` - Comprehensive v2.0 features overview

- **Updated Guides**
  - README.md updated for v2.0 features and encrypted configuration
  - Installation guide updated for new setup workflow
  - Security considerations expanded with encryption and Vault
  - Web UI documentation for React application

- **React Web UI Documentation**
  - `webui/webui-react/README_REACT.md` - Development, build, and deployment guide
  - Component architecture documentation
  - PWA features and offline support
  - API integration guide

---

### 🔧 Developer Experience
- **Helper Scripts**
  - `scripts/configure_vault.sh` - Interactive Vault configuration wizard
  - `scripts/load_config_key.sh` - Helper for loading encryption keys in services
  - Enhanced `install/setup.sh` with Vault support and service generation

- **Code Quality & Testing**
  - Expanded test coverage for all new features
  - Type hints throughout codebase
  - Pre-commit hooks for code quality
  - ~125 commits with comprehensive testing

- **Performance Optimizations**
  - In-memory config cache with instant lookups (~10x faster)
  - Backend-specific database batching strategies
  - Reduced memory footprint in database writer
  - Direct queue communication (eliminated file I/O)
  - React code splitting for smaller bundles
  - Service worker caching for offline support

---

### ⚠️ Breaking Changes

**Configuration Migration Required** - All users must migrate

- **Configuration Files**
  - `config.yaml` **NO LONGER SUPPORTED** - removed entirely
  - `.env` file **NO LONGER SUPPORTED** - removed entirely
  - All configuration now in encrypted SQLCipher database (`config.db`)
  - **Migration**: Run `sudo ./install/setup.sh` or `python scripts/migrate_config.py`
  - **Data Preservation**: All settings automatically migrated
  - **Backup**: Legacy files backed up to timestamped folder before removal

- **Environment Variables**
  - Individual credential variables **NO LONGER USED**
  - `CONFIG_ENCRYPTION_KEY` replaces individual credential variables
  - New: `FILAMENTBOX_CONFIG_KEY` - Encryption key (if not using Vault or local file)
  - Vault environment variables added: `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_ROLE_ID`, `VAULT_SECRET_ID`
  - Legacy environment variables ignored after migration

- **Service Files**
  - Service files now **AUTO-GENERATED** during setup
  - Manual service file modifications **WILL BE OVERWRITTEN**
  - Use setup script to regenerate services after changes
  - Old service files automatically backed up

- **Python API Changes** (for developers using internal APIs)
  - Configuration access method changed:
    ```python
    # Old (v1.x)
    import yaml
    config = yaml.safe_load(open('config.yaml'))
    value = config['section']['key']
    
    # New (v2.0)
    from filamentbox.config import get
    value = get('section.key')
    ```
  - New hot-reload callback system:
    ```python
    from filamentbox.config_watcher import register_callback
    register_callback('database.type', on_change_func)
    ```

---

### 🔄 Migration Path from v1.x

**Recommended Migration Steps**:
1. Backup current installation:
   ```bash
   cp config.yaml config.yaml.backup
   cp .env .env.backup
   ```

2. Update code and run setup:
   ```bash
   cd /opt/filamentcontrol
   git pull origin v2.0-rc
   sudo ./install/setup.sh
   ```

3. **CRITICAL**: Save the encryption key displayed during setup
   - Key will be displayed once
   - Store securely (password manager, Vault, secure notes)
   - Without this key, config database cannot be decrypted

4. Verify migration:
   ```bash
   python scripts/config_tool.py  # Browse configuration
   sudo systemctl status filamentbox.service  # Check service
   firefox http://localhost:5000  # Test web UI
   ```

5. Test all functionality:
   - Sensor readings working
   - Database writes successful
   - Web UI accessible and updating
   - Controls functioning (heater/fan)
   - Notifications appearing
   - Thread restarts working

**Automatic Migration Features**:
- All `config.yaml` settings preserved
- All `.env` values preserved
- Timestamped backup created automatically
- Legacy files removed after successful migration
- Service files regenerated with correct paths
- No manual configuration editing required

**For Vault Users** (Optional):
1. Set up Vault server
2. Store encryption key in Vault at configured path
3. Configure Vault during setup or via `scripts/configure_vault.sh`
4. Test key retrieval
5. Remove local `.config_key` file if desired

**Rollback Procedure** (if needed):
1. Restore from backup folder: `config_backup_YYYYMMDD_HHMMSS/`
2. Checkout v1.x: `git checkout tags/v1.6.1`
3. Restart services

---

### 🗑️ Removed
- Legacy YAML configuration support (`config.yaml` - replaced with encrypted database)
- Legacy .env file support (replaced with encrypted database)
- Manual encryption key entry (replaced with auto-generation)
- Hardcoded service file paths (replaced with dynamic generation)
- File-based inter-process communication (replaced with direct queue communication)
- Legacy vanilla HTML web UI (replaced with React PWA) - legacy files kept for reference

---

### 📊 Statistics & Metrics

**Development Activity (v1.x → v2.0)**:
- **~125 commits** since December 2024
- **10 major features** implemented
- **7 database adapters** added
- **~3000 lines** of React code
- **8 new modules**: orchestrator, config_watcher, notification_publisher, databases/*, etc.
- **5 new documentation guides**
- **Expanded test coverage** for all new features

**Lines of Code**:
- React Web UI: ~3000 lines (TypeScript/JavaScript)
- Database Adapters: ~1500 lines (7 backends)
- Orchestrator & Thread Management: ~800 lines
- Configuration System: ~1200 lines (config_db, config_tool, migration)
- Notification System: ~400 lines
- Total New Code: ~7000+ lines

---

### 🎯 What's Next - Planned for v2.1

- MQTT integration for remote monitoring
- Email/SMS alerting via notification system
- Authentication for web UI (OAuth2, basic auth)
- Historical data visualization charts in React UI
- Mobile app (React Native using same backend)
- Multi-sensor aggregation (multiple sensors in one instance)
- Grafana dashboard templates
- Kubernetes deployment manifests
- Additional sensor support (SHT31, AM2302)

---

### 🐛 Known Issues

- React dev server (Vite) requires manual start for development
- Some config changes still require service restart (will be expanded in v2.1)
- Legacy HTML web UI files still present (will be removed in v2.1)
- Dark mode theme preference not synced across devices (localStorage only)

---

### 🙏 Acknowledgments

v2.0 represents months of development with focus on:
- **Security**: Encrypted configuration, Vault integration
- **Scalability**: Multi-database support, abstraction layer
- **User Experience**: Modern React UI, real-time updates, notifications
- **Developer Experience**: Hot-reload, better architecture, comprehensive docs

Thank you to all contributors and users providing feedback!

---

### 📦 Upgrade Instructions Summary

**For Most Users**:
```bash
cd /opt/filamentcontrol
git pull origin v2.0-rc
sudo ./install/setup.sh
# Save the encryption key displayed!
sudo systemctl restart filamentbox.service
sudo systemctl restart filamentbox-webui.service
```

**For Docker Users**:
```bash
# Update image
docker pull your-registry/filamentbox:v2.0-rc

# Run migration
docker run -it -v /path/to/config:/config filamentbox:v2.0-rc python scripts/migrate_config.py

# Set encryption key environment variable
docker run -e FILAMENTBOX_CONFIG_KEY="your-key" ...
```

**For Kubernetes Users**:
```bash
# Create secret with encryption key
kubectl create secret generic filamentbox-config-key \
  --from-literal=key="your-generated-key"

# Update deployment to use secret
# See docs/VAULT_INTEGRATION.md for Vault setup
```

---

## [2.0.0-alpha] - 2024-12-XX

### Added (Alpha Release)

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
