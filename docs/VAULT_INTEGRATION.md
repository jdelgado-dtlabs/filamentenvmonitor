# HashiCorp Vault Integration - Quick Start

This guide shows how to integrate FilamentBox with HashiCorp Vault for secure encryption key storage.

## Why Use Vault?

- **Centralized Secret Management**: Store all secrets in one place
- **Audit Logging**: Track who accessed the encryption key
- **Access Control**: Fine-grained permissions via policies
- **Dynamic Secrets**: Support for key rotation
- **High Availability**: Enterprise-grade reliability

## Prerequisites

1. HashiCorp Vault server (running and accessible)
2. Vault authentication credentials (token or AppRole)
3. Network connectivity to Vault server

## Quick Setup

### Step 1: Install hvac Library

```bash
pip install hvac
```

Or uncomment in `requirements.txt`:
```
hvac>=2.0.0
```

### Step 2: Configure Vault Access

Use the interactive configuration script:

```bash
./scripts/configure_vault.sh
```

This will guide you through:
- Vault server address
- Authentication method (Token or AppRole)
- Environment variable setup

### Step 3: Set Environment Variables

**For Token Authentication:**
```bash
export VAULT_ADDR='https://vault.example.com:8200'
export VAULT_TOKEN='your-vault-token'
```

**For AppRole Authentication (Recommended):**
```bash
export VAULT_ADDR='https://vault.example.com:8200'
export VAULT_ROLE_ID='your-role-id'
export VAULT_SECRET_ID='your-secret-id'
```

### Step 4: Run Setup

```bash
./install/setup.sh
```

The encryption key will be automatically:
1. Generated (64-character random key)
2. Displayed for you to backup
3. Saved to Vault at `secret/data/filamentbox/config_key`
4. Saved to local file (as backup fallback)

## Vault Configuration

### Required Policy

Create a policy file `filamentbox-policy.hcl`:

```hcl
# Read and write access to FilamentBox encryption key
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

### AppRole Setup (Production)

```bash
# Enable AppRole auth
vault auth enable approle

# Create role with policy
vault write auth/approle/role/filamentbox \
    token_policies="filamentbox-config" \
    token_ttl=1h \
    token_max_ttl=24h

# Get Role ID (save this)
vault read auth/approle/role/filamentbox/role-id

# Generate Secret ID (save this)
vault write -f auth/approle/role/filamentbox/secret-id
```

## Systemd Service Configuration

### Option 1: Environment Variables in Service File

```ini
[Unit]
Description=Filament Storage Environmental Manager
After=network.target

[Service]
Type=simple
User=filamentbox
WorkingDirectory=/opt/filamentcontrol

# Vault configuration
Environment="VAULT_ADDR=https://vault.example.com:8200"
Environment="VAULT_ROLE_ID=your-role-id"
Environment="VAULT_SECRET_ID=your-secret-id"

ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Option 2: Environment File

Create `/etc/filamentbox/vault.env`:
```bash
VAULT_ADDR=https://vault.example.com:8200
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id
```

Set permissions:
```bash
sudo chmod 600 /etc/filamentbox/vault.env
sudo chown filamentbox:filamentbox /etc/filamentbox/vault.env
```

Update service file:
```ini
[Service]
EnvironmentFile=/etc/filamentbox/vault.env
ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
```

## Key Loading Behavior

FilamentBox loads the encryption key in this order:

1. **FILAMENTBOX_CONFIG_KEY** environment variable
2. **HashiCorp Vault** (if configured with VAULT_ADDR + auth)
3. **Local file** `.config_key` (fallback)
4. **Default key** (development only - logs warning)

This ensures:
- Vault is used when available
- Graceful fallback if Vault is temporarily unavailable
- No service interruption during Vault maintenance

## Verification

Test Vault connectivity:

```bash
# Export Vault variables
export VAULT_ADDR='https://vault.example.com:8200'
export VAULT_TOKEN='your-token'

# Test Python Vault client
python -c "
import os
import sys
sys.path.insert(0, '/opt/filamentcontrol')
from filamentbox.config_db import _get_vault_client

client = _get_vault_client()
if client and client.is_authenticated():
    print('✓ Vault connection successful')
else:
    print('✗ Vault connection failed')
"
```

## Troubleshooting

### "Vault: Failed to initialize client"

**Cause**: Network connectivity or authentication issue

**Solutions**:
1. Verify `VAULT_ADDR` is correct and reachable
2. Check firewall rules
3. Validate token/AppRole credentials
4. Check Vault server logs

### "Vault: Failed to read encryption key"

**Cause**: Key doesn't exist in Vault or permission denied

**Solutions**:
1. Run `install/setup.sh` to create the key
2. Verify Vault policy allows read access
3. Check the key path: `secret/data/filamentbox/config_key`

### Application falls back to local file

**Cause**: Vault unavailable or misconfigured (not an error)

**Behavior**: Application automatically uses `.config_key` file

**Action**: Fix Vault configuration if you want to use Vault, otherwise no action needed

## Migration from Local File to Vault

If you already have a local `.config_key` file:

1. Set up Vault environment variables
2. Read the existing key:
   ```bash
   EXISTING_KEY=$(cat /opt/filamentcontrol/.config_key)
   ```

3. Save to Vault using Python:
   ```python
   import os
   import sys
   sys.path.insert(0, '/opt/filamentcontrol')
   
   os.environ['VAULT_ADDR'] = 'https://vault.example.com:8200'
   os.environ['VAULT_TOKEN'] = 'your-token'
   
   from filamentbox.config_db import _save_key_to_vault
   
   key = open('/opt/filamentcontrol/.config_key').read().strip()
   if _save_key_to_vault(key):
       print('✓ Key migrated to Vault')
   else:
       print('✗ Failed to migrate key')
   ```

4. Keep `.config_key` as backup

## Best Practices

1. **Use AppRole** instead of tokens for production
2. **Set short TTLs** on tokens (1-24 hours)
3. **Enable audit logging** in Vault
4. **Keep local backup** - don't delete `.config_key`
5. **Monitor Vault access** via audit logs
6. **Use TLS** for Vault communication
7. **Rotate AppRole secrets** periodically

## Security Considerations

- **Network Security**: Use TLS for Vault communication
- **Authentication**: AppRole is more secure than static tokens
- **Audit**: Enable Vault audit logging to track key access
- **Backup**: Always keep encrypted backup of the key
- **Least Privilege**: Grant minimal permissions needed
- **Secret Zero Problem**: Protect AppRole credentials carefully

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [hvac Python Client](https://hvac.readthedocs.io/)
- [Vault AppRole Auth](https://www.vaultproject.io/docs/auth/approle)
- [FilamentBox Encryption Key Security](./ENCRYPTION_KEY_SECURITY.md)
