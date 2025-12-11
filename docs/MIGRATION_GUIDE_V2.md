# FilamentBox v2.0 Migration Guide

This guide provides detailed instructions for migrating from FilamentBox v1.x to v2.0.

---

## Table of Contents

1. [Before You Begin](#before-you-begin)
2. [What's Changing](#whats-changing)
3. [Migration Methods](#migration-methods)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Post-Migration Verification](#post-migration-verification)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedure](#rollback-procedure)

---

## Before You Begin

### Prerequisites Checklist

- [ ] Running FilamentBox v1.x installation
- [ ] Root/sudo access to the system
- [ ] Backup of current configuration files
- [ ] Note of current database connection (ensure it's accessible)
- [ ] 15-30 minutes for migration process

### What to Back Up

```bash
# Create backup directory
mkdir -p ~/filamentbox_backup_$(date +%Y%m%d)
cd /opt/filamentcontrol

# Backup configuration files
cp config.yaml ~/filamentbox_backup_$(date +%Y%m%d)/ 2>/dev/null || true
cp .env ~/filamentbox_backup_$(date +%Y%m%d)/ 2>/dev/null || true

# Backup service files
cp /etc/systemd/system/filamentbox*.service ~/filamentbox_backup_$(date +%Y%m%d)/ 2>/dev/null || true

# Note current git commit
git rev-parse HEAD > ~/filamentbox_backup_$(date +%Y%m%d)/git_commit.txt
```

### Data Preservation Guarantee

✅ **All your settings will be preserved**:
- Database connection settings
- Sensor configuration
- Control thresholds
- Custom tags
- All other configuration values

The migration is **fully automatic** and has been tested extensively.

---

## What's Changing

### Configuration Storage

| Aspect | v1.x | v2.0 |
|--------|------|------|
| **Format** | YAML + .env files | SQLCipher encrypted database |
| **Location** | `config.yaml` + `.env` | `config.db` |
| **Encryption** | None (plain text) | 256-bit AES |
| **Editing** | Text editor | Interactive CLI tool (`scripts/config_tool.py`) |
| **Security** | Credentials in version control | Encrypted, no plain text |

### Environment Variables

| v1.x | v2.0 | Purpose |
|------|------|---------|
| `INFLUXDB_HOST` | *(in config.db)* | Moved to encrypted database |
| `INFLUXDB_PASSWORD` | *(in config.db)* | Moved to encrypted database |
| *(all credentials)* | *(in config.db)* | All credentials now encrypted |
| *(none)* | `FILAMENTBOX_CONFIG_KEY` | Encryption key (optional, can use file) |
| *(none)* | `VAULT_ADDR` | Vault server address (optional) |
| *(none)* | `VAULT_TOKEN` | Vault authentication (optional) |

### Service Files

| Aspect | v1.x | v2.0 |
|--------|------|------|
| **Location** | `/etc/systemd/system/` | Same |
| **Generation** | Manual or installer | **Auto-generated** by setup |
| **Customization** | Edit directly | **Regenerated on setup** |
| **Vault Support** | None | Environment variables embedded |

**⚠️ Important**: Manual edits to service files will be overwritten. Use the setup script to regenerate.

---

## Migration Methods

### Method 1: Automatic Migration (Recommended)

**Best for**: Most users, production systems, first-time migration

**Pros**:
- ✅ Fully automatic
- ✅ Interactive prompts
- ✅ Validates all settings
- ✅ Regenerates service files
- ✅ Creates backups automatically
- ✅ Tests configuration

**Steps**: See [Automatic Migration](#automatic-migration-recommended)

---

### Method 2: Manual Migration

**Best for**: Advanced users, custom setups, testing environments

**Pros**:
- ✅ More control over process
- ✅ Can review before applying
- ✅ Useful for scripting

**Cons**:
- ⚠️ Requires manual service file updates
- ⚠️ No validation during migration

**Steps**: See [Manual Migration](#manual-migration-advanced)

---

## Step-by-Step Migration

### Automatic Migration (Recommended)

#### Step 1: Update Code

```bash
cd /opt/filamentcontrol

# Stop services before updating
sudo systemctl stop filamentbox.service
sudo systemctl stop filamentbox-webui.service

# Pull v2.0 code
git fetch origin
git checkout v2.0-rc  # or tags/v2.0.0 when released
```

#### Step 2: Run Setup Script

```bash
sudo ./install/setup.sh
```

**What happens**:
1. Detects existing `config.yaml` and `.env` files
2. Prompts: "Migrate existing configuration?"
3. Generates encryption key (displayed once - **SAVE THIS!**)
4. Creates encrypted database with all your settings
5. Backs up legacy files to `config_backup_YYYYMMDD_HHMMSS/`
6. Removes legacy files
7. Regenerates service files
8. Displays summary

#### Step 3: Save Encryption Key

**CRITICAL**: The encryption key is displayed **once** during setup:

```
=======================================================
ENCRYPTION KEY GENERATED
=======================================================

Your encryption key has been generated and saved to:
  /opt/filamentcontrol/.config_key

IMPORTANT: Save this key securely!

  AbCdEf123456...your-64-character-key...XyZ789

Without this key, your configuration cannot be decrypted.

Options for storing the key:
1. HashiCorp Vault (recommended for production)
2. Password manager (1Password, LastPass, etc.)
3. Secure notes (encrypted)
4. Paper backup in secure location

The key is also stored in .config_key with 600 permissions.
=======================================================
```

**Action Required**:
- [ ] Copy the key to password manager
- [ ] OR store in HashiCorp Vault
- [ ] OR write down and store securely
- [ ] Verify `.config_key` file exists and has 600 permissions

#### Step 4: Restart Services

```bash
sudo systemctl daemon-reload
sudo systemctl start filamentbox.service
sudo systemctl start filamentbox-webui.service
```

#### Step 5: Verify Migration

See [Post-Migration Verification](#post-migration-verification)

---

### Manual Migration (Advanced)

#### Step 1: Update Code

```bash
cd /opt/filamentcontrol
sudo systemctl stop filamentbox.service
sudo systemctl stop filamentbox-webui.service
git fetch origin
git checkout v2.0-rc
```

#### Step 2: Run Migration Script

```bash
# Activate virtual environment if using one
source filamentcontrol/bin/activate

# Run migration
python scripts/migrate_config.py
```

**Output**:
```
=======================================================
Configuration Migration Tool
=======================================================

Found existing configuration:
  - config.yaml: 45 settings
  - .env: 8 settings

Migrating to encrypted database...

Generating encryption key...
✓ Encryption key generated

Creating encrypted database...
✓ Database created: config.db

Importing settings...
✓ Imported 45 settings from config.yaml
✓ Imported 8 settings from .env

Creating backup...
✓ Backup created: config_backup_20250110_143022/

=======================================================
ENCRYPTION KEY - SAVE THIS SECURELY
=======================================================

  AbCdEf123456...your-64-character-key...XyZ789

Saved to: /opt/filamentcontrol/.config_key

=======================================================

Removing legacy files...
✓ Removed config.yaml
✓ Removed .env

Migration complete!
```

#### Step 3: Update Service Files

```bash
# Option A: Use setup script to regenerate
sudo ./install/setup.sh
# Choose "Skip" for configuration, just regenerate services

# Option B: Manually add encryption key to existing service
sudo nano /etc/systemd/system/filamentbox.service
```

Add to `[Service]` section:
```ini
Environment="FILAMENTBOX_CONFIG_KEY=your-key-here"
```

#### Step 4: Reload and Start

```bash
sudo systemctl daemon-reload
sudo systemctl start filamentbox.service
sudo systemctl start filamentbox-webui.service
```

---

## Post-Migration Verification

### 1. Check Service Status

```bash
# Both services should be active and running
sudo systemctl status filamentbox.service
sudo systemctl status filamentbox-webui.service
```

Expected output:
```
● filamentbox.service - Filament Storage Environmental Manager
     Loaded: loaded (/etc/systemd/system/filamentbox.service; enabled)
     Active: active (running) since ...
```

### 2. Verify Configuration

```bash
# Browse configuration with interactive tool
python scripts/config_tool.py
```

Expected:
- All your previous settings visible
- Database settings intact
- Sensor configuration preserved
- Control thresholds unchanged

**Navigation**:
- `B` - Browse sections
- `S` - Search for specific key
- `V` - View current value
- `Q` - Quit

### 3. Test Sensor Readings

```bash
# Check logs for sensor data
sudo journalctl -u filamentbox.service -n 50
```

Look for:
```
Sensor reading: 21.5°C, 45.2% humidity
Database write successful
```

### 4. Test Web UI

```bash
# Open in browser
firefox http://localhost:5000
# or
curl http://localhost:5000/api/sensor
```

Expected:
- Modern React UI loads
- Real-time sensor data updates
- Control buttons functional
- Notifications panel accessible
- Dark mode toggle works

### 5. Test Database Writes

```bash
# Check your database for recent data
# Example for InfluxDB:
influx -database filament_storage -execute 'SELECT * FROM environment ORDER BY time DESC LIMIT 5'

# Or check logs
sudo journalctl -u filamentbox.service | grep "Database write"
```

Expected:
```
Database write successful: 1 point(s)
```

### 6. Test Hot-Reload

```bash
# Change a configuration value
python scripts/config_tool.py
# Navigate to a setting and change it
# E.g., data_collection.read_interval_seconds

# Check logs for reload
sudo journalctl -u filamentbox.service -f
```

Expected:
```
Configuration file modified, reloading...
Configuration changed: data_collection.read_interval_seconds = 5
```

### 7. Test Thread Controls

1. Open web UI: `http://localhost:5000`
2. Look for thread status panel
3. Click "Restart" on any thread
4. Should see:
   - Notification: "Restarting sensor_reader thread..."
   - Thread status changes
   - Browser notification (if enabled)

### 8. Test Notifications

1. Open web UI
2. Click "Enable Browser Notifications" (if prompted)
3. Grant permission
4. Restart a thread or change config
5. Should see:
   - Browser toaster notification (OS-level)
   - In-app notification in panel
   - Color-coded by type

---

## Troubleshooting

### Service Won't Start

**Symptom**: `sudo systemctl status filamentbox.service` shows "failed"

**Check**:
```bash
sudo journalctl -u filamentbox.service -n 100
```

**Common Causes**:

#### 1. Missing Encryption Key

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: '.config_key'
```

**Fix**:
```bash
# Key should be in .config_key file
ls -la /opt/filamentcontrol/.config_key

# If missing, set environment variable
sudo nano /etc/systemd/system/filamentbox.service
# Add: Environment="FILAMENTBOX_CONFIG_KEY=your-key"

sudo systemctl daemon-reload
sudo systemctl start filamentbox.service
```

#### 2. Wrong File Permissions

**Error**:
```
PermissionError: [Errno 13] Permission denied: 'config.db'
```

**Fix**:
```bash
cd /opt/filamentcontrol
sudo chown $USER:$USER config.db .config_key
chmod 600 .config_key
chmod 644 config.db
```

#### 3. Corrupted Database

**Error**:
```
sqlite3.DatabaseError: file is not a database
```

**Fix**:
```bash
# Restore from backup
cd /opt/filamentcontrol
rm config.db
python scripts/migrate_config.py
# Use backup folder if needed:
# cp config_backup_*/config.yaml .
# cp config_backup_*/.env .
```

---

### Configuration Not Migrated

**Symptom**: Settings are missing or default values

**Check**:
```bash
python scripts/config_tool.py
# Browse sections and verify values
```

**Fix**:
```bash
# Find backup folder
ls -ltr /opt/filamentcontrol/config_backup_*

# Restore and re-migrate
cd /opt/filamentcontrol
cp config_backup_YYYYMMDD_HHMMSS/config.yaml .
cp config_backup_YYYYMMDD_HHMMSS/.env .
python scripts/migrate_config.py
```

---

### Database Not Writing

**Symptom**: No data in database after migration

**Check**:
```bash
sudo journalctl -u filamentbox.service | grep -i "database\|write\|error"
```

**Common Causes**:

#### 1. Database Settings Lost

```bash
# Verify database configuration
python scripts/config_tool.py
# Navigate to: database.influxdb (or your backend)
# Verify: host, port, database, credentials
```

#### 2. Wrong Database Type

```bash
# Check database type
python -c "from filamentbox.config import get; print(get('database.type'))"

# Should match your actual database (influxdb, prometheus, etc.)
# If wrong, fix with config tool:
python scripts/config_tool.py
# Edit: database.type
```

---

### Web UI Not Loading

**Symptom**: `http://localhost:5000` shows error or doesn't load

**Check**:
```bash
sudo systemctl status filamentbox-webui.service
sudo journalctl -u filamentbox-webui.service -n 50
```

**Common Fixes**:

#### 1. Service Not Running

```bash
sudo systemctl start filamentbox-webui.service
sudo systemctl enable filamentbox-webui.service
```

#### 2. Port Already in Use

```bash
sudo netstat -tlnp | grep :5000
# or
sudo lsof -i :5000
```

**Fix**: Kill conflicting process or change port in config

#### 3. React Build Missing

```bash
# Check if React build exists
ls -la /opt/filamentcontrol/webui/webui-react/dist/

# If missing, build it:
cd /opt/filamentcontrol/webui/webui-react
npm install
npm run build
```

---

### Notifications Not Working

**Symptom**: No browser notifications appearing

**Check**:

1. **Browser Permissions**:
   - Open web UI
   - Check browser address bar for notification icon
   - Click and grant permission

2. **Notification Support**:
   ```bash
   # Open browser console (F12)
   console.log('Notification' in window);  // Should be true
   console.log(Notification.permission);   // Should be 'granted'
   ```

3. **Backend Publishing**:
   ```bash
   sudo journalctl -u filamentbox.service | grep -i notification
   ```

---

## Rollback Procedure

If you need to rollback to v1.x:

### Step 1: Stop Services

```bash
sudo systemctl stop filamentbox.service
sudo systemctl stop filamentbox-webui.service
```

### Step 2: Restore Code

```bash
cd /opt/filamentcontrol
git checkout tags/v1.6.1  # or your previous version
```

### Step 3: Restore Configuration

```bash
# Find your backup
ls -ltr /opt/filamentcontrol/config_backup_*

# Restore files
cd /opt/filamentcontrol
cp config_backup_YYYYMMDD_HHMMSS/config.yaml .
cp config_backup_YYYYMMDD_HHMMSS/.env .

# Remove v2.0 files
rm config.db .config_key
```

### Step 4: Restore Service Files (if needed)

```bash
# If you backed up service files
sudo cp ~/filamentbox_backup_YYYYMMDD/filamentbox.service \
    /etc/systemd/system/

sudo cp ~/filamentbox_backup_YYYYMMDD/filamentbox-webui.service \
    /etc/systemd/system/
```

### Step 5: Reload and Start

```bash
sudo systemctl daemon-reload
sudo systemctl start filamentbox.service
sudo systemctl start filamentbox-webui.service
```

### Step 6: Verify Rollback

```bash
sudo systemctl status filamentbox.service
sudo journalctl -u filamentbox.service -n 50
```

---

## Advanced Topics

### Using HashiCorp Vault

After migration, you can move the encryption key to Vault:

```bash
# 1. Set up Vault (if not already)
./scripts/configure_vault.sh

# 2. Store key in Vault
vault kv put secret/filamentbox config_key="your-key-from-.config_key"

# 3. Update service to use Vault
sudo nano /etc/systemd/system/filamentbox.service
```

Add Vault environment variables:
```ini
Environment="VAULT_ADDR=https://vault.example.com:8200"
Environment="VAULT_TOKEN=s.your_token"
Environment="VAULT_KEY_PATH=secret/data/filamentbox"
```

Remove local key variable:
```ini
# Remove or comment out:
# Environment="FILAMENTBOX_CONFIG_KEY=..."
```

```bash
# 4. Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart filamentbox.service

# 5. Verify Vault integration
sudo journalctl -u filamentbox.service -n 50 | grep -i vault
```

Expected:
```
Loading encryption key from Vault...
Successfully loaded key from Vault
```

---

### Custom Installation Paths

If your installation is not in `/opt/filamentcontrol`:

```bash
# During setup, specify custom path
cd /home/user/myfilamentbox
sudo ./install/setup.sh

# Setup will auto-detect and use current directory
```

Service files are auto-generated with correct paths.

---

### Docker Migration

For Docker deployments:

```dockerfile
# Update Dockerfile to use v2.0
FROM python:3.13-slim

WORKDIR /app
COPY . /app

# Run migration during build
RUN python scripts/migrate_config.py

# Store key as environment variable
ENV FILAMENTBOX_CONFIG_KEY="your-key-here"

CMD ["python", "-m", "filamentbox.main"]
```

Or use Docker secrets:
```bash
# Create secret
docker secret create filamentbox_key .config_key

# Use in docker-compose.yml
services:
  filamentbox:
    image: filamentbox:v2.0
    secrets:
      - filamentbox_key
    environment:
      - FILAMENTBOX_CONFIG_KEY=/run/secrets/filamentbox_key
```

---

## Migration Checklist

Print this checklist and mark items as completed:

### Pre-Migration
- [ ] Backup `config.yaml`
- [ ] Backup `.env`
- [ ] Backup service files
- [ ] Note current git commit
- [ ] Verify database is accessible
- [ ] Stop services

### Migration
- [ ] Pull v2.0 code
- [ ] Run `sudo ./install/setup.sh`
- [ ] **Save encryption key**
- [ ] Verify backup created
- [ ] Review migration summary

### Post-Migration
- [ ] Start services
- [ ] Check service status
- [ ] Browse configuration
- [ ] Test sensor readings
- [ ] Test web UI
- [ ] Test database writes
- [ ] Test hot-reload
- [ ] Test thread controls
- [ ] Test notifications
- [ ] Test dark mode

### Optional
- [ ] Set up HashiCorp Vault
- [ ] Store key in Vault
- [ ] Remove local `.config_key` file
- [ ] Update documentation
- [ ] Train team on new features

---

## Getting Help

If you encounter issues:

1. **Check Logs**:
   ```bash
   sudo journalctl -u filamentbox.service -n 100 --no-pager
   ```

2. **Review Documentation**:
   - [V2.0 Features Summary](V2.0_FEATURES_SUMMARY.md)
   - [Encryption Key Security](ENCRYPTION_KEY_SECURITY.md)
   - [CHANGELOG](../CHANGELOG.md)

3. **GitHub Issues**:
   - https://github.com/jdelgado-dtlabs/filamentenvmonitor/issues
   - Include: OS, Python version, logs, config (sanitized)

4. **Common Issues**:
   - Search existing issues for your error message
   - Check troubleshooting section above

---

## Success!

Once all checks pass, your migration is complete. Enjoy v2.0 features:

- 🌐 Modern React Web UI with PWA support
- ⚡ Real-time SSE updates
- 🔔 Comprehensive notifications
- 🎨 Dark mode theme
- 🔄 Hot-reload configuration
- 🔐 Encrypted configuration
- 📊 Multi-database support
- 🎮 Thread control via web UI

**Next Steps**:
1. Explore the new React UI: `http://localhost:5000`
2. Enable browser notifications
3. Try dark mode toggle
4. Explore configuration tool: `python scripts/config_tool.py`
5. Read [v2.0 Features Summary](V2.0_FEATURES_SUMMARY.md)

Welcome to FilamentBox v2.0! 🎉
