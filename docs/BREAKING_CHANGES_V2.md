# FSEM v2.0 - Breaking Changes & Migration Requirements

**Filament Storage Environmental Manager - Quick Reference Guide**

---

## ⚠️ Breaking Changes Summary

### 1. Configuration System (HIGH IMPACT)

| What Changed | v1.x | v2.0 | Migration Required |
|--------------|------|------|-------------------|
| Format | YAML + .env | SQLCipher encrypted DB | ✅ YES |
| Storage | `config.yaml`, `.env` | `config.db` | ✅ YES |
| Encryption | None | 256-bit AES | ✅ YES |
| Editing | Text editor | CLI tool | ✅ YES |

**Action Required**: Run `sudo ./install/setup.sh` or `python scripts/migrate_config.py`

**Data Loss Risk**: ❌ None - automatic migration preserves all settings

---

### 2. Environment Variables (MEDIUM IMPACT)

**Removed Variables** (all moved to encrypted database):
```bash
# ❌ No longer used in v2.0
INFLUXDB_HOST
INFLUXDB_PORT
INFLUXDB_DATABASE
INFLUXDB_USERNAME
INFLUXDB_PASSWORD
INFLUXDB_BUCKET
INFLUXDB_ORG
INFLUXDB_TOKEN
# ... all other database credentials
```

**New Variables**:
```bash
# ✅ New in v2.0
FILAMENTBOX_CONFIG_KEY="auto-generated-64-char-key"  # Encryption key

# Optional Vault integration
VAULT_ADDR="https://vault.example.com:8200"
VAULT_TOKEN="s.your_token"
VAULT_ROLE_ID="your_role_id"
VAULT_SECRET_ID="your_secret_id"
VAULT_KEY_PATH="secret/data/filamentbox"
```

**Action Required**: None if using automatic migration (handled by setup script)

---

### 3. Service Files (LOW IMPACT)

**Change**: Service files now auto-generated during setup

**Impact**: Manual edits to service files will be overwritten

**Action Required**: 
- Re-run `sudo ./install/setup.sh` to regenerate
- Or update service files manually with new environment variables

---

### 4. Python API (LOW IMPACT - Developers Only)

**Old Configuration Access**:
```python
# ❌ No longer works in v2.0
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
value = config['section']['key']
```

**New Configuration Access**:
```python
# ✅ Use in v2.0
from filamentbox.config import get
value = get('section.key')

# ✅ Hot-reload support
from filamentbox.config_watcher import register_callback
register_callback('database.type', on_change_func)
```

**Action Required**: Update custom scripts/code using internal APIs

---

## 📋 Migration Requirements Checklist

### Must Have Before Migrating

- [ ] Running FSEM v1.x installation
- [ ] Root/sudo access
- [ ] 15-30 minutes for migration
- [ ] Space to save encryption key securely

### Must Do During Migration

- [ ] **CRITICAL**: Save encryption key when displayed
  - Without this key, config cannot be decrypted
  - Save to password manager, Vault, or secure notes
  - Key is 64 characters, auto-generated, displayed once

### Must Verify After Migration

- [ ] Services running: `sudo systemctl status filamentbox.service`
- [ ] Config accessible: `python scripts/config_tool.py`
- [ ] Sensor readings working
- [ ] Database writes successful
- [ ] Web UI accessible: `http://localhost:5000`

---

## 🚀 Quick Migration Path

### For Most Users (Recommended)

```bash
# 1. Stop services
sudo systemctl stop filamentbox.service filamentbox.service (webui integrated in v2.0)

# 2. Update code
cd /opt/filamentcontrol
git fetch origin
git checkout v2.0-rc  # or tags/v2.0.0

# 3. Run migration
sudo ./install/setup.sh

# 4. **SAVE THE ENCRYPTION KEY DISPLAYED!**

# 5. Start services
sudo systemctl start filamentbox.service filamentbox.service (webui integrated in v2.0)

# 6. Test
firefox http://localhost:5000
```

**Time Required**: ~15 minutes

**Downtime**: ~5 minutes (while services stopped)

**Risk Level**: 🟢 Low (automatic migration, automatic backups)

---

### For Advanced Users

```bash
# Manual migration with more control
cd /opt/filamentcontrol
git checkout v2.0-rc
python scripts/migrate_config.py
# Update service files manually
sudo systemctl daemon-reload
sudo systemctl restart filamentbox.service
```

**Time Required**: ~20 minutes

**Risk Level**: 🟡 Medium (requires manual service file updates)

---

## 🔄 What Gets Migrated Automatically

