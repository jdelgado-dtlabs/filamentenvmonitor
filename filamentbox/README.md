# FilamentBox Core Module

The core Python module for 3D printer filament storage environment monitoring with multi-database support, multi-sensor hardware, and active environment control.

## Architecture

The application follows a multi-threaded architecture with separate threads for:
- Data collection from sensors
- Database batch writing (7 backend options)
- Temperature control (heating)
- Humidity control (exhaust fan)

All threads share state through a thread-safe state management system.

## Module Structure

```
filamentbox/
├── __init__.py              # Package initialization
├── main.py                  # Application entry point and orchestration
├── config_db.py             # Encrypted SQLCipher configuration with Vault integration
├── sensor.py                # Multi-sensor support (BME280, DHT22, DHT11)
├── database_writer.py       # Multi-backend database writer (7 backends)
├── persistence.py           # SQLite persistence for failed batches
├── logging_config.py        # Dual-stream logging configuration
├── heating_control.py       # Temperature-based heating control
├── humidity_control.py      # Humidity-based fan control
└── shared_state.py          # Thread-safe state management
```

## Core Components

### main.py

**Purpose**: Application orchestrator and data collection loop

**Key Functions**:
- `data_collection_cycle()`: Main sensor reading loop with batching
- `main()`: Initializes all threads and manages application lifecycle

**Features**:
- Configurable read intervals
- Batch size and flush interval management
- Numeric field validation for database backends
- Queue overflow handling (drop oldest)
- Graceful shutdown with queue flush
- Debug logging with batch preview

**Thread Management**:
```python
# Global stop event for coordinated shutdown
_stop_event = threading.Event()

# Threads started:
- Data collection thread
- Database writer thread
- Heating control thread (if enabled)
- Humidity control thread (if enabled)
```

### config_db.py

**Purpose**: Encrypted configuration management with enterprise integration

**Features**:
- SQLCipher encrypted database (256-bit AES encryption)
- Auto-generated cryptographically strong encryption keys
- HashiCorp Vault integration (optional)
- Type-safe value storage with automatic inference
- Priority loading: env var > Vault > local file > default

**Key Class**:
```python
class ConfigDB:
    def get(key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation."""
    def set(key: str, value: Any) -> None:
        """Set configuration value with type preservation."""
    def delete(key: str) -> None:
        """Delete configuration key."""
    def list_all() -> dict:
        """List all configuration."""
```

**Configuration Sections**:
- `database`: Backend type and connection settings (7 backends)
- `data_collection`: Intervals, batch size, measurement name, tags
- `queue`: Maximum queue size
- `retry`: Backoff parameters, alert threshold
- `persistence`: SQLite database path, max batches
- `sensor`: Type (BME280/DHT22/DHT11), GPIO pin, settings
- `heating_control`: Enable, GPIO pin, temperature thresholds
- `humidity_control`: Enable, GPIO pin, humidity thresholds

### database_writer.py

**Purpose**: Multi-backend database abstraction

**Supported Backends**:
- **InfluxDB v1**: Legacy HTTP API
- **InfluxDB v2**: Modern with organizations and buckets
- **InfluxDB v3**: Latest with Apache Arrow
- **Prometheus**: Push gateway integration
- **TimescaleDB**: PostgreSQL-based time-series
- **VictoriaMetrics**: High-performance metrics
- **None**: Local-only mode (no remote database)

**Key Features**:
- Unified interface across all backends
- Backend-specific optimizations
- Automatic retry and batching
- Connection pooling where supported

### sensor.py

**Purpose**: Multi-sensor abstraction layer

**Supported Sensors**:
- **BME280**: I2C sensor (temperature, humidity, pressure)
- **DHT22**: GPIO sensor (temperature, humidity)

**Key Features**:
- Lazy initialization via `_init_sensor()`
- Automatic sensor type detection from config
- Error handling for sensor failures
- Temperature conversion (Celsius to Fahrenheit)

**Main Function**:
```python
def read_sensor_data() -> Dict[str, float]:
    """Read temperature and humidity from configured sensor.
    
    Returns:
        Dict with keys: temperature_c, temperature_f, humidity, pressure (BME280 only)
    """
```

**Configuration**:
```yaml
sensor:
  type: "bme280"  # or "dht22"
  gpio_pin: 4     # For DHT22 only
  sea_level_pressure: 1013.25  # For BME280 altitude calculation
```

### influx_writer.py

**Purpose**: Batched InfluxDB writer with retry logic

