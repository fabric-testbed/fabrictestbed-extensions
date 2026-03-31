"""
Unit tests for FablibManager.find_resource_slot(),
_slice_to_resources(), and _normalize_component_keys().
"""

import datetime
import os
import pathlib
import unittest
from unittest.mock import MagicMock, patch

from fabrictestbed_extensions.fablib.fablib import FablibManager


class FindResourceSlotTestBase(unittest.TestCase):
    """Common setup: create an offline FablibManager instance."""

    DUMMY_TOKEN_LOCATION = str(
        pathlib.Path(__file__).parent / "data" / "dummy-token.json"
    )
    FABRIC_RC_LOCATION = str(pathlib.Path(__file__).parent / "data" / "dummy_fabric_rc")

    def setUp(self):
        os.environ.clear()
        self.fablib = FablibManager(
            token_location=self.DUMMY_TOKEN_LOCATION,
            offline=True,
            project_id="DUMMY_PROJECT_ID",
            bastion_username="DUMMY_BASTION_USER",
            fabric_rc=self.FABRIC_RC_LOCATION,
        )


class TestFindResourceSlotValidation(FindResourceSlotTestBase):
    """Test input validation in find_resource_slot()."""

    def _times(self, hours=2):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=hours)
        return start, end

    def test_raises_when_both_slice_and_resources_provided(self):
        start, end = self._times()
        mock_slice = MagicMock()
        with self.assertRaises(ValueError) as ctx:
            self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                slice=mock_slice,
                resources=[{"type": "compute", "site": "TACC", "cores": 2}],
            )
        self.assertIn("Exactly one", str(ctx.exception))

    def test_raises_when_neither_slice_nor_resources_provided(self):
        start, end = self._times()
        with self.assertRaises(ValueError) as ctx:
            self.fablib.find_resource_slot(start=start, end=end, duration=1)
        self.assertIn("Exactly one", str(ctx.exception))

    def test_raises_when_time_range_too_short(self):
        start, end = self._times(hours=0)
        end = start + datetime.timedelta(minutes=30)
        with self.assertRaises(Exception) as ctx:
            self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                resources=[{"type": "compute", "site": "TACC", "cores": 2}],
            )
        self.assertIn("at least 60 minutes", str(ctx.exception))

    def test_exactly_60_minutes_does_not_raise(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(minutes=60)
        mock_manager = MagicMock()
        mock_manager.find_resource_slot.return_value = {"slots": []}

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                resources=[{"type": "compute", "site": "TACC", "cores": 2}],
            )
        self.assertEqual(result, {"slots": []})


