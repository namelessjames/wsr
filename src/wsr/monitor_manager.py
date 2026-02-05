import subprocess
import json
import logging
import time

logger = logging.getLogger(__name__)


class MonitorManager:
    """
    Handles detection of monitor layouts and coordinate mapping.
    """

    def __init__(self):
        """
        Initializes the MonitorManager and refreshes the layout.
        """
        self.monitors = []
        self._last_refresh = 0.0
        self._refresh_cooldown = 5.0  # Seconds between refresh attempts
        self.refresh()

    def _should_refresh(self):
        """Check if cooldown has elapsed since last refresh."""
        return (time.time() - self._last_refresh) > self._refresh_cooldown

    def refresh(self):
        """
        Fetches the current monitor layout using hyprctl.
        """
        self._last_refresh = time.time()
        self.monitors = []
        try:
            # Try Hyprland
            result = subprocess.run(
                ["hyprctl", "monitors", "-j"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for mon in data:
                    self.monitors.append({
                        'name': mon['name'],
                        'x': mon['x'],
                        'y': mon['y'],
                        'width': mon['width'],
                        'height': mon['height']
                    })
                logger.debug(f"Monitore erkannt: {len(self.monitors)}")
                return
        except Exception as e:
            logger.debug(f"hyprctl fehlgeschlagen: {e}")

        logger.warning("Keine Monitordaten gefunden.")

    def get_monitor_at(self, x, y):
        """
        Returns the name of the monitor containing coordinates (x, y).
        Triggers refresh if coordinates are outside known monitors.
        """
        for mon in self.monitors:
            if (mon['x'] <= x < mon['x'] + mon['width'] and
                    mon['y'] <= y < mon['y'] + mon['height']):
                return mon['name']

        # Coordinates outside known monitors - maybe layout changed
        if self._should_refresh():
            logger.debug(f"Coordinates ({x}, {y}) outside known monitors, refreshing...")
            self.refresh()

            # Retry after refresh
            for mon in self.monitors:
                if (mon['x'] <= x < mon['x'] + mon['width'] and
                        mon['y'] <= y < mon['y'] + mon['height']):
                    return mon['name']

        return None

    def get_relative_coordinates(self, x, y, monitor_name):
        """
        Converts global coordinates to relative coordinates for a monitor.
        """
        for mon in self.monitors:
            if mon['name'] == monitor_name:
                return x - mon['x'], y - mon['y']
        return x, y

    def get_cursor_position(self):
        """
        Returns current cursor position from Hyprland.
        Returns (x, y) tuple or None on failure.
        """
        try:
            result = subprocess.run(
                ["hyprctl", "cursorpos"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                return int(parts[0]), int(parts[1])
        except Exception as e:
            logger.debug(f"hyprctl cursorpos failed: {e}")
        return None