import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button } from './Button';
import './GaugeEditor.css';

export function HeaterConfigEditor({ onClose, onMessage, onSave }) {
  const [gpioPin, setGpioPin] = useState(16);
  const [checkInterval, setCheckInterval] = useState(10.0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const gpioPinConfig = await api.getConfig('heating_control.gpio_pin');
      const intervalConfig = await api.getConfig('heating_control.check_interval');

      setGpioPin(gpioPinConfig?.value ?? 16);
      setCheckInterval(intervalConfig?.value ?? 10.0);
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load heater configuration: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.setConfig('heating_control.gpio_pin', parseInt(gpioPin));
      await api.setConfig('heating_control.check_interval', parseFloat(checkInterval));

      onMessage('✓ Heater configuration saved successfully', 'success');
      
      if (onSave) onSave();
      onClose();
    } catch (error) {
      onMessage(error.message, 'error');
      setSaving(false);
    }
  };

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
          <h3>🔥 Heater Configuration</h3>
          <button className="close-btn" onClick={onClose} disabled={saving}>✕</button>
        </div>
        
        <div className="gauge-editor-content">
          <div className="gauge-editor-field">
            <label htmlFor="heater-gpio">GPIO Pin (BCM)</label>
            <input
              id="heater-gpio"
              type="number"
              step="1"
              min="0"
              max="27"
              value={gpioPin}
              onChange={(e) => setGpioPin(e.target.value)}
              onWheel={(e) => e.target.blur()}
              disabled={saving}
            />
            <p className="threshold-info">GPIO pin for heating relay (BCM numbering, 0-27)</p>
          </div>

          <div className="gauge-editor-field">
            <label htmlFor="heater-interval">Check Interval (seconds)</label>
            <input
              id="heater-interval"
              type="number"
              step="0.1"
              min="0.1"
              max="3600"
              value={checkInterval}
              onChange={(e) => setCheckInterval(e.target.value)}
              onWheel={(e) => e.target.blur()}
              disabled={saving}
            />
            <p className="threshold-info">Seconds between control checks (0.1 - 3600)</p>
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
