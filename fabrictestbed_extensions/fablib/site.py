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
# Author: Komal Thareja(kthare10@renci.org)

from __future__ import annotations

import json
import logging
import traceback
from typing import Dict, List, Tuple

from fabrictestbed.slice_editor import Capacities
from fim.user import Component, node
from fim.user.composite_node import CompositeNode
from fim.view_only_dict import ViewOnlyDict

from fabrictestbed_extensions.fablib.constants import Constants


class ResourceConstants:
    attribute_name_mappings = {
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
        Constants.P4_SWITCH: {
            Constants.NON_PRETTY_NAME: Constants.P4_SWITCH.lower(),
            Constants.PRETTY_NAME: Constants.P4_SWITCH,
            Constants.HEADER_NAME: Constants.P4_SWITCH,
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
    pretty_names = {
        "name": "Name",
        "state": "State",
        "address": "Address",
        "location": "Location",
        "ptp_capable": "PTP Capable",
        Constants.HOSTS.lower(): Constants.HOSTS,
        Constants.CPUS.lower(): Constants.CPUS,
    }
    for attribute, names in attribute_name_mappings.items():
        pretty_name = names.get(Constants.PRETTY_NAME)
        non_pretty_name = names.get(Constants.NON_PRETTY_NAME)
        if pretty_name not in pretty_names:
            pretty_names[f"{non_pretty_name}_{Constants.AVAILABLE.lower()}"] = (
                f"{pretty_name} {Constants.AVAILABLE}"
            )
            pretty_names[f"{non_pretty_name}_{Constants.ALLOCATED.lower()}"] = (
                f"{pretty_name} {Constants.ALLOCATED}"
            )
            pretty_names[f"{non_pretty_name}_{Constants.CAPACITY.lower()}"] = (
                f"{pretty_name} {Constants.CAPACITY}"
            )


class Switch:
    def __init__(self, switch: node.Node, fablib_manager):
        """
        Initialize a Switch object.

        :param switch: The node representing the switch.
        :type switch: node.Node

        :param fablib_manager: The manager for the Fabric library.
        :type fablib_manager: Any

        """
        self.switch = switch
        self.fablib_manager = fablib_manager

    def get_capacity(self) -> int:
        """
        Get the capacity of the switch.

        :return: The capacity of the switch.
        :rtype: int
        """
        try:
            return self.switch.capacities.unit
        except Exception:
            return 0

    def get_allocated(self) -> int:
        """
        Get the allocated capacity of the switch.

        :return: The allocated capacity of the switch.
        :rtype: int
        """
        try:
            return self.switch.capacity_allocations.unit
        except Exception:
            return 0

    def get_available(self) -> int:
        """
        Get the available capacity of the switch.

        :return: The available capacity of the switch.
        :rtype: int
        """
        return self.get_capacity() - self.get_allocated()

    def get_fim(self) -> node.Node:
        """
        Get the FIM object of the Switch.

        :return: The FIM of the Switch.
        :rtype: node.Node
        """
        return self.switch


class Host:
    def __init__(self, host: node.Node, state: str, ptp: bool, fablib_manager):
        """
        Initialize a Host object.

        :param host: The node representing the host.
        :type host: node.Node

        :param state: The state of the host.
        :type state: str

        :param ptp: Boolean indicating if the host is PTP capable.
        :type ptp: bool

        :param fablib_manager: The manager for the Fabric library.
        :type fablib_manager: Any

        :return: None
        """
        self.host = host
        self.state = state
        self.ptp = ptp
        self.fablib_manager = fablib_manager
        self.host_info = {}
        self.__load()

    def get_fablib_manager(self):
        """
        Get the Fabric library manager associated with the host.

        :return: The Fabric library manager.
        :rtype: Any
        """
        return self.fablib_manager

    def __str__(self):
        """
        Convert the Host object to a string representation in JSON format.

        :return: JSON string representation of the Host object.
        :rtype: str
        """
        return self.to_json()

    def to_dict(self) -> dict:
        """
        Convert the Host object to a dictionary.

        :return: Dictionary representation of the Host object.
        :rtype: dict
        """
        d = {
            "name": self.get_name(),
            "state": self.get_state(),
            "address": self.get_location_postal(),
            "location": self.get_location_lat_long(),
            "ptp_capable": self.get_ptp_capable(),
        }

        for attribute, names in ResourceConstants.attribute_name_mappings.items():
            if attribute in Constants.P4_SWITCH:
                continue
            capacity = self.host_info.get(attribute.lower(), {}).get(
                Constants.CAPACITY.lower(), 0
            )
            allocated = self.host_info.get(attribute.lower(), {}).get(
                Constants.ALLOCATED.lower(), 0
            )
            available = capacity - allocated
            d[
                f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.AVAILABLE.lower()}"
            ] = available
            d[
                f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.CAPACITY.lower()}"
            ] = capacity
            d[
                f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.ALLOCATED.lower()}"
            ] = allocated

        return d

    def to_json(self) -> str:
        """
        Convert the Host object to a JSON string.

        :return: JSON string representation of the Host object.
        :rtype: str
        """
        return json.dumps(self.to_dict(), indent=4)

    def get_state(self) -> str:
        """
        Get the state of the host.

        :return: The state of the host.
        :rtype: str
        """
        if not self.state:
            return ""
        return self.state

    def get_fim(self) -> node.Node:
        """
        Get the FIM object of the host.

        :return: The FIM of the host.
        :rtype: node.Node
        """
        return self.host

    def __load(self):
        """
        Load information about the host.

        :return: None
        """
        try:
            self.host_info[Constants.CORES.lower()] = {
                Constants.CAPACITY.lower(): self.get_core_capacity(),
                Constants.ALLOCATED.lower(): self.get_core_allocated(),
            }
            self.host_info[Constants.RAM.lower()] = {
                Constants.CAPACITY.lower(): self.get_ram_capacity(),
                Constants.ALLOCATED.lower(): self.get_ram_allocated(),
            }
            self.host_info[Constants.DISK.lower()] = {
                Constants.CAPACITY.lower(): self.get_disk_capacity(),
                Constants.ALLOCATED.lower(): self.get_disk_allocated(),
            }

            if self.host.components:
                for component_model_name, c in self.host.components.items():
                    comp_cap = self.host_info.setdefault(
                        component_model_name.lower(), {}
                    )
                    comp_cap.setdefault(Constants.CAPACITY.lower(), 0)
                    comp_cap.setdefault(Constants.ALLOCATED.lower(), 0)
                    comp_cap[Constants.CAPACITY.lower()] += c.capacities.unit
                    if c.capacity_allocations:
                        comp_cap[
                            Constants.ALLOCATED.lower()
                        ] += c.capacity_allocations.unit
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            pass

    def get_components(self) -> ViewOnlyDict:
        """
        Get the components associated with the host.

        :return: Dictionary-like view of the components associated with the host.
        :rtype: ViewOnlyDict
        """
        try:
            return self.host.components
        except Exception as e:
            pass

    def get_component(self, comp_model_type: str) -> Component:
        """
        Get a specific component associated with the host.

        :param comp_model_type: The type of component to retrieve.
        :type comp_model_type: str

        :return: The specified component.
        :rtype: Component
        """
        try:
            return self.host.components.get(comp_model_type)
        except Exception as e:
            pass

    def show(
        self,
        output: str = None,
        fields: list[str] = None,
        quiet: bool = False,
        pretty_names=True,
    ) -> str:
        """
        Creates a tabulated string of all the available resources at a specific host.

        Intended for printing available resources at a host.

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
            pretty_names_dict = ResourceConstants.pretty_names
        else:
            pretty_names_dict = {}

        host_table = self.get_fablib_manager().show_table(
            data,
            fields=fields,
            title="Host",
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

        return host_table

    def get_location_postal(self) -> str:
        """
        Gets the location of a site by postal address

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: postal address of the site
        :rtype: String
        """
        try:
            return self.host.location.postal
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
            return self.host.location.to_latlon()
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
            return self.ptp
        except Exception as e:
            # logging.debug(f"Failed to get PTP status for {site}")
            return False

    def get_name(self):
        """
        Gets the host name

        :return: str
        """
        try:
            return self.host.name
        except Exception as e:
            # logging.debug(f"Failed to get name for {host}")
            return ""

    def get_core_capacity(self) -> int:
        """
        Gets the total number of cores at the site

        :return: core count
        :rtype: int
        """
        try:
            return self.host.capacities.core
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
            return self.host.capacity_allocations.core
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
            return self.host.capacities.ram
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
            return self.host.capacity_allocations.ram
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
            return self.host.capacities.disk
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
            return self.host.capacity_allocations.disk
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
            if component_model_name in self.host.components:
                component_capacity += self.host.components[
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
            if (
                component_model_name in self.host.components
                and self.host.components[component_model_name].capacity_allocations
            ):
                component_allocated += self.host.components[
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


class Site:
    def __init__(self, site: CompositeNode, fablib_manager):
        """
        Initialize a Site object.

        :param site: The node representing the site.
        :type site: node.Node

        :param fablib_manager: The manager for the Fabric library.
        :type fablib_manager: Any

        :return: None
        """
        super().__init__()
        self.site = site
        self.fablib_manager = fablib_manager
        self.hosts = {}
        self.switches = {}
        self.site_info = {}
        self.__load()

    def get_hosts(self) -> Dict[str, Host]:
        """
        Get the hosts associated with the site.

        :return: Dictionary of hosts associated with the site.
        :rtype: Dict[str, Host]
        """
        return self.hosts

    def __load(self):
        """
        Load information about the site.

        :return: None
        """
        self.__load_hosts()
        self.__load_site_info()

    def __load_hosts(self):
        """
        Load Hosts and Switches for a site.

        :return: None
        """
        try:
            from fim.user import NodeType

            for c_name, child in self.site.children.items():
                if child.type == NodeType.Server:
                    self.hosts[child.name] = Host(
                        host=child,
                        state=self.get_state(child.name),
                        ptp=self.get_ptp_capable(),
                        fablib_manager=self.fablib_manager,
                    )
                elif child.type == NodeType.Switch:
                    self.switches[child.name] = Switch(
                        switch=child, fablib_manager=self.get_fablib_manager()
                    )
        except Exception as e:
            logging.error(f"Error occurred - {e}")
            logging.error(traceback.format_exc())

    def to_json(self) -> str:
        """
        Convert the Site object to a JSON string.

        :return: JSON string representation of the Site object.
        :rtype: str
        """
        return json.dumps(self.to_dict(), indent=4)

    def get_fablib_manager(self):
        """
        Get the Fabric library manager associated with the site.

        :return: The Fabric library manager.
        :rtype: Any
        """
        return self.fablib_manager

    def to_row(self) -> Tuple[list, list]:
        """
        Convert the Site object to a row for tabular display.

        :return: Tuple containing headers and row for tabular display.
        :rtype: Tuple[list, list]
        """
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

        for attribute, names in ResourceConstants.attribute_name_mappings.items():
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

    def get_host(self, name: str) -> Host:
        """
        Get a specific host associated with the site.

        :param name: The name of the host to retrieve.
        :type name: str

        :return: The specified host.
        :rtype: Host
        """
        return self.hosts.get(name)

    def __str__(self) -> str:
        """
        Convert the Site object to a string representation in JSON format.

        :return: JSON string representation of the Site object.
        :rtype: str
        """
        return self.to_json()

    def get_name(self) -> str:
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
                if self.site.maintenance_info.get(host):
                    return str(self.site.maintenance_info.get(host).state)
                else:
                    return "Active"
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

    def to_dict(self) -> dict:
        """
        Convert site information into a dictionary
        """
        d = {
            "name": self.get_name(),
            "state": self.get_state(),
            "address": self.get_location_postal(),
            "location": self.get_location_lat_long(),
            "ptp_capable": self.get_ptp_capable(),
            "hosts": self.get_host_capacity(),
            "cpus": self.get_cpu_capacity(),
        }

        for attribute, names in ResourceConstants.attribute_name_mappings.items():
            capacity = self.site_info.get(attribute.lower(), {}).get(
                Constants.CAPACITY.lower(), 0
            )
            allocated = self.site_info.get(attribute.lower(), {}).get(
                Constants.ALLOCATED.lower(), 0
            )
            available = capacity - allocated
            d[
                f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.AVAILABLE.lower()}"
            ] = available
            d[
                f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.CAPACITY.lower()}"
            ] = capacity
            d[
                f"{names.get(Constants.NON_PRETTY_NAME)}_{Constants.ALLOCATED.lower()}"
            ] = allocated

        return d

    def __load_site_info(self):
        """
        Load the total site capacity of all components for a site
        """
        try:
            self.site_info[Constants.CORES.lower()] = {
                Constants.CAPACITY.lower(): self.get_core_capacity(),
                Constants.ALLOCATED.lower(): self.get_core_allocated(),
            }
            self.site_info[Constants.RAM.lower()] = {
                Constants.CAPACITY.lower(): self.get_ram_capacity(),
                Constants.ALLOCATED.lower(): self.get_ram_allocated(),
            }
            self.site_info[Constants.DISK.lower()] = {
                Constants.CAPACITY.lower(): self.get_disk_capacity(),
                Constants.ALLOCATED.lower(): self.get_disk_allocated(),
            }

            for h in self.hosts.values():
                if h.get_components():
                    for component_model_name, c in h.get_components().items():
                        comp_cap = self.site_info.setdefault(
                            component_model_name.lower(), {}
                        )
                        comp_cap.setdefault(Constants.CAPACITY.lower(), 0)
                        comp_cap.setdefault(Constants.ALLOCATED.lower(), 0)
                        comp_cap[Constants.CAPACITY.lower()] += c.capacities.unit
                        if c.capacity_allocations:
                            comp_cap[
                                Constants.ALLOCATED.lower()
                            ] += c.capacity_allocations.unit

            p4_mappings = ResourceConstants.attribute_name_mappings.get(
                Constants.P4_SWITCH
            )
            for s in self.switches.values():
                self.site_info[p4_mappings.get(Constants.NON_PRETTY_NAME)] = {
                    Constants.CAPACITY.lower(): s.get_capacity(),
                    Constants.ALLOCATED.lower(): s.get_allocated(),
                }

        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            pass

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
            pretty_names_dict = ResourceConstants.pretty_names
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
            for h in self.hosts.values():
                component_capacity += h.get_component_capacity(
                    component_model_name=component_model_name
                )
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
            for h in self.hosts.values():
                component_allocated += h.get_component_allocated(
                    component_model_name=component_model_name
                )
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
        """
        Get the FIM object of the site.

        :return: The FIM of the site.
        :rtype: node.Node
        """
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

    def get_host_names(self) -> List[str]:
        """
        Gets a list of all currently available hosts

        :return: list of host names
        :rtype: List[String]
        """
        return list(self.hosts.keys())
