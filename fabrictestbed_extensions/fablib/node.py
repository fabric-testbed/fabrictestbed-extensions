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

import concurrent.futures
import ipaddress
import json
import logging
import select
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

import jinja2
import paramiko
from IPython.core.display_functions import display
from tabulate import tabulate

from fabrictestbed_extensions.fablib.network_service import NetworkService

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabric_cf.orchestrator.swagger_client import Sliver as OrchestratorSliver

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address

from fabrictestbed.slice_editor import Capacities, CapacityHints, Labels
from fabrictestbed.slice_editor import Node as FimNode
from fabrictestbed.slice_editor import ServiceType, UserData
from fim.slivers.network_service import NSLayer

from fabrictestbed_extensions.fablib.component import Component
from fabrictestbed_extensions.fablib.interface import Interface


class Node:
    default_cores = 2
    default_ram = 8
    default_disk = 10
    default_image = "default_rocky_8"

    def __init__(self, slice: Slice, node: FimNode):
        """
        Constructor. Sets the fablib slice and FIM node based on arguments.
        :param slice: the fablib slice to have this node on
        :type slice: Slice
        :param node: the FIM node that this Node represents
        :type node: Node
        """
        super().__init__()
        self.fim_node = node
        self.slice = slice
        self.host = None
        self.ip_addr_list_json = None

        # Try to set the username.
        try:
            self.set_username()
        except:
            self.username = None

        try:
            if slice.isStable():
                self.sliver = slice.get_sliver(reservation_id=self.get_reservation_id())
        except:
            pass

        self.sliver = None

        logging.getLogger("paramiko").setLevel(logging.WARNING)

    def get_fablib_manager(self):
        return self.slice.get_fablib_manager()

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the node.
        Intended for printing node information.
        :return: Tabulated string of node information
        :rtype: String
        """
        table = [
            ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Cores", self.get_cores()],
            ["RAM", self.get_ram()],
            ["Disk", self.get_disk()],
            ["Image", self.get_image()],
            ["Image Type", self.get_image_type()],
            ["Host", self.get_host()],
            ["Site", self.get_site()],
            ["Management IP", self.get_management_ip()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ["SSH Command", self.get_ssh_command()],
        ]

        return tabulate(table)  # , headers=["Property", "Value"])

    def get_sliver(self) -> OrchestratorSliver:
        """
        Not intended as API call
        Gets the node SM sliver
        :return: SM sliver for the node
        :rtype: Sliver
        """
        return self.sliver

    @staticmethod
    def new_node(
        slice: Slice = None, name: str = None, site: str = None, avoid: List[str] = []
    ):
        """
        Not intended for API call. See: Slice.add_node()
        Creates a new FABRIC node and returns a fablib node with the new node.
        :param slice: the fablib slice to build the new node on
        :type slice: Slice
        :param name: the name of the new node
        :type name: str
        :param site: the name of the site to build the node on
        :type site: str
        :param avoid: a list of node names to avoid
        :type avoid: List[str]
        :return: a new fablib node
        :rtype: Node
        """
        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(avoid=avoid)

        logging.info(f"Adding node: {name}, slice: {slice.get_name()}, site: {site}")
        node = Node(slice, slice.topology.add_node(name=name, site=site))
        node.set_capacities(
            cores=Node.default_cores, ram=Node.default_ram, disk=Node.default_disk
        )
        node.set_image(Node.default_image)

        node.init_fablib_data()

        return node

    @staticmethod
    def get_node(slice: Slice = None, node=None):
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
        return Node(slice, node)

    def toJson(self):
        """
        Returns the node attributes as a json string

        :return: slice attributes as json string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_name_dict():
        return {
            "id": "ID",
            "name": "Name",
            "cores": "Cores",
            "ram": "RAM",
            "disk": "Disk",
            "image": "Image",
            "image_type": "Image Type",
            "host": "Host",
            "site": "Site",
            "username": "Username",
            "management_ip": "Management IP",
            "state": "State",
            "error": "Error",
            "ssh_command": "SSH Command",
            "public_ssh_key_file": "Public SSH Key File",
            "private_ssh_key_file": "Private SSH Key File",
        }

    def toDict(self, skip=[]):
        """
        Returns the node attributes as a dictionary

        :return: slice attributes as  dictionary
        :rtype: dict
        """
        rtn_dict = {}

        if "id" not in skip:
            rtn_dict["id"] = str(self.get_reservation_id())
        if "name" not in skip:
            rtn_dict["name"] = str(self.get_name())
        if "cores" not in skip:
            rtn_dict["cores"] = str(self.get_cores())
        if "ram" not in skip:
            rtn_dict["ram"] = str(self.get_ram())
        if "disk" not in skip:
            rtn_dict["disk"] = str(self.get_disk())
        if "image" not in skip:
            rtn_dict["image"] = str(self.get_image())
        if "image_type" not in skip:
            rtn_dict["image_type"] = str(self.get_image_type())
        if "host" not in skip:
            rtn_dict["host"] = str(self.get_host())
        if "site" not in skip:
            rtn_dict["site"] = str(self.get_site())
        if "username" not in skip:
            rtn_dict["username"] = str(self.get_username())
        if "management_ip" not in skip:
            rtn_dict["management_ip"] = (
                str(self.get_management_ip()).strip()
                if str(self.get_reservation_state()) == "Active"
                and self.get_management_ip()
                else ""
            )  # str(self.get_management_ip())
        if "state" not in skip:
            rtn_dict["state"] = str(self.get_reservation_state())
        if "error" not in skip:
            rtn_dict["error"] = str(self.get_error_message())
        if "ssh_command" not in skip:
            if str(self.get_reservation_state()) == "Active":
                rtn_dict["ssh_command"] = str(self.get_ssh_command())
            else:
                rtn_dict["ssh_command"] = ""
        if "public_ssh_key_file" not in skip:
            rtn_dict["public_ssh_key_file"] = str(self.get_public_key_file())
        if "private_ssh_key_file" not in skip:
            rtn_dict["private_ssh_key_file"] = str(self.get_private_key_file())

        return rtn_dict

    def generate_template_context(self):
        context = self.toDict(skip=["ssh_command"])
        context["components"] = []
        # for component in self.get_components():
        #    context["components"].append(component.get_name())

        #    context["components"].append(component.generate_template_context())

        return context

    def get_template_context(self):
        return self.get_slice().get_template_context(self, skip=["ssh_command"])

    def render_template(self, input_string):
        environment = jinja2.Environment()
        # environment.json_encoder = json.JSONEncoder(ensure_ascii=False)
        template = environment.from_string(input_string)
        output_string = template.render(self.get_template_context())

        return output_string

    def delete(self):
        self.get_slice().get_fim_topology().remove_node(name=self.get_name())

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Show a table containing the current node attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['Name','State']

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

        # if fields == None:
        #    fields = ["ID", "Name", "Cores", "RAM", "Disk",
        #            "Image", "Image Type","Host", "Site",
        #            "Management IP", "State",
        #            "Error","SSH Command"
        #             ]

        def state_color(val):
            if val == "Active":
                color = f"{self.get_fablib_manager().SUCCESS_LIGHT_COLOR}"
            elif val == "Configuring":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            elif val == "Closed":
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            else:
                color = ""
            return "background-color: %s" % color

        if pretty_names:
            pretty_names_dict = self.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        if colors and self.get_fablib_manager().is_jupyter_notebook():
            table = self.get_fablib_manager().show_table(
                data,
                fields=fields,
                title="Node",
                output="pandas",
                quiet=True,
                pretty_names_dict=pretty_names_dict,
            )
            table.applymap(state_color)

            if quiet == False:
                display(table)
        else:
            table = self.get_fablib_manager().show_table(
                data,
                fields=fields,
                title="Node",
                output=output,
                quiet=quiet,
                pretty_names_dict=pretty_names_dict,
            )

        return table

    def list_components(
        self,
        fields=None,
        output=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the components in the node with their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','Model']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['Model'] == 'NIC_Basic'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :return: table in format specified by output parameter
        :rtype: Object
        """

        components = []
        for component in self.get_components():
            components.append(component.get_name())

        def combined_filter_function(x):
            if filter_function == None:
                if x["name"] in set(components):
                    return True
            else:
                if filter_function(x) and x["name"] in set(components):
                    return True

            return False

        if pretty_names and len(self.get_components()) > 0:
            pretty_names_dict = self.get_components()[0].get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        return self.get_slice().list_components(
            fields=fields,
            output=output,
            quiet=quiet,
            filter_function=combined_filter_function,
            pretty_names=pretty_names_dict,
        )

    def list_interfaces(
        self,
        fields=None,
        output=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the interfaces in the node with their attributes.

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
        :return: table in format specified by output parameter
        :rtype: Object
        """

        if str(self.get_reservation_state()) != "Active":
            logging.debug(
                f"Node {self.get_name()} is {self.get_reservation_state()}, Skipping get interfaces."
            )
            return

        ifaces = []
        for iface in self.get_interfaces():
            ifaces.append(iface.get_name())

        def combined_filter_function(x):
            if filter_function == None:
                if x["name"]["value"] in set(ifaces):
                    return True
            else:
                if filter_function(x) and x["name"]["value"] in set(ifaces):
                    return True

            return False

        # name_filter = lambda s: s['Name'] in set(ifaces)
        # if filter_function != None:
        #    filter_function = lambda x: filter_function(x) + name_filter(x)
        # else:
        #    filter_function = name_filter

        return self.get_slice().list_interfaces(
            fields=fields,
            output=output,
            quiet=quiet,
            filter_function=combined_filter_function,
            pretty_names=pretty_names,
        )

    def list_networks(
        self,
        fields=None,
        output=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the networks attached to  the nodes with their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','Type']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['Type'] == 'FABNetv4'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :return: table in format specified by output parameter
        :rtype: Object
        """

        interfaces = self.get_interfaces()
        networks = self.get_networks()

        networks = []
        for iface in interfaces:
            networks.append(iface.get_network().get_name())

        def combined_filter_function(x):
            if filter_function == None:
                if x["name"]["value"] in set(networks):
                    return True
            else:
                if filter_function(x) and x["name"]["value"] in set(networks):
                    return True

            return False

        if pretty_names and len(networks) > 0:
            pretty_names_dict = networks[0].get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        return self.get_slice().list_networks(
            fields=fields,
            output=output,
            quiet=quiet,
            filter_function=combined_filter_function,
            pretty_names_dict=pretty_names_dict,
        )

    def get_networks(self):
        networks = []
        for interface in self.get_interfaces():
            networks.append(interface.get_network())

        return networks

    def get_fim_node(self) -> FimNode:
        """
        Not recommended for most users.

        Gets the node's FABRIC Information Model (fim) object. This method
        is used to access data at a lower level than FABlib.

        :return: the FABRIC model node
        :rtype: FIMNode
        """
        return self.fim_node

    def set_capacities(self, cores: int = 2, ram: int = 2, disk: int = 10):
        """
        Sets the capacities of the FABRIC node.
        :param cores: the number of cores to set on this node
        :type cores: int
        :param ram: the amount of RAM to set on this node
        :type ram: int
        :param disk: the amount of disk space to set on this node
        :type disk: int
        """
        cores = int(cores)
        ram = int(ram)
        disk = int(disk)

        cap = Capacities(core=cores, ram=ram, disk=disk)
        self.get_fim_node().set_properties(capacities=cap)

    def set_instance_type(self, instance_type: str):
        """
        Sets the instance type of this fablib node on the FABRIC node.
        :param instance_type: the name of the instance type to set
        :type instance_type: String
        """
        self.get_fim_node().set_properties(
            capacity_hints=CapacityHints(instance_type=instance_type)
        )

    def set_username(self, username: str = None):
        """
        Not intended as an API call.
        Sets this fablib node's username
        Optional username parameter. The username likely should be picked
        to match the image type.
        :param username: username
        """
        if username is not None:
            self.username = username
        elif "centos" in self.get_image():
            self.username = "centos"
        elif "ubuntu" in self.get_image():
            self.username = "ubuntu"
        elif "rocky" in self.get_image():
            self.username = "rocky"
        elif "fedora" in self.get_image():
            self.username = "fedora"
        elif "cirros" in self.get_image():
            self.username = "cirros"
        elif "debian" in self.get_image():
            self.username = "debian"
        elif "freebsd" in self.get_image():
            self.username = "freebsd"
        elif "openbsd" in self.get_image():
            self.username = "openbsd"
        else:
            self.username = None

    def set_image(self, image: str, username: str = None, image_type: str = "qcow2"):
        """
        Sets the image information of this fablib node on the FABRIC node.
        :param image: the image reference to set
        :type image: String
        :param username: the username of this fablib node. Currently unused.
        :type username: String
        :param image_type: the image type to set
        :type image_type: String
        """
        self.get_fim_node().set_properties(image_type=image_type, image_ref=image)
        self.set_username(username=username)

    def set_host(self, host_name: str = None):
        """
        Sets the hostname of this fablib node on the FABRIC node.
        :param host_name: the hostname. example: host_name='renc-w2.fabric-testbed.net'
        :type host_name: String
        """
        # example: host_name='renc-w2.fabric-testbed.net'
        labels = Labels()
        labels.instance_parent = host_name
        self.get_fim_node().set_properties(labels=labels)

        # set an attribute used to get host before Submit
        self.host = host_name

    def set_site(self, site):
        """
        Sets the hostname of this fablib node on the FABRIC node.
        :param host_name: the hostname. example: host_name='renc-w2.fabric-testbed.net'
        :type host_name: String
        """
        # example: host_name='renc-w2.fabric-testbed.net'
        self.get_fim_node().site = site

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice associated with this node.
        :return: the fablib slice on this node
        :rtype: Slice
        """
        return self.slice

    def get_name(self) -> str or None:
        """
        Gets the name of the FABRIC node.
        :return: the name of the node
        :rtype: String
        """
        try:
            return self.get_fim_node().name
        except:
            return None

    def get_cores(self) -> int or None:
        """
        Gets the number of cores on the FABRIC node.
        :return: the number of cores on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname="capacity_allocations").core
        except:
            return None

    def get_ram(self) -> int or None:
        """
        Gets the amount of RAM on the FABRIC node.
        :return: the amount of RAM on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname="capacity_allocations").ram
        except:
            return None

    def get_disk(self) -> int or None:
        """
        Gets the amount of disk space on the FABRIC node.
        :return: the amount of disk space on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname="capacity_allocations").disk
        except:
            return None

    def get_image(self) -> str or None:
        """
        Gets the image reference on the FABRIC node.
        :return: the image reference on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().image_ref
        except:
            return None

    def get_image_type(self) -> str or None:
        """
        Gets the image type on the FABRIC node.
        :return: the image type on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().image_type
        except:
            return None

    def get_host(self) -> str or None:
        """
        Gets the hostname on the FABRIC node.
        :return: the hostname on the node
        :rtype: String
        """
        try:
            if self.host is not None:
                return self.host
            return (
                self.get_fim_node()
                .get_property(pname="label_allocations")
                .instance_parent
            )
        except:
            return None

    def get_site(self) -> str or None:
        """
        Gets the sitename on the FABRIC node.
        :return: the sitename on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().site
        except:
            return None

    def get_management_ip(self) -> str or None:
        """
        Gets the management IP on the FABRIC node.
        :return: management IP
        :rtype: String
        """
        try:
            return self.get_fim_node().management_ip
        except:
            return None

    def get_reservation_id(self) -> str or None:
        """
        Gets the reservation ID on the FABRIC node.
        :return: reservation ID on the node
        :rtype: String
        """
        try:
            return (
                self.get_fim_node()
                .get_property(pname="reservation_info")
                .reservation_id
            )
        except:
            return None

    def get_reservation_state(self) -> str or None:
        """
        Gets the reservation state on the FABRIC node.
        :return: the reservation state on the node
        :rtype: String
        """
        try:
            return (
                self.get_fim_node()
                .get_property(pname="reservation_info")
                .reservation_state
            )
        except:
            return None

    def get_error_message(self) -> str or None:
        """
        Gets the error message on the FABRIC node.
        :return: the error message on the node
        :rtype: String
        """
        try:
            return (
                self.get_fim_node().get_property(pname="reservation_info").error_message
            )
        except:
            return ""

    def get_interfaces(self) -> List[Interface] or None:
        """
        Gets a list of the interfaces associated with the FABRIC node.
        :return: a list of interfaces on the node
        :rtype: List[Interface]
        """
        interfaces = []
        for component in self.get_components():
            for interface in component.get_interfaces():
                interfaces.append(interface)

        return interfaces

    def get_interface(
        self, name: str = None, network_name: str = None
    ) -> Interface or None:
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
        if name is not None:
            for component in self.get_components():
                for interface in component.get_interfaces():
                    if interface.get_name() == name:
                        return interface
        elif network_name is not None:
            for interface in self.get_interfaces():
                if (
                    interface is not None
                    and interface.get_network() is not None
                    and interface.get_network().get_name() == network_name
                ):
                    return interface

        raise Exception("Interface not found: {}".format(name))

    def get_username(self) -> str:
        """
        Gets the username on this fablib node.
        :return: the username on this node
        :rtype: String
        """
        return self.username

    def get_public_key(self) -> str:
        """
        Gets the public key on fablib node.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the public key on the node
        :rtype: String
        """
        return self.get_slice().get_slice_public_key()

    def get_public_key_file(self) -> str:
        """
        Gets the public key file path on the fablib node.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the public key path
        :rtype: String
        """
        return self.get_slice().get_slice_public_key_file()

    def get_private_key(self) -> str:
        """
        Gets the private key on the fablib node.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the private key on the node
        :rtype: String
        """
        return self.get_slice().get_slice_private_key()

    def get_private_key_file(self) -> str:
        """
        Gets the private key file path on the fablib slice.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the private key path
        :rtype: String
        """
        return self.get_slice().get_slice_private_key_file()

    def get_private_key_passphrase(self) -> str:
        """
        Gets the private key passphrase on the FABLIB slice.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the private key passphrase
        :rtype: String
        """
        return self.get_slice().get_private_key_passphrase()

    def add_component(
        self, model: str = None, name: str = None, user_data: dict = {}
    ) -> Component:
        """
        Creates a new FABRIC component using this fablib node.
        Example model include:
        - NIC_Basic: A single port 100 Gbps SR-IOV Virtual Function on a Mellanox ConnectX-6
        - NIC_ConnectX_5: A dual port 25 Gbps Mellanox ConnectX-5
        - NIC_ConnectX_6: A dual port 100 Gbps Mellanox ConnectX-6
        - NVME_P4510: NVMe Storage Device
        - GPU_TeslaT4: Tesla T4 GPU
        - GPU_RTX6000: RTX6000 GPU
        - GPU_A30: A30 GPU
        - GPU_A40: A40 GPU
        - FPGA_Xilinx_U280: Xilinx U280 GPU
        :param model: the name of the component model to add
        :type model: String
        :param name: the name of the new component
        :type name: String
        :return: the new component
        :rtype: Component
        """
        return Component.new_component(
            node=self, model=model, name=name, user_data=user_data
        )

    def get_components(self) -> List[Component]:
        """
        Gets a list of components associated with this node.
        :return: a list of components on this node
        :rtype: List[Component]
        """
        return_components = []
        for component_name, component in self.get_fim_node().components.items():
            return_components.append(Component(self, component))

        return return_components

    def get_component(self, name: str) -> Component:
        """
        Gets a particular component associated with this node.
        :param name: the name of the component to search for
        :type name: String
        :raise Exception: if component not found by name
        :return: the component on the FABRIC node
        :rtype: Component
        """
        try:
            name = Component.calculate_name(node=self, name=name)
            return Component(self, self.get_fim_node().components[name])
        except Exception as e:
            logging.error(e, exc_info=True)
            raise Exception(f"Component not found: {name}")

    def get_ssh_command(self) -> str:
        """
        Gets an SSH command used to access this node node from a terminal.
        :return: the SSH command to access this node
        :rtype: str
        """

        # ssh_command = self.get_fablib_manager().get_ssh_command_line()

        # return self.template_substitution(ssh_command)

        # try:
        #    return self.template_substitution(self.get_fablib_manager().get_ssh_command_line())
        # except:
        #    return self.get_fablib_manager().get_ssh_command_line()

        try:
            return self.render_template(
                self.get_fablib_manager().get_ssh_command_line()
            )
        except:
            return self.get_fablib_manager().get_ssh_command_line()

        # for key,val in self.toDict(skip=["SSH Command"]).items():
        #    remove_str = '${'+str(key).strip()+'}'
        #    add_str = str(val)
        #    ssh_command = ssh_command.replace(remove_str, add_str)

        # for key,val in self.get_fablib_manager().get_config().items():
        #    remove_str = '${'+str(key).strip()+'}'
        #    add_str = str(val)
        #    ssh_command = ssh_command.replace(remove_str, add_str)

        # return ssh_command

        # return 'ssh -i {} -F /path/to/your/ssh/config/file {}@{}'.format(self.get_private_key_file(),
        #                                   self.get_username(),
        #                                   self.get_management_ip())

    def validIPAddress(self, IP: str) -> str:
        """
        Checks if the IP string is a valid IP address.
        :param IP: the IP string to check
        :type IP: String
        :return: the type of IP address the IP string is, or 'Invalid'
        :rtype: String
        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def get_paramiko_key(
        self, private_key_file: str = None, get_private_key_passphrase: str = None
    ) -> paramiko.PKey:
        # TODO: This is a bit of a hack and should probably test he keys for their types
        # rather than relying on execptions
        if get_private_key_passphrase:
            try:
                return paramiko.RSAKey.from_private_key_file(
                    self.get_private_key_file(),
                    password=self.get_private_key_passphrase(),
                )
            except:
                pass

            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(
                    self.get_private_key_file(),
                    password=self.get_private_key_passphrase(),
                )
            except:
                pass
        else:
            try:
                return paramiko.RSAKey.from_private_key_file(
                    self.get_private_key_file()
                )
            except:
                pass

            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(
                    self.get_private_key_file()
                )
            except:
                pass

        raise Exception(f"ssh key invalid: FABRIC requires RSA or ECDSA keys")

    def execute_thread(
        self,
        command: str,
        retry: int = 3,
        retry_interval: int = 10,
        username: str = None,
        private_key_file: str = None,
        private_key_passphrase: str = None,
        output_file: str = None,
    ) -> threading.Thread:
        """
        Creates a thread that calls node.execute().  Results (i.e. stdout, stderr) from the thread can be
        retrieved with by calling thread.result()

        :param command: the command to run
        :type command: str
        :param retry: the number of times to retry SSH upon failure
        :type retry: int
        :param retry_interval: the number of seconds to wait before retrying SSH upon failure
        :type retry_interval: int
        :param username: username
        :type username: str
        :param private_key_file: path to private key file
        :type private_key_file: str
        :param private_key_passphrase: pass phrase
        :type private_key_passphrase: str
        :param output_file: path to a file where the stdout/stderr will be written. None for no file output
        :type output_file: List[str]
        :return: a thread that called node.execute()
        :raise Exception: if management IP is invalid
        """

        return (
            self.get_fablib_manager()
            .get_ssh_thread_pool_executor()
            .submit(
                self.execute,
                command,
                retry=retry,
                retry_interval=retry_interval,
                username=username,
                private_key_file=private_key_file,
                private_key_passphrase=private_key_passphrase,
                output_file=output_file,
                quiet=True,
            )
        )

    def execute(
        self,
        command: str,
        retry: int = 3,
        retry_interval: int = 10,
        username: str = None,
        private_key_file: str = None,
        private_key_passphrase: str = None,
        quiet: bool = False,
        read_timeout: int = 10,
        timeout=None,
        output_file: str = None,
    ):
        """
        Runs a command on the FABRIC node.

        The function uses paramiko to ssh to the FABRIC node and execute an arbitrary shell command.


        :param command: the command to run
        :type command: str
        :param retry: the number of times to retry SSH upon failure
        :type retry: int
        :param retry_interval: the number of seconds to wait before retrying SSH upon failure
        :type retry_interval: int
        :param username: username
        :type username: str
        :param private_key_file: path to private key file
        :type private_key_file: str
        :param private_key_passphrase: pass phrase
        :type private_key_passphrase: str
        :param output_file: path to a file where the stdout/stderr will be written. None for no file output
        :type output_file: List[str]
        :param output: print stdout and stderr to the screen
        :type output: bool
        :param read_timeout: the number of seconds to wait before retrying to
        read from stdout and stderr
        :type read_timeout: int
        :param timeout: the number of seconds to wait before terminating the
        command using the linux timeout command. Specifying a timeout
        encapsulates the command with the timeout command for you
        :type timeout: int
        :return: a tuple of  (stdout[Sting],stderr[String])
        :rtype: Tuple
        :raise Exception: if management IP is invalid
        """
        import logging

        logging.debug(
            f"execute node: {self.get_name()}, management_ip: {self.get_management_ip()}, command: {command}",
            stack_info=True,
        )

        if not self.get_reservation_state() == "Active":
            logging.debug(
                f"Execute failed. Node {self.get_name()} in state {self.get_reservation_state()}"
            )

        if not self.get_management_ip():
            logging.debug(
                f"Execute failed. Node {self.get_name()} in management IP  {self.get_management_ip()}"
            )

        # if not quiet:
        chunking = True

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        # Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname="management_ip"))
        if self.validIPAddress(management_ip) == "IPv4":
            # src_addr = (self.get_fablib_manager().get_bastion_private_ipv4_addr(), 22)
            src_addr = ("0.0.0.0", 22)

        elif self.validIPAddress(management_ip) == "IPv6":
            # src_addr = (self.get_fablib_manager().get_bastion_private_ipv6_addr(), 22)
            src_addr = ("0:0:0:0:0:0:0:0", 22)
        else:
            logging.error("node.execute: Management IP Invalid:", exc_info=True)
            raise Exception(f"node.execute: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        bastion_username = self.get_fablib_manager().get_bastion_username()
        bastion_key_file = self.get_fablib_manager().get_bastion_key_filename()

        if username != None:
            node_username = username
        else:
            node_username = self.username

        if private_key_file != None:
            node_key_file = private_key_file
        else:
            node_key_file = self.get_private_key_file()

        if private_key_passphrase != None:
            node_key_passphrase = private_key_passphrase
        else:
            node_key_passphrase = self.get_private_key_file()

        for attempt in range(int(retry)):
            try:
                key = self.get_paramiko_key(
                    private_key_file=node_key_file,
                    get_private_key_passphrase=node_key_passphrase,
                )
                bastion = paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(
                    self.get_fablib_manager().get_bastion_public_addr(),
                    username=bastion_username,
                    key_filename=bastion_key_file,
                )

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel(
                    "direct-tcpip", dest_addr, src_addr
                )

                client = paramiko.SSHClient()
                # client.load_system_host_keys()
                # client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(
                    management_ip,
                    username=node_username,
                    pkey=key,
                    sock=bastion_channel,
                )

                if output_file:
                    file = open(output_file, "a")

                # stdin, stdout, stderr = client.exec_command('echo \"' + command + '\" > /tmp/fabric_execute_script.sh; chmod +x /tmp/fabric_execute_script.sh; /tmp/fabric_execute_script.sh')

                if timeout is not None:
                    command = (
                        f"sudo timeout --foreground -k 10 {timeout} " + command + "\n"
                    )

                stdin, stdout, stderr = client.exec_command(command)
                channel = stdout.channel

                # Only writing one command, so we can shut down stdin and
                # writing abilities
                stdin.close()
                channel.shutdown_write()

                # Read stdout and stderr:
                if not chunking:
                    # The old way
                    rtn_stdout = str(stdout.read(), "utf-8").replace("\\n", "\n")
                    rtn_stderr = str(stderr.read(), "utf-8").replace("\\n", "\n")
                    if quiet == False:
                        print(rtn_stdout, rtn_stderr)

                else:
                    # Credit to Stack Overflow user tintin's post here: https://stackoverflow.com/a/32758464
                    stdout_chunks = []
                    try:
                        stdout_chunks.append(
                            stdout.channel.recv(len(stdout.channel.in_buffer))
                        )
                    except EOFError:
                        logging.warning(
                            "A Paramiko EOFError has occurred, "
                            "if this is part of a reboot sequence, it can be ignored"
                        )
                    stderr_chunks = []

                    while (
                        not channel.closed
                        or channel.recv_ready()
                        or channel.recv_stderr_ready()
                    ):
                        got_chunk = False
                        readq, _, _ = select.select(
                            [stdout.channel], [], [], read_timeout
                        )
                        for c in readq:
                            if c.recv_ready():
                                stdoutbytes = stdout.channel.recv(len(c.in_buffer))
                                if quiet == False:
                                    print(
                                        str(stdoutbytes, "utf-8").replace("\\n", "\n"),
                                        end="",
                                    )
                                if output_file:
                                    file.write(
                                        str(stdoutbytes, "utf-8").replace("\\n", "\n")
                                    )
                                    file.flush()

                                stdout_chunks.append(stdoutbytes)
                                got_chunk = True
                            if c.recv_stderr_ready():
                                # make sure to read stderr to prevent stall
                                stderrbytes = stderr.channel.recv_stderr(
                                    len(c.in_stderr_buffer)
                                )
                                if quiet == False:
                                    print(
                                        "\x1b[31m",
                                        str(stderrbytes, "utf-8").replace("\\n", "\n"),
                                        "\x1b[0m",
                                        end="",
                                    )
                                if output_file:
                                    file.write(
                                        str(stderrbytes, "utf-8").replace("\\n", "\n")
                                    )
                                    file.flush()
                                stderr_chunks.append(stderrbytes)
                                got_chunk = True

                        if (
                            not got_chunk
                            and stdout.channel.exit_status_ready()
                            and not stderr.channel.recv_stderr_ready()
                            and not stdout.channel.recv_ready()
                        ):
                            stdout.channel.shutdown_read()
                            stdout.channel.close()
                            break

                    stdout.close()
                    stderr.close()

                    # chunks are groups of bytes, combine and convert to str
                    rtn_stdout = b"".join(stdout_chunks).decode("utf-8")
                    rtn_stderr = b"".join(stderr_chunks).decode("utf-8")

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(
                        f"Running node.execute(): command: {command}, elapsed time: {end - start} seconds"
                    )

                logging.debug(f"rtn_stdout: {rtn_stdout}")
                logging.debug(f"rtn_stderr: {rtn_stderr}")

                if output_file:
                    file.close()

                return rtn_stdout, rtn_stderr
                # success, skip other tries
                break

            except Exception as e:
                logging.warning(
                    f"Exception in node.execute() (attempt #{attempt} of {retry}): {e}"
                )

                if attempt + 1 == retry:
                    raise e

                # Fail, try again
                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    logging.debug(
                        f"SSH execute fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again"
                    )
                    logging.debug(e, exc_info=True)

                time.sleep(retry_interval)
                pass

            # Clean-up of open connections and files.
            finally:
                try:
                    client.close()
                except Exception as e:
                    logging.debug(f"Exception in client.close(): {e}")

                try:
                    bastion_channel.close()
                except Exception as e:
                    logging.debug(f"Exception in bastion_channel.close(): {e}")

                try:
                    bastion.close()
                except Exception as e:
                    logging.debug(f"Exception in bastion.close(): {e}")

                try:
                    if output_file:
                        file.close()
                except Exception as e:
                    logging.debug(f"Exception in output_file.close(): {e}")

        raise Exception("ssh failed: Should not get here")

    def upload_file_thread(
        self,
        local_file_path: str,
        remote_file_path: str = ".",
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """
        Creates a thread that calls node.upload_file().  Results from the thread can be
        retrieved with by calling thread.result()
        :param local_file_path: the path to the file to upload
        :type local_file_path: str
        :param remote_file_path: the destination path of the file on the node
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :return: a thread that called node.execute()
        :rtype: Thread
        :raise Exception: if management IP is invalid
        """
        return (
            self.get_fablib_manager()
            .get_ssh_thread_pool_executor()
            .submit(
                self.upload_file,
                local_file_path,
                remote_file_path,
                retry=retry,
                retry_interval=retry_interval,
            )
        )

    def upload_file(
        self,
        local_file_path: str,
        remote_file_path: str = ".",
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """
        Upload a local file to a remote location on the node.
        :param local_file_path: the path to the file to upload
        :type local_file_path: str
        :param remote_file_path: the destination path of the file on the node
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        logging.debug(
            f"upload node: {self.get_name()}, local_file_path: {local_file_path}"
        )

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        # Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname="management_ip"))
        if self.validIPAddress(management_ip) == "IPv4":
            src_addr = ("0.0.0.0", 22)
        elif self.validIPAddress(management_ip) == "IPv6":
            src_addr = ("0:0:0:0:0:0:0:0", 22)
        else:
            raise Exception(f"upload_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(int(retry)):
            try:
                key = self.get_paramiko_key(
                    private_key_file=self.get_private_key_file(),
                    get_private_key_passphrase=self.get_private_key_file(),
                )

                bastion = paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(
                    self.get_fablib_manager().get_bastion_public_addr(),
                    username=self.get_fablib_manager().get_bastion_username(),
                    key_filename=self.get_fablib_manager().get_bastion_key_filename(),
                )

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel(
                    "direct-tcpip", dest_addr, src_addr
                )

                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(
                    management_ip,
                    username=self.username,
                    pkey=key,
                    sock=bastion_channel,
                )

                ftp_client = client.open_sftp()
                file_attributes = ftp_client.put(local_file_path, remote_file_path)

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(
                        f"Running node.upload_file(): file: {local_file_path}, "
                        f"elapsed time: {end - start} seconds"
                    )

                return file_attributes

            except Exception as e:
                logging.warning(f"Exception on upload_file() attempt #{attempt}: {e}")

                if attempt + 1 == retry:
                    raise e

                # Fail, try again
                logging.warning(
                    f"SCP upload fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again. Exception: {e}"
                )
                # traceback.print_exc()
                time.sleep(retry_interval)
                pass

            finally:
                try:
                    ftp_client.close()
                except Exception as e:
                    logging.debug(f"Exception in ftp_client.close(): {e}")

                try:
                    client.close()
                except Exception as e:
                    logging.debug(f"Exception in client.close(): {e}")

                try:
                    bastion_channel.close()
                except Exception as e:
                    logging.debug("Exception in bastion_channel.close(): {e}")

                try:
                    bastion.close()
                except Exception as e:
                    logging.debug("Exception in bastion.close(): {e}")

        raise Exception("scp upload failed")

    def download_file_thread(
        self,
        local_file_path: str,
        remote_file_path: str,
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """ "
        Creates a thread that calls node.download_file().  Results from the thread can be
        retrieved with by calling thread.result()
        :param local_file_path: the destination path for the remote file
        :type local_file_path: str
        :param remote_file_path: the path to the remote file to download
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP upon failure
        :type retry_interval: int
        :return: a thread that called node.download_file()
        :rtype: Thread
        :raise Exception: if management IP is invalid
        """
        return (
            self.get_fablib_manager()
            .get_ssh_thread_pool_executor()
            .submit(
                self.download_file,
                local_file_path,
                remote_file_path,
                retry=retry,
                retry_interval=retry_interval,
            )
        )

    def download_file(
        self,
        local_file_path: str,
        remote_file_path: str,
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """
        Download a remote file from the node to a local destination.
        :param local_file_path: the destination path for the remote file
        :type local_file_path: str
        :param remote_file_path: the path to the remote file to download
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP upon failure
        :type retry_interval: int
        """
        logging.debug(
            f"download node: {self.get_name()}, remote_file_path: {remote_file_path}"
        )

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        # Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname="management_ip"))
        if self.validIPAddress(management_ip) == "IPv4":
            src_addr = ("0.0.0.0", 22)

        elif self.validIPAddress(management_ip) == "IPv6":
            src_addr = ("0:0:0:0:0:0:0:0", 22)
        else:
            raise Exception(f"download_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(int(retry)):
            try:
                key = self.get_paramiko_key(
                    private_key_file=self.get_private_key_file(),
                    get_private_key_passphrase=self.get_private_key_file(),
                )

                bastion = paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(
                    self.get_fablib_manager().get_bastion_public_addr(),
                    username=self.get_fablib_manager().get_bastion_username(),
                    key_filename=self.get_fablib_manager().get_bastion_key_filename(),
                )

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel(
                    "direct-tcpip", dest_addr, src_addr
                )

                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(
                    management_ip,
                    username=self.username,
                    pkey=key,
                    sock=bastion_channel,
                )

                ftp_client = client.open_sftp()
                file_attributes = ftp_client.get(remote_file_path, local_file_path)

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(
                        f"Running node.download(): file: {remote_file_path}, "
                        f"elapsed time: {end - start} seconds"
                    )

                return file_attributes

            except Exception as e:
                logging.warning(
                    f"Exception in download_file() (attempt #{attempt} of {retry}): {e}"
                )

                if attempt + 1 == retry:
                    raise e

                # Fail, try again
                logging.warning(
                    f"SCP download fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again. Exception: {e}"
                )
                # traceback.print_exc()
                time.sleep(retry_interval)
                pass

            finally:
                try:
                    ftp_client.close()
                except Exception as e:
                    logging.debug(f"Exception in ftp_client.close(): {e}")

                try:
                    client.close()
                except Exception as e:
                    logging.debug(f"Exception in client.close(): {e}")

                try:
                    bastion_channel.close()
                except Exception as e:
                    logging.debug(f"Exception in bastion_channel.close(): {e}")

                try:
                    bastion.close()
                except Exception as e:
                    logging.debug(f"Exception in bastion.close(): {e}")

        raise Exception("scp download failed")

    def upload_directory_thread(
        self,
        local_directory_path: str,
        remote_directory_path: str,
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """ "
        Creates a thread that calls node.upload_directory. Results from the thread can be
        retrieved with by calling thread.result()
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :return: a thread that called node.download_file()
        :rtype: Thread
        :raise Exception: if management IP is invalid
        """
        return (
            self.get_fablib_manager()
            .get_ssh_thread_pool_executor()
            .submit(
                self.upload_directory,
                local_directory_path,
                remote_directory_path,
                retry=retry,
                retry_interval=retry_interval,
            )
        )

    def upload_directory(
        self,
        local_directory_path: str,
        remote_directory_path: str,
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """
        Upload a directory to remote location on the node.
        Makes a gzipped tarball of a directory and uploades it to a node. Then
        unzips and tars the directory at the remote_directory_path
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        import os
        import tarfile
        import tempfile

        logging.debug(
            f"upload node: {self.get_name()}, local_directory_path: {local_directory_path}"
        )

        output_filename = local_directory_path.split("/")[-1]
        root_size = len(local_directory_path) - len(output_filename)

        temp_name = next(tempfile._get_candidate_names())

        temp_file = "/tmp/" + str(temp_name) + ".tar.gz"

        with tarfile.open(temp_file, "w:gz") as tar_handle:
            for root, dirs, files in os.walk(local_directory_path):
                for file in files:
                    tar_handle.add(
                        os.path.join(root, file),
                        arcname=os.path.join(root, file)[root_size:],
                        recursive=True,
                    )
                for directory in dirs:
                    tar_handle.add(
                        os.path.join(root, directory),
                        arcname=os.path.join(root, directory)[root_size:],
                        recursive=True,
                    )

        self.upload_file(temp_file, temp_file, retry, retry_interval)
        os.remove(temp_file)
        self.execute(
            "mkdir -p "
            + remote_directory_path
            + "; tar -xf "
            + temp_file
            + " -C "
            + remote_directory_path
            + "; rm "
            + temp_file,
            retry,
            retry_interval,
            quiet=True,
        )
        return "success"

    def download_directory_thread(
        self,
        local_directory_path: str,
        remote_directory_path: str,
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """ "
        Creates a thread that calls node.download_directory. Results from the thread can be
        retrieved with by calling thread.result()
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        return (
            self.get_fablib_manager()
            .get_ssh_thread_pool_executor()
            .submit(
                self.download_directory,
                local_directory_path,
                remote_directory_path,
                retry=retry,
                retry_interval=retry_interval,
            )
        )

    def download_directory(
        self,
        local_directory_path: str,
        remote_directory_path: str,
        retry: int = 3,
        retry_interval: int = 10,
    ):
        """
        Downloads a directory from remote location on the node.
        Makes a gzipped tarball of a directory and downloads it from a node. Then
        unzips and tars the directory at the local_directory_path
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        import os
        import tarfile

        logging.debug(
            f"upload node: {self.get_name()}, local_directory_path: {local_directory_path}"
        )

        temp_file = "/tmp/unpackingfile.tar.gz"
        self.execute(
            "tar -czf " + temp_file + " " + remote_directory_path,
            retry,
            retry_interval,
            quiet=True,
        )

        self.download_file(temp_file, temp_file, retry, retry_interval)
        tar_file = tarfile.open(temp_file)
        tar_file.extractall(local_directory_path)

        self.execute("rm " + temp_file, retry, retry_interval, quiet=True)
        os.remove(temp_file)
        return "success"

    def test_ssh(self) -> bool:
        """
        Test whether SSH is functional on the node.
        :return: true if SSH is working, false otherwise
        :rtype: bool
        """
        logging.debug(f"test_ssh: node {self.get_name()}")

        try:
            if self.get_management_ip() is None:
                logging.debug(
                    f"Node: {self.get_name()} failed test_ssh because management_ip == None"
                )

            self.execute(
                f"echo test_ssh from {self.get_name()}",
                retry=1,
                retry_interval=10,
                quiet=True,
            )
        except Exception as e:
            # logging.debug(f"{e}")
            logging.debug(e, exc_info=True)
            return False
        return True

    def get_management_os_interface(self) -> str or None:
        """
        Gets the name of the management interface used by the node's operating
        system.
        :return: interface name
        :rtype: String
        """
        # TODO: Add docstring after doc networking classes
        # Assumes that the default route uses the management network
        logging.debug(f"{self.get_name()}->get_management_os_interface")
        stdout, stderr = self.execute("sudo ip -j route list", quiet=True)
        stdout_json = json.loads(stdout)

        for i in stdout_json:
            if i["dst"] == "default":
                logging.debug(
                    f"{self.get_name()}->get_management_os_interface: management_os_interface {i['dev']}"
                )
                return i["dev"]
        return None

    def get_dataplane_os_interfaces(self) -> List[dict]:
        """
        Gets a list of all the dataplane interface names used by the node's
        operating system.
        :return: interface names
        :rtype: List[String]
        """
        management_dev = self.get_management_os_interface()

        stdout, stderr = self.execute("sudo ip -j addr list", quiet=True)
        stdout_json = json.loads(stdout)
        dataplane_devs = []
        for i in stdout_json:
            if i["ifname"] != "lo" and i["ifname"] != management_dev:
                dataplane_devs.append({"ifname": i["ifname"], "mac": i["address"]})

        return dataplane_devs

    def flush_all_os_interfaces(self):
        """
        Flushes the configuration of all dataplane interfaces in the node.
        """
        for iface in self.get_dataplane_os_interfaces():
            self.flush_os_interface(iface["ifname"])

    def flush_os_interface(self, os_iface: str):
        """
        Flush the configuration of an interface in the node
        :param os_iface: the name of the interface to flush
        :type os_iface: String
        """
        stdout, stderr = self.execute(f"sudo ip addr flush dev {os_iface}", quiet=True)
        stdout, stderr = self.execute(
            f"sudo ip -6 addr flush dev {os_iface}", quiet=True
        )

    def ip_addr_list(self, output="json", update=False):
        try:
            if self.ip_addr_list_json is not None and update == False:
                return self.ip_addr_list_json
            else:
                if output == "json":
                    stdout, stderr = self.execute(f"sudo  ip -j addr list", quiet=True)
                    self.ip_addr_list_json = json.loads(stdout)
                    return self.ip_addr_list_json
                else:
                    stdout, stderr = self.execute(f"sudo ip list", quiet=True)
                    return stdout
        except Exception as e:
            logging.debug(f"Failed to get ip addr list: {e}")
            raise e

    def ip_route_add(
        self,
        subnet: Union[IPv4Network, IPv6Network],
        gateway: Union[IPv4Address, IPv6Address],
    ):
        """
        Add a route on the node.
        :param subnet: The destination subnet
        :type subnet:  IPv4Network or IPv6Network
        :param gateway: The next hop gateway.
        :type gateway: IPv4Address or IPv6Address
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} route add {subnet} via {gateway}", quiet=True)
        except Exception as e:
            logging.warning(f"Failed to add route: {e}")
            raise e

    def network_manager_stop(self):
        """
        Stop network manager on the node.
        """
        try:
            stdout, stderr = self.execute(
                f"sudo systemctl stop NetworkManager", quiet=True
            )
            logging.info(
                f"Stopped NetworkManager with 'sudo systemctl stop "
                f"NetworkManager': stdout: {stdout}\nstderr: {stderr}"
            )
        except Exception as e:
            logging.warning(f"Failed to stop network manager: {e}")
            raise e

    def network_manager_start(self):
        """
        (re)Start network manager on the node.
        """
        try:
            stdout, stderr = self.execute(
                f"sudo systemctl restart NetworkManager", quiet=True
            )
            logging.info(
                f"Started NetworkManager with 'sudo systemctl start NetworkManager': stdout: {stdout}\nstderr: {stderr}"
            )
        except Exception as e:
            logging.warning(f"Failed to start network manager: {e}")
            raise e

    def get_ip_routes(self):
        """
        Get a list of routes from the node.
        """
        try:
            stdout, stderr = self.execute("ip -j route list", quiet=True)
            return json.loads(stdout)
        except Exception as e:
            logging.warning(f"Exception: {e}")

    # fablib.Node.get_ip_addrs()
    def get_ip_addrs(self):
        """
        Get a list of ip address info from the node.
        """
        try:
            stdout, stderr = self.execute("ip -j addr list", quiet=True)

            addrs = json.loads(stdout)

            return addrs
        except Exception as e:
            logging.warning(f"Exception: {e}")

    def ip_route_del(
        self,
        subnet: Union[IPv4Network, IPv6Network],
        gateway: Union[IPv4Address, IPv6Address],
    ):
        """
        Delete a route on the node.
        :param subnet: The destination subnet
        :type subnet:  IPv4Network or IPv6Network
        :param gateway: The next hop gateway.
        :type gateway: IPv4Address or IPv6Address
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} route del {subnet} via {gateway}", quiet=True)
        except Exception as e:
            logging.warning(f"Failed to del route: {e}")
            raise e

    def ip_addr_add(
        self,
        addr: Union[IPv4Address, IPv6Address],
        subnet: Union[IPv4Network, IPv6Network],
        interface: Interface,
    ):
        """
        Add an IP to an interface on the node.
        :param addr: IP address
        :type addr:  IPv4Address or IPv6Address
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(
                f"{ip_command} addr add {addr}/{subnet.prefixlen} dev {interface.get_device_name()} ",
                quiet=True,
            )
        except Exception as e:
            logging.warning(f"Failed to add addr: {e}")
            raise e

    def ip_addr_del(
        self,
        addr: Union[IPv4Address, IPv6Address],
        subnet: Union[IPv4Network, IPv6Network],
        interface: Interface,
    ):
        """
        Delete an IP to an interface on the node.
        :param addr: IP address
        :type addr:  IPv4Address or IPv6Address
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(
                f"{ip_command} addr del {addr}/{subnet.prefixlen} dev {interface.get_device_name()} ",
                quiet=True,
            )
        except Exception as e:
            logging.warning(f"Failed to del addr: {e}")
            raise e

    def ip_link_up(self, subnet: Union[IPv4Network, IPv6Network], interface: Interface):
        """
        Bring up a link on an interface on the node.
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """

        if interface == None:
            return

        try:
            network = interface.get_network()
            if network == None:
                return
            elif network.get_layer() == NSLayer.L3:
                if network.get_type() in [
                    ServiceType.FABNetv6,
                    ServiceType.FABNetv6Ext,
                ]:
                    ip_command = "sudo ip -6"
                elif interface.get_network().get_type() in [
                    ServiceType.FABNetv4,
                    ServiceType.FABNetv4Ext,
                ]:
                    ip_command = "sudo ip"
            else:
                ip_command = "sudo ip"
        except Exception as e:
            logging.warning(f"Failed to down link: {e}")
            return

        try:
            self.execute(
                f"{ip_command} link set dev {interface.get_physical_os_interface()} up",
                quiet=True,
            )
        except Exception as e:
            logging.warning(f"Failed to up link: {e}")
            raise e

        try:
            self.execute(
                f"{ip_command} link set dev {interface.get_device_name()} up",
                quiet=True,
            )
        except Exception as e:
            logging.warning(f"Failed to up link: {e}")
            raise e

    def ip_link_down(
        self, subnet: Union[IPv4Network, IPv6Network], interface: Interface
    ):
        """
        Bring down a link on an interface on the node.
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        try:
            if interface.get_network().get_layer() == NSLayer.L3:
                if interface.get_network().get_type() in [
                    ServiceType.FABNetv6,
                    ServiceType.FABNetv6Ext,
                ]:
                    ip_command = "sudo ip -6"
                elif interface.get_network().get_type() in [
                    ServiceType.FABNetv4,
                    ServiceType.FABNetv4Ext,
                ]:
                    ip_command = "sudo ip"
            else:
                ip_command = "sudo ip"
        except Exception as e:
            # logging.warning(f"Failed to down link: {e}")
            return

        try:
            self.execute(
                f"{ip_command} link set dev {interface.get_device_name()} down",
                quiet=True,
            )
        except Exception as e:
            logging.warning(f"Failed to down link: {e}")
            raise e

    def set_ip_os_interface(
        self,
        os_iface: str = None,
        vlan: str = None,
        ip: str = None,
        cidr: str = None,
        mtu: str = None,
    ):
        """
        Depricated
        """
        # TODO: Add docstring after doc networking classes
        if cidr:
            cidr = str(cidr)
        if mtu:
            mtu = str(mtu)

        if self.validIPAddress(ip) == "IPv4":
            ip_command = "sudo ip"
        elif self.validIPAddress(ip) == "IPv6":
            ip_command = "sudo ip -6"
        else:
            raise Exception(f"Invalid IP {ip}. IP must be vaild IPv4 or IPv6 string.")

        # Bring up base iface
        logging.debug(
            f"{self.get_name()}->set_ip_os_interface: os_iface {os_iface}, vlan {vlan}, ip {ip}, cidr {cidr}, mtu {mtu}"
        )
        command = f"{ip_command} link set dev {os_iface} up"

        if mtu is not None:
            command += f" mtu {mtu}"
        stdout, stderr = self.execute(command, quiet=True)

        # config vlan iface
        if vlan is not None:
            # create vlan iface
            command = f"{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}"
            stdout, stderr = self.execute(command, quiet=True)

            # bring up vlan iface
            os_iface = f"{os_iface}.{vlan}"
            command = f"{ip_command} link set dev {os_iface} up"
            if mtu != None:
                command += f" mtu {mtu}"
            stdout, stderr = self.execute(command, quiet=True)

        if ip is not None and cidr is not None:
            # Set ip
            command = f"{ip_command} addr add {ip}/{cidr} dev {os_iface}"
            stdout, stderr = self.execute(command, quiet=True)

        stdout, stderr = self.execute(command, quiet=True)

    def clear_all_ifaces(self):
        """
        Flush all interfaces and delete VLAN os interfaces
        """
        # TODO: Add docstring after doc networking classes
        self.remove_all_vlan_os_interfaces()
        self.flush_all_os_interfaces()

    def remove_all_vlan_os_interfaces(self):
        """
        Delete all VLAN os interfaces
        """
        # TODO: Add docstring after doc networking classes
        management_os_iface = self.get_management_os_interface()

        stdout, stderr = self.execute("sudo ip -j addr list", quiet=True)
        stdout_json = json.loads(stdout)
        dataplane_devs = []
        for i in stdout_json:
            if i["ifname"] == management_os_iface or i["ifname"] == "lo":
                stdout_json.remove(i)
                continue

            # If iface is vlan linked to base iface
            if "link" in i.keys():
                self.remove_vlan_os_interface(os_iface=i["ifname"])

    def remove_vlan_os_interface(self, os_iface: str = None):
        """
        Remove one VLAN OS interface
        """
        # TODO: Add docstring after doc networking classes
        command = f"sudo ip -j addr show {os_iface}"
        stdout, stderr = self.execute(command, quiet=True)
        try:
            [stdout_json] = json.loads(stdout)
        except Exception as e:
            logging.warning(f"os_iface: {os_iface}, stdout: {stdout}, stderr: {stderr}")
            raise e

        link = stdout_json["link"]

        command = f"sudo ip link del link {link} name {os_iface}"
        stdout, stderr = self.execute(command, quiet=True)

    def add_vlan_os_interface(
        self,
        os_iface: str = None,
        vlan: str = None,
        ip: str = None,
        cidr: str = None,
        mtu: str = None,
        interface: str = None,
    ):
        """
        Depricated
        """
        # TODO: Add docstring after doc networking classes

        if vlan:
            vlan = str(vlan)
        if cidr:
            cidr = str(cidr)
        if mtu:
            mtu = str(mtu)

        try:
            gateway = None
            if interface.get_network().get_layer() == NSLayer.L3:
                if interface.get_network().get_type() in [
                    ServiceType.FABNetv6,
                    ServiceType.FABNetv6Ext,
                ]:
                    ip_command = "sudo ip -6"
                elif interface.get_network().get_type() in [
                    ServiceType.FABNetv4,
                    ServiceType.FABNetv4Ext,
                ]:
                    ip_command = "sudo ip"
            else:
                ip_command = "sudo ip"
        except Exception as e:
            logging.warning(f"Failed to get network layer and/or type: {e}")
            ip_command = "sudo ip"

        command = f"{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}"
        stdout, stderr = self.execute(command, quiet=True)

        command = f"{ip_command} link set dev {os_iface} up"
        stdout, stderr = self.execute(command, quiet=True)

        command = f"{ip_command} link set dev {os_iface}.{vlan} up"
        stdout, stderr = self.execute(command, quiet=True)

        if ip != None and cidr != None:
            self.set_ip_os_interface(
                os_iface=f"{os_iface}.{vlan}", ip=ip, cidr=cidr, mtu=mtu
            )

    def ping_test(self, dst_ip: str) -> bool:
        """
        Test a ping from the node to a destination IP
        :param dst_ip: destination IP String.
        :type dst_ip: String
        """
        # TODO: Add docstring after doc networking classes
        logging.debug(f"ping_test: node {self.get_name()}")

        command = f"ping -c 1 {dst_ip}  2>&1 > /dev/null && echo Success"
        stdout, stderr = self.execute(command, quiet=True)
        if stdout.replace("\n", "") == "Success":
            return True
        else:
            return False

    def get_storage(self, name: str) -> Component:
        """
        Gets a particular storage associated with this node.
        :param name: the name of the storage
        :type name: String
        :raise Exception: if storage not found by name
        :return: the storage on the FABRIC node
        :rtype: Component
        """
        try:
            return Component(self, self.get_fim_node().components[name])
        except Exception as e:
            logging.error(e, exc_info=True)
            raise Exception(f"Storage not found: {name}")

    def add_storage(self, name: str, auto_mount: bool = False) -> Component:
        """
        Creates a new FABRIC Storage component and attaches it to the Node
        :param name: Name of the Storage volume created for the project outside the scope of the Slice
        :param auto_mount: Mount the storage volume
        :rtype: Component
        """
        return Component.new_storage(node=self, name=name, auto_mount=auto_mount)

    def get_fim(self):
        return self.get_fim_node()

    def set_user_data(self, user_data: dict):
        self.get_fim().set_property(
            pname="user_data", pval=UserData(json.dumps(user_data))
        )

    def get_user_data(self):
        try:
            return json.loads(str(self.get_fim().get_property(pname="user_data")))
        except:
            return {}

    def delete(self):
        for component in self.get_components():
            component.delete()

        self.get_slice().get_fim_topology().remove_node(name=self.get_name())

    def init_fablib_data(self):
        fablib_data = {
            "instantiated": "False",
            "run_update_commands": "False",
            "post_boot_commands": [],
            "post_update_commands": [],
        }
        self.set_fablib_data(fablib_data)

    def get_fablib_data(self):
        try:
            return self.get_user_data()["fablib_data"]
        except:
            return {}

    def set_fablib_data(self, fablib_data: dict):
        user_data = self.get_user_data()
        user_data["fablib_data"] = fablib_data
        self.set_user_data(user_data)

    def add_route(
        self,
        subnet: IPv4Network or IPv6Network,
        next_hop: IPv4Address or IPv6Address or NetworkService,
    ):
        if type(next_hop) == NetworkService:
            next_hop = next_hop.get_name()

        fablib_data = self.get_fablib_data()
        if "routes" not in fablib_data:
            fablib_data["routes"] = []
        fablib_data["routes"].append({"subnet": str(subnet), "next_hop": str(next_hop)})
        self.set_fablib_data(fablib_data)

    def add_post_update_command(self, command: str):
        fablib_data = self.get_fablib_data()
        if "post_update_commands" not in fablib_data:
            fablib_data["post_update_commands"] = []

        fablib_data["post_update_commands"].append(command)
        self.set_fablib_data(fablib_data)

    def get_post_update_commands(self):
        fablib_data = self.get_fablib_data()

        if "post_update_commands" in fablib_data:
            return fablib_data["post_update_commands"]
        else:
            return []

    def add_post_boot_upload_directory(
        self, local_directory_path: str, remote_directory_path: str = "."
    ):
        fablib_data = self.get_fablib_data()
        if "post_boot_tasks" not in fablib_data:
            fablib_data["post_boot_tasks"] = []
        fablib_data["post_boot_tasks"].append(
            ("upload_directory", local_directory_path, remote_directory_path)
        )
        self.set_fablib_data(fablib_data)

    def add_post_boot_upload_file(
        self, local_file_path: str, remote_file_path: str = "."
    ):
        fablib_data = self.get_fablib_data()
        if "post_boot_tasks" not in fablib_data:
            fablib_data["post_boot_tasks"] = []
        fablib_data["post_boot_tasks"].append(
            ("upload_file", local_file_path, remote_file_path)
        )
        self.set_fablib_data(fablib_data)

    def add_post_boot_execute(self, command: str):
        fablib_data = self.get_fablib_data()
        if "post_boot_tasks" not in fablib_data:
            fablib_data["post_boot_tasks"] = []
        fablib_data["post_boot_tasks"].append(("execute", command))
        self.set_fablib_data(fablib_data)

    def post_boot_tasks(self):
        fablib_data = self.get_fablib_data()

        if "post_boot_tasks" in fablib_data:
            return fablib_data["post_boot_tasks"]
        else:
            return []

    def get_routes(self):
        try:
            return self.get_fablib_data()["routes"]
        except Exception as e:
            return []

    def config_routes(self):
        routes = self.get_routes()

        for route in routes:
            try:
                next_hop = ipaddress.ip_address(route["next_hop"])
            except Exception as e:
                net_name = route["next_hop"].split(".")[0]
                # funct = getattr(NetworkService,funct_name)
                # next_hop = funct(self.get_slice().get_network(net_name))
                next_hop = (
                    self.get_slice().get_network(name=str(net_name)).get_gateway()
                )
                # next_hop = self.get_slice().get_network(name=str(route['next_hop'])).get_gateway()

            try:
                subnet = ipaddress.ip_network(route["subnet"])
            except Exception as e:
                net_name = route["subnet"].split(".")[0]
                subnet = self.get_slice().get_network(name=str(net_name)).get_subnet()

            # print(f"subnet: {subnet} ({type(subnet)}, next_hop: {next_hop} ({type(next_hop)}")

            self.ip_route_add(subnet=ipaddress.ip_network(subnet), gateway=next_hop)

    def run_post_boot_tasks(self, log_dir: str = "."):
        logging.debug(f"run_post_boot_tasks: {self.get_name()}")
        fablib_data = self.get_fablib_data()
        if "post_boot_tasks" in fablib_data:
            commands = fablib_data["post_boot_tasks"]
        else:
            commands = []

        logging.debug(f"run_post_boot_tasks: commands: {commands}")

        for command in commands:
            logging.debug(f"run_post_boot_tasks: command: {command}")

            if command[0] == "execute":
                self.execute(
                    self.render_template(command[1]),
                    quiet=True,
                    output_file=f"{log_dir}/{self.get_name()}.log",
                )
            elif command[0] == "upload_file":
                logging.debug(f"run_post_boot_tasks: upload_file: {command}")

                rtnval = self.upload_file(command[1], command[2])
                logging.debug(f"run_post_boot_tasks: upload_file rtnval: {rtnval}")

            elif command[0] == "upload_directory":
                logging.debug(f"run_post_boot_tasks: upload_directory: {command}")

                rtnval = self.upload_directory(command[1], command[2])
                logging.debug(f"run_post_boot_tasks: upload_directory rtnval: {rtnval}")

            else:
                logging.error(f"Invalid post boot command: {command}")

    def run_post_update_commands(self, log_dir: str = "."):
        fablib_data = self.get_fablib_data()
        if "post_update_commands" in fablib_data:
            commands = fablib_data["post_update_commands"]
        else:
            commands = []

        for command in commands:
            self.execute(
                command, quiet=True, output_file=f"{log_dir}/{self.get_name()}.log"
            )

    def is_instantiated(self):
        fablib_data = self.get_fablib_data()
        if "instantiated" not in fablib_data:
            logging.debug(
                f"is_instantiated False, {self.get_name()}, fablib_data['instantiated']: does not exist"
            )
            return False

        if fablib_data["instantiated"] == "True":
            logging.debug(
                f"is_instantiated True, {self.get_name()}, fablib_data['instantiated']: {fablib_data['instantiated']}"
            )
            return True
        else:
            logging.debug(
                f"is_instantiated False, {self.get_name()}, fablib_data['instantiated']: {fablib_data['instantiated']}"
            )
            return False

    def set_instantiated(self, instantiated: bool = True):
        fablib_data = self.get_fablib_data()
        fablib_data["instantiated"] = str(instantiated)
        self.set_fablib_data(fablib_data)

    def run_update_commands(self):
        fablib_data = self.get_fablib_data()
        if fablib_data["run_update_commands"] == "True":
            return True
        else:
            return False

    def set_run_update_commands(self, run_update_commands: bool = True):
        fablib_data = self.get_fablib_data()
        fablib_data["run_update_commands"] = str(run_update_commands)
        self.set_fablib_data(fablib_data)

    def config(self, log_dir="."):
        self.execute(f"sudo hostnamectl set-hostname '{self.get_name()}'", quiet=True)

        for iface in self.get_interfaces():
            iface.config()
        self.config_routes()

        if not self.is_instantiated():
            self.set_instantiated(True)
            self.run_post_boot_tasks()

        if self.run_update_commands():
            self.run_post_update_commands()

        return "Done"

    def add_fabnet(
        self, name="FABNET", net_type="IPv4", nic_type="NIC_Basic", routes=None
    ):
        site = self.get_site()

        net_name = f"{name}_{net_type}_{site}"

        net = self.get_slice().get_network(net_name)
        if not net:
            net = self.get_slice().add_l3network(name=net_name, type=net_type)

        # Add ccontrol plane network to node1
        iface = self.add_component(
            model=nic_type, name=f"{net_name}_nic"
        ).get_interfaces()[0]
        net.add_interface(iface)
        iface.set_mode("auto")

        if routes:
            for route in routes:
                self.add_route(subnet=route, next_hop=net.get_gateway())
        else:
            if net_type == "IPv4":
                self.add_route(
                    subnet=self.get_fablib_manager().FABNETV4_SUBNET,
                    next_hop=net.get_gateway(),
                )
            elif net_type == "IPv6":
                self.add_route(
                    subnet=self.get_fablib_manager().FABNETV6_SUBNET,
                    next_hop=net.get_gateway(),
                )
