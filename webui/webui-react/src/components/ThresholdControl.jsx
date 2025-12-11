import { useState } from 'react';
import { Button } from './Button';
import './ThresholdControl.css';

export function ThresholdControl({ label, value, unit, onChange, step = 0.1 }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  const handleAdjust = (delta) => {
    const newValue = parseFloat((parseFloat(value) + delta).toFixed(1));
    onChange(newValue);
  };

  const handleValueClick = () => {
    setEditValue(value.toFixed(1));
    setIsEditing(true);
  };

  const handleInputChange = (e) => {
    setEditValue(e.target.value);
  };

  const handleInputBlur = () => {
    const newValue = parseFloat(editValue);
    if (!isNaN(newValue)) {
      onChange(newValue);
    }
    setIsEditing(false);
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleInputBlur();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
    }
  };

  return (
    <div className="threshold-control">
      <span className="threshold-label">{label}</span>
      <div className="threshold-adjuster">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleAdjust(-step)}
          className="threshold-btn"
        >
          −
        </Button>
        {isEditing ? (
          <input
            type="number"
            className="threshold-input"
            value={editValue}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            onKeyDown={handleInputKeyDown}
            autoFocus
            step={step}
          />
        ) : (
          <span 
            className="threshold-value" 
            onClick={handleValueClick}
            title="Click to edit"
          >
            {value.toFixed(1)}{unit}
          </span>
        )}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleAdjust(step)}
          className="threshold-btn"
        >
          +
        </Button>
      </div>
    </div>
  );
}
