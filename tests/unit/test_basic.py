import os
import pathlib
import tempfile
import unittest

from fabrictestbed.fabric_manager import FabricManagerException
from fabrictestbed.token_manager.token_manager import TokenManagerException
from fabrictestbed.util.constants import Constants

from fabrictestbed_extensions.fablib.config.config import Config, ConfigException
from fabrictestbed_extensions.fablib.constants import Constants as FablibConstants
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
        FablibConstants.FABRIC_BASTION_HOST,
        FablibConstants.FABRIC_BASTION_USERNAME,
        FablibConstants.FABRIC_BASTION_KEY_LOCATION,
    ]

    DUMMY_TOKEN_LOCATION = str(
        pathlib.Path(__file__).parent / "data" / "dummy-token.json"
    )
    FABRIC_RC_LOCATION = str(pathlib.Path(__file__).parent / "data" / "dummy_fabric_rc")

    def setUp(self):
        # Run each test with an empty environment.
        os.environ.clear()

        # Create an empty configuration file, so that we will be
        # really testing with a clean slate.  Creating the
        # configuration file in read-only mode should ensure that it
        # will remain empty.
        self.rcfile = tempfile.NamedTemporaryFile(mode="r")
        self.rcfile.flush()

    def tearDown(self):
        self.rcfile.close()

    def test_fablib_manager_test_only_cm_host(self):
        os.environ[Constants.FABRIC_CREDMGR_HOST] = "dummy"
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.DUMMY_TOKEN_LOCATION
        # required_check fails because project_id and bastion_username have no defaults
        self.assertRaises(ConfigException, FablibManager, fabric_rc=self.rcfile.name)

    def test_fablib_manager_test_only_orchestrator_host(self):
        os.environ[Constants.FABRIC_ORCHESTRATOR_HOST] = "dummy"
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.DUMMY_TOKEN_LOCATION
        # required_check fails because project_id and bastion_username have no defaults
        self.assertRaises(ConfigException, FablibManager, fabric_rc=self.rcfile.name)

    def test_fablib_manager_test_only_project_id(self):
        os.environ[Constants.FABRIC_PROJECT_ID] = "dummy"
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.DUMMY_TOKEN_LOCATION
        self.assertRaises(Exception, FablibManager, fabric_rc=self.rcfile.name)

    def test_fablib_manager_test_only_token_location(self):
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = "dummy"
        self.assertRaises(ConfigException, FablibManager, fabric_rc=self.rcfile.name)

    def test_fablib_manager_test_with_no_token_file(self):
        # Should fail when token location is not a valid path.

        # set all required env vars.
        os.environ[Constants.FABRIC_PROJECT_ID] = "dummy_project_id"
        os.environ[FablibConstants.FABRIC_BASTION_HOST] = "dummy_bastion_host"
        os.environ[FablibConstants.FABRIC_BASTION_USERNAME] = "dummy_bastion_user_name"
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = "dummy"

        # FablibManager() without a valid token or token location
        # should raise a "SliceManagerException: Unable to refresh tokens: no refresh token found!
        self.assertRaises(ConfigException, FablibManager, fabric_rc=self.rcfile.name)

    def test_fablib_manager_test_with_dummy_token(self):
        # With all required env vars set and a valid token file,
        # FablibManager should construct successfully (manager is lazy).
        # The actual network call happens on first get_manager() access.
        for var in self.required_env_vars:
            os.environ[var] = "dummy"

        os.environ[Constants.FABRIC_CREDMGR_HOST] = ".invalid"
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.DUMMY_TOKEN_LOCATION

        # Should not raise — manager construction is now lazy
        fablib = FablibManager(fabric_rc=self.rcfile.name)
        self.assertIsNotNone(fablib)

    def test_fablib_manager_with_empty_config(self):
        # Check that an empty configuration file will cause
        # FablibManager to raise an error.
        rcfile = tempfile.NamedTemporaryFile()
        rcfile.flush()
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.DUMMY_TOKEN_LOCATION

        with self.assertRaises(Exception):
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

        with self.assertRaises(ConfigException) as ctx:
            FablibManager(fabric_rc=rcfile.name)

        # Check that the error is what we expected.
        self.assertIsInstance(ctx.exception, ConfigException)

        # Check that the error message indicates token file not found.
        # The default token location won't exist in the test environment.
        self.assertTrue(
            "Token file not found at" in str(ctx.exception),
            f"Unexpected error message: {ctx.exception}",
        )

    def test_FablibManager_no_config_no_env_var(self):
        # Instantiate Fablib manager without any config or environment variables
        # Results in using the defaults and initialization fails when token file is not found!
        # Pass the empty rcfile so no real config file on disk is read.
        self.assertRaises(
            ConfigException,
            FablibManager,
            fabric_rc=self.rcfile.name,
        )

    def test_FablibManager_no_config_no_env_var_token_location(self):
        # Instantiate Fablib manager without any config or environment variables
        # but with a token_location. required_check() fails because
        # project_id and bastion_username have no defaults and aren't set.

        with self.assertRaises(ConfigException) as ctx:
            FablibManager(
                token_location=self.DUMMY_TOKEN_LOCATION,
                fabric_rc=self.FABRIC_RC_LOCATION,
            )

        # Check that the error message indicates missing config.
        error_msg = str(ctx.exception)
        self.assertTrue(
            "project_id" in error_msg or "bastion_username" in error_msg,
            f"Unexpected error message: {error_msg}",
        )

    def test_FablibManager_no_config_no_env_var_token_location_offline(self):
        # Instantiate Fablib manager without any config or environment variables
        # Even in offline mode, required_check() validates that project_id
        # and bastion_username are present.

        with self.assertRaises(ConfigException) as ctx:
            FablibManager(
                token_location=self.DUMMY_TOKEN_LOCATION,
                offline=True,
                fabric_rc=self.FABRIC_RC_LOCATION,
            )

        # Check that the error message indicates missing config.
        error_msg = str(ctx.exception)
        self.assertTrue(
            "project_id" in error_msg or "bastion_username" in error_msg,
            f"Unexpected error message: {error_msg}",
        )

    def test_FablibManager_no_config_no_env_var_token_location_offline_project_id_bastion_user_name(
        self,
    ):
        # Instantiate Fablib manager without any config or environment variables
        project_id = "DUMMY_PROJECT_ID"
        bastion_username = "DUMMY_BASTION_USERNAME"

        fablib = FablibManager(
            token_location=self.DUMMY_TOKEN_LOCATION,
            offline=True,
            project_id=project_id,
            bastion_username=bastion_username,
            fabric_rc=self.FABRIC_RC_LOCATION,
        )
        self.assertEqual(project_id, fablib.get_project_id())
        self.assertEqual(bastion_username, fablib.get_bastion_username())
        self.assertEqual(self.DUMMY_TOKEN_LOCATION, fablib.get_token_location())

        for attrs, attr_props in Config.REQUIRED_ATTRS.items():
            if attrs not in [
                FablibConstants.PROJECT_ID,
                FablibConstants.BASTION_USERNAME,
                FablibConstants.TOKEN_LOCATION,
            ]:
                default_value = attr_props.get(FablibConstants.DEFAULT)
                if default_value:
                    self.assertEqual(default_value, fablib.runtime_config.get(attrs))

    def test_FablibManager_no_config_no_env_var_token_location_offline_project_id_bastion_user_name_env(
        self,
    ):
        # Instantiate Fablib manager without any config or environment variables
        project_id = "DUMMY_PROJECT_ID"
        bastion_username = "DUMMY_BASTION_USERNAME"
        os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.DUMMY_TOKEN_LOCATION
        os.environ[Constants.FABRIC_PROJECT_ID] = project_id
        os.environ[FablibConstants.FABRIC_BASTION_USERNAME] = bastion_username

        fablib = FablibManager(fabric_rc=self.FABRIC_RC_LOCATION, offline=True)
        self.assertEqual(project_id, fablib.get_project_id())
        self.assertEqual(bastion_username, fablib.get_bastion_username())
        self.assertEqual(self.DUMMY_TOKEN_LOCATION, fablib.get_token_location())

        for attrs, attr_props in Config.REQUIRED_ATTRS.items():
            if attrs not in [
                FablibConstants.PROJECT_ID,
                FablibConstants.BASTION_USERNAME,
                FablibConstants.TOKEN_LOCATION,
            ]:
                default_value = attr_props.get(FablibConstants.DEFAULT)
                if default_value:
                    self.assertEqual(default_value, fablib.runtime_config.get(attrs))
