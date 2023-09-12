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
from __future__ import annotations

import json
import logging
from typing import List, Tuple

from fabrictestbed.slice_editor import AdvertisedTopology, Capacities
from fabrictestbed.slice_manager import Status
from fim.slivers import maintenance_mode, network_node
from fim.user import composite_node, interface, link, node
from tabulate import tabulate


class Resources:
    site_pretty_names = {
        "name": "Name",
        "state": "State",
        "address": "Address",
        "location": "Location",
        "ptp_capable": "PTP Capable",
        "hosts": "Hosts",
        "cpus": "CPUs",
        "cores_available": "Cores Available",
        "cores_capacity": "Cores Capacity",
        "cores_allocated": "Cores Allocated",
        "ram_available": "RAM Available",
        "ram_capacity": "RAM Capacity",
        "ram_allocated": "RAM Allocated",
        "disk_available": "Disk Available",
        "disk_capacity": "Disk Capacity",
        "disk_allocated": "Disk Allocated",
        "nic_basic_available": "Basic NIC Available",
        "nic_basic_capacity": "Basic NIC Capacity",
        "nic_basic_allocated": "Basic NIC Allocated",
        "nic_connectx_6_available": "ConnectX-6 Available",
        "nic_connectx_6_capacity": "ConnectX-6 Capacity",
        "nic_connectx_6_allocated": "ConnectX-6 Allocated",
        "nic_connectx_5_available": "ConnectX-5 Available",
        "nic_connectx_5_capacity": "ConnectX-5 Capacity",
        "nic_connectx_5_allocated": "ConnectX-5 Allocated",
        "nvme_available": "NVMe Available",
        "nvme_capacity": "NVMe Capacity",
        "nvme_allocated": "NVMe Allocated",
        "tesla_t4_available": "Tesla T4 Available",
        "tesla_t4_capacity": "Tesla T4 Capacity",
        "tesla_t4_allocated": "Tesla T4 Allocated",
        "rtx6000_available": "RTX6000 Available",
        "rtx6000_capacity": "RTX6000 Capacity",
        "rtx6000_allocated": "RTX6000 Allocated",
        "a30_available": "A30 Available",
        "a30_capacity": "A30 Capacity",
        "a30_allocated": "A30 Allocated",
        "a40_available": "A40 Available",
        "a40_capacity": "A40 Capacity",
        "a40_allocated": "A40 Allocated",
        "fpga_u280_available": "U280 Available",
        "fpga_u280_capacity": "U280 Capacity",
        "fpga_u280_allocated": "U280 Allocated",
    }

    def __init__(self, fablib_manager, force_refresh: bool = False):
        """
        Constructor
        :return:
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
        for site_name, site in self.topology.sites.items():
            # logging.debug(f"site -- {site}")
            site_sliver = site.get_sliver()
            table.append(
                [
                    site.name,
                    f"{self.get_ptp_capable()}",
                    self.get_cpu_capacity(site_sliver),
                    f"{self.get_core_available(site_sliver)}/{self.get_core_capacity(site_sliver)}",
                    f"{self.get_ram_available(site_sliver)}/{self.get_ram_capacity(site_sliver)}",
                    f"{self.get_disk_available(site_sliver)}/{self.get_disk_capacity(site_sliver)}",
                    # self.get_host_capacity(site),
                    # self.get_location_postal(site),
                    # self.get_location_lat_long(site),
                    f"{self.get_component_available(site_sliver,'SharedNIC-ConnectX-6')}/{self.get_component_capacity(site_sliver,'SharedNIC-ConnectX-6')}",
                    f"{self.get_component_available(site_sliver,'SmartNIC-ConnectX-6')}/{self.get_component_capacity(site_sliver,'SmartNIC-ConnectX-6')}",
                    f"{self.get_component_available(site_sliver,'SmartNIC-ConnectX-5')}/{self.get_component_capacity(site_sliver,'SmartNIC-ConnectX-5')}",
                    f"{self.get_component_available(site_sliver,'NVME-P4510')}/{self.get_component_capacity(site_sliver,'NVME-P4510')}",
                    f"{self.get_component_available(site_sliver,'GPU-Tesla T4')}/{self.get_component_capacity(site_sliver,'GPU-Tesla T4')}",
                    f"{self.get_component_available(site_sliver,'GPU-RTX6000')}/{self.get_component_capacity(site_sliver,'GPU-RTX6000')}",
                    f"{self.get_component_available(site_sliver, 'GPU-A30')}/{self.get_component_capacity(site_sliver, 'GPU-A30')}",
                    f"{self.get_component_available(site_sliver, 'GPU-A40')}/{self.get_component_capacity(site_sliver, 'GPU-A40')}",
                    f"{self.get_component_available(site_sliver, 'FPGA-Xilinx-U280')}/{self.get_component_capacity(site_sliver, 'FPGA-Xilinx-U280')}",
                ]
            )

        return tabulate(
            table,
            headers=[
                "Name",
                "PTP Capable",
                "CPUs",
                "Cores",
                f"RAM ({Capacities.UNITS['ram']})",
                f"Disk ({Capacities.UNITS['disk']})",
                # "Workers"
                # "Physical Address",
                # "Location Coordinates"
                "Basic (100 Gbps NIC)",
                "ConnectX-6 (100 Gbps x2 NIC)",
                "ConnectX-5 (25 Gbps x2 NIC)",
                "P4510 (NVMe 1TB)",
                "Tesla T4 (GPU)",
                "RTX6000 (GPU)",
                "A30 (GPU)",
                "A40 (GPU)",
                "FPGA-Xilinx-U280",
            ],
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

        data = self.site_to_dict(site.get_sliver(), latlon=latlon)

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
            return None

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
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.attached_components_info.get_device(
                    component_model_name
                ).capacities.unit
            if isinstance(site, node.Node):
                return site.components[component_model_name].capacities.unit
            return (
                self.get_topology_site(site)
                .components[component_model_name]
                .capacities.unit
            )
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} capacity {site}")
            return 0

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
        try:
            if isinstance(site, network_node.NodeSliver):
                return site.attached_components_info.get_device(
                    component_model_name
                ).capacity_allocations.unit
            if isinstance(site, node.Node):
                return site.components[component_model_name].capacity_allocations.unit
            return (
                self.get_topology_site(site)
                .components[component_model_name]
                .capacity_allocations.unit
            )
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} allocated {site}")
            return 0

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
            .resources(force_refresh=force_refresh)
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
        core_a = self.get_core_available(site)
        core_c = self.get_core_capacity(site)
        ram_a = self.get_ram_available(site)
        ram_c = self.get_ram_capacity(site)
        disk_a = self.get_disk_available(site)
        disk_c = self.get_disk_capacity(site)
        nic_basic_a = self.get_component_available(site, "SharedNIC-ConnectX-6")
        nic_basic_c = self.get_component_capacity(site, "SharedNIC-ConnectX-6")
        nic_cx6_a = self.get_component_available(site, "SmartNIC-ConnectX-6")
        nic_cx6_c = self.get_component_capacity(site, "SmartNIC-ConnectX-6")
        nic_cx5_a = self.get_component_available(site, "SmartNIC-ConnectX-5")
        nic_cx5_c = self.get_component_capacity(site, "SmartNIC-ConnectX-5")
        nvme_a = self.get_component_available(site, "NVME-P4510")
        nvme_c = self.get_component_capacity(site, "NVME-P4510")
        tesla_t4_a = self.get_component_available(site, "GPU-Tesla T4")
        tesla_t4_c = self.get_component_capacity(site, "GPU-Tesla T4")
        rtx6000_a = self.get_component_available(site, "GPU-RTX6000")
        rtx6000_c = self.get_component_capacity(site, "GPU-RTX6000")
        a30_a = self.get_component_available(site, "GPU-A30")
        a30_c = self.get_component_capacity(site, "GPU-A30")
        a40_a = self.get_component_available(site, "GPU-A40")
        a40_c = self.get_component_capacity(site, "GPU-A40")
        u280_a = self.get_component_available(site, "FPGA-Xilinx-U280")
        u280_c = self.get_component_capacity(site, "FPGA-Xilinx-U280")
        ptp = self.get_ptp_capable(site)

        d = {
            "name": site.name if isinstance(site, node.Node) else site.get_name(),
            "state": self.get_state(site),
            "address": self.get_location_postal(site),
            "location": self.get_location_lat_long(site) if latlon else "",
            "ptp_capable": ptp,
            "hosts": self.get_host_capacity(site),
            "cpus": self.get_cpu_capacity(site),
            "cores_available": core_a,
            "cores_capacity": core_c,
            "cores_allocated": core_c - core_a,
            "ram_available": ram_a,
            "ram_capacity": ram_c,
            "ram_allocated": ram_c - ram_a,
            "disk_available": disk_a,
            "disk_capacity": disk_c,
            "disk_allocated": disk_c - disk_a,
            "nic_basic_available": nic_basic_a,
            "nic_basic_capacity": nic_basic_c,
            "nic_basic_allocated": nic_basic_c - nic_basic_a,
            "nic_connectx_6_available": nic_cx6_a,
            "nic_connectx_6_capacity": nic_cx6_c,
            "nic_connectx_6_allocated": nic_cx6_c - nic_cx6_a,
            "nic_connectx_5_available": nic_cx5_a,
            "nic_connectx_5_capacity": nic_cx5_c,
            "nic_connectx_5_allocated": nic_cx5_c - nic_cx5_a,
            "nvme_available": nvme_a,
            "nvme_capacity": nvme_c,
            "nvme_allocated": nvme_c - nvme_a,
            "tesla_t4_available": tesla_t4_a,
            "tesla_t4_capacity": tesla_t4_c,
            "tesla_t4_allocated": tesla_t4_c - tesla_t4_a,
            "rtx6000_available": rtx6000_a,
            "rtx6000_capacity": rtx6000_c,
            "rtx6000_allocated": rtx6000_c - rtx6000_a,
            "a30_available": a30_a,
            "a30_capacity": a30_c,
            "a30_allocated": a30_c - a30_a,
            "a40_available": a40_a,
            "a40_capacity": a40_c,
            "a40_allocated": a40_c - a40_a,
            "fpga_u280_available": u280_a,
            "fpga_u280_capacity": u280_c,
            "fpga_u280_allocated": u280_c - u280_a,
        }
        if not latlon:
            d.pop("location")
        return d

    def site_to_dictXXX(self, site):
        site_name = site.name
        return {
            "name": {"pretty_name": "Name", "value": site.name},
            "address": {
                "pretty_name": "Address",
                "value": self.get_location_postal(site_name),
            },
            "location": {
                "pretty_name": "Location",
                "value": self.get_location_lat_long(site_name),
            },
            "ptp": {
                "pretty_name": "PTP Capable",
                "value": self.get_ptp_capable(),
            },
            "hosts": {
                "pretty_name": "Hosts",
                "value": self.get_host_capacity(site_name),
            },
            "cpus": {"pretty_name": "CPUs", "value": self.get_cpu_capacity(site_name)},
            "cores_available": {
                "pretty_name": "Cores Available",
                "value": self.get_core_available(site_name),
            },
            "cores_capacity": {
                "pretty_name": "Cores Capacity",
                "value": self.get_core_capacity(site_name),
            },
            "cores_allocated": {
                "pretty_name": "Cores Allocated",
                "value": self.get_core_capacity(site_name)
                - self.get_core_available(site_name),
            },
            "ram_available": {
                "pretty_name": "RAM Available",
                "value": self.get_ram_available(site_name),
            },
            "ram_capacity": {
                "pretty_name": "RAM Capacity",
                "value": self.get_ram_capacity(site_name),
            },
            "ram_allocated": {
                "pretty_name": "RAM Allocated",
                "value": self.get_ram_capacity(site_name)
                - self.get_ram_available(site_name),
            },
            "disk_available": {
                "pretty_name": "Disk Available",
                "value": self.get_disk_available(site_name),
            },
            "disk_capacity": {
                "pretty_name": "Disk Capacity",
                "value": self.get_disk_capacity(site_name),
            },
            "disk_allocated": {
                "pretty_name": "Disk Allocated",
                "value": self.get_disk_capacity(site_name)
                - self.get_disk_available(site_name),
            },
            "nic_basic_available": {
                "pretty_name": "Basic NIC Available",
                "value": self.get_component_available(
                    site_name, "SharedNIC-ConnectX-6"
                ),
            },
            "nic_basic_capacity": {
                "pretty_name": "Basic NIC Capacity",
                "value": self.get_component_capacity(site_name, "SharedNIC-ConnectX-6"),
            },
            "nic_basic_allocated": {
                "pretty_name": "Basic NIC Allocated",
                "value": self.get_component_capacity(site_name, "SharedNIC-ConnectX-6")
                - self.get_component_available(site_name, "SharedNIC-ConnectX-6"),
            },
            "nic_connectx_6_available": {
                "pretty_name": "ConnectX-6 Available",
                "value": self.get_component_available(site_name, "SmartNIC-ConnectX-6"),
            },
            "nic_connectx_6_capacity": {
                "pretty_name": "ConnectX-6 Capacity",
                "value": self.get_component_capacity(site_name, "SmartNIC-ConnectX-6"),
            },
            "nic_connectx_6_allocated": {
                "pretty_name": "ConnectX-6 Allocated",
                "value": self.get_component_capacity(site_name, "SmartNIC-ConnectX-6")
                - self.get_component_available(site_name, "SmartNIC-ConnectX-6"),
            },
            "nic_connectx_5_available": {
                "pretty_name": "ConnectX-5 Available",
                "value": self.get_component_available(site_name, "SmartNIC-ConnectX-5"),
            },
            "nic_connectx_5_capacity": {
                "pretty_name": "ConnectX-5 Capacity",
                "value": self.get_component_capacity(site_name, "SmartNIC-ConnectX-5"),
            },
            "nic_connectx_5_allocated": {
                "pretty_name": "ConnectX-5 Allocated",
                "value": self.get_component_capacity(site_name, "SmartNIC-ConnectX-5")
                - self.get_component_available(site_name, "SmartNIC-ConnectX-5"),
            },
            "nvme_available": {
                "pretty_name": "NVMe Available",
                "value": self.get_component_available(site_name, "NVME-P4510"),
            },
            "nvme_capacity": {
                "pretty_name": "NVMe Capacity",
                "value": self.get_component_capacity(site_name, "NVME-P4510"),
            },
            "nvme_allocated": {
                "pretty_name": "NVMe Allocated",
                "value": self.get_component_capacity(site_name, "NVME-P4510")
                - self.get_component_available(site_name, "NVME-P4510"),
            },
            "tesla_t4_available": {
                "pretty_name": "Tesla T4 Available",
                "value": self.get_component_available(site_name, "GPU-Tesla T4"),
            },
            "tesla_t4_capacity": {
                "pretty_name": "Tesla T4 Capacity",
                "value": self.get_component_capacity(site_name, "GPU-Tesla T4"),
            },
            "tesla_t4_allocated": {
                "pretty_name": "Tesla T4 Allocated",
                "value": self.get_component_capacity(site_name, "GPU-Tesla T4")
                - self.get_component_available(site_name, "GPU-Tesla T4"),
            },
            "rtx6000_available": {
                "pretty_name": "RTX6000 Available",
                "value": self.get_component_available(site_name, "GPU-RTX6000"),
            },
            "rtx6000_capacity": {
                "pretty_name": "RTX6000 Capacity",
                "value": self.get_component_capacity(site_name, "GPU-RTX6000"),
            },
            "rtx6000_allocated": {
                "pretty_name": "RTX6000 Allocated",
                "value": self.get_component_capacity(site_name, "GPU-RTX6000")
                - self.get_component_available(site_name, "GPU-RTX6000"),
            },
            "a30_available": {
                "pretty_name": "A30 Available",
                "value": self.get_component_available(site_name, "GPU-A30"),
            },
            "a30_capacity": {
                "pretty_name": "A30 Capacity",
                "value": self.get_component_capacity(site_name, "GPU-A30"),
            },
            "a30_allocated": {
                "pretty_name": "A30 Allocated",
                "value": self.get_component_capacity(site_name, "GPU-A30")
                - self.get_component_available(site_name, "GPU-A30"),
            },
            "a40_available": {
                "pretty_name": "A40 Available",
                "value": self.get_component_available(site_name, "GPU-A40"),
            },
            "a40_capacity": {
                "pretty_name": "A40 Capacity",
                "value": self.get_component_capacity(site_name, "GPU-A40"),
            },
            "a40_allocated": {
                "pretty_name": "A40 Allocated",
                "value": self.get_component_capacity(site_name, "GPU-A40")
                - self.get_component_available(site_name, "GPU-A40"),
            },
            "fpga_u280_available": {
                "pretty_name": "FPGA U280 Available",
                "value": self.get_component_available(site_name, "FPGA-Xilinx-U280"),
            },
            "fpga_u280_capacity": {
                "pretty_name": "FPGA U280 Capacity",
                "value": self.get_component_capacity(site_name, "FPGA-Xilinx-U280"),
            },
            "fpga_u280_allocated": {
                "pretty_name": "FPGA U280 Allocated",
                "value": self.get_component_capacity(site_name, "FPGA-Xilinx-U280")
                - self.get_component_available(site_name, "FPGA-Xilinx-U280"),
            },
        }

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
            table.append(self.site_to_dict(site.get_sliver(), latlon=latlon))

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
                        iface.labels.local_name
                        if iface.labels and iface.labels.local_name
                        else "N/A",
                        iface.labels.device_name
                        if iface.labels and iface.labels.device_name
                        else "N/A",
                        iface.labels.region
                        if iface.labels and iface.labels.region
                        else "N/A",
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
            "local_name": iface.labels.local_name
            if iface.labels and iface.labels.local_name
            else "N/A",
            "device_name": iface.labels.device_name
            if iface.labels and iface.labels.device_name
            else "N/A",
            "region": iface.labels.region
            if iface.labels and iface.labels.region
            else "N/A",
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
