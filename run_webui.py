#!/usr/bin/env python3
"""
Filament Storage Environmental Manager Web UI Server Launcher

Entry point for starting the web UI server as a systemd service.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webui.webui_server import main

if __name__ == "__main__":
    main()
