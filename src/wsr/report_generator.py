import base64
import io
import logging
import os
from datetime import datetime
from PIL import Image
from .i18n import _

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Handles the generation of an HTML report from captured session events.
    """

    def __init__(self, output_path, lang="en", custom_style_path=None, image_format="png", image_quality=0.9):
        """
        Initializes the ReportGenerator.

        Args:
            output_path (str): Path where the final HTML will be saved.
            lang (str): Language code for HTML lang attribute (e.g. 'de', 'en').
            custom_style_path (str): Optional path to custom CSS file.
            image_format (str): Output format ('png', 'jpg', 'webp').
            image_quality (float): Quality for lossy formats (0.1-1.0).
        """
        self.output_path = output_path
        self.lang = lang
        self.custom_css = self._load_custom_css(custom_style_path)
        self.image_format = image_format
        self.image_quality = image_quality

    def _load_custom_css(self, style_path):
        """Load custom CSS from file if provided and exists."""
        if not style_path or not os.path.isfile(style_path):
            return None
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            logger.warning("Could not load custom CSS: %s", e)
            return None

    def _custom_style_tag(self):
        """Return custom style tag if custom CSS is loaded."""
        if self.custom_css:
            return f"    <style>\n/* Custom user styles */\n{self.custom_css}\n    </style>\n"
        return ""

    def _build_header(self):
        """Build HTML header with dynamic lang and optional custom styles."""
        return f"""<!DOCTYPE html>
<html lang="{self.lang}">
<head>
    <meta charset="UTF-8">
    <title>{_('report_title')}</title>
    <style>
        :root {{
            --bg-color: #f0f0f0;
            --card-bg: #ffffff;
            --text-color: #333333;
            --meta-color: #666666;
            --border-color: #cccccc;
            --shadow: rgba(0,0,0,0.1);
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #121212;
                --card-bg: #1e1e1e;
                --text-color: #e0e0e0;
                --meta-color: #b0b0b0;
                --border-color: #333333;
                --shadow: rgba(0,0,0,0.5);
            }}
        }}

        body {{
            font-family: sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            margin: 20px;
            transition: background 0.3s, color 0.3s;
        }}
        .step {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px var(--shadow);
        }}
        .step img {{
            max-width: 100%;
            height: auto;
            border: 1px solid var(--border-color);
            margin-top: 10px;
            display: block;
        }}
        .meta {{
            color: var(--meta-color);
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .description {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        h1 {{
            color: var(--text-color);
        }}
    </style>
{self._custom_style_tag()}</head>
<body>
    <h1>{_('report_header')}</h1>
"""

    def _build_footer(self):
        """Build HTML footer."""
        return """    </div>
</body>
</html>
"""

    def _img_to_base64(self, event):
        """
        Returns Base64 data URI from event's screenshot data.
        
        Supports two formats:
        - New: pre-compressed bytes in event['screenshot_bytes'] + event['screenshot_mime']
        - Legacy: PIL.Image in event['screenshot'] (for backwards compatibility)
        """
        # New format: already compressed bytes (memory-efficient path)
        if 'screenshot_bytes' in event:
            img_str = base64.b64encode(event['screenshot_bytes']).decode("utf-8")
            return f"data:{event['screenshot_mime']};base64,{img_str}"
        
        # Legacy format: PIL.Image (kept for backwards compatibility)
        if 'screenshot' in event:
            return self._legacy_pil_to_base64(event['screenshot'])
        
        return ""

    def _legacy_pil_to_base64(self, pil_img):
        """
        Converts a PIL Image to a Base64 string using configured format and quality.
        Legacy path - only used if screenshot wasn't pre-compressed.
        """
        if pil_img is None:
            return ""

        # Mapping for PIL and Data URI
        fmt = self.image_format.lower()
        pil_format = "PNG"
        mime_type = "image/png"
        save_kwargs = {}

        if fmt in ("jpg", "jpeg"):
            pil_format = "JPEG"
            mime_type = "image/jpeg"
            save_kwargs["quality"] = int(self.image_quality * 100)
            # JPEG doesn't support alpha channel
            if pil_img.mode in ("RGBA", "LA", "P"):
                # Create a white background
                background = Image.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == "P":
                    pil_img = pil_img.convert("RGBA")
                background.paste(pil_img, mask=pil_img.split()[3] if pil_img.mode == "RGBA" else None)
                pil_img = background
        elif fmt == "webp":
            pil_format = "WEBP"
            mime_type = "image/webp"
            save_kwargs["quality"] = int(self.image_quality * 100)

        buffered = io.BytesIO()
        pil_img.save(buffered, format=pil_format, **save_kwargs)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:{mime_type};base64,{img_str}"

    def generate(self, events):
        """
        Generates the HTML report from a list of events.

        Args:
            events (list): List of event dictionaries to include in the report.
        """
        date_str = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

        html_parts = [self._build_header()]
        html_parts.append(f"<p>{_('report_date', date=date_str)}</p>")
        html_parts.append('<div id="steps">')

        for event in events:
            time_str = datetime.fromtimestamp(
                event.get('time', 0)
            ).strftime('%H:%M:%S.%f')[:-3]

            if event['type'] == 'click':
                desc = _('desc_click', 
                          button=event.get('button', 'Unknown'),
                          x=event.get('x'), 
                          y=event.get('y'))
            elif event['type'] == 'key':
                desc = _('desc_key', key=event.get('key', 'Unknown'))
            elif event['type'] == 'key_group':
                desc = _('desc_typing', text=event.get('text', ''))
            else:
                desc = f"{_('Ereignis')}: {event['type']}"

            img_tag = ""
            if 'screenshot_bytes' in event or 'screenshot' in event:
                b64_img = self._img_to_base64(event)
                if b64_img:
                    img_tag = f'<img src="{b64_img}" alt="Screenshot">'

            step_html = f"""
            <div class="step">
                <div class="meta">{time_str}</div>
                <div class="description">{desc}</div>
                {img_tag}
            </div>
            """
            html_parts.append(step_html)

        html_parts.append(self._build_footer())
        final_html = "".join(html_parts)

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write(final_html)
            logger.info(_("report_saved", path=self.output_path))
        except Exception as e:
            logger.error(f"Error saving report: {e}")