class TestSliceToResources(FindResourceSlotTestBase):
    """Test _slice_to_resources() static method."""

    @staticmethod
    def _make_node(site, cores=2, ram=8, disk=10, components=None):
        node = MagicMock()
        node.get_site.return_value = site
        node.get_requested_cores.return_value = cores
        node.get_requested_ram.return_value = ram
        node.get_requested_disk.return_value = disk
        node.get_components.return_value = components or []
        return node

    @staticmethod
    def _make_component(comp_type, fim_model):
        comp = MagicMock()
        comp.get_type.return_value = comp_type
        comp.get_fim_model.return_value = fim_model
        return comp

    @staticmethod
    def _make_l2network(net_type, site_pairs, bandwidth=10):
        net = MagicMock()
        net.get_type.return_value = net_type
        net.get_bandwidth.return_value = bandwidth
        ifaces = []
        for site in site_pairs:
            iface = MagicMock()
            iface.get_site.return_value = site
            ifaces.append(iface)
        net.get_interfaces.return_value = ifaces
        return net

    @staticmethod
    def _make_facility_port(name, site, num_vlans=1):
        fp = MagicMock()
        fp.get_name.return_value = name
        fp.get_site.return_value = site
        fp.get_interfaces.return_value = [MagicMock() for _ in range(num_vlans)]
        return fp

    def _make_slice(self, nodes=None, networks=None, facilities=None):
        mock_slice = MagicMock()
        mock_slice.get_nodes.return_value = nodes or []
        mock_slice.get_l2networks.return_value = networks or []
        mock_slice.get_facilities.return_value = facilities or []
        return mock_slice

    def test_single_node_no_components(self):
        s = self._make_slice(nodes=[self._make_node("TACC", cores=4, ram=16, disk=50)])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "compute")
        self.assertEqual(result[0]["site"], "TACC")
        self.assertEqual(result[0]["cores"], 4)
        self.assertEqual(result[0]["ram"], 16)
        self.assertEqual(result[0]["disk"], 50)
        self.assertNotIn("components", result[0])

    def test_multiple_nodes_same_site_aggregated(self):
        nodes = [
            self._make_node("TACC", cores=2, ram=8, disk=10),
            self._make_node("TACC", cores=4, ram=16, disk=20),
        ]
        s = self._make_slice(nodes=nodes)
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["cores"], 6)
        self.assertEqual(result[0]["ram"], 24)
        self.assertEqual(result[0]["disk"], 30)

    def test_nodes_different_sites_separate_entries(self):
        nodes = [
            self._make_node("TACC", cores=2),
            self._make_node("STAR", cores=4),
        ]
        s = self._make_slice(nodes=nodes)
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 2)
        sites = {r["site"] for r in result}
        self.assertEqual(sites, {"TACC", "STAR"})

    def test_node_with_components(self):
        gpu = self._make_component("GPU", "Tesla T4")
        nic = self._make_component("SmartNIC", "ConnectX-5")
        node = self._make_node("TACC", components=[gpu, nic])
        s = self._make_slice(nodes=[node])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 1)
        comps = result[0]["components"]
        self.assertEqual(comps["GPU-Tesla T4"], 1)
        self.assertEqual(comps["SmartNIC-ConnectX-5"], 1)

    def test_multiple_same_components_counted(self):
        gpus = [self._make_component("GPU", "Tesla T4") for _ in range(3)]
        node = self._make_node("TACC", components=gpus)
        s = self._make_slice(nodes=[node])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(result[0]["components"]["GPU-Tesla T4"], 3)

    def test_component_with_none_type_skipped(self):
        comp = self._make_component(None, "ConnectX-5")
        node = self._make_node("TACC", components=[comp])
        s = self._make_slice(nodes=[node])
        result = FablibManager._slice_to_resources(s)
        self.assertNotIn("components", result[0])

    def test_component_with_none_model_skipped(self):
        comp = self._make_component("SmartNIC", None)
        node = self._make_node("TACC", components=[comp])
        s = self._make_slice(nodes=[node])
        result = FablibManager._slice_to_resources(s)
        self.assertNotIn("components", result[0])

    def test_node_with_none_cores_treated_as_zero(self):
        node = self._make_node("TACC", cores=None, ram=None, disk=None)
        s = self._make_slice(nodes=[node])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(result[0]["cores"], 0)
        self.assertEqual(result[0]["ram"], 0)
        self.assertEqual(result[0]["disk"], 0)

    def test_l2ptp_network_two_sites(self):
        net = self._make_l2network("L2PTP", ["TACC", "STAR"], bandwidth=25)
        s = self._make_slice(networks=[net])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "link")
        self.assertIn(result[0]["site_a"], ["TACC", "STAR"])
        self.assertIn(result[0]["site_b"], ["TACC", "STAR"])
        self.assertNotEqual(result[0]["site_a"], result[0]["site_b"])
        self.assertEqual(result[0]["bandwidth"], 25)

    def test_l2sts_network_included(self):
        net = self._make_l2network("L2STS", ["TACC", "STAR"])
        s = self._make_slice(networks=[net])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "link")

    def test_l2bridge_network_skipped(self):
        net = self._make_l2network("L2Bridge", ["TACC", "TACC"])
        s = self._make_slice(networks=[net])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 0)

    def test_l2ptp_single_site_skipped(self):
        """L2PTP with both interfaces on same site should be skipped."""
        net = self._make_l2network("L2PTP", ["TACC", "TACC"])
        s = self._make_slice(networks=[net])
        result = FablibManager._slice_to_resources(s)
        # sites set has only 1 element, so it's skipped
        self.assertEqual(len(result), 0)

    def test_facility_port(self):
        fp = self._make_facility_port("cloud-fp", "STAR", num_vlans=3)
        s = self._make_slice(facilities=[fp])
        result = FablibManager._slice_to_resources(s)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "facility_port")
        self.assertEqual(result[0]["name"], "cloud-fp")
        self.assertEqual(result[0]["site"], "STAR")
        self.assertEqual(result[0]["vlans"], 3)

    def test_mixed_resources(self):
        """Slice with nodes, networks, and facility ports."""
        gpu = self._make_component("GPU", "A30")
        nodes = [
            self._make_node("TACC", cores=8, ram=32, disk=100, components=[gpu]),
            self._make_node("STAR", cores=4, ram=16, disk=50),
        ]
        networks = [self._make_l2network("L2PTP", ["TACC", "STAR"], bandwidth=100)]
        facilities = [self._make_facility_port("my-port", "TACC", num_vlans=2)]
        s = self._make_slice(nodes=nodes, networks=networks, facilities=facilities)
        result = FablibManager._slice_to_resources(s)

        types = [r["type"] for r in result]
        self.assertEqual(types.count("compute"), 2)
        self.assertEqual(types.count("link"), 1)
        self.assertEqual(types.count("facility_port"), 1)


