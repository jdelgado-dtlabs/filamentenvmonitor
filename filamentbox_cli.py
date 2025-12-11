#!/usr/bin/env python3
"""CLI interface for monitoring and controlling Filament Storage Environmental Manager.

Provides real-time display of sensor readings and control states,
with ability to manually override heater and fan controls.
"""

import curses
import sys
import time
from datetime import datetime
from typing import Optional

# Add parent directory to path to import filamentbox modules
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filamentbox.shared_state import (
    get_control_states,
    get_sensor_data,
    set_fan_manual_override,
    set_heater_manual_override,
)


def format_value(value: Optional[float], decimals: int = 1) -> str:
    """Format a numeric value or return N/A if None."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def format_timestamp(timestamp: Optional[float]) -> str:
    """Format a Unix timestamp or return N/A if None."""
    if timestamp is None:
        return "N/A"
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_age_string(timestamp: Optional[float]) -> str:
    """Get age of reading in seconds."""
    if timestamp is None:
        return "N/A"
    age = time.time() - timestamp
    if age < 60:
        return f"{age:.0f}s ago"
    elif age < 3600:
        return f"{age / 60:.0f}m ago"
    else:
        return f"{age / 3600:.1f}h ago"


def draw_ui(stdscr: "curses.window") -> None:
    """Main UI drawing loop with curses.

    Args:
        stdscr: Curses window object.
    """
    # Setup
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    stdscr.timeout(100)  # Refresh every 100ms

    # Color pairs
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # ON
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)  # OFF
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Manual
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Headers
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Normal

    while True:
        try:
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Get current data
            sensor_data = get_sensor_data()
            control_states = get_control_states()

            # Title
            title = "Filament Storage Environmental Manager"
            stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(4))

            # Sensor Readings Section
            row = 2
            stdscr.addstr(row, 2, "═" * (width - 4), curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 2, "SENSOR READINGS", curses.A_BOLD | curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 2, "═" * (width - 4), curses.color_pair(4))
            row += 1

            temp_c = sensor_data["temperature_c"]
            temp_f = sensor_data["temperature_f"]
            humidity = sensor_data["humidity"]
            timestamp = sensor_data["timestamp"]

            stdscr.addstr(
                row, 4, f"Temperature: {format_value(temp_c, 2)}°C / {format_value(temp_f, 2)}°F"
            )
            row += 1
            stdscr.addstr(row, 4, f"Humidity:    {format_value(humidity, 1)}%")
            row += 1
            stdscr.addstr(
                row, 4, f"Last Update: {format_timestamp(timestamp)} ({get_age_string(timestamp)})"
            )
            row += 2

            # Control Status Section
            stdscr.addstr(row, 2, "═" * (width - 4), curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 2, "CONTROL STATUS", curses.A_BOLD | curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 2, "═" * (width - 4), curses.color_pair(4))
            row += 1

            # Heater status
            heater_on = control_states["heater_on"]
            heater_manual = control_states["heater_manual"]
            heater_status = "ON " if heater_on else "OFF"
            heater_color = curses.color_pair(1) if heater_on else curses.color_pair(2)
            heater_mode = "MANUAL" if heater_manual is not None else "AUTO"
            heater_mode_color = (
                curses.color_pair(3) if heater_manual is not None else curses.color_pair(5)
            )

            stdscr.addstr(row, 4, "Heater: ")
            stdscr.addstr(heater_status, curses.A_BOLD | heater_color)
            stdscr.addstr(" [")
            stdscr.addstr(heater_mode, heater_mode_color)
            stdscr.addstr("]")
            row += 1

            # Fan status
            fan_on = control_states["fan_on"]
            fan_manual = control_states["fan_manual"]
            fan_status = "ON " if fan_on else "OFF"
            fan_color = curses.color_pair(1) if fan_on else curses.color_pair(2)
            fan_mode = "MANUAL" if fan_manual is not None else "AUTO"
            fan_mode_color = (
                curses.color_pair(3) if fan_manual is not None else curses.color_pair(5)
            )

            stdscr.addstr(row, 4, "Fan:    ")
            stdscr.addstr(fan_status, curses.A_BOLD | fan_color)
            stdscr.addstr(" [")
            stdscr.addstr(fan_mode, fan_mode_color)
            stdscr.addstr("]")
            row += 2

            # Controls Section
            stdscr.addstr(row, 2, "═" * (width - 4), curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 2, "MANUAL CONTROLS", curses.A_BOLD | curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 2, "═" * (width - 4), curses.color_pair(4))
            row += 1

            stdscr.addstr(row, 4, "Heater:  [H] Turn ON  [h] Turn OFF  [Ctrl+H] Auto")
            row += 1
            stdscr.addstr(row, 4, "Fan:     [F] Turn ON  [f] Turn OFF  [Ctrl+F] Auto")
            row += 2

            # Help
            stdscr.addstr(row, 2, "─" * (width - 4), curses.color_pair(4))
            row += 1
            stdscr.addstr(row, 4, "[R] Refresh  [Q] Quit", curses.color_pair(5))

            # Footer
            if height > row + 2:
                footer = "Press Q to quit"
                stdscr.addstr(height - 1, (width - len(footer)) // 2, footer, curses.color_pair(5))

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()
            if key == ord("q") or key == ord("Q"):
                break
            elif key == ord("H"):  # Heater ON
                set_heater_manual_override(True)
            elif key == ord("h"):  # Heater OFF
                set_heater_manual_override(False)
            elif key == 8:  # Ctrl+H (Backspace in some terminals)
                set_heater_manual_override(None)
            elif key == ord("F"):  # Fan ON
                set_fan_manual_override(True)
            elif key == ord("f"):  # Fan OFF
                set_fan_manual_override(False)
            elif key == 6:  # Ctrl+F
                set_fan_manual_override(None)
            elif key == ord("r") or key == ord("R"):
                continue  # Refresh

            time.sleep(0.1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            stdscr.addstr(height - 2, 2, f"Error: {str(e)}", curses.color_pair(2))
            stdscr.refresh()
            time.sleep(1)


def main() -> None:
    """Main entry point for CLI interface."""
    try:
        curses.wrapper(draw_ui)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
