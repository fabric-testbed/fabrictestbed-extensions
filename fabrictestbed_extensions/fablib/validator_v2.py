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
Node validation against ResourcesV2 plain-dict resource data.

Provides :class:`NodeValidatorV2` with static methods for checking whether
requested nodes can be allocated on FABRIC hosts, working entirely with
the plain dicts returned by :class:`ResourcesV2`.

Extracted from ``FablibManagerV2`` to separate validation concerns from
the manager facade.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple

from fabrictestbed_extensions.fablib.node import Node

log = logging.getLogger("fablib")


class NodeValidatorV2:
    """Validates node allocation against ResourcesV2 plain-dict data.

    All methods are ``@staticmethod`` — no instance state is needed.
    The validator is purely functional: give it resource dicts and nodes,
    get back pass/fail results.
    """

    @staticmethod
    def can_allocate_node_in_host(
        host: Dict[str, Any],
        node: Node,
        allocated: dict,
        site: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Check if a node fits on a specific host given current allocations.

        :param host: Host dict from ResourcesV2 (keys: name, state,
            cores_available, ram_available, disk_available, components)
        :param node: Node being validated
        :param allocated: Mutable dict tracking cumulative allocations
            on this host.  Updated in-place when allocation succeeds.
        :param site: Site dict from ResourcesV2
        :return: (success, message)
        """
        if host is None or site is None:
            return (
                True,
                f"Ignoring validation: Host: {host}, Site: {site} not available.",
            )

        host_name = host.get("name", "unknown")
        msg = f"Node can be allocated on the host: {host_name}."

        host_state = host.get("state", "")
        if host_state != "Active":
            msg = (
                f"Node cannot be allocated on {host_name}, "
                f"{host_name} is in {host_state}!"
            )
            return False, msg

        allocated_core = allocated.setdefault("core", 0)
        allocated_ram = allocated.setdefault("ram", 0)
        allocated_disk = allocated.setdefault("disk", 0)
        available_cores = (host.get("cores_available", 0) or 0) - allocated_core
        available_ram = (host.get("ram_available", 0) or 0) - allocated_ram
        available_disk = (host.get("disk_available", 0) or 0) - allocated_disk

        if (
            node.get_requested_cores() > available_cores
            or node.get_requested_disk() > available_disk
            or node.get_requested_ram() > available_ram
        ):
            msg = (
                f"Insufficient Resources: Host: {host_name} "
                f"does not meet core/ram/disk requirements."
            )
            return False, msg

        # Check if there are enough components available
        host_components = host.get("components") or {}
        for c in node.get_components():
            comp_model_type = f"{c.get_type()}-{c.get_fim_model()}"
            comp_data = host_components.get(comp_model_type)
            if not comp_data:
                msg = (
                    f"Invalid Request: Host: {host_name} does not have "
                    f"the requested component: {comp_model_type}."
                )
                return False, msg

            allocated_comp_count = allocated.setdefault(comp_model_type, 0)
            comp_capacity = comp_data.get("capacity", 0) or 0
            comp_allocated = comp_data.get("allocated", 0) or 0
            available_comps = comp_capacity - comp_allocated - allocated_comp_count
            if available_comps <= 0:
                msg = (
                    f"Insufficient Resources: Host: {host_name} has reached "
                    f"the limit for component: {comp_model_type}."
                )
                return False, msg

            allocated[comp_model_type] += 1

        allocated["core"] += node.get_requested_cores()
        allocated["ram"] += node.get_requested_ram()
        allocated["disk"] += node.get_requested_disk()

        return True, msg

    @staticmethod
    def validate_node(
        node: Node,
        resources,
        allocated: Optional[dict] = None,
    ) -> Tuple[bool, str]:
        """Validate a single node against available resources.

        Unlike the former ``FablibManagerV2.validate_node``, this accepts
        a :class:`ResourcesV2` instance directly rather than calling
        ``self.get_resources()``.

        :param node: The node to validate
        :param resources: A ``ResourcesV2`` instance (already fetched)
        :param allocated: Optional dict tracking cumulative host allocations
            across multiple ``validate_node`` calls.  Keyed by
            ``host_name -> {resource_type -> count}``.
        :return: (success, message)
        """
        try:
            error = None
            if allocated is None:
                allocated = {}

            site_name = node.get_site()
            site = resources.get_site(site_name=site_name)

            if not site:
                log.warning(
                    f"Ignoring validation: Site: {site_name} not available in resources."
                )
                return (
                    True,
                    f"Ignoring validation: Site: {site_name} not available in resources.",
                )

            site_state = site.get("state", "")
            if site_state != "Active":
                msg = (
                    f"Node cannot be allocated on {site_name}, "
                    f"{site_name} is in {site_state}."
                )
                log.error(msg)
                return False, msg

            hosts = resources.get_hosts_by_site(site_name=site_name)
            if not hosts:
                msg = (
                    f"Node cannot be validated, host information "
                    f"not available for {site_name}."
                )
                log.error(msg)
                return False, msg

            # If a specific host is requested, validate only against it.
            if node.get_host():
                if node.get_host() not in hosts:
                    msg = (
                        f"Invalid Request: Requested Host {node.get_host()} "
                        f"does not exist on site: {site_name}."
                    )
                    log.error(msg)
                    return False, msg

                host = hosts.get(node.get_host())
                allocated_comps = allocated.setdefault(node.get_host(), {})
                status, error = NodeValidatorV2.can_allocate_node_in_host(
                    host=host, node=node, allocated=allocated_comps, site=site
                )
                if not status:
                    log.error(error)
                return status, error

            # No specific host — try each host until one fits.
            for host_name, host in hosts.items():
                allocated_comps = allocated.setdefault(host_name, {})
                status, error = NodeValidatorV2.can_allocate_node_in_host(
                    host=host, node=node, allocated=allocated_comps, site=site
                )
                if status:
                    return status, error

            msg = (
                f"Invalid Request: Requested Node cannot be accommodated "
                f"by any of the hosts on site: {site_name}."
            )
            if error:
                msg += f" Details: {error}"
            log.error(msg)
            return False, msg
        except Exception as e:
            log.error(e)
            log.error(traceback.format_exc())
            return False, str(e)

    @staticmethod
    def validate_nodes(
        nodes: List[Node],
        resources,
    ) -> Tuple[bool, Dict[str, str]]:
        """Batch-validate multiple nodes sharing a single allocated dict.

        Resources are fetched once by the caller and passed in.
        This is the optimised entry point for ``SliceV2.validate()``.

        :param nodes: List of Node objects to validate
        :param resources: A ``ResourcesV2`` instance (pre-fetched)
        :return: (all_valid, errors) where errors maps node_name to message
        """
        allocated: Dict[str, dict] = {}
        errors: Dict[str, str] = {}
        for node in nodes:
            status, error = NodeValidatorV2.validate_node(
                node=node, resources=resources, allocated=allocated
            )
            if not status:
                errors[node.get_name()] = error
        return len(errors) == 0, errors
