"""Integration tests for FABNetv4Ext (external IPv4) connectivity.

Run with::

    pytest tests/integration/test_fabnetv4_ext.py -v
"""

import pytest

pytestmark = [pytest.mark.network, pytest.mark.p1]


@pytest.mark.timeout(1200)
def test_fabnetv4_ext_lifecycle(fablib, available_sites_pair, slice_factory):
    """Create a slice with FABNetv4Ext, make IPs routable, verify connectivity."""
    site1, site2 = available_sites_pair

    node1_name = "Node1"
    node2_name = "Node2"
    network1_name = "net1"
    network2_name = "net2"

    # Step 1: Create slice with two nodes and external networks
    s = slice_factory("fabnetv4-ext")

    node1 = s.add_node(name=node1_name, site=site1)
    iface1 = node1.add_component(
        model="NIC_Basic", name="nic1"
    ).get_interfaces()[0]

    node2 = s.add_node(name=node2_name, site=site2)
    iface2 = node2.add_component(
        model="NIC_Basic", name="nic2"
    ).get_interfaces()[0]

    s.add_l3network(name=network1_name, interfaces=[iface1], type="IPv4Ext")
    s.add_l3network(name=network2_name, interfaces=[iface2], type="IPv4Ext")

    s.submit()

    # Step 2: Make IPs publicly routable
    s = fablib.get_slice(name=s.get_name())
    network1 = s.get_network(name=network1_name)
    network1_available_ips = network1.get_available_ips()

    network2 = s.get_network(name=network2_name)
    network2_available_ips = network2.get_available_ips()

    network1.make_ip_publicly_routable(ipv4=[str(network1_available_ips[0])])
    network2.make_ip_publicly_routable(ipv4=[str(network2_available_ips[0])])
    s.submit()

    # Step 3: Configure IPs and verify connectivity
    s = fablib.get_slice(name=s.get_name())
    network1 = s.get_network(name=network1_name)
    network2 = s.get_network(name=network2_name)

    node1 = s.get_node(name=node1_name)
    node1_iface = node1.get_interface(network_name=network1_name)
    node1_addr = network1.get_public_ips()[0]
    node1_iface.ip_addr_add(addr=node1_addr, subnet=network1.get_subnet())
    node1.ip_route_add(subnet=network2.get_subnet(), gateway=network1.get_gateway())

    node1.execute(
        f"sudo ip route add 0.0.0.0/1 via {network1.get_gateway()}"
    )

    node2 = s.get_node(name=node2_name)
    node2_iface = node2.get_interface(network_name=network2_name)
    node2_addr = network2.get_public_ips()[0]
    node2_iface.ip_addr_add(addr=node2_addr, subnet=network2.get_subnet())
    node2.ip_route_add(subnet=network1.get_subnet(), gateway=network2.get_gateway())

    node2.execute(
        f"sudo ip route add 0.0.0.0/1 via {network2.get_gateway()}"
    )

    # Verify inter-node connectivity
    node2_addr = node2.get_interface(network_name=network2_name).get_ip_addr()
    stdout, stderr = node1.execute(f"ping -c 5 {node2_addr}")
    assert "0% packet loss" in stdout or "5 received" in stdout
