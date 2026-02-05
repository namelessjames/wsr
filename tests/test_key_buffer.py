import unittest
import time
import threading
from wsr.key_buffer import KeyBuffer


class TestKeyBuffer(unittest.TestCase):
    """Original tests - Happy Path."""

    def test_grouping(self):
        buf = KeyBuffer(100)  # 100ms
        self.assertTrue(buf.add("KEY_H"))
        self.assertTrue(buf.add("KEY_A"))
        self.assertTrue(buf.add("KEY_L"))
        self.assertEqual(len(buf.buffer), 3)

    def test_timeout(self):
        buf = KeyBuffer(10)  # 10ms
        buf.add("KEY_A")
        time.sleep(0.02)
        self.assertTrue(buf.is_timed_out())
        self.assertEqual(buf.flush(), "A")

    def test_mapping(self):
        buf = KeyBuffer(100)
        buf.add("KEY_SPACE")
        buf.add("KEY_ENTER")
        buf.add("KEY_B")
        self.assertEqual(buf.flush(), " \nB")


class TestKeyBufferIntervalEdgeCases(unittest.TestCase):
    """Tests for interval_ms edge cases."""

    def test_interval_zero(self):
        """interval_ms=0 should treat every key as timeout."""
        buf = KeyBuffer(0)
        buf.add("KEY_A")
        # Second key should return False (needs flush)
        # because (now - last_time) > 0.0 (almost always)
        time.sleep(0.001)
        self.assertFalse(buf.add("KEY_B"))

    def test_interval_negative(self):
        """Negative interval should raise ValueError."""
        with self.assertRaises(ValueError):
            KeyBuffer(-100)

    def test_interval_very_large(self):
        """Very large interval should work without overflow."""
        buf = KeyBuffer(999999999)  # ~11.5 days
        buf.add("KEY_A")
        buf.add("KEY_B")
        self.assertEqual(buf.flush(), "AB")


class TestKeyBufferTimingEdgeCases(unittest.TestCase):
    """Tests for timing boundary conditions."""

    def test_exact_interval_boundary(self):
        """Keys at exactly the interval boundary (<=)."""
        buf = KeyBuffer(100)  # 100ms
        buf.add("KEY_A")
        time.sleep(0.095)  # Just under 100ms
        self.assertTrue(buf.add("KEY_B"))
        self.assertEqual(buf.flush(), "AB")

    def test_just_over_interval(self):
        """Keys just over the interval should trigger flush need."""
        buf = KeyBuffer(50)  # 50ms
        buf.add("KEY_A")
        time.sleep(0.06)  # 60ms - over 50ms
        self.assertFalse(buf.add("KEY_B"))

    def test_rapid_keys_same_timestamp(self):
        """Multiple keys added in rapid succession."""
        buf = KeyBuffer(100)
        # 100 keys as fast as possible
        for i in range(100):
            buf.add(f"KEY_{chr(65 + (i % 26))}")
        self.assertEqual(len(buf.buffer), 100)


class TestKeyBufferMappingEdgeCases(unittest.TestCase):
    """Tests for _map_key edge cases."""

    def test_map_key_empty_string(self):
        """Empty key name should not crash."""
        buf = KeyBuffer(100)
        buf.add("")
        self.assertEqual(buf.flush(), "")

    def test_map_key_no_key_prefix(self):
        """Key without KEY_ prefix should pass through."""
        buf = KeyBuffer(100)
        buf.add("BTN_LEFT")
        self.assertEqual(buf.flush(), "BTN_LEFT")

    def test_map_key_special_characters(self):
        """Special keys should be bracketed."""
        buf = KeyBuffer(100)
        buf.add("KEY_LEFTSHIFT")
        buf.add("KEY_CAPSLOCK")
        buf.add("KEY_F12")
        result = buf.flush()
        self.assertIn("[LEFTSHIFT]", result)
        self.assertIn("[CAPSLOCK]", result)
        self.assertIn("[F12]", result)

    def test_map_key_backspace(self):
        """Backspace should map to unicode symbol."""
        buf = KeyBuffer(100)
        buf.add("KEY_BACKSPACE")
        self.assertEqual(buf.flush(), "⌫")

    def test_map_key_unicode_handling(self):
        """Ensure unicode characters don't break flush."""
        buf = KeyBuffer(100)
        buf.add("KEY_A")
        buf.add("KEY_BACKSPACE")
        buf.add("KEY_ENTER")
        result = buf.flush()
        self.assertEqual(result, "A⌫\n")


class TestKeyBufferStateEdgeCases(unittest.TestCase):
    """Tests for buffer state edge cases."""

    def test_flush_empty_buffer(self):
        """Flushing empty buffer should return None."""
        buf = KeyBuffer(100)
        self.assertIsNone(buf.flush())

    def test_double_flush(self):
        """Double flush should return None on second call."""
        buf = KeyBuffer(100)
        buf.add("KEY_A")
        self.assertEqual(buf.flush(), "A")
        self.assertIsNone(buf.flush())

    def test_is_timed_out_empty_buffer(self):
        """Empty buffer should never be timed out."""
        buf = KeyBuffer(1)  # 1ms
        self.assertFalse(buf.is_timed_out())
        time.sleep(0.01)
        self.assertFalse(buf.is_timed_out())

    def test_flush_resets_state(self):
        """After flush, buffer should be empty and ready for new keys."""
        buf = KeyBuffer(100)
        buf.add("KEY_A")
        buf.flush()
        self.assertEqual(len(buf.buffer), 0)
        buf.add("KEY_B")
        self.assertEqual(buf.flush(), "B")

    def test_large_buffer(self):
        """Buffer should handle many keys without issues."""
        buf = KeyBuffer(999999)  # Never timeout
        for _ in range(10000):
            buf.add("KEY_X")
        result = buf.flush()
        self.assertEqual(len(result), 10000)
        self.assertEqual(result, "X" * 10000)


class TestKeyBufferThreadSafety(unittest.TestCase):
    """Thread-safety tests."""

    def test_concurrent_add_and_flush(self):
        """Concurrent add and flush should not crash."""
        buf = KeyBuffer(100)
        errors = []

        def adder():
            try:
                for _ in range(1000):
                    buf.add("KEY_A")
            except Exception as e:
                errors.append(e)

        def flusher():
            try:
                for _ in range(100):
                    buf.flush()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=adder)
        t2 = threading.Thread(target=flusher)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")


if __name__ == "__main__":
    unittest.main()

