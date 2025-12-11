import { useEffect } from 'react';
import './MessageBanner.css';

export function MessageBanner({ message, type = 'error', onClose }) {
  useEffect(() => {
    if (type === 'success' && onClose) {
      const timer = setTimeout(onClose, 3000);
      return () => clearTimeout(timer);
    }
  }, [type, onClose]);

  if (!message) return null;

  return (
    <div className={`message message-${type}`}>
      {message}
      {onClose && (
        <button onClick={onClose} className="message-close">×</button>
      )}
    </div>
  );
}
