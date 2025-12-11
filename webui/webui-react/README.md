# FSEM Web UI - React Application

Modern Progressive Web App (PWA) for Filament Storage Environmental Manager.

## Features

- **Real-time updates** via Server-Sent Events (SSE)
- **Dark mode** with OS preference detection
- **Notifications** - Browser notifications + in-app panel
- **Progressive Web App** - Install as native app
- **Responsive design** - Works on desktop and mobile
- **Offline support** - Service worker caching

## Technology Stack

- **React 19.2** - UI framework
- **Vite 7.2** - Build tool and dev server
- **React Router 7.10** - Client-side routing
- **PWA Plugin** - Service worker and manifest generation
- **ESLint** - Code quality and consistency

## Development

```bash
# Install dependencies
npm install

# Start development server with HMR
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Project Structure

```
src/
├── components/     # React components
│   ├── Card.jsx           # Card layout component
│   ├── Gauge.jsx          # Circular gauge for sensors
│   ├── SensorCard.jsx     # Temperature/humidity display
│   ├── DatabaseCard.jsx   # Database status
│   ├── HeaterCard.jsx     # Heater control
│   ├── FanCard.jsx        # Fan control
│   └── ...               # Config editors, buttons, etc.
├── hooks/          # Custom React hooks
│   ├── usePolling.js      # Polling hook for config
│   └── useServerEvents.js # SSE connection hook
├── services/       # API services
│   └── api.js             # Fetch wrappers for backend
├── utils/          # Utility functions
│   ├── theme.js           # Theme management
│   └── notifications.js   # Browser notification API
├── App.jsx         # Main application component
├── main.jsx        # React entry point
├── index.css       # Global styles
└── theme.css       # Theme variables (light/dark)
```

## Key Components

### Real-Time Updates (SSE)
The app uses Server-Sent Events for real-time data:
- `/api/stream` - Combined status stream (sensor, controls, database, threads)
- Updates pushed every 1 second
- Automatic reconnection with exponential backoff

### Theme System
Three modes: Light, Dark, Auto
- Auto mode follows OS `prefers-color-scheme`
- Persisted in localStorage
- Dynamic switching without reload

### Notifications
- Browser notifications for important events
- In-app notification panel with history
- Permission request flow
- Automatic fallback if unsupported

## Build Configuration

See [vite.config.js](vite.config.js) for:
- React plugin configuration
- PWA settings
- Build optimizations

## Browser Support

- Modern browsers with ES2020+ support
- EventSource API for SSE
- Service Worker API for PWA
- Notification API for browser notifications

## License

Same as parent project.
