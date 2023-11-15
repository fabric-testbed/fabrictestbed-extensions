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

from fabrictestbed_extensions.fablib.fablib import FablibManager, fablib


class L2MFLibTests(unittest.TestCase):
    def setUp(self):
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        self.slice_name = f"integration test @ {time_stamp} on {host}"

    # def tearDown(self):
    #     fablib.get_slice(self.slice_name).delete()

    def test_add_l2_measurement_nodes_modify(self):
        """
        Add measurement nodes to L2 network.

        Create slice, submit, add measurement node, submit again.
        """
        print("Creating slice")
        slice = self._make_slice()
        slice.submit()

        print("Adding measurement node")
        # Add measurement nodes to the slice.
        MFLib.addMeasNode(slice)

        # submit Slice Request
        slice.submit()

        nodes = slice.get_nodes()

        for node in nodes:
            self.assertIsNotNone(node.get_management_ip(),
                                 f"node {node.get_name()} has no management IP address")

        ifaces = slice.get_interfaces()

        for iface in ifaces:
            self.assertIsNotNone(iface.get_ip_addr(),
                                 f"iface {iface.get_name()} has no IP address")
        

    def test_add_l2_measurement_nodes_no_modify(self):
        """
        Add measurement nodes to L2 network.

        Create slice, add measurement node, then submit.
        """
        print("Adding measurement node, no modify")
        slice = self._make_slice()
        MFLib.addMeasNode(slice)
        slice.submit()

        nodes = slice.get_nodes()

        for node in nodes:
            self.assertIsNotNone(node.get_management_ip(),
                                 f"node {node.get_name()} has no management IP address")

        ifaces = slice.get_interfaces()

        for iface in ifaces:
            self.assertIsNotNone(iface.get_ip_addr(),
                                 f"iface {iface.get_name()} has no IP address")

    def _make_slice(self):
        fablib = FablibManager()
        c = fablib.get_config()

        self.assertIsNotNone(c)

        [site1, site2] = fablib.get_random_sites(count=2)
        print(f"Sites: {site1}, {site2}")

        self.assertIsNotNone(site1)
        self.assertIsNotNone(site2)

        node1_name = "node1"
        node2_name = "node2"
        network_name = "net1"

        # Create a slice
        slice = fablib.new_slice(name=self.slice_name)

        # Add an L2 network.
        net1 = slice.add_l2network(
            name=network_name, subnet=IPv4Network("192.168.1.0/24")
        )

        # Set up node1.
        node1 = slice.add_node(name=node1_name, site=site1)
        iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
        iface1.set_mode("auto")
        net1.add_interface(iface1)

        # Set up node2.
        node2 = slice.add_node(name=node2_name, site=site2)
        iface2 = node2.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]
        iface2.set_mode("auto")
        net1.add_interface(iface2)

        return slice
