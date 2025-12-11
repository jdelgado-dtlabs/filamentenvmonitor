import { useState } from 'react';
import { Card, CardHeader, Reading, StatusIndicator } from './Card';
import { Button } from './Button';
import { SensorConfigEditor } from './SensorConfigEditor';
import { Gauge } from './Gauge';
import { GaugeEditor } from './GaugeEditor';
import { api } from '../services/api';

export function formatValue(val, decimals = 1) {
  return val != null && val !== undefined ? val.toFixed(decimals) : 'N/A';
}

export function formatAge(seconds) {
  if (!seconds) return '';
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${(seconds / 3600).toFixed(1)}h ago`;
}

export function SensorCard({ status, threads, config, onMessage, onUpdate, useFahrenheit, kioskMode = false }) {
  const [configOpen, setConfigOpen] = useState(false);
  const [gaugeEditorOpen, setGaugeEditorOpen] = useState(null);
  const collectorThread = threads?.data_collector || {};
  const isStale = status?.sensor?.age && status.sensor.age > 10;

  // Get gauge ranges from config
  const gaugeTempMin = config?.['data_collection.gauge_temp_min']?.value ?? 0;
  const gaugeTempMax = config?.['data_collection.gauge_temp_max']?.value ?? 50;
  const gaugeHumidityMin = config?.['data_collection.gauge_humidity_min']?.value ?? 0;
  const gaugeHumidityMax = config?.['data_collection.gauge_humidity_max']?.value ?? 100;

  // Get gauge color thresholds from config
  const tempRedHigh = config?.['data_collection.gauge_temp_color_red_high']?.value ?? 90;
  const tempYellowHigh = config?.['data_collection.gauge_temp_color_yellow_high']?.value ?? 60;
  const tempGreenHigh = config?.['data_collection.gauge_temp_color_green_high']?.value ?? 30;
  const tempYellowLow = config?.['data_collection.gauge_temp_color_yellow_low']?.value ?? 10;
  
  const humidityRedHigh = config?.['data_collection.gauge_humidity_color_red_high']?.value ?? 90;
  const humidityYellowHigh = config?.['data_collection.gauge_humidity_color_yellow_high']?.value ?? 60;
  const humidityGreenHigh = config?.['data_collection.gauge_humidity_color_green_high']?.value ?? 30;
  const humidityYellowLow = config?.['data_collection.gauge_humidity_color_yellow_low']?.value ?? 10;

  // Convert temperature gauge range if using Fahrenheit
  const displayTempMin = useFahrenheit ? (gaugeTempMin * 9/5) + 32 : gaugeTempMin;
  const displayTempMax = useFahrenheit ? (gaugeTempMax * 9/5) + 32 : gaugeTempMax;
  const displayTemp = useFahrenheit ? status?.sensor?.temperature_f : status?.sensor?.temperature_c;

  const handleRestart = async () => {
    try {
      const result = await api.restartThread('data_collector');
      onMessage(result.message, 'success');
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  return (
    <Card stale={isStale}>
      <CardHeader
        title="📊 Sensor Readings"
        actions={
          !kioskMode && (
            <>
              <Button variant="primary" size="sm" onClick={() => setConfigOpen(!configOpen)}>
                ⚙️ Config
              </Button>
              {collectorThread.restartable && (
                <Button variant="warning" size="sm" onClick={handleRestart}>
                  🔄 Restart
                </Button>
              )}
            </>
          )
        }
      />
      <div className="readings-horizontal">
        <div className="reading-with-gauge">
          <Gauge
            value={displayTemp}
            min={displayTempMin}
            max={displayTempMax}
            unit={useFahrenheit ? '°F' : '°C'}
            redHigh={tempRedHigh}
            yellowHigh={tempYellowHigh}
            greenHigh={tempGreenHigh}
            yellowLow={tempYellowLow}
          />
          {!kioskMode && (
            <button 
              className="gauge-edit-btn" 
              onClick={() => setGaugeEditorOpen('temp')}
              title="Edit gauge range"
            >
              ⚙️ Range
            </button>
          )}
        </div>
        <div className="sensor-timestamp">
          <Reading
            label="Last Update"
            value={<span className="timestamp">{formatAge(status?.sensor?.age)}</span>}
          />
        </div>
        <div className="reading-with-gauge">
          <Gauge
            value={status?.sensor?.humidity}
            min={gaugeHumidityMin}
            max={gaugeHumidityMax}
            unit="%"
            redHigh={humidityRedHigh}
            yellowHigh={humidityYellowHigh}
            greenHigh={humidityGreenHigh}
            yellowLow={humidityYellowLow}
          />
          {!kioskMode && (
            <button 
              className="gauge-edit-btn" 
              onClick={() => setGaugeEditorOpen('humidity')}
              title="Edit gauge range"
            >
              ⚙️ Range
            </button>
          )}
        </div>
      </div>
      {configOpen && (
        <SensorConfigEditor
          onClose={() => setConfigOpen(false)}
          onMessage={onMessage}
          onSave={onUpdate}
        />
      )}
      {gaugeEditorOpen && (
        <GaugeEditor
          type={gaugeEditorOpen}
          onClose={() => setGaugeEditorOpen(null)}
          onMessage={onMessage}
          onSave={onUpdate}
        />
      )}
    </Card>
  );
}
