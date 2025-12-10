# Configuration Tags Guide

## Overview

The FilamentBox configuration system supports complex values like dictionaries (JSON objects) for features such as database tags. This guide explains how to set and manage these values.

## Setting Tags

### Using the Configuration Tool

Tags can be set using the `config_tool.py` with JSON syntax:

```bash
sudo FILAMENTBOX_CONFIG_KEY=$(sudo cat .config_key) \
  filamentcontrol/bin/python scripts/config_tool.py \
  --db /opt/filamentcontrol/filamentbox_config.db \
  --key "$(sudo cat .config_key)" \
  --set database.influxdb.tags '{"location":"garage","device":"raspberry_pi","environment":"production"}'
```

### JSON Format Requirements

- Must be valid JSON syntax
- Wrap the entire JSON object in single quotes
- Use double quotes for keys and string values
- Example: `'{"key1":"value1","key2":"value2"}'`

### Supported Tag Examples

#### Location Tagging
```bash
--set database.influxdb.tags '{"location":"garage"}'
```

#### Device Identification
```bash
--set database.influxdb.tags '{"device":"raspberry_pi_1","room":"filament_storage"}'
```

#### Multi-Tag Configuration
```bash
--set database.influxdb.tags '{"location":"garage","device":"pi1","environment":"production","zone":"a"}'
```

## Viewing Tags

To view the current tags configuration:

```bash
sudo FILAMENTBOX_CONFIG_KEY=$(sudo cat .config_key) \
  filamentcontrol/bin/python scripts/config_tool.py \
  --db /opt/filamentcontrol/filamentbox_config.db \
  --key "$(sudo cat .config_key)" \
  --get database.influxdb.tags
```

Output will be pretty-printed:
```
database.influxdb.tags = {
  "location": "garage",
  "device": "raspberry_pi",
  "environment": "production"
}
```

## How Tags Are Used

### InfluxDB
Tags are added to every data point written to InfluxDB. They allow you to:
- Filter and group data by location, device, or environment
- Run queries across multiple devices
- Organize time-series data by metadata

### PostgreSQL/MySQL
For relational databases, tags can be stored as JSON fields or in separate tag tables depending on your schema design.

### SQLite
Tags are stored as JSON text in the database.

## Hot-Reload Support

When you change tags using the configuration tool, you have two options:

### Option 1: Restart Service (Immediate)
```bash
sudo systemctl restart filamentbox
```

### Option 2: Use Hot-Reload (Automatic)
Some configuration keys support automatic hot-reload. However, database tags are loaded only once when the database writer initializes, so a service restart is required for tag changes to take effect.

## Troubleshooting

### Invalid JSON Error
If you get an error about invalid JSON:
- Check that you're using double quotes for keys and string values
- Ensure the JSON is wrapped in single quotes
- Validate your JSON using a tool like `echo '{"test":"value"}' | python3 -m json.tool`

### Tags Not Applied
If tags aren't appearing in your database:
1. Verify they're set correctly: `--get database.influxdb.tags`
2. Restart the service: `sudo systemctl restart filamentbox`
3. Check logs for errors: `sudo journalctl -u filamentbox -n 50`

### Old Data With Wrong Tags
If you have persisted batches with old tags that are causing errors:
1. Stop the service: `sudo systemctl stop filamentbox`
2. Remove persisted batches: `sudo rm /opt/filamentcontrol/unsent_batches.db`
3. Start the service: `sudo systemctl start filamentbox`

Note: Only remove persisted batches if you're willing to lose unsent data points.

## Technical Details

### Storage Format
Tags are stored as JSON in the SQLCipher configuration database:
- Key: `database.influxdb.tags`
- Type: `dict`
- Encryption: Yes (SQLCipher)

### Database Schema
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,          -- JSON serialized
    value_type TEXT,               -- 'dict' for tags
    description TEXT,
    updated_at REAL
);
```

### Python Usage
In your code, tags are accessed as a Python dictionary:
```python
from filamentbox.config_db import get

tags = get("database.influxdb.tags", {})
# Returns: {'location': 'garage', 'device': 'raspberry_pi'}
```

## Examples

### Home Lab Setup
```bash
--set database.influxdb.tags '{"location":"home_lab","rack":"1","device":"filamentbox_1"}'
```

### Production Environment
```bash
--set database.influxdb.tags '{"environment":"production","datacenter":"dc1","cabinet":"a12"}'
```

### Development Testing
```bash
--set database.influxdb.tags '{"environment":"development","user":"shadowmage","purpose":"testing"}'
```

## Related Configuration

Other configuration keys that accept JSON/dict values:
- `database.influxdb.tags` - InfluxDB measurement tags
- (More may be added in future versions)

For primitive configuration values (strings, numbers, booleans), see the main [Configuration Guide](configuration.md).
