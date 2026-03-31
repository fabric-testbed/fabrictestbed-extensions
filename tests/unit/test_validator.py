"""Unit tests for NodeValidator."""

import unittest
from unittest.mock import MagicMock, PropertyMock

from fabrictestbed_extensions.fablib.validator import NodeValidator


class TestCanAllocateNodeInHost(unittest.TestCase):
    """Tests for NodeValidator.can_allocate_node_in_host."""

    def _make_node(self, cores=2, ram=8, disk=10, components=None):
        """Create a mock Node with the given resource requests."""
        node = MagicMock()
        node.get_requested_cores.return_value = cores
        node.get_requested_ram.return_value = ram
        node.get_requested_disk.return_value = disk
        node.get_components.return_value = components or []
        return node

    def _make_host(
        self,
        name="host1",
        state="Active",
        cores=32,
        ram=128,
        disk=1000,
        components=None,
    ):
        """Create a host dict matching ResourcesV2 format."""
        return {
            "name": name,
            "state": state,
            "cores_available": cores,
            "ram_available": ram,
            "disk_available": disk,
            "components": components or {},
        }

    def test_node_fits_on_active_host(self):
        host = self._make_host()
        node = self._make_node()
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertTrue(success)
        self.assertEqual(allocated["core"], 2)
        self.assertEqual(allocated["ram"], 8)
        self.assertEqual(allocated["disk"], 10)

    def test_inactive_host_rejected(self):
        host = self._make_host(state="Maintenance")
        node = self._make_node()
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)
        self.assertIn("Maintenance", msg)

    def test_insufficient_cores(self):
        host = self._make_host(cores=1)
        node = self._make_node(cores=4)
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)
        self.assertIn("Insufficient Resources", msg)

    def test_insufficient_ram(self):
        host = self._make_host(ram=4)
        node = self._make_node(ram=16)
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)

    def test_insufficient_disk(self):
        host = self._make_host(disk=5)
        node = self._make_node(disk=100)
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)

    def test_cumulative_allocation_tracked(self):
        host = self._make_host(cores=10, ram=32, disk=200)
        node1 = self._make_node(cores=6, ram=16, disk=100)
        node2 = self._make_node(cores=6, ram=16, disk=100)
        allocated = {}
        site = {"state": "Active"}

        # First node fits (6 of 10 cores)
        success1, _ = NodeValidator.can_allocate_node_in_host(
            host=host, node=node1, allocated=allocated, site=site
        )
        self.assertTrue(success1)

        # Second node doesn't fit (needs 6, only 4 remaining)
        success2, _ = NodeValidator.can_allocate_node_in_host(
            host=host, node=node2, allocated=allocated, site=site
        )
        self.assertFalse(success2)

    def test_component_available(self):
        comp = MagicMock()
        comp.get_type.return_value = "GPU"
        comp.get_fim_model.return_value = "Tesla_T4"
        node = self._make_node(components=[comp])

        host = self._make_host(
            components={"GPU-Tesla_T4": {"capacity": 4, "allocated": 0}}
        )
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertTrue(success)
        self.assertEqual(allocated["GPU-Tesla_T4"], 1)

    def test_component_not_available(self):
        comp = MagicMock()
        comp.get_type.return_value = "GPU"
        comp.get_fim_model.return_value = "A100"
        node = self._make_node(components=[comp])

        host = self._make_host(components={})
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)
        self.assertIn("does not have", msg)

    def test_component_exhausted(self):
        comp = MagicMock()
        comp.get_type.return_value = "GPU"
        comp.get_fim_model.return_value = "Tesla_T4"
        node = self._make_node(components=[comp])

        host = self._make_host(
            components={"GPU-Tesla_T4": {"capacity": 2, "allocated": 2}}
        )
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)
        self.assertIn("reached the limit", msg)

    def test_none_host_skips_validation(self):
        node = self._make_node()
        allocated = {}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=None, node=node, allocated=allocated, site={"state": "Active"}
        )

        self.assertTrue(success)
        self.assertIn("Ignoring validation", msg)

    def test_none_site_skips_validation(self):
        host = self._make_host()
        node = self._make_node()
        allocated = {}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=None
        )

        self.assertTrue(success)
        self.assertIn("Ignoring validation", msg)

    def test_none_cores_available_treated_as_zero(self):
        host = self._make_host()
        host["cores_available"] = None
        node = self._make_node(cores=1)
        allocated = {}
        site = {"state": "Active"}

        success, msg = NodeValidator.can_allocate_node_in_host(
            host=host, node=node, allocated=allocated, site=site
        )

        self.assertFalse(success)


