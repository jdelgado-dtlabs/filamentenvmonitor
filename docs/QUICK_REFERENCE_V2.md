# FSEM v2.0 - Quick Reference Card

**Filament Storage Environmental Manager - One-Page Feature Summary**

---

## 🎯 Core Improvements at a Glance

| Feature | v1.x | v2.0 | Benefit |
|---------|------|------|---------|
| **Web UI** | Vanilla HTML | React PWA | Modern, installable, offline |
| **Real-Time** | 2s polling | SSE push | Instant updates, lower load |
| **Notifications** | None | Browser + Panel | Alerts, history, color-coded |
| **Theme** | Light only | Light/Dark/Auto | OS integration, preferences |
| **Config** | YAML + .env | Encrypted DB | Security, no plain text |
| **Databases** | InfluxDB v1 | 7 backends | Flexibility, choice |
| **Hot-Reload** | No (restart) | Yes (auto) | Zero downtime config |
| **Thread Control** | SSH only | Web UI | Remote management |
| **Architecture** | File IPC | Queue IPC | Faster, cleaner |
| **Vault** | No | Yes | Enterprise secrets |

---

## 🌐 Modern Web Experience

### React PWA
```
✓ Install as native app
✓ Offline support
✓ Fast performance
✓ Code splitting
✓ Responsive design
```

### Server-Sent Events
```
✓ Push updates (no polling)
✓ Real-time sensor data
✓ Live control states
✓ Thread monitoring
✓ Lower bandwidth
```

### Notifications
```
✓ OS toaster alerts
✓ In-app panel
✓ Color-coded types
✓ Dismissible history
✓ Real-time delivery
```

### Dark Mode
```
✓ Light / Dark / Auto
✓ OS preference detection
✓ Persistent settings
✓ Smooth transitions
✓ CSS variables
```

---

## 🔐 Security & Configuration

### Encrypted Config
```yaml
# v1.x - Plain text
database:
  host: localhost
  password: secret123

# v2.0 - Encrypted
config.db (SQLCipher)
256-bit AES encryption
No plain text anywhere
```

### Key Management
```
Priority Order:
1. Environment variable (highest)
2. HashiCorp Vault
3. Local file (.config_key)
4. Default (dev only)
```

### Migration
```bash
# One command
sudo ./install/setup.sh

# Result
✓ All settings preserved
✓ Auto encryption
✓ Legacy files backed up
✓ Key generated
```

---

## 📊 Database Support

### 7 Backend Options
```
1. InfluxDB v1    - HTTP API
2. InfluxDB v2    - Token/bucket
3. InfluxDB v3    - Cloud
4. Prometheus     - Push gateway
5. TimescaleDB    - PostgreSQL
6. VictoriaMetrics- High-perf
7. None           - Sensor-only
```

### Easy Switching
```bash
python scripts/config_tool.py
# database.type → prometheus
sudo systemctl restart filamentbox
# Now using Prometheus!
```

---

## 🔄 Configuration Management

### Hot-Reload
```
Change → Auto-Reload → No Restart

Example:
Edit threshold → 2s → Applied
No downtime!
```

### Config Tool
```bash
python scripts/config_tool.py

Commands:
B - Browse sections
S - Search keys
V - View value
E - Edit value
D - Delete value
C - Create value
Q - Quit
```

---

## 🎮 Thread Control

### Web UI Management
```
View Status:
✓ Running / Stopped / Error
✓ Real-time updates

Controls:
✓ Restart thread
✓ Start thread
✓ Stop thread
✓ No SSH needed
```

### API Endpoints
```bash
# Get status
GET /api/threads

# Restart
POST /api/threads/sensor_reader/restart

# Start
POST /api/threads/database_writer/start

# Stop
POST /api/threads/heating_control/stop
```

---

## 🚀 Quick Start

### Installation
```bash
git clone <repo>
cd filamentenvmonitor
git checkout v2.0-rc
sudo ./install/install.sh
```

### Migration
```bash
cd /opt/filamentcontrol
git checkout v2.0-rc
sudo ./install/setup.sh
# SAVE THE KEY!
```

### Access
```bash
# Web UI
http://localhost:5000

# Config Tool
python scripts/config_tool.py

# Logs
sudo journalctl -u filamentbox.service -f
```

---

## ⚠️ Breaking Changes

### Must Migrate
```
✗ config.yaml     → config.db
✗ .env            → config.db
✓ All auto        → 15 min
```

