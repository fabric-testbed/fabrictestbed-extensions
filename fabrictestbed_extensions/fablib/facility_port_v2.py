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
V2 FacilityPort implementation with improved caching.

This module provides ``FacilityPortV2``, an optimized version of ``FacilityPort`` that:
- Caches frequently accessed FIM properties
- Uses dirty flags to avoid redundant FIM access
- Caches interface list
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from fabrictestbed_extensions.fablib.facility_port import FacilityPort

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice_v2 import SliceV2
    from fabrictestbed_extensions.fablib.interface_v2 import InterfaceV2
    from fim.user.node import Node as FimNode

log = logging.getLogger("fablib")


class FacilityPortV2(FacilityPort):
    """
    V2 FacilityPort implementation with improved caching.

    This class extends FacilityPort with:
    - Cached FIM property access for name, site
    - Cached interface list
    - Dirty flag to track when caches need refresh
    """

    def __init__(self, slice: SliceV2, fim_interface: FimNode):
        """
        FacilityPortV2 constructor.

        :param slice: the fablib slice this facility port belongs to
        :type slice: SliceV2
        :param fim_interface: the FIM node representing the facility port
        :type fim_interface: FimNode
        """
        super().__init__(slice=slice, fim_interface=fim_interface)

        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        # V2 specific: cached FIM properties
        self._cached_name: Optional[str] = None
        self._cached_site: Optional[str] = None

        # V2 specific: cached interfaces
        self._interfaces_cache: Dict[str, InterfaceV2] = {}

    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        self._fim_dirty = True
        self._cached_name = None
        self._cached_site = None
        self._interfaces_cache = {}

    def update(self, fim_node: FimNode = None):
        """
        Update the facility port with new FIM data.

        :param fim_node: The new FIM node data
        :type fim_node: FimNode
        """
        if fim_node:
            self.fim_interface = fim_node
            self._invalidate_cache()
            self.get_interfaces(refresh=True)
            self._fim_dirty = False

    # -------------------------------------------------------------------------
    # Cached property accessors
    # -------------------------------------------------------------------------

    def get_name(self) -> str:
        """
        Gets the name of the facility port.

        Results are cached for performance.

        :return: the facility port name
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

    def get_site(self) -> str:
        """
        Gets the site where the facility port is located.

        Results are cached for performance.

        :return: the site name
        :rtype: str
        """
        if self._cached_site is None:
            try:
                if self.fim_interface:
                    self._cached_site = self.fim_interface.site
                else:
                    self._cached_site = ""
            except Exception:
                self._cached_site = ""
        return self._cached_site

    # -------------------------------------------------------------------------
    # Cached interfaces
    # -------------------------------------------------------------------------

    def get_interfaces(
        self, refresh: bool = False, output: str = "list"
    ) -> Union[Dict[str, InterfaceV2], List[InterfaceV2]]:
        """
        Gets interfaces associated with this facility port.

        Results are cached. Use refresh=True to force reload.

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
            return list(self._interfaces_cache.values())

        self._interfaces_cache = {}

        try:
            if self.fim_interface and hasattr(self.fim_interface, 'interfaces'):
                for iface in self.fim_interface.interfaces.values():
                    interface = InterfaceV2(fim_interface=iface, node=self)
                    self._interfaces_cache[interface.get_name()] = interface
        except Exception as e:
            log.debug(f"Error getting interfaces: {e}")

        if output == "dict":
            return self._interfaces_cache
        return list(self._interfaces_cache.values())

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
        interfaces = self.get_interfaces(refresh=refresh, output="dict")
        return interfaces.get(name)

    # -------------------------------------------------------------------------
    # Optimized toDict
    # -------------------------------------------------------------------------

    def toDict(self, skip: List[str] = None) -> dict:
        """
        Returns the facility port attributes as a dictionary.

        Uses cached values where available for better performance.

        :param skip: list of keys to skip
        :type skip: List[str]
        :return: facility port attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        rtn_dict = {}

        if "name" not in skip:
            rtn_dict["name"] = self.get_name()
        if "site" not in skip:
            rtn_dict["site"] = self.get_site()

        return rtn_dict

    # -------------------------------------------------------------------------
    # Static factory method
    # -------------------------------------------------------------------------

    @staticmethod
    def get_facility_port(slice: SliceV2, fim_node: FimNode) -> FacilityPortV2:
        """
        Factory method to create a FacilityPortV2 from a FIM node.

        :param slice: the slice this facility port belongs to
        :type slice: SliceV2
        :param fim_node: the FIM node
        :type fim_node: FimNode
        :return: a FacilityPortV2 instance
        :rtype: FacilityPortV2
        """
        return FacilityPortV2(slice=slice, fim_interface=fim_node)
