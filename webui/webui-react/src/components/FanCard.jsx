import { useState, useEffect } from 'react';
import { Card, CardHeader, StatusIndicator } from './Card';
import { Button } from './Button';
import { StartStopButton } from './StartStopButton';
import { EnableDisableButton } from './EnableDisableButton';
import { FanConfigEditor } from './FanConfigEditor';
import { ThresholdControl } from './ThresholdControl';
import { api } from '../services/api';
import './ControlCard.css';

export function FanCard({ status, threads, config, onMessage, onUpdate, kioskMode = false }) {
  const [configOpen, setConfigOpen] = useState(false);
  const minHumidity = config?.['humidity_control.min_humidity']?.value || 0;
  const maxHumidity = config?.['humidity_control.max_humidity']?.value || 0;
  const enabled = config?.['humidity_control.enabled']?.value || false;
  const fanThread = threads?.humidity_control || {};

  // Local state for threshold editing
  const [localMinHumidity, setLocalMinHumidity] = useState(minHumidity);
  const [localMaxHumidity, setLocalMaxHumidity] = useState(maxHumidity);
  const [hasChanges, setHasChanges] = useState(false);

  // Update local state when config changes
  useEffect(() => {
    setLocalMinHumidity(minHumidity);
    setLocalMaxHumidity(maxHumidity);
    setHasChanges(false);
  }, [minHumidity, maxHumidity]);

  const handleControl = async (state) => {
    try {
      await api.controlDevice('fan', state);
      onUpdate();
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  const handleMinHumidityChange = (value) => {
    setLocalMinHumidity(value);
    setHasChanges(value !== minHumidity || localMaxHumidity !== maxHumidity);
  };

  const handleMaxHumidityChange = (value) => {
    setLocalMaxHumidity(value);
    setHasChanges(localMinHumidity !== minHumidity || value !== maxHumidity);
  };

  const handleSaveThresholds = async () => {
    try {
      await api.setConfig('humidity_control.min_humidity', parseFloat(localMinHumidity.toFixed(1)));
      await api.setConfig('humidity_control.max_humidity', parseFloat(localMaxHumidity.toFixed(1)));
      onMessage(`✓ Humidity thresholds updated`, 'success');
      onUpdate();
      setHasChanges(false);
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  const handleCancelChanges = () => {
    setLocalMinHumidity(minHumidity);
    setLocalMaxHumidity(maxHumidity);
    setHasChanges(false);
  };

  const handleRestart = async () => {
    try {
      const result = await api.restartThread('humidity_control');
      onMessage(result.message, 'success');
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  return (
    <Card>
      <CardHeader
        title="💨 Fan"
        actions={
          <>
            <StatusIndicator on={status?.controls?.fan?.on} />
            {!kioskMode && (
              <>
                <Button variant="primary" size="sm" onClick={() => setConfigOpen(!configOpen)}>
                  ⚙️ Config
                </Button>
                <EnableDisableButton
                  configKey="humidity_control.enabled"
                  currentValue={enabled}
                  onMessage={onMessage}
                  onUpdate={onUpdate}
                />
                <StartStopButton
                  threadName="humidity_control"
                  thread={fanThread}
                  onMessage={onMessage}
                  onUpdate={onUpdate}
                />
                {fanThread.restartable && fanThread.running && (
                  <Button variant="warning" size="sm" onClick={handleRestart}>
                    🔄 Restart
                  </Button>
                )}
              </>
            )}
          </>
        }
      />
      <div className="thresholds-horizontal">
        <ThresholdControl
          label="On"
          value={localMaxHumidity}
          unit="%"
          onChange={handleMaxHumidityChange}
          step={0.1}
        />
        <ThresholdControl
          label="Off"
          value={localMinHumidity}
          unit="%"
          onChange={handleMinHumidityChange}
          step={0.1}
        />
      </div>
      {hasChanges && (
        <div className="threshold-actions">
          <Button variant="success" onClick={handleSaveThresholds}>
            💾 Save Changes
          </Button>
          <Button variant="secondary" onClick={handleCancelChanges}>
            ✕ Cancel
          </Button>
        </div>
      )}
      <div className="controls">
        <Button variant="success" onClick={() => handleControl(true)} disabled={!enabled}>
          Force ON
        </Button>
        <Button variant="danger" onClick={() => handleControl(false)} disabled={!enabled}>
          Force OFF
        </Button>
        <Button variant="secondary" onClick={() => handleControl(null)} disabled={!enabled}>
          Auto
        </Button>
      </div>
      {configOpen && (
        <FanConfigEditor
          onClose={() => setConfigOpen(false)}
          onMessage={onMessage}
          onSave={onUpdate}
        />
      )}
    </Card>
  );
}
