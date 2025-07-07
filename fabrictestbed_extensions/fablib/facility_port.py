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
This module contains methods to work with FABRIC `facility ports`_.

.. _`facility ports`: https://learn.fabric-testbed.net/knowledge-base/glossary/#facility_port
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, List, Union

import jinja2
from fabrictestbed.slice_editor import Capacities, Labels
from tabulate import tabulate

from fabrictestbed_extensions.fablib.interface import Interface

if TYPE_CHECKING:
    from fim.user.node import Node as FimNode

    from fabrictestbed_extensions.fablib.slice import Slice


class FacilityPort:
    """
    A class for working with FABRIC facility ports.
    """

    fim_interface = None
    slice = None

    def __init__(self, slice: Slice, fim_interface: FimNode):
        """
        :param slice: the fablib slice to have this node on
        :type slice: Slice

        :param fim_interface:
        :type fim_interface: FimNode
        """
        super().__init__()
        self.fim_interface = fim_interface
        self.slice = slice
        self.interfaces = {}

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the
        node.  Intended for printing node information.

        :return: Tabulated string of node information
        :rtype: String
        """
        table = [["name", self.get_name()]]

        return tabulate(table)

    def toJson(self):
        """
        Return a JSON representation of the facility port.
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_name_dict():
        """
        Return a mapping used when rendering table headers.
        """
        return {
            "name": "Name",
        }

    def toDict(self, skip=[]):
        """
        Return a Python `dict` representation of the facility port.
        """
        return {"name": str(self.get_name())}

    def get_template_context(self):
        return self.get_slice().get_template_context(self)

    def render_template(self, input_string):
        environment = jinja2.Environment()
        template = environment.from_string(input_string)
        output_string = template.render(self.get_template_context())

        return output_string

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Get a human-readable representation of the facility port.
        """
        data = self.toDict()

        # fields = ["Name",
        #         ]

        if pretty_names:
            pretty_names_dict = self.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        table = self.get_fablib_manager().show_table(
            data,
            fields=fields,
            title="Facility Port",
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

        return table

    def get_fablib_manager(self):
        """
        Get a reference to :py:class:`.FablibManager`.
        """
        return self.slice.get_fablib_manager()

    def get_fim_interface(self) -> FimNode:
        """
        .. warning::
            Not recommended for most users.

        Gets the node's FABRIC Information Model (fim) object.  This
        method is used to access data at a lower level than FABlib.
        """
        return self.fim_interface

    def get_fim(self):
        """
        Gets the Facility Ports's FABRIC Information Model (fim) object.

        This method is used to access data at a lower level than
        FABlib.
        """
        return self.get_fim_interface()

    def get_model(self) -> str:
        """
        Get fablib model name for the facility port.
        """
        return "Facility_Port"

    def get_name(self) -> str:
        """
        Gets the name of the FABRIC node.

        :return: the name of the node
        :rtype: String
        """
        return self.get_fim_interface().name

    def get_site(self) -> str:
        """
        Gets the site associated with the facility port.
        """
        return self.fim_interface.site

    @staticmethod
    def new_facility_port(
        slice: Slice = None,
        name: str = None,
        site: str = None,
        vlan: Union[List, str] = None,
        bandwidth: int = None,
        mtu: int = None,
        labels: Labels = None,
        peer_labels: Labels = None,
    ) -> FacilityPort:
        """
        Create a new facility port in the given slice.

        You might want to :py:meth:`Slice.add_facility_port()`, in
        most cases.

        :param slice: The slice in which the facility port will be created.
        :param name: The name of the facility port.
        :param site: The site where the facility port will be located.
        :param vlan: A list or single string representing the VLANs for the facility port.
        :param bandwidth: The bandwidth capacity for the facility port, default is 10.
        :param mtu: MTU size
        :param labels: Labels associated with the facility port.
        :param peer_labels: Peer labels associated with the facility port.
        :return: A FacilityPort object representing the created facility port.
        """
        capacities = Capacities()
        if bandwidth:
            capacities.bw = int(bandwidth)
        if mtu:
            capacities.mtu = mtu

        interfaces = None

        if vlan:
            index = 1
            interfaces = []
            if isinstance(vlan, str):
                vlan = [vlan]

            for v in vlan:
                iface_tuple = (
                    f"iface-{index}",
                    Labels(vlan=v),
                    capacities,
                )
                interfaces.append(iface_tuple)

        fim_facility_port = slice.get_fim_topology().add_facility(
            name=name,
            site=site,
            capacities=capacities,
            labels=labels,
            peer_labels=peer_labels,
            interfaces=interfaces,
        )
        return FacilityPort(slice, fim_facility_port)

    @staticmethod
    def get_facility_port(slice: Slice = None, facility_port: FimNode = None):
        """

        :param slice:
        :param facility_port:
        :return:
        """
        return FacilityPort(slice, facility_port)

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice associated with this node.

        :return: the fablib slice on this node
        :rtype: Slice
        """
        return self.slice

    def get_interfaces(
        self, refresh: bool = False, output: str = "list"
    ) -> Union[dict[str, Interface], list[Interface]]:
        """
        Gets a interface associated with a FABRIC Facility Port.

        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :param output: Specify how the return type is expected; Possible values: list or dict
        :type output: str

        :return: a list or dict of interfaces on the node
        :rtype: Union[dict[str, Interface], list[Interface]]
        """
        if refresh or len(self.interfaces) == 0:
            self.interfaces = {}
            for fim_interface in self.get_fim_interface().interface_list:
                iface = Interface(node=self, fim_interface=fim_interface)
                self.interfaces[iface.get_name()] = iface

        if output == "dict":
            return self.interfaces
        else:
            return list(self.interfaces.values())

    def update(self, fim_node: FimNode):
        if fim_node:
            self.fim_interface = fim_node

    def delete(self):
        """
        Remove the facility from the slice. All interfaces associated with
        the Facility Port are removed from the Slice.
        """
        for iface in self.get_interfaces():
            iface.delete()

        self.get_slice().get_fim_topology().remove_facility(name=self.get_name())
