import unittest
from unittest.mock import patch, MagicMock
from wsr.monitor_manager import MonitorManager


class TestMonitorManager(unittest.TestCase):
    def setUp(self):
        with patch('wsr.monitor_manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
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

    @patch('wsr.monitor_manager.subprocess.run')
    def test_get_cursor_position_success(self, mock_run):
        """Test get_cursor_position parses hyprctl output correctly."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1905, 492\n"
        )

        result = self.mgr.get_cursor_position()

        self.assertEqual(result, (1905, 492))
        mock_run.assert_called_with(
            ["hyprctl", "cursorpos"],
            capture_output=True,
            text=True
        )

    @patch('wsr.monitor_manager.subprocess.run')
    def test_get_cursor_position_failure(self, mock_run):
        """Test get_cursor_position returns None on hyprctl failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = self.mgr.get_cursor_position()

        self.assertIsNone(result)

    @patch('wsr.monitor_manager.subprocess.run')
    def test_get_cursor_position_exception(self, mock_run):
        """Test get_cursor_position returns None on exception."""
        mock_run.side_effect = FileNotFoundError("hyprctl not found")

        result = self.mgr.get_cursor_position()

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
