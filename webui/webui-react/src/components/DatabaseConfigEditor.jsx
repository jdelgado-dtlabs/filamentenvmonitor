import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button } from './Button';
import { TagEditor } from './TagEditor';
import './GaugeEditor.css';

export function DatabaseConfigEditor({ onClose, onMessage, onSave }) {
  const [dbType, setDbType] = useState('none');
  const [batchSize, setBatchSize] = useState(10);
  const [flushInterval, setFlushInterval] = useState(60);
  
  // InfluxDB fields
  const [influxVersion, setInfluxVersion] = useState('2');
  const [influxUrl, setInfluxUrl] = useState('');
  const [influxToken, setInfluxToken] = useState('');
  const [influxOrg, setInfluxOrg] = useState('');
  const [influxBucket, setInfluxBucket] = useState('');
  const [influxMeasurement, setInfluxMeasurement] = useState('environment');
  const [influxUsername, setInfluxUsername] = useState('');
  
  // Prometheus fields
  const [promUrl, setPromUrl] = useState('');
  const [promJob, setPromJob] = useState('filamentbox');
  const [promInstance, setPromInstance] = useState('');
  const [promUsername, setPromUsername] = useState('');
  const [promPassword, setPromPassword] = useState('');
  
  // TimescaleDB fields
  const [tsHost, setTsHost] = useState('');
  const [tsPort, setTsPort] = useState(5432);
  const [tsDatabase, setTsDatabase] = useState('');
  const [tsUsername, setTsUsername] = useState('');
  const [tsPassword, setTsPassword] = useState('');
  const [tsTable, setTsTable] = useState('environment_data');
  const [tsSslMode, setTsSslMode] = useState('prefer');
  
  // VictoriaMetrics fields
  const [vmUrl, setVmUrl] = useState('');
  const [vmUsername, setVmUsername] = useState('');
  const [vmPassword, setVmPassword] = useState('');
  const [vmTenant, setVmTenant] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tagEditorOpen, setTagEditorOpen] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const typeConfig = await api.getConfig('database.type');
      const batchConfig = await api.getConfig('database.batch_size');
      const flushConfig = await api.getConfig('database.flush_interval');

      const currentType = typeConfig?.value ?? 'none';
      setDbType(currentType);
      setBatchSize(batchConfig?.value ?? 10);
      setFlushInterval(flushConfig?.value ?? 60);
      
      // Load database-specific configs based on type
      if (currentType === 'influxdb') {
        const configs = await Promise.all([
          api.getConfig('database.influxdb.version'),
          api.getConfig('database.influxdb.url'),
          api.getConfig('database.influxdb.token'),
          api.getConfig('database.influxdb.org'),
          api.getConfig('database.influxdb.bucket'),
          api.getConfig('database.influxdb.measurement'),
          api.getConfig('database.influxdb.username'),
        ]);
        setInfluxVersion(configs[0]?.value ?? '2');
        setInfluxUrl(configs[1]?.value ?? '');
        setInfluxToken(configs[2]?.value ?? '');
        setInfluxOrg(configs[3]?.value ?? '');
        setInfluxBucket(configs[4]?.value ?? '');
        setInfluxMeasurement(configs[5]?.value ?? 'environment');
        setInfluxUsername(configs[6]?.value ?? '');
      } else if (currentType === 'prometheus') {
        const configs = await Promise.all([
          api.getConfig('database.prometheus.pushgateway_url'),
          api.getConfig('database.prometheus.job'),
          api.getConfig('database.prometheus.instance'),
          api.getConfig('database.prometheus.username'),
          api.getConfig('database.prometheus.password'),
        ]);
        setPromUrl(configs[0]?.value ?? '');
        setPromJob(configs[1]?.value ?? 'filamentbox');
        setPromInstance(configs[2]?.value ?? '');
        setPromUsername(configs[3]?.value ?? '');
        setPromPassword(configs[4]?.value ?? '');
      } else if (currentType === 'timescaledb') {
        const configs = await Promise.all([
          api.getConfig('database.timescaledb.host'),
          api.getConfig('database.timescaledb.port'),
          api.getConfig('database.timescaledb.database'),
          api.getConfig('database.timescaledb.username'),
          api.getConfig('database.timescaledb.password'),
          api.getConfig('database.timescaledb.table'),
          api.getConfig('database.timescaledb.ssl_mode'),
        ]);
        setTsHost(configs[0]?.value ?? '');
        setTsPort(configs[1]?.value ?? 5432);
        setTsDatabase(configs[2]?.value ?? '');
        setTsUsername(configs[3]?.value ?? '');
        setTsPassword(configs[4]?.value ?? '');
        setTsTable(configs[5]?.value ?? 'environment_data');
        setTsSslMode(configs[6]?.value ?? 'prefer');
      } else if (currentType === 'victoriametrics') {
        const configs = await Promise.all([
          api.getConfig('database.victoriametrics.url'),
          api.getConfig('database.victoriametrics.username'),
          api.getConfig('database.victoriametrics.password'),
          api.getConfig('database.victoriametrics.tenant'),
        ]);
        setVmUrl(configs[0]?.value ?? '');
        setVmUsername(configs[1]?.value ?? '');
        setVmPassword(configs[2]?.value ?? '');
        setVmTenant(configs[3]?.value ?? '');
      }
      
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load database configuration: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.setConfig('database.type', dbType);
      
      if (dbType !== 'none') {
        await api.setConfig('database.batch_size', parseInt(batchSize));
        await api.setConfig('database.flush_interval', parseInt(flushInterval));
        
        // Save database-specific configs
        if (dbType === 'influxdb') {
          await api.setConfig('database.influxdb.version', influxVersion);
          await api.setConfig('database.influxdb.url', influxUrl);
          await api.setConfig('database.influxdb.token', influxToken);
          await api.setConfig('database.influxdb.org', influxOrg);
          await api.setConfig('database.influxdb.bucket', influxBucket);
          await api.setConfig('database.influxdb.measurement', influxMeasurement);
          if (influxVersion === '1') {
            await api.setConfig('database.influxdb.username', influxUsername);
          }
        } else if (dbType === 'prometheus') {
          await api.setConfig('database.prometheus.pushgateway_url', promUrl);
          await api.setConfig('database.prometheus.job', promJob);
          await api.setConfig('database.prometheus.instance', promInstance);
          if (promUsername) {
            await api.setConfig('database.prometheus.username', promUsername);
            await api.setConfig('database.prometheus.password', promPassword);
          }
        } else if (dbType === 'timescaledb') {
          await api.setConfig('database.timescaledb.host', tsHost);
          await api.setConfig('database.timescaledb.port', parseInt(tsPort));
          await api.setConfig('database.timescaledb.database', tsDatabase);
          await api.setConfig('database.timescaledb.username', tsUsername);
          await api.setConfig('database.timescaledb.password', tsPassword);
          await api.setConfig('database.timescaledb.table', tsTable);
          await api.setConfig('database.timescaledb.ssl_mode', tsSslMode);
        } else if (dbType === 'victoriametrics') {
          await api.setConfig('database.victoriametrics.url', vmUrl);
          if (vmUsername) {
            await api.setConfig('database.victoriametrics.username', vmUsername);
            await api.setConfig('database.victoriametrics.password', vmPassword);
          }
          if (vmTenant) {
            await api.setConfig('database.victoriametrics.tenant', vmTenant);
          }
        }
      }

      onMessage('✓ Database configuration saved successfully', 'success');
      setTimeout(() => {
        onMessage('ℹ️ Database thread restart may be required. Use the Restart button if needed.', 'success');
      }, 1500);
      
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
          <h3>💾 Database Configuration</h3>
          <button className="close-btn" onClick={onClose} disabled={saving}>✕</button>
        </div>
        
        <div className="gauge-editor-content">
          <div className="gauge-editor-field">
            <label htmlFor="db-type">Database Type</label>
            <select
              id="db-type"
              value={dbType}
              onChange={(e) => setDbType(e.target.value)}
              disabled={saving}
            >
              <option value="none">None</option>
              <option value="influxdb">InfluxDB</option>
              <option value="prometheus">Prometheus</option>
              <option value="timescaledb">TimescaleDB</option>
              <option value="victoriametrics">VictoriaMetrics</option>
            </select>
            <p className="threshold-info">Select the database backend for storing sensor data</p>
          </div>

          {dbType !== 'none' && (
            <>
              <div className="gauge-editor-field">
                <label htmlFor="batch-size">Batch Size</label>
                <input
                  id="batch-size"
                  type="number"
                  step="1"
                  min="1"
                  max="10000"
                  value={batchSize}
                  onChange={(e) => setBatchSize(e.target.value)}
                  onWheel={(e) => e.target.blur()}
                  disabled={saving}
                />
                <p className="threshold-info">Number of data points to collect before writing (1 - 10000)</p>
              </div>

              <div className="gauge-editor-field">
                <label htmlFor="flush-interval">Flush Interval (seconds)</label>
                <input
                  id="flush-interval"
                  type="number"
                  step="1"
                  min="1"
                  max="3600"
                  value={flushInterval}
                  onChange={(e) => setFlushInterval(e.target.value)}
                  onWheel={(e) => e.target.blur()}
                  disabled={saving}
                />
                <p className="threshold-info">Maximum seconds before forcing a write (1 - 3600)</p>
              </div>

              {/* InfluxDB specific fields */}
              {dbType === 'influxdb' && (
                <>
                  <div className="gauge-editor-field">
                    <label htmlFor="influx-version">InfluxDB Version</label>
                    <select
                      id="influx-version"
                      value={influxVersion}
                      onChange={(e) => setInfluxVersion(e.target.value)}
                      disabled={saving}
                    >
                      <option value="1">1.x</option>
                      <option value="2">2.x</option>
                      <option value="3">3.x</option>
                    </select>
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="influx-url">URL</label>
                    <input
                      id="influx-url"
                      type="text"
                      value={influxUrl}
                      onChange={(e) => setInfluxUrl(e.target.value)}
                      disabled={saving}
                      placeholder="http://192.168.1.100:8086"
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="influx-token">Token{influxVersion === '1' ? ' / Password' : ''}</label>
                    <input
                      id="influx-token"
                      type="password"
                      value={influxToken}
                      onChange={(e) => setInfluxToken(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  {influxVersion === '2' && (
                    <div className="gauge-editor-field">
                      <label htmlFor="influx-org">Organization</label>
                      <input
                        id="influx-org"
                        type="text"
                        value={influxOrg}
                        onChange={(e) => setInfluxOrg(e.target.value)}
                        disabled={saving}
                      />
                    </div>
                  )}

                  {influxVersion === '1' && (
                    <div className="gauge-editor-field">
                      <label htmlFor="influx-username">Username</label>
                      <input
                        id="influx-username"
                        type="text"
                        value={influxUsername}
                        onChange={(e) => setInfluxUsername(e.target.value)}
                        disabled={saving}
                      />
                    </div>
                  )}

                  <div className="gauge-editor-field">
                    <label htmlFor="influx-bucket">{influxVersion === '2' ? 'Bucket' : 'Database'}</label>
                    <input
                      id="influx-bucket"
                      type="text"
                      value={influxBucket}
                      onChange={(e) => setInfluxBucket(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="influx-measurement">Measurement</label>
                    <input
                      id="influx-measurement"
                      type="text"
                      value={influxMeasurement}
                      onChange={(e) => setInfluxMeasurement(e.target.value)}
                      disabled={saving}
                    />
                  </div>
                </>
              )}

              {/* Prometheus specific fields */}
              {dbType === 'prometheus' && (
                <>
                  <div className="gauge-editor-field">
                    <label htmlFor="prom-url">Pushgateway URL</label>
                    <input
                      id="prom-url"
                      type="text"
                      value={promUrl}
                      onChange={(e) => setPromUrl(e.target.value)}
                      disabled={saving}
                      placeholder="http://192.168.1.100:9091"
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="prom-job">Job Name</label>
                    <input
                      id="prom-job"
                      type="text"
                      value={promJob}
                      onChange={(e) => setPromJob(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="prom-instance">Instance (optional)</label>
                    <input
                      id="prom-instance"
                      type="text"
                      value={promInstance}
                      onChange={(e) => setPromInstance(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="prom-username">Username (optional)</label>
                    <input
                      id="prom-username"
                      type="text"
                      value={promUsername}
                      onChange={(e) => setPromUsername(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="prom-password">Password (optional)</label>
                    <input
                      id="prom-password"
                      type="password"
                      value={promPassword}
                      onChange={(e) => setPromPassword(e.target.value)}
                      disabled={saving}
                    />
                  </div>
                </>
              )}

              {/* TimescaleDB specific fields */}
              {dbType === 'timescaledb' && (
                <>
                  <div className="gauge-editor-field">
                    <label htmlFor="ts-host">Host</label>
                    <input
                      id="ts-host"
                      type="text"
                      value={tsHost}
                      onChange={(e) => setTsHost(e.target.value)}
                      disabled={saving}
                      placeholder="192.168.1.100"
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="ts-port">Port</label>
                    <input
                      id="ts-port"
                      type="number"
                      step="1"
                      min="1024"
                      max="65535"
                      value={tsPort}
                      onChange={(e) => setTsPort(e.target.value)}
                      onWheel={(e) => e.target.blur()}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="ts-database">Database</label>
                    <input
                      id="ts-database"
                      type="text"
                      value={tsDatabase}
                      onChange={(e) => setTsDatabase(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="ts-username">Username</label>
                    <input
                      id="ts-username"
                      type="text"
                      value={tsUsername}
                      onChange={(e) => setTsUsername(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="ts-password">Password</label>
                    <input
                      id="ts-password"
                      type="password"
                      value={tsPassword}
                      onChange={(e) => setTsPassword(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="ts-table">Table Name</label>
                    <input
                      id="ts-table"
                      type="text"
                      value={tsTable}
                      onChange={(e) => setTsTable(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="ts-sslmode">SSL Mode</label>
                    <select
                      id="ts-sslmode"
                      value={tsSslMode}
                      onChange={(e) => setTsSslMode(e.target.value)}
                      disabled={saving}
                    >
                      <option value="disable">Disable</option>
                      <option value="allow">Allow</option>
                      <option value="prefer">Prefer</option>
                      <option value="require">Require</option>
                      <option value="verify-ca">Verify CA</option>
                      <option value="verify-full">Verify Full</option>
                    </select>
                  </div>
                </>
              )}

              {/* VictoriaMetrics specific fields */}
              {dbType === 'victoriametrics' && (
                <>
                  <div className="gauge-editor-field">
                    <label htmlFor="vm-url">URL</label>
                    <input
                      id="vm-url"
                      type="text"
                      value={vmUrl}
                      onChange={(e) => setVmUrl(e.target.value)}
                      disabled={saving}
                      placeholder="http://192.168.1.100:8428"
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="vm-username">Username (optional)</label>
                    <input
                      id="vm-username"
                      type="text"
                      value={vmUsername}
                      onChange={(e) => setVmUsername(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="vm-password">Password (optional)</label>
                    <input
                      id="vm-password"
                      type="password"
                      value={vmPassword}
                      onChange={(e) => setVmPassword(e.target.value)}
                      disabled={saving}
                    />
                  </div>

                  <div className="gauge-editor-field">
                    <label htmlFor="vm-tenant">Tenant ID (optional)</label>
                    <input
                      id="vm-tenant"
                      type="text"
                      value={vmTenant}
                      onChange={(e) => setVmTenant(e.target.value)}
                      disabled={saving}
                    />
                  </div>
                </>
              )}

              <div className="gauge-editor-field">
                <Button variant="primary" size="sm" onClick={() => setTagEditorOpen(true)} disabled={saving}>
                  🏷️ Edit {dbType === 'influxdb' ? 'Tags' : 'Labels'}
                </Button>
                <p className="threshold-info">Configure additional {dbType === 'influxdb' ? 'tags' : 'labels'} for {dbType}</p>
              </div>
            </>
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

        {tagEditorOpen && (
          <TagEditor
            dbType={dbType}
            onClose={() => setTagEditorOpen(false)}
            onMessage={onMessage}
            onSave={onSave}
          />
        )}
      </div>
    </div>
  );
}
