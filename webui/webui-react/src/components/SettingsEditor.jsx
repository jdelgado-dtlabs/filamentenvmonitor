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

  useEffect(() => {
    loadConfig();
    // Load notification preferences
    setNotificationsEnabledState(areNotificationsEnabled());
    if (isNotificationSupported()) {
      setNotificationPermission(getNotificationPermission());
    }
  }, []);

  const loadConfig = async () => {
    try {
      const dbVisibleConfig = await api.getConfig('ui.show_database_card');
      const heaterVisibleConfig = await api.getConfig('ui.show_heater_card');
      const fanVisibleConfig = await api.getConfig('ui.show_fan_card');
      const dbEnabledConfig = await api.getConfig('database.enabled');
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
            <div className="toggle-switch-container horizontal">
              <button
                className={`toggle-option ${!useFahrenheit ? 'active' : ''}`}
                onClick={() => setUseFahrenheit(false)}
                disabled={saving}
              >
                °C
              </button>
              <button
                className={`toggle-option ${useFahrenheit ? 'active' : ''}`}
                onClick={() => setUseFahrenheit(true)}
                disabled={saving}
              >
                °F
              </button>
            </div>
            <p className="threshold-info">Temperature display unit for gauges and readings</p>
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
              </label>
              {isDatabaseBlocked && (
                <p className="threshold-info" style={{ color: '#f39c12', marginTop: '0.25rem' }}>
                  ⚠️ {isDatabaseThreadRunning ? 'Thread is running - ' : ''}Stop and disable database first
                </p>
              )}
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
              </label>
              {isHeaterBlocked && (
                <p className="threshold-info" style={{ color: '#f39c12', marginTop: '0.25rem' }}>
                  ⚠️ {isHeaterThreadRunning ? 'Thread is running - ' : ''}Stop and disable heater control first
                </p>
              )}
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
              </label>
              {isFanBlocked && (
                <p className="threshold-info" style={{ color: '#f39c12', marginTop: '0.25rem' }}>
                  ⚠️ {isFanThreadRunning ? 'Thread is running - ' : ''}Stop and disable fan control first
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="gauge-editor-section">
          <h4>Notifications</h4>
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
