import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { MessageBanner } from './components/MessageBanner';
import { SensorCard } from './components/SensorCard';
import { DatabaseCard } from './components/DatabaseCard';
import { HeaterCard } from './components/HeaterCard';
import { FanCard } from './components/FanCard';
import { SettingsEditor } from './components/SettingsEditor';
import { NotificationPanel } from './components/NotificationPanel';
import { usePolling } from './hooks/usePolling';
import { api } from './services/api';
import { 
  showSuccessNotification, 
  showErrorNotification, 
  showWarningNotification,
  showInfoNotification,
  isFirstTime,
  setAutoRequestAttempted,
  requestNotificationPermission,
  setNotificationsEnabled as setNotificationsEnabledPref
} from './utils/notifications';
import './App.css';

function Dashboard() {
  const location = useLocation();
  const navigate = useNavigate();
  const isKioskMode = location.pathname === '/kiosk';
  
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('error');
  const [useFahrenheit, setUseFahrenheit] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [notificationPanelOpen, setNotificationPanelOpen] = useState(false);
  const [showDatabase, setShowDatabase] = useState(true);
  const [showHeater, setShowHeater] = useState(true);
  const [showFan, setShowFan] = useState(true);
  const [viewedNotifications, setViewedNotifications] = useState(new Set());

  // Add/remove class from body for kiosk mode
  useEffect(() => {
    if (isKioskMode) {
      document.body.classList.add('kiosk-mode-body');
    } else {
      document.body.classList.remove('kiosk-mode-body');
    }
    return () => {
      document.body.classList.remove('kiosk-mode-body');
    };
  }, [isKioskMode]);

  // Auto-request notification permission on first load
  useEffect(() => {
    const attemptAutoEnable = async () => {
      if (isFirstTime()) {
        setAutoRequestAttempted(); // Mark that we tried
        const permission = await requestNotificationPermission();
        if (permission === 'granted') {
          setNotificationsEnabledPref(true);
        }
        // If denied or default, don't enable - user must explicitly enable in settings
      }
    };
    attemptAutoEnable();
  }, []);

  const { data: status, refetch: refetchStatus } = usePolling(() => api.getStatus(), 2000);
  const { data: dbStatus } = usePolling(() => api.getDatabase(), 2000);
  const { data: threads } = usePolling(() => api.getThreads(), 2000);
  const { data: dataCollectionConfig } = usePolling(() => api.getConfigSection('data_collection'), 2000);
  const { data: databaseConfig } = usePolling(() => api.getConfigSection('database'), 2000);
  const { data: heatingConfig } = usePolling(() => api.getConfigSection('heating_control'), 2000);
  const { data: humidityConfig } = usePolling(() => api.getConfigSection('humidity_control'), 2000);
  const { data: uiConfig } = usePolling(() => api.getConfigSection('ui'), 2000);

  // Poll for backend notifications
  const { data: notificationsData } = usePolling(() => api.getNotifications(5), 3000);

  // Process backend notifications
  useEffect(() => {
    if (!notificationsData?.notifications) return;
    
    // Track which notification IDs we've already shown
    const shown = new Set(JSON.parse(sessionStorage.getItem('shown_notifications') || '[]'));
    
    notificationsData.notifications.forEach(notification => {
      const notifId = `${notification.timestamp}_${notification.message}`;
      if (!shown.has(notifId)) {
        // Show the notification from backend
        showMessage(notification.message, notification.type);
        shown.add(notifId);
      }
    });
    
    // Persist shown notifications (limit to last 100)
    const shownArray = Array.from(shown).slice(-100);
    sessionStorage.setItem('shown_notifications', JSON.stringify(shownArray));
  }, [notificationsData]);

  // Check for unviewed notifications
  const hasUnviewed = notificationsData?.notifications?.some(notif => {
    const notifId = `${notif.timestamp}_${notif.message}`;
    return !viewedNotifications.has(notifId);
  }) ?? false;

  // Mark notifications as viewed when panel is opened
  const handleOpenNotificationPanel = () => {
    setNotificationPanelOpen(true);
    if (notificationsData?.notifications) {
      const newViewed = new Set(viewedNotifications);
      notificationsData.notifications.forEach(notif => {
        const notifId = `${notif.timestamp}_${notif.message}`;
        newViewed.add(notifId);
      });
      setViewedNotifications(newViewed);
    }
  };

  const handleClearNotifications = async () => {
    try {
      await api.clearNotifications();
      setViewedNotifications(new Set());
    } catch (error) {
      showMessage(`Failed to clear notifications: ${error.message}`, 'error');
    }
  };

  // Update card visibility from config
  useEffect(() => {
    if (uiConfig) {
      setShowDatabase(uiConfig['ui.show_database_card']?.value ?? true);
      setShowHeater(uiConfig['ui.show_heater_card']?.value ?? true);
      setShowFan(uiConfig['ui.show_fan_card']?.value ?? true);
    }
  }, [uiConfig]);

  const showMessage = (msg, type = 'error') => {
    setMessage(msg);
    setMessageType(type);
    
    // Show browser notification based on type
    if (type === 'success') {
      showSuccessNotification(msg);
    } else if (type === 'error') {
      showErrorNotification(msg);
    } else if (type === 'warning') {
      showWarningNotification(msg);
    } else if (type === 'info') {
      showInfoNotification(msg);
    }
  };

  const clearMessage = () => {
    setMessage(null);
  };

  const handleUpdate = () => {
    refetchStatus();
  };

  return (
    <div className={`container ${isKioskMode ? 'kiosk-mode' : ''}`}>
      {!isKioskMode && (
        <header className="app-header">
          <div>
            <h1>🌡️ Filament Storage Environmental Manager</h1>
            <p>Real-time monitoring and control for 3D printer filament storage</p>
          </div>
          <div className="header-controls">
            <button 
              className="notification-bell-btn"
              onClick={handleOpenNotificationPanel}
              title="Notifications"
            >
              🔔
              {hasUnviewed && <span className="notification-dot"></span>}
            </button>
            <button 
              className="settings-btn"
              onClick={() => setSettingsOpen(true)}
              title="Settings"
            >
              ⚙️
            </button>
            <button 
              className="kiosk-mode-btn"
              onClick={() => navigate('/kiosk')}
            >
              🖥️ Kiosk Mode
            </button>
          </div>
        </header>
      )}

      <MessageBanner message={message} type={messageType} onClose={clearMessage} />

      {isKioskMode ? (
        <>
          <div className="kiosk-top-row">
            {status && threads && dataCollectionConfig && (
              <SensorCard 
                status={status} 
                threads={threads}
                config={dataCollectionConfig}
                onMessage={showMessage}
                onUpdate={handleUpdate}
                useFahrenheit={useFahrenheit}
                kioskMode={true}
              />
            )}
          </div>
          <div className="kiosk-bottom-row">
            {showHeater && status && threads && heatingConfig && (
              <HeaterCard 
                status={status} 
                threads={threads}
                config={heatingConfig} 
                onMessage={showMessage}
                onUpdate={handleUpdate}
                useFahrenheit={useFahrenheit}
                kioskMode={true}
              />
            )}
            {showFan && status && threads && humidityConfig && (
              <FanCard 
                status={status} 
                threads={threads}
                config={humidityConfig} 
                onMessage={showMessage}
                onUpdate={handleUpdate}
                kioskMode={true}
              />
            )}
          </div>
        </>
      ) : (
        <div className="dashboard">
          {status && threads && dataCollectionConfig && (
            <SensorCard 
              status={status} 
              threads={threads}
              config={dataCollectionConfig}
              onMessage={showMessage}
              onUpdate={handleUpdate}
              useFahrenheit={useFahrenheit}
              kioskMode={false}
            />
          )}
          {showDatabase && dbStatus && threads && databaseConfig && (
            <DatabaseCard 
              dbStatus={dbStatus} 
              threads={threads}
              config={databaseConfig}
              onMessage={showMessage}
              onUpdate={handleUpdate}
            />
          )}
          {showHeater && status && threads && heatingConfig && (
            <HeaterCard 
              status={status} 
              threads={threads}
              config={heatingConfig} 
              onMessage={showMessage}
              onUpdate={handleUpdate}
              useFahrenheit={useFahrenheit}
              kioskMode={false}
            />
          )}
          {showFan && status && threads && humidityConfig && (
            <FanCard 
              status={status} 
              threads={threads}
              config={humidityConfig} 
              onMessage={showMessage}
              onUpdate={handleUpdate}
              kioskMode={false}
            />
          )}
        </div>
      )}

      {settingsOpen && (
        <SettingsEditor
          onClose={() => setSettingsOpen(false)}
          onMessage={showMessage}
          onSave={handleUpdate}
          useFahrenheit={useFahrenheit}
          setUseFahrenheit={setUseFahrenheit}
          threads={threads}
        />
      )}

      {notificationPanelOpen && (
        <NotificationPanel
          notifications={notificationsData?.notifications || []}
          onClose={() => setNotificationPanelOpen(false)}
          onClear={handleClearNotifications}
        />
      )}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/kiosk" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
