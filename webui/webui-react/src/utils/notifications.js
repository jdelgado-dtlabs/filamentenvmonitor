/**
 * Browser notification utility for OS-level toaster notifications
 */

const NOTIFICATION_STORAGE_KEY = 'notifications_enabled';
const AUTO_REQUEST_ATTEMPTED_KEY = 'notifications_auto_request_attempted';

/**
 * Check if notifications are enabled in settings
 */
export function areNotificationsEnabled() {
  return localStorage.getItem(NOTIFICATION_STORAGE_KEY) === 'true';
}

/**
 * Enable or disable notifications
 */
export function setNotificationsEnabled(enabled) {
  localStorage.setItem(NOTIFICATION_STORAGE_KEY, enabled.toString());
}

/**
 * Check if auto-request was already attempted
 */
export function wasAutoRequestAttempted() {
  return localStorage.getItem(AUTO_REQUEST_ATTEMPTED_KEY) === 'true';
}

/**
 * Mark that auto-request was attempted
 */
export function setAutoRequestAttempted() {
  localStorage.setItem(AUTO_REQUEST_ATTEMPTED_KEY, 'true');
}

/**
 * Check if this is first time user is loading the app (for auto-enable)
 */
export function isFirstTime() {
  return !localStorage.getItem(NOTIFICATION_STORAGE_KEY) && !wasAutoRequestAttempted();
}

/**
 * Check if browser supports notifications
 */
export function isNotificationSupported() {
  return 'Notification' in window;
}

/**
 * Get current notification permission status
 */
export function getNotificationPermission() {
  if (!isNotificationSupported()) {
    return 'unsupported';
  }
  return Notification.permission;
}

/**
 * Request notification permission from the browser
 * @returns {Promise<string>} Permission status: 'granted', 'denied', or 'default'
 */
export async function requestNotificationPermission() {
  if (!isNotificationSupported()) {
    return 'unsupported';
  }

  if (Notification.permission === 'granted') {
    return 'granted';
  }

  if (Notification.permission === 'denied') {
    return 'denied';
  }

  try {
    const permission = await Notification.requestPermission();
    return permission;
  } catch (error) {
    console.error('Error requesting notification permission:', error);
    return 'denied';
  }
}

/**
 * Show a browser notification
 * @param {string} title - Notification title
 * @param {Object} options - Notification options
 * @param {string} options.body - Notification body text
 * @param {string} options.icon - Icon URL
 * @param {string} options.tag - Notification tag (replaces notifications with same tag)
 * @param {string} options.type - Message type: 'success', 'error', 'warning', 'info'
 */
export function showNotification(title, options = {}) {
  // Check if notifications are enabled and supported
  if (!areNotificationsEnabled() || !isNotificationSupported()) {
    return null;
  }

  // Check permission
  if (Notification.permission !== 'granted') {
    return null;
  }

  // Map message types to icons
  const iconMap = {
    success: '✓',
    error: '✕',
    warning: '⚠️',
    info: 'ℹ️',
  };

  const icon = iconMap[options.type] || '';
  const body = options.body || '';
  const fullBody = icon ? `${icon} ${body}` : body;

  try {
    const notification = new Notification(title, {
      body: fullBody,
      icon: options.icon || '/favicon.ico',
      tag: options.tag || 'filament-storage',
      requireInteraction: options.type === 'error', // Keep error notifications until dismissed
    });

    // Auto-close success notifications after 4 seconds
    if (options.type === 'success' && !options.requireInteraction) {
      setTimeout(() => notification.close(), 4000);
    }

    return notification;
  } catch (error) {
    console.error('Error showing notification:', error);
    return null;
  }
}

/**
 * Show a success notification
 */
export function showSuccessNotification(message) {
  return showNotification('Filament Storage Manager', {
    body: message,
    type: 'success',
  });
}

/**
 * Show an error notification
 */
export function showErrorNotification(message) {
  return showNotification('Filament Storage Manager', {
    body: message,
    type: 'error',
  });
}

/**
 * Show a warning notification
 */
export function showWarningNotification(message) {
  return showNotification('Filament Storage Manager', {
    body: message,
    type: 'warning',
  });
}

/**
 * Show an info notification
 */
export function showInfoNotification(message) {
  return showNotification('Filament Storage Manager', {
    body: message,
    type: 'info',
  });
}
