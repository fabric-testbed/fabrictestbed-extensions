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
"""FABRIC P4 programmable switch abstraction.

This module provides the Switch class for working with P4-programmable
network switches in FABRIC. Switches extend the Node class with specialized
functionality for programmable data planes.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from IPython.core.display_functions import display
from fabrictestbed_extensions.utils.utils import Utils
from tabulate import tabulate

from fabrictestbed_extensions.fablib.constants import Constants
from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.node import Node

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice

from fabrictestbed.slice_editor import Capacities
from fabrictestbed.slice_editor import Node as FimNode

log = logging.getLogger("fablib")


class Switch(Node):
    _show_title = "Switch"

    """Represents a P4-programmable network switch in FABRIC.

    Switch extends :class:`~fabrictestbed_extensions.fablib.node.Node` to model
    programmable data-plane devices with interfaces exposed as P4 ports. The
    management username defaults to the FABRIC system account for switch access.

    :ivar str username: Set to :data:`~fabrictestbed_extensions.fablib.constants.Constants.FABRIC_USER`
        for system-level access.
    """

    def __init__(
        self,
        slice: Slice,
        node: FimNode,
        validate: bool = False,
        raise_exception: bool = False,
    ):
        """
        Switch constructor, usually invoked by ``Slice.add_switch()``.

        :param slice: the fablib slice to have this switch on
        :type slice: Slice

        :param node: the FIM node that this Switch represents
        :type node: FimNode

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :param raise_exception: Raise exception in case validation fails
        :type raise_exception: bool

        """
        super(Switch, self).__init__(
            slice=slice, node=node, validate=validate, raise_exception=raise_exception
        )
        self.username = Constants.FABRIC_USER

        # Cached interfaces
        self._interfaces_cache: Dict[str, Interface] = {}

    def _invalidate_cache(self):
        """Invalidate all cached properties including interfaces."""
        super()._invalidate_cache()
        self._interfaces_cache = {}

    def update(self, fim_node: FimNode = None):
        """
        Update the switch with new FIM data.

        :param fim_node: The new FIM node data
        :type fim_node: FimNode
        """
        if fim_node:
            self.fim_node = fim_node
            self._invalidate_cache()
            self.get_interfaces(refresh=True)
            self._fim_dirty = False

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
    def get_switch(slice: Slice, node: FimNode) -> Switch:
        """
        Factory method to create a SwitchV2 from a FIM node.

        :param slice: the slice this switch belongs to
        :type slice: SliceV2
        :param node: the FIM node
        :type node: FimNode
        :return: a SwitchV2 instance
        :rtype: SwitchV2
        """
        switch = Switch(slice=slice, node=node)
        switch.get_interfaces()
        return switch

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
        Creates a new FABRIC switch on the slice.

        Not intended for API use. Use slice.add_switch() instead.

        :param slice: the fablib slice to build the new switch on
        :type slice: SliceV2
        :param name: the name of the new switch
        :type name: str
        :param site: the name of the site to build the switch on
        :type site: str
        :param avoid: a list of site names to avoid
        :type avoid: List[str]
        :param validate: Validate switch can be allocated w.r.t available resources
        :type validate: bool
        :param raise_exception: Raise exception if validation fails
        :type raise_exception: bool
        :return: a new Switch
        :rtype: Switch
        """
        if avoid is None:
            avoid = []

        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(avoid=avoid)

        log.info(f"Adding switch: {name}, slice: {slice.get_name()}, site: {site}")

        from fabrictestbed.slice_editor import Capacities

        switch = Switch(
            slice,
            slice.topology.add_switch(name=name, site=site),
            validate=validate,
            raise_exception=raise_exception,
        )
        # Set capacities
        cap = Capacities(unit=1)
        switch.get_fim().set_properties(capacities=cap)
        switch.init_fablib_data()

        return switch


    @staticmethod
    def get_pretty_name_dict():
        """
        Get a mapping of field names to human-readable labels for display.

        Returns a dictionary that maps internal field names to user-friendly
        display names used when rendering tables and formatted output.

        :return: Dictionary mapping field names to pretty names
        :rtype: dict
        """
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
        Returns the node attributes as a dictionary.

        Results are cached. Cache is invalidated when ``_invalidate_cache()``
        is called.

        :param skip: list of keys to exclude
        :type skip: list
        :return: switch attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        if self._cached_dict is None:
            d = {}
            d["id"] = str(self.get_reservation_id())
            d["name"] = str(self.get_name())
            d["site"] = str(self.get_site())
            d["username"] = str(self.get_username())
            d["management_ip"] = (
                str(self.get_management_ip()).strip()
                if str(self.get_reservation_state()) == "Active"
                and self.get_management_ip()
                else ""
            )
            d["state"] = str(self.get_reservation_state())
            d["error"] = str(self.get_error_message())
            if str(self.get_reservation_state()) == "Active":
                d["ssh_command"] = str(self.get_ssh_command())
            else:
                d["ssh_command"] = ""
            d["public_ssh_key_file"] = str(self.get_public_key_file())
            d["private_ssh_key_file"] = str(self.get_private_key_file())
            self._cached_dict = d

        if not skip:
            return dict(self._cached_dict)
        return {k: v for k, v in self._cached_dict.items() if k not in skip}

    def generate_template_context(self, skip: list = None):
        """
        Generate the base template context for this switch.

        Creates a dictionary context suitable for Jinja2 template rendering,
        excluding the SSH command and setting an empty components list.

        :param skip: list of keys to exclude
        :type skip: list
        :return: Template context dictionary with switch attributes
        :rtype: dict
        """
        if skip is None:
            skip = []
        if "ssh_command" not in skip:
            skip.append("ssh_command")
        context = self.toDict(skip=skip)
        context["components"] = []
        return context

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

    def get_interfaces(
        self, include_subs: bool = True, refresh: bool = False, output: str = "list"
    ) -> Union[Dict[str, Interface], List[Interface]]:
        """
        Gets a list of the interfaces associated with the FABRIC node.

        Results are cached. Use refresh=True to force reload.

        :param include_subs: Flag indicating if sub interfaces should be included
        :type include_subs: bool

        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :param output: return type - 'list' or 'dict'
        :type output: str

        :return: interfaces on the node
        :rtype: Union[Dict[str, Interface], List[Interface]]
        """
        if self._interfaces_cache and not refresh and not self._fim_dirty:
            if output == "dict":
                return self._interfaces_cache
            return [
                self._interfaces_cache[key]
                for key in sorted(self._interfaces_cache.keys())
            ]

        self._interfaces_cache = {}

        try:
            if self.fim_node and hasattr(self.fim_node, "interfaces"):
                for name, fim_iface in self.fim_node.interfaces.items():
                    self._interfaces_cache[name] = Interface(
                        node=self, fim_interface=fim_iface, model="NIC_P4"
                    )
        except Exception as e:
            log.debug(f"Error getting interfaces: {e}")

        # Keep self.interfaces in sync for backward compatibility
        self.interfaces = dict(self._interfaces_cache)

        if output == "dict":
            return self._interfaces_cache

        return [
            self._interfaces_cache[key]
            for key in sorted(self._interfaces_cache.keys())
        ]

    def get_interface(
        self, name: str = None, refresh: bool = False
    ) -> Optional[Interface]:
        """
        Gets a specific interface by name.

        :param name: the interface name
        :type name: str
        :param refresh: force refresh from FIM
        :type refresh: bool
        :return: the interface
        :rtype: Interface
        """
        if not self._interfaces_cache or refresh or self._fim_dirty:
            self.get_interfaces(refresh=refresh, output="dict")

        return self._interfaces_cache.get(name)

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
        ret_val = Switch(slice, node)
        ret_val.get_interfaces()
        return ret_val
