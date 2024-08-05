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
Methods to work with FABRIC `nodes`_.

.. _`nodes`: https://learn.fabric-testbed.net/knowledge-base/glossary/#node

You would add a node and operate on it like so::

    from fabrictestbed_extensions.fablib.fablib import FablibManager

    fablib = FablibManager()

    slice = fablib.new_slice(name="MySlice")
    node = slice.add_node(name="node1")
    slice.submit();

    node.execute('echo Hello, FABRIC from node `hostname -s`')

    slice.delete()
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import select
import threading
import time
import traceback
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

import jinja2
import paramiko
from fabric_cf.orchestrator.orchestrator_proxy import Status
from fim.user import NodeType
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
    """
    A class for working with FABRIC nodes.
    """

    default_cores = 2
    default_ram = 8
    default_disk = 10
    default_image = "default_rocky_8"

    def __init__(
        self,
        slice: Slice,
        node: FimNode,
        validate: bool = False,
        raise_exception: bool = False,
    ):
        """
        Node constructor, usually invoked by ``Slice.add_node()``.

        :param slice: the fablib slice to have this node on
        :type slice: Slice

        :param node: the FIM node that this Node represents
        :type node: Node

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :param raise_exception: Raise exception in case validation failes
        :type raise_exception: bool

        """
        super().__init__()
        self.fim_node = node
        self.slice = slice
        self.host = None
        self.ip_addr_list_json = None
        self.validate = validate
        self.raise_exception = raise_exception
        self.node_type = NodeType.VM

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
        """
        Get a reference to :py:class:`.FablibManager`.
        """
        return self.slice.get_fablib_manager()

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the
        node.

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
        Gets the node SM sliver.

        :note: Not intended as API call.

        :return: SM sliver for the node
        :rtype: Sliver
        """
        return self.sliver

    @staticmethod
    def new_node(
        slice: Slice = None,
        name: str = None,
        site: str = None,
        avoid: List[str] = [],
        validate: bool = False,
        raise_exception: bool = False,
    ):
        """
        Not intended for API call.  See: Slice.add_node()

        Creates a new FABRIC node and returns a fablib node with the
        new node.

        :param slice: the fablib slice to build the new node on
        :type slice: Slice

        :param name: the name of the new node
        :type name: str

        :param site: the name of the site to build the node on
        :type site: str

        :param avoid: a list of node names to avoid
        :type avoid: List[str]

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :param raise_exception: Raise exception in case of failure
        :type raise_exception: bool

        :return: a new fablib node
        :rtype: Node
        """
        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(
                avoid=avoid,
            )

        logging.info(f"Adding node: {name}, slice: {slice.get_name()}, site: {site}")
        node = Node(
            slice,
            slice.topology.add_node(name=name, site=site),
            validate=validate,
            raise_exception=raise_exception,
        )
        node.set_capacities(
            cores=Node.default_cores, ram=Node.default_ram, disk=Node.default_disk
        )
        node.set_image(Node.default_image)

        node.init_fablib_data()

        return node

    @staticmethod
    def get_node(slice: Slice = None, node=None):
        """
        Returns a new fablib node using existing FABRIC resources.

        :note: Not intended for API call.

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
        Returns the node attributes as a JSON string

        :return: slice attributes as JSON string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_name_dict():
        """
        Return mappings from non-pretty names to pretty names.

        Pretty names are in table headers.
        """
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

    def get_template_context(self, skip: List[str] = ["ssh_command"]):
        return self.get_slice().get_template_context(self, skip=skip)

    def render_template(self, input_string, skip: List[str] = ["ssh_command"]):
        environment = jinja2.Environment()
        # environment.json_encoder = json.JSONEncoder(ensure_ascii=False)
        template = environment.from_string(input_string)
        output_string = template.render(self.get_template_context(skip=skip))

        return output_string

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Show a table containing the current node attributes.

        There are several output options: ``"text"``, ``"pandas"``,
        and ``"json"`` that determine the format of the output that is
        returned and (optionally) displayed/printed.

        :param output: output format.  Options are:

                - ``"text"``: string formatted with tabular

                - ``"pandas"``: pandas dataframe

                - ``"json"``: string in json format

        :type output: str

        :param fields: List of fields to show.  JSON output will
            include all available fields.
        :type fields: List[str]

        :param quiet: True to specify printing/display
        :type quiet: bool

        :param colors: True to specify state colors for pandas output
        :type colors: bool

        :return: table in format specified by output parameter
        :rtype: Object

        Here's an example of ``fields``::

            fields=['Name','State']
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

        There are several output options: ``"text"``, ``"pandas"``,
        and ``"json"`` that determine the format of the output that is
        returned and (optionally) displayed/printed.

        :param output: output format.  Output can be one of:

                - ``"text"``: string formatted with tabular

                - ``"pandas"``: pandas dataframe

                - ``"json"``: string in json format

        :type output: str

        :param fields: list of fields (table columns) to show.  JSON
            output will include all available fields/columns.
        :type fields: List[str]

        :param quiet: True to specify printing/display
        :type quiet: bool

        :param filter_function: A lambda function to filter data by
            field values.

        :type filter_function: lambda

        :return: table in format specified by output parameter
        :rtype: Object


        Here's an example of ``fields``::

            fields=['Name','Model']

        Here's an example of ``filter_function``::

            filter_function=lambda s: s['Model'] == 'NIC_Basic'
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

        There are several output options: ``"text"``, ``"pandas"``,
        and ``"json"`` that determine the format of the output that is
        returned and (optionally) displayed/printed.

        :param output: Output format.  Options are:

                - ``"text"``: string formatted with tabular

                - ``"pandas"``: pandas dataframe

                - ``"json"``: string in json format

        :type output: str

        :param fields: List of fields (table columns) to show.  JSON
            output will include all available fields/columns.
        :type fields: List[str]

        :param quiet: True to specify printing/display
        :type quiet: bool

        :param filter_function: A lambda function to filter data by
            field values.
        :type filter_function: lambda

        :return: table in format specified by output parameter
        :rtype: Object

        Example of ``fields``::

            fields=['Name','MAC']

        Example of ``filter_function``::

            filter_function=lambda s: s['Node'] == 'Node1'
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
        Lists all the networks attached to the nodes with their
        attributes.

        There are several output options: ``"text"``, ``"pandas"``,
        and ``"json"`` that determine the format of the output that is
        returned and (optionally) displayed/printed.

        :param output: Output format.  Options are:

                - ``"text"``: string formatted with tabular

                - ``"pandas"``: pandas dataframe

                - ``"json"``: string in JSON format

        :type output: str

        :param fields: List of fields (table columns) to show.  JSON
            output will include all available fields/columns.
        :type fields: List[str]

        :param quiet: True to specify printing/display
        :type quiet: bool

        :param filter_function: A lambda function to filter data by
            field values.
        :type filter_function: lambda

        :param pretty_names: Use "nicer" names in column headers.
            Default is ``True``.
        :type pretty_names: bool

        :return: table in format specified by output parameter
        :rtype: Object

        Example of ``fields``::

            fields=['Name','Type']

        Example of ``filter_function``::

            filter_function=lambda s: s['Type'] == 'FABNetv4'
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

        return self.get_slice().list_networks(
            fields=fields,
            output=output,
            quiet=quiet,
            filter_function=combined_filter_function,
            pretty_names=pretty_names,
        )

    def get_networks(self):
        """
        Get a list of networks attached to the node.
        """
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
        Sets this fablib node's username

        :note: Not intended as an API call.

        :param username: Optional username parameter.  The username
            likely should be picked to match the image type.
        """
        if username is not None:
            self.username = username
        elif "default_centos9_stream" == self.get_image():
            self.username = "cloud-user"
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
        Sets the image information of this fablib node on the FABRIC
        node.

        :param image: the image reference to set
        :type image: String

        :param username: the username of this fablib node.  Currently
            unused.
        :type username: String

        :param image_type: the image type to set
        :type image_type: String
        """
        self.get_fim_node().set_properties(image_type=image_type, image_ref=image)
        self.set_username(username=username)

    def set_host(self, host_name: str = None):
        """
        Sets the hostname of this fablib node on the FABRIC node.

        :param host_name: the hostname.  example:
            host_name='renc-w2.fabric-testbed.net'
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
        Sets the site of this fablib node on FABRIC.

        :param site: the site
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

    def get_instance_name(self) -> str or None:
        """
        Gets the instance name of the FABRIC node.

        :return: the instance name of the node
        :rtype: String
        """
        try:
            return self.get_fim_node().get_property(pname="label_allocations").instance
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

    def get_requested_cores(self) -> int or None:
        """
        Gets the requested number of cores on the FABRIC node.

        :return: the requested number of cores on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname="capacities").core
        except:
            return 0

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

    def get_requested_ram(self) -> int or None:
        """
        Gets the requested amount of RAM on the FABRIC node.

        :return: the requested amount of RAM on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname="capacities").ram
        except:
            return 0

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

    def get_requested_disk(self) -> int or None:
        """
        Gets the amount of disk space on the FABRIC node.

        :return: the amount of disk space on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname="capacities").disk
        except:
            return 0

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
            label_allocations = self.get_fim_node().get_property(
                pname="label_allocations"
            )
            labels = self.get_fim_node().get_property(pname="labels")
            if label_allocations:
                return label_allocations.instance_parent
            if labels:
                return labels.instance_parent
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

    def get_interfaces(self, include_subs: bool = True) -> List[Interface] or None:
        """
        Gets a list of the interfaces associated with the FABRIC node.

        :param include_subs: Flag indicating if sub interfaces should be included
        :type include_subs: bool

        :return: a list of interfaces on the node
        :rtype: List[Interface]
        """
        interfaces = []
        for component in self.get_components():
            for interface in component.get_interfaces(include_subs=include_subs):
                interfaces.append(interface)

        return interfaces

    def get_interface(
        self, name: str = None, network_name: str = None
    ) -> Interface or None:
        """
        Gets a particular interface associated with a FABRIC node.
        Accepts either the interface name or a network_name.  If a
        network name is used this method will return the interface on
        the node that is connected to the network specified.  If a
        name and network_name are both used, the interface name will
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

        Important!  Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the public key on the node
        :rtype: String
        """
        return self.get_slice().get_slice_public_key()

    def get_public_key_file(self) -> str:
        """
        Gets the public key file path on the fablib node.

        Important!  Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the public key path
        :rtype: String
        """
        return self.get_slice().get_slice_public_key_file()

    def get_private_key(self) -> str:
        """
        Gets the private key on the fablib node.

        Important!  Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the private key on the node
        :rtype: String
        """
        return self.get_slice().get_slice_private_key()

    def get_private_key_file(self) -> str:
        """
        Gets the private key file path on the fablib slice.

        Important!  Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the private key path
        :rtype: String
        """
        return self.get_slice().get_slice_private_key_file()

    def get_private_key_passphrase(self) -> str:
        """
        Gets the private key passphrase on the FABLIB slice.

        Important!  Slice key management is underdevelopment and this
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
        Example models include:

        - NIC_Basic: A single port 100 Gbps SR-IOV Virtual
          Function on a Mellanox ConnectX-6

        - NIC_ConnectX_5: A dual port 25 Gbps Mellanox ConnectX-5

        - NIC_ConnectX_6: A dual port 100 Gbps Mellanox ConnectX-6

        - NVME_P4510: NVMe Storage Device

        - GPU_TeslaT4: Tesla T4 GPU

        - GPU_RTX6000: RTX6000 GPU

        - GPU_A30: A30 GPU

        - GPU_A40: A40 GPU

        - FPGA_Xilinx_U280: Xilinx U280 FPGA card

        :param model: the name of the component model to add
        :type model: String

        :param name: the name of the new component
        :type name: String

        :return: the new component
        :rtype: Component
        """
        component = Component.new_component(
            node=self, model=model, name=name, user_data=user_data
        )
        if self.validate:
            status, error = self.get_fablib_manager().validate_node(node=self)
            if not status:
                component.delete()
                component = None
                logging.warning(error)
                if self.raise_exception:
                    raise ValueError(error)
        return component

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
        Gets an SSH command used to access this node from a terminal.

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
                self.get_fablib_manager().get_ssh_command_line(),
                skip=["ssh_command", "interfaces"],
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
        """
        Get SSH pubkey, for internal use.

        :return: an SSH pubkey.
        :rtype: paramiko.PKey
        """
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

        The function uses paramiko to ssh to the FABRIC node and
        execute an arbitrary shell command.

        :param command: the command to run
        :type command: str

        :param retry: the number of times to retry SSH upon failure
        :type retry: int

        :param retry_interval: the number of seconds to wait before
            retrying SSH upon failure
        :type retry_interval: int

        :param username: username
        :type username: str

        :param private_key_file: path to private key file
        :type private_key_file: str

        :param private_key_passphrase: pass phrase
        :type private_key_passphrase: str

        :param output_file: path to a file where the stdout/stderr
            will be written.  None for no file output
        :type output_file: List[str]

        :param output: print stdout and stderr to the screen
        :type output: bool

        :param read_timeout: the number of seconds to wait before
            retrying to read from stdout and stderr
        :type read_timeout: int

        :param timeout: the number of seconds to wait before
            terminating the command using the linux timeout command.
            Specifying a timeout encapsulates the command with the
            timeout command for you
        :type timeout: int

        :return: a tuple of (stdout[Sting],stderr[String])
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
        bastion_key_file = self.get_fablib_manager().get_bastion_key_location()

        if username is not None:
            node_username = username
        else:
            node_username = self.username

        if private_key_file is not None:
            node_key_file = private_key_file
        else:
            node_key_file = self.get_private_key_file()

        if private_key_passphrase is not None:
            node_key_passphrase = private_key_passphrase
        else:
            node_key_passphrase = self.get_private_key_passphrase()

        for attempt in range(int(retry)):
            try:
                key = self.get_paramiko_key(
                    private_key_file=node_key_file,
                    get_private_key_passphrase=node_key_passphrase,
                )
                bastion = paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(
                    self.get_fablib_manager().get_bastion_host(),
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
                    f"Exception in node.execute() command: {command} (attempt #{attempt} of {retry}): {e}"
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
        Creates a thread that calls ``node.upload_file()``.

        Results from the thread can be retrieved with by calling
        ``thread.result()``.

        :param local_file_path: the path to the file to upload
        :type local_file_path: str

        :param remote_file_path: the destination path of the file on
            the node
        :type remote_file_path: str

        :param retry: how many times to retry SCP upon failure
        :type retry: int

        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int

        :return: a thread that called ``node.execute()``
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

        :param remote_file_path: the destination path of the file on
            the node
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
                    self.get_fablib_manager().get_bastion_host(),
                    username=self.get_fablib_manager().get_bastion_username(),
                    key_filename=self.get_fablib_manager().get_bastion_key_location(),
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
        """
        Creates a thread that calls node.download_file().  Results
        from the thread can be retrieved with by calling
        thread.result()

        :param local_file_path: the destination path for the remote
            file
        :type local_file_path: str

        :param remote_file_path: the path to the remote file to
            download
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

        :param local_file_path: the destination path for the remote
            file
        :type local_file_path: str

        :param remote_file_path: the path to the remote file to
            download
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
                    self.get_fablib_manager().get_bastion_host(),
                    username=self.get_fablib_manager().get_bastion_username(),
                    key_filename=self.get_fablib_manager().get_bastion_key_location(),
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
        """
        Creates a thread that calls ``Node.upload_directory()``.

        Results from the thread can be retrieved with by calling
        ``thread.result()``.

        :param local_directory_path: the path to the directory to
            upload
        :type local_directory_path: str

        :param remote_directory_path: the destination path of the
            directory on the node
        :type remote_directory_path: str

        :param retry: how many times to retry SCP upon failure
        :type retry: int

        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int

        :return: a thread that called ``node.upload_directory()``
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

        Makes a gzipped tarball of a directory and uploads it to a
        node.  Then unzips and untars the directory at the
        ``remote_directory_path``.

        :param local_directory_path: the path to the directory to
            upload
        :type local_directory_path: str

        :param remote_directory_path: the destination path of the
            directory on the node
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
        """
        Creates a thread that calls node.download_directory.  Results
        from the thread can be retrieved with by calling
        thread.result()

        :param local_directory_path: the path to the directory to
            upload
        :type local_directory_path: str

        :param remote_directory_path: the destination path of the
            directory on the node
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
        Downloads a directory from remote location on the node.  Makes
        a gzipped tarball of a directory and downloads it from a node.
        Then unzips and tars the directory at the local_directory_path

        :param local_directory_path: the path to the directory to
            upload
        :type local_directory_path: str

        :param remote_directory_path: the destination path of the
            directory on the node
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
        Gets the name of the management interface used by the node's
        operating system.

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
        Gets a list of all the dataplane interface names used by the
        node's operating system.

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
        """
        Return the list of IP addresses assciated with this node.

        :param output: Output format; ``"json"`` by default.
        :param update: Setting this to ``True`` will force-update the
            cached list of IP addresses; default is ``False``.

        :returns: When ``output`` is set to ``"json"`` (which is the
                  default), the result of running ``ip -j[son] addr
                  list``, converted to a Python object.  Otherwise the
                  result of ``ip addr list``.
        """
        try:
            if self.ip_addr_list_json is not None and update == False:
                return self.ip_addr_list_json
            else:
                if output == "json":
                    stdout, stderr = self.execute(f"sudo  ip -j addr list", quiet=True)
                    self.ip_addr_list_json = json.loads(stdout)
                    return self.ip_addr_list_json
                else:
                    stdout, stderr = self.execute(f"sudo ip addr list", quiet=True)
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
        :type subnet: IPv4Network or IPv6Network

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
        :type subnet: IPv4Network or IPv6Network

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
        :type addr: IPv4Address or IPv6Address

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
        :type addr: IPv4Address or IPv6Address

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

    def un_manage_interface(self, interface: Interface):
        """
        Mark an interface unmanaged by Network Manager;

        This is needed to be run on rocky* images to avoid the network
        configuration from being overwritten by NetworkManager

        :param interface: the FABlib interface.
        :type interface: Interface
        """

        if interface is None:
            return

        try:
            self.execute(
                f"sudo nmcli dev set {interface.get_physical_os_interface_name()} managed no",
                quiet=True,
            )
        except Exception as e:
            logging.warning(f"Failed to mark interface as unmanaged: {e}")

    def ip_link_up(self, subnet: Union[IPv4Network, IPv6Network], interface: Interface):
        """
        Bring up a link on an interface on the node.

        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network

        :param interface: the FABlib interface.
        :type interface: Interface
        """

        if not interface:
            return

        ip_command = None
        try:
            network = interface.get_network()
            if not network:
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
                f"{ip_command} link set dev {interface.get_physical_os_interface_name()} up",
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
        ip_command = None

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
        Configure IP Address on network interface as seen inside the VM
        :param os_iface: Interface name as seen by the OS such as eth1 etc.
        :type os_iface: String

        :param vlan: Vlan tag
        :type vlan: String

        :param ip: IP address to be assigned to the tagged interface
        :type ip: String

        :param cidr: CIDR associated with IP address
        :type ip: String

        :param mtu: MTU size
        :type mtu: String

        NOTE: This does not add the IP information in the fablib_data
        """
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
        interface: Interface = None,
    ):
        """
        Add VLAN tagged interface for a given interface and set IP address on it

        :param os_iface: Interface name as seen by the OS such as eth1 etc.
        :type os_iface: String

        :param vlan: Vlan tag
        :type vlan: String

        :param ip: IP address to be assigned to the tagged interface
        :type ip: String

        :param cidr: CIDR associated with IP address
        :type ip: String

        :param mtu: MTU size
        :type mtu: String

        :param interface: Interface for which tagged interface has to be added
        :type interface: Interface
        """
        if vlan:
            vlan = str(vlan)
        if cidr:
            cidr = str(cidr)
        if mtu:
            mtu = str(mtu)

        ip_command = "sudo ip"
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
            logging.warning(f"Failed to get network layer and/or type: {e}")
            ip_command = "sudo ip"

        command = f"{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}"
        stdout, stderr = self.execute(command, quiet=True)

        command = f"{ip_command} link set dev {os_iface} up"
        stdout, stderr = self.execute(command, quiet=True)

        command = f"{ip_command} link set dev {os_iface}.{vlan} up"
        stdout, stderr = self.execute(command, quiet=True)

        if ip and cidr:
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
        Creates a new FABRIC Storage component and attaches it to the
        Node

        :param name: Name of the Storage volume created for the
            project outside the scope of the Slice
        :param auto_mount: Mount the storage volume

        :rtype: Component
        """
        return Component.new_storage(node=self, name=name, auto_mount=auto_mount)

    def get_fim(self):
        """
        Get FABRIC Information Model (fim) object for the node.
        """
        return self.get_fim_node()

    def set_user_data(self, user_data: dict):
        """
        Set user data.

        :param user_data: a `dict`.
        """
        self.get_fim().set_property(
            pname="user_data", pval=UserData(json.dumps(user_data))
        )

    def get_user_data(self):
        """
        Get user data.
        """
        try:
            return json.loads(str(self.get_fim().get_property(pname="user_data")))
        except:
            return {}

    def delete(self):
        """
        Remove the node from the slice. All components and interfaces associated with
        the Node are removed from the Slice.
        """
        for component in self.get_components():
            component.delete()

        self.get_slice().get_fim_topology().remove_node(name=self.get_name())

    def init_fablib_data(self):
        """
        Initialize fablib data.  Called by :py:meth:`new_node()`.
        """
        fablib_data = {
            "instantiated": "False",
            "run_update_commands": "False",
            "post_boot_commands": [],
            "post_update_commands": [],
        }
        self.set_fablib_data(fablib_data)

    def get_fablib_data(self):
        """
        Get fablib data. Usually used internally.
        """
        try:
            return self.get_user_data()["fablib_data"]
        except:
            return {}

    def set_fablib_data(self, fablib_data: dict):
        """
        Set fablib data. Usually used internally.
        """
        user_data = self.get_user_data()
        user_data["fablib_data"] = fablib_data
        self.set_user_data(user_data)

    def add_route(
        self,
        subnet: IPv4Network or IPv6Network,
        next_hop: IPv4Address or IPv6Address or NetworkService,
    ):
        """
        Add a route.

        :param subnet: an IPv4 or IPv6 address.

        :type subnet:IPv4Network or IPv6Network.

        :param next_hop: a gateway address (IPv4Address or
            IPv6Address) or a NetworkService.
        :type next_hop: IPv4Address or IPv6Address or NetworkService.
        """
        if type(next_hop) == NetworkService:
            next_hop = next_hop.get_name()

        fablib_data = self.get_fablib_data()
        if "routes" not in fablib_data:
            fablib_data["routes"] = []
        fablib_data["routes"].append({"subnet": str(subnet), "next_hop": str(next_hop)})
        self.set_fablib_data(fablib_data)

    def add_post_update_command(self, command: str):
        """
        Run a command after boot.
        """
        fablib_data = self.get_fablib_data()
        if "post_update_commands" not in fablib_data:
            fablib_data["post_update_commands"] = []

        fablib_data["post_update_commands"].append(command)
        self.set_fablib_data(fablib_data)

    def get_post_update_commands(self):
        """
        Get the list of commands that are to be run after boot.
        """
        fablib_data = self.get_fablib_data()

        if "post_update_commands" in fablib_data:
            return fablib_data["post_update_commands"]
        else:
            return []

    def add_post_boot_upload_directory(
        self, local_directory_path: str, remote_directory_path: str = "."
    ):
        """
        Upload a directory to the node after boot.

        :param local_directory_path: local directory.
        :type local_directory_path: str

        :param remote_directory_path: directory on the node.
        :type remote_directory_path: str
        """
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
        """
        Upload a file to the node after boot.

        :param local_file_path: path to file on local filesystem.
        :type local_file_path: str

        :param remote_file_path: path to file on the node.
        :type remote_file_path: str
        """
        fablib_data = self.get_fablib_data()
        if "post_boot_tasks" not in fablib_data:
            fablib_data["post_boot_tasks"] = []
        fablib_data["post_boot_tasks"].append(
            ("upload_file", local_file_path, remote_file_path)
        )
        self.set_fablib_data(fablib_data)

    def add_post_boot_execute(self, command: str):
        """
        Execute a command on the node after boot.

        :param command: command to be executed on the node.
        :type command: str
        """
        fablib_data = self.get_fablib_data()
        if "post_boot_tasks" not in fablib_data:
            fablib_data["post_boot_tasks"] = []
        fablib_data["post_boot_tasks"].append(("execute", command))
        self.set_fablib_data(fablib_data)

    def post_boot_tasks(self):
        """
        Get the list of tasks to be performed on this node after boot.
        """
        fablib_data = self.get_fablib_data()

        if "post_boot_tasks" in fablib_data:
            return fablib_data["post_boot_tasks"]
        else:
            return []

    def get_routes(self):
        """
        .. warning::

            This method is for fablib internal use, and will be made private in the future.
        """
        try:
            return self.get_fablib_data()["routes"]
        except Exception as e:
            return []

    def config_routes(self):
        """
        .. warning::

            This method is for fablib internal use, and will be made private in the future.
        """
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
        """
        Run post-boot tasks.  Called by :py:meth:`config()`.

        Post-boot tasks are list of commands associated with
        `post_boot_tasks` in fablib data.
        """
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
        """
        Run post-update commands.  Called by :py:meth:`config()`.

        Post-update commands are list of commands associated with
        `post_update_commands` in fablib data.
        """
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
        """
        Returns `True` if the node has been instantiated.
        """
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
        """
        Mark node as instantiated. Called by :py:meth:`config()`.
        """
        fablib_data = self.get_fablib_data()
        fablib_data["instantiated"] = str(instantiated)
        self.set_fablib_data(fablib_data)

    def run_update_commands(self):
        """
        Returns `True` if `run_update_commands` flag is set.
        """
        fablib_data = self.get_fablib_data()
        if fablib_data["run_update_commands"] == "True":
            return True
        else:
            return False

    def set_run_update_commands(self, run_update_commands: bool = True):
        """
        Set `run_update_commands` flag.
        """
        fablib_data = self.get_fablib_data()
        fablib_data["run_update_commands"] = str(run_update_commands)
        self.set_fablib_data(fablib_data)

    def config(self, log_dir="."):
        """
        Run configuration tasks for this node.

        .. note ::

            Use this method in order to re-apply configuration to a
            rebooted node.  Normally this method is invoked by
            ``Slice.submit()`` or ``Slice.modify()``.

        Configuration tasks include:

            - Setting hostname.

            - Configuring interfaces.

            - Configuring routes.

            - Running post-boot tasks added by
              ``add_post_boot_execute()``,
              ``add_post_boot_upload_file()``, and
              ``add_post_boot_upload_directory()``.

            - Running post-update commands added by
              ``add_post_update_command()``.
        """
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
        """
        Add a simple layer 3 network to this node.

        :param name: a name for the network.  Default is ``"FABNET"``.
        :param net_type: Network type, ``"IPv4"`` or ``"IPv6"``.
        :param nic_type: a NIC type.  Default is ``"NIC_Basic"``.
        :param routes: a list of routes to add.  Default is ``None``.
        """
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

    def poa(
        self,
        operation: str,
        vcpu_cpu_map: List[Dict[str, str]] = None,
        node_set: List[str] = None,
        keys: List[Dict[str, str]] = None,
    ) -> Union[Dict, str]:
        """
        Perform operation action on a VM; an action which is triggered by CF via the Aggregate

        :param operation: operation to be performed
        :param vcpu_cpu_map: map virtual cpu to host cpu map
        :param node_set: list of numa nodes
        :param keys: list of ssh keys

        :raise Exception: in case of failure

        :return: State of POA or Dictionary containing the info, in
                 case of INFO POAs
        """
        retry = 20

        status, poa_info = (
            self.get_fablib_manager()
            .get_slice_manager()
            .poa(
                sliver_id=self.get_reservation_id(),
                operation=operation,
                vcpu_cpu_map=vcpu_cpu_map,
                node_set=node_set,
                keys=keys,
            )
        )
        logger = logging.getLogger()
        if status != Status.OK:
            raise Exception(f"Failed to issue POA - {operation} Error {poa_info}")

        logger.info(
            f"POA {poa_info[0].poa_id}/{operation} submitted for {self.get_reservation_id()}/{self.get_name()}"
        )

        poa_state = "Nascent"
        poa_info_status = None
        attempt = 0
        states = ["Success", "Failed"]
        while poa_state not in states and attempt < retry:
            status, poa_info_status = (
                self.get_fablib_manager()
                .get_slice_manager()
                .get_poas(poa_id=poa_info[0].poa_id)
            )
            attempt += 1
            if status != Status.OK:
                raise Exception(
                    f"Failed to get POA Status - {poa_info[0].poa_id}/{operation} Error {poa_info_status}"
                )
            poa_state = poa_info_status[0].state
            logger.info(
                f"Waiting for POA {poa_info[0].poa_id}/{operation} to complete! "
                f"Checking POA Status (attempt #{attempt} of {retry}) current state: {poa_state}"
            )
            if poa_state in states:
                break
            time.sleep(10)

        if poa_info_status[0].state == "Failed":
            raise Exception(
                f"POA - {poa_info[0].poa_id}/{operation} failed with error: - {poa_info_status[0].error}"
            )

        if poa_info_status[0].info.get(operation) is not None:
            return poa_info_status[0].info.get(operation)
        else:
            return poa_info_status[0].state

    def get_cpu_info(self) -> dict:
        """
        Get CPU Information for the Node and the host on which the VM is running

        :return: cpu info dict
        """
        """
        Host INFO looks like:
        {'Node 0': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 1': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 2': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 3': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 4': {'Heap': '0', 'Huge': '0', 'Private': '1', 'Stack': '0', 'Total': '1'},
        'Node 5': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 6': {'Heap': '6', 'Huge': '0', 'Private': '32812', 'Stack': '0', 'Total': '32817'},
        'Node 7': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Total': {'Heap': '6', 'Huge': '0', 'Private': '32813', 'Stack': '0', 'Total': '32818'}}

        VM INFO looks like:
        In this example below, no CPU pinning has been applied so CPU Affinity lists all the CPUs
        After the pinning has been applied, CPU Affinity would show only the pinned CPU
            [{'CPU': '116', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '20.2s', 'State': 'running', 'VCPU': '0'},
        {'CPU': '118', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '9.0s', 'State': 'running', 'VCPU': '1'},
        {'CPU': '117', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '8.9s', 'State': 'running', 'VCPU': '2'},
        {'CPU': '119', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '8.8s', 'State': 'running', 'VCPU': '3'},
        {'CPU': '52', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '0.8s', 'State': 'running', 'VCPU': '4'},
        {'CPU': '88', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '0.4s', 'State': 'running', 'VCPU': '5'},
        {'CPU': '54', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '1.4s', 'State': 'running', 'VCPU': '6'},
        {'CPU': '55', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '0.8s', 'State': 'running', 'VCPU': '7'},
        {'CPU': '116', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '1.1s', 'State': 'running', 'VCPU': '8'},
        {'CPU': '117', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '1.3s', 'State': 'running', 'VCPU': '9'},
        {'CPU': '113', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '0.5s', 'State': 'running', 'VCPU': '10'},
        {'CPU': '119', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '1.4s', 'State': 'running', 'VCPU': '11'},
        {'CPU': '116', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '0.7s', 'State': 'running', 'VCPU': '12'},
        {'CPU': '53', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '2.1s', 'State': 'running', 'VCPU': '13'},
        {'CPU': '117', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '1.3s', 'State': 'running', 'VCPU': '14'},
        {'CPU': '49', 'CPU Affinity': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127', 'CPU time': '0.8s', 'State': 'running', 'VCPU': '15'}]        
        """
        # Get CPU Info for the VM and Host on which VM resides
        cpu_info = self.poa(operation="cpuinfo")
        logging.getLogger().info(f"HOST CPU INFO: {cpu_info.get(self.get_host())}")
        logging.getLogger().info(
            f"Instance CPU INFO: {cpu_info.get(self.get_instance_name())}"
        )
        if cpu_info == "Failed":
            raise Exception("POA Failed to get CPU INFO")
        return cpu_info

    def get_numa_info(self) -> dict:
        """
        Get Numa Information for the Node and the host on which the VM is running

        :return: numa info dict
        """
        """
        Host INFO looks like:
        {'available': '8 nodes (0-7)',
        'node 0': {'cpus': '0 1 2 3 4 5 6 7 64 65 66 67 68 69 70 71', 'free': '18366 MB', 'size': '63794 MB'},
        'node 1': {'cpus': '8 9 10 11 12 13 14 15 72 73 74 75 76 77 78 79', 'free': '61574 MB', 'size': '64466 MB'},
        'node 2': {'cpus': '16 17 18 19 20 21 22 23 80 81 82 83 84 85 86 87', 'free': '654 MB', 'size': '64507 MB'},
        'node 3': {'cpus': '24 25 26 27 28 29 30 31 88 89 90 91 92 93 94 95', 'free': '350 MB', 'size': '64495 MB'},
        'node 4': {'cpus': '32 33 34 35 36 37 38 39 96 97 98 99 100 101 102 103', 'free': '43491 MB', 'size': '64507 MB'},
        'node 5': {'cpus': '40 41 42 43 44 45 46 47 104 105 106 107 108 109 110 111', 'free': '46958 MB', 'size': '64507 MB'},
        'node 6': {'cpus': '48 49 50 51 52 53 54 55 112 113 114 115 116 117 118 119', 'free': '10348 MB', 'size': '64507 MB'},
        'node 7': {'cpus': '56 57 58 59 60 61 62 63 120 121 122 123 124 125 126 127', 'free': '63374 MB', 'size': '64506 MB'}}

        VM INFO looks like:
        {'Node 0': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 1': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 2': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 3': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 4': {'Heap': '0', 'Huge': '0', 'Private': '1', 'Stack': '0', 'Total': '1'},
        'Node 5': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Node 6': {'Heap': '6', 'Huge': '0', 'Private': '32812', 'Stack': '0', 'Total': '32817'},
        'Node 7': {'Heap': '0', 'Huge': '0', 'Private': '0', 'Stack': '0', 'Total': '0'},
        'Total': {'Heap': '6', 'Huge': '0', 'Private': '32813', 'Stack': '0', 'Total': '32818'}}
        """
        # Get Numa Info for the VM and Host on which VM resides
        numa_info = self.poa(operation="numainfo")
        logging.getLogger().info(f"HOST Numa INFO: {numa_info.get(self.get_host())}")
        logging.getLogger().info(
            f"Instance Numa INFO: {numa_info.get(self.get_instance_name())}"
        )
        if numa_info == "Failed":
            raise Exception("POA Failed to get Numa INFO")
        return numa_info

    def pin_cpu(self, component_name: str, cpu_range_to_pin: str = None):
        """
        Pin the cpus for the VM to the numa node associated with the
        component.

        :param component_name: Component Name
        :param cpu_range_to_pin: range of the cpus to pin; example:
            0-1 or 0
        """
        try:
            allocated_cpu_list = list(range(0, self.get_cores()))
            if cpu_range_to_pin is None:
                result_list = allocated_cpu_list
            else:
                start, end = map(int, cpu_range_to_pin.split("-"))
                result_list = list(range(start, end + 1))

                set_cpu = set(allocated_cpu_list)
                if any(item not in set_cpu for item in result_list):
                    raise Exception(
                        f"Requested CPU range outside the Cores allocated {self.get_cores()} to Node"
                    )

            # Get CPU Info for the VM and Host on which VM resides
            cpu_info = self.get_cpu_info()

            pinned_cpus = cpu_info.get(self.get_host()).get("pinned_cpus")

            # Find Numa Node for the NIC
            numa_node = self.get_component(name=component_name).get_numa_node()

            # Find CPUs assigned to the numa node
            numa_cpu_range_str = cpu_info.get(self.get_host()).get(
                f"NUMA node{numa_node} CPU(s):"
            )

            # Determine the CPU range belonging to the Numa Node
            numa_cpu_range = []
            for r in numa_cpu_range_str.split(","):
                start, end = map(int, r.split("-"))
                numa_cpu_range.extend(map(str, range(start, end + 1)))

            # Exclude any Pinned CPUs
            available_cpus = list(set(numa_cpu_range) - set(pinned_cpus))

            number_of_cpus_to_pin = len(result_list)
            number_of_available_cpus = len(available_cpus)

            # Verify Requested CPUs do not exceed Available CPUs
            if number_of_cpus_to_pin > number_of_available_cpus:
                msg = (
                    f"Not enough Host CPUs available to pin! Requested CPUs: {number_of_cpus_to_pin} "
                    f"Available CPUs: {number_of_available_cpus}"
                )

                logging.getLogger().warning(msg)
                number_of_cpus_to_pin = number_of_available_cpus
                if not number_of_cpus_to_pin:
                    raise Exception(msg)

            # Build the VCPU to CPU Mapping
            vcpu_cpu_map = []
            for x in range(number_of_cpus_to_pin):
                temp = {"vcpu": str(result_list[x]), "cpu": str(available_cpus[x])}
                vcpu_cpu_map.append(temp)

            msg = (
                f"Pinning Node: {self.get_name()} CPUs for component: {component_name} to "
                f"Numa Node: {numa_node}"
            )
            logging.getLogger().info(f"{msg}  CPU Map: {vcpu_cpu_map}")
            print(msg)

            # Issue POA
            status = self.poa(operation="cpupin", vcpu_cpu_map=vcpu_cpu_map)
            if status == "Failed":
                raise Exception("POA Failed")
            logging.getLogger().info(
                f"CPU Pinning complete for node: {self.get_name()}"
            )
        except Exception as e:
            logging.getLogger().error(traceback.format_exc())
            logging.getLogger(f"Failed to Pin CPU for node: {self.get_name()} e: {e}")
            raise e

    def os_reboot(self):
        """
        Request Openstack to reboot the VM.
        NOTE: This is not same as rebooting the VM via reboot or init 6 command.
        Instead this is like openstack server reboot.
        """
        status = self.poa(operation="reboot")
        if status == "Failed":
            raise Exception("Failed to reboot the server")
        logging.getLogger().info(f"Node: {self.get_name()} rebooted!")

    def numa_tune(self):
        """
        Pin the memory for the VM to the numa node associated with the components
        """
        try:
            # Get CPU Info for the VM and Host on which VM resides
            numa_info = self.get_numa_info()

            total_available_memory = 0

            numa_nodes = []

            for c in self.get_components():
                # Find Numa Node for the NIC
                numa_node = c.get_numa_node()

                # Skip Numa node if already checked
                if numa_node in numa_nodes:
                    continue

                logging.getLogger().info(
                    f"Numa Node {numa_node} for component: {c.get_name()}"
                )

                # Free Memory for the Numa Node
                numa_memory_free_str = (
                    numa_info.get(self.get_host()).get(f"node {numa_node}").get("free")
                )
                logging.getLogger().info(
                    f"Numa Node {numa_node} free memory: {numa_memory_free_str}"
                )
                numa_memory_free = int(re.search(r"\d+", numa_memory_free_str).group())
                logging.getLogger().info(
                    f"Numa Node {numa_node} free memory: {numa_memory_free}"
                )

                # Memory allocated to VM on the Numa Node
                logging.getLogger().info(
                    f"VM memory: {numa_info.get(self.get_instance_name())}"
                )
                logging.getLogger().info(
                    f"VM memory: {numa_info.get(self.get_instance_name()).get(f'Node {numa_node}')}"
                )
                vm_mem = (
                    numa_info.get(self.get_instance_name())
                    .get(f"Node {numa_node}")
                    .get("Total")
                )
                logging.getLogger().info(f"VM memory: {vm_mem}")

                # Exclude VM memory
                available_memory_on_node = int(numa_memory_free) + int(vm_mem)
                logging.getLogger().info(
                    f"Available memory: {available_memory_on_node}"
                )

                if available_memory_on_node <= 0:
                    continue

                numa_nodes.append(numa_node)

                # Compute the total available Memory
                total_available_memory += available_memory_on_node

            requested_vm_memory = self.get_ram() * 1024

            if requested_vm_memory > total_available_memory:
                raise Exception(
                    f"Cannot numatune VM to Numa Nodes {numa_nodes}; requested memory "
                    f"{requested_vm_memory} exceeds available: {total_available_memory}"
                )

            msg = (
                f"Numa tune Node: {self.get_name()} Memory to Numa  Nodes: {numa_nodes}"
            )
            logging.getLogger().info(msg)
            print(msg)

            # Issue POA
            status = self.poa(operation="numatune", node_set=numa_nodes)
            if status == "Failed":
                logging.getLogger().error(
                    f"Numa tune failed for node: {self.get_name()}"
                )
            else:
                logging.getLogger().info(
                    f"Numa tune complete for node: {self.get_name()}"
                )
        except Exception as e:
            logging.getLogger().error(traceback.format_exc())
            logging.getLogger(f"Failed to Numa tune for node: {self.get_name()} e: {e}")
            raise e

    def add_public_key(
        self,
        *,
        sliver_key_name: str = None,
        email: str = None,
        sliver_public_key: str = None,
    ):
        """
        Add public key to a node;
        - Adds user's portal public key identified by sliver_key_name to the node
        - Adds portal public key identified by sliver_key_name for a user identified by email to the node
        - Add public key from the sliver_public_key to the node

        :param sliver_key_name: Sliver Key Name on the Portal
        :type sliver_key_name: str

        :param email: Email
        :type email: str

        :param sliver_public_key: Public sliver key
        :type sliver_public_key: str

        :raises Exception in case of errors
        """
        self.__ssh_key_helper(
            sliver_key_name=sliver_key_name,
            sliver_public_key=sliver_public_key,
            email=email,
        )

    def remove_public_key(
        self,
        *,
        sliver_key_name: str = None,
        email: str = None,
        sliver_public_key: str = None,
    ):
        """
        Remove public key to a node;
        - Remove user's portal public key identified by sliver_key_name to the node
        - Remove portal public key identified by sliver_key_name for a user identified by email to the node
        - Remove public key from the sliver_public_key to the node

        :param sliver_key_name: Sliver Key Name on the Portal
        :type sliver_key_name: str

        :param email: Email
        :type email: str

        :param sliver_public_key: Public sliver key
        :type sliver_public_key: str

        :raises Exception in case of errors
        """
        self.__ssh_key_helper(
            sliver_key_name=sliver_key_name,
            email=email,
            sliver_public_key=sliver_public_key,
            remove=True,
        )

    def __ssh_key_helper(
        self,
        *,
        sliver_key_name: str = None,
        email: str = None,
        sliver_public_key: str = None,
        remove: bool = False,
    ):
        """
        Add/Remove public key to a node;
        - Adds/Remove user's portal public key identified by sliver_key_name to the node
        - Adds/Remove portal public key identified by sliver_key_name for a user identified by email to the node
        - Add/Remove public key from the sliver_public_key to the node

        :param sliver_key_name: Sliver Key Name on the Portal
        :type sliver_key_name: str

        :param email: Email
        :type email: str

        :param sliver_public_key: Public sliver key
        :type sliver_public_key: str

        :param remove: Flag indicating if the key should be removed
        :type remove: bool

        :raises Exception in case of errors
        """
        if sliver_key_name is None and sliver_public_key is None:
            raise ValueError(
                f"Either sliver_key_name: {sliver_key_name} or "
                f"sliver_public_key_file: {sliver_public_key} must be specified!"
            )

        # Fetch the public key from portal
        if sliver_key_name is not None:
            ssh_keys = (
                self.get_fablib_manager().get_slice_manager().get_ssh_keys(email=email)
            )
            found = None
            if ssh_keys is not None and len(ssh_keys):
                for item in ssh_keys:
                    if sliver_key_name == item["comment"]:
                        found = item
                        break

            if not found:
                raise Exception(f"Sliver key: {sliver_key_name} not found!")
            sliver_public_key = f'{found["ssh_key_type"]} {found["public_key"]}'

        operation = "addkey" if not remove else "removekey"

        key_dict = {"key": sliver_public_key, "comment": f"{operation}-by-poa-fablib"}

        status = self.poa(operation=operation, keys=[key_dict])
        if status == "Failed":
            raise Exception(f"Failed to {operation} the node")
        logging.getLogger().info(
            f"{operation} to the node {self.get_name()} successful!"
        )
        print(f"{operation} to the node {self.get_name()} successful!")
