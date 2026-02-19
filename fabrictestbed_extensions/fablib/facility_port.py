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
import logging
from typing import TYPE_CHECKING, List, Union, Optional, Dict

from fabrictestbed.slice_editor import Capacities, Labels

from fabrictestbed_extensions.utils.utils import Utils
from tabulate import tabulate

from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.template_mixin import TemplateMixin

if TYPE_CHECKING:
    from fim.user.node import Node as FimNode
    from fabrictestbed_extensions.fablib.fablib import FablibManager
    from fabrictestbed_extensions.fablib.slice import Slice

log = logging.getLogger("fablib")


class FacilityPort(TemplateMixin):
    """
    A class for working with FABRIC facility ports.
    """

    _show_title = "Facility Port"

    fim_object = None
    slice = None

    def __init__(self, slice: Slice, fim_object: FimNode):
        """
        :param slice: the fablib slice to have this node on
        :type slice: Slice

        :param fim_object:
        :type fim_object: FimNode
        """
        super().__init__()
        self.fim_object: FimNode = fim_object
        self.slice: Slice = slice
        self.interfaces: Dict[str, Interface] = {}

        self._cached_site: Optional[str] = None

        # V2 specific: cached interfaces
        self._interfaces_cache: Dict[str, Interface] = {}

    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        super(FacilityPort, self)._invalidate_cache()

        self._cached_site = None
        self._interfaces_cache = {}

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the
        node.  Intended for printing node information.

        :return: Tabulated string of node information
        :rtype: String
        """
        table = [["name", self.get_name()]]

        return tabulate(table)

    @staticmethod
    def get_pretty_name_dict():
        """
        Return a mapping used when rendering table headers.
        """
        return {
            "name": "Name",
        }

    def toDict(self, skip: list = None):
        """
        Return a Python `dict` representation of the facility port.

        Results are cached. Cache is invalidated when ``_invalidate_cache()``
        is called.

        :param skip: list of keys to exclude
        :type skip: list
        """
        if skip is None:
            skip = []

        if self._cached_dict is None:
            d = {}
            d["name"] = str(self.get_name())
            self._cached_dict = d

        if not skip:
            return dict(self._cached_dict)
        return {k: v for k, v in self._cached_dict.items() if k not in skip}

    def get_fim(self):
        """
        Gets the Facility Ports's FABRIC Information Model (fim) object.

        This method is used to access data at a lower level than
        FABlib.
        """
        return self.fim_object

    def get_model(self) -> str:
        """
        Get fablib model name for the facility port.
        """
        return "Facility_Port"

    def get_site(self) -> str:
        """
        Gets the site where the facility port is located.

        Results are cached for performance.

        :return: the site name
        :rtype: str
        """
        if self._cached_site is None:
            try:
                if self.fim_object:
                    self._cached_site = self.fim_object.site
                else:
                    self._cached_site = ""
            except Exception:
                self._cached_site = ""
        return self._cached_site

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
        Create a FacilityPort object from an existing FIM facility port.

        Factory method that wraps a FIM (FABRIC Information Model) facility
        port object in a FABlib FacilityPort wrapper.

        :param slice: The slice containing the facility port.
        :type slice: Slice

        :param facility_port: FIM facility port object to wrap.
        :type facility_port: FimNode

        :return: FacilityPort object wrapping the FIM facility port.
        :rtype: FacilityPort
        """
        return FacilityPort(slice=slice, fim_object=facility_port)

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice associated with this node.

        :return: the fablib slice on this node
        :rtype: Slice
        """
        return self.slice

    def get_interfaces(
            self, refresh: bool = False, output: str = "list"
    ) -> Union[Dict[str, Interface], List[Interface]]:
        """
        Gets interfaces associated with this facility port.

        Results are cached. Use refresh=True to force reload.

        :param refresh: force refresh from FIM
        :type refresh: bool
        :param output: return type - 'list' or 'dict'
        :type output: str
        :return: interfaces
        :rtype: Union[Dict[str, Interface], List[Interface]]
        """
        from fabrictestbed_extensions.fablib.interface import Interface

        if self._interfaces_cache and not refresh and not self._fim_dirty:
            if output == "dict":
                return self._interfaces_cache
            return list(self._interfaces_cache.values())

        self._interfaces_cache = {}

        try:
            if self.fim_object and hasattr(self.fim_object, 'interfaces'):
                for iface in self.fim_object.interfaces.values():
                    interface = Interface(fim_interface=iface, node=self)
                    self._interfaces_cache[interface.get_name()] = interface
        except Exception as e:
            log.debug(f"Error getting interfaces: {e}")

        if output == "dict":
            return self._interfaces_cache
        return list(self._interfaces_cache.values())

    def get_interface(
            self, name: str = None, refresh: bool = False
    ) -> Optional[Interface]:
        """
        Gets a specific interface by name.

        :param name: the interface name
        :type name: str
        :param refresh: force refresh from FIM
        :type refresh: bool
        :rtype: Interface
        """
        # Ensure cache is populated
        interfaces = self.get_interfaces(refresh=refresh, output="dict")
        return interfaces.get(name)

    def update(self, fim_node: FimNode = None):
        """
        Update the facility port with new FIM data.

        :param fim_node: The new FIM node data
        :type fim_node: FimNode
        """
        if fim_node:
            self.fim_object = fim_node
            self._invalidate_cache()
            self.get_interfaces(refresh=True)
            self._fim_dirty = False

    def delete(self):
        """
        Remove the facility from the slice. All interfaces associated with
        the Facility Port are removed from the Slice.
        """
        for iface in self.get_interfaces():
            iface.delete()

        self.get_slice().get_fim_topology().remove_facility(name=self.get_name())
