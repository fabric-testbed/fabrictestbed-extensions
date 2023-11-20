#!/usr/bin/env python3
#
# MIT License
#
# Copyright (c) 2023 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Extracted from create_l2network_wide_area_auto.ipynb

import socket
import time
import unittest
from ipaddress import IPv4Network

from mflib.mflib import MFLib

from fabrictestbed_extensions.fablib.fablib import fablib


class L2L3Tests(unittest.TestCase):
    def setUp(self):
        # Create a slice
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        slice_name = f"integration test @ {time_stamp} on {host}"
        self._slice = fablib.new_slice(name=slice_name)

    # def tearDown(self):
    #     self._slice.delete()

    def test_add_l2_l3_nodes_modify(self):
        """
        Add measurement nodes to L2 network.

        Create slice, submit, add measurement node, submit again.
        """
        [site1, site2, site3] = fablib.get_random_sites(count=3)
        # site1, site2 = "ATLA", "TACC"
        print(f"Sites: {site1}, {site2}, {site3}")

        self.assertIsNotNone(site1)
        self.assertIsNotNone(site2)
        self.assertIsNotNone(site3)
        
        print(f"Adding nodes to slice at {site1} and {site2}")
        self._make_l2_slice(site1, site2)
        self._slice.submit()

        # Add measurement nodes to the slice.
        print("Adding measurement node")        
        MFLib.addMeasNode(self._slice)
        self._slice.submit()

        # nodes = slice.get_nodes()

        # for node in nodes:
        #     self.assertIsNotNone(node.get_management_ip(),
        #                          f"node {node.get_name()} has no management IP address")

        ifaces = self._slice.get_interfaces()

        # for iface in ifaces:
        #     self.assertIsNotNone(iface.get_ip_addr(),
        #                          f"iface {iface.get_name()} has no IP address")

        print("Interfaces:")
        print("------------------------------------------------------------")

        for iface in ifaces:
            print(f"{iface}")

        print("------------------------------------------------------------")

        for iface in ifaces:
            print(f"iface: {iface.get_name()}, ip: {iface.get_ip_addr()}")

        print("------------------------------------------------------------")

    def test_add_l2_measurement_nodes_no_modify(self):
        """
        Add measurement nodes to L2 network.

        Create slice, add measurement node, then submit.
        """
        print("Adding measurement node, no modify")
        slice = self._make_l2_slice()
        MFLib.addMeasNode(slice)

        print("Submitting slice")

        slice.submit()

        # print("------------------------------------------------------------")

        # print("Nodes:")

        # nodes = slice.get_nodes()

        # for node in nodes:
        #     print(f"node: {node}, management ip: {node.get_management_ip()}")
        #     self.assertIsNotNone(node.get_management_ip(),
        #                          f"node {node.get_name()} has no management IP address")

        # print("------------------------------------------------------------")

        # print("Interfaces:")

        ifaces = slice.get_interfaces()

        # for iface in ifaces:
        #     self.assertIsNotNone(iface.get_ip_addr(),
        #                          f"iface {iface.get_name()} has no IP address")

        for iface in ifaces:
            print(f"{iface}")

        print("------------------------------------------------------------")

        for iface in ifaces:
            print(f"iface: {iface.get_name()}, ip: {iface.get_ip_addr()}")

        print("------------------------------------------------------------")

    def _make_l2_slice(self, site1, site2):
        """
        Make a slice with an L2 network and two nodes.
        """
        node1_name = "node1"
        node2_name = "node2"
        network_name = "net1"

        # Add an L2 network.
        net1 = self._slice.add_l2network(
            name=network_name, subnet=IPv4Network("192.168.1.0/24")
        )

        # Set up node1.
        node1 = self._slice.add_node(name=node1_name, site=site1)
        iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
        iface1.set_mode("auto")
        net1.add_interface(iface1)

        # Set up node2.
        node2 = self._slice.add_node(name=node2_name, site=site2)
        iface2 = node2.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
        iface2.set_mode("auto")
        net1.add_interface(iface2)

        # return slice

    def _add_l3_network(self):
        """
        Add an L3 network to the slice.
        """

        # Add an L3 network to each site in the slice.
        for node in slice.get_nodes():
            this_site = node.get_site()
            l3_network_name = f"l3_net_{this_site}"
            if self._slice.get_l3network(name=l3_network_name) is None:
                print(f"Adding network {l3_network_name}")
                self._slice.add_l3network(name=l3_network_name, type="IPv4")

        # Add another L3 network tied and a new node.
        l3_net = self._slice.add_l3network(name=f"l3_network", type="IPv4")

        # Hard-code third site for now.
        site3 = "EDC"
        l3_node = self._slice.add_node(f"l3-node-1-{site3}")
        iface = l3_node.node2.add_component(
            model="NIC_Basic", name="nic1"
        ).get_interfaces()[0]
        iface.set_mode("auto")
        l3_net.add_interface(l3_net)
