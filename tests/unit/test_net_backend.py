"""Unit tests for per-device network backend selection and fallback."""

import json
import unittest
from ipaddress import IPv4Address, IPv4Network
from unittest.mock import MagicMock

from fabrictestbed_extensions.fablib.node import Node


def _make_node(outputs):
    """
    Build a Node without a slice whose ``execute`` answers from ``outputs``.

    :param outputs: dict mapping a command substring to its stdout, or a
        callable taking the command and returning stdout.
    """
    node = Node.__new__(Node)
    node._net_config_backend = None
    node._net_backend_by_device = {}
    node._netplan_present = None
    node._persistent_config = True
    node.get_name = MagicMock(return_value="Node1")
    node.calls = []

    def execute(command, quiet=True, **kwargs):
        node.calls.append(command)
        if callable(outputs):
            return outputs(command), ""
        for key, value in outputs.items():
            if key in command:
                return value, ""
        return "", ""

    node.execute = execute
    return node


UBUNTU_WITH_NM = {
    "command -v nmcli": "/usr/bin/nmcli\n",
    "command -v netplan": "/usr/sbin/netplan\n",
    "device status": "enp3s0:unmanaged\nenp7s0:unmanaged\nlo:unmanaged\n",
}
ROCKY = {
    "command -v nmcli": "/usr/bin/nmcli\n",
    "command -v netplan": "",
    "device status": "eth0:unmanaged\neth1:disconnected\nlo:unmanaged\n",
}
UBUNTU_STOCK = {
    "command -v nmcli": "",
    "command -v netplan": "/usr/sbin/netplan\n",
}


class TestBackendSelection(unittest.TestCase):
    def test_ubuntu_nm_unmanaged_device_uses_netplan(self):
        node = _make_node(UBUNTU_WITH_NM)
        self.assertEqual(node._get_effective_backend(ifname="enp7s0"), "netplan")

    def test_result_is_cached_per_device(self):
        node = _make_node(UBUNTU_WITH_NM)
        node._get_effective_backend(ifname="enp7s0")
        node._get_effective_backend(ifname="enp7s0")
        status_calls = [c for c in node.calls if "device status" in c]
        self.assertEqual(len(status_calls), 1)

    def test_rocky_managed_device_keeps_nmcli(self):
        node = _make_node(ROCKY)
        self.assertEqual(node._get_effective_backend(ifname="eth1"), "nmcli")

    def test_stock_ubuntu_uses_netplan(self):
        node = _make_node(UBUNTU_STOCK)
        self.assertEqual(node._get_effective_backend(ifname="enp7s0"), "netplan")

    def test_unmanaged_without_netplan_uses_ip(self):
        outputs = dict(ROCKY, **{"device status": "eth1:unmanaged\n"})
        node = _make_node(outputs)
        self.assertEqual(node._get_effective_backend(ifname="eth1"), "ip")

    def test_unknown_device_keeps_nmcli_and_rechecks(self):
        node = _make_node(ROCKY)
        self.assertEqual(node._get_effective_backend(ifname="eth9"), "nmcli")
        self.assertNotIn("eth9", node._net_backend_by_device)

    def test_vlan_subinterface_checks_parent(self):
        node = _make_node(UBUNTU_WITH_NM)
        self.assertEqual(node._get_effective_backend(ifname="enp7s0.100"), "netplan")
        self.assertIn("enp7s0", node._net_backend_by_device)

    def test_no_ifname_returns_node_level_backend(self):
        node = _make_node(UBUNTU_WITH_NM)
        self.assertEqual(node._get_effective_backend(), "nmcli")

    def test_persistent_false_forces_ip(self):
        node = _make_node(UBUNTU_WITH_NM)
        self.assertEqual(
            node._get_effective_backend(persistent=False, ifname="enp7s0"), "ip"
        )

    def test_fall_back_from_nmcli_is_remembered(self):
        node = _make_node(ROCKY)
        self.assertEqual(node._fall_back_from_nmcli("eth1"), "ip")
        self.assertEqual(node._get_effective_backend(ifname="eth1"), "ip")


class TestExecuteChecked(unittest.TestCase):
    def test_returns_output_without_marker(self):
        node = _make_node(lambda cmd: "hello\n__fablib_rc=0\n")
        self.assertEqual(node._execute_checked("echo hello", "echo").strip(), "hello")

    def test_raises_on_nonzero_exit(self):
        node = _make_node(
            lambda cmd: "Error: No suitable device found\n__fablib_rc=4\n"
        )
        with self.assertRaises(RuntimeError) as ctx:
            node._execute_checked("nmcli c up x", "nmcli c up x")
        self.assertIn("rc=4", str(ctx.exception))
        self.assertIn("No suitable device", str(ctx.exception))

    def test_raises_when_marker_missing(self):
        node = _make_node(lambda cmd: "")
        with self.assertRaises(RuntimeError):
            node._execute_checked("true", "true")

    def test_nmcli_up_failure_raises(self):
        node = _make_node(lambda cmd: "__fablib_rc=4\n")
        with self.assertRaises(RuntimeError):
            node._nmcli_up("fabric-enp7s0")


