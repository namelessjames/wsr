import base64
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, output_path):
        self.output_path = output_path
        self.header = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>WSR - Wayland Session Record</title>
    <style>
        body { font-family: sans-serif; background: #f0f0f0; margin: 20px; }
        .step { background: white; border: 1px solid #ccc; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .step img { max-width: 100%; height: auto; border: 1px solid #eee; margin-top: 10px; display: block; }
        .meta { color: #666; font-size: 0.9em; margin-bottom: 5px; }
        .description { font-weight: bold; font-size: 1.1em; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>WSR Session Record</h1>
"""
        self.footer = """
    </div>
</body>
</html>
"""

    def _img_to_base64(self, pil_img):
        """Converts a PIL Image to a Base64 string."""
        if pil_img is None:
            return ""
        buffered = io.BytesIO()
        pil_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"

    def generate(self, events):
        """Generates the HTML report from a list of events."""
        logger.info(f"Generiere Report mit {len(events)} Ereignissen...")
        
        date_str = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        
        html_parts = [self.header]
        html_parts.append(f"<p>Aufnahme vom: {date_str}</p>")
        html_parts.append('<div id="steps">')

        for event in events:
            time_str = datetime.fromtimestamp(event.get('time', 0)).strftime('%H:%M:%S.%f')[:-3]
            
            if event['type'] == 'click':
                desc = f"Mausklick: {event.get('button', 'Unknown')} bei {event.get('x')}, {event.get('y')}"
            elif event['type'] == 'key':
                desc = f"Taste gedrückt: {event.get('key', 'Unknown')}"
            elif event['type'] == 'key_group':
                desc = f"Tippen: '{event.get('text', '')}'"
            else:
                desc = f"Ereignis: {event['type']}"

            img_tag = ""
            if 'screenshot' in event:
                b64_img = self._img_to_base64(event['screenshot'])
                img_tag = f'<img src="{b64_img}" alt="Screenshot">'

            step_html = f"""
            <div class="step">
                <div class="meta">{time_str}</div>
                <div class="description">{desc}</div>
                {img_tag}
            </div>
            """
            html_parts.append(step_html)

        html_parts.append(self.footer)
        final_html = "".join(html_parts)

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write(final_html)
            logger.info(f"Report erfolgreich gespeichert unter: {self.output_path}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Reports: {e}")