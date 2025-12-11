import { useState, useEffect } from 'react';
import { Button } from './Button';
import './NotificationPanel.css';

export function NotificationPanel({ notifications, onClose, onClear }) {
  const [filter, setFilter] = useState('all'); // all, error, warning, success, info

  const filteredNotifications = notifications.filter(notif => {
    if (filter === 'all') return true;
    return notif.type === filter;
  });

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'success': return '✓';
      case 'error': return '✕';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '•';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'success': return '#27ae60';
      case 'error': return '#e74c3c';
      case 'warning': return '#f39c12';
      case 'info': return '#3498db';
      default: return '#95a5a6';
    }
  };

  return (
    <div className="notification-panel-overlay" onClick={onClose}>
      <div className="notification-panel" onClick={(e) => e.stopPropagation()}>
        <div className="notification-panel-header">
          <h3>Notifications</h3>
          <div className="notification-panel-actions">
            {notifications.length > 0 && (
              <Button variant="secondary" size="sm" onClick={onClear}>
                Clear All
              </Button>
            )}
            <button className="close-button" onClick={onClose}>✕</button>
          </div>
        </div>

        <div className="notification-filters">
          <button 
            className={filter === 'all' ? 'active' : ''} 
            onClick={() => setFilter('all')}
          >
            All ({notifications.length})
          </button>
          <button 
            className={filter === 'error' ? 'active' : ''} 
            onClick={() => setFilter('error')}
          >
            Errors ({notifications.filter(n => n.type === 'error').length})
          </button>
          <button 
            className={filter === 'warning' ? 'active' : ''} 
            onClick={() => setFilter('warning')}
          >
            Warnings ({notifications.filter(n => n.type === 'warning').length})
          </button>
          <button 
            className={filter === 'success' ? 'active' : ''} 
            onClick={() => setFilter('success')}
          >
            Success ({notifications.filter(n => n.type === 'success').length})
          </button>
        </div>

        <div className="notification-list">
          {filteredNotifications.length === 0 ? (
            <div className="notification-empty">
              <p>No notifications to display</p>
            </div>
          ) : (
            filteredNotifications.map((notif, index) => (
              <div 
                key={`${notif.timestamp}_${index}`} 
                className="notification-item"
                style={{ borderLeftColor: getTypeColor(notif.type) }}
              >
                <div className="notification-icon" style={{ color: getTypeColor(notif.type) }}>
                  {getTypeIcon(notif.type)}
                </div>
                <div className="notification-content">
                  <div className="notification-message">{notif.message}</div>
                  <div className="notification-time">{formatTimestamp(notif.timestamp)}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
