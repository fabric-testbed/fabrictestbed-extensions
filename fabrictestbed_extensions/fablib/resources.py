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
from datetime import datetime
from typing import List, Tuple

from fabrictestbed.slice_editor import AdvertisedTopology
from fabrictestbed.slice_manager import Status
from fim.user import interface, link, node
from tabulate import tabulate

from fabrictestbed_extensions.fablib.site import ResourceConstants, Site


class Resources:
    def __init__(
        self,
        fablib_manager,
        force_refresh: bool = False,
        start: datetime = None,
        end: datetime = None,
        avoid: List[str] = None,
        includes: List[str] = None,
    ):
        """
        :param fablib_manager: a :class:`FablibManager` instance.
        :type fablib_manager: fablib.FablibManager

        :param force_refresh: force a refresh of available testbed
            resources.
        :type force_refresh: bool

        :param start: start time in UTC format: %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param end: end time in UTC format:  %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param avoid: list of sites to avoid
        :type: list of string

        :param includes: list of sites to include
        :type: list of string

        """
        super().__init__()

        self.fablib_manager = fablib_manager

        self.topology = None

        self.sites = {}

        self.update(
            force_refresh=force_refresh,
            start=start,
            end=end,
            includes=includes,
            avoid=avoid,
        )

    def __str__(self) -> str:
        """
        Creates a tabulated string of all the available resources.

        Intended for printing available resources.

        :return: Tabulated string of available resources
        :rtype: String
        """
        table = []
        headers = []
        for site_name, site in self.sites.items():
            headers, row = site.to_row()
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
        :param output: Output type
        :type output: str
        :param fields: List of fields to include
        :type fields: List
        :param quiet: flag indicating verbose or quiet display
        :type quiet: bool
        :param pretty_names: flag indicating if pretty names for the fields to be used or not
        :type pretty_names: bool
        :param latlon: Flag indicating if lat lon to be included or not
        :type latlon: bool

        :return: Tabulated string of available resources
        :rtype: String
        """
        site = self.sites.get(site_name)
        return site.show(
            output=output, fields=fields, quiet=quiet, pretty_names=pretty_names
        )

    def get_site_names(self) -> List[str]:
        """
        Gets a list of all currently available site names

        :return: list of site names
        :rtype: List[String]
        """
        return list(self.sites.keys())

    def get_site(self, site_name: str) -> Site:
        """
        Get a specific site by name.

        :param site_name: The name of the site to retrieve.
        :type site_name: str

        :return: The specified site.
        :rtype: Site
        """
        try:
            return self.sites.get(site_name)
        except Exception as e:
            logging.warning(f"Failed to get site {site_name}")

    def __get_topology_site(self, site_name: str) -> node.Node:
        """
        Get a specific site from the topology.

        :param site_name: The name of the site to retrieve from the topology.
        :type site_name: str

        :return: The node representing the specified site from the topology.
        :rtype: node.Node
        """
        try:
            return self.topology.sites.get(site_name)
        except Exception as e:
            logging.warning(f"Failed to get site {site_name}")

    def get_state(self, site: str or node.Node) -> str:
        """
        Gets the maintenance state of the node

        :param site: site Node or NodeSliver object or name
        :type site: String or Node or NodeSliver
        :return: str(MaintenanceState)
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_name()
        except Exception as e:
            # logging.warning(f"Failed to get site state {site_name}")
            return ""

    def get_component_capacity(
        self,
        site: str or node.Node,
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
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_component_capacity(
                component_model_name=component_model_name
            )

        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} capacity {site}: {e}")
            return component_capacity

    def get_component_allocated(
        self,
        site: str or node.Node,
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
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_component_allocated(
                component_model_name=component_model_name
            )
        except Exception as e:
            # logging.error(f"Failed to get {component_model_name} allocated {site}: {e}")
            return component_allocated

    def get_component_available(
        self,
        site: str or node.Node,
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
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_component_available(
                component_model_name=component_model_name
            )
        except Exception as e:
            # logging.debug(f"Failed to get {component_model_name} available {site}")
            return self.get_component_capacity(site, component_model_name)

    def get_location_lat_long(self, site: str or node.Node) -> Tuple[float, float]:
        """
        Gets gets location of a site in latitude and longitude

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: latitude and longitude of the site
        :rtype: Tuple(float,float)
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_location_lat_long()
        except Exception as e:
            # logging.warning(f"Failed to get location postal {site}")
            return 0, 0

    def get_location_postal(self, site: str or node.Node) -> str:
        """
        Gets the location of a site by postal address

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: postal address of the site
        :rtype: String
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_location_postal()
        except Exception as e:
            # logging.debug(f"Failed to get location postal {site}")
            return ""

    def get_host_capacity(self, site: str or node.Node) -> int:
        """
        Gets the number of hosts at the site

        :param site: site name or site object
        :type site: String or Node or NodeSliver
        :return: host count
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_host_capacity()
        except Exception as e:
            # logging.debug(f"Failed to get host count {site}")
            return 0

    def get_cpu_capacity(self, site: str or node.Node) -> int:
        """
        Gets the total number of cpus at the site

        :param site: site name or site object
        :type site: String or node.Node or NodeSliver
        :return: cpu count
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_cpu_capacity()
        except Exception as e:
            # logging.debug(f"Failed to get cpu capacity {site}")
            return 0

    def get_core_capacity(self, site: str or node.Node) -> int:
        """
        Gets the total number of cores at the site

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: core count
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_core_capacity()
        except Exception as e:
            # logging.debug(f"Failed to get core capacity {site}")
            return 0

    def get_core_allocated(self, site: str or node.Node) -> int:
        """
        Gets the number of currently allocated cores at the site

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: core count
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_core_allocated()
        except Exception as e:
            # logging.debug(f"Failed to get cores allocated {site}")
            return 0

    def get_core_available(self, site: str or node.Node) -> int:
        """
        Gets the number of currently available cores at the site

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: core count
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_core_available()
        except Exception as e:
            # logging.debug(f"Failed to get cores available {site}")
            return self.get_core_capacity(site)

    def get_ram_capacity(self, site: str or node.Node) -> int:
        """
        Gets the total amount of memory at the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_ram_capacity()
        except Exception as e:
            # logging.debug(f"Failed to get ram capacity {site}")
            return 0

    def get_ram_allocated(self, site: str or node.Node) -> int:
        """
        Gets the amount of memory currently  allocated the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_ram_allocated()
        except Exception as e:
            # logging.debug(f"Failed to get ram allocated {site}")
            return 0

    def get_ram_available(self, site: str or node.Node) -> int:
        """
        Gets the amount of memory currently  available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: ram in GB
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_ram_available()
        except Exception as e:
            # logging.debug(f"Failed to get ram available {site_name}")
            return self.get_ram_capacity(site)

    def get_disk_capacity(self, site: str or node.Node) -> int:
        """
        Gets the total amount of disk available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_disk_capacity()
        except Exception as e:
            # logging.debug(f"Failed to get disk capacity {site}")
            return 0

    def get_disk_allocated(self, site: str or node.Node) -> int:
        """
        Gets the amount of disk allocated the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_disk_allocated()
        except Exception as e:
            # logging.debug(f"Failed to get disk allocated {site}")
            return 0

    def get_disk_available(self, site: str or node.Node) -> int:
        """
        Gets the amount of disk available the site in GB

        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: disk in GB
        :rtype: int
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_disk_available()
        except Exception as e:
            # logging.debug(f"Failed to get disk available {site_name}")
            return self.get_disk_capacity(site)

    def get_ptp_capable(self, site: str or node.Node) -> bool:
        """
        Gets the PTP flag of the site - if it has a native PTP capability
        :param site: site name or object
        :type site: String or Node or NodeSliver
        :return: boolean flag
        :rtype: bool
        """
        try:
            if isinstance(site, str):
                site = self.get_site(site_name=site)
            elif isinstance(site, node.Node):
                site = Site(site=site, fablib_manager=self.fablib_manager)
            return site.get_ptp_capable()
        except Exception as e:
            # logging.debug(f"Failed to get PTP status for {site}")
            return False

    def get_fablib_manager(self):
        """
        Get the Fabric library manager associated with the resources.

        :return: The Fabric library manager.
        :rtype: Any
        """
        return self.fablib_manager

    def update(
        self,
        force_refresh: bool = False,
        start: datetime = None,
        end: datetime = None,
        avoid: List[str] = None,
        includes: List[str] = None,
    ):
        """
        Update the available resources by querying the FABRIC services
        :param force_refresh: force a refresh of available testbed
            resources.
        :type force_refresh: bool

        :param start: start time in UTC format: %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param end: end time in UTC format:  %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param avoid: list of sites to avoid
        :type: list of string

        :param includes: list of sites to include
        :type: list of string

        """
        logging.info(f"Updating available resources")
        return_status, topology = (
            self.get_fablib_manager()
            .get_slice_manager()
            .resources(
                force_refresh=force_refresh,
                level=2,
                start=start,
                end=end,
                excludes=avoid,
                includes=includes,
            )
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to get advertised_topology: {}, {}".format(
                    return_status, topology
                )
            )

        self.topology = topology

        for site_name, site in self.topology.sites.items():
            s = Site(site=site, fablib_manager=self.get_fablib_manager())
            self.sites[site_name] = s

    def get_topology(self, update: bool = False) -> AdvertisedTopology:
        """
        Get the FIM object of the Resources.

        :return: The FIM of the resources.
        :rtype: AdvertisedTopology
        """
        return self.get_fim(update=update)

    def get_fim(self, update: bool = False) -> AdvertisedTopology:
        """
        Get the FIM object of the Resources.

        :return: The FIM of the resources.
        :rtype: AdvertisedTopology
        """
        if update or self.topology is None:
            self.update()

        return self.topology

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
        """
        Convert site information into a JSON string.

        :param site: Name of the site or site object.
        :type site: str or node.Node

        :param latlon: Flag indicating whether to convert address to latitude and longitude.
        :type latlon: bool

        :return: JSON string representation of the site information.
        :rtype: str
        """
        return json.dumps(self.site_to_dict(site, latlon=latlon), indent=4)

    def site_to_dict(self, site: str or node.Node, latlon=True):
        """
        Convert site information into a dictionary.

        :param site: Name of the site or site object.
        :type site: str or node.Node

        :param latlon: Flag indicating whether to convert address to latitude and longitude.
        :type latlon: bool

        :return: Dictionary representation of the site information.
        :rtype: dict
        """
        if isinstance(site, str):
            site = self.get_site(site_name=site)
        elif isinstance(site, node.Node):
            site = Site(site=site, fablib_manager=self.fablib_manager)
        return site.to_dict()

    def list_sites(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
        latlon=True,
    ):
        """
        List information about sites.

        :param output: Output type for listing information.
        :type output: Any, optional

        :param fields: List of fields to include in the output.
        :type fields: Optional[List[str]], optional

        :param quiet: Flag indicating whether to display output quietly.
        :type quiet: bool, optional

        :param filter_function: Function to filter the output.
        :type filter_function: Optional[Callable[[Dict], bool]], optional

        :param pretty_names: Flag indicating whether to use pretty names for fields.
        :type pretty_names: bool, optional

        :param latlon: Flag indicating whether to convert address to latitude and longitude.
        :type latlon: bool, optional

        :return: Table listing information about sites.
        :rtype: str
        """
        table = []
        for site_name, site in self.sites.items():
            site_dict = site.to_dict()
            if site_dict.get("hosts"):
                table.append(site_dict)

        if pretty_names:
            pretty_names_dict = ResourceConstants.pretty_names
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

    def list_hosts(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        List information about hosts.

        :param output: Output type for listing information.
        :type output: Any, optional

        :param fields: List of fields to include in the output.
        :type fields: Optional[List[str]], optional

        :param quiet: Flag indicating whether to display output quietly.
        :type quiet: bool, optional

        :param filter_function: Function to filter the output.
        :type filter_function: Optional[Callable[[Dict], bool]], optional

        :param pretty_names: Flag indicating whether to use pretty names for fields.
        :type pretty_names: bool, optional

        :return: Table listing information about hosts.
        :rtype: str
        """
        table = []
        for site_name, site in self.sites.items():
            for host_name, host in site.get_hosts().items():
                host_dict = host.to_dict()
                table.append(host_dict)

        if pretty_names:
            pretty_names_dict = ResourceConstants.pretty_names
        else:
            pretty_names_dict = {}

        return self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Hosts",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

    def validate_requested_ero_path(self, source: str, end: str, hops: List[str]):
        """
        Validate a requested network path between two sites for layer 2 network connection
        :param source: Source site
        :type source: str
        :param end: Target site
        :type end: str
        :param hops: requested hops
        :type hops: List[str

        :raises Exception in case of error or if requested path does not exist or is invalid
        """
        hop_sites_node_ids = []
        for hop in hops:
            ns = self.get_topology().network_services.get(f"{hop.upper()}_ns")
            if not ns:
                raise Exception(f"Hop: {hop} is not found in the available sites!")
            hop_sites_node_ids.append(ns.node_id)

        source_site = self.__get_topology_site(site_name=source)
        end_site = self.__get_topology_site(site_name=end)

        if not source_site or not end_site:
            raise Exception(f"Source {source} or End: {end} is not found!")

        path = self.get_fim().graph_model.get_nodes_on_path_with_hops(
            node_a=source_site.node_id, node_z=end_site.node_id, hops=hop_sites_node_ids
        )
        if not path or not len(path):
            raise Exception(
                f"Requested path via {hops} between {source} and {end} is invalid!"
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
        "allocated_vlan_range": "Allocated VLAN Range",
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
                "allocated_vlan_range",
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
        label_allocations = iface.get_property("label_allocations")
        return {
            "name": name,
            "site_name": site,
            "node_id": iface.node_id,
            "vlan_range": iface.labels.vlan_range if iface.labels else "N/A",
            "allocated_vlan_range": (
                label_allocations.vlan if label_allocations else "N/A"
            ),
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

        :param output: Output type for listing information.
        :type output: Any, optional

        :param fields: List of fields to include in the output.
        :type fields: Optional[List[str]], optional

        :param quiet: Flag indicating whether to display output quietly.
        :type quiet: bool, optional

        :param filter_function: Function to filter the output.
        :type filter_function: Optional[Callable[[Dict], bool]], optional

        :param pretty_names: Flag indicating whether to use pretty names for fields.
        :type pretty_names: bool, optional

        :return: Formatted table of resources.
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
