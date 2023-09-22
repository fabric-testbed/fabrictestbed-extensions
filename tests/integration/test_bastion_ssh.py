import tempfile
import unittest

import paramiko

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
        self.assertTrue(fm.probe_bastion_host())

    def test_probe_bastion_host_no_username(self):
        """
        Test bastion with an empty username.
        """
        fm = FablibManager(offline=True, bastion_username="")
        self.assertRaises(paramiko.ssh_exception.SSHException, fm.probe_bastion_host)

    def test_probe_bastion_host_empty_key(self):
        """
        Test bastion with an empty key.
        """
        keyfile = tempfile.NamedTemporaryFile()

        fm = FablibManager(offline=True, bastion_key_filename=keyfile.name)
        self.assertRaises(paramiko.ssh_exception.SSHException, fm.probe_bastion_host)

    def test_probe_bastion_host_bad_key(self):
        """
        Test bastion with a key we just generated.
        """
        keyfile = tempfile.NamedTemporaryFile()

        rsa_key = paramiko.RSAKey.generate(bits=2048)
        rsa_key.write_private_key_file(keyfile.name)

        fm = FablibManager(offline=True, bastion_key_filename=keyfile.name)
        self.assertRaises(paramiko.ssh_exception.SSHException, fm.probe_bastion_host)
