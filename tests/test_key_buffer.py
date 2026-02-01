import unittest
import time
from wsr.key_buffer import KeyBuffer

class TestKeyBuffer(unittest.TestCase):
    def test_grouping(self):
        buf = KeyBuffer(100) # 100ms
        self.assertTrue(buf.add("KEY_H"))
        self.assertTrue(buf.add("KEY_A"))
        self.assertTrue(buf.add("KEY_L"))
        self.assertEqual(len(buf.buffer), 3)
        
    def test_timeout(self):
        buf = KeyBuffer(10) # 10ms
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

if __name__ == '__main__':
    unittest.main()

