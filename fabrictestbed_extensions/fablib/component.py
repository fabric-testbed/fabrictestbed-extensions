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

"""
Methods to work with FABRIC components_.

.. _components: https://learn.fabric-testbed.net/knowledge-base/glossary/#component

You normally would not create :class:`Component` objects directly with
a constructor call; they are created when you invoke
:py:func:`fabrictestbed_extensions.fablib.node.Node.add_component()`,
like so::

    node.add_component(model='NVME_P4510', name="nvme1")
    node.add_component(model='NIC_Basic', name="nic1")
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Union

import jinja2

from fabrictestbed_extensions.fablib.constants import Constants

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabrictestbed_extensions.fablib.node import Node
    from fabrictestbed_extensions.fablib.interface import Interface
    from fabrictestbed_extensions.fablib.interface import Interface

import logging
from typing import List

from fabrictestbed.slice_editor import Component as FimComponent
from fabrictestbed.slice_editor import ComponentModelType, Flags, Labels, UserData
from tabulate import tabulate


class Component:
    """
    A class for working with FABRIC components.
    """

    component_model_map = {
        Constants.CMP_NIC_Basic: ComponentModelType.SharedNIC_ConnectX_6,
        Constants.CMP_NIC_BlueField2_ConnectX_6: ComponentModelType.SmartNIC_BlueField_2_ConnectX_6,
        Constants.CMP_NIC_ConnectX_6: ComponentModelType.SmartNIC_ConnectX_6,
        Constants.CMP_NIC_ConnectX_5: ComponentModelType.SmartNIC_ConnectX_5,
        Constants.CMP_NIC_P4: Constants.P4_DedicatedPort,
        Constants.CMP_NVME_P4510: ComponentModelType.NVME_P4510,
        Constants.CMP_GPU_TeslaT4: ComponentModelType.GPU_Tesla_T4,
        Constants.CMP_GPU_RTX6000: ComponentModelType.GPU_RTX6000,
        Constants.CMP_GPU_A40: ComponentModelType.GPU_A40,
        Constants.CMP_GPU_A30: ComponentModelType.GPU_A30,
        Constants.CMP_NIC_OpenStack: ComponentModelType.SharedNIC_OpenStack_vNIC,
        Constants.CMP_FPGA_Xilinx_U280: ComponentModelType.FPGA_Xilinx_U280,
        Constants.CMP_FPGA_Xilinx_SN1022: ComponentModelType.FPGA_Xilinx_SN1022,
    }

    component_configure_commands = {
        Constants.CMP_NIC_BlueField2_ConnectX_6: [
            "sudo ip addr add 192.168.100.1/24 dev tmfifo_net0",
            "sudo bfb-install --bfb /opt/bf-bundle/bf-bundle-2.9.1-40_24.11_ubuntu-22.04_prod.bfb --rshim rshim0",
        ]
    }

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the component.

        Intended for printing component information.

        :return: Tabulated string of component information
        :rtype: String
        """
        table = [
            ["Name", self.get_name()],
            ["Details", self.get_details()],
            ["Disk", self.get_disk()],
            ["Units", self.get_unit()],
            ["PCI Address", self.get_pci_addr()],
            ["Model", self.get_model()],
            ["Type", self.get_type()],
        ]

        return tabulate(table)

    def get_fablib_manager(self):
        """
        Get the Fabric library manager associated with the component.
        """
        return self.get_slice().get_fablib_manager()

    def toJson(self):
        """
        Returns the component attributes as a json string

        :return: slice attributes as json string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_name_dict():
        """
        Returns the mapping used when rendering table headers.
        """
        return {
            "name": "Name",
            "short_name": "Short Name",
            "details": "Details",
            "disk": "Disk",
            "units": "Units",
            "pci_address": "PCI Address",
            "model": "Model",
            "type": "Type",
            "dev": "Device",
            "node": "Node",
            "numa": "Numa Node",
        }

    def toDict(self, skip=[]):
        """
        Returns the component attributes as a dictionary

        :return: slice attributes as dictionary
        :rtype: dict
        """
        return {
            "name": str(self.get_name()),
            "short_name": str(self.get_short_name()),
            "details": str(self.get_details()),
            "disk": str(self.get_disk()),
            "units": str(self.get_unit()),
            "pci_address": str(self.get_pci_addr()),
            "model": str(self.get_model()),
            "type": str(self.get_type()),
            "dev": str(self.get_device_name()),
            "node": str(self.get_node().get_name()),
            "numa": str(self.get_numa_node()),
        }

    def generate_template_context(self):
        context = self.toDict()
        context["interfaces"] = []
        # for interface in self.get_interfaces():
        #    context["interfaces"].append(interface.get_name())

        #    context["interfaces"].append(interface.generate_template_context())
        return context

    def get_template_context(self):
        return self.get_slice().get_template_context(self)

    def render_template(self, input_string):
        environment = jinja2.Environment()
        # environment.json_encoder = json.JSONEncoder(ensure_ascii=False)
        template = environment.from_string(input_string)
        output_string = template.render(self.get_template_context())

        return output_string

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Show a table containing the current component attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['Name','PCI Address']

        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param colors: True to specify state colors for pandas output
        :type colors: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """
        data = self.toDict()

        # fields = ["Name", "Details", "Disk", "Units", "PCI Address",
        #        "Model", "Type"
        #         ]

        if pretty_names:
            pretty_names_dict = self.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        table = self.get_fablib_manager().show_table(
            data,
            fields=fields,
            title="Component",
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

        return table

    def list_interfaces(
        self,
        fields=None,
        output=None,
        quiet=False,
        filter_function=None,
        refresh: bool = False,
    ):
        """
        Lists all the interfaces in the component with their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','MAC']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['Node'] == 'Node1'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        ifaces = []
        for iface in self.get_interfaces(refresh=refresh):
            ifaces.append(iface.get_name())

        name_filter = lambda s: s["Name"] in set(ifaces)
        if filter_function is not None:
            filter_function = lambda x: filter_function(x) + name_filter(x)
        else:
            filter_function = name_filter

        return self.get_slice().list_interfaces(
            fields=fields,
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            refresh=refresh,
        )

    @staticmethod
    def calculate_name(node: Node = None, name: str = None) -> str:
        """
        Not intended for API use
        """
        # Hack to make it possile to find interfaces
        return f"{node.get_name()}-{name}"

    @staticmethod
    def new_component(
        node: Node = None, model: str = None, name: str = None, user_data: dict = {}
    ):
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

        component = Component(
            node=node,
            fim_component=node.fim_node.add_component(
                model_type=Component.component_model_map[model], name=name
            ),
        )
        component.set_user_data(user_data)
        component.get_interfaces(refresh=True)
        return component

    def __init__(self, node: Node = None, fim_component: FimComponent = None):
        """
        Typically invoked when you add a component to a ``Node``.

        .. note ::

            ``Component`` constructer is not meant to be directly used.

        :param node: the fablib node to build the component on
        :type node: Node

        :param fim_component: the FIM component this object represents
        :type fim_component: FIMComponent
        """
        super().__init__()
        self.fim_component = fim_component
        self.node = node
        self.interfaces = {}

    def get_interfaces(
        self, include_subs: bool = True, refresh: bool = False, output: str = "list"
    ) -> Union[dict[str, Interface], list[Interface]]:
        """
        Gets the interfaces attached to this fablib component's FABRIC component.

        :param include_subs: Flag indicating if sub interfaces should be included
        :type include_subs: bool

        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :param output: Specify how the return type is expected; Possible values: list or dict
        :type output: str

        :return: a list or dict of the interfaces on this component.
        :rtype: Union[dict[str, Interface], list[Interface]]
        """

        from fabrictestbed_extensions.fablib.interface import Interface

        if len(self.interfaces) == 0 or refresh:
            for fim_interface in self.get_fim_component().interface_list:
                iface = Interface(component=self, fim_interface=fim_interface)
                self.interfaces[iface.get_name()] = iface
                if include_subs:
                    child_interfaces = iface.get_interfaces(
                        refresh=refresh, output="dict"
                    )
                    if child_interfaces and len(child_interfaces):
                        self.interfaces.update(child_interfaces)

        if output == "dict":
            return self.interfaces
        else:
            return list(self.interfaces.values())

    def get_fim_component(self) -> FimComponent:
        """
        Not recommended for most users.

        GGets the FABRIC component this fablib component represents. This method
        is used to access data at a lower level than FABlib.

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

    def get_short_name(self):
        """
        Gets the short name of the component.
        """
        # strip of the extra parts of the name added by fim
        return self.get_name()[len(f"{self.get_node().get_name()}-") :]

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

    def get_numa_node(self) -> str:
        """
        Get the Numa Node assigned to the device
        """
        try:
            numa = self.get_fim_component().get_property(pname="label_allocations").numa
            if numa is not None:
                if isinstance(numa, str):
                    return numa
                if isinstance(numa, list):
                    return numa[0]
        except Exception as e:
            logging.error(f"get_numa_node failed: {e}")
            return None

    def get_disk(self) -> int:
        """
        Gets the amount of disk space on this component.

        :return: this component's disk space
        :rtype: int
        """
        return self.get_fim_component().get_property(pname="capacity_allocations").disk

    def get_unit(self) -> int:
        """
        Get unit count for this component.

        :return: unit
        :rtype: int
        """
        return self.get_fim_component().get_property(pname="capacity_allocations").unit

    def get_pci_addr(self) -> str:
        """
        Get the PIC device ID for this component.

        :return: PCI device ID
        :rtype: String
        """
        return self.get_fim_component().get_property(pname="label_allocations").bdf

    def get_model(self) -> str:
        """
        Get FABlib model name for this component.

        :return: FABlib model name
        :rtype: String
        """
        # TODO: This a hack that need a real fix
        if (
            str(self.get_type()) == "SmartNIC"
            and str(self.get_fim_model()) == "ConnectX-6"
        ):
            return Constants.CMP_NIC_ConnectX_6
        if (
            str(self.get_type()) == "SmartNIC"
            and str(self.get_fim_model()) == "BlueField-2-ConnectX-6"
        ):
            return Constants.CMP_NIC_BlueField2_ConnectX_6
        elif (
            str(self.get_type()) == "SmartNIC"
            and str(self.get_fim_model()) == "ConnectX-5"
        ):
            return Constants.CMP_NIC_ConnectX_5
        elif str(self.get_type()) == "NVME" and str(self.get_fim_model()) == "P4510":
            return Constants.CMP_NVME_P4510
        elif str(self.get_type()) == "GPU" and str(self.get_fim_model()) == "Tesla T4":
            return Constants.CMP_GPU_TeslaT4
        elif str(self.get_type()) == "GPU" and str(self.get_fim_model()) == "RTX6000":
            return Constants.CMP_GPU_RTX6000
        elif (
            str(self.get_type()) == "SharedNIC"
            and str(self.get_fim_model()) == "ConnectX-6"
        ):
            return Constants.CMP_NIC_Basic

    def get_reservation_id(self) -> str or None:
        """
        Get reservation ID for this component.

        :return:  reservation ID
        :rtype: String
        """
        try:
            # This does not work
            # print(f"{self.get_fim_component()}")
            return (
                self.get_fim_component()
                .get_property(pname="reservation_info")
                .reservation_id
            )
        except:
            return None

    def get_reservation_state(self) -> str or None:
        """
        Get reservation state for this component.

        :return:  reservation state
        :rtype: String
        """
        try:
            return (
                self.get_fim_component()
                .get_property(pname="reservation_info")
                .reservation_state
            )
        except:
            return None

    def get_error_message(self) -> str:
        """
        Get error message for this component.

        :return:  reservation state
        :rtype: String
        """
        try:
            return (
                self.get_fim_component()
                .get_property(pname="reservation_info")
                .error_message
            )
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

    def configure(self, commands: List[str] = []):
        """
        Configure a component by executing a set of commands provided by the user or run any default commands
        """
        output = []
        start = time.time()
        try:
            if not commands or len(commands) == 0:
                commands = Component.component_configure_commands.get(self.get_model())

            if not commands or len(commands) == 0:
                return output

            for cmd in commands:
                stdout, stderr = self.node.execute(cmd)
                if stdout != "":
                    output.append(stdout)
                if stderr != "":
                    output.append(stderr)
        except Exception:
            logging.error(f"configure Fail: {self.get_name()}:", exc_info=True)
            raise Exception(str(output))

        print(f"\nTime to configure {time.time() - start:.0f} seconds")
        return output

    def configure_nvme(self, mount_point=""):
        """
        Configure the NVMe drive.

        Note this works but may be reorganized.

        :param mount_point: The mount point in the filesystem. Default = "" later reassigned to /mnt/{linux device name}
        :type mount_point: String
        """
        output = []
        try:
            device_pci_id = self.get_pci_addr()[0]
            stdout, stderr = self.node.execute(
                f'basename `sudo ls -l /sys/block/nvme*|grep "'
                f"{device_pci_id}\"|awk '{{print $9}}'`",
                quiet=True,
            )
            if stderr != "":
                output.append(
                    f"Cannot find NVME device name for PCI ID : {device_pci_id}"
                )
                raise Exception
            device_name = stdout.strip()
            block_device_name = f"/dev/{device_name}"
            output.append(self.node.execute(f"sudo fdisk -l {block_device_name}"))
            output.append(
                self.node.execute(f"sudo parted -s {block_device_name} mklabel gpt")
            )
            output.append(
                self.node.execute(f"sudo parted -s {block_device_name} print")
            )
            output.append(
                self.node.execute(
                    f"sudo parted -s {block_device_name} print unit MB print free"
                )
            )
            output.append(
                self.node.execute(
                    f"sudo parted -s --align optimal "
                    f"{block_device_name} "
                    f"mkpart primary ext4 0% 100%"
                )
            )
            output.append(self.node.execute(f"lsblk {block_device_name}"))
            output.append(self.node.execute(f"sudo mkfs.ext4 {block_device_name}p1"))
            # This is to use a unique mountpoint when it is not provided by the user
            if mount_point == "":
                mount_point = f"/mnt/{device_name}"
            output.append(
                self.node.execute(
                    f"sudo mkdir -p "
                    f"{mount_point}"
                    f" && sudo mount "
                    f"{block_device_name}"
                    f"p1 "
                    f"{mount_point}"
                )
            )
            output.append(self.node.execute(f"df -h {mount_point}"))
        except Exception as e:
            logging.error(f"config_nvme Fail: {self.get_name()}:", exc_info=True)
            raise Exception(str(output))

        return output

    def get_device_name(self) -> str:
        """
        Not for API use
        """
        labels = self.get_fim_component().get_property(pname="label_allocations")
        return labels.device_name

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

        fim_component = node.fim_node.add_storage(
            name=name,
            labels=Labels(local_name=name),
            flags=Flags(auto_mount=auto_mount),
        )
        return Component(node=node, fim_component=fim_component)

    def get_fim(self):
        """
        Gets the component's FABRIC Information Model (fim) object.

        This method is used to access data at a lower level than
        FABlib.
        """
        return self.get_fim_component()

    def set_user_data(self, user_data: dict):
        """
        Set the user data for the component.

        This method stores the given user data dictionary as a JSON
        string in the FIM object associated with the component.

        :param user_data: The user data to be set.
        :type user_data: dict
        """
        self.get_fim().set_property(
            pname="user_data", pval=UserData(json.dumps(user_data))
        )

    def get_user_data(self) -> dict:
        """
        Retrieve the user data for the component.

        This method fetches the user data stored in the FIM object
        associated with the component and returns it as a dictionary.
        If an error occurs, it returns an empty dictionary.

        :return: The user data dictionary.
        :rtype: dict
        """
        try:
            return json.loads(str(self.get_fim().get_property(pname="user_data")))
        except:
            return {}

    def delete(self):
        """
        Remove the component from the slice/node.
        """
        if self.get_interfaces(refresh=True):
            for interface in self.get_interfaces():
                interface.delete()

        self.get_slice().get_fim_topology().nodes[
            self.get_node().get_name()
        ].remove_component(name=self.get_name())
