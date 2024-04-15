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
Methods to work with FABRIC `resources`_.

.. _`resources`: https://learn.fabric-testbed.net/knowledge-base/glossary/#resource
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Dict, List, Tuple

from fabrictestbed.slice_editor import AdvertisedTopology, Capacities
from fabrictestbed.slice_manager import Status
from fim.slivers import network_node
from fim.user import interface, link, node
from fim.view_only_dict import ViewOnlyDict
from tabulate import tabulate


class Resources:
    NON_PRETTY_NAME = "non_pretty_name"
    PRETTY_NAME = "pretty_name"
    HEADER_NAME = "header_name"
    AVAILABLE = "Available"
    CAPACITY = "Capacity"
    ALLOCATED = "Allocated"
    VALUE = "value"

    NIC_SHARED_CONNECTX_6 = "SharedNIC-ConnectX-6"
    SMART_NIC_CONNECTX_6 = "SmartNIC-ConnectX-6"
    SMART_NIC_CONNECTX_5 = "SmartNIC-ConnectX-5"
    NVME_P4510 = "NVME-P4510"
    GPU_TESLA_T4 = "GPU-Tesla T4"
    GPU_RTX6000 = "GPU-RTX6000"
    GPU_A30 = "GPU-A30"
    GPU_A40 = "GPU-A40"
    FPGA_XILINX_U280 = "FPGA-Xilinx-U280"
    CORES = "Cores"
    RAM = "Ram"
    DISK = "Disk"
    CPUS = "CPUs"
    HOSTS = "Hosts"

    site_attribute_name_mappings = {
        CORES.lower(): {NON_PRETTY_NAME: CORES.lower(), PRETTY_NAME: CORES, HEADER_NAME: CORES},
        RAM.lower(): {
            NON_PRETTY_NAME: RAM.lower(),
            PRETTY_NAME: RAM,
            HEADER_NAME: f"{RAM} ({Capacities.UNITS[RAM.lower()]})",
        },
        DISK: {
            NON_PRETTY_NAME: DISK.lower(),
            PRETTY_NAME: DISK,
            HEADER_NAME: f"{DISK} ({Capacities.UNITS[DISK.lower()]})",
        },
        NIC_SHARED_CONNECTX_6: {
            NON_PRETTY_NAME: "nic_basic",
            PRETTY_NAME: "Basic NIC",
            HEADER_NAME: "Basic (100 Gbps NIC)",
        },
        SMART_NIC_CONNECTX_6: {
            NON_PRETTY_NAME: "nic_connectx_6",
            PRETTY_NAME: "ConnectX-6",
            HEADER_NAME: "ConnectX-6 (100 Gbps x2 NIC)",
        },
        SMART_NIC_CONNECTX_5: {
            NON_PRETTY_NAME: "nic_connectx_5",
            PRETTY_NAME: "ConnectX-5",
            HEADER_NAME: "ConnectX-5 (25 Gbps x2 NIC)",
        },
        NVME_P4510: {
            NON_PRETTY_NAME: "nvme",
            PRETTY_NAME: "NVMe",
            HEADER_NAME: "P4510 (NVMe 1TB)",
        },
        GPU_TESLA_T4: {
            NON_PRETTY_NAME: "tesla_t4",
            PRETTY_NAME: "Tesla T4",
            HEADER_NAME: "Tesla T4 (GPU)",
        },
        GPU_RTX6000: {
            NON_PRETTY_NAME: "rtx6000",
            PRETTY_NAME: "RTX6000",
            HEADER_NAME: "RTX6000 (GPU)",
        },
        GPU_A30: {
            NON_PRETTY_NAME: "a30",
            PRETTY_NAME: "A30",
            HEADER_NAME: "A30 (GPU)",
        },
        GPU_A40: {
            NON_PRETTY_NAME: "a40",
            PRETTY_NAME: "A40",
            HEADER_NAME: "A40 (GPU)",
        },
        FPGA_XILINX_U280: {
            NON_PRETTY_NAME: "fpga_u280",
            PRETTY_NAME: "U280",
            HEADER_NAME: "FPGA-Xilinx-U280",
        },
    }
    site_pretty_names = {
        "name": "Name",
        "state": "State",
        "address": "Address",
        "location": "Location",
        "ptp_capable": "PTP Capable",
        HOSTS.lower(): HOSTS,
        CPUS.lower(): CPUS,
    }
    for attribute, names in site_attribute_name_mappings.items():
        non_pretty_name = names.get(NON_PRETTY_NAME)
        pretty_name = names.get(PRETTY_NAME)
        site_pretty_names[non_pretty_name] = pretty_name
        site_pretty_names[
            f"{non_pretty_name}_{AVAILABLE.lower()}"
        ] = f"{pretty_name} {AVAILABLE}"
        site_pretty_names[
            f"{non_pretty_name}_{CAPACITY.lower()}"
        ] = f"{pretty_name} {CAPACITY}"
        site_pretty_names[
            f"{non_pretty_name}_{ALLOCATED.lower()}"
        ] = f"{pretty_name} {ALLOCATED}"

    def __init__(self, fablib_manager, force_refresh: bool = False):
        """
        :param fablib_manager: a :class:`FablibManager` instance.
        :type fablib_manager: fablib.FablibManager

        :param force_refresh: force a refresh of available testbed
            resources.
        :type force_refresh: bool
        """
        super().__init__()

        self.fablib_manager = fablib_manager

        self.topology = None

        self.update(force_refresh=force_refresh)

    def __str__(self) -> str:
        """
        Creates a tabulated string of all the available resources.

        Intended for printing available resources.

        :return: Tabulated string of available resources
        :rtype: String
        """
        table = []
        headers = [
            "Name",
            "PTP Capable",
            self.CPUS,
        ]
        for site_name, site in self.topology.sites.items():
            site_info = self.get_site_info(site)
            row = [
                site.name,
                self.get_ptp_capable(site),
                self.get_cpu_capacity(site),
            ]
            for attribute, names in self.site_attribute_name_mappings.items():
                allocated = site_info.get(attribute, {}).get(self.ALLOCATED.lower(), 0)
                capacity = site_info.get(attribute, {}).get(self.CAPACITY.lower(), 0)
                available = capacity - allocated
                row.append(f"{available}/{capacity}")
                headers.append(names.get(self.HEADER_NAME))

            table.append(row)

        return tabulate(
            table,
            headers=headers,
        )

    def show_site(
        self,
        site_name: str,
        output: str = None,
        fields: list[str] = None,
        quiet: bool = False,
        pretty_names=True,
        latlon=True,
    ) -> str:
        """
        Creates a tabulated string of all the available resources at a specific site.

        Intended for printing available resources at a site.

        :param site_name: site name
        :type site_name: String
        :return: Tabulated string of available resources
        :rtype: String
        """
        site = self.topology.sites[site_name]

        data = self.site_to_dict(site, latlon=latlon)

        if pretty_names:
            pretty_names_dict = self.site_pretty_names
        else:
            pretty_names_dict = {}

        site_table = self.get_fablib_manager().show_table(
            data,
            fields=fields,
            title="Site",
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

        return site_table

    def get_site_names(self) -> List[str]:
        """
        Gets a list of all currently available site names

        :return: list of site names
        :rtype: List[String]
        """
        site_name_list = []
        for site_name in self.topology.sites.keys():
            site_name_list.append(str(site_name))

        return site_name_list

    def get_topology_site(self, site_name: str) -> node.Node:
        """
        Not recommended for most users.
        """
        try:
            return self.topology.sites[site_name]
        except Exception as e:
            logging.warning(f"Failed to get site {site_name}")

    def get_state(self, site: str or node.Node or network_node.NodeSliver) -> str:
        """
        Gets the maintenance state of the node

        :param site: site Node or NodeSliver object or name
        :type site: String or Node or NodeSliver
        :return: str(MaintenanceState)
        """
        site_name = ""
        try:
            if isinstance(site, network_node.NodeSliver):
                return str(site.maintenance_info.get(site.get_name()).state)
            if isinstance(site, node.Node):
                return str(site.maintenance_info.get(site.name).state)
            return str(self.get_topology_site(site).maintenance_info.get(site).state)
        except Exception as e:
            # logging.warning(f"Failed to get site state {site_name}")
            return ""

    def get_nodes(self, site: str or network_node.NodeSliver) -> ViewOnlyDict:
        """
        Get worker nodes on a site
        :param site: site name
        :type site: String
        """
        try:
            from fim.graph.abc_property_graph import ABCPropertyGraph

            if isinstance(site, str):
                site = self.get_topology_site(site)

            node_id_list = site.topo.graph_model.get_first_neighbor(
                node_id=site.node_id,
                rel=ABCPropertyGraph.REL_HAS,
                node_label=ABCPropertyGraph.CLASS_NetworkNode,
            )
            ret = dict()
            for nid in node_id_list:
                _, node_props = site.topo.graph_model.get_node_properties(node_id=nid)
                n = node.Node(
                    name=node_props[ABCPropertyGraph.PROP_NAME],
                    node_id=nid,
                    topo=site.topo,
                )
                # exclude Facility nodes
                from fim.user import NodeType

                if n.type != NodeType.Facility:
                    ret[n.name] = n
            return ViewOnlyDict(ret)
        except Exception as e:
            logging.error(f"Error occurred - {e}")
            logging.error(traceback.format_exc())

    def get_site_info(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> Dict[str, Dict[str, int]]:
        """
        Gets the total site capacity of all components for a site

        :param site: site object or sliver or site name
        :type site: String or Node or NodeSliver
        :return: total component capacity for all components
        :rtype: Dict[str, int]
        """
        site_info = {}

        try:
            nodes = self.get_nodes(site=site)
            site_info[self.CORES.lower()] = {
                self.CAPACITY.lower(): site.capacities.core,
                self.ALLOCATED.lower(): site.capacity_allocations.core
                if site.capacity_allocations
                else 0,
            }
            site_info[self.RAM.lower()] = {
                self.CAPACITY.lower(): site.capacities.ram,
                self.ALLOCATED.lower(): site.capacity_allocations.ram
                if site.capacity_allocations
                else 0,
            }
            site_info[self.DISK.lower()] = {
                self.CAPACITY.lower(): site.capacities.disk,
                self.ALLOCATED.lower(): site.capacity_allocations.disk
                if site.capacity_allocations
                else 0,
            }

            if nodes:
                for w in nodes.values():
                    if w.components:
                        for component_model_name, c in w.components.items():
                            comp_cap = site_info.setdefault(component_model_name, {})
                            comp_cap.setdefault(self.CAPACITY.lower(), 0)
                            comp_cap.setdefault(self.ALLOCATED.lower(), 0)
                            comp_cap[self.CAPACITY.lower()] += c.capacities.unit
                            if c.capacity_allocations:
                                comp_cap[
                                    self.ALLOCATED.lower()
                                ] += c.capacity_allocations.unit

            return site_info
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            return site_info

    def get_component_capacity(
        self,
        site: str or node.Node or network_node.NodeSliver,
        component_model_name: str,
    ) -> int:
        """
        Gets the total site capacity of a component by model name.

        :param site: site object or sliver or site name
        :type site: String or Node or NodeSliver
        :param component_model_name: component model name
        :type component_model_name: String
        :return: total component capacity
        :rtype: int
        """
        component_capacity = 0
        try:
            nodes = self.get_nodes(site=site)
            if nodes:
                for w in nodes.values():
                    if component_model_name in w.components:
                        component_capacity += w.components[
                            component_model_name
                        ].capacities.unit
            return component_capacity
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            return component_capacity

    def get_component_allocated(
        self,
        site: str or node.Node or network_node.NodeSliver,
        component_model_name: str,
    ) -> int:
        """
        Gets gets number of currently allocated components on a the site
        by the component by model name.

        :param site: site object or site name
        :type site: String or Node or NodeSliver
        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently allocated component of this model
        :rtype: int
        """
        component_allocated = 0
        try:
            nodes = self.get_nodes(site=site)
            if nodes:
                for w in nodes.values():
                    if (
                        component_model_name in w.components
                        and w.components[component_model_name].capacity_allocations
                    ):
                        component_allocated += w.components[
                            component_model_name
                        ].capacity_allocations.unit
            return component_allocated
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} allocated {site}: {e}")
            return component_allocated

    def get_component_available(
        self,
        site: str or node.Node or network_node.NodeSliver,
        component_model_name: str,
    ) -> int:
        """
        Gets gets number of currently available components on the site
        by the component by model name.

        :param site: site object or site name
        :type site: String or Node or NodeSliver
        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently available component of this model
        :rtype: int
        """
        try:
            return self.get_component_capacity(
                site, component_model_name
            ) - self.get_component_allocated(site, component_model_name)
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} available {site}")
            return self.get_component_capacity(site, component_model_name)

    def get_location_lat_long(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> Tuple[float, float]:
        """
        Gets gets location of a site in latitude and longitude

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: latitude and longitude of the site
        :rtype: Tuple(float,float)
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_location().to_latlon()
            if isinstance(site, node.Node):
                return site.location.to_latlon()
            return self.get_topology_site(site).location.to_latlon()
        except Exception as e:
            # logging.warning(f"Failed to get location postal {site}")
            return 0, 0

    def get_location_postal(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> str:
        """
        Gets the location of a site by postal address

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: postal address of the site
        :rtype: String
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_location().postal
            if isinstance(site, node.Node):
                return site.location.postal
            return self.get_topology_site(site).location.postal
        except Exception as e:
            # logging.debug(f"Failed to get location postal {site}")
            return ""

    def get_host_capacity(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the number of worker hosts at the site

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: host count
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacities().unit
            if isinstance(site, node.Node):
                return site.capacities.unit
            return self.get_topology_site(site).capacities.unit
        except Exception as e:
            # logging.debug(f"Failed to get host count {site}")
            return 0

    def get_cpu_capacity(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the total number of cpus at the site

        :param site: site name or site object
        :type site: String or node.Node or NodeSliver
        :return: cpu count
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacities().cpu
            if isinstance(site, node.Node):
                return site.capacities.cpu
            return self.get_topology_site(site).capacities.cpu
        except Exception as e:
            # logging.debug(f"Failed to get cpu capacity {site}")
            return 0

    def get_core_capacity(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the total number of cores at the site

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: core count
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacities().core
            if isinstance(site, node.Node):
                return site.capacities.core
            return self.get_topology_site(site).capacities.core
        except Exception as e:
            # logging.debug(f"Failed to get core capacity {site}")
            return 0

    def get_core_allocated(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the number of currently allocated cores at the site

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: core count
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacity_allocations().core
            if isinstance(site, node.Node):
                return site.capacity_allocations.core
            return self.get_topology_site(site).capacity_allocations.core
        except Exception as e:
            # logging.debug(f"Failed to get cores allocated {site}")
            return 0

    def get_core_available(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the number of currently available cores at the site

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: core count
        :rtype: int
        """
        try:
            return self.get_core_capacity(site) - self.get_core_allocated(site)
        except Exception as e:
            # logging.debug(f"Failed to get cores available {site}")
            return self.get_core_capacity(site)

    def get_ram_capacity(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the total amount of memory at the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacities().ram
            if isinstance(site, node.Node):
                return site.capacities.ram
            return self.get_topology_site(site).capacities.ram
        except Exception as e:
            # logging.debug(f"Failed to get ram capacity {site}")
            return 0

    def get_ram_allocated(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the amount of memory currently  allocated the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacity_allocations().ram
            if isinstance(site, node.Node):
                return site.capacity_allocations.ram
            return self.get_topology_site(site).capacity_allocations.ram
        except Exception as e:
            # logging.debug(f"Failed to get ram allocated {site}")
            return 0

    def get_ram_available(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the amount of memory currently  available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            return self.get_ram_capacity(site) - self.get_ram_allocated(site)
        except Exception as e:
            # logging.debug(f"Failed to get ram available {site_name}")
            return self.get_ram_capacity(site)

    def get_disk_capacity(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the total amount of disk available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacities().disk
            if isinstance(site, node.Node):
                return site.capacities.disk
            return self.get_topology_site(site).capacities.disk
        except Exception as e:
            # logging.debug(f"Failed to get disk capacity {site}")
            return 0

    def get_disk_allocated(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the amount of disk allocated the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.get_capacity_allocations().disk
            if isinstance(site, node.Node):
                return site.capacity_allocations.disk
            return self.get_topology_site(site).capacity_allocations.disk
        except Exception as e:
            # logging.debug(f"Failed to get disk allocated {site}")
            return 0

    def get_disk_available(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> int:
        """
        Gets the amount of disk available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            return self.get_disk_capacity(site) - self.get_disk_allocated(site)
        except Exception as e:
            # logging.debug(f"Failed to get disk available {site_name}")
            return self.get_disk_capacity(site)

    def get_ptp_capable(
        self, site: str or node.Node or network_node.NodeSliver
    ) -> bool:
        """
        Gets the PTP flag of the site - if it has a native PTP capability
        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: boolean flag
        :rtype: bool
        """
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.flags.ptp
            if isinstance(site, node.Node):
                return site.flags.ptp
            return self.get_topology_site(site).flags.ptp
        except Exception as e:
            # logging.debug(f"Failed to get PTP status for {site}")
            return False

    def get_fablib_manager(self):
        return self.fablib_manager

    def update(self, force_refresh: bool = False):
        """
        Update the available resources by querying the FABRIC services

        """
        logging.info(f"Updating available resources")
        return_status, topology = (
            self.get_fablib_manager()
            .get_slice_manager()
            .resources(force_refresh=force_refresh, level=2)
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to get advertised_topology: {}, {}".format(
                    return_status, topology
                )
            )

        self.topology = topology

    def get_topology(self, update: bool = False) -> AdvertisedTopology:
        """
        Not intended for API use
        """
        if update or self.topology is None:
            self.update()

        return self.topology

    def get_site_list(self, update: bool = False) -> List[str]:
        """
        Gets a list of all sites by name

        :param update: (optional) set to True update available resources
        :type update: bool
        :return: list of site names
        :rtype: List[String]
        """
        if update or self.topology is None:
            self.update()

        rtn_sites = []
        for site_name, site in self.topology.sites.items():
            rtn_sites.append(site_name)

        return rtn_sites

    def get_link_list(self, update: bool = False) -> List[str]:
        """
        Gets a list of all links by name

        :param update: (optional) set to True update available resources
        :type update: bool
        :return: list of link names
        :rtype: List[String]
        """
        if update:
            self.update()

        rtn_links = []
        for link_name, link in self.topology.links.items():
            rtn_links.append(link_name)

        return rtn_links

    def site_to_json(self, site, latlon=True):
        return json.dumps(self.site_to_dict(site, latlon=latlon), indent=4)

    def site_to_dict(
        self, site: str or node.Node or network_node.NodeSliver, latlon=True
    ):
        """
        Convert site information into a dictionary

        :param site: site name or site object
        :param latlon: convert address to latlon (makes online call to openstreetmaps.org)
        """
        site_info = self.get_site_info(site)
        d = {
            "name": site.name if isinstance(site, node.Node) else site.get_name(),
            "state": self.get_state(site),
            "address": self.get_location_postal(site),
            "location": self.get_location_lat_long(site) if latlon else "",
            "ptp_capable": self.get_ptp_capable(site),
            "hosts": self.get_host_capacity(site),
            "cpus": self.get_cpu_capacity(site),
        }

        for attribute, names in self.site_attribute_name_mappings.items():
            capacity = site_info.get(attribute, {}).get(self.CAPACITY.lower(), 0)
            allocated = site_info.get(attribute, {}).get(self.ALLOCATED.lower(), 0)
            available = capacity - allocated
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.AVAILABLE.lower()}"] = available
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.CAPACITY.lower()}"] = capacity
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.ALLOCATED.lower()}"] = allocated

        if not latlon:
            d.pop("location")

        return d

    def site_to_dictXXX(self, site):
        site_name = site.name
        site_info = self.get_site_info(site)
        d = {
            "name": {self.PRETTY_NAME: "Name", self.VALUE: site.name},
            "address": {
                self.PRETTY_NAME: "Address",
                self.VALUE: self.get_location_postal(site_name),
            },
            "location": {
                self.PRETTY_NAME: "Location",
                self.VALUE: self.get_location_lat_long(site_name),
            },
            "ptp": {
                self.PRETTY_NAME: "PTP Capable",
                self.VALUE: self.get_ptp_capable(site),
            },
            self.HOSTS.lower(): {
                self.PRETTY_NAME: self.HOSTS,
                self.VALUE: self.get_host_capacity(site_name),
            },
            self.CPUS.lower(): {
                self.PRETTY_NAME: self.CPUS,
                self.VALUE: self.get_cpu_capacity(site_name),
            },
        }

        for attribute, names in self.site_attribute_name_mappings.items():
            capacity = site_info.get(attribute, {}).get(self.CAPACITY.lower(), 0)
            allocated = site_info.get(attribute, {}).get(self.ALLOCATED.lower(), 0)
            available = capacity - allocated

            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.AVAILABLE.lower()}"] = {
                self.PRETTY_NAME: f"{names.get(self.PRETTY_NAME)} {self.AVAILABLE}",
                self.VALUE: available,
            }
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.CAPACITY.lower()}"] = {
                self.PRETTY_NAME: f"{names.get(self.PRETTY_NAME)} {self.CAPACITY}",
                self.VALUE: capacity,
            }
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.ALLOCATED.lower()}"] = {
                self.PRETTY_NAME: f"{names.get(self.PRETTY_NAME)} {self.ALLOCATED}",
                self.VALUE: allocated,
            }

        return d

    def list_sites(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
        latlon=True,
    ):
        table = []
        for site_name, site in self.topology.sites.items():
            site_dict = self.site_to_dict(site, latlon=latlon)
            if site_dict.get("hosts"):
                table.append(site_dict)

        if pretty_names:
            pretty_names_dict = self.site_pretty_names
        else:
            pretty_names_dict = {}

        return self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Sites",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )


class Links(Resources):
    link_pretty_names = {
        "site_names": "Sites",
        "node_id": "Link Name",
        "link_capacity_Gbps": "Capacity (Gbps)",
        "link_layer": "Link Layer",
    }

    def __init__(self, fablib_manager):
        """
        Constructor
        :return:
        """
        super().__init__(fablib_manager)

    def __str__(self) -> str:
        """
        Creates a tabulated string of all the links.

        Intended for printing available resources.

        :return: Tabulated string of available resources
        :rtype: String
        """
        table = []
        for _, link in self.topology.links.items():
            iface = link.interface_list[0]
            site_names = iface.name.split("_")
            if iface.type.name == "TrunkPort" and "HundredGig" not in site_names[0]:
                table.append(
                    [
                        tuple(site_names),
                        link.node_id,
                        iface.capacities.bw if iface.capacities else "N/A",
                        link.layer,
                    ]
                )

        return tabulate(
            table,
            headers=[
                "site_names",
                "node_id",
                "link_capacity_Gbps",
                "link_layer",
            ],
        )

    def link_to_dict(self, link: link.Link, iface: interface.Interface) -> dict:
        """
        Converts the link resources to a dictionary.

        Intended for printing links in table format.

        :return: collection of link properties
        :rtype: dict
        """
        return {
            "site_names": tuple(iface.name.split("_")),
            "node_id": link.node_id,
            "link_capacity_Gbps": iface.capacities.bw if iface.capacities else "N/A",
            "link_layer": link.layer,
        }

    def list_links(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ) -> object:
        """
        Print a table of link resources in pretty format.

        :return: formatted table of resources
        :rtype: object
        """
        table = []
        for _, link in self.topology.links.items():
            iface = link.interface_list[0]
            site_names = iface.name.split("_")
            if iface.type.name == "TrunkPort" and "HundredGig" not in site_names[0]:
                table.append(self.link_to_dict(link, iface))

        if pretty_names:
            pretty_names_dict = self.link_pretty_names
        else:
            pretty_names_dict = {}

        return self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Links",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )


class FacilityPorts(Resources):
    link_pretty_names = {
        "name": "Name",
        "site_name": "Site",
        "node_id": "Interface Name",
        "vlan_range": "VLAN Range",
        "local_name": "Local Name",
        "device_name": "Device Name",
        "region": "Region",
    }

    def __init__(self, fablib_manager):
        """
        Constructor
        :return:
        """
        super().__init__(fablib_manager)

    def __str__(self) -> str:
        """
        Creates a tabulated string of all the links.

        Intended for printing available resources.

        :return: Tabulated string of available resources
        :rtype: String
        """
        table = []
        for fp in self.topology.facilities.values():
            for iface in fp.interface_list:
                table.append(
                    [
                        fp.name,
                        fp.site,
                        iface.node_id,
                        iface.labels.vlan_range if iface.labels else "N/A",
                        (
                            iface.labels.local_name
                            if iface.labels and iface.labels.local_name
                            else "N/A"
                        ),
                        (
                            iface.labels.device_name
                            if iface.labels and iface.labels.device_name
                            else "N/A"
                        ),
                        (
                            iface.labels.region
                            if iface.labels and iface.labels.region
                            else "N/A"
                        ),
                    ]
                )

        return tabulate(
            table,
            headers=[
                "name",
                "site_name",
                "node_id",
                "vlan_range",
                "local_name",
                "device_name",
                "region",
            ],
        )

    def fp_to_dict(self, iface: interface.Interface, name: str, site: str) -> dict:
        """
        Converts the link resources to a dictionary.

        Intended for printing links in table format.

        :return: collection of link properties
        :rtype: dict
        """
        return {
            "name": name,
            "site_name": site,
            "node_id": iface.node_id,
            "vlan_range": iface.labels.vlan_range if iface.labels else "N/A",
            "local_name": (
                iface.labels.local_name
                if iface.labels and iface.labels.local_name
                else "N/A"
            ),
            "device_name": (
                iface.labels.device_name
                if iface.labels and iface.labels.device_name
                else "N/A"
            ),
            "region": (
                iface.labels.region if iface.labels and iface.labels.region else "N/A"
            ),
        }

    def list_facility_ports(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ) -> object:
        """
        Print a table of link resources in pretty format.

        :return: formatted table of resources
        :rtype: object
        """
        table = []
        for fp in self.topology.facilities.values():
            for iface in fp.interface_list:
                table.append(self.fp_to_dict(iface, name=fp.name, site=fp.site))

        if pretty_names:
            pretty_names_dict = self.link_pretty_names
        else:
            pretty_names_dict = {}

        return self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Facility Ports",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )
