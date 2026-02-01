import subprocess
import io
import logging
import os
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class ScreenshotEngine:
    """
    Handles screenshot capturing and cursor overlaying.
    """

    def __init__(self):
        """
        Initializes the ScreenshotEngine and detects the backend.
        """
        self.backend = self._detect_backend()
        self.cursor_icon = self._create_default_cursor()

    def _detect_backend(self):
        """
        Detects the available screenshot tool based on environment.
        """
        # Check for grim (wlroots)
        try:
            subprocess.run(["grim", "-h"], capture_output=True, check=True)
            if not os.environ.get("WAYLAND_DISPLAY"):
                logger.warning(
                    "grim gefunden, aber WAYLAND_DISPLAY fehlt. "
                    "Nutze sudo -E."
                )
            logger.info("Screenshot-Backend erkannt: grim")
            return "grim"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback to gnome-screenshot
        try:
            subprocess.run(
                ["gnome-screenshot", "--version"],
                capture_output=True,
                check=True
            )
            logger.info("Screenshot-Backend erkannt: gnome-screenshot")
            return "gnome-screenshot"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        logger.warning("Kein Screenshot-Backend gefunden.")
        return None

    def _create_default_cursor(self):
        """
        Creates a simple arrow cursor placeholder as a PIL image.
        """
        img = Image.new("RGBA", (24, 24), (245, 245, 245, 0))
        draw = ImageDraw.Draw(img)
        draw.polygon(
            [(0, 0), (0, 20), (5, 15), (15, 15)],
            fill="white",
            outline="black"
        )
        return img

    def capture(self, monitor_name=None):
        """
        Captures a screenshot and returns it as a PIL Image object.
        """
        if not self.backend:
            logger.error("Kein Screenshot-Backend verfügbar.")
            return None

        try:
            if self.backend == "grim":
                cmd = ["grim"]
                if monitor_name:
                    cmd.extend(["-o", monitor_name])
                cmd.append("-")

                result = subprocess.run(cmd, capture_output=True, check=True)
                return Image.open(io.BytesIO(result.stdout))

            elif self.backend == "gnome-screenshot":
                temp_file = "/tmp/wsr_temp_shot.png"
                subprocess.run(
                    ["gnome-screenshot", "-f", temp_file],
                    check=True
                )
                img = Image.open(temp_file)
                img.load()
                os.remove(temp_file)
                return img

        except Exception as e:
            logger.error(f"Fehler bei Screenshot-Aufnahme ({self.backend}): {e}")

        return None

    def add_cursor(self, screenshot, x, y):
        """
        Overlays the cursor icon onto the screenshot at (x, y).
        """
        if screenshot is None:
            return None

        combined = screenshot.copy()
        if combined.mode != "RGBA":
            combined = combined.convert("RGBA")

        combined.alpha_composite(self.cursor_icon, (int(x), int(y)))
        return combined