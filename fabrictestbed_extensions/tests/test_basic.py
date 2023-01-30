import os
import pathlib
import unittest

from fabrictestbed.util.constants import Constants

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
        # Constants.FABRIC_TOKEN_LOCATION,
        FablibManager.FABRIC_BASTION_HOST,
        FablibManager.FABRIC_BASTION_USERNAME,
        FablibManager.FABRIC_BASTION_KEY_LOCATION,
    ]

    def setUp(self):
        os.environ.clear()

    def test_fablib_manager_no_env_vars(self):
        # Test with no required env vars set.
        with self.assertRaises(AttributeError):
            FablibManager()

    def test_fablib_manager_one_env_var(self):
        # Test with some required env vars set.
        for var in self.required_env_vars:
            with self.assertRaises(AttributeError):
                os.environ[var] = "dummy"
                FablibManager()

    def test_fablib_manager_all_env_vars(self):
        # Test with all required_env_vars except token location set.
        for var in self.required_env_vars:
            os.environ[var] = "dummy"

        with self.assertRaises(AttributeError):            
            FablibManager()

    def test_fablib_manager_test_only_cm_host(self):
        with self.assertRaises(AttributeError):
            os.environ[Constants.FABRIC_CREDMGR_HOST] = "dummy"
            FablibManager()

    def test_fablib_manager_test_only_orchestrator_host(self):
        with self.assertRaises(AttributeError):
            os.environ[Constants.FABRIC_ORCHESTRATOR_HOST] = "dummy"
            FablibManager()

    def test_fablib_manager_test_only_project_id(self):
        with self.assertRaises(AttributeError):
            os.environ[Constants.FABRIC_PROJECT_ID] = "dummy"
            FablibManager()

    def test_fablib_manager_test_only_token_location(self):
        with self.assertRaises(AttributeError):
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = "dummy"
            FablibManager()

    def test_fablib_manager_test_with_no_token_file(self):
        # Should fail when token location is not a valid path.
        with self.assertRaises(ValueError):
            # FablibManager() without a valid token or token location
            # should raise a "ValueError: Invalid value for
            # `refresh_token`, must not be `None`"
            os.environ[Constants.FABRIC_CREDMGR_HOST] = "dummy"
            os.environ[Constants.FABRIC_ORCHESTRATOR_HOST] = "dummy"
            os.environ[Constants.FABRIC_PROJECT_ID] = "dummy"
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = "dummy"
            os.environ[FablibManager.FABRIC_BASTION_HOST] = "dummy"
            os.environ[FablibManager.FABRIC_BASTION_USERNAME] = "dummy"
            os.environ[FablibManager.FABRIC_BASTION_KEY_LOCATION] = "dummy"            
            FablibManager()

    def test_fablib_manager_test_with_dummy_token(self):
        # TODO: That FablibManager() calls build_slice_manager()
        # complicates writing a test for it.  It eventually makes a
        # network call to credential manager API, but it is not right
        # for a unit test to do such a thing.  We could probably
        # somehow mock a CM here?
        with self.assertRaises(Exception):
            # '.invalid' is an invalid host per RFC 6761, so this test
            # must fail without ever making a successful network call.
            os.environ[Constants.FABRIC_CREDMGR_HOST] = ".test"
            os.environ[Constants.FABRIC_ORCHESTRATOR_HOST] = "dummy"
            os.environ[Constants.FABRIC_PROJECT_ID] = "dummy"

            path = os.path.join(os.path.dirname(__file__), "dummy-token.json")
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = path

            os.environ[FablibManager.FABRIC_BASTION_HOST] = "dummy"
            os.environ[FablibManager.FABRIC_BASTION_USERNAME] = "dummy"
            os.environ[FablibManager.FABRIC_BASTION_KEY_LOCATION] = "dummy"            

            FablibManager()