✅ **All Configuration Values**:
- Database settings (host, port, credentials, type)
- Sensor settings (type, GPIO pins, calibration)
- Control thresholds (heating, humidity)
- Data collection intervals
- Batch sizes and queue settings
- Retry logic configuration
- Persistence settings
- Custom tags
- **Everything in `config.yaml` and `.env`**

✅ **Automatic Backups**:
- Original files backed up to `config_backup_YYYYMMDD_HHMMSS/`
- Timestamped for easy rollback
- Kept indefinitely (manual cleanup)

✅ **Service Files**:
- Auto-regenerated with correct paths
- Vault variables embedded if configured
- Old files backed up

---

## ❌ What Does NOT Get Migrated

- ❌ Database data (not configuration - your historical data is untouched)
- ❌ Python packages (re-install if needed: `pip install -r requirements.txt`)
- ❌ Custom scripts outside the repository
- ❌ Nginx configurations (but templates provided)

---

## 🔑 Critical: Encryption Key Management

### Where the Key is Stored (Priority Order)

1. **Environment Variable** (highest priority)
   - `FILAMENTBOX_CONFIG_KEY=your-key`
   - In service file or shell environment

2. **HashiCorp Vault** (recommended for production)
   - `VAULT_ADDR` + `VAULT_TOKEN` or `VAULT_ROLE_ID/SECRET_ID`
   - Retrieves key from `VAULT_KEY_PATH`

3. **Local File** (default)
   - `/opt/filamentcontrol/.config_key`
   - Permissions: 600 (owner read/write only)

4. **Default Key** (dev/testing only - insecure)
   - Fallback if nothing else available

### How to Save Your Key

**Option 1: Password Manager** (recommended for individuals)
```
Store in: 1Password, LastPass, Bitwarden, etc.
Title: FilamentBox Encryption Key
Username: filamentbox@hostname
Password: [your-64-char-key]
URL: http://your-pi-ip:5000
Notes: Generated on YYYY-MM-DD during v2.0 migration
```

**Option 2: HashiCorp Vault** (recommended for teams/production)
```bash
# Store in Vault
vault kv put secret/filamentbox config_key="your-64-char-key"

# Configure service to use Vault
# (done automatically if you configure Vault during setup)
```

**Option 3: Secure Notes** (encrypted file)
```bash
# Create encrypted backup
gpg --symmetric --cipher-algo AES256 -o config_key.gpg <<EOF
your-64-char-key
EOF

# Store config_key.gpg in backup location
```

**Option 4: Paper Backup** (physical security)
```
Write key on paper
Store in safe, safety deposit box, or secure filing cabinet
Label: "FilamentBox Config Key - Generated YYYY-MM-DD"
```

### Key Recovery

**If You Lose the Key**:

1. ❌ **Cannot decrypt existing config.db**
   - Encryption is real, key is required
   - No backdoor, no master key

2. ✅ **Can Re-Migrate** (if you have backup)
   ```bash
   # Use backup folder
   cd /opt/filamentcontrol
   cp config_backup_YYYYMMDD_HHMMSS/config.yaml .
   cp config_backup_YYYYMMDD_HHMMSS/.env .
   rm config.db .config_key
   python scripts/migrate_config.py
   # New key generated, save it this time!
   ```

3. ✅ **Can Reconfigure** (manual setup)
   ```bash
   rm config.db .config_key
   sudo ./install/setup.sh
   # Set up configuration from scratch
   ```

---

## 🐛 Common Migration Issues & Fixes

### Issue: "Service won't start after migration"

**Cause**: Missing encryption key

**Fix**:
```bash
# Check if key file exists
ls -la /opt/filamentcontrol/.config_key

# If missing, add to service file
sudo nano /etc/systemd/system/filamentbox.service
# Add under [Service]:
Environment="FILAMENTBOX_CONFIG_KEY=your-key"

sudo systemctl daemon-reload
sudo systemctl start filamentbox.service
```

---

### Issue: "Configuration settings are default values"

**Cause**: Migration didn't run or failed

**Fix**:
```bash
# Check for backup
ls -la /opt/filamentcontrol/config_backup_*

# Re-run migration
cd /opt/filamentcontrol
cp config_backup_YYYYMMDD_HHMMSS/config.yaml .
cp config_backup_YYYYMMDD_HHMMSS/.env .
rm config.db .config_key
python scripts/migrate_config.py
```

---

### Issue: "Database not writing after migration"

**Cause**: Database credentials lost or wrong backend type

**Fix**:
```bash
# Verify database settings
python scripts/config_tool.py
# Browse to: database.influxdb (or your backend)
# Check: host, port, credentials, database name

# Verify database type matches
python -c "from filamentbox.config import get; print(get('database.type'))"
# Should be: influxdb, influxdb2, influxdb3, prometheus, timescaledb, victoriametrics, or none
```

