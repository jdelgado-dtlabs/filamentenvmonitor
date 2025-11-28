#!/opt/filamentcontrol/filamentcontrol/bin/python
"""FilamentBox Environment Data Logger - Main Entry Point.

This is a thin wrapper around the filamentbox package. Run this script directly
or use `python -m filamentbox` to start the logger.
"""

from filamentbox.main import main

if __name__ == "__main__":
    main()
