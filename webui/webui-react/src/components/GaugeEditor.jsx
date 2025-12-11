import { useState, useEffect } from 'react';
import { Button } from './Button';
import { api } from '../services/api';
import './GaugeEditor.css';

export function GaugeEditor({ type, onClose, onMessage, onSave }) {
  const [minValue, setMinValue] = useState(0);
  const [maxValue, setMaxValue] = useState(100);
  const [redHigh, setRedHigh] = useState(90);
  const [yellowHigh, setYellowHigh] = useState(60);
  const [greenHigh, setGreenHigh] = useState(30);
  const [yellowLow, setYellowLow] = useState(10);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const minKey = `data_collection.gauge_${type}_min`;
  const maxKey = `data_collection.gauge_${type}_max`;
  const label = type === 'temp' ? 'Temperature' : 'Humidity';
  const unit = type === 'temp' ? '°C' : '%';

  useEffect(() => {
    loadValues();
  }, []);

  const loadValues = async () => {
    try {
      const minConfig = await api.getConfig(minKey);
      const maxConfig = await api.getConfig(maxKey);
      const redHighConfig = await api.getConfig(`data_collection.gauge_${type}_color_red_high`);
      const yellowHighConfig = await api.getConfig(`data_collection.gauge_${type}_color_yellow_high`);
      const greenHighConfig = await api.getConfig(`data_collection.gauge_${type}_color_green_high`);
      const yellowLowConfig = await api.getConfig(`data_collection.gauge_${type}_color_yellow_low`);
      
      setMinValue(minConfig?.value ?? (type === 'temp' ? 0 : 0));
      setMaxValue(maxConfig?.value ?? (type === 'temp' ? 50 : 100));
      setRedHigh(redHighConfig?.value ?? 90);
      setYellowHigh(yellowHighConfig?.value ?? 60);
      setGreenHigh(greenHighConfig?.value ?? 30);
      setYellowLow(yellowLowConfig?.value ?? 10);
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load gauge settings: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      if (parseFloat(minValue) >= parseFloat(maxValue)) {
        onMessage('Minimum value must be less than maximum value', 'error');
        return;
      }

      // Validate color thresholds are in correct order
      const rh = parseFloat(redHigh);
      const yh = parseFloat(yellowHigh);
      const gh = parseFloat(greenHigh);
      const yl = parseFloat(yellowLow);
      
      if (rh <= yh || yh <= gh || gh <= yl || yl < 0 || rh > 100) {
        onMessage('Color thresholds must be in descending order: Red High > Yellow High > Green High > Yellow Low (0-100%)', 'error');
        return;
      }

      setSaving(true);
      await api.setConfig(minKey, parseFloat(minValue));
      await api.setConfig(maxKey, parseFloat(maxValue));
      await api.setConfig(`data_collection.gauge_${type}_color_red_high`, rh);
      await api.setConfig(`data_collection.gauge_${type}_color_yellow_high`, yh);
      await api.setConfig(`data_collection.gauge_${type}_color_green_high`, gh);
      await api.setConfig(`data_collection.gauge_${type}_color_yellow_low`, yl);
      
      onMessage(`✓ ${label} gauge settings updated`, 'success');
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
          <h3>📊 {label} Gauge Settings</h3>
          <button className="close-btn" onClick={onClose} disabled={saving}>✕</button>
        </div>
        
        <div className="gauge-editor-content">
          <div className="gauge-editor-field">
            <label>Minimum Value ({unit})</label>
            <input
              type="number"
              value={minValue}
              onChange={(e) => setMinValue(e.target.value)}
              onWheel={(e) => e.target.blur()}
              step="0.1"
            />
          </div>
          
          <div className="gauge-editor-field">
            <label>Maximum Value ({unit})</label>
            <input
              type="number"
              value={maxValue}
              onChange={(e) => setMaxValue(e.target.value)}
              onWheel={(e) => e.target.blur()}
              step="0.1"
            />
          </div>

          <div className="gauge-editor-section">
            <h4>Color Thresholds (% of range)</h4>
            <p className="threshold-help">Colors change based on percentage of the gauge range</p>
            
            <div className="gauge-editor-field">
              <label style={{color: '#e74c3c'}}>🔴 Red (High) - Above %</label>
              <input
                type="number"
                value={redHigh}
                onChange={(e) => setRedHigh(e.target.value)}
                onWheel={(e) => e.target.blur()}
                step="1"
                min="0"
                max="100"
              />
            </div>

            <div className="gauge-editor-field">
              <label style={{color: '#f39c12'}}>🟡 Yellow (High) - Above %</label>
              <input
                type="number"
                value={yellowHigh}
                onChange={(e) => setYellowHigh(e.target.value)}
                onWheel={(e) => e.target.blur()}
                step="1"
                min="0"
                max="100"
              />
            </div>

            <div className="gauge-editor-field">
              <label style={{color: '#2ecc71'}}>🟢 Green - Above %</label>
              <input
                type="number"
                value={greenHigh}
                onChange={(e) => setGreenHigh(e.target.value)}
                onWheel={(e) => e.target.blur()}
                step="1"
                min="0"
                max="100"
              />
            </div>

            <div className="gauge-editor-field">
              <label style={{color: '#f39c12'}}>🟡 Yellow (Low) - Above %</label>
              <input
                type="number"
                value={yellowLow}
                onChange={(e) => setYellowLow(e.target.value)}
                onWheel={(e) => e.target.blur()}
                step="1"
                min="0"
                max="100"
              />
            </div>

            <div className="gauge-editor-field">
              <label style={{color: '#e74c3c'}}>🔴 Red (Low) - 0% to Yellow Low</label>
              <p className="threshold-info">Automatically red from 0% to {yellowLow}%</p>
            </div>
          </div>

          <div className="gauge-editor-preview">
            <p>Range: {minValue} - {maxValue} {unit}</p>
            <p className="color-preview">
              <span style={{color: '#e74c3c'}}>0-{yellowLow}% Red</span> → 
              <span style={{color: '#f39c12'}}> {yellowLow}-{greenHigh}% Yellow</span> → 
              <span style={{color: '#2ecc71'}}> {greenHigh}-{yellowHigh}% Green</span> → 
              <span style={{color: '#f39c12'}}> {yellowHigh}-{redHigh}% Yellow</span> → 
              <span style={{color: '#e74c3c'}}> {redHigh}-100% Red</span>
            </p>
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
