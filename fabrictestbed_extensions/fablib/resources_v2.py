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

from fabrictestbed_extensions.fablib.constants import Constants
from fabrictestbed_extensions.fablib.site import ResourceConstants
from fabrictestbed_extensions.utils.utils import Utils

log = logging.getLogger("fablib")


# ------------------------------------------------------------------
# Pretty-name dictionaries
# ------------------------------------------------------------------

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
# Helpers – build ordered dicts matching v1 Site.to_dict / Host.to_dict
# ------------------------------------------------------------------

# Reverse map: FIM model name → v1 non_pretty_name used by attribute_name_mappings
_FIM_MODEL_TO_ATTR: Dict[str, str] = {}
for _attr, _names in ResourceConstants.attribute_name_mappings.items():
    _FIM_MODEL_TO_ATTR[_attr] = _attr          # exact FIM key (lowered)
    _FIM_MODEL_TO_ATTR[_attr.lower()] = _attr   # lowered duplicate safe

# Also map component model names that appear in the summary JSON
# to the attribute_name_mappings key they correspond to.
_SUMMARY_COMP_TO_ATTR: Dict[str, str] = {
    "GPU-Tesla T4": Constants.GPU_TESLA_T4,
    "GPU-RTX6000": Constants.GPU_RTX6000,
    "GPU-A30": Constants.GPU_A30,
    "GPU-A40": Constants.GPU_A40,
    "SmartNIC-ConnectX-6": Constants.SMART_NIC_CONNECTX_6,
    "SmartNIC-ConnectX-5": Constants.SMART_NIC_CONNECTX_5,
    "SmartNIC-ConnectX-7-100": Constants.SMART_NIC_CONNECTX_7_100,
    "SmartNIC-ConnectX-7-400": Constants.SMART_NIC_CONNECTX_7_400,
    "SmartNIC-BlueField2-ConnectX-6": Constants.SMART_NIC_BlueField2_CONNECTX_6,
    "SharedNIC-ConnectX-6": Constants.NIC_SHARED_CONNECTX_6,
    "NVME-P4510": Constants.NVME_P4510,
    "FPGA-Xilinx-U280": Constants.FPGA_XILINX_U280,
    "FPGA-Xilinx-SN1022": Constants.FPGA_XILINX_SN1022,
}


