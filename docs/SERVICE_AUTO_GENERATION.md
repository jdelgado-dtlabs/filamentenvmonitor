# Systemd Service Auto-Generation

**FSEM v2.0+ - Automated Service File Generation**

FSEM v2.0+ automatically generates systemd service files configured for your environment during setup.

## How It Works

When you run `./install/setup.sh`, the script:

1. **Detects Installation Path**: Automatically determines where FSEM is installed
2. **Detects User/Group**: Uses the current user and group for service execution
3. **Detects Vault Configuration**: Checks if HashiCorp Vault environment variables are set
4. **Generates Service Files**: Creates `filamentbox.service` and `filamentbox.service (webui integrated in v2.0)`
5. **Configures Appropriately**:
   - **With Vault**: Embeds Vault environment variables in service files
   - **Without Vault**: Services will automatically use local `.config_key` file

## Dynamic Configuration

The generated service files are customized based on your setup:

- **Installation Path**: Automatically uses the actual installation directory (not hardcoded)
- **User/Group**: Uses the user who ran setup (or SUDO_USER if run with sudo)
- **Vault Integration**: Includes Vault configuration if available
- **Portable**: Works regardless of installation location

## Generated Service Files

### Location
```
<installation-path>/install/filamentbox.service
<installation-path>/install/filamentbox.service (webui integrated in v2.0)
```

For example:
- `/opt/filamentcontrol/install/filamentbox.service`
- `/home/user/myapp/install/filamentbox.service`

### With Vault Support

When Vault is configured during setup, the service files include:

```ini
[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/filamentcontrol
Environment="PATH=/opt/filamentcontrol/filamentcontrol/bin"

# HashiCorp Vault configuration for encryption key
Environment="VAULT_ADDR=https://vault.example.com:8200"
Environment="VAULT_TOKEN=your-token"
# OR
Environment="VAULT_ROLE_ID=your-role-id"
Environment="VAULT_SECRET_ID=your-secret-id"

ExecStart=/opt/filamentcontrol/filamentcontrol/bin/python /opt/filamentcontrol/run_filamentbox.py
```

### Without Vault (Local File Mode)

When Vault is not configured, service files are generated without Vault variables:

```ini
[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/filamentcontrol
Environment="PATH=/opt/filamentcontrol/filamentcontrol/bin"

# No Vault configuration - will use local .config_key file
ExecStart=/opt/filamentcontrol/filamentcontrol/bin/python /opt/filamentcontrol/run_filamentbox.py
```

The application automatically loads the key from `/opt/filamentcontrol/.config_key`.

## Installation Flow

1. **Run Setup**:
   ```bash
   ./install/setup.sh
   ```

2. **Answer Vault Questions**:
   - "Do you have a HashiCorp Vault server available?"
   - If yes: provide Vault details
   - If no: local file mode

3. **Service Files Generated Automatically**:
   - Setup script creates service files with appropriate configuration
   - No manual editing required

4. **Install Services**:
   ```bash
   sudo ./install/install_service.sh
   sudo ./install/install_webui_service.sh
   ```

## Portable Installation Support

FilamentBox supports installation in any directory. The service files are automatically configured for your installation path.

### Example Installations

**Standard Installation:**
```bash
cd /opt/filamentcontrol
./install/setup.sh
# Services configured for /opt/filamentcontrol
```

**Home Directory Installation:**
```bash
cd /home/myuser/filamentbox
./install/setup.sh
# Services configured for /home/myuser/filamentbox
```

**Custom Location:**
```bash
cd /srv/monitoring/filamentbox
./install/setup.sh
# Services configured for /srv/monitoring/filamentbox
```

### What Gets Configured

For an installation at `/home/pi/filamentbox`, the service file will contain:

```ini
[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/filamentbox
Environment="PATH=/home/pi/filamentbox/filamentcontrol/bin"
ExecStart=/home/pi/filamentbox/filamentcontrol/bin/python /home/pi/filamentbox/run_filamentbox.py

# Security
ReadWritePaths=/home/pi/filamentbox
```

All paths are dynamically configured - no hardcoded `/opt/filamentcontrol` paths.

## Regenerating Service Files

If you change your Vault configuration or want to regenerate service files:

1. **Delete existing service files**:
   ```bash
   rm install/filamentbox.service install/filamentbox.service (webui integrated in v2.0)
   ```

2. **Run setup again**:
   ```bash
   ./install/setup.sh
   ```

The setup script will detect the existing configuration database and regenerate service files based on current Vault environment variables.

## Manual Service File Updates

If you need to manually update Vault credentials in service files:

### Option 1: Regenerate (Recommended)
```bash
rm install/*.service
./install/setup.sh
```

### Option 2: Edit Directly
```bash
# Edit service files
nano install/filamentbox.service
nano install/filamentbox.service (webui integrated in v2.0)

# Reinstall
sudo ./install/install_service.sh
sudo ./install/install_webui_service.sh

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart filamentbox
sudo systemctl restart filamentbox (webui integrated in v2.0)
```

## Vault Credential Rotation

When rotating Vault AppRole credentials:

1. **Update environment variables**:
   ```bash
   export VAULT_SECRET_ID='new-secret-id'
   ```

2. **Regenerate service files**:
   ```bash
   rm install/*.service
   ./install/setup.sh
   ```

3. **Reinstall services**:
   ```bash
   sudo ./install/install_service.sh
   sudo ./install/install_webui_service.sh
   sudo systemctl daemon-reload
   sudo systemctl restart filamentbox filamentbox (webui integrated in v2.0)
   ```

## Security Considerations

### Vault Token in Service Files

When using token authentication, the token is stored in plain text in the service file at `/etc/systemd/system/filamentbox.service`.

**Security measures:**
- Service files are owned by root with 644 permissions
- Only root can modify service files
- Tokens should have limited TTL and be rotated regularly
- AppRole authentication is more secure for production

### AppRole Secrets

AppRole Secret IDs in service files should be:
- Treated as sensitive credentials
- Rotated periodically
- Generated with limited TTL
- Monitored via Vault audit logs

### Best Practices

1. **Use AppRole** instead of tokens for production
2. **Set short TTLs** on tokens and Secret IDs
3. **Rotate credentials** regularly
4. **Monitor access** via Vault audit logs
5. **Keep local backup** - `.config_key` file is always created as fallback

## Troubleshooting

### Service fails to start

**Check logs:**
```bash
sudo journalctl -u filamentbox -n 50
```

**Common issues:**
- Vault server unreachable: Service falls back to local key file
- Invalid credentials: Check Vault environment variables
- Missing key file: Run setup.sh to create it

### Vault connection errors

Service will automatically fall back to local `.config_key` file if Vault is unavailable. Check logs:

```bash
# Should see: "Using encryption key from local file"
sudo journalctl -u filamentbox | grep -i "key\|vault"
```

### Update Vault configuration

If Vault configuration changes (new server, new credentials):

1. Stop services
2. Update environment variables
3. Regenerate service files
4. Reinstall services
5. Restart services

## Advantages of Auto-Generation

✅ **No manual editing**: Service files configured automatically  
✅ **Vault integration**: Seamlessly includes Vault credentials  
✅ **Fallback support**: Always creates local key file as backup  
✅ **Consistent configuration**: Setup and services use same Vault settings  
✅ **Easy updates**: Simply regenerate when configuration changes  
✅ **Security**: Credentials flow from secure setup process  

## See Also

- [Vault Integration Guide](./VAULT_INTEGRATION.md)
- [Encryption Key Security](./ENCRYPTION_KEY_SECURITY.md)
- Service installation scripts in `/opt/filamentcontrol/install/`
