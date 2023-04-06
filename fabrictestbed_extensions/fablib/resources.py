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
import logging
from tabulate import tabulate

from typing import List, Tuple
import json

from fabrictestbed.slice_editor import AdvertisedTopology
from fabrictestbed.slice_editor import Capacities
from fabrictestbed.slice_manager import Status
from fim.user import link, interface


class Resources:
    site_pretty_names = {
        "name": "Name",
        "state": "State",
        "address": "Address",
        "location": "Location",
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
    }

    def __init__(self, fablib_manager):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.fablib_manager = fablib_manager

        self.topology = None

        self.update()

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
            table.append(
                [
                    site.name,
                    self.get_cpu_capacity(site_name),
                    f"{self.get_core_available(site_name)}/{self.get_core_capacity(site_name)}",
                    f"{self.get_ram_available(site_name)}/{self.get_ram_capacity(site_name)}",
                    f"{self.get_disk_available(site_name)}/{self.get_disk_capacity(site_name)}",
                    # self.get_host_capacity(site_name),
                    # self.get_location_postal(site_name),
                    # self.get_location_lat_long(site_name),
                    f"{self.get_component_available(site_name,'SharedNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SharedNIC-ConnectX-6')}",
                    f"{self.get_component_available(site_name,'SmartNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-6')}",
                    f"{self.get_component_available(site_name,'SmartNIC-ConnectX-5')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-5')}",
                    f"{self.get_component_available(site_name,'NVME-P4510')}/{self.get_component_capacity(site_name,'NVME-P4510')}",
                    f"{self.get_component_available(site_name,'GPU-Tesla T4')}/{self.get_component_capacity(site_name,'GPU-Tesla T4')}",
                    f"{self.get_component_available(site_name,'GPU-RTX6000')}/{self.get_component_capacity(site_name,'GPU-RTX6000')}",
                ]
            )

        return tabulate(
            table,
            headers=[
                "Name",
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
            ],
        )

    def show_site(
        self,
        site_name: str,
        output: str = None,
        fields: list[str] = None,
        quiet: bool = False,
        pretty_names=True,
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

        data = self.site_to_dict(site)

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

    def get_topology_site(self, site_name: str) -> str:
        """
        Not recommended for most users.
        """
        try:
            return self.topology.sites[site_name]
        except Exception as e:
            logging.warning(f"Failed to get site {site_name}")
            return ""

    def get_state(self, site_name: str):
        try:
            return str(
                self.get_topology_site(site_name)
                .get_property("maintenance_info")
                .get(site_name)
                .state
            )
        except Exception as e:
            logging.warning(f"Failed to get site state {site_name}")
            return ""

    def get_component_capacity(self, site_name: str, component_model_name: str) -> int:
        """
        Gets gets the total site capacity of a component by model name.

        :param site_name: site name
        :type site_name: String
        :param component_model_name: component model name
        :type component_model_name: String
        :return: total component capacity
        :rtype: int
        """
        try:
            return (
                self.get_topology_site(site_name)
                .components[component_model_name]
                .capacities.unit
            )
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} capacity {site_name}")
            return 0

    def get_component_allocated(self, site_name: str, component_model_name: str) -> int:
        """
        Gets gets number of currently allocated components on a the site
        by the component by model name.

        :param site_name: site name
        :type site_name: String
        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently allocated component of this model
        :rtype: int
        """
        try:
            return (
                self.get_topology_site(site_name)
                .components[component_model_name]
                .capacity_allocations.unit
            )
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} allocated {site_name}")
            return 0

    def get_component_available(self, site_name: str, component_model_name: str) -> int:
        """
        Gets gets number of currently available components on the site
        by the component by model name.

        :param site_name: site name
        :type site_name: String
        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently available component of this model
        :rtype: int
        """
        try:
            return self.get_component_capacity(
                site_name, component_model_name
            ) - self.get_component_allocated(site_name, component_model_name)
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} available {site_name}")
            return self.get_component_capacity(site_name, component_model_name)

    def get_location_lat_long(self, site_name: str) -> Tuple[float, float]:
        """
        Gets gets location of a site in latitude and longitude

        :param site_name: site name
        :type site_name: String
        :return: latitude and longitude of the site
        :rtype: Tuple(float,float)
        """
        try:
            # site.get_property("location").to_latlon()
            return (
                self.get_topology_site(site_name).get_property("location").to_latlon()
            )
        except Exception as e:
            # logging.warning(f"Failed to get location postal {site_name}")
            return 0, 0

    def get_location_postal(self, site_name: str) -> str:
        """
        Gets the location of a site by postal address

        :param site_name: site name
        :type site_name: String
        :return: postal address of the site
        :rtype: String
        """
        try:
            return self.get_topology_site(site_name).location.postal
        except Exception as e:
            # logging.debug(f"Failed to get location postal {site_name}")
            return ""

    def get_host_capacity(self, site_name: str) -> int:
        """
        Gets the number of worker hosts at the site

        :param site_name: site name
        :type site_name: String
        :return: host count
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacities.unit
        except Exception as e:
            # logging.debug(f"Failed to get host count {site_name}")
            return 0

    def get_cpu_capacity(self, site_name: str) -> int:
        """
        Gets the total number of cpus at the site

        :param site_name: site name
        :type site_name: String
        :return: cpu count
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacities.cpu
        except Exception as e:
            # logging.debug(f"Failed to get cpu capacity {site_name}")
            return 0

    def get_core_capacity(self, site_name: str) -> int:
        """
        Gets the total number of cores at the site

        :param site_name: site name
        :type site_name: String
        :return: core count
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacities.core
        except Exception as e:
            # logging.debug(f"Failed to get core capacity {site_name}")
            return 0

    def get_core_allocated(self, site_name: str) -> int:
        """
        Gets the number of currently allocated cores at the site

        :param site_name: site name
        :type site_name: String
        :return: core count
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacity_allocations.core
        except Exception as e:
            # logging.debug(f"Failed to get cores allocated {site_name}")
            return 0

    def get_core_available(self, site_name: str) -> int:
        """
        Gets the number of currently available cores at the site

        :param site_name: site name
        :type site_name: String
        :return: core count
        :rtype: int
        """
        try:
            return self.get_core_capacity(site_name) - self.get_core_allocated(
                site_name
            )
        except Exception as e:
            # logging.debug(f"Failed to get cores available {site_name}")
            return self.get_core_capacity(site_name)

    def get_ram_capacity(self, site_name: str) -> int:
        """
        Gets the total amount of memory at the site in GB

        :param site_name: site name
        :type site_name: String
        :return: ram in GB
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacities.ram
        except Exception as e:
            # logging.debug(f"Failed to get ram capacity {site_name}")
            return 0

    def get_ram_allocated(self, site_name: str) -> int:
        """
        Gets the amount of memory currently  allocated the site in GB

        :param site_name: site name
        :type site_name: String
        :return: ram in GB
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacity_allocations.ram
        except Exception as e:
            # logging.debug(f"Failed to get ram allocated {site_name}")
            return 0

    def get_ram_available(self, site_name: str) -> int:
        """
        Gets the amount of memory currently  available the site in GB

        :param site_name: site name
        :type site_name: String
        :return: ram in GB
        :rtype: int
        """
        try:
            return self.get_ram_capacity(site_name) - self.get_ram_allocated(site_name)
        except Exception as e:
            # logging.debug(f"Failed to get ram available {site_name}")
            return self.get_ram_capacity(site_name)

    def get_disk_capacity(self, site_name: str) -> int:
        """
        Gets the total amount of disk available the site in GB

        :param site_name: site name
        :type site_name: String
        :return: disk in GB
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacities.disk
        except Exception as e:
            # logging.debug(f"Failed to get disk capacity {site_name}")
            return 0

    def get_disk_allocated(self, site_name: str) -> int:
        """
        Gets the amount of disk allocated the site in GB

        :param site_name: site name
        :type site_name: String
        :return: disk in GB
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).capacity_allocations.disk
        except Exception as e:
            # logging.debug(f"Failed to get disk allocated {site_name}")
            return 0

    def get_disk_available(self, site_name: str) -> int:
        """
        Gets the amount of disk available the site in GB

        :param site_name: site name
        :type site_name: String
        :return: disk in GB
        :rtype: int
        """
        try:
            return self.get_disk_capacity(site_name) - self.get_disk_allocated(
                site_name
            )
        except Exception as e:
            # logging.debug(f"Failed to get disk available {site_name}")
            return self.get_disk_capacity(site_name)

    def get_fablib_manager(self):
        return self.fablib_manager

    def update(self):
        """
        Update the available resources by querying the FABRIC services

        """
        logging.info(f"Updating available resources")
        return_status, topology = (
            self.get_fablib_manager().get_slice_manager().resources()
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

    def site_to_json(self, site):
        return json.dumps(self.site_to_dict(site), indent=4)

    def site_to_dict(self, site):
        site_name = site.name
        return {
            "name": site.name,
            "state": self.get_state(site_name),
            "address": self.get_location_postal(site_name),
            "location": self.get_location_lat_long(site_name),
            "hosts": self.get_host_capacity(site_name),
            "cpus": self.get_cpu_capacity(site_name),
            "cores_available": self.get_core_available(site_name),
            "cores_capacity": self.get_core_capacity(site_name),
            "cores_allocated": self.get_core_capacity(site_name)
            - self.get_core_available(site_name),
            "ram_available": self.get_ram_available(site_name),
            "ram_capacity": self.get_ram_capacity(site_name),
            "ram_allocated": self.get_ram_capacity(site_name)
            - self.get_ram_available(site_name),
            "disk_available": self.get_disk_available(site_name),
            "disk_capacity": self.get_disk_capacity(site_name),
            "disk_allocated": self.get_disk_capacity(site_name)
            - self.get_disk_available(site_name),
            "nic_basic_available": self.get_component_available(
                site_name, "SharedNIC-ConnectX-6"
            ),
            "nic_basic_capacity": self.get_component_capacity(
                site_name, "SharedNIC-ConnectX-6"
            ),
            "nic_basic_allocated": self.get_component_capacity(
                site_name, "SharedNIC-ConnectX-6"
            )
            - self.get_component_available(site_name, "SharedNIC-ConnectX-6"),
            "nic_connectx_6_available": self.get_component_available(
                site_name, "SmartNIC-ConnectX-6"
            ),
            "nic_connectx_6_capacity": self.get_component_capacity(
                site_name, "SmartNIC-ConnectX-6"
            ),
            "nic_connectx_6_allocated": self.get_component_capacity(
                site_name, "SmartNIC-ConnectX-6"
            )
            - self.get_component_available(site_name, "SmartNIC-ConnectX-6"),
            "nic_connectx_5_available": self.get_component_available(
                site_name, "SmartNIC-ConnectX-5"
            ),
            "nic_connectx_5_capacity": self.get_component_capacity(
                site_name, "SmartNIC-ConnectX-5"
            ),
            "nic_connectx_5_allocated": self.get_component_capacity(
                site_name, "SmartNIC-ConnectX-5"
            )
            - self.get_component_available(site_name, "SmartNIC-ConnectX-5"),
            "nvme_available": self.get_component_available(site_name, "NVME-P4510"),
            "nvme_capacity": self.get_component_capacity(site_name, "NVME-P4510"),
            "nvme_allocated": self.get_component_capacity(site_name, "NVME-P4510")
            - self.get_component_available(site_name, "NVME-P4510"),
            "tesla_t4_available": self.get_component_available(
                site_name, "GPU-Tesla T4"
            ),
            "tesla_t4_capacity": self.get_component_capacity(site_name, "GPU-Tesla T4"),
            "tesla_t4_allocated": self.get_component_capacity(site_name, "GPU-Tesla T4")
            - self.get_component_available(site_name, "GPU-Tesla T4"),
            "rtx6000_available": self.get_component_available(site_name, "GPU-RTX6000"),
            "rtx6000_capacity": self.get_component_capacity(site_name, "GPU-RTX6000"),
            "rtx6000_allocated": self.get_component_capacity(site_name, "GPU-RTX6000")
            - self.get_component_available(site_name, "GPU-RTX6000"),
        }

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
        }

    def list_sites(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        table = []
        for site_name, site in self.topology.sites.items():
            table.append(self.site_to_dict(site))

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
        "site_name": "Site",
        "node_id": "Link Name",
        "vlan_range": "VLAN Range",
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
            if iface.type.name == "FacilityPort":
                table.append(
                    [
                        tuple(site_names),
                        link.node_id,
                        iface.labels.vlan_range,
                        link.layer,
                    ]
                )

        return tabulate(
            table,
            headers=[
                "site_name",
                "node_id",
                "vlan_range",
                "link_layer",
            ],
        )

    def fp_to_dict(self, link: link.Link, iface: interface.Interface) -> dict:
        """
        Converts the link resources to a dictionary.

        Intended for printing links in table format.

        :return: collection of link properties
        :rtype: dict
        """
        return {
            "site_name": tuple(iface.name.split("_")),
            "node_id": link.node_id,
            "vlan_range": iface.labels.vlan_range if iface.labels else "N/A",
            "link_layer": link.layer,
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
        for _, link in self.topology.links.items():
            iface = link.interface_list[0]
            if iface.type.name == "FacilityPort":
                table.append(self.fp_to_dict(link, iface))

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
