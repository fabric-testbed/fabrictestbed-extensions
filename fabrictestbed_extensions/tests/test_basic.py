import os
import pathlib
import tempfile
import unittest

from fabrictestbed.util.constants import Constants

from fabrictestbed_extensions.fablib.exceptions import FablibConfigurationError
from fabrictestbed_extensions.fablib.fablib import FablibManager


class FablibManagerTests(unittest.TestCase):
    """
    Some basic tests to exercise FablibManager.

    Instantiating FablibManager will throw some exceptions if some
    required environment variables are not set.
    """

    required_env_vars = [
        Constants.FABRIC_CREDMGR_HOST,
        Constants.FABRIC_ORCHESTRATOR_HOST,
        Constants.FABRIC_PROJECT_ID,
        Constants.FABRIC_TOKEN_LOCATION,
        FablibManager.FABRIC_BASTION_HOST,
        FablibManager.FABRIC_BASTION_USERNAME,
        FablibManager.FABRIC_BASTION_KEY_LOCATION,
    ]

    def setUp(self):
        # Run each test with an empty environment.
        os.environ.clear()

    def test_fablib_manager_no_env_vars(self):
        # Test with no required env vars set.
        with self.assertRaises(FablibConfigurationError) as ctx:
            FablibManager()

            self.assertEqual(ctx.exception.message, "Error initializing FablibManager")

            expected_errors = [
                "orchestrator host is not set",
                "credmanager host is not set",
                "FABRIC token is not set",
                "project ID is not set",
                "bastion username is not set",
                "bastion key file is not set",
                "bastion host address is not set",
                "bastion key filename is set to None",
                "Error reading SSH key: None (error: Key object may not be empty)",
                "Error reading SSH key: None (error: 'NoneType' object has no attribute 'get_text')",
                "Error reading SSH key: None (error: Key object may not be empty)",
                "Error reading SSH key: None (error: 'NoneType' object has no attribute 'get_text')",
            ]

            self.assertEqual(expected_errors, ctx.exception.errors)

    def test_fablib_manager_one_env_var(self):
        # Test with some required env vars set.
        for var in self.required_env_vars:
            with self.assertRaises(FablibConfigurationError):
                os.environ[var] = "dummy"
                FablibManager()

    def test_fablib_manager_all_env_vars(self):
        # Test with all required configuration except
        # FABRIC_TOKEN_LOCATION.
        for var in self.required_env_vars:
            os.environ[var] = "dummy"

        with self.assertRaises(FablibConfigurationError):
            FablibManager()

    def test_fablib_manager_test_only_cm_host(self):
        with self.assertRaises(FablibConfigurationError):
            os.environ[Constants.FABRIC_CREDMGR_HOST] = "dummy"
            FablibManager()

    def test_fablib_manager_test_only_orchestrator_host(self):
        with self.assertRaises(FablibConfigurationError):
            os.environ[Constants.FABRIC_ORCHESTRATOR_HOST] = "dummy"
            FablibManager()

    def test_fablib_manager_test_only_project_id(self):
        with self.assertRaises(FablibConfigurationError):
            os.environ[Constants.FABRIC_PROJECT_ID] = "dummy"
            FablibManager()

    def test_fablib_manager_test_only_token_location(self):
        with self.assertRaises(FablibConfigurationError):
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = "dummy"
            FablibManager()

    def test_fablib_manager_test_with_no_token_file(self):
        # Should fail when token location is not a valid path.

        # set all required env vars.
        for var in self.required_env_vars:
            os.environ[var] = "dummy"

        with self.assertRaises(FablibConfigurationError) as ctx:
            FablibManager()

        self.assertEqual(ctx.exception.message, "Error initializing FablibManager")

        expected_errors = [
            "Error reading SSH key: dummy (error: [Errno 2] No such file or directory: 'dummy')",
            "Error reading SSH key: dummy (error: [Errno 2] No such file or directory: 'dummy')",
            "Error reading SSH key: None (error: Key object may not be empty)",
            "Error reading SSH key: None (error: 'NoneType' object has no attribute 'get_text')",
        ]

        self.assertEqual(ctx.exception.errors, expected_errors)

    def test_fablib_manager_test_with_dummy_token(self):
        # TODO: That FablibManager() calls build_slice_manager()
        # complicates writing a test for it.  It eventually makes a
        # network call to credential manager API, but it is not right
        # for a unit test to do such a thing.  We could probably
        # somehow mock a CM here?

        # set all required env vars.
        for var in self.required_env_vars:
            os.environ[var] = "dummy"

        # '.invalid' is an invalid host per RFC 6761, so this test
        # must fail without ever making a successful network call.
        os.environ[Constants.FABRIC_CREDMGR_HOST] = ".invalid"
        path = os.path.join(os.path.dirname(__file__), "dummy-token.json")
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = path

        with self.assertRaises(FablibConfigurationError):
            FablibManager()

    def test_fablib_manager_with_empty_config(self):
        # Check that an empty configuration file will cause
        # FablibManager to raise an error.
        rcfile = tempfile.NamedTemporaryFile()
        rcfile.flush()

        with self.assertRaises(FablibConfigurationError):
            FablibManager(fabric_rc=rcfile.name)

    def test_fablib_manager_with_some_config(self):
        # Test with some configuration in the rc file.
        rcfile = tempfile.NamedTemporaryFile()

        # Write all configuration except FABRIC_TOKEN_LOCATION.  The
        # token location is a special case because when it is set,
        # Fablib will need network access to reach CredentialManager.
        for var in self.required_env_vars:
            rcfile.write(f"export {var} = dummy\n".encode())

        rcfile.flush()

        with self.assertRaises(FablibConfigurationError) as ctx:
            FablibManager(fabric_rc=rcfile.name)

        # Check that the error is what we expected.
        self.assertIsInstance(ctx.exception, FablibConfigurationError)

        # # TODO - (1) check that the token is a readable file.  Leave
        # # the validation to FABRIC API; (2) use our own exception
        # # class that holds a list of error strings.  The assertEqual
        # # below is unweildy; (3) Improve error messages.  What key are
        # # we talking about?  Public or private key? Bastion or
        # # slice/sliver key?

        self.assertEqual(ctx.exception.message, "Error initializing FablibManager")

        expected_errors = [
            "Error reading SSH key: dummy (error: [Errno 2] No such file or directory: 'dummy')",
            "Error reading SSH key: dummy (error: [Errno 2] No such file or directory: 'dummy')",
            "Error reading SSH key: None (error: Key object may not be empty)",
            "Error reading SSH key: None (error: 'NoneType' object has no attribute 'get_text')",
        ]

        self.assertEqual(ctx.exception.errors, expected_errors)
