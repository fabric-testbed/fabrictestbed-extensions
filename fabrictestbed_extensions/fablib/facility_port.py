#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
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
#
# Author: Paul Ruth (pruth@renci.org)

from tabulate import tabulate

from fabrictestbed.slice_editor import Labels, Capacities

from fabrictestbed_extensions.fablib.slice import Slice


class FacilityPort:
    fim_interface = None
    slice = None

    def __init__(self, slice: Slice, fim_interface):
        """
        Constructor. Sets the fablib slice and FIM node based on arguments.
        :param slice: the fablib slice to have this node on
        :type slice: Slice
        :param node: the FIM node that this Node represents
        :type node: Node
        """
        super().__init__()
        self.fim_interface = fim_interface
        self.slice = slice

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the node.
        Intended for printing node information.
        :return: Tabulated string of node information
        :rtype: String
        """
        table = [ ["name", self.get_name()], ]

        return tabulate(table) #, headers=["Property", "Value"])

    def get_fim_interface(self):
        return self.fim_interface

    def get_model(self):
        return "Facility_Port"

    def get_name(self):
        """
        Gets the name of the FABRIC node.
        :return: the name of the node
        :rtype: String
        """
        return self.get_fim_interface().name

    def get_site(self):
        return self.fim_interface.site

    @staticmethod
    def new_facility_port(slice=None, name=None, site=None, vlan=None, bandwidth=10):

        fim_facility_port = slice.get_fim_topology().add_facility(name=name, site=site,
                                                                 capacities=Capacities(bw=bandwidth),
                                                                 labels=Labels(vlan=vlan))
        return FacilityPort(slice, fim_facility_port)

    @staticmethod
    def get_facility_port(slice=None, facility_port=None):
        """
        Not intended for API call.
        Returns a new fablib node using existing FABRIC resources.
        :param slice: the fablib slice storing the existing node
        :type slice: Slice
        :param node: the FIM node stored in this fablib node
        :type node: Node
        :return: a new fablib node storing resources
        :rtype: Node
        """
        return FacilityPort(slice, facility_port)

    def get_slice(self):
        """
        Gets the fablib slice associated with this node.
        :return: the fablib slice on this node
        :rtype: Slice
        """
        return self.slice

    def get_name(self):

        try:
            return self.get_fim_node().name
        except:
            return None


    def get_interfaces(self):
        """
        Gets a particular interface associated with a FABRIC node.
        Accepts either the interface name or a network_name. If a network name
        is used this method will return the interface on the node that is
        connected to the network specified.
        If a name and network_name are both used, the interface name will
        take precedence.
        :param name: interface name to search for
        :type name: str
        :param network_name: network name to search for
        :type name: str
        :raise Exception: if interface is not found
        :return: an interface on the node
        :rtype: Interface
        """

        from fabrictestbed_extensions.fablib.interface import Interface

        ifaces = []
        for fim_interface in self.get_fim_interface().interface_list:
            ifaces.append(Interface(component=self, fim_interface=fim_interface))

        return ifaces




