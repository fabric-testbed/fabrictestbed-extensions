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
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabrictestbed_extensions.fablib.node import Node
    from fabrictestbed_extensions.fablib.interface import Interface

from tabulate import tabulate
from typing import List

from fabrictestbed.slice_editor import ComponentModelType, Labels, Flags
from fabrictestbed.slice_editor import Component as FimComponent


class Component:
    component_model_map = { 'NIC_Basic': ComponentModelType.SharedNIC_ConnectX_6,
                            'NIC_ConnectX_6': ComponentModelType.SmartNIC_ConnectX_6,
                            'NIC_ConnectX_5': ComponentModelType.SmartNIC_ConnectX_5,
                            'NVME_P4510': ComponentModelType.NVME_P4510,
                            'GPU_TeslaT4': ComponentModelType.GPU_Tesla_T4,
                            'GPU_RTX6000': ComponentModelType.GPU_RTX6000
                            }

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the component.

        Intended for printing component information.

        :return: Tabulated string of component information
        :rtype: String
        """
        table = [   [ "Name", self.get_name() ],
                    [ "Details", self.get_details() ],
                    [ "Disk (G)", self.get_disk() ],
                    [ "Units", self.get_unit() ],
                    [ "PCI Address", self.get_pci_addr() ],
                    [ "Model", self.get_model() ],
                    [ "Type", self.get_type() ],
                    ]

        return tabulate(table)

    def list_interfaces(self) -> List[str]:
        """
        Creates a tabulated string describing all components in the slice.

        Intended for printing a list of all components.

        :return: Tabulated srting of all components information
        :rtype: String
        """
        table = []
        for iface in self.get_interfaces():
            network_name = ""
            if iface.get_network():
                network_name = iface.get_network().get_name()

            table.append( [     iface.get_name(),
                                network_name,
                                iface.get_bandwidth(),
                                iface.get_vlan(),
                                iface.get_mac(),
                                iface.get_physical_os_interface_name(),
                                iface.get_os_interface(),
                                ] )

        return tabulate(table, headers=["Name", "Network", "Bandwidth", "VLAN", "MAC", "Physical OS Interface", "OS Interface" ])

    @staticmethod
    def calculate_name(node: Node = None, name: str = None) -> str:
        """
        Not intended for API use
        """
        # Hack to make it possile to find interfaces
        return f"{node.get_name()}-{name}"

    @staticmethod
    def new_component(node: Node = None, model: str = None, name: str = None):
        """
        Not intended for API use

        Creates a new FIM component on the fablib node inputted.

        :param node: the fablib node to build the component on
        :type node: Node
        :param model: the name of the component type to build
        :type model: str
        :param name: the name of the new component
        :type name: str
        :return: the new fablib compoent
        :rtype: Component
        """
        # Hack to make it possile to find interfaces
        name = Component.calculate_name(node=node, name=name)

        return Component(node=node, fim_component=node.fim_node.add_component(
            model_type=Component.component_model_map[model], name=name))

    @staticmethod
    def new_storage(node: Node, name: str, auto_mount: bool = False):
        """
        Not intended for API use

        Creates a new FIM component on the fablib node inputted.

        :param node: the fablib node to build the component on
        :param name: the name of the new component
        :param auto_mount: True - mount the storage; False - do not mount
        :return: the new fablib compoent
        :rtype: Component
        """
        # Hack to make it possile to find interfaces

        fim_component = node.fim_node.add_component(name=name, labels=Labels(local_name=name),
                                                    flags=Flags(auto_mount=auto_mount))
        return Component(node=node, fim_component=fim_component)

    def __init__(self, node: Node = None, fim_component: FimComponent = None):
        """
        Not intended for API use

        Constructor. Sets the FIM component and fablib node to the inputted values.

        :param node: the fablib node to build the component on
        :type node: Node
        :param fim_component: the FIM component this object represents
        :type fim_component: FIMComponent
        """
        super().__init__()
        self.fim_component = fim_component
        self.node = node

    def get_interfaces(self) -> List[Interface]:
        """
        Gets the interfaces attached to this fablib component's FABRIC component.

        :return: a list of the interfaces on this component.
        :rtype: List[Interface]
        """

        from fabrictestbed_extensions.fablib.interface import Interface
        ifaces = []
        for fim_interface in self.get_fim_component().interface_list:
            ifaces.append(Interface(component=self, fim_interface=fim_interface))

        return ifaces

    def get_fim_component(self) -> FimComponent:
        """
        Not intended for API use

        Gets the FABRIC component this fablib component represents.

        :return: the FABRIC component on this component
        :rtype: FIMComponent
        """
        return self.fim_component

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice associated with this component's node.

        :return: the slice this component is on
        :rtype: Slice
        """
        return self.node.get_slice()

    def get_node(self) -> Node:
        """
        Gets the fablib node this component is associated with.

        :return: the node this component is on
        :rtype: Node
        """
        return self.node

    def get_site(self) -> str:
        """
        Gets the name of the site this component's node is on.

        :return: the site name this node is on
        :rtype: String
        """
        return self.node.get_site()

    def get_name(self) -> str:
        """
        Gets the name of this component from the FABRIC component.

        :return: the name of this component
        :rtype: str
        """
        return self.get_fim_component().name

    def get_details(self) -> str:
        """
        Not intended for API use
        """
        return self.get_fim_component().details

    def get_disk(self) -> int:
        """
        Gets the amount of disk space on this component.

        :return: this component's disk space
        :rtype: int
        """
        return self.get_fim_component().get_property(pname='capacity_allocations').disk

    def get_unit(self) -> int:
        """
        Get unit count for this component.

        :return: unit
        :rtype: int
        """
        return self.get_fim_component().get_property(pname='capacity_allocations').unit

    def get_pci_addr(self) -> str:
        """
        Get the PIC device ID for this component.

        :return: PCI device ID
        :rtype: String
        """
        return self.get_fim_component().get_property(pname='label_allocations').bdf

    def get_model(self) -> str:
        """
        Get FABlib model name for this component.

        :return: FABlib model name
        :rtype: String
        """
        #TODO: This a hack that need a real fix
        if str(self.get_type()) == "SmartNIC" and str(self.get_fim_model()) == "ConnectX-6":
            return 'NIC_ConnectX_6'
        elif str(self.get_type()) == "SmartNIC" and str(self.get_fim_model()) == "ConnectX-5":
            return 'NIC_ConnectX_5'
        elif str(self.get_type()) == "NVME"  and str(self.get_fim_model()) == "P4510":
            return 'NVME_P4510'
        elif str(self.get_type())== "GPU"  and str(self.get_fim_model()) == "Tesla T4":
            return 'GPU_TeslaT4'
        elif str(self.get_type()) == "GPU"  and str(self.get_fim_model()) == "RTX6000":
            return 'GPU_RTX6000'
        elif str(self.get_type()) == "SharedNIC"  and str(self.get_fim_model()) == "ConnectX-6":
            return 'NIC_Basic'
        else:
            return None

    def get_reservation_id(self) -> str or None:
        """
        Get reservation ID for this component.

        :return:  reservation ID
        :rtype: String
        """
        try:
            #This does not work
            #print(f"{self.get_fim_component()}")
            return self.get_fim_component().get_property(pname='reservation_info').reservation_id
        except:
            return None

    def get_reservation_state(self) -> str or None:
        """
        Get reservation state for this component.

        :return:  reservation state
        :rtype: String
        """
        try:
            return self.get_fim_component().get_property(pname='reservation_info').reservation_state
        except:
            return None

    def get_error_message(self) -> str:
        """
        Get error message for this component.

        :return:  reservation state
        :rtype: String
        """
        try:
            return self.get_fim_component().get_property(pname='reservation_info').error_message
        except:
            return ""

    def get_fim_model(self) -> str:
        """
        Not for API use
        """
        return self.get_fim_component().model

    def get_type(self) -> str:
        """
        Not for API use

        Gets the type of this component.

        :return: the type of component
        :rtype: str
        """
        return self.get_fim_component().type

    def configure_nvme(self, mount_point='/mnt/nvme_mount'):
        """
        Configure the NVMe drive.

        Note this works but may be reorganzied. 

        :param mount_point: The mount point in the filesystem. Default = /mnt/nvme_mount
        :type mount_point: String
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
            #traceback.print_exc()
            raise Exception(str(output))

        return output
