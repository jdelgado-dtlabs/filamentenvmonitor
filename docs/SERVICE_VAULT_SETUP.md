# Using HashiCorp Vault with FilamentBox Services

## Overview

FilamentBox services automatically retrieve the encryption key from HashiCorp Vault when properly configured. No code changes needed - just set the appropriate environment variables.

## How It Works

When FilamentBox starts, it loads the encryption key in this priority order:

1. **FILAMENTBOX_CONFIG_KEY** environment variable (explicit override)
2. **HashiCorp Vault** (if VAULT_ADDR + auth credentials are set)
3. **Local file** `.config_key` (automatic fallback)
4. **Default key** (development only - logs warning)

This means your service will automatically use Vault when configured, with graceful fallback to local file if Vault is temporarily unavailable.

## Quick Setup for Systemd Services

### Step 1: Create Vault Environment File

Create `/etc/filamentbox/vault.env`:

```bash
sudo mkdir -p /etc/filamentbox
sudo nano /etc/filamentbox/vault.env
```

**For Token Authentication:**
```bash
VAULT_ADDR=https://vault.example.com:8200
VAULT_TOKEN=your-vault-token
```

**For AppRole Authentication (Recommended):**
```bash
VAULT_ADDR=https://vault.example.com:8200
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id
```

**For Vault Enterprise with Namespace:**
```bash
VAULT_ADDR=https://vault.example.com:8200
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id
VAULT_NAMESPACE=your-namespace
```

Set secure permissions:
```bash
sudo chmod 600 /etc/filamentbox/vault.env
sudo chown filamentbox:filamentbox /etc/filamentbox/vault.env
```

### Step 2: Configure Systemd Service

Copy the example service file:
```bash
sudo cp /opt/filamentcontrol/install/filamentbox.service.example /etc/systemd/system/filamentbox.service
```

Edit the service file:
```bash
sudo nano /etc/systemd/system/filamentbox.service
```

Uncomment the EnvironmentFile line:
```ini
[Service]
EnvironmentFile=/etc/filamentbox/vault.env
ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
```

### Step 3: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable filamentbox
sudo systemctl start filamentbox
```

### Step 4: Verify Vault Integration

Check the service logs to confirm Vault is being used:
```bash
sudo journalctl -u filamentbox -f
```

Look for log messages like:
```
INFO - Vault: Successfully retrieved encryption key
```

Or if Vault is unavailable (automatic fallback):
```
WARNING - Vault: Failed to read encryption key
INFO - Using encryption key from local file
```

## Alternative: Inline Environment Variables

Instead of using an environment file, you can set variables directly in the service file:

Edit `/etc/systemd/system/filamentbox.service`:

```ini
[Service]
Environment="VAULT_ADDR=https://vault.example.com:8200"
Environment="VAULT_ROLE_ID=your-role-id"
Environment="VAULT_SECRET_ID=your-secret-id"
ExecStart=/opt/filamentcontrol/filamentbox/bin/python /opt/filamentcontrol/filamentbox.py
```

**Note:** This stores credentials in the service file (less secure than environment file).

## Docker/Container Usage

### Docker Compose

```yaml
version: '3.8'

services:
  filamentbox:
    image: filamentbox:latest
    environment:
      - VAULT_ADDR=https://vault.example.com:8200
      - VAULT_ROLE_ID=${VAULT_ROLE_ID}
      - VAULT_SECRET_ID=${VAULT_SECRET_ID}
    # Or use env_file
    env_file:
      - /etc/filamentbox/vault.env
    volumes:
      - /opt/filamentcontrol:/app
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: filamentbox-vault-creds
type: Opaque
stringData:
  VAULT_ADDR: "https://vault.example.com:8200"
  VAULT_ROLE_ID: "your-role-id"
  VAULT_SECRET_ID: "your-secret-id"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filamentbox
spec:
  replicas: 1
  selector:
    matchLabels:
      app: filamentbox
  template:
    metadata:
      labels:
        app: filamentbox
    spec:
      containers:
      - name: filamentbox
        image: filamentbox:latest
        envFrom:
        - secretRef:
            name: filamentbox-vault-creds
```

Or use Vault Agent Injector for better security:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filamentbox
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "filamentbox"
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/filamentbox/config_key"
```

## Vault Configuration Requirements

### Required Policy

Your Vault policy must allow reading the encryption key:

```hcl
# Vault Policy for FilamentBox
path "secret/data/filamentbox/config_key" {
  capabilities = ["read"]
}

path "secret/metadata/filamentbox/config_key" {
  capabilities = ["read", "list"]
}
```

Apply the policy:
```bash
vault policy write filamentbox-service filamentbox-service.hcl
```

### AppRole Configuration

Create an AppRole for the service:

```bash
# Enable AppRole
vault auth enable approle

# Create role
vault write auth/approle/role/filamentbox-service \
    token_policies="filamentbox-service" \
    token_ttl=1h \
    token_max_ttl=24h \
    secret_id_ttl=0

# Get Role ID (save this)
vault read auth/approle/role/filamentbox-service/role-id

# Generate Secret ID (save this)
vault write -f auth/approle/role/filamentbox-service/secret-id
```

Use the Role ID and Secret ID in your service configuration.

## Monitoring and Troubleshooting

### Check Service Status

```bash
sudo systemctl status filamentbox
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u filamentbox -f

# Last 100 lines
sudo journalctl -u filamentbox -n 100

# Filter for Vault messages
sudo journalctl -u filamentbox | grep -i vault
```

### Common Issues

**Issue: "Vault: Failed to initialize client"**
- Check VAULT_ADDR is correct and reachable
- Verify network connectivity to Vault
- Check firewall rules

**Issue: "Vault: No valid authentication method found"**
- Ensure VAULT_TOKEN or (VAULT_ROLE_ID + VAULT_SECRET_ID) are set
- Verify credentials are correct
- Check Vault authentication is enabled

**Issue: "Vault: Failed to read encryption key"**
- Verify the key exists in Vault: `vault kv get secret/filamentbox/config_key`
- Check policy allows read access
- Ensure authentication token hasn't expired

**Issue: Service falls back to local file**
- This is expected behavior if Vault is unavailable
- Service continues to work using local backup
- Check Vault connectivity when convenient

## High Availability Considerations

### Vault Cluster

For production, use a Vault cluster:
```bash
VAULT_ADDR=https://vault-cluster.example.com:8200
```

The Vault cluster handles failover automatically.

### Multiple Services

All FilamentBox services can share the same Vault credentials:
- Same Role ID and Secret ID for all instances
- Vault handles concurrent access
- Centralized key management

### Token Renewal

For Token authentication, tokens may expire. Use AppRole for automatic renewal:
- AppRole tokens auto-renew before expiration
- Set appropriate TTL values
- Monitor token expiration in logs

## Security Best Practices

1. **Use AppRole** instead of tokens for service authentication
2. **Rotate Secret IDs** periodically
3. **Set short TTLs** (1-24 hours) for tokens
4. **Use TLS** for Vault communication
5. **Restrict permissions** - read-only access to encryption key
6. **Monitor access** via Vault audit logs
7. **Keep local backup** - don't delete `.config_key` file
8. **Secure env files** - 600 permissions, proper ownership
9. **Use namespaces** in Vault Enterprise for isolation
10. **Enable audit logging** to track key access

## Testing Vault Integration

Test Vault connectivity before starting the service:

```bash
# Set environment variables
export VAULT_ADDR=https://vault.example.com:8200
export VAULT_ROLE_ID=your-role-id
export VAULT_SECRET_ID=your-secret-id

# Test with Python
cd /opt/filamentcontrol
python -c "
import sys
import os
sys.path.insert(0, '.')
from filamentbox.config_db import _get_vault_client, _load_key_from_vault

# Test client
client = _get_vault_client()
if client and client.is_authenticated():
    print('✓ Vault authentication successful')
    
    # Test key retrieval
    key = _load_key_from_vault()
    if key:
        print(f'✓ Encryption key retrieved (length: {len(key)})')
    else:
        print('✗ Failed to retrieve encryption key')
else:
    print('✗ Vault authentication failed')
"
```

Expected output:
```
INFO:root:Vault: Authenticated using AppRole
✓ Vault authentication successful
INFO:root:Vault: Successfully retrieved encryption key
✓ Encryption key retrieved (length: 64)
```

## Migration: Local File to Vault for Running Services

If you have a running service using local file and want to migrate to Vault:

1. **Ensure key is in Vault** (setup.sh does this automatically)
2. **Add Vault environment variables** to service
3. **Reload systemd and restart service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart filamentbox
   ```
4. **Verify Vault is being used** in logs
5. **Keep local file as backup** - don't delete it

The service will automatically prefer Vault over local file.

## Benefits of Using Vault with Services

✅ **Centralized Management** - Update key in one place for all services
✅ **Audit Trail** - Track which services accessed the key and when
✅ **Access Control** - Fine-grained permissions per service
✅ **Automatic Rotation** - Support key rotation without service restarts
✅ **High Availability** - Vault cluster ensures key availability
✅ **Secrets Management** - Part of broader secrets strategy
✅ **Graceful Degradation** - Automatic fallback to local file
✅ **Zero Downtime** - Service continues if Vault temporarily unavailable

## References

- [FilamentBox Vault Integration](./VAULT_INTEGRATION.md)
- [Encryption Key Security](./ENCRYPTION_KEY_SECURITY.md)
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault AppRole Auth](https://www.vaultproject.io/docs/auth/approle)
- [Vault Agent Injector](https://www.vaultproject.io/docs/platform/k8s/injector)
