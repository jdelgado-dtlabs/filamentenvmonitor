# Deprecation: data_collection.tags

## Summary
The configuration key `data_collection.tags` has been **completely deprecated** and removed from the system. Tags are now database-specific.

## What Changed

### ✅ Correct Implementation (Current)
Tags are configured per database type:
- `database.influxdb.tags` - Tags for InfluxDB data points
- `database.prometheus.tags` - Tags for Prometheus metrics
- `database.timescaledb.tags` - Tags for TimescaleDB (if supported)
- `database.victoriametrics.tags` - Tags for VictoriaMetrics (if supported)

### ❌ Deprecated (Removed)
- `data_collection.tags` - NEVER actually used in production code

## Files Updated

### 1. Configuration Schema (`filamentbox/config_schema.py`)
**Status:** ✅ Already clean
- `data_collection` section has: `read_interval`, `batch_size`, `flush_interval`
- No `tags` field in data_collection section
- Database sections have proper tags support

### 2. Configuration Database (`filamentbox_config.db`)
**Status:** ✅ Clean
- Checked: `data_collection.tags` does not exist in database
- Existing tags: `database.influxdb.tags: {"location": "filamentbox"}`

### 3. React UI (`webui/webui-react/src/components/`)
**Status:** ✅ Updated
- TagEditor now database-specific (accepts `dbType` prop)
- Removed from SensorCard
- Added to DatabaseConfigEditor (one editor per database type)
- Each database tab has "🏷️ Edit {dbtype} Tags" button

### 4. Scripts (`scripts/config_tool.py`)
**Status:** ✅ Updated
- `edit_tags_menu()` function signature updated
- Removed default parameter `base_key = "data_collection.tags"`
- Added deprecation note in docstring
- Function requires explicit `base_key` parameter (database-specific)

### 5. Tests (`tests/test_data_point_tags.py`)
**Status:** ⚠️ Updated but deprecated
- Updated to use `database.influxdb.tags` instead of `data_collection.tags`
- Tests marked as DEPRECATED (mock non-existent functions)
- TODO: Rewrite to test actual orchestrator.py implementation

## Implementation Details

### Where Tags Are Actually Used
File: `filamentbox/orchestrator.py` (lines 168-200)

```python
# Get measurement and tags from config
measurement = get("data_collection.measurement") or "environment"
tags = get("database.influxdb.tags", {})

# Build data point
db_json_body = {
    "measurement": measurement,
    "fields": {
        "time": timestamp,
        "temperature_c": temperature_c,
        "temperature_f": temperature_f,
        "humidity": humidity,
    },
}

# Only include tags if configured
if tags:
    db_json_body["tags"] = tags
```

### How to Edit Tags (Web UI)
1. Navigate to Configuration → Database
2. Select database tab (InfluxDB, Prometheus, etc.)
3. Click "🏷️ Edit {database} Tags" button
4. Add/remove key-value pairs
5. Click Save (restart notification shown)

### How to Edit Tags (CLI - if config_tool supports it)
```bash
# Note: edit_tags_menu() now requires explicit base_key
edit_tags_menu(cache, base_key="database.influxdb.tags")
```

## Migration Guide

### If You Were Using data_collection.tags
**You weren't.** This config key was never actually used in production code.

### If You Have data_collection.tags in Your Config
Run this to check:
```bash
sudo FILAMENTBOX_CONFIG_KEY=$(sudo cat .config_key) ./filamentcontrol/bin/python3 -c "
from filamentbox.config_db import get_config_db
db = get_config_db()
val = db.get('data_collection.tags')
print(f'data_collection.tags: {val}')
"
```

If it exists, delete it:
```bash
sudo FILAMENTBOX_CONFIG_KEY=$(sudo cat .config_key) ./filamentcontrol/bin/python3 -c "
from filamentbox.config_db import get_config_db
db = get_config_db()
db.delete('data_collection.tags')
print('Deleted data_collection.tags')
"
```

### Moving Forward
Always use database-specific tag configuration:
- **InfluxDB:** `database.influxdb.tags`
- **Prometheus:** `database.prometheus.tags`
- **TimescaleDB:** `database.timescaledb.tags`
- **VictoriaMetrics:** `database.victoriametrics.tags`

## Verification Checklist
- [x] Schema clean (config_schema.py)
- [x] Database clean (filamentbox_config.db)
- [x] React UI migrated to database-specific tags
- [x] Scripts updated (config_tool.py)
- [x] Tests updated (marked deprecated, needs rewrite)
- [x] Production code uses database.{dbtype}.tags

## Date
December 10, 2025
