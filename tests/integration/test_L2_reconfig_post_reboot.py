"""Integration test for L2 network reconfiguration after node reboot.

Verifies that automatic L2Bridge configuration survives a reboot when
nodes are reconfigured afterward.

Run with::

    pytest tests/integration/test_L2_reconfig_post_reboot.py -v
"""

from ipaddress import IPv4Network

import pytest

pytestmark = [pytest.mark.network, pytest.mark.p2, pytest.mark.slow]


@pytest.mark.timeout(1200)
def test_reconfig_post_reboot(fablib, available_site_with_shared_nic, slice_factory):
    """Create L2 bridge, verify ping, reboot both nodes, reconfigure, verify again."""
    site = available_site_with_shared_nic
    s = slice_factory("l2-reconfig-reboot")

    network_name = "net1"
    node1_name = "Node1"
    node2_name = "Node2"

    # Build topology
    net1 = s.add_l2network(name=network_name, subnet=IPv4Network("192.168.1.0/24"))

    node1 = s.add_node(name=node1_name, site=site, image="default_ubuntu_22")
    iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
    iface1.set_mode("auto")
    net1.add_interface(iface1)

    node2 = s.add_node(name=node2_name, site=site, image="default_ubuntu_22")
    iface2 = node2.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
    iface2.set_mode("auto")
    net1.add_interface(iface2)

    s.submit()

    # Verify initial connectivity
    s = fablib.get_slice(s.get_name())
    node1 = s.get_node(name=node1_name)
    node2 = s.get_node(name=node2_name)
    node2_addr = node2.get_interface(network_name=network_name).get_ip_addr()

    stdout, stderr = node1.execute(f"ping -c 5 {node2_addr}")
    assert "5 packets transmitted, 5 received, 0% packet loss" in stdout

    # Reboot both nodes
    node1.execute("sudo reboot")
    node2.execute("sudo reboot")

    # Wait and reconfigure
    s.wait_ssh()
    node1 = s.get_node(name=node1_name)
    node1.config()
    node2 = s.get_node(name=node2_name)
    node2.config()

    # Verify connectivity after reboot
    s = fablib.get_slice(s.get_name())
    node1 = s.get_node(name=node1_name)
    node2 = s.get_node(name=node2_name)
    node2_addr = node2.get_interface(network_name=network_name).get_ip_addr()

    stdout, stderr = node1.execute(f"ping -c 5 {node2_addr}")
    assert "5 packets transmitted, 5 received, 0% packet loss" in stdout
