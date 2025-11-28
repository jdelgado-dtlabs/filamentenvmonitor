"""Logging configuration utilities.

Sets up dual-stream logging: DEBUG/INFO/WARNING to stdout, ERROR+ to stderr.
"""

import logging
import sys


class _MaxLevelFilter(logging.Filter):
    """Filter permitting only records up to provided max level (inclusive)."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        return record.levelno <= self.max_level


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger handlers and levels for application logging."""
    root = logging.getLogger()
    # remove existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(_MaxLevelFilter(logging.WARNING))
    stdout_handler.setFormatter(fmt)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(fmt)

    root.setLevel(level)
    root.addHandler(stdout_handler)
    root.addHandler(stderr_handler)
