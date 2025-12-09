# FilamentBox Web UI Deployment Guide

This guide covers deploying the FilamentBox Web UI as a systemd service with optional nginx reverse proxy.

## Quick Start

### 1. Install Web UI Service

```bash
sudo ./install_webui_service.sh
```

This will:
- Check for Flask dependencies and install if needed
- Install the systemd service file
- Enable the service to start on boot
- Optionally start the service immediately

### 2. Access Web UI

Direct access (without nginx):
```
http://YOUR_PI_IP:5000
```

## Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start filamentbox-webui.service

# Stop service
sudo systemctl stop filamentbox-webui.service

# Restart service
sudo systemctl restart filamentbox-webui.service

# Check status
sudo systemctl status filamentbox-webui.service

# View logs
sudo journalctl -u filamentbox-webui.service -f

# View last 100 lines
sudo journalctl -u filamentbox-webui.service -n 100
```

### Enable/Disable Auto-start

```bash
# Enable (start on boot)
sudo systemctl enable filamentbox-webui.service

# Disable (don't start on boot)
sudo systemctl disable filamentbox-webui.service
```

## Nginx Reverse Proxy Setup

Using nginx as a reverse proxy provides several benefits:
- Standard HTTP/HTTPS ports (80/443)
- SSL/TLS encryption support
- Better performance and caching
- Access control and authentication options

### Installation

1. **Install nginx**:
```bash
sudo apt update
sudo apt install nginx
```

2. **Copy configuration file**:
```bash
sudo cp nginx-filamentbox.conf /etc/nginx/sites-available/filamentbox
```

3. **Edit configuration**:
```bash
sudo nano /etc/nginx/sites-available/filamentbox
```

Update the `server_name` directive to match your hostname or IP address:
```nginx
server_name your-hostname.local;  # or your IP address
```

4. **Enable the site**:
```bash
sudo ln -s /etc/nginx/sites-available/filamentbox /etc/nginx/sites-enabled/
```

5. **Test nginx configuration**:
```bash
sudo nginx -t
```

6. **Reload nginx**:
```bash
sudo systemctl reload nginx
```

7. **Access via nginx**:
```
http://your-hostname.local
# or
http://YOUR_PI_IP
```

### HTTPS/SSL Configuration

To enable HTTPS (recommended for production):

1. **Generate self-signed certificate** (for testing):
```bash
sudo mkdir -p /etc/ssl/private
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/filamentbox.key \
    -out /etc/ssl/certs/filamentbox.crt
```

2. **Or use Let's Encrypt** (for production with domain name):
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

3. **Uncomment HTTPS section** in `/etc/nginx/sites-available/filamentbox`:
```bash
sudo nano /etc/nginx/sites-available/filamentbox
```
Uncomment the HTTPS server block and HTTP redirect section.

4. **Update certificate paths** if needed:
```nginx
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

5. **Reload nginx**:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Firewall Configuration

If using UFW firewall:

```bash
# Allow nginx (HTTP and HTTPS)
sudo ufw allow 'Nginx Full'

# Or allow only HTTP
sudo ufw allow 'Nginx HTTP'

# Or allow only HTTPS
sudo ufw allow 'Nginx HTTPS'

# If not using nginx, allow Flask directly
sudo ufw allow 5000/tcp
```

## Troubleshooting

### Web UI not accessible

1. **Check if service is running**:
```bash
sudo systemctl status filamentbox-webui.service
```

2. **Check if main application is running**:
```bash
sudo systemctl status filamentbox.service
```

3. **Check logs**:
```bash
sudo journalctl -u filamentbox-webui.service -n 50
```

4. **Test Flask directly**:
```bash
curl http://localhost:5000/api/status
```

### Nginx issues

1. **Check nginx status**:
```bash
sudo systemctl status nginx
```

2. **Check nginx error logs**:
```bash
sudo tail -f /var/log/nginx/filamentbox-error.log
```

3. **Test configuration**:
```bash
sudo nginx -t
```

4. **Verify proxy is working**:
```bash
curl -I http://localhost/api/status
```

### Permission issues

The web UI service runs as root to access shared state with the main application. If you need to run as a different user:

1. Edit the service file:
```bash
sudo nano /etc/systemd/system/filamentbox-webui.service
```

2. Change `User` and `Group` directives

3. Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart filamentbox-webui.service
```

### Port already in use

If port 5000 is already in use, you can change it:

1. Edit `webui_server.py`:
```python
app.run(host="0.0.0.0", port=5001, debug=False)  # Change port
```

2. Update nginx configuration if using reverse proxy:
```nginx
proxy_pass http://127.0.0.1:5001;  # Update port
```

## Security Considerations

1. **Firewall**: Only expose necessary ports
2. **HTTPS**: Use SSL/TLS for production deployments
3. **Authentication**: Consider adding nginx basic auth or application-level authentication
4. **Network**: Restrict access to trusted networks if possible
5. **Updates**: Keep Flask, nginx, and system packages updated

### Adding Basic Authentication (nginx)

1. Install apache2-utils:
```bash
sudo apt install apache2-utils
```

2. Create password file:
```bash
sudo htpasswd -c /etc/nginx/.htpasswd username
```

3. Add to nginx configuration:
```nginx
location / {
    auth_basic "FilamentBox Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://127.0.0.1:5000;
    # ... rest of proxy configuration
}
```

4. Reload nginx:
```bash
sudo systemctl reload nginx
```

## Advanced Configuration

### Custom Port Configuration

Edit `/etc/systemd/system/filamentbox-webui.service`:
```ini
[Service]
Environment="FLASK_RUN_PORT=5001"
```

### Multiple Instances

To run multiple instances on different ports:

1. Copy and modify service file
2. Update port in each instance
3. Configure nginx to proxy to different backends

### Monitoring

Add monitoring with systemd:
```bash
# Watch service status
watch -n 1 systemctl status filamentbox-webui.service

# Monitor resource usage
systemd-cgtop
```

## Uninstallation

To remove the web UI service:

```bash
# Stop and disable service
sudo systemctl stop filamentbox-webui.service
sudo systemctl disable filamentbox-webui.service

# Remove service file
sudo rm /etc/systemd/system/filamentbox-webui.service

# Remove nginx configuration (if installed)
sudo rm /etc/nginx/sites-enabled/filamentbox
sudo rm /etc/nginx/sites-available/filamentbox

# Reload systemd
sudo systemctl daemon-reload

# Reload nginx (if installed)
sudo systemctl reload nginx
```
