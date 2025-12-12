import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button } from './Button';
import { EnableDisableButton } from './EnableDisableButton';
import { 
  areNotificationsEnabled, 
  setNotificationsEnabled, 
  requestNotificationPermission,
  isNotificationSupported,
  getNotificationPermission 
} from '../utils/notifications';
import { getCurrentTheme, setTheme } from '../utils/theme';
import './GaugeEditor.css';

export function SettingsEditor({ onClose, onMessage, onSave, useFahrenheit, setUseFahrenheit, threads }) {
  const [showDatabase, setShowDatabase] = useState(true);
  const [showHeater, setShowHeater] = useState(true);
  const [showFan, setShowFan] = useState(true);
  const [databaseEnabled, setDatabaseEnabled] = useState(false);
  const [heaterEnabled, setHeaterEnabled] = useState(false);
  const [fanEnabled, setFanEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notificationsEnabled, setNotificationsEnabledState] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState('default');
  const [currentTheme, setCurrentTheme] = useState('light');

  useEffect(() => {
    loadConfig();
    // Load notification preferences
    setNotificationsEnabledState(areNotificationsEnabled());
    if (isNotificationSupported()) {
      setNotificationPermission(getNotificationPermission());
    }
    // Load current theme
    setCurrentTheme(getCurrentTheme());
  }, []);

  const loadConfig = async () => {
    try {
      const dbVisibleConfig = await api.getConfig('ui.show_database_card');
      const heaterVisibleConfig = await api.getConfig('ui.show_heater_card');
      const fanVisibleConfig = await api.getConfig('ui.show_fan_card');
      const dbEnabledConfig = await api.getConfig('data_collection.enabled');
      const heaterEnabledConfig = await api.getConfig('heating_control.enabled');
      const fanEnabledConfig = await api.getConfig('humidity_control.enabled');

      setShowDatabase(dbVisibleConfig?.value ?? true);
      setShowHeater(heaterVisibleConfig?.value ?? true);
      setShowFan(fanVisibleConfig?.value ?? true);
      setDatabaseEnabled(dbEnabledConfig?.value ?? false);
      setHeaterEnabled(heaterEnabledConfig?.value ?? false);
      setFanEnabled(fanEnabledConfig?.value ?? false);
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load settings: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.setConfig('ui.show_database_card', showDatabase);
      await api.setConfig('ui.show_heater_card', showHeater);
      await api.setConfig('ui.show_fan_card', showFan);

      onMessage('✓ Settings saved successfully', 'success');
      
      if (onSave) onSave();
      onClose();
    } catch (error) {
      onMessage(error.message, 'error');
      setSaving(false);
    }
  };

  const handleNotificationEnable = async () => {
    // Request permission if we don't have it
    if (notificationPermission !== 'granted') {
      const permission = await requestNotificationPermission();
      setNotificationPermission(permission);
      
      if (permission !== 'granted') {
        onMessage?.('Notification permission denied by browser', 'error');
        return;
      }
    }
    setNotificationsEnabled(true);
    setNotificationsEnabledState(true);
    onMessage?.('Browser notifications enabled', 'success');
  };

  const handleNotificationDisable = async () => {
    setNotificationsEnabled(false);
    setNotificationsEnabledState(false);
    onMessage?.('Browser notifications disabled', 'success');
  };

  const handleThemeChange = (theme) => {
    setTheme(theme);
    setCurrentTheme(theme);
  };

  const isDatabaseThreadRunning = threads?.database_writer?.running ?? false;
  const isHeaterThreadRunning = threads?.heating_control?.running ?? false;
  const isFanThreadRunning = threads?.humidity_control?.running ?? false;

  const isDatabaseBlocked = isDatabaseThreadRunning || databaseEnabled;
  const isHeaterBlocked = isHeaterThreadRunning || heaterEnabled;
  const isFanBlocked = isFanThreadRunning || fanEnabled;

  if (loading) {
    return (
      <div className="gauge-editor-overlay">
        <div className="gauge-editor">
          <div className="gauge-editor-header">
            <h3>Loading...</h3>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="gauge-editor-overlay" onClick={saving ? undefined : onClose}>
      <div className="gauge-editor" onClick={(e) => e.stopPropagation()}>
        <div className="gauge-editor-header">
          <h3>⚙️ Settings</h3>
          <button className="close-btn" onClick={onClose} disabled={saving}>✕</button>
        </div>
        
        <div className="gauge-editor-content">
          <div className="gauge-editor-field">
            <label>Temperature Unit</label>
            <p className="threshold-info" style={{ textAlign: 'center', marginBottom: '0.75rem' }}>Temperature display unit for gauges and readings</p>
            <div className="theme-slider-container">
              <div 
                className={`theme-slider ${useFahrenheit ? 'dark' : 'light'}`}
                onClick={() => setUseFahrenheit(!useFahrenheit)}
              >
                <div className="theme-slider-track">
                  <span className="theme-option left">°C Celsius</span>
                  <span className="theme-option right">°F Fahrenheit</span>
                </div>
                <div className="theme-slider-thumb"></div>
              </div>
            </div>
          </div>

          <div className="gauge-editor-field">
            <label>Theme</label>
            <p className="threshold-info" style={{ textAlign: 'center', marginBottom: '0.75rem' }}>Choose your preferred color scheme</p>
            <div className="theme-slider-container">
              <div 
                className={`theme-slider ${currentTheme === 'dark' ? 'dark' : 'light'}`}
                onClick={() => handleThemeChange(currentTheme === 'dark' ? 'light' : 'dark')}
              >
                <div className="theme-slider-track">
                  <span className="theme-option left">☀️ Light</span>
                  <span className="theme-option right">🌙 Dark</span>
                </div>
                <div className="theme-slider-thumb"></div>
              </div>
            </div>
          </div>

          <div className="gauge-editor-field">
            <label>Visible Cards</label>
            <p className="threshold-info">Control which cards appear on the dashboard</p>
          </div>

          <div className="gauge-editor-field">
            <div className="toggle-switch-container">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showDatabase}
                  onChange={(e) => setShowDatabase(e.target.checked)}
                  disabled={saving || isDatabaseBlocked}
                />
                <span>Database Card</span>
                {isDatabaseBlocked && (
                  <span className="threshold-info" style={{ color: '#f39c12', marginLeft: '0.5rem', fontSize: '0.85rem' }}>
                    ⚠️ {isDatabaseThreadRunning ? 'Thread running - ' : ''}Stop and disable first
                  </span>
                )}
              </label>
            </div>
          </div>

          <div className="gauge-editor-field">
            <div className="toggle-switch-container">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showHeater}
                  onChange={(e) => setShowHeater(e.target.checked)}
                  disabled={saving || isHeaterBlocked}
                />
                <span>Heater Card</span>
                {isHeaterBlocked && (
                  <span className="threshold-info" style={{ color: '#f39c12', marginLeft: '0.5rem', fontSize: '0.85rem' }}>
                    ⚠️ {isHeaterThreadRunning ? 'Thread running - ' : ''}Stop and disable first
                  </span>
                )}
              </label>
            </div>
          </div>

          <div className="gauge-editor-field">
            <div className="toggle-switch-container">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showFan}
                  onChange={(e) => setShowFan(e.target.checked)}
                  disabled={saving || isFanBlocked}
                />
                <span>Fan Card</span>
                {isFanBlocked && (
                  <span className="threshold-info" style={{ color: '#f39c12', marginLeft: '0.5rem', fontSize: '0.85rem' }}>
                    ⚠️ {isFanThreadRunning ? 'Thread running - ' : ''}Stop and disable first
                  </span>
                )}
              </label>
            </div>
          </div>

          <div className="gauge-editor-field">
            <label>Browser Notifications</label>
            {!isNotificationSupported() ? (
              <p className="threshold-info" style={{ color: '#e74c3c', marginTop: '0.25rem' }}>
                ❌ Notifications not supported by this browser
              </p>
            ) : (
              <>
                <EnableDisableButton
                  isEnabled={notificationsEnabled}
                  onEnable={handleNotificationEnable}
                  onDisable={handleNotificationDisable}
                  enableLabel="Enable Notifications"
                  disableLabel="Disable Notifications"
                  disabled={saving}
                />
                {notificationPermission === 'denied' && (
                  <p className="threshold-info" style={{ color: '#e74c3c', marginTop: '0.5rem' }}>
                    ❌ Permission denied. Enable in browser settings.
                  </p>
                )}
                {notificationsEnabled && notificationPermission === 'granted' && (
                  <p className="threshold-info" style={{ color: '#27ae60', marginTop: '0.5rem' }}>
                    ✓ OS notifications enabled
                  </p>
                )}
              </>
            )}
          </div>
        </div>

        <div className="gauge-editor-actions">
          <Button variant="success" onClick={handleSave} disabled={saving}>
            {saving ? '⏳ Saving...' : '💾 Save'}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
