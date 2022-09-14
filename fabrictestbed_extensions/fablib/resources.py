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

from fabrictestbed.slice_editor import AdvertisedTopology
from fabrictestbed.slice_editor import Capacities
from fabrictestbed.slice_manager import Status


class Resources:

    def __init__(self,  fablib_manager):
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
            #logging.debug(f"site -- {site}")
            table.append( [     site.name,
                                self.get_cpu_capacity(site_name),
                                f"{self.get_core_available(site_name)}/{self.get_core_capacity(site_name)}",
                                f"{self.get_ram_available(site_name)}/{self.get_ram_capacity(site_name)}",
                                f"{self.get_disk_available(site_name)}/{self.get_disk_capacity(site_name)}",
                                #self.get_host_capacity(site_name),
                                #self.get_location_postal(site_name),
                                #self.get_location_lat_long(site_name),
                                f"{self.get_component_available(site_name,'SharedNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SharedNIC-ConnectX-6')}",
                                f"{self.get_component_available(site_name,'SmartNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-6')}",
                                f"{self.get_component_available(site_name,'SmartNIC-ConnectX-5')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-5')}",
                                f"{self.get_component_available(site_name,'NVME-P4510')}/{self.get_component_capacity(site_name,'NVME-P4510')}",
                                f"{self.get_component_available(site_name,'GPU-Tesla T4')}/{self.get_component_capacity(site_name,'GPU-Tesla T4')}",
                                f"{self.get_component_available(site_name,'GPU-RTX6000')}/{self.get_component_capacity(site_name,'GPU-RTX6000')}",
                                ] )

        return tabulate(table, headers=["Name",
                                        "CPUs",
                                        "Cores",
                                        f"RAM ({Capacities.UNITS['ram']})",
                                        f"Disk ({Capacities.UNITS['disk']})",
                                        #"Workers"
                                        #"Physical Address",
                                        #"Location Coordinates"
                                        "Basic (100 Gbps NIC)",
                                        "ConnectX-6 (100 Gbps x2 NIC)",
                                        "ConnectX-5 (25 Gbps x2 NIC)",
                                        "P4510 (NVMe 1TB)",
                                        "Tesla T4 (GPU)",
                                        "RTX6000 (GPU)",
                                        ])

    def show_site(self, site_name: str) -> str:
        """
        Creates a tabulated string of all the available resources at a specific site.

        Intended for printing available resources at a site.

        :param site_name: site name
        :type site_name: String
        :return: Tabulated string of available resources
        :rtype: String
        """
        try:
            site = self.get_topology_site(site_name)

            table = [   [ "Name", site.name ],
                        [ "CPUs", self.get_cpu_capacity(site_name) ],
                        [ f"Cores ({Capacities.UNITS['core']})", f"{self.get_core_available(site_name)}/{self.get_core_capacity(site_name)}" ],
                        [ f"RAM ({Capacities.UNITS['ram']})", f"{self.get_ram_available(site_name)}/{self.get_ram_capacity(site_name)}" ],
                        [ f"Disk ({Capacities.UNITS['disk']})", f"{self.get_disk_available(site_name)}/{self.get_disk_capacity(site_name)}" ],
                        [ "Worker Count", self.get_host_capacity(site_name) ],
                        [ "Physical Address", self.get_location_postal(site_name) ],
                        [ "Location Coordinates", self.get_location_lat_long(site_name) ],
                        [ "Basic (100 Gbps NIC)", f"{self.get_component_available(site_name,'SharedNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SharedNIC-ConnectX-6')}" ],
                        [ "ConnectX-6 (100 Gbps x2 NIC)", f"{self.get_component_available(site_name,'SmartNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-6')}" ],
                        [ "ConnectX-5 (25 Gbps x2 NIC)", f"{self.get_component_available(site_name,'SmartNIC-ConnectX-5')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-5')}" ],
                        [ "P4510 (NVMe 1TB)", f"{self.get_component_available(site_name,'NVME-P4510')}/{self.get_component_capacity(site_name,'NVME-P4510')}" ],
                        [ "Tesla T4 (GPU)", f"{self.get_component_available(site_name,'GPU-Tesla T4')}/{self.get_component_capacity(site_name,'GPU-Tesla T4')}" ],
                        [ "RTX6000 (GPU)", f"{self.get_component_available(site_name,'GPU-RTX6000')}/{self.get_component_capacity(site_name,'GPU-RTX6000')}" ],
                    ]

            return tabulate(table) #, headers=["Property", "Value"])
        except Exception as e:
            logging.warning(f"Failed to show site {site_name}")
            logging.error(e, exc_info=True)

            return ""

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
        Note intended as an API call
        """
        try:
            return self.topology.sites[site_name]
        except Exception as e:
            logging.warning(f"Failed to get site {site_name}")
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
            return self.get_topology_site(site_name).components[component_model_name].capacities.unit
        except Exception as e:
            logging.debug(f"Failed to get {component_model_name} capacity {site_name}")
            return 0

    def get_component_allocated(self, site_name: str, component_model_name: str) -> int:
        """
        Gets gets number of currrently allocated comoponents on a the site
        by the component by model name.

        :param site_name: site name
        :type site_name: String
        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently allocated component of this model
        :rtype: int
        """
        try:
            return self.get_topology_site(site_name).components[component_model_name].capacity_allocations.unit
        except Exception as e:
            logging.debug(f"Failed to get {component_model_name} alloacted {site_name}")
            return 0

    def get_component_available(self, site_name: str, component_model_name: str) -> int:
        """
        Gets gets number of currrently available comoponents on a the site
        by the component by model name.

        :param site_name: site name
        :type site_name: String
        :param component_model_name: component model name
        :type component_model_name: String
        :return: currently available component of this model
        :rtype: int
        """
        try:
            return self.get_component_capacity(site_name, component_model_name) - self.get_component_allocated(site_name, component_model_name)
        except Exception as e:
            logging.debug(f"Failed to get {component_model_name} available {site_name}")
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
            #site.get_property("location").to_latlon()
            return self.get_topology_site(site_name).get_property("location").to_latlon()
        except Exception as e:
            logging.warning(f"Failed to get location postal {site_name}")
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
            logging.debug(f"Failed to get location postal {site_name}")
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
            logging.debug(f"Failed to get host count {site_name}")
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
            logging.debug(f"Failed to get cpu capacity {site_name}")
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
            logging.debug(f"Failed to get core capacity {site_name}")
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
            logging.debug(f"Failed to get cores alloacted {site_name}")
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
            return self.get_core_capacity(site_name) - self.get_core_allocated(site_name)
        except Exception as e:
            logging.debug(f"Failed to get cores available {site_name}")
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
            logging.debug(f"Failed to get ram capacity {site_name}")
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
            logging.debug(f"Failed to get ram alloacted {site_name}")
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
            logging.debug(f"Failed to get ram available {site_name}")
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
            logging.debug(f"Failed to get disk capacity {site_name}")
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
            logging.debug(f"Failed to get disk alloacted {site_name}")
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
            return self.get_disk_capacity(site_name) - self.get_disk_allocated(site_name)
        except Exception as e:
            logging.debug(f"Failed to get disk available {site_name}")
            return self.get_disk_capacity(site_name)

    def get_fablib_manager(self):
        return self.fablib_manager

    def update(self):
        """
        Update the available resources by querying the FABRIC services

        """
        return_status, topology = self.get_fablib_manager().get_slice_manager().resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))

        self.topology = topology

    def get_topology(self, update: bool = False) -> AdvertisedTopology:
        """
        Not intended for API use
        """
        if update or self.topology is None: self.update()

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
