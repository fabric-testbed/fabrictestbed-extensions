"""P1 FABNetv4 (L3 routed IPv4) network tests.

Run with::

    pytest tests/integration/test_network_fabnetv4.py -v
    pytest tests/integration -m network -v
"""

import pytest

pytestmark = [
    pytest.mark.network,
    pytest.mark.p1,
    pytest.mark.slow,
    pytest.mark.timeout(1200),
]


class TestFABNetv4:
    """Test FABNetv4 auto-configured L3 IPv4 routing."""

    def test_fabnetv4_cross_site_ping(
        self, fablib, available_sites_pair, slice_factory
    ):
        """Two nodes on different sites can ping via FABNetv4."""
        site1, site2 = available_sites_pair
        s = slice_factory("fabnetv4-ping")

        node1 = s.add_node(name="node1", site=site1, cores=1, ram=2, disk=10)
        iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
        iface1.set_mode("auto")
        net1 = s.add_l3network(name="net1", interfaces=[iface1], type="IPv4")

        node2 = s.add_node(name="node2", site=site2, cores=1, ram=2, disk=10)
        iface2 = node2.add_component(model="NIC_Basic", name="nic2").get_interfaces()[0]
        iface2.set_mode("auto")
        net2 = s.add_l3network(name="net2", interfaces=[iface2], type="IPv4")

        s.submit()

        node1 = s.get_node(name="node1")
        node2 = s.get_node(name="node2")

        node2_iface = node2.get_interface(network_name="net2")
        node2_ip = node2_iface.get_ip_addr()
        assert node2_ip is not None, "node2 should have an auto-assigned IP"

        stdout, _ = node1.execute(f"ping -c 5 -W 10 {node2_ip}", quiet=True)
        assert "0% packet loss" in stdout or "0.0% packet loss" in stdout
