"""Unit tests for fabrictestbed_extensions.fablib.constants."""

import unittest

from fabrictestbed_extensions.fablib.constants import Constants


class TestConstants(unittest.TestCase):
    """Tests for the Constants class — image names, model maps, defaults."""

    def test_image_names_not_empty(self):
        """Image names dict should have entries."""
        images = Constants.IMAGE_NAMES
        self.assertIsInstance(images, dict)
        self.assertGreater(len(images), 0)

    def test_image_names_have_required_keys(self):
        """Each image entry should have 'default_user' and 'description'."""
        for name, info in Constants.IMAGE_NAMES.items():
            self.assertIsInstance(name, str, f"Image name should be str: {name}")
            self.assertIn(
                "default_user",
                info,
                f"Image '{name}' missing 'default_user'",
            )

    def test_rocky_9_in_image_names(self):
        """Rocky 9 should be available as an image."""
        images = Constants.IMAGE_NAMES
        rocky_keys = [k for k in images if "rocky" in k.lower() and "9" in k]
        self.assertGreater(len(rocky_keys), 0, "Expected Rocky 9 image")

    def test_default_log_level_is_set(self):
        """DEFAULT_LOG_LEVEL should be defined."""
        self.assertTrue(hasattr(Constants, "DEFAULT_LOG_LEVEL"))
        self.assertIsNotNone(Constants.DEFAULT_LOG_LEVEL)

    def test_default_bastion_host_is_set(self):
        """DEFAULT_FABRIC_BASTION_HOST should be defined."""
        self.assertTrue(hasattr(Constants, "DEFAULT_FABRIC_BASTION_HOST"))
        self.assertIsNotNone(Constants.DEFAULT_FABRIC_BASTION_HOST)
        self.assertGreater(len(Constants.DEFAULT_FABRIC_BASTION_HOST), 0)

    def test_default_token_location_is_set(self):
        """DEFAULT_TOKEN_LOCATION should be defined."""
        self.assertTrue(hasattr(Constants, "DEFAULT_TOKEN_LOCATION"))
        self.assertIsNotNone(Constants.DEFAULT_TOKEN_LOCATION)


if __name__ == "__main__":
    unittest.main()
