# FilamentBox Encryption Key Security

## Overview

FilamentBox v2.0+ uses encrypted configuration with SQLCipher. The encryption key is automatically generated during setup and stored securely.

## Key Generation

During initial setup, the `install/setup.sh` script automatically generates a strong 64-character random encryption key using `/dev/urandom`. The key is:
- Cryptographically secure random data
- Base64 encoded for safe storage
- 64 characters long (384 bits of entropy)
- Displayed on screen for you to copy and backup
- Saved to `.config_key` file with restrictive permissions

**IMPORTANT:** When the key is displayed during setup, copy it to a secure location (password manager, encrypted vault) before continuing.

## Key Storage Location

The encryption key is stored in:
```
/opt/filamentcontrol/.config_key
```

**Permissions:** `600` (owner read/write only)

## Key Loading Priority

The application loads the encryption key in the following order:

1. **Environment Variable** (highest priority)
   ```bash
   export FILAMENTBOX_CONFIG_KEY='your-encryption-key'
   ```

2. **Key File** (automatic fallback)
   ```
   /opt/filamentcontrol/.config_key
   ```

3. **Default Key** (development only - warning logged)
   - Only used if neither environment variable nor key file is found
   - Should never be used in production

## For Service/Daemon Usage

### Option 1: Automatic (Recommended)

The application automatically reads from `.config_key` file - no additional configuration needed.

### Option 2: Source Key Loading Script

Source the helper script in your service startup:

```bash
# In your service startup script
source /opt/filamentcontrol/scripts/load_config_key.sh
```

### Option 3: Systemd Service with EnvironmentFile

Create `/etc/filamentbox/config.env`:
```bash
FILAMENTBOX_CONFIG_KEY=your-encryption-key
```

Set permissions:
```bash
sudo chmod 600 /etc/filamentbox/config.env
sudo chown filamentbox:filamentbox /etc/filamentbox/config.env
```

Reference in systemd service:
```ini
[Service]
EnvironmentFile=/etc/filamentbox/config.env
ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
```

### Option 4: Systemd Service with Environment Variable

Directly in systemd service file:
```ini
[Service]
Environment="FILAMENTBOX_CONFIG_KEY=your-encryption-key"
ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
```

**Note:** This method stores the key in plain text in the service file.

## Security Best Practices

1. **File Permissions**: Always keep `.config_key` with `600` permissions
2. **Backup**: Store key backup in secure location (password manager, encrypted vault)
3. **Environment Variables**: Preferred for containerized environments
4. **Key File**: Preferred for bare metal/VM deployments
5. **Never commit**: Add `.config_key` to `.gitignore`

## Key Management

### View Current Key Location

```bash
cd /opt/filamentcontrol
python -c "from filamentbox.config_db import _load_encryption_key; print(_load_encryption_key()[:8] + '...')"
```

### Change Encryption Key

⚠️ **Warning**: Changing the key requires re-encrypting the database.

1. Backup current configuration:
   ```bash
   cp filamentbox_config.db filamentbox_config.db.backup
   ```

2. Export current configuration:
   ```bash
   python scripts/config_tool.py --list > config_backup.txt
   ```

3. Create new key and database:
   ```bash
   mv .config_key .config_key.old
   mv filamentbox_config.db filamentbox_config.db.old
   ./install/setup.sh
   ```

4. Manually re-enter configuration values

### Rotate Key (Advanced)

For automated key rotation, you'll need to:
1. Decrypt database with old key
2. Re-encrypt with new key
3. Update `.config_key` file

## Troubleshooting

### "Wrong encryption key" error

**Cause**: The key in environment/file doesn't match the database encryption.

**Solution**:
1. Verify you're using the correct key
2. Check if `.config_key` file is readable
3. Restore from backup if key is lost

### Key file not found

**Cause**: Setup script not run or key file deleted.

**Solution**:
```bash
cd /opt/filamentcontrol
./install/setup.sh
```

### Permission denied reading key file

**Cause**: Incorrect file permissions or ownership.

**Solution**:
```bash
sudo chown $USER:$USER /opt/filamentcontrol/.config_key
chmod 600 /opt/filamentcontrol/.config_key
```

## Recovery

If you lose your encryption key:
- **There is NO way to recover the encrypted configuration**
- You must create a new configuration database from scratch
- This is why backup of the key is critical

Always keep a secure backup of:
1. `.config_key` file
2. Exported configuration (plain text backup)
