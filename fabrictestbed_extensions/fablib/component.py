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

# from .. import images


#class Component(AbcFabLIB):
class Component():

    """
    Class representing hardware components.
    """

    component_model_map = { 'NIC_Basic': ComponentModelType.SharedNIC_ConnectX_6,
                            'NIC_ConnectX_6': ComponentModelType.SmartNIC_ConnectX_6,
                            'NIC_ConnectX_5': ComponentModelType.SmartNIC_ConnectX_5,
                            'NVME_P4510': ComponentModelType.NVME_P4510,
                            'GPU_TeslaT4': ComponentModelType.GPU_Tesla_T4,
                            'GPU_RTX6000': ComponentModelType.GPU_RTX6000
                            }


    @staticmethod
    def calculate_name(node=None, name=None):
        """
        Static hack that makes it possible to find interfaces. Takes the node's full name and subtracts out the inputted name.

        :param node: Node to calculate the name of.
        :type node: Node
        :param name: Name to subtract from Node's name.
        :type name: str
        :return: the calculated name.
        :rtype: str
        """
        #Hack to make it possile to find interfaces
        return f"{node.get_name()}-{name}"

    @staticmethod
    def new_component(node=None, model=None, name=None):
        """
        Static method that adds a component of a particular model to an inputted node.

        :param node: Node to calculate name of.
        :type node: Node
        :param model: Model key of component model desired.
        :type model: str
        :param name: Name of the component.
        :type name: str
        :return: the new Component.
        :rtype: Component
        """
        #Hack to make it possile to find interfaces
        name = Component.calculate_name(node=node, name=name)

        return Component(node = node, fim_component = node.fim_node.add_component(model_type=Component.component_model_map[model], name=name))
        #return Component(node = node, model=model, name=name)

    def __init__(self, node=None, fim_component=None):
        """
        Constructor. Sets up class state based on input values (default None).

        :param node: A Node instance to pass to this Component.
        :type node: Node
        :param node: A FIM Compnent instance to pass to this Component.
        :type node: Component
        """
        super().__init__()
        self.fim_component = fim_component
        self.node = node

    def get_interfaces(self):
        """
        Gets the interfaces attached to the Component instance called on.

        :return: a list of interfaces on the Component instance.
        :rtype: list<interface>
        """
        from fabrictestbed_extensions.fablib.interface import Interface

        ifaces = []
        for fim_interface in self.get_fim_component().interface_list:
            ifaces.append(Interface(component=self, fim_interface=fim_interface))

        return ifaces

    def get_fim_component(self):
        """
        Getter method for `fim_component`.

        :return: the `fim_component` field.
        :rtype: Component
        """
        return self.fim_component

    def get_slice(self):
        """
        Getter method for `get_slice`.

        :return: the `get_slice` field.
        :rtype: Slice
        """
        return self.node.get_slice()

    def get_node(self):
        """
        Getter method for `node`.

        :return: the `node` field.
        :rtype: Node
        """
        return self.node

    def get_site(self):
        """
        Wrapped getter method for `node.get_site()`.

        :return: the site of `node`
        :rtype: Site
        """
        return self.node.get_site()

    def get_name(self):
        """
        Wrapped getter method for the name of the FIM component.

        :return: the name of the FIM component.
        :rtype: str
        """
        return self.get_fim_component().name

    def get_details(self):
        """
        Wrapped getter method for the details of the FIM component.

        :return: the details of the FIM component.
        :rtype: str
        """
        return self.get_fim_component().details

    def get_disk(self):
        """
        Wrapped getter method for the disk space of the FIM component.

        :return: the amount of disk space on the FIM component.
        :rtype: int
        """
        return self.get_fim_component().get_property(pname='capacity_allocations').disk

    def get_unit(self):
        """
        Wrapped getter method for the unit of the FIM component.

        :return: the unit on the FIM component.
        :rtype: str
        """
        return self.get_fim_component().get_property(pname='capacity_allocations').unit

    def get_pci_addr(self):
        """
        Wrapped getter method for the PCI Address of the FIM component.

        :return: the PCI Address on the FIM component.
        :rtype: str
        """
        return self.get_fim_component().get_property(pname='label_allocations').bdf

    def get_model(self):
        """
        Get the model of the component.

        :return: the model of the component.
        :rtype: Model
        """
        #TODO: get new model names (NIC_Basic, etc.)
        return self.get_fim_model()

    def get_fim_model(self):
        """
        Get the model of the FIM component.

        :return: the model of the FIM component.
        :rtype: Model
        """
        return self.get_fim_component().model

    def get_type(self):
        """
        Get the type of the component.

        :return: the type of the component.
        :rtype: Model
        """
        return self.get_fim_component().type

    def configure_nvme(self, mount_point='/mnt/nvme_mount', verbose=False):
        """
        Configure the NVME of this component.

        :param mount_point: The system location of this component's mount point.
        :type mount_point: str
        :param verbose: An indicator for whether or not to provide verbose output.
        :type verbose: boolean
        """
        output = []
        try:
            output.append(self.node.execute('sudo fdisk -l /dev/nvme*'))
            output.append(self.node.execute('sudo parted -s /dev/nvme0n1 mklabel gpt'))
            output.append(self.node.execute('sudo parted -s /dev/nvme0n1 print'))
            output.append(self.node.execute('sudo parted -s /dev/nvme0n1 print unit MB print free'))
            output.append(self.node.execute('sudo parted -s --align optimal /dev/nvme0n1 mkpart primary ext4 0% 960197MB'))
            output.append(self.node.execute('lsblk /dev/nvme0n1'))
            output.append(self.node.execute('sudo mkfs.ext4 /dev/nvme0n1p1'))
            output.append(self.node.execute(f'sudo mkdir {mount_point} && sudo mount /dev/nvme0n1p1 {mount_point}'))
            output.append(self.node.execute(f'df -h {mount_point}'))
        except Exception as e:
            print(f"config_nvme Fail: {self.get_name()}")
            traceback.print_exc()
            raise Exception(str(output))

        return output


class Disk(Component):

    def __init__(self, component):
        """
        Constructor
        """
        super().__init__(component)

class NIC(Component):
    def __init__(self, component):
        """
        Constructor
        """
        super().__init__(component)

class GPU(Component):
    def __init__(self, component):
        """
        Constructor
        """
        super().__init__(component)
