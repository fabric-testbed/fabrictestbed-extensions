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
# Author: Komal Thareja (kthare10@renci.org)

"""
V2 Node implementation with improved caching and reduced FIM topology access.

This module provides ``NodeV2``, an optimized version of ``Node`` that:
- Caches frequently accessed FIM properties
- Uses dirty flags to avoid redundant topology iterations
- Provides single-access patterns for FIM data

You would add a node and operate on it like so::

    from fabrictestbed_extensions.fablib.fablib_v2 import FablibManagerV2

    fablib = FablibManagerV2()

    slice = fablib.new_slice(name="MySlice")
    node = slice.add_node(name="node1")
    slice.submit()

    node.execute('echo Hello, FABRIC from node `hostname -s`')

    slice.delete()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from fabrictestbed_extensions.fablib.component import Component
from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.node import Node

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice_v2 import SliceV2
    from fabrictestbed.slice_editor import Node as FimNode

log = logging.getLogger("fablib")


class NodeV2(Node):
    """
    V2 Node implementation with improved caching.

    This class extends Node with:
    - Cached FIM property access
    - Dirty flag to track when caches need refresh
    - Optimized component and interface initialization
    """

    def __init__(
        self,
        slice: SliceV2,
        node: FimNode,
        validate: bool = False,
        raise_exception: bool = False,
    ):
        """
        NodeV2 constructor.

        :param slice: the fablib slice to have this node on
        :type slice: SliceV2
        :param node: the FIM node that this Node represents
        :type node: FimNode
        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool
        :param raise_exception: Raise exception in case validation fails
        :type raise_exception: bool
        """
        # Initialize parent
        super().__init__(
            slice=slice,
            node=node,
            validate=validate,
            raise_exception=raise_exception,
        )

        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        # V2 specific: cached FIM properties (None means not yet cached)
        self._cached_name: Optional[str] = None
        self._cached_site: Optional[str] = None
        self._cached_management_ip: Optional[str] = None
        self._cached_reservation_id: Optional[str] = None

    def _invalidate_cache(self):
        """
        Invalidate all cached properties.

        Called when the FIM node is updated.
        """
        self._fim_dirty = True
        self._cached_name = None
        self._cached_site = None
        self._cached_management_ip = None
        self._cached_reservation_id = None

    def update(self, fim_node: FimNode):
        """
        Update the node with new FIM data.

        :param fim_node: The new FIM node data
        :type fim_node: FimNode
        """
        if fim_node:
            self.fim_node = fim_node
            self._invalidate_cache()
            self.get_components(refresh=True)
            self.get_interfaces(refresh=True)
            # Mark as clean after refresh
            self._fim_dirty = False

    # -------------------------------------------------------------------------
    # Cached property accessors
    # -------------------------------------------------------------------------

    def get_name(self) -> str:
        """
        Gets the name of the FABRIC node.

        Results are cached for performance.

        :return: the name of the node
        :rtype: String
        """
        if self._cached_name is None:
            try:
                self._cached_name = self.fim_node.name
            except Exception:
                self._cached_name = ""
        return self._cached_name

    def get_site(self) -> str:
        """
        Gets the site this node is on.

        Results are cached for performance.

        :return: the site this node is on
        :rtype: String
        """
        if self._cached_site is None:
            try:
                self._cached_site = self.fim_node.site
            except Exception:
                self._cached_site = ""
        return self._cached_site

    def get_management_ip(self) -> str:
        """
        Gets the management IP of the node (IPv6).

        Results are cached for performance.

        :return: management IP
        :rtype: String
        """
        if self._cached_management_ip is None:
            try:
                self._cached_management_ip = str(self.fim_node.management_ip)
            except Exception:
                self._cached_management_ip = ""
        return self._cached_management_ip

    def get_reservation_id(self) -> str:
        """
        Gets the reservation ID of the node.

        Results are cached for performance.

        :return: reservation ID
        :rtype: String
        """
        if self._cached_reservation_id is None:
            try:
                self._cached_reservation_id = str(
                    self.fim_node.get_property(pname="reservation_info").reservation_id
                )
            except Exception:
                self._cached_reservation_id = ""
        return self._cached_reservation_id

    # -------------------------------------------------------------------------
    # Improved component/interface caching
    # -------------------------------------------------------------------------

    def get_components(self, refresh: bool = False) -> List[Component]:
        """
        Gets a list of components associated with this node.

        Results are cached. Use refresh=True to force reload from FIM.

        :param refresh: Refresh the component objects with latest FIM info
        :type refresh: bool
        :return: a list of components on this node
        :rtype: List[Component]
        """
        # Skip refresh if cache is valid
        if self.components and not refresh and not self._fim_dirty:
            return list(self.components.values())

        # Get components from FIM (single access)
        fim_components = self.fim_node.components

        if refresh or not self.components:
            self.components.clear()

        # Update or create component objects
        for component_name, fim_component in fim_components.items():
            if component_name not in self.components:
                self.components[component_name] = Component(self, fim_component)
            elif refresh:
                # Update existing component's FIM reference
                self.components[component_name].fim_component = fim_component

        # Remove components no longer in FIM
        current_names = set(fim_components.keys())
        to_remove = [name for name in self.components if name not in current_names]
        for name in to_remove:
            del self.components[name]

        return list(self.components.values())

    def get_component(self, name: str, refresh: bool = False) -> Component:
        """
        Retrieve a component associated with this node.

        Results are cached. Use refresh=True to force reload from FIM.

        :param name: Name of the component to retrieve
        :type name: str
        :param refresh: Whether to refresh the component from the latest FIM data
        :type refresh: bool
        :return: The requested component
        :rtype: Component
        :raises Exception: If the component is not found
        """
        try:
            calculated_name = Component.calculate_name(node=self, name=name)

            # Check cache first (if not forcing refresh)
            if not refresh and not self._fim_dirty:
                for key in (calculated_name, name):
                    if key in self.components:
                        return self.components[key]

            # Get from FIM (single access)
            fim_components = self.fim_node.components
            fim_comp = fim_components.get(calculated_name) or fim_components.get(name)

            if not fim_comp:
                raise Exception(f"Component not found in FIM: {name}")

            # Create and cache new component
            key = calculated_name if fim_comp.name == calculated_name else name
            component = Component(self, fim_comp)
            self.components[key] = component
            return component

        except Exception as e:
            log.error(f"Error retrieving component '{name}': {e}", exc_info=True)
            raise Exception(f"Component not found: {name}")

    def get_interfaces(
        self, include_subs: bool = True, refresh: bool = False, output: str = "list"
    ) -> Union[Dict[str, Interface], List[Interface]]:
        """
        Gets a list of the interfaces associated with the FABRIC node.

        Results are cached. Use refresh=True to force reload from FIM.

        :param include_subs: Flag indicating if sub interfaces should be included
        :type include_subs: bool
        :param refresh: Refresh the interface objects with latest FIM info
        :type refresh: bool
        :param output: Return type - 'list' or 'dict'
        :type output: str
        :return: interfaces on the node
        :rtype: Union[Dict[str, Interface], List[Interface]]
        """
        # Skip refresh if cache is valid
        if self.interfaces and not refresh and not self._fim_dirty:
            if output == "dict":
                return self.interfaces
            return list(self.interfaces.values())

        # Rebuild interface cache from components
        self.interfaces.clear()
        for component in self.get_components(refresh=refresh):
            c_interfaces = component.get_interfaces(
                include_subs=include_subs, refresh=refresh, output="dict"
            )
            self.interfaces.update(c_interfaces)

        if output == "dict":
            return self.interfaces
        return list(self.interfaces.values())

    def get_interface(
        self, name: str = None, network_name: str = None, refresh: bool = False
    ) -> Optional[Interface]:
        """
        Gets a particular interface associated with a FABRIC node.

        Accepts either the interface name or a network_name. If a network name
        is used, returns the interface connected to that network. If both name
        and network_name are provided, name takes precedence.

        :param name: interface name to search for
        :type name: str
        :param network_name: network name to search for
        :type network_name: str
        :param refresh: Refresh interface objects with latest FIM info
        :type refresh: bool
        :return: an interface on the node
        :rtype: Interface
        :raises Exception: if interface is not found
        """
        # Ensure interfaces are loaded
        interfaces = self.get_interfaces(refresh=refresh, output="dict")

        if name is not None:
            interface = interfaces.get(name)
            if interface is not None:
                return interface
        elif network_name is not None:
            for interface in interfaces.values():
                if (
                    interface is not None
                    and interface.get_network() is not None
                    and interface.get_network().get_name() == network_name
                ):
                    return interface

        raise Exception(f"Interface not found: {name or network_name}")

    # -------------------------------------------------------------------------
    # Static factory methods
    # -------------------------------------------------------------------------

    @staticmethod
    def get_node(slice: SliceV2, node: FimNode) -> NodeV2:
        """
        Factory method to create a NodeV2 from a FIM node.

        Not intended for API use.

        :param slice: the slice this node belongs to
        :type slice: SliceV2
        :param node: the FIM node
        :type node: FimNode
        :return: a NodeV2 instance
        :rtype: NodeV2
        """
        return NodeV2(slice=slice, node=node)

    @staticmethod
    def new_node(
        slice: SliceV2 = None,
        name: str = None,
        site: str = None,
        avoid: List[str] = None,
        validate: bool = False,
        raise_exception: bool = False,
    ) -> NodeV2:
        """
        Creates a new FABRIC node on the slice.

        Not intended for API use. Use slice.add_node() instead.

        :param slice: the fablib slice to build the new node on
        :type slice: SliceV2
        :param name: the name of the new node
        :type name: str
        :param site: the name of the site to build the node on
        :type site: str
        :param avoid: a list of site names to avoid
        :type avoid: List[str]
        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool
        :param raise_exception: Raise exception if validation fails
        :type raise_exception: bool
        :return: a new NodeV2
        :rtype: NodeV2
        """
        if avoid is None:
            avoid = []

        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(avoid=avoid)

        log.info(f"Adding node: {name}, slice: {slice.get_name()}, site: {site}")

        # Create FIM node and NodeV2 instance
        node = NodeV2(
            slice,
            slice.topology.add_node(name=name, site=site),
            validate=validate,
            raise_exception=raise_exception,
        )
        node.set_capacities(
            cores=NodeV2.default_cores, ram=NodeV2.default_ram, disk=NodeV2.default_disk
        )
        node.set_image(NodeV2.default_image)
        node.init_fablib_data()

        return node

    # -------------------------------------------------------------------------
    # Optimized toDict with cached values
    # -------------------------------------------------------------------------

    def toDict(self, skip: List[str] = None) -> dict:
        """
        Returns the node attributes as a dictionary.

        Uses cached values where available for better performance.

        :param skip: list of keys to skip
        :type skip: List[str]
        :return: node attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        rtn_dict = {}

        if "id" not in skip:
            rtn_dict["id"] = self.get_reservation_id()
        if "name" not in skip:
            rtn_dict["name"] = self.get_name()
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
        if "site" not in skip:
            rtn_dict["site"] = self.get_site()
        if "host" not in skip:
            rtn_dict["host"] = str(self.get_host())
        if "username" not in skip:
            rtn_dict["username"] = str(self.get_username())
        if "management_ip" not in skip:
            rtn_dict["management_ip"] = self.get_management_ip()
        if "state" not in skip:
            rtn_dict["state"] = str(self.get_reservation_state())
        if "error" not in skip:
            rtn_dict["error"] = str(self.get_error_message())

        return rtn_dict
