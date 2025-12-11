import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button } from './Button';
import './ConfigEditor.css';

export function ConfigEditor({ section, onClose, onMessage, onSave, excludeFields = [] }) {
  const [config, setConfig] = useState(null);
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadConfig();
  }, [section]);

  const loadConfig = async () => {
    try {
      const data = await api.getConfigSection(section);
      setConfig(data);
      const initialValues = {};
      Object.keys(data).forEach((key) => {
        initialValues[key] = data[key].value;
      });
      setValues(initialValues);
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load ${section} configuration: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleChange = (key, newValue) => {
    setValues((prev) => ({ ...prev, [key]: newValue }));
    setHasChanges(true);
    // Clear error for this field when user makes a change
    setErrors((prev) => ({ ...prev, [key]: null }));
  };

  const handleSave = async () => {
    setSaving(true);
    const saveErrors = [];
    let hasChangedValues = false;

    for (const [key, info] of Object.entries(config)) {
      if (values[key] === info.value) continue; // No change

      hasChangedValues = true;
      try {
        let value = values[key];
        if (info.type === 'bool') {
          value = value === 'true' || value === true;
        } else if (info.type === 'int') {
          value = parseInt(value);
          if (isNaN(value)) {
            saveErrors.push(`${key}: Invalid integer value`);
            continue;
          }
        } else if (info.type === 'float') {
          value = parseFloat(value);
          if (isNaN(value)) {
            saveErrors.push(`${key}: Invalid float value`);
            continue;
          }
        }

        await api.setConfig(key, value);
      } catch (error) {
        saveErrors.push(`${key}: ${error.message}`);
      }
    }

    if (saveErrors.length > 0) {
      onMessage(`Errors saving configuration: ${saveErrors.join(', ')}`, 'error');
      setSaving(false);
      return;
    }
    
    if (!hasChangedValues) {
      onMessage('No changes to save', 'error');
      setSaving(false);
      return;
    }

    onMessage('✓ Configuration saved successfully', 'success');
    setHasChanges(false);
    setSaving(false);
    
    // Show restart notification for thread-related configs
    const threadSections = ['data_collection', 'heating_control', 'humidity_control', 'database'];
    if (threadSections.includes(section)) {
      setTimeout(() => {
        onMessage('ℹ️ Thread restart may be required for changes to take effect. Use the Restart button if needed.', 'success');
      }, 1500);
    }
    
    if (onSave) onSave();
  };

  const handleCancel = () => {
    loadConfig();
    setHasChanges(false);
    setErrors({});
  };

  if (loading) {
    return (
      <div className="config-section active">
        <p>Loading configuration...</p>
      </div>
    );
  }

  if (!config) {
    return null;
  }

  // Function to convert snake_case to Title Case
  const formatFieldName = (key) => {
    const fieldName = key.split('.').pop();
    return fieldName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Filter out excluded fields
  const filteredConfig = Object.entries(config).filter(([key]) => {
    const fieldName = key.split('.').pop();
    return !excludeFields.includes(fieldName);
  });

  return (
    <div className="config-section active">
      {filteredConfig.map(([key, info]) => {
        const displayName = formatFieldName(key);
        const inputId = `input-${key.replace(/\./g, '-')}`;
        const hasError = errors[key];

        return (
          <div key={key} className="config-item">
            <label htmlFor={inputId} title={info.description}>
              {displayName}
            </label>
            {renderInput(inputId, key, info, values[key], handleChange, hasError)}
            {hasError && <div className="config-error active">{hasError}</div>}
            {info.description && (
              <div className="config-help">
                {info.description}
                {info.example && ` (e.g., ${info.example})`}
              </div>
            )}
          </div>
        );
      })}
      {hasChanges && (
        <div className="save-indicator active">
          <Button variant="success" onClick={handleSave} disabled={saving}>
            {saving ? '⏳ Saving...' : '💾 Save Changes'}
          </Button>
          <Button variant="secondary" onClick={handleCancel} disabled={saving}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}

function renderInput(id, key, info, value, onChange, hasError) {
  if (info.choices) {
    return (
      <select
        id={id}
        value={value || ''}
        onChange={(e) => onChange(key, e.target.value)}
        className={hasError ? 'error' : ''}
      >
        {info.choices.map((choice) => (
          <option key={choice} value={choice}>
            {choice}
          </option>
        ))}
      </select>
    );
  }

  if (info.type === 'bool') {
    return (
      <select
        id={id}
        value={value === true || value === 'true' ? 'true' : 'false'}
        onChange={(e) => onChange(key, e.target.value)}
        className={hasError ? 'error' : ''}
      >
        <option value="true">True</option>
        <option value="false">False</option>
      </select>
    );
  }

  const inputType = info.type === 'int' || info.type === 'float' ? 'number' : 'text';
  const step = info.type === 'float' ? '0.1' : '1';
  
  // Use password type for sensitive fields
  const fieldName = key.toLowerCase();
  const isSensitive = fieldName.includes('password') || fieldName.includes('token');
  const actualInputType = isSensitive ? 'password' : inputType;

  return (
    <input
      id={id}
      type={actualInputType}
      step={step}
      value={value !== null && value !== undefined ? value : ''}
      onChange={(e) => onChange(key, e.target.value)}
      onWheel={inputType === 'number' ? (e) => e.target.blur() : undefined}
      title={`${info.description}${info.example ? ` (e.g., ${info.example})` : ''}`}
      className={hasError ? 'error' : ''}
    />
  );
}
