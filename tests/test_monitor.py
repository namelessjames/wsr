import unittest
from wsr.monitor_manager import MonitorManager

class TestMonitorManager(unittest.TestCase):
    def setUp(self):
        self.mgr = MonitorManager()
        # Mock monitor setup
        self.mgr.monitors = [
            {'name': 'eDP-1', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
            {'name': 'DP-1', 'x': 1920, 'y': 0, 'width': 2560, 'height': 1440}
        ]

    def test_get_monitor_at(self):
        self.assertEqual(self.mgr.get_monitor_at(500, 500), 'eDP-1')
        self.assertEqual(self.mgr.get_monitor_at(2000, 500), 'DP-1')
        self.assertIsNone(self.mgr.get_monitor_at(5000, 500))

    def test_get_relative_coordinates(self):
        self.assertEqual(self.mgr.get_relative_coordinates(2000, 500, 'DP-1'), (80, 500))
        self.assertEqual(self.mgr.get_relative_coordinates(500, 500, 'eDP-1'), (500, 500))

if __name__ == '__main__':
    unittest.main()
