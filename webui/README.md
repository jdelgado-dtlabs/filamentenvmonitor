# FilamentBox Web UI

A modern, responsive web interface for monitoring and controlling the FilamentBox environment system.

## Features

- 📊 Real-time sensor readings (temperature and humidity)
- 🔥 Heater control with manual override
- 💨 Fan control with manual override
- 🎨 Clean, modern UI with responsive design
- 🔄 Auto-refresh every 2 seconds
- 📱 Mobile-friendly layout

## Architecture

- **Frontend**: Vanilla HTML/CSS/JavaScript (no build tools required)
- **Backend**: Flask REST API server
- **Data**: Shared state with main monitoring application

## Running the Web UI

### Quick Start (Development)

Install Flask and Flask-CORS:

```bash
source filamentcontrol/bin/activate
pip install Flask Flask-CORS
```

Start the server:

```bash
# Make sure the main application is running first
python -m filamentbox.main

# In another terminal, start the web server
source filamentcontrol/bin/activate
python webui_server.py
```

The web interface will be available at: `http://localhost:5000`

Or from other devices on your network: `http://YOUR_PI_IP:5000`

### Production Deployment

For production use with systemd and optional nginx reverse proxy:

```bash
# Install as systemd service
sudo ./install_webui_service.sh

# Access directly
http://YOUR_PI_IP:5000

# Or configure nginx reverse proxy (see WEBUI_DEPLOYMENT.md)
http://YOUR_PI_IP
```

See [WEBUI_DEPLOYMENT.md](../WEBUI_DEPLOYMENT.md) for complete deployment documentation including:
- Systemd service installation and management
- Nginx reverse proxy configuration
- HTTPS/SSL setup
- Firewall configuration
- Troubleshooting guide

## API Endpoints

### GET /api/sensor
Returns current sensor readings:
```json
{
  "temperature_c": 22.5,
  "temperature_f": 72.5,
  "humidity": 45.2,
  "timestamp": 1702123456.789,
  "age": 2.5
}
```

### GET /api/controls
Returns control states:
```json
{
  "heater": {
    "on": true,
    "manual": null,
    "mode": "auto"
  },
  "fan": {
    "on": false,
    "manual": null,
    "mode": "auto"
  }
}
```

### GET /api/status
Returns combined sensor and control data.

### POST /api/controls/heater
Control heater state:
```json
{
  "state": true   // true = force ON, false = force OFF, null = auto
}
```

### POST /api/controls/fan
Control fan state:
```json
{
  "state": false   // true = force ON, false = force OFF, null = auto
}
```

## UI Controls

- **Turn ON**: Force device to turn on (manual mode)
- **Turn OFF**: Force device to turn off (manual mode)
- **Auto Mode**: Return device to automatic temperature/humidity control

## Security Note

The web server runs on `0.0.0.0:5000` by default, making it accessible from other devices on your network. For production use, consider:

- Running behind a reverse proxy (nginx/Apache)
- Adding authentication
- Using HTTPS
- Restricting access with firewall rules

## Troubleshooting

### Web UI shows "Loading data..." indefinitely
- Ensure the main application is running
- Check that both applications can access shared_state.py
- Verify no firewall is blocking port 5000

### Controls don't work
- Check browser console for errors
- Verify API endpoints are accessible: `curl http://localhost:5000/api/status`
- Ensure main application is running with proper GPIO permissions

### Data appears stale
- UI will dim cards when data is older than 10 seconds
- Check that main application is actively collecting data
- Verify sensor is connected and working
