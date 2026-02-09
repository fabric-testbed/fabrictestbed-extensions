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
V2 NetworkService implementation with improved caching.

This module provides ``NetworkServiceV2``, an optimized version of ``NetworkService`` that:
- Caches frequently accessed FIM properties
- Uses dirty flags to avoid redundant FIM access
- Caches interface list
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from fabrictestbed_extensions.fablib.network_service import NetworkService

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice_v2 import SliceV2
    from fabrictestbed_extensions.fablib.interface_v2 import InterfaceV2
    from fabrictestbed.slice_editor import NetworkService as FimNetworkService

log = logging.getLogger("fablib")


class NetworkServiceV2(NetworkService):
    """
    V2 NetworkService implementation with improved caching.

    This class extends NetworkService with:
    - Cached FIM property access for name, type, layer, subnet, gateway
    - Cached interface list
    - Dirty flag to track when caches need refresh
    """

    def __init__(
        self,
        slice: SliceV2 = None,
        fim_network_service: FimNetworkService = None,
        name: str = None,
    ):
        """
        NetworkServiceV2 constructor.

        :param slice: the slice this network service belongs to
        :type slice: SliceV2
        :param fim_network_service: the FIM network service
        :type fim_network_service: FimNetworkService
        :param name: the name of the network service
        :type name: str
        """
        super().__init__(
            slice=slice,
            fim_network_service=fim_network_service,
            name=name,
        )

        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        # V2 specific: cached FIM properties
        self._cached_name: Optional[str] = None
        self._cached_type: Optional[str] = None
        self._cached_layer: Optional[str] = None
        self._cached_subnet: Optional[str] = None
        self._cached_gateway: Optional[str] = None
        self._cached_reservation_id: Optional[str] = None

        # V2 specific: cached interfaces
        self._interfaces_cache: Dict[str, InterfaceV2] = {}

    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        self._fim_dirty = True
        self._cached_name = None
        self._cached_type = None
        self._cached_layer = None
        self._cached_subnet = None
        self._cached_gateway = None
        self._cached_reservation_id = None
        self._interfaces_cache = {}

    def update(self, fim_network_service: FimNetworkService = None):
        """
        Update the network service with new FIM data.

        :param fim_network_service: The new FIM network service data
        :type fim_network_service: FimNetworkService
        """
        if fim_network_service:
            self.fim_network_service = fim_network_service
            self._invalidate_cache()
            self._fim_dirty = False

    # -------------------------------------------------------------------------
    # Cached property accessors
    # -------------------------------------------------------------------------

    def get_name(self) -> str:
        """
        Gets the name of the network service.

        Results are cached for performance.

        :return: the network service name
        :rtype: str
        """
        if self._cached_name is None:
            try:
                if self.fim_network_service:
                    self._cached_name = self.fim_network_service.name
                else:
                    self._cached_name = ""
            except Exception:
                self._cached_name = ""
        return self._cached_name

    def get_type(self) -> str:
        """
        Gets the type of the network service.

        Results are cached for performance.

        :return: the network service type
        :rtype: str
        """
        if self._cached_type is None:
            try:
                if self.fim_network_service:
                    ns_type = self.fim_network_service.get_property("type")
                    self._cached_type = str(ns_type) if ns_type else ""
                else:
                    self._cached_type = ""
            except Exception:
                self._cached_type = ""
        return self._cached_type

    def get_layer(self) -> str:
        """
        Gets the layer of the network service.

        Results are cached for performance.

        :return: the network layer (L2 or L3)
        :rtype: str
        """
        if self._cached_layer is None:
            try:
                if self.fim_network_service:
                    layer = self.fim_network_service.layer
                    self._cached_layer = str(layer) if layer else ""
                else:
                    self._cached_layer = ""
            except Exception:
                self._cached_layer = ""
        return self._cached_layer

    def get_subnet(self) -> str:
        """
        Gets the subnet of the network service.

        Results are cached for performance.

        :return: the subnet
        :rtype: str
        """
        if self._cached_subnet is None:
            try:
                if self.fim_network_service:
                    labels = self.fim_network_service.get_property("label_allocations")
                    if labels:
                        if hasattr(labels, 'ipv4_subnet') and labels.ipv4_subnet:
                            self._cached_subnet = str(labels.ipv4_subnet)
                        elif hasattr(labels, 'ipv6_subnet') and labels.ipv6_subnet:
                            self._cached_subnet = str(labels.ipv6_subnet)
                        else:
                            self._cached_subnet = ""
                    else:
                        self._cached_subnet = ""
                else:
                    self._cached_subnet = ""
            except Exception:
                self._cached_subnet = ""
        return self._cached_subnet

    def get_gateway(self) -> str:
        """
        Gets the gateway of the network service.

        Results are cached for performance.

        :return: the gateway address
        :rtype: str
        """
        if self._cached_gateway is None:
            try:
                if self.fim_network_service:
                    gateway = self.fim_network_service.gateway
                    if gateway:
                        if hasattr(gateway, 'gateway'):
                            self._cached_gateway = str(gateway.gateway)
                        else:
                            self._cached_gateway = str(gateway)
                    else:
                        self._cached_gateway = ""
                else:
                    self._cached_gateway = ""
            except Exception:
                self._cached_gateway = ""
        return self._cached_gateway

    def get_reservation_id(self) -> str:
        """
        Gets the reservation ID of the network service.

        Results are cached for performance.

        :return: the reservation ID
        :rtype: str
        """
        if self._cached_reservation_id is None:
            try:
                if self.fim_network_service:
                    res_info = self.fim_network_service.get_property("reservation_info")
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

    def get_interfaces(self, refresh: bool = False) -> List:
        """
        Gets interfaces associated with this network service.

        Results are cached. Use refresh=True to force reload.

        :param refresh: force refresh from FIM
        :type refresh: bool
        :return: list of interfaces
        :rtype: List[Interface]
        """
        from fabrictestbed_extensions.fablib.interface import Interface

        if self._interfaces_cache and not refresh and not self._fim_dirty:
            return list(self._interfaces_cache.values())

        self._interfaces_cache = {}

        try:
            if self.fim_network_service and hasattr(self.fim_network_service, 'interfaces'):
                for iface in self.fim_network_service.interfaces.values():
                    interface = Interface(fim_interface=iface)
                    interface.set_network(self)
                    self._interfaces_cache[interface.get_name()] = interface
        except Exception as e:
            log.debug(f"Error getting interfaces: {e}")

        return list(self._interfaces_cache.values())

    def get_interface(self, name: str = None, refresh: bool = False):
        """
        Gets a specific interface by name.

        :param name: the interface name
        :type name: str
        :param refresh: force refresh from FIM
        :type refresh: bool
        :return: the interface
        :rtype: Interface
        """
        # Ensure cache is populated
        if not self._interfaces_cache or refresh or self._fim_dirty:
            self.get_interfaces(refresh=refresh)

        return self._interfaces_cache.get(name)

    # -------------------------------------------------------------------------
    # Optimized toDict
    # -------------------------------------------------------------------------

    def toDict(self, skip: List[str] = None) -> dict:
        """
        Returns the network service attributes as a dictionary.

        Uses cached values where available for better performance.

        :param skip: list of keys to skip
        :type skip: List[str]
        :return: network service attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        rtn_dict = {}

        if "name" not in skip:
            rtn_dict["name"] = self.get_name()
        if "type" not in skip:
            rtn_dict["type"] = self.get_type()
        if "layer" not in skip:
            rtn_dict["layer"] = self.get_layer()
        if "subnet" not in skip:
            rtn_dict["subnet"] = self.get_subnet()
        if "gateway" not in skip:
            rtn_dict["gateway"] = self.get_gateway()
        if "state" not in skip:
            rtn_dict["state"] = str(self.get_reservation_state())
        if "error" not in skip:
            rtn_dict["error"] = str(self.get_error_message())

        return rtn_dict
