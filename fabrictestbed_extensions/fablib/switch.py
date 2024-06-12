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
# Author: Komal Thareja (kthare10@renci.org)
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, List

import jinja2
from IPython.core.display_functions import display
from tabulate import tabulate

from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.node import Node

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice

from fabrictestbed.slice_editor import Capacities
from fabrictestbed.slice_editor import Node as FimNode


class Switch(Node):
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
        super(Switch, self).__init__(
            slice=slice, node=node, validate=validate, raise_exception=raise_exception
        )
        self.username = "rare"

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
            ["Site", self.get_site()],
            ["Management IP", self.get_management_ip()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ["SSH Command", self.get_ssh_command()],
        ]

        return tabulate(table)  # , headers=["Property", "Value"])

    @staticmethod
    def new_switch(
        slice: Slice = None,
        name: str = None,
        site: str = None,
        avoid: List[str] = None,
        validate: bool = False,
        raise_exception: bool = False,
    ) -> Switch:
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
        if not avoid:
            avoid = []

        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(
                avoid=avoid,
            )

        logging.info(f"Adding node: {name}, slice: {slice.get_name()}, site: {site}")
        node = Switch(
            slice,
            slice.topology.add_switch(name=name, site=site),
            validate=validate,
            raise_exception=raise_exception,
        )
        node.__set_capacities(unit=1)

        node.init_fablib_data()

        return node

    def toJson(self):
        """
        Returns the node attributes as a JSON string

        :return: slice attributes as JSON string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_name_dict():
        return {
            "id": "ID",
            "name": "Name",
            "site": "Site",
            "username": "Username",
            "management_ip": "Management IP",
            "state": "State",
            "error": "Error",
            "ssh_command": "SSH Command",
            "public_ssh_key_file": "Public SSH Key File",
            "private_ssh_key_file": "Private SSH Key File",
        }

    def toDict(self, skip: list = None):
        """
        Returns the node attributes as a dictionary

        :return: slice attributes as  dictionary
        :rtype: dict
        """
        if not skip:
            skip = []

        rtn_dict = {}

        if "id" not in skip:
            rtn_dict["id"] = str(self.get_reservation_id())
        if "name" not in skip:
            rtn_dict["name"] = str(self.get_name())
        if "site" not in skip:
            rtn_dict["site"] = str(self.get_site())
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
        return context

    def get_template_context(self, skip: List[str] = None):
        if not skip:
            skip = ["ssh_command"]

        return self.get_slice().get_template_context(self, skip=skip)

    def render_template(self, input_string, skip: List[str] = None):
        if not skip:
            skip = ["ssh_command"]

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
                title="Switch",
                output="pandas",
                quiet=True,
                pretty_names_dict=pretty_names_dict,
            )
            table.applymap(state_color)

            if not quiet:
                display(table)
        else:
            table = self.get_fablib_manager().show_table(
                data,
                fields=fields,
                title="Switch",
                output=output,
                quiet=quiet,
                pretty_names_dict=pretty_names_dict,
            )

        return table

    def get_fim(self) -> FimNode:
        """
        Not recommended for most users.

        Gets the node's FABRIC Information Model (fim) object. This method
        is used to access data at a lower level than FABlib.

        :return: the FABRIC model node
        :rtype: FIMNode
        """
        return self.fim_node

    def __set_capacities(self, unit: int = 1):
        """
        Sets the capacities of the FABRIC node.
        """
        cap = Capacities(unit=unit)
        self.get_fim().set_properties(capacities=cap)

    def delete(self):
        """
        Remove the switch from the slice. All components and interfaces associated with
        the Node are removed from the Slice.
        """
        self.get_slice().get_fim_topology().remove_switch(name=self.get_name())

    def get_interfaces(self) -> List[Interface] or None:
        """
        Gets a list of the interfaces associated with the FABRIC node.

        :return: a list of interfaces on the node
        :rtype: List[Interface]
        """
        interfaces = []
        for name, ifs in self.get_fim().interfaces.items():
            interfaces.append(Interface(node=self, fim_interface=ifs, model="NIC_P4"))

        return interfaces
