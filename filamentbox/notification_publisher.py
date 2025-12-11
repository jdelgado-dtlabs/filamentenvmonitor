"""Notification publisher for sending real-time alerts to connected web clients.

This module allows backend threads to publish notifications that will be sent
to the web UI for display as browser notifications or in-app messages.
"""

import logging
import time
from collections import deque
from typing import Optional, Dict, Any, Callable, List
from threading import Lock

# Notification callback (set by web server at startup)
_notification_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None

# Store recent notifications in a deque (thread-safe with lock)
_recent_notifications: deque = deque(maxlen=50)  # Keep last 50 notifications
_notifications_lock = Lock()


def set_notification_callback(callback: Callable[[str, str, Dict[str, Any]], None]) -> None:
    """Register a callback function for publishing notifications.

    The callback should accept:
    - message (str): The notification message text
    - type (str): Notification type ('success', 'error', 'warning', 'info')
    - metadata (dict): Optional metadata about the notification

    Args:
        callback: Function to call when notifications are published
    """
    global _notification_callback
    _notification_callback = callback
    logging.info("Notification callback registered")


def get_recent_notifications(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent notifications.

    Args:
        limit: Maximum number of notifications to return (default: 10)

    Returns:
        List of notification dictionaries with 'message', 'type', 'timestamp', and any metadata
    """
    with _notifications_lock:
        # Return most recent notifications (deque is ordered oldest to newest)
        return list(_recent_notifications)[-limit:]


def clear_notifications() -> None:
    """Clear all stored notifications."""
    with _notifications_lock:
        _recent_notifications.clear()


def publish_notification(message: str, notification_type: str = "info", **metadata) -> None:
    """Publish a notification to connected web clients.

    Args:
        message: The notification message text
        notification_type: Type of notification ('success', 'error', 'warning', 'info')
        **metadata: Additional metadata to include with the notification
    """
    # Store in recent notifications
    notification_data = {
        "message": message,
        "type": notification_type,
        "timestamp": time.time(),
        **metadata,
    }

    with _notifications_lock:
        _recent_notifications.append(notification_data)

    # Call registered callback if present
    if _notification_callback is not None:
        try:
            _notification_callback(message, notification_type, metadata)
        except Exception:
            logging.exception("Error calling notification callback")
    else:
        # No callback registered - just log
        logging.debug(f"Notification ({notification_type}): {message}")


# Convenience functions for common notification types
def notify_success(message: str, **metadata) -> None:
    """Publish a success notification."""
    publish_notification(message, "success", **metadata)


def notify_error(message: str, **metadata) -> None:
    """Publish an error notification."""
    publish_notification(message, "error", **metadata)


def notify_warning(message: str, **metadata) -> None:
    """Publish a warning notification."""
    publish_notification(message, "warning", **metadata)


def notify_info(message: str, **metadata) -> None:
    """Publish an info notification."""
    publish_notification(message, "info", **metadata)
