import { useState, useEffect } from 'react';
import { Card, CardHeader, StatusIndicator } from './Card';
import { Button } from './Button';
import { StartStopButton } from './StartStopButton';
import { EnableDisableButton } from './EnableDisableButton';
import { HeaterConfigEditor } from './HeaterConfigEditor';
import { ThresholdControl } from './ThresholdControl';
import { api } from '../services/api';
import './ControlCard.css';

export function HeaterCard({ status, threads, config, onMessage, onUpdate, useFahrenheit, kioskMode = false }) {
  const [configOpen, setConfigOpen] = useState(false);
  const minTempC = config?.['heating_control.min_temp_c']?.value || 0;
  const maxTempC = config?.['heating_control.max_temp_c']?.value || 0;
  const enabled = config?.['heating_control.enabled']?.value || false;
  const heaterThread = threads?.heating_control || {};

  // Local state for threshold editing
  const [localMinTemp, setLocalMinTemp] = useState(minTempC);
  const [localMaxTemp, setLocalMaxTemp] = useState(maxTempC);
  const [hasChanges, setHasChanges] = useState(false);

  // Update local state when config changes
  useEffect(() => {
    setLocalMinTemp(minTempC);
    setLocalMaxTemp(maxTempC);
    setHasChanges(false);
  }, [minTempC, maxTempC]);

  // Convert Celsius to Fahrenheit
  const cToF = (c) => (c * 9/5) + 32;
  // Convert Fahrenheit to Celsius
  const fToC = (f) => (f - 32) * 5/9;

  // Get display values based on unit selection
  const getDisplayMin = () => useFahrenheit ? cToF(localMinTemp) : localMinTemp;
  const getDisplayMax = () => useFahrenheit ? cToF(localMaxTemp) : localMaxTemp;

  const handleControl = async (state) => {
    try {
      await api.controlDevice('heater', state);
      onUpdate();
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  const handleMinTempChange = (value) => {
    const tempC = useFahrenheit ? fToC(value) : value;
    setLocalMinTemp(tempC);
    setHasChanges(tempC !== minTempC || localMaxTemp !== maxTempC);
  };

  const handleMaxTempChange = (value) => {
    const tempC = useFahrenheit ? fToC(value) : value;
    setLocalMaxTemp(tempC);
    setHasChanges(localMinTemp !== minTempC || tempC !== maxTempC);
  };

  const handleSaveThresholds = async () => {
    try {
      await api.setConfig('heating_control.min_temp_c', parseFloat(localMinTemp.toFixed(1)));
      await api.setConfig('heating_control.max_temp_c', parseFloat(localMaxTemp.toFixed(1)));
      onMessage(`✓ Temperature thresholds updated`, 'success');
      onUpdate();
      setHasChanges(false);
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  const handleCancelChanges = () => {
    setLocalMinTemp(minTempC);
    setLocalMaxTemp(maxTempC);
    setHasChanges(false);
  };

  const handleRestart = async () => {
    try {
      const result = await api.restartThread('heating_control');
      onMessage(result.message, 'success');
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  return (
    <Card>
      <CardHeader
        title="🔥 Heater"
        actions={
          <>
            <StatusIndicator on={status?.controls?.heater?.on} />
            {!kioskMode && (
              <>
                <Button variant="primary" size="sm" onClick={() => setConfigOpen(!configOpen)}>
                  ⚙️ Config
                </Button>
                <EnableDisableButton
                  configKey="heating_control.enabled"
                  currentValue={enabled}
                  onMessage={onMessage}
                  onUpdate={onUpdate}
                />
                <StartStopButton
                  threadName="heating_control"
                  thread={heaterThread}
                  onMessage={onMessage}
                  onUpdate={onUpdate}
                />
                {heaterThread.restartable && heaterThread.running && (
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
          value={getDisplayMin()}
          unit={useFahrenheit ? "°F" : "°C"}
          onChange={handleMinTempChange}
          step={0.1}
        />
        <ThresholdControl
          label="Off"
          value={getDisplayMax()}
          unit={useFahrenheit ? "°F" : "°C"}
          onChange={handleMaxTempChange}
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
        <HeaterConfigEditor
          onClose={() => setConfigOpen(false)}
          onMessage={onMessage}
          onSave={onUpdate}
        />
      )}
    </Card>
  );
}
