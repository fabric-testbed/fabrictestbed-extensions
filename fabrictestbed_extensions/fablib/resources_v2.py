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
V2 resource classes built on top of ``FabricManagerV2.resources_summary``.

Provides :class:`ResourcesV2Wrapper` with list/show helpers for sites,
hosts, links, and facility ports.  All tabular output goes through
``Utils.list_table`` / ``Utils.show_table``.

The ``resources_summary`` JSON API is the **primary** data source.
A full FIM topology is loaded lazily only when ERO path validation is
required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from fabrictestbed.fabric_manager_v2 import FabricManagerV2
from fabrictestbed.slice_editor import AdvertisedTopology
from fabrictestbed.slice_manager import Status

from fabrictestbed_extensions.fablib.site import ResourceConstants
from fabrictestbed_extensions.utils.utils import Utils

log = logging.getLogger("fablib")


# ------------------------------------------------------------------
# Pretty-name dictionaries
# ------------------------------------------------------------------

SITE_PRETTY_NAMES: Dict[str, str] = {
    "name": "Name",
    "state": "State",
    "address": "Address",
    "location": "Location",
    "ptp_capable": "PTP Capable",
    "ipv4_management": "IPv4 Mgmt",
    "hosts_count": "Hosts",
    "cores_capacity": "Cores Capacity",
    "cores_allocated": "Cores Allocated",
    "cores_available": "Cores Available",
    "ram_capacity": "RAM Capacity",
    "ram_allocated": "RAM Allocated",
    "ram_available": "RAM Available",
    "disk_capacity": "Disk Capacity",
    "disk_allocated": "Disk Allocated",
    "disk_available": "Disk Available",
}

HOST_PRETTY_NAMES: Dict[str, str] = {
    "name": "Name",
    "site": "Site",
    "cores_capacity": "Cores Capacity",
    "cores_allocated": "Cores Allocated",
    "cores_available": "Cores Available",
    "ram_capacity": "RAM Capacity",
    "ram_allocated": "RAM Allocated",
    "ram_available": "RAM Available",
    "disk_capacity": "Disk Capacity",
    "disk_allocated": "Disk Allocated",
    "disk_available": "Disk Available",
}

LINK_PRETTY_NAMES: Dict[str, str] = {
    "name": "Link Name",
    "layer": "Layer",
    "bandwidth": "Capacity (Gbps)",
    "allocated_bandwidth": "Allocated (Gbps)",
    "sites": "Sites",
}

