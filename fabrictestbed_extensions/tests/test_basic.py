import os
import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager

class FablibManagerTests(unittest.TestCase):
    """
    Some basic tests for FablibManager.

    Instantiating FablibManager will throw some exceptions if some
    required environment variables are not set.
    """

    def setUp(self):
        os.environ.clear()

    def test_fablib_no_env_vars(self):
        with self.assertRaises(AttributeError):
            FablibManager()
