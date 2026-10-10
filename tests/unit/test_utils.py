"""Unit tests for utility modules."""

import unittest


class TestConstantsImageNames(unittest.TestCase):
    """Tests for Constants.IMAGE_NAMES dictionary structure."""

    def test_image_names_dict_exists(self):
        from fabrictestbed_extensions.fablib.constants import Constants

        self.assertIsInstance(Constants.IMAGE_NAMES, dict)
        self.assertGreater(len(Constants.IMAGE_NAMES), 0)

    def test_image_entries_have_required_keys(self):
        from fabrictestbed_extensions.fablib.constants import Constants

        for image_name, info in Constants.IMAGE_NAMES.items():
            self.assertIsInstance(image_name, str, f"Key {image_name} should be str")
            self.assertIsInstance(info, dict, f"Value for {image_name} should be dict")
            # Each image should have at least a description or username
            # The structure varies but should be a dict
            self.assertGreater(len(info), 0, f"Image {image_name} should have metadata")

    def test_default_rocky_9_exists(self):
        from fabrictestbed_extensions.fablib.constants import Constants

        self.assertIn("default_rocky_9", Constants.IMAGE_NAMES)

    def test_default_ubuntu_22_exists(self):
        from fabrictestbed_extensions.fablib.constants import Constants

        self.assertIn("default_ubuntu_22", Constants.IMAGE_NAMES)


class TestConstantsDefaults(unittest.TestCase):
    """Tests for Constants default values."""

    def test_default_hosts_are_strings(self):
        from fabrictestbed_extensions.fablib.constants import Constants

        self.assertIsInstance(Constants.DEFAULT_FABRIC_CREDMGR_HOST, str)
        self.assertIsInstance(Constants.DEFAULT_FABRIC_ORCHESTRATOR_HOST, str)
        self.assertIsInstance(Constants.DEFAULT_FABRIC_CORE_API_HOST, str)
        self.assertIsInstance(Constants.DEFAULT_FABRIC_BASTION_HOST, str)

    def test_default_hosts_not_empty(self):
        from fabrictestbed_extensions.fablib.constants import Constants

        self.assertGreater(len(Constants.DEFAULT_FABRIC_CREDMGR_HOST), 0)
        self.assertGreater(len(Constants.DEFAULT_FABRIC_ORCHESTRATOR_HOST), 0)

    def test_log_levels_defined(self):
        from fabrictestbed_extensions.fablib.config.config import Config

        self.assertIn("DEBUG", Config.LOG_LEVELS)
        self.assertIn("INFO", Config.LOG_LEVELS)
        self.assertIn("WARNING", Config.LOG_LEVELS)
        self.assertIn("ERROR", Config.LOG_LEVELS)
        self.assertIn("CRITICAL", Config.LOG_LEVELS)


class TestConfigRequiredAttrs(unittest.TestCase):
    """Tests for Config.REQUIRED_ATTRS structure."""

    def test_required_attrs_is_dict(self):
        from fabrictestbed_extensions.fablib.config.config import Config

        self.assertIsInstance(Config.REQUIRED_ATTRS, dict)
        self.assertGreater(len(Config.REQUIRED_ATTRS), 0)

    def test_required_attrs_have_valid_structure(self):
        from fabrictestbed_extensions.fablib.config.config import Config
        from fabrictestbed_extensions.fablib.constants import Constants

        for key, props in Config.REQUIRED_ATTRS.items():
            self.assertIsInstance(key, str, f"Key {key} should be str")
            self.assertIsInstance(props, dict, f"Props for {key} should be dict")
            # Each should have either an env_var or a default
            has_env = Constants.ENV_VAR in props
            has_default = Constants.DEFAULT in props
            self.assertTrue(
                has_env or has_default,
                f"Attr {key} should have env_var or default",
            )

    def test_token_location_has_default(self):
        from fabrictestbed_extensions.fablib.config.config import Config
        from fabrictestbed_extensions.fablib.constants import Constants

        token_props = Config.REQUIRED_ATTRS[Constants.TOKEN_LOCATION]
        self.assertIn(Constants.DEFAULT, token_props)
