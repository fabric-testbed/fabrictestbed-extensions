"""Unit tests for FacilityPort, focusing on multi-VLAN interface creation."""

import unittest
from unittest.mock import MagicMock

from fim.user.topology import ExperimentTopology

from fabrictestbed_extensions.fablib.facility_port import FacilityPort


class TestFacilityPortMultiVlan(unittest.TestCase):
    """Test that add_facility_port with multiple VLANs creates distinct interfaces."""

    def _make_mock_slice(self):
        """Create a mock Slice backed by a real FIM ExperimentTopology."""
        topology = ExperimentTopology()
        mock_slice = MagicMock()
        mock_slice.get_fim_topology.return_value = topology
        return mock_slice, topology

    def test_single_vlan_creates_one_interface(self):
        mock_slice, topology = self._make_mock_slice()

        fp = FacilityPort.new_facility_port(
            slice=mock_slice,
            name="TestFP-LOSA",
            site="LOSA",
            vlan="3520",
        )

        interfaces = list(fp.get_fim().interfaces.values())
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].labels.vlan, "3520")

    def test_single_vlan_as_list_creates_one_interface(self):
        mock_slice, topology = self._make_mock_slice()

        fp = FacilityPort.new_facility_port(
            slice=mock_slice,
            name="TestFP-LOSA",
            site="LOSA",
            vlan=["3520"],
        )

        interfaces = list(fp.get_fim().interfaces.values())
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].labels.vlan, "3520")

    def test_multiple_vlans_create_distinct_interfaces(self):
        mock_slice, topology = self._make_mock_slice()

        fp = FacilityPort.new_facility_port(
            slice=mock_slice,
            name="TestFP-LOSA",
            site="LOSA",
            vlan=["3520", "3521", "3522"],
        )

        interfaces = list(fp.get_fim().interfaces.values())
        self.assertEqual(len(interfaces), 3)

        # Each interface should have a unique name
        names = [iface.name for iface in interfaces]
        self.assertEqual(len(set(names)), 3, f"Interface names are not unique: {names}")

        # Each interface should have the correct VLAN
        vlans = sorted(iface.labels.vlan for iface in interfaces)
        self.assertEqual(vlans, ["3520", "3521", "3522"])

    def test_multiple_vlans_interface_naming(self):
        mock_slice, topology = self._make_mock_slice()

        fp = FacilityPort.new_facility_port(
            slice=mock_slice,
            name="TestFP-LOSA",
            site="LOSA",
            vlan=["100", "200"],
        )

        interfaces = list(fp.get_fim().interfaces.values())
        names = sorted(iface.name for iface in interfaces)
        self.assertEqual(names, ["iface-1", "iface-2"])

    def test_no_vlan_creates_default_interface(self):
        mock_slice, topology = self._make_mock_slice()

        fp = FacilityPort.new_facility_port(
            slice=mock_slice,
            name="TestFP-LOSA",
            site="LOSA",
        )

        interfaces = list(fp.get_fim().interfaces.values())
        self.assertEqual(len(interfaces), 1)
        # Default interface uses name-int naming from FIM
        self.assertEqual(interfaces[0].name, "TestFP-LOSA-int")


if __name__ == "__main__":
    unittest.main()