### Must Save
```
⚠️ Encryption key (displayed once!)
   Save to:
   - Password manager
   - HashiCorp Vault
   - Secure notes
   - Paper backup
```

### Must Update
```
Service files auto-regenerated
Manual edits will be lost
Re-run setup to regenerate
```

---

## 📚 Documentation

### Read First
- [V2.0 Features](docs/V2.0_FEATURES_SUMMARY.md)
- [Migration Guide](docs/MIGRATION_GUIDE_V2.md)
- [Breaking Changes](docs/BREAKING_CHANGES_V2.md)

### Reference
- [README.md](README.md) - Overview
- [CHANGELOG.md](CHANGELOG.md) - Detailed history
- [Vault Integration](docs/VAULT_INTEGRATION.md)
- [React Web UI](webui/webui-react/README_REACT.md)

---

## 🐛 Common Issues

### Service Won't Start
```bash
# Check key file
ls -la .config_key

# Add to service
sudo nano /etc/systemd/system/filamentbox.service
Environment="FILAMENTBOX_CONFIG_KEY=key"

sudo systemctl daemon-reload
sudo systemctl start filamentbox.service
```

### Config Missing
```bash
# Restore from backup
ls config_backup_*
cp config_backup_*/config.yaml .
python scripts/migrate_config.py
```

### Web UI Not Loading
```bash
# Check service
sudo systemctl status filamentbox-webui.service

# Rebuild React
cd webui/webui-react
npm install && npm run build
```

---

## 🎯 Key Features Summary

### Top 5 User-Facing
1. **React PWA** - Modern installable web app
2. **Real-Time SSE** - Instant updates, no polling
3. **Notifications** - Browser alerts + in-app panel
4. **Dark Mode** - OS integration, persistent
5. **Hot-Reload** - Config changes without restart

### Top 5 Technical
1. **Encrypted Config** - 256-bit AES, no plain text
2. **Multi-Database** - 7 backends, easy switching
3. **Orchestrator** - Centralized thread management
4. **Vault Integration** - Enterprise key management
5. **Tag Support** - Universal across all databases

---

## 📊 Migration Checklist

### Pre-Migration
- [ ] Backup config files
- [ ] Note database settings
- [ ] Check disk space
- [ ] Schedule downtime (5 min)

### Migration
- [ ] Stop services
- [ ] Pull v2.0 code
- [ ] Run setup script
- [ ] **Save encryption key!**
- [ ] Start services

### Post-Migration
- [ ] Test web UI
- [ ] Verify sensor readings
- [ ] Check database writes
- [ ] Test controls
- [ ] Enable notifications

---

## 🔑 Encryption Key

### Where Stored
```
1. ENV VAR    (highest priority)
2. VAULT      (enterprise)
3. FILE       (.config_key)
4. DEFAULT    (dev only)
```

### How to Save
```
✓ Password manager (recommended)
✓ Vault (for teams)
✓ Encrypted backup
✓ Paper in safe
```

### Recovery
```
✗ Cannot decrypt without key
✓ Can re-migrate from backup
✓ Can reconfigure from scratch
```

---

## 🚀 What's New Summary

```
Modern Web:
  ✓ React PWA
  ✓ SSE updates
  ✓ Notifications
  ✓ Dark mode

Security:
  ✓ Encrypted config
  ✓ Auto-gen keys
  ✓ Vault support
  ✓ No plain text

Database:
  ✓ 7 backends
  ✓ Abstraction layer
  ✓ Universal tags
  ✓ Easy switching

Operations:
  ✓ Hot-reload
  ✓ Thread control
  ✓ Orchestrator
  ✓ Remote management
```

---

## 📞 Get Help

**Docs**: `/docs` folder  
**Issues**: GitHub Issues  
**Logs**: `sudo journalctl -u filamentbox.service`

**Before Asking**:
1. Check logs
2. Verify key exists
3. Test config tool
4. Search existing issues

---

## ✅ Success Criteria

Your migration succeeds when:
```
✓ Services running
✓ Config accessible
✓ Sensor reading
✓ Database writing
✓ Web UI working
✓ Updates real-time
✓ Controls working
✓ Notifications enabled
✓ Dark mode toggles
✓ Key saved securely
```

---

**v2.0: Built for Security, Speed, and Modern UX** 🚀

*Keep this card handy during migration!*

---

*Version: 2.0.0-rc*  
*Updated: 2025-01-10*