**Key Features**:
- Batch writing to reduce network overhead
- Exponential backoff with jitter on failures
- Alert threshold for persistent failures
- SQLite persistence when alert threshold reached
- Configurable retry parameters

**Main Function**:
```python
def influx_writer_thread(
    data_queue: queue.Queue,
    stop_event: threading.Event,
    alert_handler: Optional[Callable] = None
) -> None:
    """Worker thread that writes batches to InfluxDB."""
```

**Retry Logic**:
```python
backoff = min(backoff_base * (2 ** failure_count), backoff_max)
jitter = random.uniform(0, backoff * 0.1)
time.sleep(backoff + jitter)
```

**Alert System**:
- Configurable failure threshold
- Optional custom alert handler
- Automatic persistence to SQLite on alert

### persistence.py

**Purpose**: SQLite-based persistence for failed batches

**Key Features**:
- JSON serialization of batch data
- FIFO queue with max batch limit
- Atomic load-and-flush operations
- Thread-safe database operations

**Main Functions**:
```python
def save_batch(batch: List[Dict[str, Any]], db_path: str) -> None:
    """Save a batch to SQLite database."""

def load_and_flush(db_path: str) -> List[List[Dict[str, Any]]]:
    """Load all batches and delete them atomically."""
```

**Database Schema**:
```sql
CREATE TABLE IF NOT EXISTS unsent_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_json TEXT NOT NULL,
    timestamp REAL NOT NULL
)
```

### heating_control.py

**Purpose**: Temperature-based heating control with GPIO relay

**Key Features**:
- Hysteresis control to prevent rapid cycling
- Configurable temperature thresholds
- Manual override support
- Thread-safe state management

**Control Logic**:
```python
if temp_c < min_temp and not heater_on:
    turn_heater_on()  # Below minimum
elif temp_c > max_temp and heater_on:
    turn_heater_off()  # Above maximum
# Stays in current state within hysteresis range
```

**Configuration**:
```yaml
heating_control:
  enabled: true
  gpio_pin: 16
  min_temp_c: 20.0
  max_temp_c: 22.0
  check_interval: 10
```

### humidity_control.py

**Purpose**: Humidity-based exhaust fan control with GPIO relay

**Key Features**:
- Hysteresis control to prevent rapid cycling
- Configurable humidity thresholds
- Manual override support
- Thread-safe state management

**Control Logic**:
```python
if humidity > max_humidity and not fan_on:
    turn_fan_on()  # Above maximum, need exhaust
elif humidity < min_humidity and fan_on:
    turn_fan_off()  # Below minimum, stop exhaust
# Stays in current state within hysteresis range
```

**Configuration**:
```yaml
humidity_control:
  enabled: true
  gpio_pin: 20
  min_humidity: 10.0
  max_humidity: 15.0
  check_interval: 10
```

### shared_state.py

**Purpose**: Thread-safe state management for sensor data and control states

**Key Features**:
- Thread-safe dictionary operations
- Sensor data storage and retrieval
- Control state tracking (heater, fan)
- Manual override flag management

**Main Functions**:
```python
def update_sensor_data(
    temperature_c: float,
    temperature_f: float,
    humidity: float,
    pressure: Optional[float] = None
) -> None:
    """Update shared sensor data (thread-safe)."""

def get_sensor_data() -> Dict[str, Any]:
    """Get current sensor data (thread-safe)."""

def update_heater_state(on: bool) -> None:
    """Update heater state (thread-safe)."""

def set_heater_manual_override(state: Optional[bool]) -> None:
    """Set manual override for heater (thread-safe)."""
```

**State Dictionary**:
```python
{
    "temperature_c": float,
    "temperature_f": float,
    "humidity": float,
    "pressure": Optional[float],
    "timestamp": float,
    "heater_on": bool,
    "heater_manual": Optional[bool],  # None = auto, True = force on, False = force off
    "fan_on": bool,
    "fan_manual": Optional[bool]
}
```

### logging_config.py

**Purpose**: Dual-stream logging configuration

**Features**:
- INFO/WARNING to stdout
- ERROR/CRITICAL to stderr
- Colored output with timestamps
- Separate handlers for different severity levels

**Setup**:
```python
def setup_logging(debug: bool = False) -> None:
    """Configure dual-stream logging."""
```

## Data Flow

