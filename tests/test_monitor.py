import unittest
from unittest.mock import patch, MagicMock
import time
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


class TestMonitorManagerLazyRefresh(unittest.TestCase):
    """Tests for lazy refresh and throttling behavior."""

    def setUp(self):
        with patch('wsr.monitor_manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            self.mgr = MonitorManager()
        self.mgr.monitors = [
            {'name': 'eDP-1', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
        ]

    def test_throttle_state_initialized(self):
        """Test that throttle state attributes are initialized."""
        with patch('wsr.monitor_manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            mgr = MonitorManager()

        self.assertIsInstance(mgr._last_refresh, float)
        self.assertEqual(mgr._refresh_cooldown, 5.0)

    def test_should_refresh_after_cooldown(self):
        """Test _should_refresh returns True after cooldown elapsed."""
        self.mgr._last_refresh = time.time() - 10.0  # 10 seconds ago
        self.assertTrue(self.mgr._should_refresh())

    def test_should_not_refresh_during_cooldown(self):
        """Test _should_refresh returns False during cooldown."""
        self.mgr._last_refresh = time.time() - 2.0  # 2 seconds ago
        self.assertFalse(self.mgr._should_refresh())

    @patch('wsr.monitor_manager.subprocess.run')
    def test_get_monitor_at_triggers_refresh_on_miss(self, mock_run):
        """Test that get_monitor_at triggers refresh when coords outside known monitors."""
        # Set up: cooldown elapsed, coords outside known monitors
        self.mgr._last_refresh = time.time() - 10.0

        # Mock hyprctl to return a new monitor at the requested position
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "DP-1", "x": 1920, "y": 0, "width": 2560, "height": 1440}]'
        )

        # Query coords on the "new" monitor
        result = self.mgr.get_monitor_at(2000, 500)

        # Should have called refresh and found the monitor
        mock_run.assert_called_once()
        self.assertEqual(result, 'DP-1')

    @patch('wsr.monitor_manager.subprocess.run')
    def test_get_monitor_at_respects_cooldown(self, mock_run):
        """Test that get_monitor_at does not refresh during cooldown."""
        # Set up: cooldown NOT elapsed
        self.mgr._last_refresh = time.time() - 2.0

        # Query coords outside known monitors
        result = self.mgr.get_monitor_at(5000, 500)

        # Should NOT have called refresh
        mock_run.assert_not_called()
        self.assertIsNone(result)

    @patch('wsr.monitor_manager.subprocess.run')
    def test_refresh_updates_last_refresh_time(self, mock_run):
        """Test that refresh() updates _last_refresh timestamp."""
        mock_run.return_value = MagicMock(returncode=1)
        old_time = self.mgr._last_refresh

        time.sleep(0.01)  # Ensure time advances
        self.mgr.refresh()

        self.assertGreater(self.mgr._last_refresh, old_time)

    def test_get_monitor_at_no_refresh_when_found(self):
        """Test that get_monitor_at does not refresh when monitor is found."""
        self.mgr._last_refresh = time.time() - 10.0  # Cooldown elapsed
        initial_refresh_time = self.mgr._last_refresh

        # Query coords inside known monitor
        result = self.mgr.get_monitor_at(500, 500)

        # Should find monitor without refreshing
        self.assertEqual(result, 'eDP-1')
        self.assertEqual(self.mgr._last_refresh, initial_refresh_time)


if __name__ == '__main__':
    unittest.main()
