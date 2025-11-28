# 3D Printer Filament Storage Environment Monitor

A Python 3.13 application for collecting BME280 environmental data (temperature/humidity) and writing measurements to InfluxDB with durable batching, retry backoff, and recovery of unsent batches.

## Features
- Periodic BME280 sensor reads (configurable interval)
- Batched writes to InfluxDB (size or time flush triggers)
- Automatic database creation on startup (best-effort)
- Exponential backoff with jitter on write failures
- Alert threshold with optional persistence of failed batches
- SQLite persistence of unsent batches across restarts
- Startup recovery flushing persisted batches
- Queue overflow handling (drops oldest to keep fresh data)
- Structured debug output (batch preview before write)
- Configurable measurement name and tags (YAML or environment)
- Clean separation of concerns (config, sensor, writer, persistence, logging)

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
- BME280 sensor connected over I2C

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
- `sensor.sea_level_pressure`

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

## Extensibility Ideas
- Add metrics export (Prometheus) for internal health.
- Implement structured logging (JSON format) for ingestion pipelines.
- Add additional sensors (pressure, VOC) with tagging.

## License
Internal / Proprietary (add license terms if needed).

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
```

## Development
- Dev dependencies live in `requirements-dev.txt` (includes `-r requirements.txt`).
- Hooks: `pre-commit install` to enable automatic lint and type checks on commit.
- Configuration lives in `pyproject.toml` for ruff/mypy.
- If Git shows a "dubious ownership" error on this path, mark it safe:
  `git config --global --add safe.directory /opt/filamentcontrol`.

## CI
GitHub Actions workflow (`.github/workflows/ci.yml`) runs ruff, mypy, and pytest on pushes/PRs
across Python 3.11, 3.12, and 3.13 on Ubuntu (Linux), matching Raspberry Pi targets.

<!-- Replace OWNER/REPO with your GitHub org/repo -->
![CI](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/ci.yml/badge.svg)
![Release](https://github.com/jdelgado-dtlabs/filamentenvmonitor/actions/workflows/release.yml/badge.svg)
[
![Latest Release](https://img.shields.io/github/v/release/jdelgado-dtlabs/filamentenvmonitor?label=latest%20release)
](https://github.com/jdelgado-dtlabs/filamentenvmonitor/releases/latest)

## Releases
- Tag a commit using `vX.Y.Z` (e.g., `v0.1.0`).
- The release workflow (`.github/workflows/release.yml`) runs lint, types, and tests, then
  creates a GitHub Release with autogenerated notes and attaches a source zip.
 - A Release Drafter workflow maintains a draft release with categorized notes; labels influence
   sections in the notes. See `.github/release-drafter.yml` for categories and label mapping.

## Support
For enhancements or issues, document reproduction steps, debug output, and configuration diffs.
