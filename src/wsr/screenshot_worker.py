"""
Asynchronous screenshot processing using a ThreadPoolExecutor.

This module decouples screenshot capture from the main event loop,
preventing UI lag during rapid click sequences.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Optional, Tuple

from .screenshot_engine import ScreenshotEngine

logger = logging.getLogger(__name__)


class ScreenshotWorker:
    """
    Processes screenshot requests in background threads.
    
    Screenshots are captured asynchronously - the main thread queues requests
    and continues processing events without blocking on grim/gnome-screenshot.
    """
    
    def __init__(self, screenshot_engine: ScreenshotEngine, max_workers: int = 2):
        """
        Initialize the screenshot worker.
        
        Args:
            screenshot_engine: The ScreenshotEngine instance for capturing
            max_workers: Number of parallel screenshot threads (default: 2)
        """
        self.engine = screenshot_engine
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: List[Future] = []
        self._shutdown = False
    
    def request_screenshot(
        self,
        event: dict,
        monitor_name: Optional[str],
        rel_x: int,
        rel_y: int,
        image_format: str = "png",
        image_quality: int = 90
    ) -> None:
        """
        Queue a screenshot request for async processing.
        
        The event dict will be updated in-place with 'screenshot_bytes' and
        'screenshot_mime' keys when the capture completes.
        
        Args:
            event: The click event dict (mutated in-place)
            monitor_name: Target monitor name
            rel_x: Cursor X position relative to monitor
            rel_y: Cursor Y position relative to monitor
            image_format: Output format ('png', 'jpg', 'webp')
            image_quality: Compression quality for lossy formats (1-100)
        """
        if self._shutdown:
            logger.warning("ScreenshotWorker already shut down, ignoring request")
            return
        
        future = self.executor.submit(
            self._do_screenshot,
            event,
            monitor_name,
            rel_x,
            rel_y,
            image_format,
            image_quality
        )
        self.futures.append(future)
    
    def _do_screenshot(
        self,
        event: dict,
        monitor_name: Optional[str],
        rel_x: int,
        rel_y: int,
        image_format: str,
        image_quality: int
    ) -> None:
        """
        Capture screenshot and update event dict in-place.
        
        This runs in a background thread.
        """
        try:
            img_bytes, mime_type = self.engine.capture_with_cursor_compressed(
                rel_x,
                rel_y,
                monitor_name=monitor_name,
                format=image_format,
                quality=image_quality
            )
            if img_bytes:
                event['screenshot_bytes'] = img_bytes
                event['screenshot_mime'] = mime_type
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
    
    def wait_for_pending(self, timeout: float = 5.0) -> int:
        """
        Wait for all pending screenshot requests to complete.
        
        Args:
            timeout: Maximum seconds to wait per future
            
        Returns:
            Number of completed screenshots
        """
        completed = 0
        for future in self.futures:
            try:
                future.result(timeout=timeout)
                completed += 1
            except Exception as e:
                logger.warning(f"Screenshot future failed: {e}")
        self.futures.clear()
        return completed
    
    def pending_count(self) -> int:
        """Return number of pending screenshot requests."""
        return sum(1 for f in self.futures if not f.done())
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the worker thread pool.
        
        Args:
            wait: If True, wait for pending tasks to complete
        """
        self._shutdown = True
        self.executor.shutdown(wait=wait)
