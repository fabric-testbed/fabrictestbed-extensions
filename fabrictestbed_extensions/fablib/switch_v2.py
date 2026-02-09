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
V2 Switch implementation with improved caching.

This module provides ``SwitchV2``, an optimized version of ``Switch`` that:
- Caches frequently accessed FIM properties
- Uses dirty flags to avoid redundant FIM access
- Caches interface list
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from fabrictestbed_extensions.fablib.switch import Switch

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice_v2 import SliceV2
    from fabrictestbed_extensions.fablib.interface_v2 import InterfaceV2
    from fim.user.node import Node as FimNode

log = logging.getLogger("fablib")


class SwitchV2(Switch):
    """
    V2 Switch implementation with improved caching.

    This class extends Switch with:
    - Cached FIM property access for name, site, management_ip, reservation_id
    - Cached interface list
    - Dirty flag to track when caches need refresh
    """

    def __init__(
        self,
        slice: SliceV2,
        node: FimNode,
        validate: bool = False,
        raise_exception: bool = False,
    ):
        """
        SwitchV2 constructor.

        :param slice: the fablib slice to have this switch on
        :type slice: SliceV2
        :param node: the FIM node that this Switch represents
        :type node: FimNode
        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool
        :param raise_exception: Raise exception in case validation fails
        :type raise_exception: bool
        """
        super().__init__(
            slice=slice,
            node=node,
            validate=validate,
            raise_exception=raise_exception,
        )

        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        # V2 specific: cached FIM properties
        self._cached_name: Optional[str] = None
        self._cached_site: Optional[str] = None
        self._cached_management_ip: Optional[str] = None
        self._cached_reservation_id: Optional[str] = None

        # V2 specific: cached interfaces
        self._interfaces_cache: Dict[str, InterfaceV2] = {}

    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        self._fim_dirty = True
        self._cached_name = None
        self._cached_site = None
        self._cached_management_ip = None
        self._cached_reservation_id = None
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

    # -------------------------------------------------------------------------
    # Cached property accessors
    # -------------------------------------------------------------------------

    def get_name(self) -> str:
        """
        Gets the name of the switch.

        Results are cached for performance.

        :return: the switch name
        :rtype: str
        """
        if self._cached_name is None:
            try:
                if self.fim_node:
                    self._cached_name = self.fim_node.name
                else:
                    self._cached_name = ""
            except Exception:
                self._cached_name = ""
        return self._cached_name

    def get_site(self) -> str:
        """
        Gets the site where the switch is located.

        Results are cached for performance.

        :return: the site name
        :rtype: str
        """
        if self._cached_site is None:
            try:
                if self.fim_node:
                    self._cached_site = self.fim_node.site
                else:
                    self._cached_site = ""
            except Exception:
                self._cached_site = ""
        return self._cached_site

    def get_management_ip(self) -> str:
        """
        Gets the management IP of the switch (IPv6).

        Results are cached for performance.

        :return: management IP
        :rtype: str
        """
        if self._cached_management_ip is None:
            try:
                if self.fim_node:
                    self._cached_management_ip = str(self.fim_node.management_ip)
                else:
                    self._cached_management_ip = ""
            except Exception:
                self._cached_management_ip = ""
        return self._cached_management_ip

    def get_reservation_id(self) -> str:
        """
        Gets the reservation ID of the switch.

        Results are cached for performance.

        :return: reservation ID
        :rtype: str
        """
        if self._cached_reservation_id is None:
            try:
                if self.fim_node:
                    res_info = self.fim_node.get_property(pname="reservation_info")
                    if res_info and res_info.reservation_id:
                        self._cached_reservation_id = str(res_info.reservation_id)
                    else:
                        self._cached_reservation_id = ""
                else:
                    self._cached_reservation_id = ""
            except Exception:
                self._cached_reservation_id = ""
        return self._cached_reservation_id

    # -------------------------------------------------------------------------
    # Cached interfaces
    # -------------------------------------------------------------------------

    def get_interfaces(
        self, include_subs: bool = True, refresh: bool = False, output: str = "list"
    ) -> Union[Dict[str, InterfaceV2], List[InterfaceV2]]:
        """
        Gets interfaces associated with this switch.

        Results are cached. Use refresh=True to force reload.

        :param include_subs: Flag indicating if sub interfaces should be included
        :type include_subs: bool
        :param refresh: force refresh from FIM
        :type refresh: bool
        :param output: return type - 'list' or 'dict'
        :type output: str
        :return: interfaces
        :rtype: Union[Dict[str, InterfaceV2], List[InterfaceV2]]
        """
        from fabrictestbed_extensions.fablib.interface_v2 import InterfaceV2

        if self._interfaces_cache and not refresh and not self._fim_dirty:
            if output == "dict":
                return self._interfaces_cache
            # Return sorted by interface name
            sorted_interfaces = [
                self._interfaces_cache[key]
                for key in sorted(self._interfaces_cache.keys())
            ]
            return sorted_interfaces

        self._interfaces_cache = {}

        try:
            if self.fim_node and hasattr(self.fim_node, 'interfaces'):
                for name, fim_iface in self.fim_node.interfaces.items():
                    interface = InterfaceV2(
                        node=self, fim_interface=fim_iface, model="NIC_P4"
                    )
                    self._interfaces_cache[name] = interface
        except Exception as e:
            log.debug(f"Error getting interfaces: {e}")

        if output == "dict":
            return self._interfaces_cache

        # Return sorted by interface name
        sorted_interfaces = [
            self._interfaces_cache[key]
            for key in sorted(self._interfaces_cache.keys())
        ]
        return sorted_interfaces

    def get_interface(
        self, name: str = None, refresh: bool = False
    ) -> Optional[InterfaceV2]:
        """
        Gets a specific interface by name.

        :param name: the interface name
        :type name: str
        :param refresh: force refresh from FIM
        :type refresh: bool
        :return: the interface
        :rtype: InterfaceV2
        """
        # Ensure cache is populated
        if not self._interfaces_cache or refresh or self._fim_dirty:
            self.get_interfaces(refresh=refresh, output="dict")

        return self._interfaces_cache.get(name)

    # -------------------------------------------------------------------------
    # Optimized toDict
    # -------------------------------------------------------------------------

    def toDict(self, skip: List[str] = None) -> dict:
        """
        Returns the switch attributes as a dictionary.

        Uses cached values where available for better performance.

        :param skip: list of keys to skip
        :type skip: List[str]
        :return: switch attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        rtn_dict = {}

        if "id" not in skip:
            rtn_dict["id"] = self.get_reservation_id()
        if "name" not in skip:
            rtn_dict["name"] = self.get_name()
        if "site" not in skip:
            rtn_dict["site"] = self.get_site()
        if "username" not in skip:
            rtn_dict["username"] = str(self.get_username())
        if "management_ip" not in skip:
            rtn_dict["management_ip"] = (
                self.get_management_ip().strip()
                if str(self.get_reservation_state()) == "Active"
                and self.get_management_ip()
                else ""
            )
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

    # -------------------------------------------------------------------------
    # Static factory methods
    # -------------------------------------------------------------------------

    @staticmethod
    def get_switch(slice: SliceV2, node: FimNode) -> SwitchV2:
        """
        Factory method to create a SwitchV2 from a FIM node.

        :param slice: the slice this switch belongs to
        :type slice: SliceV2
        :param node: the FIM node
        :type node: FimNode
        :return: a SwitchV2 instance
        :rtype: SwitchV2
        """
        switch = SwitchV2(slice=slice, node=node)
        switch.get_interfaces()
        return switch

    @staticmethod
    def new_switch(
        slice: SliceV2 = None,
        name: str = None,
        site: str = None,
        avoid: List[str] = None,
        validate: bool = False,
        raise_exception: bool = False,
    ) -> SwitchV2:
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
        :return: a new SwitchV2
        :rtype: SwitchV2
        """
        if avoid is None:
            avoid = []

        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(avoid=avoid)

        log.info(f"Adding switch: {name}, slice: {slice.get_name()}, site: {site}")

        from fabrictestbed.slice_editor import Capacities

        switch = SwitchV2(
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
