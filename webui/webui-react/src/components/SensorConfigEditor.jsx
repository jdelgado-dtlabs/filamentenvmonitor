import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button } from './Button';
import './GaugeEditor.css';

export function SensorConfigEditor({ onClose, onMessage, onSave }) {
  const [sensorType, setSensorType] = useState('bme280');
  const [readInterval, setReadInterval] = useState(5.0);
  const [bme280Address, setBme280Address] = useState('0x76');
  const [bme280Pressure, setBme280Pressure] = useState(1013.25);
  const [dht22Pin, setDht22Pin] = useState(4);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const typeConfig = await api.getConfig('sensors.type');
      const intervalConfig = await api.getConfig('sensors.read_interval');
      const bme280AddressConfig = await api.getConfig('sensors.bme280.i2c_address');
      const bme280PressureConfig = await api.getConfig('sensors.bme280.sea_level_pressure');
      const dht22PinConfig = await api.getConfig('sensors.dht22.gpio_pin');

      setSensorType(typeConfig?.value ?? 'bme280');
      setReadInterval(intervalConfig?.value ?? 5.0);
      setBme280Address(bme280AddressConfig?.value ?? '0x76');
      setBme280Pressure(bme280PressureConfig?.value ?? 1013.25);
      setDht22Pin(dht22PinConfig?.value ?? 4);
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load sensor configuration: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.setConfig('sensors.type', sensorType);
      await api.setConfig('sensors.read_interval', parseFloat(readInterval));
      
      if (sensorType === 'bme280') {
        await api.setConfig('sensors.bme280.i2c_address', bme280Address);
        await api.setConfig('sensors.bme280.sea_level_pressure', parseFloat(bme280Pressure));
      } else {
        await api.setConfig('sensors.dht22.gpio_pin', parseInt(dht22Pin));
      }

      onMessage('✓ Sensor configuration saved successfully', 'success');
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
          <h3>🌡️ Sensor Configuration</h3>
          <button className="close-btn" onClick={onClose} disabled={saving}>✕</button>
        </div>
        
        <div className="gauge-editor-content">
          <div className="gauge-editor-field">
            <label htmlFor="sensor-type">Sensor Type</label>
        <select
          id="sensor-type"
          value={sensorType}
          onChange={(e) => setSensorType(e.target.value)}
          disabled={saving}
        >
          <option value="bme280">BME280</option>
          <option value="dht22">DHT22</option>
        </select>
        <p className="threshold-info">Select the type of sensor connected to your device</p>
      </div>

      <div className="gauge-editor-field">
        <label htmlFor="read-interval">Read Interval (seconds)</label>
        <input
          id="read-interval"
          type="number"
          step="0.1"
          min="0.1"
          max="3600"
          value={readInterval}
          onChange={(e) => setReadInterval(e.target.value)}
          onWheel={(e) => e.target.blur()}
          disabled={saving}
        />
        <p className="threshold-info">Seconds between sensor reads (0.1 - 3600)</p>
      </div>

      {sensorType === 'bme280' && (
        <>
          <div className="gauge-editor-field">
            <label htmlFor="bme280-address">I2C Address</label>
            <select
              id="bme280-address"
              value={bme280Address}
              onChange={(e) => setBme280Address(e.target.value)}
              disabled={saving}
            >
              <option value="0x76">0x76</option>
              <option value="0x77">0x77</option>
            </select>
            <p className="threshold-info">I2C address of the BME280 sensor</p>
          </div>

          <div className="gauge-editor-field">
            <label htmlFor="bme280-pressure">Sea Level Pressure (hPa)</label>
            <input
              id="bme280-pressure"
              type="number"
              step="0.01"
              min="900"
              max="1100"
              value={bme280Pressure}
              onChange={(e) => setBme280Pressure(e.target.value)}
              onWheel={(e) => e.target.blur()}
              disabled={saving}
            />
            <p className="threshold-info">Sea level pressure for altitude calculation (900 - 1100 hPa)</p>
          </div>
        </>
      )}

      {sensorType === 'dht22' && (
        <div className="gauge-editor-field">
          <label htmlFor="dht22-pin">GPIO Pin (BCM)</label>
          <input
            id="dht22-pin"
            type="number"
            step="1"
            min="0"
            max="27"
            value={dht22Pin}
            onChange={(e) => setDht22Pin(e.target.value)}
            onWheel={(e) => e.target.blur()}
            disabled={saving}
          />
          <p className="threshold-info">GPIO pin number (BCM numbering) connected to DHT22 data pin (0 - 27)</p>
        </div>
      )}
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
