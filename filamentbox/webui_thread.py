"""Web UI thread wrapper for running Flask in a background thread.

Allows the web UI to run as part of the main FilamentBox process
instead of as a separate service.
"""

import logging
import threading


def start_webui_thread(host: str, port: int, stop_event: threading.Event) -> None:
    """Start the Flask web UI in the current thread.

    This function is designed to be run as a thread target. It starts Flask
    with production-ready settings using waitress WSGI server for better
    SSE support.

    Args:
        host: Host address to bind to (e.g., '0.0.0.0')
        port: Port number to listen on (e.g., 5000)
        stop_event: Threading event to signal shutdown
    """
    try:
        # Import Flask app from webui module
        import sys
        import os

        # Ensure webui module is in path
        webui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webui")
        if webui_path not in sys.path:
            sys.path.insert(0, webui_path)

        from webui.webui_server import app

        logging.info(f"Starting Flask web UI on {host}:{port}")

        try:
            # Try to use waitress (better SSE support)
            from waitress import serve

            logging.info("Using waitress WSGI server (production mode)")
            serve(
                app,
                host=host,
                port=port,
                threads=16,  # Increase threads for multiple concurrent SSE connections
                channel_timeout=300,  # Keep SSE connections alive for 5 min
                asyncore_use_poll=True,  # Use poll() for better concurrency
                _quiet=False,
            )
        except ImportError:
            # Fall back to Flask development server
            logging.warning(
                "waitress not available, using Flask dev server (install waitress for better SSE support)"
            )
            app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True,
            )

    except ImportError as e:
        logging.error(f"Failed to import Flask app: {e}")
        logging.error("Ensure webui module and Flask are properly installed")
    except OSError as e:
        logging.error(f"Failed to bind to {host}:{port}: {e}")
        logging.error("Port may already be in use or insufficient permissions")
    except Exception as e:
        logging.error(f"Web UI thread error: {e}", exc_info=True)
    finally:
        logging.info("Web UI thread exiting")


def run_webui_standalone(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Run the web UI in standalone mode (for backward compatibility).

    This allows the web UI to be run as a separate process using run_webui.py

    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    import sys
    import os

    # Ensure webui module is in path
    webui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webui")
    if webui_path not in sys.path:
        sys.path.insert(0, webui_path)

    from webui.webui_server import app

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info(f"Starting Flask web UI in standalone mode on {host}:{port}")

    try:
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )
    except KeyboardInterrupt:
        logging.info("Web UI stopped by user")
    except Exception as e:
        logging.error(f"Web UI error: {e}", exc_info=True)
