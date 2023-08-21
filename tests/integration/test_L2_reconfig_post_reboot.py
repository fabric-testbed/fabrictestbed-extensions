#!/usr/bin/env python3
# # Create a Local Ethernet (Layer 2) Network: Automatic Configuration
#
# This notebook shows how to create an isolated local Ethernet and connect compute nodes to it and
# use FABlib's automatic configuration functionality.
#
import unittest
from ipaddress import IPv4Network

from fabrictestbed_extensions.fablib.fablib import FablibManager


class L2ReconfigPostRebootTests(unittest.TestCase):
    def test_reconfig_post_reboot(self):
        # Import the FABlib Library
        fablib = FablibManager()

        fablib.show_config()

        # Create the Experiment Slice
        #
        # The following creates two nodes with basic NICs connected to an isolated local Ethernet.
        #
        # Two nodes are created and one NIC component is added to each node.
        # This example uses components of model `NIC_Basic` which are SR-IOV Virtual Function on a 100 Gpbs
        # Mellanox ConnectX-6 PCI device. The VF is accessed by the node via PCI passthrough.
        # Other NIC models are listed below. When using dedicated PCI devices the whole physical device is
        # allocated to one node and the device is accessed by the node using PCI passthrough.
        # Calling the `get_interfaces()` method on a component will return a list of interfaces.
        # Many dedicated NIC components may have more than one port.  Either port can be connected to the network.
        #
        # Automatic configuration requires specify a subnet for the network and setting the
        # interface's mode to `auto` using the `iface1.set_mode('auto')` function before submitting the request.
        # With automatic configuration, FABlib will allocate an IP from the network's subnet and configure the
        # device during the post boot configuration stage.  Optionally, you can add routes to the node before
        # submitting the request.
        #
        #
        # NIC component models options:
        # - NIC_Basic: 100 Gbps Mellanox ConnectX-6 SR-IOV VF (1 Port)
        # - NIC_ConnectX_5: 25 Gbps Dedicated Mellanox ConnectX-5 PCI Device (2 Ports)
        # - NIC_ConnectX_6: 100 Gbps Dedicated Mellanox ConnectX-6 PCI Device (2 Ports)

        slice_name = "MySlice"
        site = fablib.get_random_site()
        site = "GATECH"
        print(f"Site: {site}")

        node1_name = "Node1"
        node2_name = "Node2"

        network_name = "net1"

        # Create Slice
        slice = fablib.new_slice(name=slice_name)

        try:
            print(f"Building topology for the slice: {slice_name}")
            # Network
            net1 = slice.add_l2network(
                name=network_name, subnet=IPv4Network("192.168.1.0/24")
            )

            # Node1
            node1 = slice.add_node(
                name=node1_name, site=site, image="default_ubuntu_22"
            )
            iface1 = node1.add_component(
                model="NIC_Basic", name="nic1"
            ).get_interfaces()[0]
            iface1.set_mode("auto")
            net1.add_interface(iface1)

            # Node2
            node2 = slice.add_node(
                name=node2_name, site=site, image="default_ubuntu_22"
            )
            iface2 = node2.add_component(
                model="NIC_Basic", name="nic1"
            ).get_interfaces()[0]
            iface2.set_mode("auto")
            net1.add_interface(iface2)

            print(f"Submitting slice {slice_name}")
            # Submit Slice Request
            slice.submit()

            # Run the Experiment
            #
            # With automatic configuration the slice is ready for experimentation after it becomes active.
            # Note that automatic configuration works well when saving slices to a file and reinstantiating the slice.
            # Configuration tasks can be stored in the saved slice, reducing the complexity of notebooks and
            # other runtime steps.
            #
            # We will find the ping round trip time for this pair of sites.  Your experiment should be more interesting!
            #
            print(f"Verifying connectivity between the nodes connected via L2Bridge")
            slice = fablib.get_slice(slice_name)
            node1 = slice.get_node(name=node1_name)
            node2 = slice.get_node(name=node2_name)
            node2_addr = node2.get_interface(network_name=network_name).get_ip_addr()

            stdout, stderr = node1.execute(f"ping -c 5 {node2_addr}")
            self.assertTrue(
                "5 packets transmitted, 5 received, 0% packet loss" in stdout
            )
            self.assertEqual(stderr, "")

            # Reboot Nodes
            slice = fablib.get_slice(slice_name)

            print(f"Rebooting Node {node1_name}")
            node1 = slice.get_node(name=node1_name)
            node1.execute("sudo reboot")

            print(f"Rebooting Node {node2_name}")
            node2 = slice.get_node(name=node2_name)
            node2.execute("sudo reboot")

            # Wait for the Nodes to come back up and re-configure them
            print(f"Waiting for Nodes to come up")
            slice.wait_ssh()
            print(f"Reconfiguring {node1_name}")
            node1.config()
            print(f"Reconfiguring {node2_name}")
            node2.config()

            # Verify that the traffic can still be passed between the VMs
            print(f"Verifying connectivity between the nodes connected via L2Bridge")
            slice = fablib.get_slice(slice_name)

            node1 = slice.get_node(name=node1_name)
            node2 = slice.get_node(name=node2_name)

            node2_addr = node2.get_interface(network_name=network_name).get_ip_addr()

            stdout, stderr = node1.execute(f"ping -c 5 {node2_addr}")
            self.assertTrue(
                "5 packets transmitted, 5 received, 0% packet loss" in stdout
            )
            self.assertEqual(stderr, "")

        finally:
            # Delete the slice
            slice.delete()


if __name__ == "__main__":
    unittest.main()
