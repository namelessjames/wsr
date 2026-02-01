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
sys.modules['evdev'].ecodes.KEY_A = 30
sys.modules['evdev'].ecodes.KEY = {30: 'KEY_A'}
sys.modules['evdev'].ecodes.BTN = {272: 'BTN_LEFT'}

# Now import the module to test
from wsr.input_manager import InputManager

class TestInputManager(unittest.TestCase):
    def setUp(self):
        self.mgr = InputManager()
    
    @patch('wsr.input_manager.evdev.list_devices')
    @patch('wsr.input_manager.evdev.InputDevice')
    def test_find_devices(self, mock_input_device, mock_list_devices):
        # Mock device paths
        mock_list_devices.return_value = ['/dev/input/event0']
        
        # Mock device capabilities
        mock_dev = MagicMock()
        mock_dev.capabilities.return_value = {
            sys.modules['evdev'].ecodes.EV_REL: [0, 1],
            sys.modules['evdev'].ecodes.EV_KEY: [30] # Key A
        }
        mock_input_device.return_value = mock_dev
        
        self.mgr.find_devices()
        
        # Should be identified as both mouse and keyboard based on current loose logic
        self.assertEqual(len(self.mgr.mouse_devices), 1)
        self.assertEqual(len(self.mgr.keyboard_devices), 1)

    def test_mouse_tracking(self):
        # Create a dummy event object
        mock_event = MagicMock()
        mock_event.type = sys.modules['evdev'].ecodes.EV_REL
        mock_event.code = sys.modules['evdev'].ecodes.REL_X
        mock_event.value = 10
        
        self.mgr._handle_event(MagicMock(), mock_event)
        self.assertEqual(self.mgr.mouse_x, 970) # 960 + 10

if __name__ == '__main__':
    unittest.main()
