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
# Author: Komal Thareja(kthar10@renci.org)

from __future__ import annotations

import json
import logging
import traceback
from typing import List, Dict, Tuple

from fabrictestbed.slice_editor import Capacities
from fim.view_only_dict import ViewOnlyDict

from fabrictestbed_extensions.fablib.constants import Constants
from fim.user import node


class Site:
    site_attribute_name_mappings = {
        Constants.CORES.lower(): {
            Constants.NON_PRETTY_NAME: Constants.CORES.lower(),
            Constants.PRETTY_NAME: Constants.CORES,
            Constants.HEADER_NAME: Constants.CORES,
        },
        Constants.RAM.lower(): {
            Constants.NON_PRETTY_NAME: Constants.RAM.lower(),
            Constants.PRETTY_NAME: Constants.RAM,
            Constants.HEADER_NAME: f"{Constants.RAM} ({Capacities.UNITS[Constants.RAM.lower()]})",
        },
        Constants.DISK: {
            Constants.NON_PRETTY_NAME: Constants.DISK.lower(),
            Constants.PRETTY_NAME: Constants.DISK,
            Constants.HEADER_NAME: f"{Constants.DISK} ({Capacities.UNITS[Constants.DISK.lower()]})",
        },
        Constants.NIC_SHARED_CONNECTX_6: {
            Constants.NON_PRETTY_NAME: "nic_basic",
            Constants.PRETTY_NAME: "Basic NIC",
            Constants.HEADER_NAME: "Basic (100 Gbps NIC)",
        },
        Constants.SMART_NIC_CONNECTX_6: {
            Constants.NON_PRETTY_NAME: "nic_connectx_6",
            Constants.PRETTY_NAME: "ConnectX-6",
            Constants.HEADER_NAME: "ConnectX-6 (100 Gbps x2 NIC)",
        },
        Constants.SMART_NIC_CONNECTX_5: {
            Constants.NON_PRETTY_NAME: "nic_connectx_5",
            Constants.PRETTY_NAME: "ConnectX-5",
            Constants.HEADER_NAME: "ConnectX-5 (25 Gbps x2 NIC)",
        },
        Constants.NVME_P4510: {
            Constants.NON_PRETTY_NAME: "nvme",
            Constants.PRETTY_NAME: "NVMe",
            Constants.HEADER_NAME: "P4510 (NVMe 1TB)",
        },
        Constants.GPU_TESLA_T4: {
            Constants.NON_PRETTY_NAME: "tesla_t4",
            Constants.PRETTY_NAME: "Tesla T4",
            Constants.HEADER_NAME: "Tesla T4 (GPU)",
        },
        Constants.GPU_RTX6000: {
            Constants.NON_PRETTY_NAME: "rtx6000",
            Constants.PRETTY_NAME: "RTX6000",
            Constants.HEADER_NAME: "RTX6000 (GPU)",
        },
        Constants.GPU_A30: {
            Constants.NON_PRETTY_NAME: "a30",
            Constants.PRETTY_NAME: "A30",
            Constants.HEADER_NAME: "A30 (GPU)",
        },
        Constants.GPU_A40: {
            Constants.NON_PRETTY_NAME: "a40",
            Constants.PRETTY_NAME: "A40",
            Constants.HEADER_NAME: "A40 (GPU)",
        },
        Constants.FPGA_XILINX_U280: {
            Constants.NON_PRETTY_NAME: "fpga_u280",
            Constants.PRETTY_NAME: "U280",
            Constants.HEADER_NAME: "FPGA-Xilinx-U280",
        },
    }
    site_pretty_names = {
        "name": "Name",
        "state": "State",
        "address": "Address",
        "location": "Location",
        "ptp_capable": "PTP Capable",
        Constants.HOSTS.lower(): Constants.HOSTS,
        Constants.CPUS.lower(): Constants.CPUS,
    }

    def __init__(self, site: node.Node, fablib_manager):
        """
        :param site: Site Node from Fim Topology
        :type site: node.Node

        """
        super().__init__()
        self.site = site
        self.fablib_manager = fablib_manager
        self.hosts = self.__get_hosts_topology()
        self.site_info = self.__get_site_info()

    def get_hosts(self) -> ViewOnlyDict:
        return self.hosts

    def __get_hosts_topology(self) -> ViewOnlyDict:
        """
        Get worker nodes on a site
        :param site: site name
        :type site: String
        """
        try:
            from fim.graph.abc_property_graph import ABCPropertyGraph

            node_id_list = self.site.topo.graph_model.get_first_neighbor(
                node_id=self.site.node_id,
                rel=ABCPropertyGraph.REL_HAS,
                node_label=ABCPropertyGraph.CLASS_NetworkNode,
            )
            ret = dict()
            for nid in node_id_list:
                _, node_props = self.site.topo.graph_model.get_node_properties(node_id=nid)
                n = node.Node(
                    name=node_props[ABCPropertyGraph.PROP_NAME],
                    node_id=nid,
                    topo=self.site.topo,
                )
                # exclude Facility nodes
                from fim.user import NodeType

                if n.type != NodeType.Facility:
                    ret[n.name] = n
            return ViewOnlyDict(ret)
        except Exception as e:
            logging.error(f"Error occurred - {e}")
            logging.error(traceback.format_exc())

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

    def get_name(self):
        """
        Gets the site name

        :return: str(MaintenanceState)
        """
        try:
            return self.site.name
        except Exception as e:
            # logging.debug(f"Failed to get name for {site}")
            return ""

    def get_state(self, host: str = None):
        """
        Gets the maintenance state of the node

        :return: str(MaintenanceState)
        """
        try:
            if not host:
                return str(self.site.maintenance_info.get(self.site.name).state)
            else:
                return str(self.site.maintenance_info.get(host).state)
        except Exception as e:
            # logging.debug(f"Failed to get maintenance state for {site}")
            return ""

    def get_location_postal(self) -> str:
        """
        Gets the location of a site by postal address

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: postal address of the site
        :rtype: String
        """
        try:
            return self.site.location.postal
        except Exception as e:
            # logging.debug(f"Failed to get postal address for {site}")
            return ""

    def get_location_lat_long(self) -> Tuple[float, float]:
        """
        Gets gets location of a site in latitude and longitude

        :return: latitude and longitude of the site
        :rtype: Tuple(float,float)
        """
        try:
            return self.site.location.to_latlon()
        except Exception as e:
            # logging.debug(f"Failed to get latitude and longitude for {site}")
            return 0, 0

    def get_ptp_capable(self) -> bool:
        """
        Gets the PTP flag of the site - if it has a native PTP capability
        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: boolean flag
        :rtype: bool
        """
        try:
            return self.site.flags.ptp
        except Exception as e:
            # logging.debug(f"Failed to get PTP status for {site}")
            return False

    def get_host_capacity(self) -> int:
        """
        Gets the number of hosts at the site

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: host count
        :rtype: int
        """
        try:
            return self.site.capacities.unit
        except Exception as e:
            # logging.debug(f"Failed to get host count {site}")
            return 0

    def get_cpu_capacity(self) -> int:
        """
        Gets the total number of cpus at the site

        :param site: site name or site object
        :type site: String or node.Node or NodeSliver
        :return: cpu count
        :rtype: int
        """
        try:
            return self.site.capacities.cpu
        except Exception as e:
            # logging.debug(f"Failed to get cpu capacity {site}")
            return 0

    def to_dict(self):
        """
        Convert site information into a dictionary
        """
        d = {
            "name": self.get_name() ,
            "state": self.get_state(),
            "address": self.get_location_postal(),
            "location": self.get_location_lat_long(),
            "ptp_capable": self.get_ptp_capable(),
            "hosts": self.get_host_capacity(),
            "cpus": self.get_cpu_capacity(),
        }

        for attribute, names in self.site_attribute_name_mappings.items():
            capacity = self.site_info.get(attribute, {}).get(Constants.CAPACITY.lower(), 0)
            allocated = self.site_info.get(attribute, {}).get(Constants.ALLOCATED.lower(), 0)
            available = capacity - allocated
            d[f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.AVAILABLE.lower()}"] = available
            d[f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.CAPACITY.lower()}"] = capacity
            d[f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.ALLOCATED.lower()}"] = allocated

        return d

    def __get_site_info(self) -> Dict[str, Dict[str, int]]:
        """
        Gets the total site capacity of all components for a site

        :return: total component capacity for all components
        :rtype: Dict[str, int]
        """
        site_info = {}

        try:
            site_info[Constants.CORES.lower()] = {
                Constants.CAPACITY.lower(): self.site.capacities.core,
                Constants.ALLOCATED.lower(): (
                    self.site.capacity_allocations.core if self.site.capacity_allocations else 0
                ),
            }
            site_info[Constants.RAM.lower()] = {
                Constants.CAPACITY.lower(): self.site.capacities.ram,
                Constants.ALLOCATED.lower(): (
                    self.site.capacity_allocations.ram if self.site.capacity_allocations else 0
                ),
            }
            site_info[Constants.DISK.lower()] = {
                Constants.CAPACITY.lower(): self.site.capacities.disk,
                Constants.ALLOCATED.lower(): (
                    self.site.capacity_allocations.disk if self.site.capacity_allocations else 0
                ),
            }

            if self.hosts:
                for h in self.hosts.values():
                    if h.components:
                        for component_model_name, c in h.components.items():
                            comp_cap = site_info.setdefault(component_model_name, {})
                            comp_cap.setdefault(Constants.CAPACITY.lower(), 0)
                            comp_cap.setdefault(Constants.ALLOCATED.lower(), 0)
                            comp_cap[Constants.CAPACITY.lower()] += c.capacities.unit
                            if c.capacity_allocations:
                                comp_cap[
                                    Constants.ALLOCATED.lower()
                                ] += c.capacity_allocations.unit

            return site_info
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            return site_info

    def show(
        self,
        output: str = None,
        fields: list[str] = None,
        quiet: bool = False,
        pretty_names=True,
    ) -> str:
        """
        Creates a tabulated string of all the available resources at a specific site.

        Intended for printing available resources at a site.

        :param output: Output type
        :type output: str
        :param fields: List of fields to include
        :type fields: List
        :param quiet: flag indicating verbose or quiet display
        :type quiet: bool
        :param pretty_names: flag indicating if pretty names for the fields to be used or not
        :type pretty_names: bool

        :return: Tabulated string of available resources
        :rtype: String
        """

        data = self.to_dict()

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

    def get_fablib_manager(self):
        return self.fablib_manager

    def to_row(self):
        headers = [
            "Name",
            "PTP Capable",
            Constants.CPUS,
        ]
        row = [
            self.get_name(),
            self.get_ptp_capable(),
            self.get_cpu_capacity(),
        ]

        for attribute, names in self.site_attribute_name_mappings.items():
            allocated = self.site_info.get(attribute, {}).get(
                Constants.ALLOCATED.lower(), 0
            )
            capacity = self.site_info.get(attribute, {}).get(
                Constants.CAPACITY.lower(), 0
            )
            available = capacity - allocated
            row.append(f"{available}/{capacity}")
            headers.append(names.get(Constants.HEADER_NAME))
        return headers, row

    def get_component_capacity(
        self,
        component_model_name: str,
    ) -> int:
        """
        Gets the total site capacity of a component by model name.

        :param component_model_name: component model name
        :type component_model_name: String
        :return: total component capacity
        :rtype: int
        """
        component_capacity = 0
        try:
            if self.hosts:
                for h in self.hosts.values():
                    if component_model_name in h.components:
                        component_capacity += h.components[
                            component_model_name
                        ].capacities.unit
            return component_capacity
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            return component_capacity

    def get_component_allocated(
        self,
        component_model_name: str,
    ) -> int:
        """
        Gets gets number of currently allocated components on a the site
        by the component by model name.

        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently allocated component of this model
        :rtype: int
        """
        component_allocated = 0
        try:
            if self.hosts:
                for h in self.hosts.values():
                    if (
                        component_model_name in h.components
                        and h.components[component_model_name].capacity_allocations
                    ):
                        component_allocated += h.components[
                            component_model_name
                        ].capacity_allocations.unit
            return component_allocated
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} allocated {site}: {e}")
            return component_allocated

    def get_component_available(
        self,
        component_model_name: str,
    ) -> int:
        """
        Gets gets number of currently available components on the site
        by the component by model name.

        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently available component of this model
        :rtype: int
        """
        try:
            return self.get_component_capacity(
                component_model_name
            ) - self.get_component_allocated(component_model_name)
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} available {site}")
            return self.get_component_capacity(component_model_name)

    def get_fim(self) -> node.Node:
        return self.site

    def get_core_capacity(self) -> int:
        """
        Gets the total number of cores at the site

        :return: core count
        :rtype: int
        """
        try:
            return self.site.capacities.core
        except Exception as e:
            # logging.debug(f"Failed to get core capacity {site}")
            return 0

    def get_core_allocated(self) -> int:
        """
        Gets the number of currently allocated cores at the site

        :return: core count
        :rtype: int
        """
        try:
            return self.site.capacity_allocations.core
        except Exception as e:
            # logging.debug(f"Failed to get cores allocated {site}")
            return 0

    def get_core_available(self) -> int:
        """
        Gets the number of currently available cores at the site
        :return: core count
        :rtype: int
        """
        try:
            return self.get_core_capacity() - self.get_core_allocated()
        except Exception as e:
            # logging.debug(f"Failed to get cores available {site}")
            return self.get_core_capacity()

    def get_ram_capacity(self) -> int:
        """
        Gets the total amount of memory at the site in GB

        :return: ram in GB
        :rtype: int
        """
        try:
            return self.site.capacities.ram
        except Exception as e:
            # logging.debug(f"Failed to get ram capacity {site}")
            return 0

    def get_ram_allocated(self) -> int:
        """
        Gets the amount of memory currently  allocated the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            return self.site.capacity_allocations.ram
        except Exception as e:
            # logging.debug(f"Failed to get ram allocated {site}")
            return 0

    def get_ram_available(self) -> int:
        """
        Gets the amount of memory currently  available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            return self.get_ram_capacity() - self.get_ram_allocated()
        except Exception as e:
            # logging.debug(f"Failed to get ram available {site_name}")
            return self.get_ram_capacity()

    def get_disk_capacity(self) -> int:
        """
        Gets the total amount of disk available the site in GB

        :return: disk in GB
        :rtype: int
        """
        try:
            return self.site.capacities.disk
        except Exception as e:
            # logging.debug(f"Failed to get disk capacity {site}")
            return 0

    def get_disk_allocated(self) -> int:
        """
        Gets the amount of disk allocated the site in GB

        :return: disk in GB
        :rtype: int
        """
        try:
            return self.site.capacity_allocations.disk
        except Exception as e:
            # logging.debug(f"Failed to get disk allocated {site}")
            return 0

    def get_disk_available(self) -> int:
        """
        Gets the amount of disk available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            return self.get_disk_capacity() - self.get_disk_allocated()
        except Exception as e:
            # logging.debug(f"Failed to get disk available {site_name}")
            return self.get_disk_capacity()
