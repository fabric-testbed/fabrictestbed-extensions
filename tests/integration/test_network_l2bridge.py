"""P1 L2Bridge network tests — single-site Ethernet bridge.

Run with::

    pytest tests/integration/test_network_l2bridge.py -v
    pytest tests/integration -m network -v
"""

import pytest
from ipaddress import IPv4Network

pytestmark = [pytest.mark.network, pytest.mark.p1, pytest.mark.timeout(900)]


class TestL2Bridge:
    """Test L2Bridge (single-site local Ethernet)."""

    def test_l2bridge_two_node_ping(
        self, fablib, available_site_with_shared_nic, slice_factory
    ):
        """Two nodes on the same site can ping each other via L2Bridge."""
        site = available_site_with_shared_nic
        s = slice_factory("l2bridge-ping")

        net = s.add_l2network(name="net1", subnet=IPv4Network("192.168.1.0/24"))

        node1 = s.add_node(name="node1", site=site, cores=1, ram=2, disk=10)
        iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
        iface1.set_mode("auto")
        net.add_interface(iface1)

        node2 = s.add_node(name="node2", site=site, cores=1, ram=2, disk=10)
        iface2 = node2.add_component(model="NIC_Basic", name="nic2").get_interfaces()[0]
        iface2.set_mode("auto")
        net.add_interface(iface2)

        s.submit()

        node1 = s.get_node(name="node1")
        node2 = s.get_node(name="node2")

        node2_iface = node2.get_interface(network_name="net1")
        node2_addr = node2_iface.get_ip_addr()
        assert node2_addr is not None, "node2 should have an IP on net1"

        stdout, _ = node1.execute(f"ping -c 3 -W 5 {node2_addr}", quiet=True)
        assert "0% packet loss" in stdout or "0.0% packet loss" in stdout
