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

import os
import traceback
import re

import functools
import time

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

#from fabrictestbed_extensions.fabricx.fabricx import FabricX
#from fabrictestbed_extensions.fabricx.slicex import SliceX
#from fabrictestbed_extensions.fabricx.nodex import NodeX
#from .slicex import SliceX
#from .nodex import NodeX
#from .fabricx import FabricX


from ipaddress import ip_address, IPv4Address


#from fim.user import node


#from .abc_fablib import AbcFabLIB

#class Interface(AbcFabLIB):
class Interface():
    """
    Interface class. Contains information for FABRIC interfaces.
    """

    def __init__(self, component=None, fim_interface=None):
        """
        Constructor for the Interface class. Sets the component and fim_interface with
        the keyword variables.

        :param component: The component to initialize this interface with.
        :type component: ComponentType
        :param fim_interface: The FIM Interface to initialize this interface with.
        :type fim_interface: Interface
        """
        super().__init__()
        self.fim_interface  = fim_interface
        self.component = component

    def get_os_interface(self):
        """
        Gets the operating system interface. Builds the interface name with the OS interface name
        and the VLAN.

        :return: the operating system interface.
        :rtype: Interface
        """
        try:
            os_iface = self.get_physical_os_interface()['ifname']
            vlan = self.get_vlan()

            if vlan != None:
                os_iface = f"{os_iface}.{vlan}"
        except:
            os_iface = None


        return os_iface

    def get_mac(self):
        """
        Gets the MAC address of the operating system interface.

        :return: the MAC address of the operating system interface.
        :rtype: str
        """
        try:
            os_iface = self.get_physical_os_interface()
            mac = os_iface['mac']
        except:
            mac = None

        return mac


    def get_physical_os_interface(self):
        """
        Gets the physical operating system interface from the slice's interface name.

        :return: the physical operating system interface
        :rtype: Interface
        """
        if self.get_network() == None:
            return None

        network_name = self.get_network().get_name()
        node_name = self.get_node().get_name()

        #print(f"get_physical_os_interface: network_name = {network_name}")
        #print(f"get_physical_os_interface: node_name = {node_name}")


        return self.get_slice().get_interface_map()[network_name][node_name]

    def config_vlan_iface(self):
        """
        Configures the VLAN interface.
        """
        if self.get_vlan() != None:
            self.get_node().add_vlan_os_interface(os_iface=self.get_physical_os_interface()['ifname'],
                                                  vlan=self.get_vlan())


    def set_ip(self, ip=None, cidr=None):
        """
        Sets the IP address.

        :param ip: The IP address.
        :type ip: str
        :param cidr: The CIDR address.
        :type cidr: str
        """
        self.get_node().set_ip_os_interface(os_iface=self.get_physical_os_interface()['ifname'],
                                            vlan=self.get_vlan(),
                                            ip=ip, cidr=cidr)

    def set_vlan(self, vlan=None):
        """
        Sets the VLAN.

        :param vlan: The VLAN to set.
        :type vlan: VLAN
        """
        if_labels = self.get_fim_interface().get_property(pname="labels")
        if_labels.vlan = str(vlan)
        self.get_fim_interface().set_properties(labels=if_labels)

    def get_fim_interface(self):
        """
        Getter method for the FIM interface state.

        :return: the FIM interface
        :rtype: Interface
        """
        return self.fim_interface

    def get_bandwidth(self):
        """
        Getter method for the bandwidth capacity.

        :return: the bandwidth capacity of the interface.
        :rtype: int
        """
        return self.get_fim_interface().capacities.bw

    def get_vlan(self):
        """
        Getter method for the VLAN.

        :return: the VLAN on this interface.
        :rtype: VLAN
        """
        try:
            vlan = self.get_fim_interface().get_property(pname="labels").vlan
        except:
            vlan = None
        return vlan

    def get_name(self):
        """
        Getter method for the name of the interface.

        :return: the name of the interface
        :rtype: str
        """
        return self.get_fim_interface().name

    def get_component(self):
        """
        Getter method for the component attached to this interface.

        :return: the component attached to this interface
        :rtype: Component
        """
        return self.component

    def get_model(self):
        """
        Getter method for the model of this interface's component.

        :return: the model of the interface component
        :rtype: ComponentModelType
        """
        return self.get_component().get_model()

    def get_site(self):
        """
        Getter method for the site of this interface's component.

        :return: the site of the interface component
        :rtype: str
        """
        return self.get_component().get_site()

    def get_slice(self):
        """
        Getter method for the slice this interface is on.

        :return: the interface's slice
        :rtype: Slice
        """
        return self.get_node().get_slice()

    def get_node(self):
        """
        Getter method for the node this interface's component is on.

        :return: the node of the interface component
        :rtype: Node
        """
        return self.get_component().get_node()

    def get_network(self):
        """
        Gets the network this interface is on, or None.

        :return: the network this interface is on
        :rtype: Network
        """
        for net in self.get_slice().get_l2networks():
            if net.has_interface(self):
                return net

        return None
        #raise Exception(f"Network not found: interface {self.get_name()}")
