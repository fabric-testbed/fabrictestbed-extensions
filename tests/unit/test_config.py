"""Unit tests for fabrictestbed_extensions.fablib.config.config.

Tests configuration precedence, validation, and path resolution
without requiring FABRIC credentials or network access.
"""

import os
import pathlib
import tempfile
import unittest

from fabrictestbed_extensions.fablib.config.config import Config, ConfigException
from fabrictestbed_extensions.fablib.constants import Constants


class TestConfigPrecedence(unittest.TestCase):
    """Test that configuration sources have correct precedence:
    CLI args > env vars > fabric_rc > defaults.
    """

    FABRIC_RC = str(pathlib.Path(__file__).parent / "data" / "dummy_fabric_rc")

    def setUp(self):
        os.environ.clear()

    def tearDown(self):
        os.environ.clear()

    def test_env_var_overrides_fabric_rc(self):
        """Environment variables should override fabric_rc values."""
        os.environ["FABRIC_PROJECT_ID"] = "env-project-id"
        config = Config(fabric_rc=self.FABRIC_RC)
        self.assertEqual(config.get_project_id(), "env-project-id")

    def test_constructor_arg_overrides_env(self):
        """Constructor kwargs should override environment variables."""
        os.environ["FABRIC_PROJECT_ID"] = "env-project-id"
        config = Config(fabric_rc=self.FABRIC_RC, project_id="arg-project-id")
        self.assertEqual(config.get_project_id(), "arg-project-id")

    def test_fabric_rc_values_loaded(self):
        """Values from fabric_rc should be loaded when no env/args set."""
        config = Config(fabric_rc=self.FABRIC_RC)
        # dummy_fabric_rc should have a bastion host
        bastion = config.get_bastion_host()
        self.assertIsNotNone(bastion)
        self.assertGreater(len(bastion), 0)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation."""

    def setUp(self):
        os.environ.clear()

    def tearDown(self):
        os.environ.clear()

    def test_missing_fabric_rc_uses_defaults(self):
        """Config with nonexistent fabric_rc should still work with env vars."""
        os.environ["FABRIC_CREDMGR_HOST"] = "https://credmgr.example.com"
        os.environ["FABRIC_ORCHESTRATOR_HOST"] = "https://orch.example.com"
        os.environ["FABRIC_PROJECT_ID"] = "test-project"
        os.environ["FABRIC_BASTION_HOST"] = "bastion.example.com"
        os.environ["FABRIC_BASTION_USERNAME"] = "testuser"
        os.environ["FABRIC_BASTION_KEY_LOCATION"] = "/tmp/nonexistent_key"

        config = Config(fabric_rc="/nonexistent/path/fabric_rc")
        self.assertEqual(config.get_project_id(), "test-project")

    def test_get_log_level_default(self):
        """Default log level should be INFO."""
        os.environ["FABRIC_CREDMGR_HOST"] = "https://credmgr.example.com"
        os.environ["FABRIC_ORCHESTRATOR_HOST"] = "https://orch.example.com"
        os.environ["FABRIC_PROJECT_ID"] = "test"
        os.environ["FABRIC_BASTION_HOST"] = "bastion"
        os.environ["FABRIC_BASTION_USERNAME"] = "user"
        os.environ["FABRIC_BASTION_KEY_LOCATION"] = "/tmp/key"

        config = Config(fabric_rc="/nonexistent")
        # get_log_level() returns a string or int depending on context
        log_level = config.get_log_level()
        self.assertIn(str(log_level), ["INFO", "20"])


class TestConfigPaths(unittest.TestCase):
    """Test path resolution in Config."""

    def setUp(self):
        os.environ.clear()

    def tearDown(self):
        os.environ.clear()

    def test_bastion_key_location_stored(self):
        """Bastion key location should be stored from env var."""
        os.environ["FABRIC_CREDMGR_HOST"] = "https://credmgr.example.com"
        os.environ["FABRIC_ORCHESTRATOR_HOST"] = "https://orch.example.com"
        os.environ["FABRIC_PROJECT_ID"] = "test"
        os.environ["FABRIC_BASTION_HOST"] = "bastion"
        os.environ["FABRIC_BASTION_USERNAME"] = "user"
        os.environ["FABRIC_BASTION_KEY_LOCATION"] = "/tmp/my_key"

        config = Config(fabric_rc="/nonexistent")
        key_loc = config.get_bastion_key_location()
        self.assertEqual(key_loc, "/tmp/my_key")


if __name__ == "__main__":
    unittest.main()