def _site_summary_to_v1_dict(site_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a resources_summary site dict to a v1-compatible ordered dict.

    The key order and key names match ``Site.to_dict()`` exactly so that
    ``Utils.list_table`` renders identical columns.
    """
    # -- header fields (same order as Site.to_dict) --
    hosts_raw = site_data.get("hosts")
    if isinstance(hosts_raw, list):
        hosts_count = len(hosts_raw)
    elif isinstance(hosts_raw, int):
        hosts_count = hosts_raw
    else:
        hosts_count = site_data.get("hosts_count", 0)

    d: Dict[str, Any] = {
        "name": site_data.get("name"),
        "state": site_data.get("state"),
        "address": site_data.get("address"),
        "location": site_data.get("location"),
        "ptp_capable": site_data.get("ptp_capable"),
        "hosts": hosts_count,
        "cpus": site_data.get("cores_capacity", 0),
    }

    # Build a lookup from attribute_name_mappings key → {capacity, allocated}
    # sourced from the flat summary keys and nested components dict.
    components = site_data.get("components") or {}

    def _get_cap_alloc(attr_key: str) -> Tuple[int, int]:
        """Return (capacity, allocated) for a given attribute_name_mappings key."""
        low = attr_key.lower()
        # cores / ram / disk come as flat top-level keys
        names = ResourceConstants.attribute_name_mappings[attr_key]
        non_pretty = names.get(Constants.NON_PRETTY_NAME)

        # Try flat summary keys first (e.g. cores_capacity, ram_capacity)
        cap_key = f"{low}_capacity"
        alloc_key = f"{low}_allocated"
        if cap_key in site_data:
            return (site_data.get(cap_key, 0) or 0,
                    site_data.get(alloc_key, 0) or 0)

        # Try components dict (keyed by FIM model name)
        for comp_name, const_key in _SUMMARY_COMP_TO_ATTR.items():
            if const_key == attr_key and comp_name in components:
                cv = components[comp_name]
                if isinstance(cv, dict):
                    return (cv.get("capacity", 0) or 0,
                            cv.get("allocated", 0) or 0)

        # Also try lowercased component key
        if low in components:
            cv = components[low]
            if isinstance(cv, dict):
                return (cv.get("capacity", 0) or 0,
                        cv.get("allocated", 0) or 0)

        return (0, 0)

    # -- iterate in the exact order defined by attribute_name_mappings --
    for attr_key, names in ResourceConstants.attribute_name_mappings.items():
        non_pretty = names.get(Constants.NON_PRETTY_NAME)
        cap, alloc = _get_cap_alloc(attr_key)
        avail = cap - alloc
        d[f"{non_pretty}_{Constants.AVAILABLE.lower()}"] = avail
        d[f"{non_pretty}_{Constants.CAPACITY.lower()}"] = cap
        d[f"{non_pretty}_{Constants.ALLOCATED.lower()}"] = alloc

    return d


def _host_summary_to_v1_dict(host_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a resources_summary host dict to a v1-compatible ordered dict.

    The key order and key names match ``Host.to_dict()`` exactly.
    """
    d: Dict[str, Any] = {
        "name": host_data.get("name"),
        "state": host_data.get("state"),
        "address": host_data.get("address"),
        "location": host_data.get("location"),
        "ptp_capable": host_data.get("ptp_capable"),
    }

    components = host_data.get("components") or {}

    def _get_cap_alloc(attr_key: str) -> Tuple[int, int]:
        low = attr_key.lower()
        # cores / ram / disk come as flat keys
        cap_key = f"{low}_capacity"
        alloc_key = f"{low}_allocated"
        if cap_key in host_data:
            return (host_data.get(cap_key, 0) or 0,
                    host_data.get(alloc_key, 0) or 0)

        for comp_name, const_key in _SUMMARY_COMP_TO_ATTR.items():
            if const_key == attr_key and comp_name in components:
                cv = components[comp_name]
                if isinstance(cv, dict):
                    return (cv.get("capacity", 0) or 0,
                            cv.get("allocated", 0) or 0)

        if low in components:
            cv = components[low]
            if isinstance(cv, dict):
                return (cv.get("capacity", 0) or 0,
                        cv.get("allocated", 0) or 0)

        return (0, 0)

    for attr_key, names in ResourceConstants.attribute_name_mappings.items():
        # Host.to_dict skips P4-Switch
        if attr_key in Constants.P4_SWITCH:
            continue
        non_pretty = names.get(Constants.NON_PRETTY_NAME)
        cap, alloc = _get_cap_alloc(attr_key)
        avail = cap - alloc
        d[f"{non_pretty}_{Constants.AVAILABLE.lower()}"] = avail
        d[f"{non_pretty}_{Constants.CAPACITY.lower()}"] = cap
        d[f"{non_pretty}_{Constants.ALLOCATED.lower()}"] = alloc

    return d


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
            row = _site_summary_to_v1_dict(site_data)
            if row.get("hosts") or row.get("hosts_count"):
                table.append(row)

        return Utils.list_table(
            table,
            fields=fields,
            title="Sites",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=ResourceConstants.pretty_names if pretty_names else {},
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

        data = _site_summary_to_v1_dict(site_data)
        return Utils.show_table(
            data,
            fields=fields,
            title=f"Site: {site_name}",
            output=output,
            quiet=quiet,
            pretty_names_dict=ResourceConstants.pretty_names if pretty_names else {},
        )

    # ----------------------------------------------------------
    # list / show — hosts
    # ----------------------------------------------------------

    def list_hosts(
        self,
        output: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quiet: bool = False,
        filter_function: Optional[Callable] = None,
        pretty_names: bool = True,
    ) -> object:
        table = [_host_summary_to_v1_dict(h) for h in self._hosts_data]

        return Utils.list_table(
            table,
            fields=fields,
            title="Hosts",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=ResourceConstants.pretty_names if pretty_names else {},
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
                data = _host_summary_to_v1_dict(h)
                return Utils.show_table(
                    data,
                    fields=fields,
                    title=f"Host: {host_name}",
                    output=output,
                    quiet=quiet,
                    pretty_names_dict=ResourceConstants.pretty_names if pretty_names else {},
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
