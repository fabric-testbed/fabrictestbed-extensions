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

"""
V2 Interface implementation with improved caching.

This module provides ``InterfaceV2``, an optimized version of ``Interface`` that:
- Caches frequently accessed FIM properties
- Uses dirty flags to avoid redundant FIM access
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from fabrictestbed_extensions.fablib.interface import Interface

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.component import Component
    from fabrictestbed_extensions.fablib.facility_port import FacilityPort
    from fabrictestbed_extensions.fablib.switch import Switch
    from fim.user.interface import Interface as FimInterface

log = logging.getLogger("fablib")


class InterfaceV2(Interface):
    """
    V2 Interface implementation with improved caching.

    This class extends Interface with:
    - Cached FIM property access for name, mac, vlan, bandwidth, site
    - Dirty flag to track when caches need refresh
    """

    def __init__(
        self,
        component: Component = None,
        fim_interface: FimInterface = None,
        node: Union[Switch, FacilityPort] = None,
        model: str = None,
        parent: Interface = None,
    ):
        """
        InterfaceV2 constructor.

        :param component: the component to set on this interface
        :type component: Component
        :param fim_interface: the FIM interface
        :type fim_interface: FimInterface
        :param node: the facility port or switch associated with this interface
        :type node: Union[Switch, FacilityPort]
        :param model: the model name
        :type model: str
        :param parent: parent interface for sub-interfaces
        :type parent: Interface
        """
        super().__init__(
            component=component,
            fim_interface=fim_interface,
            node=node,
            model=model,
            parent=parent,
        )

        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        # V2 specific: cached FIM properties
        self._cached_name: Optional[str] = None
        self._cached_mac: Optional[str] = None
        self._cached_vlan: Optional[str] = None
        self._cached_bandwidth: Optional[int] = None
        self._cached_site: Optional[str] = None
        self._cached_physical_os_interface: Optional[str] = None

    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        self._fim_dirty = True
        self._cached_name = None
        self._cached_mac = None
        self._cached_vlan = None
        self._cached_bandwidth = None
        self._cached_site = None
        self._cached_physical_os_interface = None

    def update(self, fim_interface: FimInterface = None):
        """
        Update the interface with new FIM data.

        :param fim_interface: The new FIM interface data
        :type fim_interface: FimInterface
        """
        if fim_interface:
            self.fim_interface = fim_interface
            self._invalidate_cache()
            self._fim_dirty = False

    # -------------------------------------------------------------------------
    # Cached property accessors
    # -------------------------------------------------------------------------

    def get_name(self) -> str:
        """
        Gets the name of the interface.

        Results are cached for performance.

        :return: the interface name
        :rtype: str
        """
        if self._cached_name is None:
            try:
                if self.fim_interface:
                    self._cached_name = self.fim_interface.name
                else:
                    self._cached_name = ""
            except Exception:
                self._cached_name = ""
        return self._cached_name

    def get_mac(self) -> str:
        """
        Gets the MAC address of the interface.

        Results are cached for performance.

        :return: the MAC address
        :rtype: str
        """
        if self._cached_mac is None:
            try:
                if self.fim_interface:
                    label_allocations = self.fim_interface.get_property(
                        pname="label_allocations"
                    )
                    if label_allocations:
                        self._cached_mac = label_allocations.mac
                    else:
                        self._cached_mac = ""
                else:
                    self._cached_mac = ""
            except Exception:
                self._cached_mac = ""
        return self._cached_mac if self._cached_mac else ""

    def get_vlan(self) -> str:
        """
        Gets the VLAN of the interface.

        Results are cached for performance.

        :return: the VLAN
        :rtype: str
        """
        if self._cached_vlan is None:
            try:
                if self.fim_interface:
                    label_allocations = self.fim_interface.get_property(
                        pname="label_allocations"
                    )
                    if label_allocations and label_allocations.vlan:
                        self._cached_vlan = str(label_allocations.vlan)
                    else:
                        self._cached_vlan = ""
                else:
                    self._cached_vlan = ""
            except Exception:
                self._cached_vlan = ""
        return self._cached_vlan

    def get_bandwidth(self) -> int:
        """
        Gets the bandwidth of the interface in Gbps.

        Results are cached for performance.

        :return: the bandwidth in Gbps
        :rtype: int
        """
        if self._cached_bandwidth is None:
            try:
                if self.fim_interface:
                    capacities = self.fim_interface.get_property(pname="capacities")
                    if capacities and capacities.bw:
                        self._cached_bandwidth = int(capacities.bw)
                    else:
                        self._cached_bandwidth = 0
                else:
                    self._cached_bandwidth = 0
            except Exception:
                self._cached_bandwidth = 0
        return self._cached_bandwidth

    def get_site(self) -> str:
        """
        Gets the site where the interface is located.

        Results are cached for performance.

        :return: the site name
        :rtype: str
        """
        if self._cached_site is None:
            try:
                if self.get_node():
                    self._cached_site = self.get_node().get_site()
                else:
                    self._cached_site = ""
            except Exception:
                self._cached_site = ""
        return self._cached_site

    def get_physical_os_interface_name(self) -> str:
        """
        Gets the physical OS interface name.

        Results are cached for performance.

        :return: the physical OS interface name
        :rtype: str
        """
        if self._cached_physical_os_interface is None:
            try:
                if self.fim_interface:
                    label_allocations = self.fim_interface.get_property(
                        pname="label_allocations"
                    )
                    if label_allocations and label_allocations.local_name:
                        self._cached_physical_os_interface = label_allocations.local_name
                    else:
                        self._cached_physical_os_interface = ""
                else:
                    self._cached_physical_os_interface = ""
            except Exception:
                self._cached_physical_os_interface = ""
        return self._cached_physical_os_interface

    # -------------------------------------------------------------------------
    # Optimized toDict
    # -------------------------------------------------------------------------

    def toDict(self, skip: List[str] = None) -> dict:
        """
        Returns the interface attributes as a dictionary.

        Uses cached values where available for better performance.

        :param skip: list of keys to skip
        :type skip: List[str]
        :return: interface attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        rtn_dict = {}

        if "name" not in skip:
            rtn_dict["name"] = self.get_name()
        if "network" not in skip:
            network = self.get_network()
            rtn_dict["network"] = network.get_name() if network else None
        if "bandwidth" not in skip:
            rtn_dict["bandwidth"] = str(self.get_bandwidth())
        if "vlan" not in skip:
            rtn_dict["vlan"] = self.get_vlan()
        if "mac" not in skip:
            rtn_dict["mac"] = self.get_mac()
        if "physical_dev" not in skip:
            rtn_dict["physical_dev"] = self.get_physical_os_interface_name()
        if "dev" not in skip:
            rtn_dict["dev"] = str(self.get_device_name())
        if "site" not in skip:
            rtn_dict["site"] = self.get_site()

        return rtn_dict

    # -------------------------------------------------------------------------
    # Sub-interface handling with caching
    # -------------------------------------------------------------------------

    def get_interfaces(
        self, include_subs: bool = True, refresh: bool = False, output: str = "list"
    ) -> Union[Dict[str, "InterfaceV2"], List["InterfaceV2"]]:
        """
        Gets sub-interfaces of this interface.

        Results are cached. Use refresh=True to force reload.

        :param include_subs: whether to include sub-interfaces
        :type include_subs: bool
        :param refresh: force refresh from FIM
        :type refresh: bool
        :param output: return type - 'list' or 'dict'
        :type output: str
        :return: sub-interfaces
        :rtype: Union[Dict[str, InterfaceV2], List[InterfaceV2]]
        """
        if refresh or not self.interfaces or self._fim_dirty:
            self.interfaces = {}
            if self.fim_interface and hasattr(self.fim_interface, 'interfaces'):
                for iface in self.fim_interface.interfaces.values():
                    sub_iface = InterfaceV2(
                        component=self.component,
                        fim_interface=iface,
                        node=self.node,
                        parent=self,
                    )
                    self.interfaces[sub_iface.get_name()] = sub_iface

        if output == "dict":
            return self.interfaces
        return list(self.interfaces.values())
