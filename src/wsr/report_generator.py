import base64
import io
import logging
from datetime import datetime
from .i18n import _

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Handles the generation of an HTML report from captured session events.
    """

    def __init__(self, output_path):
        """
        Initializes the ReportGenerator.

        Args:
            output_path (str): Path where the final HTML will be saved.
        """
        self.output_path = output_path
        self.header = f"""
<!DOCTYPE html>
<html lang="de">
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
</head>
<body>
    <h1>{_('report_header')}</h1>
"""
        self.footer = """
    </div>
</body>
</html>
"""

    def _img_to_base64(self, pil_img):
        """
        Converts a PIL Image to a Base64 string.
        """
        if pil_img is None:
            return ""
        buffered = io.BytesIO()
        pil_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"

    def generate(self, events):
        """
        Generates the HTML report from a list of events.

        Args:
            events (list): List of event dictionaries to include in the report.
        """
        date_str = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

        html_parts = [self.header]
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
            logger.info(_("report_saved", path=self.output_path))
        except Exception as e:
            logger.error(f"Error saving report: {e}")
