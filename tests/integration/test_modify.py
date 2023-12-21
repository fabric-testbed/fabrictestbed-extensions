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

import logging
import socket
import time
import unittest
from ipaddress import IPv4Network

from fabrictestbed_extensions.fablib.fablib import fablib


class ModifyTests(unittest.TestCase):
    # Parts of this is extracted from the notebook
    # create_l2network_wide_area_auto.ipynb, while investigating
    # https://github.com/fabric-testbed/fabrictestbed-extensions/issues/261

    def setUp(self):
        # Create a slice
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        slice_name = f"integration test @ {time_stamp} on {host}"
        self._slice = fablib.new_slice(name=slice_name)

    def tearDown(self):
        self._slice.delete()

    def test_modify_add_l2_l3_nodes(self):
        # Add nodes with L2 network, submit, add a third node with L3
        # network, add L3 network to the first two nodes, submit again.

        [site1, site2, site3] = fablib.get_random_sites(count=3)
        print(f"Sites: {site1}, {site2}, {site3}")

        print(f"Adding nodes to slice at {site1} and {site2}")
        self._add_l2(site1, site2)
        print(f"Submitting '{self._slice.get_name()}'")
        self._slice.submit()

        # Add a "marker" log line for ease of searching/spotting.
        logging.info("@@@@@@@@@@@@@@@ BEGIN MODIFY @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

        print(f"Adding a third node at {site3}")
        self._add_l3(site1, site2, site3)
        print(f"Re-submitting '{self._slice.get_name()}'")
        self._slice.submit()

        logging.info("############### END MODIFY #################################")

        self._check_interfaces()

    def test_no_modify_l2_l3_nodes(self):
        # Add nodes with L2 network, add a third node, and L3 network,
        # then submit.

        print("Adding nodes, no modify")
        [site1, site2, site3] = fablib.get_random_sites(count=3)
        print(f"Sites: {site1}, {site2}, {site3}")

        print(f"Adding nodes and L2 network to slice at {site1} and {site2}")
        self._add_l2(site1, site2)

        print(f"Adding a node at {site3} and L3 network to slice at {site1}, {site2}")
        self._add_l3(site1, site2, site3)

        print("Submitting slice")
        self._slice.submit()

        self._check_interfaces()

    def _add_l2(self, site1, site2):
        """
        Make a slice with an L2 network and two nodes.
        """
        # Add an L2 network.
        network_name = "net-L2"
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

        # Add another L3 network tied to a new node.
        self.__add_l3_node(site3)

    def __add_l3_to_node(self, site):
        node_name = f"node-{site}"
        node = self._slice.get_node(name=node_name)
        self.__add_l3_iface(site, node)

    def __add_l3_node(self, site):
        node_name = f"node-L3-{site}"
        print(f"Adding node {node_name}")
        node = self._slice.add_node(name=node_name, site=site)

        self.__add_l3_iface(site, node)

    def __add_l3_iface(self, site, node):
        if_name = f"nic-L3-{site}"
        print(f"Adding {if_name} to {node.get_name()}")

        iface = node.add_component(model="NIC_Basic", name=if_name).get_interfaces()[0]
        iface.set_mode("auto")

        l3_net_name = f"net-L3-{site}"
        print(f"Adding L3 network {l3_net_name}, with {if_name}")
        l3_net = self._slice.add_l3network(name=l3_net_name, type="IPv4")

        l3_net.add_interface(iface)

    def _check_interfaces(self):
        print("============ interfaces ====================================")

        ifaces = self._slice.get_interfaces()
        for iface in ifaces:
            print(f"{iface}")

        print("============ networks ======================================")

        networks = self._slice.get_networks()
        for network in networks:
            print(f"{network}")

        print("============================================================")

        errors = []

        for iface in ifaces:
            if iface.get_ip_addr() is None:
                errors.append(f"iface {iface.get_name()} has no IP address")

        self.assertEqual(errors, [])