class TestValidateNode(unittest.TestCase):
    """Tests for NodeValidator.validate_node."""

    def _make_node(self, site="TACC", host=None, cores=2, ram=8, disk=10):
        node = MagicMock()
        node.get_site.return_value = site
        node.get_host.return_value = host
        node.get_name.return_value = "test-node"
        node.get_requested_cores.return_value = cores
        node.get_requested_ram.return_value = ram
        node.get_requested_disk.return_value = disk
        node.get_components.return_value = []
        return node

    def _make_resources(self, site=None, hosts=None):
        resources = MagicMock()
        resources.get_site.return_value = site
        resources.get_hosts_by_site.return_value = hosts
        return resources

    def test_missing_site_skips(self):
        node = self._make_node(site="NONEXISTENT")
        resources = self._make_resources(site=None)

        success, msg = NodeValidator.validate_node(node=node, resources=resources)

        self.assertTrue(success)
        self.assertIn("Ignoring validation", msg)

    def test_inactive_site_rejected(self):
        node = self._make_node()
        resources = self._make_resources(site={"state": "Maintenance"})

        success, msg = NodeValidator.validate_node(node=node, resources=resources)

        self.assertFalse(success)
        self.assertIn("Maintenance", msg)

    def test_no_hosts_rejected(self):
        node = self._make_node()
        resources = self._make_resources(site={"state": "Active"}, hosts=None)

        success, msg = NodeValidator.validate_node(node=node, resources=resources)

        self.assertFalse(success)
        self.assertIn("host information not available", msg)

    def test_specific_host_not_found(self):
        node = self._make_node(host="nonexistent-host")
        resources = self._make_resources(site={"state": "Active"}, hosts={"host1": {}})

        success, msg = NodeValidator.validate_node(node=node, resources=resources)

        self.assertFalse(success)
        self.assertIn("does not exist", msg)

    def test_valid_node_on_active_site(self):
        node = self._make_node()
        host = {
            "name": "host1",
            "state": "Active",
            "cores_available": 32,
            "ram_available": 128,
            "disk_available": 1000,
            "components": {},
        }
        resources = self._make_resources(
            site={"state": "Active"}, hosts={"host1": host}
        )

        success, msg = NodeValidator.validate_node(node=node, resources=resources)

        self.assertTrue(success)


class TestValidateNodes(unittest.TestCase):
    """Tests for NodeValidator.validate_nodes (batch validation)."""

    def test_all_valid(self):
        nodes = []
        for i in range(3):
            node = MagicMock()
            node.get_site.return_value = "TACC"
            node.get_host.return_value = None
            node.get_name.return_value = f"node{i}"
            node.get_requested_cores.return_value = 2
            node.get_requested_ram.return_value = 8
            node.get_requested_disk.return_value = 10
            node.get_components.return_value = []
            nodes.append(node)

        host = {
            "name": "host1",
            "state": "Active",
            "cores_available": 64,
            "ram_available": 256,
            "disk_available": 5000,
            "components": {},
        }
        resources = MagicMock()
        resources.get_site.return_value = {"state": "Active"}
        resources.get_hosts_by_site.return_value = {"host1": host}

        all_valid, errors = NodeValidator.validate_nodes(
            nodes=nodes, resources=resources
        )

        self.assertTrue(all_valid)
        self.assertEqual(len(errors), 0)

    def test_some_invalid(self):
        node_ok = MagicMock()
        node_ok.get_site.return_value = "TACC"
        node_ok.get_host.return_value = None
        node_ok.get_name.return_value = "ok"
        node_ok.get_requested_cores.return_value = 2
        node_ok.get_requested_ram.return_value = 8
        node_ok.get_requested_disk.return_value = 10
        node_ok.get_components.return_value = []

        node_bad = MagicMock()
        node_bad.get_site.return_value = "CLOSED"
        node_bad.get_host.return_value = None
        node_bad.get_name.return_value = "bad"
        node_bad.get_requested_cores.return_value = 2
        node_bad.get_requested_ram.return_value = 8
        node_bad.get_requested_disk.return_value = 10
        node_bad.get_components.return_value = []

        host = {
            "name": "host1",
            "state": "Active",
            "cores_available": 64,
            "ram_available": 256,
            "disk_available": 5000,
            "components": {},
        }
        resources = MagicMock()

        def get_site(site_name):
            if site_name == "TACC":
                return {"state": "Active"}
            return {"state": "Closed"}

        resources.get_site.side_effect = get_site
        resources.get_hosts_by_site.return_value = {"host1": host}

        all_valid, errors = NodeValidator.validate_nodes(
            nodes=[node_ok, node_bad], resources=resources
        )

        self.assertFalse(all_valid)
        self.assertIn("bad", errors)
        self.assertNotIn("ok", errors)
