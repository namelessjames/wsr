import subprocess
import json
import logging

logger = logging.getLogger(__name__)

class MonitorManager:
    def __init__(self):
        self.monitors = []
        self.refresh()

    def refresh(self):
        """Fetches the current monitor layout."""
        self.monitors = []
        try:
            # Try Hyprland
            result = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True)
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
                logger.debug(f"Monitore via hyprctl erkannt: {len(self.monitors)}")
                return
        except Exception as e:
            logger.debug(f"hyprctl fehlgeschlagen: {e}")

        # Fallback for other wlroots (very basic parser for wlr-randr could be added here)
        logger.warning("Keine Monitordaten gefunden. Multi-Monitor Mapping deaktiviert.")

    def get_monitor_at(self, x, y):
        """Returns the name of the monitor containing coordinates (x, y)."""
        for mon in self.monitors:
            if (mon['x'] <= x < mon['x'] + mon['width'] and
                mon['y'] <= y < mon['y'] + mon['height']):
                return mon['name']
        return None

    def get_relative_coordinates(self, x, y, monitor_name):
        """Converts global coordinates to relative coordinates for a specific monitor."""
        for mon in self.monitors:
            if mon['name'] == monitor_name:
                return x - mon['x'], y - mon['y']
        return x, y
