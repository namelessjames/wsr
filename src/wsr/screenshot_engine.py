import subprocess
import io
import logging
from PIL import Image, ImageDraw
import os

logger = logging.getLogger(__name__)

class ScreenshotEngine:
    def __init__(self):
        self.backend = self._detect_backend()
        self.cursor_icon = self._create_default_cursor()

    def _detect_backend(self):
        """Detects the available screenshot tool based on environment."""
        # Check for grim (wlroots)
        try:
            subprocess.run(["grim", "-h"], capture_output=True, check=True)
            if not os.environ.get("WAYLAND_DISPLAY"):
                logger.warning("grim gefunden, aber WAYLAND_DISPLAY ist nicht gesetzt. Screenshots könnten fehlschlagen (nutze sudo -E).")
            logger.info("Screenshot-Backend erkannt: grim")
            return "grim"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback to gnome-screenshot if available
        try:
            subprocess.run(["gnome-screenshot", "--version"], capture_output=True, check=True)
            logger.info("Screenshot-Backend erkannt: gnome-screenshot")
            return "gnome-screenshot"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        logger.warning("Kein bekanntes Screenshot-Backend (grim, gnome-screenshot) gefunden.")
        return None

    def _create_default_cursor(self):
        """Creates a simple arrow cursor placeholder as a PIL image."""
        # Simple triangle/arrow
        img = Image.new("RGBA", (24, 24), (245, 245, 245, 0))
        draw = ImageDraw.Draw(img)
        # Coordinates for a basic arrow
        draw.polygon([(0, 0), (0, 20), (5, 15), (15, 15)], fill="white", outline="black")
        return img

    def capture(self):
        """Captures a screenshot and returns it as a PIL Image object."""
        if not self.backend:
            logger.error("Kein Screenshot-Backend verfügbar.")
            return None

        try:
            if self.backend == "grim":
                # Capture to stdout
                result = subprocess.run(["grim", "-"], capture_output=True, check=True)
                return Image.open(io.BytesIO(result.stdout))
            
            elif self.backend == "gnome-screenshot":
                # gnome-screenshot usually saves to file, so we use a temp file
                temp_file = "/tmp/wsr_temp_shot.png"
                subprocess.run(["gnome-screenshot", "-f", temp_file], check=True)
                img = Image.open(temp_file)
                img.load() # Load into memory before deleting
                os.remove(temp_file)
                return img
        
        except Exception as e:
            logger.error(f"Fehler bei Screenshot-Aufnahme: {e}")
        
        return None

    def add_cursor(self, screenshot, x, y):
        """Overlays the cursor icon onto the screenshot at (x, y)."""
        if screenshot is None:
            return None
        
        # Create a copy to avoid modifying the original
        combined = screenshot.copy()
        # Ensure screenshot is RGBA for transparency support if needed
        if combined.mode != "RGBA":
            combined = combined.convert("RGBA")
        
        # Paste cursor (using the cursor itself as mask for transparency)
        combined.alpha_composite(self.cursor_icon, (int(x), int(y)))
        return combined
