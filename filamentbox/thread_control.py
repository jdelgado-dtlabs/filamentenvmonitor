"""Thread control module for managing and restarting worker threads.

Provides centralized control for restarting individual threads in the FilamentBox application.
"""

import logging
import threading
from typing import Callable, Optional

from .shared_state import update_thread_status as _update_shared_state

logger = logging.getLogger(__name__)

# Thread registry
_threads: dict[str, Optional[threading.Thread]] = {
    "data_collector": None,
    "database_writer": None,
    "heating_control": None,
    "humidity_control": None,
}

# Thread restart callbacks
_restart_callbacks: dict[str, Callable[[], None]] = {}

# Thread start callbacks
_start_callbacks: dict[str, Callable[[], None]] = {}

# Thread stop callbacks
_stop_callbacks: dict[str, Callable[[], None]] = {}

# Lock for thread operations
_thread_lock = threading.Lock()


def register_thread(name: str, thread: threading.Thread) -> None:
    """Register a thread for monitoring and control.

    Args:
        name: Thread identifier (data_collector, database_writer, etc.)
        thread: The thread object
    """
    with _thread_lock:
        if name not in _threads:
            logger.warning(f"Unknown thread name: {name}")
            return
        _threads[name] = thread
        logger.debug(f"Registered thread: {name}")


def register_restart_callback(name: str, callback: Callable[[], None]) -> None:
    """Register a callback function to restart a specific thread.

    Args:
        name: Thread identifier
        callback: Function that will restart the thread when called
    """
    with _thread_lock:
        _restart_callbacks[name] = callback
        logger.debug(f"Registered restart callback for: {name}")


def register_start_callback(name: str, callback: Callable[[], None]) -> None:
    """Register a callback function to start a specific thread.

    Args:
        name: Thread identifier
        callback: Function that will start the thread when called
    """
    with _thread_lock:
        _start_callbacks[name] = callback
        logger.debug(f"Registered start callback for: {name}")


def register_stop_callback(name: str, callback: Callable[[], None]) -> None:
    """Register a callback function to stop a specific thread.

    Args:
        name: Thread identifier
        callback: Function that will stop the thread when called
    """
    with _thread_lock:
        _stop_callbacks[name] = callback
        logger.debug(f"Registered stop callback for: {name}")


def get_thread_status() -> dict:
    """Get status of all registered threads.

    Returns:
        Dictionary mapping thread names to their running status
    """
    with _thread_lock:
        status = {
            name: {
                "running": thread.is_alive() if thread is not None else False,
                "exists": thread is not None,
                "restartable": name in _restart_callbacks,
            }
            for name, thread in _threads.items()
        }
        # Also update shared state for cross-process access
        _update_shared_state(status)
        return status


def restart_thread(name: str) -> tuple[bool, str]:
    """Restart a specific thread.

    Args:
        name: Thread identifier

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check prerequisites with lock
    with _thread_lock:
        if name not in _threads:
            return False, f"Unknown thread: {name}"

        if name not in _restart_callbacks:
            return False, f"Thread '{name}' does not have a restart callback registered"

        thread = _threads[name]
        if thread is not None and thread.is_alive():
            logger.info(f"Thread '{name}' is still running, restart may not be necessary")

        callback = _restart_callbacks[name]

    # Call callback WITHOUT holding the lock (callback may need to call register_thread)
    try:
        callback()
        logger.info(f"Successfully restarted thread: {name}")
        return True, f"Thread '{name}' restarted successfully"
    except Exception as e:
        error_msg = f"Failed to restart thread '{name}': {e}"
        logger.error(error_msg)
        return False, error_msg


def start_thread(name: str) -> tuple[bool, str]:
    """Start a specific thread.

    Args:
        name: Thread identifier

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check prerequisites with lock
    with _thread_lock:
        if name not in _threads:
            return False, f"Unknown thread: {name}"

        if name not in _start_callbacks:
            return False, f"Thread '{name}' does not have a start callback registered"

        thread = _threads[name]
        if thread is not None and thread.is_alive():
            return False, f"Thread '{name}' is already running"

        callback = _start_callbacks[name]

    # Call callback WITHOUT holding the lock (callback may need to call register_thread)
    try:
        callback()
        logger.info(f"Successfully started thread: {name}")
        return True, f"Thread '{name}' started successfully"
    except Exception as e:
        error_msg = f"Failed to start thread '{name}': {e}"
        logger.error(error_msg)
        return False, error_msg


def stop_thread(name: str) -> tuple[bool, str]:
    """Stop a specific thread.

    Args:
        name: Thread identifier

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check prerequisites with lock
    with _thread_lock:
        if name not in _threads:
            return False, f"Unknown thread: {name}"

        if name not in _stop_callbacks:
            return False, f"Thread '{name}' does not have a stop callback registered"

        thread = _threads[name]
        if thread is None or not thread.is_alive():
            return False, f"Thread '{name}' is not running"

        callback = _stop_callbacks[name]

    # Call callback WITHOUT holding the lock (callback may need to call register_thread)
    try:
        callback()
        logger.info(f"Successfully stopped thread: {name}")
        return True, f"Thread '{name}' stopped successfully"
    except Exception as e:
        error_msg = f"Failed to stop thread '{name}': {e}"
        logger.error(error_msg)
        return False, error_msg


def get_thread(name: str) -> Optional[threading.Thread]:
    """Get a thread object by name.

    Args:
        name: Thread identifier

    Returns:
        Thread object or None if not found
    """
    with _thread_lock:
        return _threads.get(name)
