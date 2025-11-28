# 3D Printer Filament Storage Environment Monitor

![CI](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/ci.yml/badge.svg)
![Release](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/release.yml/badge.svg)
[![Latest Release](https://img.shields.io/github/v/release/jdelgado-dtlabs/filamentenvmonitor?label=latest%20release)](https://github.com/jdelgado-dtlabs/filamentenvmonitor/releases/latest)

A Python 3.13 application for monitoring temperature and humidity in 3D printer filament storage environments. Supports multiple sensor types (BME280, DHT22) with robust data collection, batching, and InfluxDB integration.

## Features
- **Multi-sensor support**: BME280 (I2C) and DHT22 (GPIO) with automatic detection
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

## Directory Layout
```
filamentcontrol/
  filamentbox/
    __init__.py
    main.py
    influx_writer.py
    sensor.py
    persistence.py
    config.py
    logging_config.py
config.yaml
.env (ignored by VCS)
unsent_batches.db (created at runtime if persistence used)
```

## Requirements
- Python 3.13 (virtual environment recommended)
- InfluxDB (tested with 1.x HTTP API)
- Supported sensors:
  - BME280 (I2C interface)
  - DHT22 (GPIO pin, default GPIO4)

## Installation & Setup
```bash
# Create / activate virtual environment (already present in repository example)
python -m venv filamentcontrol
source filamentcontrol/bin/activate

# Install runtime dependencies
pip install -r requirements.txt

# (Optional) Install development tooling (lint, type-check, hooks)
pip install -r requirements-dev.txt
pre-commit install
```

## Configuration
Primary configuration lives in `config.yaml`. Environment variables override sensitive or dynamic values.

`config.yaml` (key sections):
- `influxdb.host`, `influxdb.port`, `influxdb.username`, `influxdb.password`, `influxdb.database`
- `data_collection.read_interval`, `data_collection.batch_size`, `data_collection.flush_interval`, `data_collection.measurement`, optional `data_collection.tags`
- `queue.max_size`
- `retry.backoff_base`, `retry.backoff_max`, `retry.alert_threshold`, `retry.persist_on_alert`
- `persistence.db_path`, `persistence.max_batches`
- `sensor.type` ("bme280" or "dht22"), `sensor.sea_level_pressure` (BME280 only), `sensor.gpio_pin` (DHT22 only)

Environment overrides (via `.env` or shell):
```
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=secret
INFLUXDB_HOST=192.168.1.10
INFLUXDB_PORT=8086
INFLUXDB_DATABASE=influx
DATA_COLLECTION_MEASUREMENT=environment
DATA_COLLECTION_TAGS={"location": "filamentbox", "device": "pi-zero"}
```
Tags must be valid JSON.

## Running the Application

### Interactive Mode
```bash
source filamentcontrol/bin/activate
python -m filamentbox.main           # Normal run
python -m filamentbox.main --debug   # Enable verbose debug logging
```

### As a systemd Service

#### Quick Install
```bash
# Run the installation script
sudo ./install_service.sh

# Start the service
sudo systemctl start filamentbox.service

# View logs
sudo journalctl -u filamentbox.service -f
```

#### Manual Install
```bash
# Copy service file to systemd directory
sudo cp filamentbox.service /etc/systemd/system/

# Edit the service file if needed (adjust User, Group, WorkingDirectory)
sudo nano /etc/systemd/system/filamentbox.service

# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable filamentbox.service
sudo systemctl start filamentbox.service

# Check service status
sudo systemctl status filamentbox.service

# View logs
sudo journalctl -u filamentbox.service -f
```

### Debug Mode
Shows per-batch preview:
```
DEBUG - Batch ready for write (N points):
DEBUG -   Point 1: {"measurement": "environment", "fields": {...}, "tags": {...}}
```

### Graceful Shutdown
Press Ctrl+C; application flushes queue, persists unsent batches (if threshold reached), and exits.

## Data Point Structure
Each measurement dict enqueued:
```json
{
  "measurement": "environment",
  "fields": {
    "temperature_c": 22.53,
    "temperature_f": 72.55,
    "humidity": 28.7
  },
  "tags": {"location": "filamentbox"}
}
```
Fields with `None` values are omitted. Tags optional.

## Persistence & Recovery
- Failed write batches (after alert threshold) can be persisted to SQLite (`unsent_batches.db`).
- On startup, `load_and_flush_persisted_batches` attempts immediate write of oldest-first batches.
- Malformed JSON or HTTP 400 (bad request) responses cause permanent drop of the batch.

## Retry & Backoff
On write failure:
- Failure count increments.
- Exponential backoff: `backoff = min(base * 2**(n-1), max)` plus 0–10% jitter.
- After `alert_threshold`, alert handler (if registered) invoked and batch may persist.

## Queue Behavior
Write queue max size configurable (`queue.max_size`). When full:
- Oldest item dropped to make room for newest (freshness bias).

## Available Python Entry Points
- `filamentbox.main` — Main application with threads and recovery.
- `filamentbox.sensor` — Sensor helpers (`read_bme280_data`, `convert_c_to_f`).
- `filamentbox.influx_writer` — Writer thread utilities (`enqueue_data_point`, `register_alert_handler`, `wait_for_queue_empty`).
- `filamentbox.persistence` — Batch persistence (`persist_batch`, `load_and_flush_persisted_batches`).
- `filamentbox.config` — Configuration (`get`, `load_config`).
- `filamentbox.logging_config` — Logging setup (`configure_logging`).

## Programmatic Usage Example
```python
from filamentbox.config import get
from filamentbox.influx_writer import enqueue_data_point

point = {
    "measurement": get("data_collection.measurement") or "environment",
    "fields": {"temperature_c": 21.3, "humidity": 40.2},
    "tags": get("data_collection.tags")
}
enqueue_data_point(point)
```

## Monitoring & Troubleshooting
- Enable `--debug` for detailed batch content before writes.
- Look for ERROR logs (stderr) indicating write failures or sensor exceptions.
- CRITICAL logs indicate unexpected thread termination.

## Common Issues
| Symptom | Cause | Resolution |
|--------|-------|-----------|
| Database not found | Missing `influxdb.database` | Add to `config.yaml` or set `INFLUXDB_DATABASE` |
| Tags missing | Incorrect JSON in env variable | Ensure `DATA_COLLECTION_TAGS` is valid JSON |
| 400 errors | Invalid field types or line protocol | Ensure numeric fields only; no empty strings |
| Queue drops data | Queue size too small | Increase `queue.max_size` |
| Sensor read errors | Wrong sensor type configured | Verify `sensor.type` matches your hardware (bme280/dht22) |
| DHT22 timeouts | GPIO pin misconfiguration | Check `sensor.gpio_pin` matches wiring |
| Service won't start | Config file missing | Ensure `config.yaml` exists in `/opt/filamentcontrol` |

## Quick Reference Commands
```bash
# Run application
python -m filamentbox.main
python -m filamentbox.main --debug

# Or use the convenience launcher script
python run_filamentbox.py
python run_filamentbox.py --debug

# Set environment overrides (example)
export INFLUXDB_HOST=192.168.1.25
export DATA_COLLECTION_TAGS='{"location": "rack-1"}'

# Inspect persisted DB (SQLite)
sqlite3 unsent_batches.db '.tables'
sqlite3 unsent_batches.db 'SELECT COUNT(*) FROM unsent_batches;'

# Manual point enqueue (interactive Python)
python - <<'PY'
from filamentbox.influx_writer import enqueue_data_point
from filamentbox.config import get
enqueue_data_point({
  'measurement': get('data_collection.measurement'),
  'fields': {'temperature_c': 23.4, 'humidity': 45.1},
  'tags': get('data_collection.tags')
})
PY

# Development: run linters, types, and tests
ruff check .
ruff format --check .
mypy filamentbox
pre-commit run --all-files
pytest -q

# Service management
sudo systemctl status filamentbox.service
sudo systemctl restart filamentbox.service
sudo journalctl -u filamentbox.service -f --since "10 minutes ago"
```

## Project Structure & Architecture

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
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Workflow
- Dev dependencies live in `requirements-dev.txt` (includes `-r requirements.txt`)
- Hooks: `pre-commit install` enables automatic lint and type checks on commit
- Configuration lives in `pyproject.toml` for ruff/mypy
- If Git shows "dubious ownership" error: `git config --global --add safe.directory /opt/filamentcontrol`

### Running Tests
```bash
# Run all tests
pytest

# Quick test run
pytest -q

# With coverage
pytest --cov=filamentbox
```

## CI/CD

### Continuous Integration
GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push/PR:
- Linting (Ruff)
- Type checking (Mypy)
- Unit tests (pytest)
- Python versions: 3.11, 3.12, 3.13
- Platform: Ubuntu (matches Raspberry Pi target)

### Releases
1. Tag a commit: `git tag v0.X.Y && git push --tags`
2. Release workflow (`.github/workflows/release.yml`) automatically:
   - Runs full CI suite
   - Creates GitHub Release with autogenerated notes
   - Attaches source archive
3. Release Drafter maintains draft releases with categorized notes (see `.github/release-drafter.yml`)

## Version History

### v1.0.0 - Stable Major Release
- Public repository with working badges (CI, Release, Latest).
- Robust, production-ready monitoring with multi-sensor support (BME280, DHT22).
- Systemd service integration with automated installer.
- Reliable batching, retry with exponential backoff + jitter, and SQLite persistence.
- Comprehensive configuration via YAML with environment overrides; lazy config loading.
- Full code quality pipeline: Ruff lint/format, Mypy typing, pytest tests, pre-commit hooks.
- CI/CD on Python 3.11–3.13; automated GitHub Releases with source archives.

### v0.2.0 - Service Integration & Multi-Sensor Support
- Added systemd service file and automated installer
- DHT22 sensor support alongside BME280
- Removed local InfluxDB dependency (supports remote instances)
- Portable shebang for cross-environment compatibility
- CI enhancements for hardware dependency handling

### v0.1.0 - Initial Release
- BME280 sensor data collection
- InfluxDB batch writing with retry/backoff
- Configuration via YAML and environment
- SQLite-based persistence and recovery
- Comprehensive testing and CI/CD

## Support & Contributing
For enhancements or issues, document reproduction steps, debug output, and configuration diffs.
See `.github/workflows/` for CI configuration and `.pre-commit-config.yaml` for code quality standards.