class TestNormalizeComponentKeys(FindResourceSlotTestBase):
    """Test _normalize_component_keys() static method."""

    def test_fablib_name_normalized_to_db_format(self):
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": {"NIC_ConnectX_5": 1},
            }
        ]
        result = FablibManager._normalize_component_keys(resources)
        comps = result[0]["components"]
        # Should be converted to "SmartNIC-ConnectX-5"
        self.assertIn("SmartNIC-ConnectX-5", comps)
        self.assertNotIn("NIC_ConnectX_5", comps)

    def test_already_normalized_keys_pass_through(self):
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": {"SmartNIC-ConnectX-5": 2},
            }
        ]
        result = FablibManager._normalize_component_keys(resources)
        self.assertEqual(result[0]["components"]["SmartNIC-ConnectX-5"], 2)

    def test_unknown_keys_pass_through(self):
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": {"SomeUnknownThing": 1},
            }
        ]
        result = FablibManager._normalize_component_keys(resources)
        self.assertIn("SomeUnknownThing", result[0]["components"])

    def test_gpu_normalization(self):
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": {"GPU_TeslaT4": 1, "GPU_A30": 2},
            }
        ]
        result = FablibManager._normalize_component_keys(resources)
        comps = result[0]["components"]
        self.assertIn("GPU-Tesla T4", comps)
        self.assertEqual(comps["GPU-Tesla T4"], 1)
        self.assertIn("GPU-A30", comps)
        self.assertEqual(comps["GPU-A30"], 2)

    def test_non_compute_resources_unchanged(self):
        resources = [
            {"type": "link", "site_a": "TACC", "site_b": "STAR", "bandwidth": 10},
            {"type": "facility_port", "name": "fp1", "site": "TACC", "vlans": 1},
        ]
        result = FablibManager._normalize_component_keys(resources)
        self.assertEqual(result, resources)

    def test_compute_without_components_unchanged(self):
        resources = [{"type": "compute", "site": "TACC", "cores": 4}]
        result = FablibManager._normalize_component_keys(resources)
        self.assertEqual(result[0], resources[0])

    def test_mixed_fablib_and_db_keys(self):
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": {
                    "NIC_ConnectX_5": 1,
                    "GPU-A30": 2,  # already DB format
                },
            }
        ]
        result = FablibManager._normalize_component_keys(resources)
        comps = result[0]["components"]
        self.assertIn("SmartNIC-ConnectX-5", comps)
        self.assertEqual(comps["SmartNIC-ConnectX-5"], 1)
        self.assertIn("GPU-A30", comps)
        self.assertEqual(comps["GPU-A30"], 2)

    def test_original_resources_not_mutated(self):
        original_comps = {"NIC_ConnectX_5": 1}
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": original_comps,
            }
        ]
        FablibManager._normalize_component_keys(resources)
        # Original dict should not be modified
        self.assertIn("NIC_ConnectX_5", original_comps)


class TestFindResourceSlotManagerCall(FindResourceSlotTestBase):
    """Test that find_resource_slot() correctly calls the manager."""

    def test_resources_forwarded_to_manager(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=4)
        resources = [
            {"type": "compute", "site": "TACC", "cores": 4, "ram": 16, "disk": 50}
        ]
        expected = {"slots": [{"start": "2025-07-01T00:00:00Z"}]}

        mock_manager = MagicMock()
        mock_manager.find_resource_slot.return_value = expected

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.find_resource_slot(
                start=start, end=end, duration=2, resources=resources, max_results=3
            )

        mock_manager.find_resource_slot.assert_called_once_with(
            start=start, end=end, duration=2, resources=resources, max_results=3
        )
        self.assertEqual(result, expected)

    def test_slice_converted_and_forwarded(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=4)

        mock_slice = MagicMock()
        mock_slice.get_nodes.return_value = []
        mock_slice.get_l2networks.return_value = []
        mock_slice.get_facilities.return_value = []

        mock_manager = MagicMock()
        mock_manager.find_resource_slot.return_value = {"slots": []}

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            self.fablib.find_resource_slot(
                start=start, end=end, duration=1, slice=mock_slice
            )

        mock_manager.find_resource_slot.assert_called_once()
        call_kwargs = mock_manager.find_resource_slot.call_args[1]
        self.assertEqual(call_kwargs["resources"], [])
        self.assertEqual(call_kwargs["start"], start)
        self.assertEqual(call_kwargs["end"], end)
        self.assertEqual(call_kwargs["duration"], 1)

    def test_component_keys_normalized_before_manager_call(self):
        """Ensure fablib-format keys are normalized before hitting the API."""
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=4)
        resources = [
            {
                "type": "compute",
                "site": "TACC",
                "cores": 2,
                "components": {"NIC_ConnectX_5": 1},
            }
        ]

        mock_manager = MagicMock()
        mock_manager.find_resource_slot.return_value = {"slots": []}

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            self.fablib.find_resource_slot(
                start=start, end=end, duration=1, resources=resources
            )

        call_kwargs = mock_manager.find_resource_slot.call_args[1]
        comps = call_kwargs["resources"][0]["components"]
        self.assertIn("SmartNIC-ConnectX-5", comps)
        self.assertNotIn("NIC_ConnectX_5", comps)


if __name__ == "__main__":
    unittest.main()
