import { useState } from 'react';
import { Card, CardHeader, Reading, StatusIndicator } from './Card';
import { Button } from './Button';
import { StartStopButton } from './StartStopButton';
import { EnableDisableButton } from './EnableDisableButton';
import { DatabaseConfigEditor } from './DatabaseConfigEditor';
import { api } from '../services/api';
import { formatAge } from './SensorCard';

export function DatabaseCard({ dbStatus, threads, config, onMessage, onUpdate }) {
  const [configOpen, setConfigOpen] = useState(false);
  const dbThread = threads?.database_writer || {};
  const dbType = dbStatus?.type === 'none' ? 'None' : 
    dbStatus?.type?.charAt(0).toUpperCase() + dbStatus?.type?.slice(1);
  // Use 'data_collection.enabled' which controls whether the writer runs
  const enabled = config?.['data_collection.enabled']?.value ?? true;

  const handleRestart = async () => {
    try {
      const result = await api.restartThread('database_writer');
      onMessage(result.message, 'success');
    } catch (error) {
      onMessage(error.message, 'error');
    }
  };

  return (
    <Card>
      <CardHeader
        title="💾 Database"
        actions={
          <>
            <Button variant="primary" size="sm" onClick={() => setConfigOpen(!configOpen)}>
              ⚙️ Config
            </Button>
            <EnableDisableButton
              configKey="data_collection.enabled"
              currentValue={enabled}
              onMessage={onMessage}
              onUpdate={onUpdate}
            />
            <StartStopButton
              threadName="database_writer"
              thread={dbThread}
              onMessage={onMessage}
              onUpdate={onUpdate}
            />
            {dbThread.restartable && dbThread.running && (
              <Button variant="warning" size="sm" onClick={handleRestart}>
                🔄 Restart
              </Button>
            )}
          </>
        }
      />
      <div className="readings-horizontal">
        <Reading label="Type" value={<span style={{ fontSize: '1.1rem' }}>{dbType}</span>} />
        <Reading
          label="Last Write"
          value={<span style={{ fontSize: '0.9rem' }}>{dbStatus?.storing_data && dbStatus?.last_write_time ? formatAge(dbStatus.last_write_age) : '—'}</span>}
        />
        <Reading
          label="Status"
          value={
            <StatusIndicator
              on={dbStatus?.storing_data}
              onLabel="STORING"
              offLabel="INACTIVE"
            />
          }
        />
      </div>
      {configOpen && (
        <DatabaseConfigEditor
          onClose={() => setConfigOpen(false)}
          onMessage={onMessage}
          onSave={onUpdate}
        />
      )}
    </Card>
  );
}
