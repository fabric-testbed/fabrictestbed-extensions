import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager


class FabNet4ExtTest(unittest.TestCase):
    """
    Run some basic tests against the testbed.
    """

    fablib = None
    slice_name = "MySlice-fabnet-v4ext"
    node1_name = "Node1"
    node2_name = "Node2"

    network1_name = "net1"
    network2_name = "net2"

    node1_nic_name = "nic1"
    node2_nic_name = "nic2"

    def setUp(self) -> None:
        self.fablib = FablibManager()
        self.fablib.show_config()

    def test_1_fabnetv4_ext_create_slice(self):
        """
        Create a slice with a single node, and echo a message from the node.
        """
        [site1, site2] = self.fablib.get_random_sites(count=2)
        print(f"Sites: {site1}, {site2}")

        # Create Slice
        slice = self.fablib.new_slice(name=self.slice_name)

        # Node1
        node1 = slice.add_node(name=self.node1_name, site=site1)
        iface1 = node1.add_component(
            model="NIC_Basic", name=self.node1_nic_name
        ).get_interfaces()[0]

        # Node2
        node2 = slice.add_node(name=self.node2_name, site=site2)
        iface2 = node2.add_component(
            model="NIC_Basic", name=self.node2_nic_name
        ).get_interfaces()[0]

        # NetworkS
        net1 = slice.add_l3network(
            name=self.network1_name, interfaces=[iface1], type="IPv4Ext"
        )
        net2 = slice.add_l3network(
            name=self.network2_name, interfaces=[iface2], type="IPv4Ext"
        )

        # Submit Slice Request
        slice.submit()

    def test_2_fabnetv4_ext_make_ip_routable(self):
        slice = self.fablib.get_slice(name=self.slice_name)
        network1 = slice.get_network(name=self.network1_name)
        network1_available_ips = network1.get_available_ips()
        network1.show()

        network2 = slice.get_network(name=self.network2_name)
        network2_available_ips = network2.get_available_ips()
        network2.show()

        try:
            # Enable Public IPv6 make_ip_publicly_routable
            network1.make_ip_publicly_routable(ipv4=[str(network1_available_ips[0])])

            # Enable Public IPv6 make_ip_publicly_routable
            network2.make_ip_publicly_routable(ipv4=[str(network2_available_ips[0])])

            slice.submit()

        except Exception as e:
            print(f"Exception: {e}")
            import traceback

            traceback.print_exc()

    def test_3_fabnetv4_ext_connectivity(self):
        slice = self.fablib.get_slice(name=self.slice_name)
        network1 = slice.get_network(name=self.network1_name)
        network2 = slice.get_network(name=self.network2_name)

        node1 = slice.get_node(name=self.node1_name)
        node1_iface = node1.get_interface(network_name=self.network1_name)
        node1_addr = network1.get_public_ips()[0]
        node1_iface.ip_addr_add(addr=node1_addr, subnet=network1.get_subnet())

        node1.ip_route_add(subnet=network2.get_subnet(), gateway=network1.get_gateway())

        # Add route to external network
        stdout, stderr = node1.execute(
            f"sudo ip route add 0.0.0.0/1 via {network1.get_gateway()}"
        )

        stdout, stderr = node1.execute(f"ip addr show {node1_iface.get_device_name()}")
        stdout, stderr = node1.execute(f"ip route list")

        node2 = slice.get_node(name=self.node2_name)
        node2_iface = node2.get_interface(network_name=self.network2_name)
        node2_addr = network2.get_public_ips()[0]
        node2_iface.ip_addr_add(addr=node2_addr, subnet=network2.get_subnet())

        node2.ip_route_add(subnet=network1.get_subnet(), gateway=network2.get_gateway())

        # Add route to external network
        stdout, stderr = node2.execute(
            f"sudo ip route add 0.0.0.0/1 via {network2.get_gateway()}"
        )

        stdout, stderr = node2.execute(f"ip addr show {node2_iface.get_device_name()}")
        stdout, stderr = node2.execute(f"ip route list")

        node1 = slice.get_node(name=self.node1_name)
        node2 = slice.get_node(name=self.node2_name)

        node2_addr = node2.get_interface(network_name=self.network2_name).get_ip_addr()

        stdout, stderr = node1.execute(f"ping -c 5 {node2_addr}")

        # Verify external connectivity
        stdout, stderr = node1.execute(
            f"sudo ping -c 5 -I {node1_iface.get_device_name()} bing.com"
        )

        stdout, stderr = node1.execute(
            f"sudo ping -c 5 -I {node2_iface.get_device_name()} bing.com"
        )

    def test_3_fabnetv4_ext_delete(self):
        slice = self.fablib.get_slice(name=self.slice_name)
        slice.delete()


if __name__ == "__main__":
    unittest.main()
