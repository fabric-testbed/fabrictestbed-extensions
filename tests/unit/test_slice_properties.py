"""Unit tests for Slice property methods and state checks.

Uses mocked FIM and FablibManager to avoid network access.
"""

import unittest
from unittest.mock import MagicMock, patch


class TestSliceStateChecks(unittest.TestCase):
    """Test Slice.isStable(), is_dead_or_closing(), etc."""

    def _make_slice(self, state):
        """Create a mock Slice-like object for state testing."""
        # Import here to avoid module-level import issues on Python 3.9
        try:
            from fabrictestbed_extensions.fablib.slice import Slice
        except Exception:
            self.skipTest("Cannot import Slice (requires Python 3.10+)")

        mock_sm_slice = MagicMock()
        mock_sm_slice.state = state
        mock_sm_slice.slice_id = "test-slice-id"
        mock_sm_slice.model = ""

        mock_fablib = MagicMock()
        mock_fablib.get_log_level.return_value = 20  # INFO

        s = Slice.__new__(Slice)
        s.sm_slice = mock_sm_slice
        s.fablib_manager = mock_fablib
        s.topology = MagicMock()
        s.nodes = {}
        s.network_services = {}
        s.interfaces = {}
        s.facilities = {}
        s.slivers = []
        s._sliver_map = {}
        s.slice_id = "test-slice-id"
        s.slice_name = "test-slice"
        s.user_only = True
        s.update_topology_count = 0
        s.update_slivers_count = 0
        s.update_slice_count = 0
        return s

    def test_is_stable_returns_true_for_stable_ok(self):
        s = self._make_slice("StableOK")
        self.assertTrue(s.isStable())

    def test_is_stable_returns_true_for_stable_error(self):
        s = self._make_slice("StableError")
        self.assertTrue(s.isStable())

    def test_is_stable_returns_true_for_modify_ok(self):
        s = self._make_slice("ModifyOK")
        self.assertTrue(s.isStable())

    def test_is_stable_returns_false_for_configuring(self):
        s = self._make_slice("Configuring")
        self.assertFalse(s.isStable())

    def test_is_stable_returns_false_for_nascent(self):
        s = self._make_slice("Nascent")
        self.assertFalse(s.isStable())

    def test_is_dead_or_closing_for_dead(self):
        s = self._make_slice("Dead")
        self.assertTrue(s.is_dead_or_closing())

    def test_is_dead_or_closing_for_closing(self):
        s = self._make_slice("Closing")
        self.assertTrue(s.is_dead_or_closing())

    def test_is_dead_or_closing_false_for_stable(self):
        s = self._make_slice("StableOK")
        self.assertFalse(s.is_dead_or_closing())

    def test_get_state_returns_sm_slice_state(self):
        s = self._make_slice("StableOK")
        self.assertEqual(s.get_state(), "StableOK")


class TestSliceSliverMap(unittest.TestCase):
    """Test the sliver dict cache."""

    def test_sliver_map_populated_on_update(self):
        """_sliver_map should be built from slivers list."""
        try:
            from fabrictestbed_extensions.fablib.slice import Slice
        except Exception:
            self.skipTest("Cannot import Slice (requires Python 3.10+)")

        s = Slice.__new__(Slice)
        s.sm_slice = MagicMock()
        s.sm_slice.slice_id = "test-id"
        s.fablib_manager = MagicMock()
        s.user_only = True
        s.update_slivers_count = 0
        s.slivers = []
        s._sliver_map = {}
        s.slice_name = "test-slice"

        # Mock the API call
        mock_sliver1 = MagicMock()
        mock_sliver1.sliver_id = "res-001"
        mock_sliver2 = MagicMock()
        mock_sliver2.sliver_id = "res-002"

        s.fablib_manager.get_manager.return_value.list_slivers.return_value = [
            mock_sliver1,
            mock_sliver2,
        ]

        s.update_slivers()

        self.assertEqual(len(s._sliver_map), 2)
        self.assertEqual(s._sliver_map["res-001"], mock_sliver1)
        self.assertEqual(s._sliver_map["res-002"], mock_sliver2)

    def test_get_sliver_uses_dict_lookup(self):
        """get_sliver() should use O(1) dict lookup."""
        try:
            from fabrictestbed_extensions.fablib.slice import Slice
        except Exception:
            self.skipTest("Cannot import Slice (requires Python 3.10+)")

        s = Slice.__new__(Slice)
        s.slivers = []
        mock_sliver = MagicMock()
        mock_sliver.sliver_id = "res-123"
        s._sliver_map = {"res-123": mock_sliver}

        result = s.get_sliver("res-123")
        self.assertEqual(result, mock_sliver)

    def test_get_sliver_returns_none_for_missing(self):
        """get_sliver() should return None for unknown reservation_id."""
        try:
            from fabrictestbed_extensions.fablib.slice import Slice
        except Exception:
            self.skipTest("Cannot import Slice (requires Python 3.10+)")

        s = Slice.__new__(Slice)
        s.slivers = []
        s._sliver_map = {"res-123": MagicMock()}

        result = s.get_sliver("res-nonexistent")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
