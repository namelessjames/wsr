import unittest
from src.report_generator import ReportGenerator
from PIL import Image
import os
import tempfile

class TestReportGenerator(unittest.TestCase):
    def test_img_to_base64(self):
        gen = ReportGenerator("dummy.html")
        img = Image.new("RGB", (10, 10), "red")
        b64 = gen._img_to_base64(img)
        self.assertTrue(b64.startswith("data:image/png;base64,"))

    def test_generate_report(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            output_path = tmp.name
        
        try:
            gen = ReportGenerator(output_path)
            events = [
                {'type': 'key', 'key': 'KEY_A', 'time': 1600000000},
                {'type': 'click', 'button': 'BTN_LEFT', 'x': 100, 'y': 200, 'time': 1600000001, 
                 'screenshot': Image.new("RGB", (10, 10), "blue")}
            ]
            
            gen.generate(events)
            
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r") as f:
                content = f.read()
                self.assertIn("WSR Session Record", content)
                self.assertIn("KEY_A", content)
                self.assertIn("BTN_LEFT", content)
                self.assertIn("data:image/png;base64,", content)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

if __name__ == '__main__':
    unittest.main()
