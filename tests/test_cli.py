import unittest
from wsr.main import parse_arguments

class TestCLI(unittest.TestCase):
    def test_import(self):
        """Simple test to ensure src module can be imported."""
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