```
┌─────────────┐
│   Sensor    │
│ (BME280/    │
│  DHT22)     │
└──────┬──────┘
       │ read_sensor_data()
       ▼
┌─────────────┐
│    main.py  │
│  data_      │
│  collection │
└──────┬──────┘
       │ queue.put()
       ▼
┌─────────────┐
│    Queue    │
│  (bounded)  │
└──────┬──────┘
       │ batch when full or timeout
       ▼
┌─────────────┐
│  influx_    │
│  writer.py  │
└──────┬──────┘
       │ on failure
       ▼
┌─────────────┐
│ persistence │
│  .py        │
│ (SQLite)    │
└─────────────┘
```

## Thread Communication

All threads use the global `_stop_event` for coordinated shutdown:

```python
while not stop_event.is_set():
    # Thread work
    time.sleep(interval)
```

Sensor data and control states flow through `shared_state.py`:

```
Data Collection → shared_state.update_sensor_data()
                          ↓
Heating Control ← shared_state.get_sensor_data()
                          ↓
Humidity Control ← shared_state.get_sensor_data()
                          ↓
Web UI Server ← shared_state.get_sensor_data()
                          ↓
CLI Interface ← shared_state.get_sensor_data()
```

## Error Handling

### Sensor Failures
- Logged as errors
- Returns None values
- Continues operation (doesn't crash)

### InfluxDB Failures
- Exponential backoff with jitter
- Persistence to SQLite after threshold
- Alert handler callback option
- Automatic retry on recovery

### GPIO Failures
- Graceful fallback if GPIO unavailable
- Control threads continue (no-op if no GPIO)
- Errors logged but don't crash application

## Configuration Best Practices

### Interactive Configuration Tool
Use the config tool for all configuration management:
```bash
# Interactive menu-based editor
python scripts/config_tool.py --interactive

# Command-line operations
python scripts/config_tool.py --list                    # View all
python scripts/config_tool.py --get database.type      # Get value
python scripts/config_tool.py --set sensor.type BME280 # Set value
```

### Encryption Key Security
Store encryption keys securely:
```bash
# Key priority (highest to lowest):
1. CONFIG_ENCRYPTION_KEY environment variable
2. HashiCorp Vault (if configured)
3. .config_key file (600 permissions)
4. Default key (not recommended)
```

See [Encryption Key Security](../docs/ENCRYPTION_KEY_SECURITY.md) for details.

### Database Backend Selection
Choose appropriate backend for your deployment:
```bash
# For existing InfluxDB v1 installations
python scripts/config_tool.py --set database.type influxdb_v1

# For modern InfluxDB v2 with organizations
python scripts/config_tool.py --set database.type influxdb_v2

# For latest InfluxDB v3 cloud
python scripts/config_tool.py --set database.type influxdb_v3

# For Prometheus ecosystem
python scripts/config_tool.py --set database.type prometheus

# For local-only mode (no remote database)
python scripts/config_tool.py --set database.type none
```

### Tags Configuration
Use the interactive tag editor for key-value pairs:
```bash
python scripts/config_tool.py --interactive
# Navigate to data_collection section
# Select 'tags' key
# Use special tag editor to add/edit/remove tags
```

## Extending the Module

### Adding a New Sensor

1. Update `sensor.py`:
```python
elif sensor_type == "newsensor":
    from newsensor import NewSensor
    _sensor = NewSensor()
```

2. Add configuration using config tool:
```bash
python scripts/config_tool.py --set sensor.type newsensor
python scripts/config_tool.py --set sensor.custom_param value
```

3. Implement `read_sensor_data()` compatible interface

### Adding a New Control Module

1. Create new file (e.g., `cooling_control.py`)
2. Follow pattern from `heating_control.py`
3. Use `shared_state` for sensor data
4. Start thread in `main.py`
5. Add configuration section using config tool:
```bash
python scripts/config_tool.py --set cooling_control.enabled true
python scripts/config_tool.py --set cooling_control.gpio_pin 21
```

### Adding a New Database Backend

1. Update `database_writer.py`:
```python
elif db_type == "newdb":
    from newdb_writer import NewDBWriter
    _writer = NewDBWriter(config)
```

2. Implement unified writer interface:
```python
class NewDBWriter:
    def write_batch(self, batch: List[Dict]) -> bool:
        """Write batch to database, return success."""
```

3. Add configuration:
```bash
python scripts/config_tool.py --set database.type newdb
python scripts/config_tool.py --set database.newdb.host localhost
python scripts/config_tool.py --set database.newdb.port 9999
```

## Related Documentation

- [Main README](../README.md) - Project overview and installation
- [Tests README](../tests/README.md) - Testing documentation
- [Web UI README](../webui/README.md) - Web interface documentation
