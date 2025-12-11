"""Pytest configuration and fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add parent directory to path before any other imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock the config module before it's imported
mock_config_module = MagicMock()
mock_config_module.get.return_value = True
mock_config_module.load_config.return_value = {}
sys.modules["filamentbox.config"] = mock_config_module