---

### Issue: "Web UI not loading"

**Cause**: React build missing or service not running

**Fix**:
```bash
# Check web UI service
sudo systemctl status filamentbox.service (webui integrated in v2.0)

# If not running
sudo systemctl start filamentbox.service (webui integrated in v2.0)

# If React build missing
cd /opt/filamentcontrol/webui/webui-react
npm install
npm run build
sudo systemctl restart filamentbox.service (webui integrated in v2.0)
```

---

## 📞 Getting Help

### Documentation
- **Migration Guide**: [MIGRATION_GUIDE_V2.md](MIGRATION_GUIDE_V2.md)
- **Features Summary**: [V2.0_FEATURES_SUMMARY.md](V2.0_FEATURES_SUMMARY.md)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)
- **Security**: [ENCRYPTION_KEY_SECURITY.md](ENCRYPTION_KEY_SECURITY.md)

### Support
- **GitHub Issues**: https://github.com/jdelgado-dtlabs/filamentenvmonitor/issues
- **Include**: OS, Python version, logs (`sudo journalctl -u filamentbox.service -n 100`), sanitized config

### Before Asking for Help
1. Check logs: `sudo journalctl -u filamentbox.service -n 100`
2. Verify key exists: `ls -la .config_key`
3. Test config tool: `python scripts/config_tool.py`
4. Search existing issues on GitHub

---

## ✅ Migration Success Criteria

Your migration is successful when:

- [x] ✅ Services running: `systemctl status filamentbox.service` shows "active (running)"
- [x] ✅ Config accessible: `python scripts/config_tool.py` shows all your settings
- [x] ✅ Sensor reading: Logs show temperature/humidity readings
- [x] ✅ Database writing: Logs show "Database write successful"
- [x] ✅ Web UI working: `http://localhost:5000` loads modern React interface
- [x] ✅ Real-time updates: Sensor data updates every 1-2 seconds without refresh
- [x] ✅ Controls working: Heater/fan controls respond in web UI
- [x] ✅ Notifications working: Browser notifications appear (after granting permission)
- [x] ✅ Dark mode working: Theme toggle switches between light/dark
- [x] ✅ Encryption key saved: Key stored securely in password manager/Vault

---

## 🎯 What's New After Migration

Once migrated, you can enjoy:

### 🌐 Modern React Web UI
- Progressive Web App (install as native app)
- Offline support with service worker
- Responsive design for all devices
- Dark mode with OS preference detection

### ⚡ Real-Time Features
- Server-Sent Events for instant updates
- No polling needed - push updates from server
- Live sensor readings every 1-2 seconds
- Real-time thread status monitoring

### 🔔 Comprehensive Notifications
- Browser notifications (OS-level toasters)
- In-app notification panel with history
- Thread state changes
- Configuration updates
- Error alerts

### 🔄 Hot-Reload Configuration
- Change settings without restarting service
- Instant updates for most configuration
- Background watcher monitors database
- Callbacks for dependent components

### 🎮 Thread Management
- Restart/start/stop threads via web UI
- Remote troubleshooting without SSH
- Graceful restarts without full service restart
- Real-time status in UI

### 📊 Multi-Database Support
- 7 database backends (InfluxDB v1/v2/v3, Prometheus, TimescaleDB, VictoriaMetrics, None)
- Easy switching between backends
- Universal tag support across all backends
- Backend-specific optimizations

### 🔐 Enhanced Security
- Encrypted configuration (no plain-text credentials)
- HashiCorp Vault integration (optional)
- Auto-generated cryptographic keys
- Secure key storage with 600 permissions

---

## 📅 Migration Timeline

**Estimated Timeline for Different Scenarios**:

| Scenario | Time Required | Downtime | Risk |
|----------|--------------|----------|------|
| **Standard Installation** | 15 min | 5 min | 🟢 Low |
| **Custom Installation** | 30 min | 10 min | 🟡 Medium |
| **Docker Deployment** | 20 min | 5 min | 🟢 Low |
| **Vault Integration** | +15 min | +0 min | 🟡 Medium |
| **Multi-Node Setup** | per node | per node | 🟡 Medium |

**Best Time to Migrate**:
- ✅ During planned maintenance window
- ✅ Off-peak hours (low data collection importance)
- ✅ When you have 30-60 minutes available
- ❌ Not during critical monitoring periods
- ❌ Not without ability to rollback if needed

---

**Ready to migrate? See [MIGRATION_GUIDE_V2.md](MIGRATION_GUIDE_V2.md) for detailed step-by-step instructions.**

---

*Last Updated: 2025-01-10*  
*Version: 2.0.0-rc*
