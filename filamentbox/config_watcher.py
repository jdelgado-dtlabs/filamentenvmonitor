"""Configuration change watcher for hot-reloading.

Monitors the configuration database for changes and notifies listeners.
"""

import logging
import os
import threading
from typing import Any, Callable, Dict, Optional, Set

# Configuration update callbacks
_callbacks: Dict[str, Set[Callable[[str, Any], None]]] = {}
_global_callbacks: Set[Callable[[str, Any], None]] = set()
_callback_lock = threading.Lock()

# Watcher state
_watcher_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_last_mtime: Optional[float] = None
_last_values: Dict[str, Any] = {}

# Watcher configuration
_watch_interval: float = 2.0  # Check every 2 seconds
_config_db_path: Optional[str] = None


def _get_db_mtime() -> Optional[float]:
    """Get modification time of the config database file."""
    if _config_db_path and os.path.exists(_config_db_path):
        try:
            return os.path.getmtime(_config_db_path)
        except OSError:
            pass
    return None


def _check_for_changes() -> None:
    """Check if configuration has changed and notify callbacks."""
    global _last_mtime, _last_values

    try:
        # Import here to avoid circular dependency
        from .config import get, reload_config

        current_mtime = _get_db_mtime()

        # Check if file was modified
        if current_mtime is None:
            return

        if _last_mtime is not None and current_mtime <= _last_mtime:
            # No changes
            return

        _last_mtime = current_mtime

        # Reload configuration from database
        logging.info("Configuration file modified, reloading...")
        reload_config()

        # Get current values for keys we're watching
        changed_keys: Set[str] = set()

        with _callback_lock:
            watched_keys = set(_callbacks.keys())

        for key in watched_keys:
            current_value = get(key)
            previous_value = _last_values.get(key)

            if current_value != previous_value:
                _last_values[key] = current_value
                changed_keys.add(key)
                logging.info(f"Configuration changed: {key} = {current_value}")

        # Notify callbacks for changed keys
        if changed_keys:
            with _callback_lock:
                for key in changed_keys:
                    value = _last_values[key]

                    # Call key-specific callbacks
                    if key in _callbacks:
                        for callback in _callbacks[key]:
                            try:
                                callback(key, value)
                            except Exception as e:
                                logging.error(f"Error in config callback for {key}: {e}")

                    # Call global callbacks
                    for callback in _global_callbacks:
                        try:
                            callback(key, value)
                        except Exception as e:
                            logging.error(f"Error in global config callback: {e}")

    except Exception as e:
        logging.debug(f"Error checking for config changes: {e}")


def _watcher_loop() -> None:
    """Main loop for the configuration watcher thread."""
    logging.info("Configuration watcher started")

    while not _stop_event.is_set():
        _check_for_changes()
        _stop_event.wait(_watch_interval)

    logging.info("Configuration watcher stopped")


def start_watcher(config_db_path: str, interval: float = 2.0) -> None:
    """Start the configuration change watcher.

    Args:
        config_db_path: Path to the configuration database file
        interval: Check interval in seconds (default: 2.0)
    """
    global _watcher_thread, _config_db_path, _watch_interval

    if _watcher_thread is not None and _watcher_thread.is_alive():
        logging.warning("Configuration watcher is already running")
        return

    _config_db_path = config_db_path
    _watch_interval = interval
    _stop_event.clear()

    # Initialize last modification time
    global _last_mtime
    _last_mtime = _get_db_mtime()

    # Start watcher thread
    _watcher_thread = threading.Thread(target=_watcher_loop, name="ConfigWatcher", daemon=True)
    _watcher_thread.start()


def stop_watcher() -> None:
    """Stop the configuration change watcher."""
    global _watcher_thread

    if _watcher_thread is None or not _watcher_thread.is_alive():
        return

    _stop_event.set()
    _watcher_thread.join(timeout=5.0)
    _watcher_thread = None


def watch(key: str, callback: Callable[[str, Any], None]) -> None:
    """Register a callback for configuration changes on a specific key.

    Args:
        key: Configuration key to watch (e.g., "sensor.type")
        callback: Function to call when value changes, receives (key, new_value)
    """
    with _callback_lock:
        if key not in _callbacks:
            _callbacks[key] = set()
        _callbacks[key].add(callback)

        # Store initial value
        from .config import get

        _last_values[key] = get(key)


def watch_all(callback: Callable[[str, Any], None]) -> None:
    """Register a callback for all configuration changes.

    Args:
        callback: Function to call when any value changes, receives (key, new_value)
    """
    with _callback_lock:
        _global_callbacks.add(callback)


def unwatch(key: str, callback: Callable[[str, Any], None]) -> None:
    """Unregister a callback for a specific key.

    Args:
        key: Configuration key
        callback: Callback to remove
    """
    with _callback_lock:
        if key in _callbacks:
            _callbacks[key].discard(callback)
            if not _callbacks[key]:
                del _callbacks[key]


def unwatch_all(callback: Callable[[str, Any], None]) -> None:
    """Unregister a global callback.

    Args:
        callback: Callback to remove
    """
    with _callback_lock:
        _global_callbacks.discard(callback)
