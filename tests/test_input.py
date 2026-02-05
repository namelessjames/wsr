import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock evdev module since it might not be installed in the test environment
sys.modules['evdev'] = MagicMock()
sys.modules['evdev.ecodes'] = MagicMock()
# Setup some constants usually found in ecodes
sys.modules['evdev'].ecodes.EV_REL = 2
sys.modules['evdev'].ecodes.EV_KEY = 1
sys.modules['evdev'].ecodes.REL_X = 0
sys.modules['evdev'].ecodes.REL_Y = 1
sys.modules['evdev'].ecodes.BTN_LEFT = 272
sys.modules['evdev'].ecodes.BTN_RIGHT = 273
sys.modules['evdev'].ecodes.BTN_MIDDLE = 274
sys.modules['evdev'].ecodes.KEY_A = 30
sys.modules['evdev'].ecodes.KEY = {30: 'KEY_A'}
sys.modules['evdev'].ecodes.BTN = {272: 'BTN_LEFT', 273: 'BTN_RIGHT', 274: 'BTN_MIDDLE'}

# Now import the module to test
from wsr.input_manager import InputManager


class TestInputManager(unittest.TestCase):
    def setUp(self):
        self.cursor_fn = MagicMock(return_value=(100, 200))
        self.mgr = InputManager(cursor_position_fn=self.cursor_fn)

    @patch('wsr.input_manager.evdev.list_devices')
    @patch('wsr.input_manager.evdev.InputDevice')
    def test_find_devices(self, mock_input_device, mock_list_devices):
        # Mock device paths
        mock_list_devices.return_value = ['/dev/input/event0']

        # Mock device capabilities
        mock_dev = MagicMock()
        mock_dev.capabilities.return_value = {
            sys.modules['evdev'].ecodes.EV_REL: [0, 1],
            sys.modules['evdev'].ecodes.EV_KEY: [30]  # Key A
        }
        mock_input_device.return_value = mock_dev

        self.mgr.find_devices()

        # Should be identified as both mouse and keyboard based on current loose logic
        self.assertEqual(len(self.mgr.mouse_devices), 1)
        self.assertEqual(len(self.mgr.keyboard_devices), 1)

    def test_click_uses_cursor_position_fn(self):
        """Test that click events use the cursor_position_fn callback."""
        mock_event = MagicMock()
        mock_event.type = sys.modules['evdev'].ecodes.EV_KEY
        mock_event.code = sys.modules['evdev'].ecodes.BTN_LEFT
        mock_event.value = 1  # Key down

        self.mgr._handle_event(MagicMock(), mock_event)

        # cursor_position_fn should have been called
        self.cursor_fn.assert_called_once()

        # Check event was put in queue with correct coordinates
        event = self.mgr.event_queue.get_nowait()
        self.assertEqual(event['type'], 'click')
        self.assertEqual(event['x'], 100)
        self.assertEqual(event['y'], 200)

    def test_click_with_no_cursor_fn(self):
        """Test that click events work without cursor_position_fn (fallback to 0,0)."""
        mgr_no_fn = InputManager(cursor_position_fn=None)

        mock_event = MagicMock()
        mock_event.type = sys.modules['evdev'].ecodes.EV_KEY
        mock_event.code = sys.modules['evdev'].ecodes.BTN_LEFT
        mock_event.value = 1

        mgr_no_fn._handle_event(MagicMock(), mock_event)

        event = mgr_no_fn.event_queue.get_nowait()
        self.assertEqual(event['x'], 0)
        self.assertEqual(event['y'], 0)

    def test_click_with_cursor_fn_returning_none(self):
        """Test fallback when cursor_position_fn returns None."""
        failing_fn = MagicMock(return_value=None)
        mgr = InputManager(cursor_position_fn=failing_fn)

        mock_event = MagicMock()
        mock_event.type = sys.modules['evdev'].ecodes.EV_KEY
        mock_event.code = sys.modules['evdev'].ecodes.BTN_LEFT
        mock_event.value = 1

        mgr._handle_event(MagicMock(), mock_event)

        event = mgr.event_queue.get_nowait()
        self.assertEqual(event['x'], 0)
        self.assertEqual(event['y'], 0)


if __name__ == '__main__':
    unittest.main()
