import './Card.css';

export function Card({ children, className = '', stale = false }) {
  return (
    <div className={`card ${stale ? 'stale-data' : ''} ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, actions }) {
  return (
    <div className="card-header">
      <h2>{title}</h2>
      {actions && <div className="card-actions">{actions}</div>}
    </div>
  );
}

export function Reading({ label, value, unit }) {
  return (
    <div className="reading">
      <div className="reading-label">{label}</div>
      <div className="reading-value">
        {value}
        {unit && <span className="reading-unit">{unit}</span>}
      </div>
    </div>
  );
}

export function StatusIndicator({ on, onLabel = 'ON', offLabel = 'OFF' }) {
  return (
    <span className={`status-indicator ${on ? 'status-on' : 'status-off'}`}>
      <span className="status-dot"></span>
      {on ? onLabel : offLabel}
    </span>
  );
}