class TestVerifyIp(unittest.TestCase):
    ENTRY = [
        {
            "ifname": "enp7s0",
            "addr_info": [{"family": "inet", "local": "10.136.129.2"}],
        }
    ]

    def test_present(self):
        node = _make_node(lambda cmd: json.dumps(self.ENTRY))
        node._verify_ip_on_device("enp7s0", "10.136.129.2", interval=0)

    def test_polls_until_present(self):
        answers = iter(["[]", "[]", json.dumps(self.ENTRY)])
        node = _make_node(lambda cmd: next(answers))
        node._verify_ip_on_device("enp7s0", "10.136.129.2", attempts=5, interval=0)
        self.assertEqual(len(node.calls), 3)

    def test_absent_raises(self):
        node = _make_node(lambda cmd: "[]")
        with self.assertRaises(RuntimeError):
            node._verify_ip_on_device("enp7s0", "10.136.129.2", attempts=3, interval=0)


class TestIpAddrAddFallback(unittest.TestCase):
    def _node_and_iface(self, outputs, device="enp7s0"):
        node = _make_node(outputs)
        for name in (
            "_nmcli_ensure_connection",
            "_nmcli_up",
            "_netplan_write_config",
            "_netplan_apply",
            "_verify_ip_on_device",
            "_ip_addr_add_legacy",
        ):
            setattr(node, name, MagicMock())
        iface = MagicMock()
        iface.get_network.return_value = None
        iface.get_device_name.return_value = device
        return node, iface

    def _add(self, node, iface):
        node.ip_addr_add(
            addr=IPv4Address("10.136.129.2"),
            subnet=IPv4Network("10.136.129.0/24"),
            interface=iface,
        )

    def test_unmanaged_device_goes_straight_to_netplan(self):
        node, iface = self._node_and_iface(UBUNTU_WITH_NM)
        self._add(node, iface)
        node._nmcli_up.assert_not_called()
        node._netplan_write_config.assert_called_once()
        node._ip_addr_add_legacy.assert_not_called()

    def test_nmcli_failure_falls_back_to_netplan(self):
        outputs = dict(UBUNTU_WITH_NM, **{"device status": "enp7s0:disconnected\n"})
        node, iface = self._node_and_iface(outputs)
        node._verify_ip_on_device.side_effect = [RuntimeError("missing"), None]
        self._add(node, iface)
        node._nmcli_up.assert_called_once()
        node._netplan_write_config.assert_called_once()
        node._ip_addr_add_legacy.assert_not_called()
        self.assertEqual(node._net_backend_by_device["enp7s0"], "netplan")

    def test_all_persistent_backends_fail_uses_ip(self):
        outputs = dict(UBUNTU_WITH_NM, **{"device status": "enp7s0:disconnected\n"})
        node, iface = self._node_and_iface(outputs)
        node._verify_ip_on_device.side_effect = RuntimeError("missing")
        self._add(node, iface)
        node._ip_addr_add_legacy.assert_called_once()

    def test_rocky_success_stays_on_nmcli(self):
        node, iface = self._node_and_iface(ROCKY, device="eth1")
        self._add(node, iface)
        node._nmcli_up.assert_called_once()
        node._netplan_write_config.assert_not_called()
        node._ip_addr_add_legacy.assert_not_called()


class TestCephSetupFailure(unittest.TestCase):
    def test_mount_script_failure_raises(self):
        from fabrictestbed_extensions.fablib.slice import _setup_ceph_on_node

        node = _make_node(
            lambda cmd: "ERROR: mount failed with rc=32\n__fablib_rc=32\n"
        )
        node.upload_directory = MagicMock()
        bundle = {
            "cluster_dir": "/tmp/east",
            "mount_script": "/tmp/east/mount_alice.sh",
        }
        with self.assertRaises(RuntimeError) as ctx:
            _setup_ceph_on_node(node, bundle)
        self.assertIn("mount failed", str(ctx.exception))

    def test_mount_script_success(self):
        from fabrictestbed_extensions.fablib.slice import _setup_ceph_on_node

        node = _make_node(lambda cmd: "All mounts attempted.\n__fablib_rc=0\n")
        node.upload_directory = MagicMock()
        bundle = {
            "cluster_dir": "/tmp/east",
            "mount_script": "/tmp/east/mount_alice.sh",
        }
        _setup_ceph_on_node(node, bundle)


if __name__ == "__main__":
    unittest.main()
