"""Filament Storage Environmental Manager.

This wrapper calls `filamentbox.main:main()` so you can run:

    python run_filamentbox.py [--debug]

It is equivalent to `python -m filamentbox.main [--debug]`.
"""

from filamentbox.main import main


if __name__ == "__main__":
    main()
