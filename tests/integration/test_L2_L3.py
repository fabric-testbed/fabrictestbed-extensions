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

from fabrictestbed_extensions.fablib.fablib import fablib, FablibManager


class L2L3Tests(unittest.TestCase):
    def setUp(self):
        # Create a slice
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        slice_name = f"integration test @ {time_stamp} on {host}"
        self._slice = fablib.new_slice(name=slice_name)

    def tearDown(self):
        self._slice.delete()

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
        self._add_l2(site1, site2)
        print(f"Submitting '{self._slice.get_name()}' [#1]")
        self._slice.submit()

        # Add measurement nodes to the slice.
        print("Adding L3 node")
        # MFLib.addMeasNode(self._slice)
        self._add_l3(site1, site2, site3)
        print(f"Submitting '{self._slice.get_name()}' [#2]")
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
        print("Adding nodes, no modify")
        [site1, site2, site3] = fablib.get_random_sites(count=3)
        print(f"Sites: {site1}, {site2}, {site3}")

        print(f"Adding nodes and L2 network to slice at {site1} and {site2}")
        self._add_l2(site1, site2)

        print(f"Adding a node at {site3} and L3 network to slice at {site1}, {site2}")
        self._add_l3(site1, site2, site3)

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

        # for iface in ifaces:
        #     print(f"{iface}")

        print("------------------------------------------------------------")

        for iface in ifaces:
            print(f"iface: {iface.get_name()}, ip: {iface.get_ip_addr()}")

        print("------------------------------------------------------------")

    def _add_l2(self, site1, site2):
        """
        Make a slice with an L2 network and two nodes.
        """
        # Add an L2 network.
        network_name = "net1"
        l2_net = self._slice.add_l2network(
            name=network_name, subnet=IPv4Network("192.168.1.0/24")
        )

        # Add some nodes with L2 networking.
        self.__add_node_l2(site1, l2_net)
        self.__add_node_l2(site2, l2_net)

    def __add_node_l2(self, site, net):
        # Set up a node with a NIC.
        node_name = f"node-{site}"
        print(f"Adding node {node_name}")
        node = self._slice.add_node(name=node_name, site=site)

        ifname = f"nic-L2-{site}"
        print(f"Adding {ifname} to {node_name}")

        iface = node.add_component(model="NIC_Basic", name=ifname).get_interfaces()[0]
        iface.set_mode("auto")

        net.add_interface(iface)

    def _add_l3(self, site1, site2, site3):
        """
        Add an L3 network to the slice.
        """
        # Add L3 networking to existing nodes.
        self.__add_l3_to_node(site1)
        self.__add_l3_to_node(site2)

        # Add another L3 network tied and a new node.
        self.__add_l3_node(site3)

    def __add_l3_to_node(self, site):
        l3_net_name = f"l3_net_{site}"
        print(f"Adding L3 network {l3_net_name}")
        l3_net = self._slice.add_l3network(name=l3_net_name, type="IPv4")

        node_name = f"node-{site}"
        node = self._slice.get_node(name=node_name)
        # node = self._slice.add_node(name=node_name, site=site)

        iface_name = f"nic-L3-{site}"
        print(f"Adding {iface_name} to {node.get_name()}")

        iface = node.add_component(
            model="NIC_Basic",
            name=iface_name,
        ).get_interfaces()[0]
        iface.set_mode("auto")

        l3_net.add_interface(iface)

        # node.add_route(
        #     subnet=FablibManager.FABNETV4_SUBNET, next_hop=l3_net.get_gateway()
        # )

        # # print(f"Adding fabnet to {node.get_name()}")
        # # node.add_fabnet()

    def __add_l3_node(self, site):
        l3_net_name = f"l3_net_{site}"
        print(f"Adding L3 network {l3_net_name}")
        l3_net = self._slice.add_l3network(name=l3_net_name, type="IPv4")

        node_name = f"l3_node_{site}"
        print(f"Adding node {node_name}")
        node = self._slice.add_node(name=node_name)

        ifname = f"nic-L3-{site}"
        print(f"Adding {ifname} to {node_name}")

        iface = node.add_component(model="NIC_Basic", name=ifname).get_interfaces()[0]
        iface.set_mode("auto")

        l3_net.add_interface(iface)

        # node.add_route(
        #     subnet=FablibManager.FABNETV4_SUBNET, next_hop=l3_net.get_gateway()
        # )

        # # print(f"Adding fabnet to {node.get_name()}")
        # # node.add_fabnet()
