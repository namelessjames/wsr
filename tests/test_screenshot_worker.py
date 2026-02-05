"""
Tests for the ScreenshotWorker async screenshot processing.
"""

import unittest
import time
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from wsr.screenshot_worker import ScreenshotWorker


class TestScreenshotWorker(unittest.TestCase):
    """Tests for ScreenshotWorker."""
    
    def setUp(self):
        """Set up mock screenshot engine."""
        self.mock_engine = MagicMock()
        self.mock_engine.capture_with_cursor_compressed.return_value = (
            b"fake_image_bytes",
            "image/png"
        )
    
    def tearDown(self):
        """Ensure worker is shut down."""
        if hasattr(self, 'worker'):
            try:
                self.worker.shutdown(wait=False)
            except Exception:
                pass
    
    def test_init(self):
        """Worker initializes with engine and executor."""
        worker = ScreenshotWorker(self.mock_engine, max_workers=2)
        self.worker = worker
        
        self.assertEqual(worker.engine, self.mock_engine)
        self.assertIsInstance(worker.executor, ThreadPoolExecutor)
        self.assertEqual(worker.futures, [])
        self.assertFalse(worker._shutdown)
    
    def test_request_screenshot_queues_work(self):
        """request_screenshot() submits work to executor."""
        worker = ScreenshotWorker(self.mock_engine, max_workers=1)
        self.worker = worker
        
        event = {'type': 'click', 'x': 100, 'y': 200}
        worker.request_screenshot(event, "eDP-1", 100, 200)
        
        # Should have one pending future
        self.assertEqual(len(worker.futures), 1)
    
    def test_async_event_mutation(self):
        """Screenshot bytes are added to event dict asynchronously."""
        worker = ScreenshotWorker(self.mock_engine, max_workers=1)
        self.worker = worker
        
        event = {'type': 'click', 'x': 100, 'y': 200}
        worker.request_screenshot(event, "eDP-1", 100, 200)
        
        # Wait for completion
        worker.wait_for_pending(timeout=2.0)
        
        # Event should now have screenshot data
        self.assertEqual(event['screenshot_bytes'], b"fake_image_bytes")
        self.assertEqual(event['screenshot_mime'], "image/png")
        
        # Engine should have been called
        self.mock_engine.capture_with_cursor_compressed.assert_called_once_with(
            100, 200,
            monitor_name="eDP-1",
            format="png",
            quality=90
        )
    
    def test_pending_count(self):
        """pending_count() tracks incomplete futures."""
        # Use slow mock to keep futures pending
        def slow_capture(*args, **kwargs):
            time.sleep(0.5)
            return (b"bytes", "image/png")
        
        self.mock_engine.capture_with_cursor_compressed.side_effect = slow_capture
        worker = ScreenshotWorker(self.mock_engine, max_workers=1)
        self.worker = worker
        
        event1 = {'type': 'click'}
        event2 = {'type': 'click'}
        
        worker.request_screenshot(event1, "eDP-1", 0, 0)
        worker.request_screenshot(event2, "eDP-1", 0, 0)
        
        # Should have 2 pending (or 1 if first already started)
        pending = worker.pending_count()
        self.assertGreaterEqual(pending, 1)
        self.assertLessEqual(pending, 2)
        
        # Wait and check again
        worker.wait_for_pending(timeout=3.0)
        self.assertEqual(worker.pending_count(), 0)
    
    def test_wait_for_pending_clears_futures(self):
        """wait_for_pending() clears the futures list."""
        worker = ScreenshotWorker(self.mock_engine, max_workers=2)
        self.worker = worker
        
        for _ in range(3):
            worker.request_screenshot({'type': 'click'}, "eDP-1", 0, 0)
        
        self.assertEqual(len(worker.futures), 3)
        
        completed = worker.wait_for_pending(timeout=2.0)
        
        self.assertEqual(completed, 3)
        self.assertEqual(len(worker.futures), 0)
    
    def test_shutdown_prevents_new_requests(self):
        """After shutdown(), new requests are ignored."""
        worker = ScreenshotWorker(self.mock_engine, max_workers=1)
        self.worker = worker
        
        worker.shutdown(wait=True)
        
        event = {'type': 'click'}
        worker.request_screenshot(event, "eDP-1", 0, 0)
        
        # Should not have queued anything
        self.assertEqual(len(worker.futures), 0)
        self.assertNotIn('screenshot_bytes', event)
    
    def test_capture_failure_logged(self):
        """Capture exceptions are logged, not raised."""
        self.mock_engine.capture_with_cursor_compressed.side_effect = RuntimeError("grim failed")
        worker = ScreenshotWorker(self.mock_engine, max_workers=1)
        self.worker = worker
        
        event = {'type': 'click'}
        worker.request_screenshot(event, "eDP-1", 0, 0)
        
        # Should not raise
        worker.wait_for_pending(timeout=2.0)
        
        # Event should not have screenshot
        self.assertNotIn('screenshot_bytes', event)
    
    def test_image_format_and_quality_passed(self):
        """Custom image format and quality are passed to engine."""
        worker = ScreenshotWorker(self.mock_engine, max_workers=1)
        self.worker = worker
        
        event = {'type': 'click'}
        worker.request_screenshot(
            event, "HDMI-1", 50, 75,
            image_format="webp",
            image_quality=80
        )
        
        worker.wait_for_pending(timeout=2.0)
        
        self.mock_engine.capture_with_cursor_compressed.assert_called_once_with(
            50, 75,
            monitor_name="HDMI-1",
            format="webp",
            quality=80
        )
    
    def test_multiple_parallel_captures(self):
        """Multiple screenshots can be processed in parallel."""
        capture_times = []
        
        def timed_capture(*args, **kwargs):
            start = time.time()
            time.sleep(0.2)
            capture_times.append(time.time() - start)
            return (b"bytes", "image/png")
        
        self.mock_engine.capture_with_cursor_compressed.side_effect = timed_capture
        worker = ScreenshotWorker(self.mock_engine, max_workers=2)
        self.worker = worker
        
        # Queue 2 screenshots
        start = time.time()
        worker.request_screenshot({'type': 'click'}, "eDP-1", 0, 0)
        worker.request_screenshot({'type': 'click'}, "eDP-1", 0, 0)
        
        worker.wait_for_pending(timeout=2.0)
        total_time = time.time() - start
        
        # With 2 workers, 2 x 0.2s tasks should complete in ~0.2s, not 0.4s
        # Allow some slack for thread overhead
        self.assertLess(total_time, 0.5)


class TestScreenshotWorkerNoneResult(unittest.TestCase):
    """Test handling of None screenshot results."""
    
    def test_none_result_not_added_to_event(self):
        """If capture returns None, event is not updated."""
        mock_engine = MagicMock()
        mock_engine.capture_with_cursor_compressed.return_value = (None, None)
        
        worker = ScreenshotWorker(mock_engine, max_workers=1)
        
        event = {'type': 'click'}
        worker.request_screenshot(event, "eDP-1", 0, 0)
        worker.wait_for_pending(timeout=2.0)
        
        self.assertNotIn('screenshot_bytes', event)
        self.assertNotIn('screenshot_mime', event)
        
        worker.shutdown(wait=False)


if __name__ == '__main__':
    unittest.main()
