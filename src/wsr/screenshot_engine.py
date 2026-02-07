import subprocess
import io
import logging
import os
import tempfile
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
                fd, temp_file = tempfile.mkstemp(suffix=".png", prefix="wsr_")
                os.close(fd)
                try:
                    subprocess.run(
                        ["gnome-screenshot", "-f", temp_file],
                        check=True
                    )
                    img = Image.open(temp_file)
                    img.load()
                    return img
                finally:
                    try:
                        os.unlink(temp_file)
                    except OSError:
                        pass

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

    def capture_with_cursor_compressed(self, x, y, monitor_name=None, 
                                        format="webp", quality=80):
        """
        Captures a screenshot with cursor overlay and returns compressed bytes.
        
        This is the memory-efficient path: instead of holding a 31.6 MB PIL.Image
        in RAM, we compress immediately to ~50-200 KB.
        
        Args:
            x: Cursor x position (relative to monitor)
            y: Cursor y position (relative to monitor)
            monitor_name: Target monitor (None for primary)
            format: Image format ('webp', 'jpg', 'jpeg', 'png')
            quality: Compression quality for lossy formats (1-100)
            
        Returns:
            tuple: (bytes, mime_type) or (None, None) on failure
        """
        img = self.capture(monitor_name)
        if img is None:
            return None, None
        
        # Add cursor overlay
        img = self.add_cursor(img, x, y)
        if img is None:
            return None, None
        
        buffered = io.BytesIO()
        
        if format == "webp":
            img.save(buffered, format="WEBP", quality=quality)
            return buffered.getvalue(), "image/webp"
        elif format in ("jpg", "jpeg"):
            # JPEG doesn't support alpha - composite onto white background
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background
            img.save(buffered, format="JPEG", quality=quality)
            return buffered.getvalue(), "image/jpeg"
        else:
            # PNG - lossless, no quality param
            img.save(buffered, format="PNG")
            return buffered.getvalue(), "image/png"