FACILITY_PORT_PRETTY_NAMES: Dict[str, str] = {
    "name": "Name",
    "site": "Site",
    "port": "Port",
    "switch": "Switch",
    "vlans": "VLAN Range",
    "allocated_vlans": "Allocated VLANs",
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_COMPONENT_KEY_MAP: Dict[str, str] = {
    "GPU-Tesla T4": "tesla_t4",
    "GPU-RTX6000": "rtx6000",
    "GPU-A30": "a30",
    "GPU-A40": "a40",
    "SmartNIC-ConnectX-6": "nic_connectx_6",
    "SmartNIC-ConnectX-5": "nic_connectx_5",
    "SmartNIC-ConnectX-7-100": "nic_connectx_7_100",
    "SmartNIC-ConnectX-7-400": "nic_connectx_7_400",
    "SmartNIC-BlueField2-ConnectX-6": "nic_bluefield2_connectx_5",
    "SharedNIC-ConnectX-6": "nic_basic",
    "NVME-P4510": "nvme",
    "FPGA-Xilinx-U280": "fpga_u280",
    "FPGA-Xilinx-SN1022": "fpga_sn1022",
}


def _component_key(model: str) -> str:
    """Map a FIM component model string to a short snake_case key."""
    return _COMPONENT_KEY_MAP.get(model, model.lower().replace("-", "_"))


def _flatten_components(d: Dict[str, Any]) -> Dict[str, Any]:
    """Pop 'components' from *d* and flatten into ``<key>_{capacity,allocated,available}``."""
    components = d.pop("components", {}) or {}
    for model, vals in components.items():
        if not isinstance(vals, dict):
            continue
        key = _component_key(model)
        cap = vals.get("capacity", 0) or 0
        alloc = vals.get("allocated", 0) or 0
        d[f"{key}_capacity"] = cap
        d[f"{key}_allocated"] = alloc
        d[f"{key}_available"] = max(0, cap - alloc)
    return d


def _merged_pretty_names() -> Dict[str, str]:
    """Combine v2 pretty names with the v1 ResourceConstants.pretty_names."""
    merged = dict(ResourceConstants.pretty_names)
    merged.update(SITE_PRETTY_NAMES)
    merged.update(HOST_PRETTY_NAMES)
    return merged


# ==================================================================
# ResourcesV2Wrapper — sites + hosts (main entry point)
# ==================================================================

class ResourcesV2Wrapper:
    """High-performance resource manager backed by ``resources_summary``.

    Uses ``FabricManagerV2.resources_summary()`` to fetch sites, hosts,
    links, and facility ports as plain dicts.  The full FIM topology is
    loaded **lazily** only when ERO path validation is needed.
    """

    def __init__(
        self,
        fablib_manager,
        force_refresh: bool = False,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        avoid: Optional[List[str]] = None,
        includes: Optional[List[str]] = None,
    ):
        self.fablib_manager = fablib_manager

        # Summary-derived caches (lists of plain dicts)
        self._sites_data: List[Dict[str, Any]] = []
        self._hosts_data: List[Dict[str, Any]] = []
        self._links_data: List[Dict[str, Any]] = []
        self._facility_ports_data: List[Dict[str, Any]] = []

        # Keyed lookup for sites
        self._sites_by_name: Dict[str, Dict[str, Any]] = {}

        # FIM topology — loaded lazily for ERO validation only
        self._topology: Optional[AdvertisedTopology] = None
        self._lazy_params: Dict[str, Any] = {}

        self.update(
            force_refresh=force_refresh,
            start=start,
            end=end,
            avoid=avoid,
            includes=includes,
        )

    # ----------------------------------------------------------
    # Loading / refresh
    # ----------------------------------------------------------

    def update(
        self,
        force_refresh: bool = False,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        avoid: Optional[List[str]] = None,
        includes: Optional[List[str]] = None,
    ) -> None:
        """Refresh resource data via ``resources_summary``."""
        log.info("ResourcesV2Wrapper: updating resources via resources_summary")

        self._lazy_params = {
            "force_refresh": force_refresh,
            "start_date": start,
            "end_date": end,
            "avoid": avoid,
            "includes": includes,
        }
        # Invalidate cached topology so it gets re-fetched if needed
        self._topology = None

        manager = self.fablib_manager.get_manager()
        if not isinstance(manager, FabricManagerV2):
            raise Exception(
                "ResourcesV2Wrapper requires FabricManagerV2 as the manager"
            )

        summary = manager.resources_summary(level=2, start=start, end=end, includes=includes, excludes=avoid,
                                            force_refresh=force_refresh)
        if not summary:
            raise Exception(
                "resources_summary returned None — endpoint may be unavailable"
            )

        # ---- sites ----
        raw_sites = summary.get("sites") or []
        self._sites_data = []
        self._sites_by_name = {}
        for s in raw_sites:
            name = s.get("name")
            if not name:
                continue
            if avoid and name in avoid:
                continue
            if includes and name not in includes:
                continue
            self._sites_data.append(s)
            self._sites_by_name[name] = s

        # ---- hosts ----
        self._hosts_data = summary.get("hosts") or []
        # Filter hosts to only those belonging to non-excluded sites
        if avoid or includes:
            valid = set(self._sites_by_name.keys())
            self._hosts_data = [
                h for h in self._hosts_data if h.get("site") in valid
            ]

        # ---- links ----
        self._links_data = summary.get("links") or []

        # ---- facility ports ----
        self._facility_ports_data = summary.get("facility_ports") or []

    # ----------------------------------------------------------
    # Lazy FIM topology (for ERO validation only)
    # ----------------------------------------------------------

    def _ensure_topology_loaded(self) -> None:
        """Load the full FIM topology if not already present."""
        if self._topology is not None:
            return
        log.info("ResourcesV2Wrapper: lazily loading FIM topology for ERO validation")
        manager = self.fablib_manager.get_manager()
        p = self._lazy_params
        return_status, topology = manager.resources(
            force_refresh=p.get("force_refresh", False),
            level=2,
            start_date=p.get("start_date"),
            end_date=p.get("end_date"),
            excludes=p.get("avoid"),
            includes=p.get("includes"),
        )
        if return_status != Status.OK:
            raise Exception(
                f"Failed to get advertised_topology: {return_status}, {topology}"
            )
        self._topology = topology

    # ----------------------------------------------------------
    # Accessors
    # ----------------------------------------------------------

    def get_fablib_manager(self):
        return self.fablib_manager

    def get_topology(self) -> AdvertisedTopology:
        self._ensure_topology_loaded()
        return self._topology

    def get_fim(self) -> AdvertisedTopology:
        self._ensure_topology_loaded()
        return self._topology

    # ----------------------------------------------------------
    # Site accessors
    # ----------------------------------------------------------

    def get_site_names(self) -> List[str]:
        return list(self._sites_by_name.keys())

    def get_site(self, site_name: str) -> Optional[Dict[str, Any]]:
        return self._sites_by_name.get(site_name)

    # ----------------------------------------------------------
    # Site helpers: capacity / allocated / available
    # ----------------------------------------------------------

    def _site_val(self, site_name: str, key: str, default: Any = 0) -> Any:
        s = self._sites_by_name.get(site_name)
        if not s:
            return default
        return s.get(key, default)

    def get_core_capacity(self, site_name: str) -> int:
        return self._site_val(site_name, "cores_capacity", 0)

    def get_core_allocated(self, site_name: str) -> int:
        return self._site_val(site_name, "cores_allocated", 0)

    def get_core_available(self, site_name: str) -> int:
        return self._site_val(site_name, "cores_available", 0)

    def get_ram_capacity(self, site_name: str) -> int:
        return self._site_val(site_name, "ram_capacity", 0)

    def get_ram_allocated(self, site_name: str) -> int:
        return self._site_val(site_name, "ram_allocated", 0)

    def get_ram_available(self, site_name: str) -> int:
        return self._site_val(site_name, "ram_available", 0)

    def get_disk_capacity(self, site_name: str) -> int:
        return self._site_val(site_name, "disk_capacity", 0)

    def get_disk_allocated(self, site_name: str) -> int:
        return self._site_val(site_name, "disk_allocated", 0)

    def get_disk_available(self, site_name: str) -> int:
        return self._site_val(site_name, "disk_available", 0)

    def get_component_capacity(self, site_name: str, component_model_name: str) -> int:
        s = self._sites_by_name.get(site_name)
        if not s:
            return 0
        return (s.get("components") or {}).get(component_model_name, {}).get("capacity", 0)

    def get_component_allocated(self, site_name: str, component_model_name: str) -> int:
        s = self._sites_by_name.get(site_name)
        if not s:
            return 0
        return (s.get("components") or {}).get(component_model_name, {}).get("allocated", 0)

    def get_component_available(self, site_name: str, component_model_name: str) -> int:
        s = self._sites_by_name.get(site_name)
        if not s:
            return 0
        return (s.get("components") or {}).get(component_model_name, {}).get("available", 0)

    def get_location_lat_long(self, site_name: str) -> Tuple[float, float]:
        loc = self._site_val(site_name, "location", None)
        if isinstance(loc, (list, tuple)) and len(loc) == 2:
            return (loc[0], loc[1])
        return (0.0, 0.0)

    def get_location_postal(self, site_name: str) -> str:
        return self._site_val(site_name, "address", "") or ""

    def get_ptp_capable(self, site_name: str) -> bool:
        return bool(self._site_val(site_name, "ptp_capable", False))

    # ----------------------------------------------------------
    # list / show — sites
    # ----------------------------------------------------------

    def __str__(self) -> str:
        return self.list_sites(output="text", quiet=True)

    def _site_table_row(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a flat dict for one site suitable for Utils.list_table."""
        d = dict(site_data)
        _flatten_components(d)
        # Ensure hosts_count is present (summary may use "hosts" as a list)
        if "hosts_count" not in d:
            hosts = d.pop("hosts", None)
            if isinstance(hosts, list):
                d["hosts_count"] = len(hosts)
            elif isinstance(hosts, int):
                d["hosts_count"] = hosts
            else:
                d["hosts_count"] = 0
        return d

    def list_sites(
        self,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        filter_function: Optional[Callable] = None,
        pretty_names: bool = True,
    ) -> object:
        table = []
        for site_data in self._sites_data:
            row = self._site_table_row(site_data)
            if row.get("hosts_count", 0) > 0:
                table.append(row)

        return Utils.list_table(
            table,
            fields=fields,
            title="Sites",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=_merged_pretty_names() if pretty_names else {},
        )

    def show_site(
        self,
        site_name: str,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        pretty_names: bool = True,
    ) -> object:
        site_data = self._sites_by_name.get(site_name)
        if not site_data:
            return f"Site '{site_name}' not found."

        data = self._site_table_row(site_data)
        return Utils.show_table(
            data,
            fields=fields,
            title=f"Site: {site_name}",
            output=output,
            quiet=quiet,
            pretty_names_dict=_merged_pretty_names() if pretty_names else {},
        )

    # ----------------------------------------------------------
    # list / show — hosts
    # ----------------------------------------------------------

    def _host_table_row(self, host_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a flat dict for one host suitable for Utils.list_table."""
        d = dict(host_data)
        _flatten_components(d)
        # Ensure *_available keys are present
        for resource in ("cores", "ram", "disk"):
            if f"{resource}_available" not in d:
                cap = d.get(f"{resource}_capacity", 0) or 0
                alloc = d.get(f"{resource}_allocated", 0) or 0
                d[f"{resource}_available"] = max(0, cap - alloc)
        return d

    def list_hosts(
        self,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        filter_function: Optional[Callable] = None,
        pretty_names: bool = True,
    ) -> object:
        table = [self._host_table_row(h) for h in self._hosts_data]

        return Utils.list_table(
            table,
            fields=fields,
            title="Hosts",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=_merged_pretty_names() if pretty_names else {},
        )

    def show_host(
        self,
        host_name: str,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        pretty_names: bool = True,
    ) -> object:
        for h in self._hosts_data:
            if h.get("name") == host_name:
                data = self._host_table_row(h)
                return Utils.show_table(
                    data,
                    fields=fields,
                    title=f"Host: {host_name}",
                    output=output,
                    quiet=quiet,
                    pretty_names_dict=_merged_pretty_names() if pretty_names else {},
                )
        return f"Host '{host_name}' not found."

    # ----------------------------------------------------------
    # list / show — links
    # ----------------------------------------------------------

    def list_links(
        self,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        filter_function: Optional[Callable] = None,
        pretty_names: bool = True,
    ) -> object:
        return Utils.list_table(
            self._links_data,
            fields=fields,
            title="Links",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=LINK_PRETTY_NAMES if pretty_names else {},
        )

    def show_link(
        self,
        link_name: str,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        pretty_names: bool = True,
    ) -> object:
        for link in self._links_data:
            if link.get("name") == link_name:
                return Utils.show_table(
                    link,
                    fields=fields,
                    title=f"Link: {link_name}",
                    output=output,
                    quiet=quiet,
                    pretty_names_dict=LINK_PRETTY_NAMES if pretty_names else {},
                )
        return f"Link '{link_name}' not found."

    def get_link_list(self) -> List[str]:
        return [l.get("name") for l in self._links_data if l.get("name")]

    # ----------------------------------------------------------
    # list / show — facility ports
    # ----------------------------------------------------------

    def list_facility_ports(
        self,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        filter_function: Optional[Callable] = None,
        pretty_names: bool = True,
    ) -> object:
        return Utils.list_table(
            self._facility_ports_data,
            fields=fields,
            title="Facility Ports",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=FACILITY_PORT_PRETTY_NAMES if pretty_names else {},
        )

    def show_facility_port(
        self,
        fp_name: str,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        pretty_names: bool = True,
    ) -> object:
        for fp in self._facility_ports_data:
            if fp.get("name") == fp_name:
                return Utils.show_table(
                    fp,
                    fields=fields,
                    title=f"Facility Port: {fp_name}",
                    output=output,
                    quiet=quiet,
                    pretty_names_dict=FACILITY_PORT_PRETTY_NAMES if pretty_names else {},
                )
        return f"Facility port '{fp_name}' not found."

    # ----------------------------------------------------------
    # ERO path validation (requires full FIM topology)
    # ----------------------------------------------------------

    def validate_requested_ero_path(
        self, source: str, end: str, hops: List[str]
    ) -> None:
        self._ensure_topology_loaded()

        hop_sites_node_ids = []
        for hop in hops:
            ns = self._topology.network_services.get(f"{hop.upper()}_ns")
            if not ns:
                raise Exception(f"Hop: {hop} is not found in the available sites!")
            hop_sites_node_ids.append(ns.node_id)

        source_site = self._topology.sites.get(source)
        end_site = self._topology.sites.get(end)

        if not source_site or not end_site:
            raise Exception(f"Source {source} or End: {end} is not found!")

        path = self._topology.graph_model.get_nodes_on_path_with_hops(
            node_a=source_site.node_id,
            node_z=end_site.node_id,
            hops=hop_sites_node_ids,
        )
        if not path or not len(path):
            raise Exception(
                f"Requested path via {hops} between {source} and {end} is invalid!"
            )
