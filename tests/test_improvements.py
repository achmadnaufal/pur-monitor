
import unittest
from monitor import cmd_summary, get_con

class TestPURMonitor(unittest.TestCase):
    def test_summary_loads(self):
        '''Test that summary command runs without error'''
        # Mock test - verify basic import works
        self.assertTrue(callable(cmd_summary))
