# FilamentBox React Web UI

Modern React-based Progressive Web App (PWA) for monitoring and controlling 3D printer filament storage.

## Features

- **Real-time Monitoring**: Live sensor data updates every 2 seconds
- **Control Interface**: Manage heater and fan controls with threshold adjustments
- **Configuration Editor**: Edit all settings with real-time validation
- **Progressive Web App**: Install as a mobile/desktop app
- **Offline Support**: Service worker caches for offline functionality
- **Responsive Design**: Works on desktop, tablet, and mobile

## Development

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Setup

```bash
cd /opt/filamentcontrol/webui/webui-react
npm install
```

### Development Server

Run the dev server with hot reload and API proxy:

```bash
npm run dev
```

The app will be available at `http://localhost:5173` and will proxy API requests to `http://localhost:5000`.

### Build for Production

```bash
npm run build
```

The production build will be created in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/          # React components
│   ├── Button.jsx      # Reusable button component
│   ├── Card.jsx        # Card container components
│   ├── ConfigEditor.jsx # Configuration editing with validation
│   ├── DatabaseCard.jsx # Database status card
│   ├── FanCard.jsx     # Fan control card
│   ├── HeaterCard.jsx  # Heater control card
│   ├── MessageBanner.jsx # Success/error messages
│   ├── SensorCard.jsx  # Sensor readings card
│   └── ThresholdControl.jsx # +/- threshold adjusters
├── hooks/              # Custom React hooks
│   └── usePolling.js   # Auto-refresh polling hook
├── services/           # API layer
│   └── api.js          # Backend API calls
├── App.jsx             # Main app component
└── main.jsx            # React entry point
```

## PWA Features

### Installation

On mobile devices, use "Add to Home Screen" to install as an app.

On desktop (Chrome/Edge), click the install icon in the address bar.

### Offline Support

The service worker caches static assets and API responses for limited offline functionality.

## API Integration

The app communicates with the Flask backend at `/api/*` endpoints:

- `GET /api/status` - Sensor and control status
- `GET /api/database` - Database status
- `GET /api/threads` - Thread status
- `GET /api/config/section/{section}` - Configuration section
- `PUT /api/config/{key}` - Update configuration
- `POST /api/controls/{device}` - Control devices
- `POST /api/threads/{name}/restart` - Restart threads

## Deployment

The Flask server automatically serves the React build from `webui-react/dist/` when available.

After building:

```bash
sudo systemctl restart filamentbox.service
```

The React app will be served at `http://your-device:5000/`

## Technology Stack

- **React 19** - UI framework
- **Vite** - Build tool and dev server
- **Vite PWA Plugin** - Progressive Web App support
- **Workbox** - Service worker and caching
- **Vanilla CSS** - No CSS frameworks for minimal bundle size

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## License

Part of the Filament Storage Environmental Manager project.
