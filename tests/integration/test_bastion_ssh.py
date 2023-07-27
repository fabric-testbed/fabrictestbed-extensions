import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager

class BastionHostTests(unittest.TestCase):
    """
    Test that bastion setup works.

    Fablib needs bastion host name, username, ssh key, and the
    (optional) key passphrase to function correctly.
    """

    def test_probe_bastion_host(self):
        """
        This should pass when fablib set up is correct.
        """
        fm = FablibManager(offline=True)
        result = fm.probe_bastion_host()
        self.assertTrue(result)
