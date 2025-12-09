"""Base interface for time series database adapters.

This module defines the abstract base class that all time series database
adapters must implement to provide consistent data writing capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any


class TimeSeriesDB(ABC):
    """Abstract base class for time series database adapters.

    All database adapters must implement this interface to ensure
    consistent behavior across different time series databases.
    """

    @abstractmethod
    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the database adapter with configuration.

        Args:
            config: Database-specific configuration dictionary.
        """
        pass

    @abstractmethod
    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a batch of data points to the time series database.

        Args:
            points: List of data point dictionaries to write.

        Raises:
            Exception: If write operation fails.
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the database connection.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection and cleanup resources."""
        pass
