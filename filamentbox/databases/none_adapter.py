"""None/Disabled adapter for when data collection is disabled.

Implements the TimeSeriesDB interface but performs no actual database operations.
"""

import logging
from typing import Any

from .base import TimeSeriesDB


class NoneAdapter(TimeSeriesDB):
    """Null adapter that discards all data (used when data collection is disabled)."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the None adapter.

        Args:
            config: Configuration dictionary (ignored for None adapter)
        """
        self.config = config
        logging.info(
            "Initialized None adapter - data collection disabled, all data will be discarded"
        )

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Discard data points without writing anywhere.

        Args:
            points: List of data point dictionaries (discarded)
        """
        logging.debug(f"None adapter: discarding {len(points)} points")

    def test_connection(self) -> bool:
        """Always returns True since there's no actual connection.

        Returns:
            bool: Always True
        """
        return True

    def close(self) -> None:
        """No-op close method since there's no connection."""
        logging.debug("None adapter closed (no connection to close)")
