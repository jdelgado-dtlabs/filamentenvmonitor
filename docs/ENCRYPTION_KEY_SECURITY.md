# FilamentBox Encryption Key Security

## Overview

FilamentBox v2.0+ uses encrypted configuration with SQLCipher. The encryption key is automatically generated during setup and stored securely in HashiCorp Vault (if available) or a local encrypted file.

## Key Generation

During initial setup, the `install/setup.sh` script automatically generates a strong 64-character random encryption key using `/dev/urandom`. The key is:
- Cryptographically secure random data
- Base64 encoded for safe storage
- 64 characters long (384 bits of entropy)
- Displayed on screen for you to copy and backup
- Saved to HashiCorp Vault (if configured) and/or `.config_key` file

**IMPORTANT:** When the key is displayed during setup, copy it to a secure location (password manager, encrypted vault) before continuing.

## Key Storage Options

### HashiCorp Vault (Recommended for Production)

If HashiCorp Vault is configured, the encryption key is stored in Vault at:
```
secret/data/filamentbox/config_key
```

**Benefits:**
- Centralized secret management
- Audit logging of key access
- Dynamic secret rotation support
- Enterprise-grade security
- No local file storage required

**Requirements:**
- `hvac` Python library: `pip install hvac`
- Vault server accessible via `VAULT_ADDR`
- Valid authentication (token or AppRole)

**Configuration:** See [HashiCorp Vault Setup](#hashicorp-vault-setup) below.

### Local File (Automatic Fallback)

The encryption key is also stored in:
```
/opt/filamentcontrol/.config_key
```

**Permissions:** `600` (owner read/write only)

**Use cases:**
- Development environments
- Standalone deployments
- Backup if Vault is temporarily unavailable

## Key Loading Priority

The application loads the encryption key in the following order:

1. **Environment Variable** (highest priority)
   ```bash
   export FILAMENTBOX_CONFIG_KEY='your-encryption-key'
   ```

2. **HashiCorp Vault** (if configured)
   - Requires `VAULT_ADDR` and authentication credentials
   - Automatic retry with exponential backoff

3. **Local Key File** (automatic fallback)
   ```
   /opt/filamentcontrol/.config_key
   ```

4. **Default Key** (development only - warning logged)
   - Only used if no other source is available
   - Should never be used in production

## HashiCorp Vault Setup

### Quick Start

Use the configuration helper script:
```bash
./scripts/configure_vault.sh
```

This interactive script will:
1. Install `hvac` library if needed
2. Prompt for Vault server address
3. Configure authentication (Token or AppRole)
4. Generate environment variable exports

### Manual Configuration

#### 1. Install hvac Library
```bash
pip install hvac
```

#### 2. Set Environment Variables

**Token Authentication (Simple):**
```bash
export VAULT_ADDR='https://vault.example.com:8200'
export VAULT_TOKEN='your-vault-token'
```

**AppRole Authentication (Recommended for Production):**
```bash
export VAULT_ADDR='https://vault.example.com:8200'
export VAULT_ROLE_ID='your-role-id'
export VAULT_SECRET_ID='your-secret-id'
```

**Vault Enterprise with Namespace:**
```bash
export VAULT_NAMESPACE='your-namespace'
```

#### 3. Run Setup

Once Vault is configured, run the setup script:
```bash
./install/setup.sh
```

The encryption key will be automatically saved to both Vault and the local file (as backup).

### Vault Policy Requirements

The FilamentBox service needs the following Vault policy:

```hcl
# Policy for FilamentBox encryption key access
path "secret/data/filamentbox/config_key" {
  capabilities = ["read", "create", "update"]
}

path "secret/metadata/filamentbox/config_key" {
  capabilities = ["read", "list"]
}
```

Apply the policy:
```bash
vault policy write filamentbox-config filamentbox-policy.hcl
```

### Creating AppRole for Production

```bash
# Enable AppRole auth method
vault auth enable approle

# Create role
vault write auth/approle/role/filamentbox \
    token_policies="filamentbox-config" \
    token_ttl=1h \
    token_max_ttl=24h

# Get Role ID
vault read auth/approle/role/filamentbox/role-id

# Generate Secret ID
vault write -f auth/approle/role/filamentbox/secret-id
```

## For Service/Daemon Usage

### Option 1: Automatic with Vault (Recommended)

The application automatically retrieves the key from Vault - no additional configuration needed if Vault environment variables are set.

**Systemd Example:**
```ini
[Service]
Environment="VAULT_ADDR=https://vault.example.com:8200"
Environment="VAULT_ROLE_ID=your-role-id"
Environment="VAULT_SECRET_ID=your-secret-id"
ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
```

### Option 2: Automatic with Local File

The application automatically reads from `.config_key` file - no additional configuration needed.

### Option 3: Source Key Loading Script

Source the helper script in your service startup:

```bash
# In your service startup script
source /opt/filamentcontrol/scripts/load_config_key.sh
```

### Option 4: Systemd Service with EnvironmentFile

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
