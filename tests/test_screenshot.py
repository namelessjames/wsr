import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
from wsr.screenshot_engine import ScreenshotEngine
import io

class TestScreenshotEngine(unittest.TestCase):
    def setUp(self):
        # Prevent auto-detection during init if needed, or just mock subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=b'grim -h')
            self.engine = ScreenshotEngine()

    def test_create_default_cursor(self):
        cursor = self.engine._create_default_cursor()
        self.assertIsInstance(cursor, Image.Image)
        self.assertEqual(cursor.size, (24, 24))

    @patch('subprocess.run')
    def test_capture_grim(self, mock_run):
        self.engine.backend = "grim"
        # Create a fake PNG image in bytes
        img = Image.new("RGB", (100, 100), "red")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        
        mock_run.return_value = MagicMock(stdout=img_byte_arr.getvalue())
        
        captured = self.engine.capture()
        self.assertIsInstance(captured, Image.Image)
        self.assertEqual(captured.size, (100, 100))

    def test_add_cursor(self):
        img = Image.new("RGB", (100, 100), "blue")
        result = self.engine.add_cursor(img, 50, 50)
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (100, 100))
        # Check if it's RGBA now
        self.assertEqual(result.mode, "RGBA")

if __name__ == '__main__':
    unittest.main()
