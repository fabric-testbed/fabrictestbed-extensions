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
Methods to work with FABRIC `network services`_.

.. _`network services`: https://learn.fabric-testbed.net/knowledge-base/glossary/#network_service
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from fabrictestbed.external_api.orchestrator_client import SliverDTO

from fabrictestbed_extensions.utils.utils import Utils
from fim.slivers.path_info import Path
from fim.user import ERO, Gateway
from tabulate import tabulate

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabrictestbed_extensions.fablib.interface import Interface

import ipaddress
import json
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from fabrictestbed.slice_editor import Capacities, Labels
from fabrictestbed_extensions.fablib.template_mixin import TemplateMixin
from fabrictestbed.slice_editor import NetworkService as FimNetworkService
from fabrictestbed.slice_editor import ServiceType, UserData
from fim.slivers.network_service import NSLayer, ServiceType, NetworkServiceSliver
from fim.user.network_service import MirrorDirection

log = logging.getLogger("fablib")


class NetworkService(TemplateMixin):
    """
    A class for working with FABRIC network services.
    """

    _show_title = "Network"

    network_service_map = {
        "L2Bridge": ServiceType.L2Bridge,
        "L2PTP": ServiceType.L2PTP,
        "L2STS": ServiceType.L2STS,
        "PortMirror": ServiceType.PortMirror,
        "FABNetv4": ServiceType.FABNetv4,
        "FABNetv6": ServiceType.FABNetv6,
        "FABNetv4Ext": ServiceType.FABNetv4Ext,
        "FABNetv6Ext": ServiceType.FABNetv6Ext,
        "L3VPN": ServiceType.L3VPN,
    }

    # Type names used in fim network services
    fim_l2network_service_types = ["L2Bridge", "L2PTP", "L2STS"]
    fim_l3network_service_types = [
        "FABNetv4",
        "FABNetv6",
        "FABNetv4Ext",
        "FABNetv6Ext",
        "L3VPN",
    ]

    fim_special_service_types = ["PortMirror"]

    @staticmethod
    def __get_fim_l2network_service_types() -> List[str]:
        """
        Not intended for API use. Returns a list of FIM L2 network service types.

        :return: List of FIM L2 network service types.
        :rtype: List[str]
        """
        return NetworkService.fim_l2network_service_types

    @staticmethod
    def __get_fim_l3network_service_types() -> List[str]:
        """
        Not intended for API use. Returns a list of FIM L3 network service types.

        :return: List of FIM L3 network service types.
        :rtype: List[str]
        """
        return NetworkService.fim_l3network_service_types

    @staticmethod
    def __get_fim_special_service_types() -> List[str]:
        """
        Not intended for API use. Returns a list of FIM special service types.

        :return: List of FIM special service types.
        :rtype: List[str]
        """
        return NetworkService.fim_special_service_types

    @staticmethod
    def get_fim_network_service_types() -> List[str]:
        """
        Not intended for API use. Returns a list of all FIM network service types.

        :return: List of all FIM network service types.
        :rtype: List[str]
        """
        return (
            NetworkService.__get_fim_l2network_service_types()
            + NetworkService.__get_fim_l3network_service_types()
            + NetworkService.__get_fim_special_service_types()
        )

    @staticmethod
    def __calculate_l2_nstype(
        interfaces: List[Interface] = None, ero_enabled: bool = False
    ) -> ServiceType:
        """
        Not inteded for API use

        Determines the L2 network service type based on the number of interfaces inputted.

        :param interfaces: a list of interfaces
        :type interfaces: list[Interface]

        :param ero_enabled: Flag indicating if ERO is specified
        :type ero_enabled: bool

        :raises Exception: if no network service type is not appropriate for the number of interfaces
        :return: the network service type
        :rtype: ServiceType
        """

        from fabrictestbed_extensions.fablib.facility_port import FacilityPort

        # if there is a basic NIC, WAN must be STS
        basic_nic_count = 0

        sites = set([])
        includes_facility_port = False
        facility_port_interfaces = 0
        for interface in interfaces:
            sites.add(interface.get_site())
            if isinstance(interface.get_node(), FacilityPort):
                includes_facility_port = True
                facility_port_interfaces += 1
            if interface.get_model() == "NIC_Basic":
                basic_nic_count += 1

        rtn_nstype = None
        if 1 >= len(sites) >= 0:
            rtn_nstype = NetworkService.network_service_map["L2Bridge"]
        # elif basic_nic_count == 0 and len(sites) == 2 and len(interfaces) == 2:
        #    #TODO: remove this when STS works on all links.
        #    rtn_nstype = NetworkService.network_service_map['L2PTP']
        elif len(sites) == 2:
            # Use L2STS when connecting two facility ports instead of L2PTP
            # L2PTP limitation for Facility Ports:
            # basically the layer-2 point-to-point server template applied is not popping
            # vlan tags over the MPLS tunnel between two facility ports.
            if (
                (includes_facility_port and facility_port_interfaces < 2) or ero_enabled
            ) and not basic_nic_count:
                # For now WAN FacilityPorts require L2PTP
                rtn_nstype = NetworkService.network_service_map["L2PTP"]
            elif len(interfaces) >= 2:
                rtn_nstype = NetworkService.network_service_map["L2STS"]
        else:
            raise Exception(
                f"Invalid Network Service: Networks are limited to 2 unique sites. Site requested: {sites}"
            )

        return rtn_nstype

    @staticmethod
    def __validate_nstype(type, interfaces):
        """
        Not intended for API use


        Verifies the network service type against the number of interfaces.

        :param type: the network service type to check
        :type type: ServiceType
        :param interfaces: the list of interfaces to check
        :type interfaces: list[Interface]
        :raises Exception: if the network service type is invalid based on the number of interfaces
        :return: true if the network service type is valid based on the number of interfaces
        :rtype: bool
        """
        # Just an empty network created; NS type would be validated when add_interface is invoked.
        if not len(interfaces):
            return True

        from fabrictestbed_extensions.fablib.facility_port import FacilityPort

        sites = set([])
        nics = set([])
        nodes = set([])
        for interface in interfaces:
            try:
                sites.add(interface.get_site())
                nics.add(interface.get_model())
                nodes.add(interface.get_node())
            except Exception as e:
                log.info(
                    f"validate_nstype: skipping interface {interface.get_name()}, likely its a facility port"
                )

        # models: 'NIC_Basic', 'NIC_ConnectX_6', 'NIC_ConnectX_5'
        if type == NetworkService.network_service_map["L2Bridge"]:
            if len(sites) > 1:
                raise Exception(
                    f"Network type {type} must be empty or include interfaces from exactly one site. {len(sites)} "
                    f"sites requested: {sites}"
                )

        elif type == NetworkService.network_service_map["L2PTP"]:
            if not len(sites) == 2:
                raise Exception(
                    f"Network type {type} must include interfaces from exactly two sites. {len(sites)} sites "
                    f"requested: {sites}"
                )
            if "NIC_Basic" in nics:
                raise Exception(
                    f"Network type {type} does not support interfaces of type 'NIC_Basic'"
                )

        elif type == NetworkService.network_service_map["L2STS"]:
            exception_list = []
            if len(sites) != 2:
                exception_list.append(
                    f"Network type {type} must include interfaces from exactly two sites. {len(sites)} sites "
                    f"requested: {sites}"
                )
            if len(interfaces) > 2:
                hosts = set([])
                nodes_per_site = {}
                for interface in interfaces:
                    node = interface.get_node()
                    if node.get_site() not in nodes_per_site:
                        nodes_per_site[node.get_site()] = 0
                    if isinstance(node, FacilityPort):
                        continue
                    nodes_per_site[node.get_site()] += 1
                for interface in interfaces:
                    node = interface.get_node()
                    if (
                        interface.get_model() == "NIC_Basic"
                        and nodes_per_site[node.get_site()] > 1
                    ):
                        if node.get_host() is None:
                            exception_list.append(
                                f"Network type {type} does not support multiple NIC_Basic interfaces on VMs "
                                f"residing on the same host. Please see Node.set_host(host_name) to explicitly "
                                f"bind a nodes to a specific host. Node {node.get_name()} is unbound."
                            )
                        elif node.get_host() in hosts:
                            exception_list.append(
                                f"Network type {type} does not support multiple NIC_Basic interfaces on VMs residing "
                                f"on the same host. Please see Node.set_host(host_name) to explicitly bind a nodes "
                                f"to a specific host. Multiple nodes bound to {node.get_host()}."
                            )
                        else:
                            hosts.add(node.get_host())

            if len(exception_list) > 0:
                raise Exception(f"{exception_list}")
        else:
            raise Exception(f"Unknown network type {type}")

        return True

    @staticmethod
    def new_portmirror_service(
        slice: Slice = None,
        name: str = None,
        mirror_interface_name: str = None,
        mirror_interface_vlan: str = None,
        receive_interface: Optional[Interface] = None,
        mirror_direction: str = "both",
    ) -> NetworkService:
        """
        Instantiate a new PortMirror service.

        ``mirror_direction`` can be ``"rx"``, ``"tx"`` or ``"both"``
        (non-case-sensitive)
        """
        # decode the direction
        if not isinstance(mirror_interface_name, str):
            raise Exception(
                f"When creating a PortMirror service mirror_interface is specified by name"
            )
        if not isinstance(mirror_direction, str):
            raise Exception(
                f'When creating a PortMirror service mirror_direction is a string "rx", "tx" or "both"'
                f'defaulting to "both"'
            )
        if not receive_interface:
            raise Exception(
                f"For PortMirror service the receiving interface must be specified upfront"
            )
        direction = MirrorDirection.Both
        # enable below when we are officially off python 3.9 and into 3.10 or higher
        # match mirror_direction.lower():
        #    case ['rx']:
        #        direction = MirrorDirection.RX_Only
        #    case ['tx']:
        #        direction = MirrorDirection.TX_Only
        #   case ['both']:
        #        direction = MirrorDirection.Both
        #   case _:
        #       raise Exception(f'Unknown direction specifier "{mirror_direction}" when creating PortMirror'
        #                        f'service {name}')
        no_case_direction = mirror_direction.lower()
        if no_case_direction == "rx":
            direction = MirrorDirection.RX_Only
        elif no_case_direction == "tx":
            direction = MirrorDirection.TX_Only
        elif no_case_direction == "both":
            pass
        else:
            raise Exception(
                f'Unknown direction specifier "{mirror_direction}" when creating PortMirror'
                f"service {name}"
            )
        log.info(
            f"Create PortMirror Service: Slice: {slice.get_name()}, Network Name: {name} listening on "
            f"{mirror_interface_name} with direction {direction}"
        )
        fim_network_service = slice.topology.add_port_mirror_service(
            name=name,
            from_interface_name=mirror_interface_name,
            from_interface_vlan=mirror_interface_vlan,
            to_interface=receive_interface.fim_interface,
            direction=direction,
        )

        network_service = NetworkService(
            slice=slice, fim_network_service=fim_network_service
        )
        network_service.init_fablib_data()
        return network_service

    @staticmethod
    def new_l3network(
        slice: Slice = None,
        name: str = None,
        interfaces: List[Interface] = [],
        type: str = None,
        user_data: dict = {},
        technology: str = None,
        subnet: Optional[ipaddress.ip_network] = None,
        site: str = None,
    ):
        """
        Not inteded for API use. See slice.add_l3network
        """
        if type == "IPv6":
            nstype = ServiceType.FABNetv6
        elif type == "IPv4":
            nstype = ServiceType.FABNetv4
        elif type == "IPv4Ext":
            nstype = ServiceType.FABNetv4Ext
        elif type == "IPv6Ext":
            nstype = ServiceType.FABNetv6Ext
        elif type == "L3VPN":
            nstype = ServiceType.L3VPN
        else:
            raise Exception(
                "Invalid L3 Network Type: Allowed values [IPv4, IPv4Ext, IPv6, IPv6Ext, L3VPN]"
            )

        # TODO: need a fabnet version of this
        # validate nstype and interface List
        # NetworkService.validate_nstype(nstype, interfaces)

        return NetworkService.__new_network_service(
            slice=slice,
            name=name,
            nstype=nstype,
            interfaces=interfaces,
            user_data=user_data,
            technology=technology,
            subnet=subnet,
            site=site
        )

    @staticmethod
    def new_l2network(
        slice: Slice = None,
        name: str = None,
        interfaces: List[Interface] = [],
        type: str = None,
        user_data: dict = {},
    ):
        """
        Not inteded for API use. See slice.add_l2network

        Creates a new L2 network service.

        :param slice: the fablib slice to build this network on
        :type slice: Slice
        :param name: the name of the new network
        :type name: str
        :param interfaces: a list of interfaces to build the network service on
        :type interfaces: list[Interface]
        :param type: the type of network service to build (optional)
        :tyep type: str
        :return: the new L2 network service
        :rtype: NetworkService
        """
        if type is None:
            nstype = NetworkService.__calculate_l2_nstype(interfaces=interfaces)
        else:
            if type in NetworkService.__get_fim_l2network_service_types():
                nstype = NetworkService.network_service_map[type]
            else:
                raise Exception(
                    f"Invalid l2 network type: {type}. Please choose from "
                    f"{NetworkService.__get_fim_l2network_service_types()} or None for automatic selection"
                )

        # validate nstype and interface List
        NetworkService.__validate_nstype(nstype, interfaces)

        # Set default VLANs for P2P networks that did not pass in VLANs
        if nstype == ServiceType.L2PTP and len(
            interfaces
        ):  # or nstype == ServiceType.L2STS:
            vlan1 = interfaces[0].get_vlan()
            vlan2 = interfaces[1].get_vlan()

            if vlan1 is None and vlan2 is None:
                # TODO: Long term we might have multiple vlan on one property
                # and will need to make sure they are unique.  For now this okay
                interfaces[0].set_vlan("100")
                interfaces[1].set_vlan("100")
            elif vlan1 is None and vlan2 is not None:
                # Match VLANs if one is set.
                interfaces[0].set_vlan(vlan2)
            elif vlan1 is not None and vlan2 is None:
                # Match VLANs if one is set.
                interfaces[1].set_vlan(vlan1)

            # for interface in interfaces:
            #    if interface.get_model() != 'NIC_Basic' and not interface.get_vlan():
            #
            #        interface.set_vlan("100")
        network_service = NetworkService.__new_network_service(
            slice=slice,
            name=name,
            nstype=nstype,
            interfaces=interfaces,
            user_data=user_data,
        )
        return network_service

    @staticmethod
    def __new_network_service(
        slice: Slice = None,
        name: str = None,
        nstype: ServiceType = None,
        interfaces: List[Interface] = [],
        user_data: dict = {},
        technology: str = None,
        subnet: Optional[ipaddress.ip_network] = None,
        site: str = None,
    ):
        """
        Not intended for API use. See slice.add_l2network


        Creates a new FABRIC network service and returns the fablib instance.

        :param slice: the fabric slice to build the network service with
        :type slice: Slice

        :param name: the name of the new network service
        :type name: str

        :param nstype: the type of network service to create
        :type nstype: ServiceType

        :param interfaces: a list of interfaces to
        :type interfaces: List

        :param technology: Specify the technology used should be set to AL2S when using for AL2S peering; otherwise None
        :type technology: str

        :param subnet: Request a specific subnet for FabNetv4, FabNetv6 or FabNetv6Ext services.
                       It's ignored for any other services.
        :type ipaddress.ip_network

        :param site: Site for L3 networks
        :type site: str

        :return: the new fablib network service
        :rtype: NetworkService
        """
        fim_interfaces = []
        for interface in interfaces:
            fim_interfaces.append(interface.get_fim())

        log.info(
            f"Create Network Service: Slice: {slice.get_name()}, Network Name: {name}, Type: {nstype}"
        )
        fim_network_service = slice.topology.add_network_service(
            name=name, nstype=nstype, interfaces=fim_interfaces, technology=technology,
        )

        if site is not None and nstype in NetworkService.__get_fim_l3network_service_types():
            fim_network_service.site = site

        if subnet:
            if nstype == ServiceType.FABNetv4:
                fim_network_service.gateway = Gateway(
                    lab=Labels(
                        ipv4_subnet=subnet.with_prefixlen,
                        ipv4=str(next(subnet.hosts())),
                    )
                )
            elif nstype in [ServiceType.FABNetv6, ServiceType.FABNetv6Ext]:
                fim_network_service.gateway = Gateway(
                    lab=Labels(
                        ipv6_subnet=subnet.with_prefixlen,
                        ipv6=str(next(subnet.hosts())),
                    )
                )

        network_service = NetworkService(
            slice=slice, fim_network_service=fim_network_service
        )
        network_service.set_user_data(user_data)
        network_service.init_fablib_data()

        return network_service

    @staticmethod
    def get_l3network_services(slice: Slice = None) -> list:
        """
        Gets all L3 networks services in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        topology = slice.get_fim_topology()

        rtn_network_services = []
        fim_network_service = None
        log.debug(
            f"NetworkService.get_fim_l3network_service_types(): {NetworkService.__get_fim_l3network_service_types()}"
        )

        for net_name, net in topology.network_services.items():
            log.debug(f"scanning network: {net_name}, net: {net}")
            if (
                str(net.get_property("type"))
                in NetworkService.__get_fim_l3network_service_types()
            ):
                log.debug(f"returning network: {net_name}, net: {net}")
                rtn_network_services.append(
                    NetworkService(slice=slice, fim_network_service=net)
                )

        return rtn_network_services

    @staticmethod
    def get_l3network_service(slice: Slice = None, name: str = None):
        """
        Gets a particular L3 network service from this slice.

        :param slice: the fabric slice to build this network on
        :type slice: Slice
        :param name: Name network
        :type name: String
        :return: network services on this slice
        :rtype: list[NetworkService]
        """
        for net in NetworkService.get_l3network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.slice_name}, network {name}")

    @staticmethod
    def get_l2network_services(slice: Slice = None) -> list:
        """
        Not inteded for API use.

        Gets a list of L2 network services on a fablib slice.

        :param slice: the fablib slice from which to get the network services
        :type slice: Slice
        :return: a list of network services on slice
        :rtype: list[NetworkService]
        """
        topology = slice.get_fim_topology()

        rtn_network_services = []
        for net_name, net in topology.network_services.items():
            if (
                str(net.get_property("type"))
                in NetworkService.__get_fim_l2network_service_types()
            ):
                rtn_network_services.append(
                    NetworkService(slice=slice, fim_network_service=net)
                )

        return rtn_network_services

    @staticmethod
    def get_l2network_service(slice: Slice = None, name: str = None):
        """
        Not inteded for API use.

        Gets a particular network service on a fablib slice.

        :param slice: the fablib slice from which to get the network service
        :type slice: Slice
        :param name: the name of the network service to get
        :type name: str
        :raises Exception: if the network is not found
        :return: the particular network service
        :rtype: NetworkService
        """
        for net in NetworkService.get_l2network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.slice_name}, network {name}")

    @staticmethod
    def get_network_services(
        slice: Slice = None, output: str = "list"
    ) -> dict[str, NetworkService]:
        """
        Gets all network services (L2 and L3) in this slice

        :return: Dict of all network services in this slice
        :rtype: dict[str, NetworkService]
        """

        topology = slice.get_fim_topology()

        rtn_network_services = {}
        for net_name, net in topology.network_services.items():
            if (
                str(net.get_property("type"))
                in NetworkService.get_fim_network_service_types()
            ):
                rtn_network_services[net_name] = NetworkService(
                    slice=slice, fim_network_service=net
                )

        if output == "dict":
            return rtn_network_services
        else:
            return list(rtn_network_services.values())

    @staticmethod
    def get_network_service(slice: Slice = None, name: str = None):
        """
        Gest a particular network service from this slice.

        :param slice: the fablib slice from which to get the network services
        :type slice: Slice
        :param name: the name of the network service to search for
        :type name: str
        :return: a particular network service
        :rtype: NetworkService
        """
        for net in NetworkService.get_network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.slice_name}, network {name}")

    def __init__(
        self,
        slice: Slice = None,
        fim_network_service: FimNetworkService = None,
        name: str = None,
    ):
        """
        .. note::

            Not inteded for API use.

        :param slice: the fablib slice to set as instance state
        :type slice: Slice

        :param fim_network_service: the FIM network service to set as
            instance state
        :type fim_network_service: FimNetworkService

        :param name: the name of the network service
        :type name: str
        """
        super().__init__()
        self.fim_network_service = fim_network_service
        self.slice = slice

        self.interfaces = None
        self.sliver = None

        try:
            if self.slice.isStable():
                self.sliver = self.slice.get_sliver(
                    reservation_id=self.get_reservation_id()
                )
        except:
            pass

        self.lock = threading.Lock()

        # Caching support
        self._cached_type: Optional[str] = None
        self._cached_layer: Optional[str] = None
        self._cached_subnet: Optional[Union[IPv4Network, IPv6Network]] = None
        self._cached_gateway: Optional[Union[IPv4Address, IPv6Address]] = None

        self._interfaces_cache: Dict[str, Interface] = {}

    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        super(NetworkService, self)._invalidate_cache()

        self._cached_type = None
        self._cached_layer = None
        self._cached_subnet = None
        self._cached_gateway = None

        self._interfaces_cache = {}
        self.interfaces = None

    def update(self, fim_network_service: FimNetworkService = None):
        """
        Update the network service with new FIM data.

        :param fim_network_service: The new FIM network service data
        :type fim_network_service: FimNetworkService
        """
        if fim_network_service:
            self.fim_network_service = fim_network_service
            self._invalidate_cache()
            self._fim_dirty = False

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the network service.

        Intended for printing network service information.

        :return: Tabulated string of network service information
        :rtype: String
        """
        table = [
            ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Layer", self.get_layer()],
            ["Type", self.get_type()],
            ["Site", self.get_site()],
            ["Gateway", self.get_gateway()],
            ["Subnet", self.get_subnet()],
            ["State", self.get_reservation_state()],
            ["Error", self.get_error_message()],
        ]

        return tabulate(table)  # , headers=["Property", "Value"])

    @staticmethod
    def get_pretty_name_dict():
        """
        Return mappings from non-pretty names to pretty names.

        Pretty names are used when rendering table headers.
        """
        return {
            "id": "ID",
            "name": "Name",
            "layer": "Layer",
            "type": "Type",
            "site": "Site",
            "gateway": "Gateway",
            "subnet": "Subnet",
            "state": "State",
            "error": "Error",
        }

    def toDict(self, skip: List[str] = None):
        """
        Returns the network attributes as a dictionary.

        Results are cached. Cache is invalidated when ``_invalidate_cache()``
        is called.

        :param skip: list of keys to skip
        :type skip: List[str]
        :return: network attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        if self._cached_dict is None:
            d = {}
            d["id"] = str(self.get_reservation_id())
            d["name"] = str(self.get_name())
            d["layer"] = str(self.get_layer())
            d["type"] = str(self.get_type())
            d["site"] = str(self.get_site())
            d["subnet"] = str(self.get_subnet())
            d["gateway"] = str(self.get_gateway())
            d["state"] = str(self.get_reservation_state())
            d["error"] = str(self.get_error_message())
            self._cached_dict = d

        if not skip:
            return dict(self._cached_dict)
        return {k: v for k, v in self._cached_dict.items() if k not in skip}

    def generate_template_context(self, skip: List[str] = None):
        context = self.toDict(skip=skip)
        context["interfaces"] = []

        return context

    def _configure_template_environment(self, environment):
        environment.json_encoder = json.JSONEncoder(ensure_ascii=False)

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice this network service is built on.

        :return: the slice this network is on
        :rtype: Slice
        """
        return self.slice

    def get_site(self) -> Optional[str]:
        """
        Gets site name on network service.
        """
        sliver = self.get_sliver()
        if sliver:
            if isinstance(sliver, SliverDTO):
                return sliver.site
            elif isinstance(sliver, NetworkServiceSliver):
                return sliver.site
            return None
        else:
            return None

    def get_layer(self) -> Optional[str]:
        """
        Gets the layer of the network services (L2 or L3).

        Results are cached for performance.

        :return: L2 or L3
        :rtype: String
        """
        if self._cached_layer is None:
            try:
                if self.get_fim():
                    layer = self.get_fim().get_property(pname="layer")
                    self._cached_layer = layer if layer else None
                else:
                    self._cached_layer = None
            except Exception as e:
                log.warning(f"Failed to get layer: {e}")
                self._cached_layer = None
        return self._cached_layer

    def get_type(self):
        """
        Gets the type of the network services.

        Results are cached for performance.

        :return: network service types
        :rtype: String
        """
        if self._cached_type is None:
            try:
                if self.get_fim():
                    ns_type = self.get_fim().get_property("type")
                    self._cached_type = ns_type if ns_type else None
                else:
                    self._cached_type = None
            except Exception as e:
                log.warning(f"Failed to get type: {e}")
                self._cached_type = None
        return self._cached_type

    def get_sliver(self) -> SliverDTO:
        """
        Gets the sliver.
        """
        if not self.sliver and self.slice.isStable():
            self.sliver = self.slice.get_sliver(
                reservation_id=self.get_reservation_id()
            )
        return self.sliver

    def get_gateway(self) -> Optional[Union[IPv4Address, IPv6Address]]:
        """
        Gets the assigned gateway for a FABnetv L3 IPv6 or IPv4 network.

        Results are cached for performance. Cache is invalidated when
        ``set_gateway()`` or ``set_instantiated()`` is called.

        :return: gateway IP
        :rtype: IPv4Address or IPv6Network
        """
        if self._cached_gateway is not None:
            return self._cached_gateway

        try:
            gateway = None

            if self.is_instantiated():
                if self.get_layer() == NSLayer.L3:
                    if self.get_sliver().sliver.get('Type') in ("FABNetv4", "FABNetv4Ext"):
                        gateway = IPv4Address(self.get_sliver().gateway.get("ipv4"))
                    else:
                        gateway = IPv6Address(self.get_sliver().gateway.get("ipv6"))
                else:
                    # L2 Network
                    fablib_data = self.get_fablib_data()
                    try:
                        gateway = ipaddress.ip_address(fablib_data["subnet"]["gateway"])
                    except Exception as e:
                        gateway = None
            else:
                gateway = f"{self.get_name()}.gateway"

            if gateway is not None:
                self._cached_gateway = gateway
            return gateway
        except Exception as e:
            log.warning(f"Failed to get gateway: {e}")

    def get_available_ips(
        self, count: int = 256
    ) -> Optional[List[IPv4Address or IPv6Address]]:
        """
        Gets the IPs available for a FABnet L3 network

        Note: large IPv6 address spaces take considerable time to build this
        list. By default this will return the first 256 addresses.  If you needed
        more addresses, set the count parameter.

        :param count: number of addresse to include
        :type slice: Slice
        :return: gateway IP
        :rtype: List[IPv4Address]
        """
        try:
            ip_list = []
            gateway = self.get_gateway()
            for i in range(count):
                log.debug(f"adding IP {i}")
                ip_list.append(gateway + i + 1)
            return ip_list
        except Exception as e:
            log.warning(f"Failed to get_available_ips: {e}")

    def get_public_ips(self) -> Optional[Union[List[IPv4Address] or List[IPv6Address]]]:
        """
        Get list of public IPs assigned to the FabNetv*Ext service

        :return: List of Public IPs
        :rtype: List[IPv4Address] or List[IPv6Address] or None
        """
        if self.get_fim().labels is not None:
            if self.get_fim().labels.ipv4 is not None:
                result = []
                for x in self.get_fim().labels.ipv4:
                    result.append(IPv4Address(x))
                return result
            elif self.get_fim().labels.ipv6 is not None:
                result = []
                for x in self.get_fim().labels.ipv6:
                    result.append(IPv6Address(x))
                return result
        return None

    def get_subnet(self) -> Optional[Union[IPv4Network, IPv6Network]]:
        """
        Gets the assigned subnet for a FABnet L3 IPv6 or IPv4 network.

        Results are cached for performance. Cache is invalidated when
        ``set_subnet()`` or ``set_instantiated()`` is called.

        :return: subnet
        :rtype: IPv4Network or IPv6Network
        """
        if self._cached_subnet is not None:
            return self._cached_subnet

        try:
            subnet = None
            if self.is_instantiated():
                if self.get_layer() == NSLayer.L3:
                    if self.get_sliver().sliver.get('Type') in ("FABNetv4", "FABNetv4Ext"):
                        subnet_key = "ipv4_subnet"
                    else:
                        subnet_key = "ipv6_subnet"
                    gateway = self.get_sliver().gateway
                    if gateway:
                        subnet_str = gateway.get(subnet_key)
                        if subnet_str:
                            subnet = ipaddress.ip_network(subnet_str)
                else:
                    # L2 Network
                    fablib_data = self.get_fablib_data()
                    if fablib_data.get("subnet") and fablib_data.get("subnet").get(
                        "subnet"
                    ):
                        try:
                            subnet = ipaddress.ip_network(
                                fablib_data["subnet"]["subnet"]
                            )
                        except Exception as e:
                            log.warning(f"Failed to get L2 subnet: {e}")
            else:
                subnet = f"{self.get_name()}.subnet"

            if subnet is not None:
                self._cached_subnet = subnet
            return subnet
        except Exception as e:
            log.warning(f"Failed to get subnet: {e}")

    def get_interfaces(self, refresh: bool = False) -> List[Interface]:
        """
        Gets the interfaces on this network service.

        Results are cached. Use refresh=True to force reload.

        :param refresh: force refresh from FIM
        :type refresh: bool
        :return: the interfaces on this network service
        :rtype: List[Interfaces]
        """
        if self._interfaces_cache and not refresh and not self._fim_dirty:
            return list(self._interfaces_cache.values())

        self._interfaces_cache = {}
        self.interfaces = []

        for interface in self.get_fim().interface_list:
            log.debug(f"interface: {interface}")

            try:
                iface = self.get_slice().get_interface(name=interface.name)
                self.interfaces.append(iface)
                self._interfaces_cache[interface.name] = iface
            except:
                log.warning(f"interface not found: {interface.name}")

        return self.interfaces

    def get_interface(self, name: str = None, refresh: bool = False) -> Optional[Interface]:
        """
        Gets a particular interface on this network service.

        :param name: the name of the interface to search for
        :type name: str
        :param refresh: force refresh from FIM
        :type refresh: bool
        :return: the particular interface
        :rtype: Interface
        """
        # Ensure cache is populated
        if not self._interfaces_cache or refresh or self._fim_dirty:
            self.get_interfaces(refresh=refresh)

        # Check cache first (exact match)
        if name in self._interfaces_cache:
            return self._interfaces_cache[name]

        # Fall back to substring match for compatibility
        for iface_name, iface in self._interfaces_cache.items():
            if name in iface_name:
                return iface

        return None

    def has_interface(self, interface: Interface) -> bool:
        """
        Determines whether this network service has a particular interface.

        :param interface: the fablib interface to search for
        :type interface: Interface
        :return: whether this network service has interface
        :rtype: bool
        """
        for fim_interface in self.get_fim().interface_list:
            if fim_interface.name.endswith(interface.get_name()):
                return True

        return False

    def get_fim(self) -> FimNetworkService:
        """
        Gets the FABRIC information model (FIM) object.
        """
        return self.fim_network_service

    def __replace_network_service(self, nstype: ServiceType):
        fim_interfaces = []
        name = self.get_name()

        # Use cache if available — get_interfaces() may fail to resolve
        # FIM connection-point names back to fablib Interface objects for
        # pre-submit networks (e.g. facility ports).
        if self._interfaces_cache:
            current_interfaces = list(self._interfaces_cache.values())
        else:
            current_interfaces = self.get_interfaces()

        for interface in current_interfaces:
            fim_interfaces.append(interface.get_fim())
            self.get_fim().disconnect_interface(interface=interface.get_fim())

        user_data = self.get_user_data()
        saved_cache = dict(self._interfaces_cache) if self._interfaces_cache else {}
        self.get_slice().topology.remove_network_service(name=self.get_name())

        self.fim_network_service = self.get_slice().topology.add_network_service(
            name=name, nstype=nstype, interfaces=fim_interfaces
        )
        # Restore the interface cache so that subsequent add_interface()
        # calls still see all previously connected interfaces
        self._interfaces_cache = saved_cache
        self.interfaces = current_interfaces
        self.set_user_data(user_data)

    def add_interface(self, interface: Interface):
        """
        Add an :py:class:`.Interface` to the network service.
        """
        if self.get_type() == ServiceType.PortMirror:
            raise Exception(
                "Interfaces cannot be attached to PortMirror service - they can only"
                "be specified at service creation"
            )

        iface_fablib_data = interface.get_fablib_data()

        # Build new_interfaces from cache if populated (reliable for
        # pre-submit), falling back to FIM-based resolution.  The FIM
        # resolution path (get_interfaces) can silently lose interfaces
        # whose FIM connection-point names don't match fablib names
        # (e.g. facility ports), so the cache is the source of truth
        # when available.
        if self._interfaces_cache:
            new_interfaces = list(self._interfaces_cache.values())
        else:
            new_interfaces = self.get_interfaces()
        if interface not in new_interfaces:
            new_interfaces.append(interface)

        curr_nstype = self.get_type()
        if self.get_layer() == NSLayer.L2:
            ero_enabled = True if self.get_fim().ero else False
            new_nstype = NetworkService.__calculate_l2_nstype(
                interfaces=new_interfaces, ero_enabled=ero_enabled
            )
            if curr_nstype != new_nstype:
                self.__replace_network_service(new_nstype)
            self.get_fim().connect_interface(interface=interface.get_fim())
            # Add to cache so subsequent add_interface calls see all
            # previously connected interfaces
            self._interfaces_cache[interface.get_name()] = interface
        elif self.get_layer() == NSLayer.L3 and self.is_instantiated():
            if interface.get_site() != self.get_site():
                raise Exception("L3 networks can only include nodes from one site")

        if "addr" in iface_fablib_data:
            addr = iface_fablib_data["addr"]
        else:
            addr = None

        if "auto" in iface_fablib_data:
            auto = iface_fablib_data["auto"]
        else:
            auto = False

        if self.get_subnet():
            if addr:
                iface_fablib_data["addr"] = str(self.allocate_ip(addr))
            elif auto:
                iface_fablib_data["addr"] = str(self.allocate_ip())

        interface.set_fablib_data(iface_fablib_data)

        if self.get_layer() == NSLayer.L3:
            self.get_fim().connect_interface(interface=interface.get_fim())
            # Add to cache after L3 connect as well
            self._interfaces_cache[interface.get_name()] = interface

    def remove_interface(self, interface: Interface):
        """
        Remove an :py:class:`.Interface` from the network service.
        """
        iface_fablib_data = interface.get_fablib_data()

        self.free_ip(interface.get_ip_addr())

        # Use cache if available for accurate interface tracking
        if self._interfaces_cache:
            interfaces = list(self._interfaces_cache.values())
        else:
            interfaces = self.get_interfaces()

        if interface in interfaces:
            interfaces.remove(interface)

        curr_nstype = self.get_type()
        if self.get_layer() == NSLayer.L2:
            ero_enabled = True if self.get_fim().ero else False
            new_nstype = NetworkService.__calculate_l2_nstype(
                interfaces=interfaces, ero_enabled=ero_enabled
            )
            if curr_nstype != new_nstype:
                self.__replace_network_service(new_nstype)

        interface.set_fablib_data(iface_fablib_data)

        self.get_fim().disconnect_interface(interface=interface.get_fim())
        # Remove from cache instead of clearing entirely
        iface_name = interface.get_name()
        self._interfaces_cache.pop(iface_name, None)
        # Also remove by iterating in case the key doesn't match exactly
        self._interfaces_cache = {
            k: v for k, v in self._interfaces_cache.items() if v is not interface
        }

    def delete(self):
        """
        Delete the network service.
        """
        for ifs in self.get_interfaces():
            ifs.network = None

        self.get_slice().get_fim_topology().remove_network_service(name=self.get_name())
        # Mark slice topology as dirty so cached network/interface lists
        # get refreshed on next access
        self.get_slice()._topology_dirty = True

    def set_subnet(self, subnet: Union[IPv4Network, IPv6Network]):
        """
        Add subnet info to the network service.
        """
        fablib_data = self.get_fablib_data()
        if "subnet" not in fablib_data:
            fablib_data["subnet"] = {}
        fablib_data["subnet"]["subnet"] = str(subnet)
        fablib_data["subnet"]["allocated_ips"] = []
        self.set_fablib_data(fablib_data)
        self._cached_subnet = None

    def set_gateway(self, gateway: Union[IPv4Address, IPv6Address]):
        """
        Add gateway info to the network service.
        """
        fablib_data = self.get_fablib_data()
        if "subnet" not in fablib_data:
            fablib_data["subnet"] = {}
        fablib_data["subnet"]["gateway"] = str(gateway)
        self.set_fablib_data(fablib_data)
        self._cached_gateway = None

    def get_allocated_ips(self):
        """
        Get the list of IP addesses allocated for the network service.
        """
        try:
            allocated_ips = []
            for addr in self.get_fablib_data()["subnet"]["allocated_ips"]:
                allocated_ips.append(ipaddress.ip_address(addr))

            return allocated_ips
        except Exception as e:
            return []

    def set_allocated_ip(self, addr: Optional[Union[IPv4Address, IPv6Address]] = None):
        """
        Add ``addr`` to the list of allocated IPs.
        """
        fablib_data = self.get_fablib_data()
        if "subnet" not in fablib_data:
            fablib_data["subnet"] = {}
        allocated_ips = fablib_data["subnet"]["allocated_ips"]
        allocated_ips.append(str(addr))
        self.set_fablib_data(fablib_data)

    def allocate_ip(self, addr: Optional[Union[IPv4Address, IPv6Address]] = None):
        """
        Allocate an IP for the network service.
        """
        try:
            self.lock.acquire()
            subnet = self.get_subnet()
            allocated_ips = self.get_allocated_ips()

            if addr:
                # if addr != subnet.network_address and addr not in allocated_ips:
                if addr not in allocated_ips:
                    self.set_allocated_ip(addr)
                    return addr
            elif (
                type(subnet) == ipaddress.IPv4Network
                or type(subnet) == ipaddress.IPv6Network
            ):
                for host in subnet:
                    if host != subnet.network_address and host not in allocated_ips:
                        self.set_allocated_ip(host)

                        return host
            return None
        finally:
            self.lock.release()

    def set_allocated_ips(self, allocated_ips: list[Union[IPv4Address, IPv6Address]]):
        """
        Set a list of IPs to be "allocated IPs".
        """
        fablib_data = self.get_fablib_data()
        allocated_ips_strs = []
        for ip in allocated_ips:
            allocated_ips_strs.append(str(ip))

        if "subnet" not in fablib_data:
            fablib_data["subnet"] = {}

        fablib_data["subnet"]["allocated_ips"] = allocated_ips_strs
        self.set_fablib_data(fablib_data)

    def free_ip(self, addr: Union[IPv4Address, IPv6Address]):
        """
        Remove an IP from the list of allocated IPs.
        """
        try:
            self.lock.acquire()
            allocated_ips = self.get_allocated_ips()
            if addr in allocated_ips:
                allocated_ips.remove(addr)
            self.set_allocated_ips(allocated_ips)
        finally:
            self.lock.release()

    def make_ip_publicly_routable(self, ipv6: list[str] = None, ipv4: list[str] = None):
        """
        Mark a list of IPs as publicly routable.
        """
        labels = self.get_fim().labels
        if labels is None:
            labels = Labels()
        if self.fim_network_service.type == ServiceType.FABNetv4Ext:
            labels = Labels.update(labels, ipv4=ipv4)

        elif self.fim_network_service.type == ServiceType.FABNetv6Ext:
            labels = Labels.update(labels, ipv6=ipv6)

        self.fim_network_service.set_properties(labels=labels)
        self._invalidate_cache()

    def init_fablib_data(self):
        """
        Initialize fablib data.
        """
        fablib_data = {"instantiated": "False", "mode": "manual"}
        self.set_fablib_data(fablib_data)

    def is_instantiated(self):
        """
        Return ``True`` if network service has been instantiated.
        """
        fablib_data = self.get_fablib_data()
        if "instantiated" in fablib_data and fablib_data["instantiated"] == "True":
            return True
        else:
            return False

    def set_instantiated(self, instantiated: bool = True):
        """
        Set instantiated flag in the fablib_data saved in UserData
        blob in the FIM model.

        :param instantiated: flag indicating if the service has been
            instantiated or not
        :type instantiated: bool
        """
        fablib_data = self.get_fablib_data()
        fablib_data["instantiated"] = str(instantiated)
        self.set_fablib_data(fablib_data)
        # Invalidate subnet/gateway caches since instantiation state
        # affects which code path is used to compute them
        self._cached_subnet = None
        self._cached_gateway = None

    def config(self):
        """
        Sets up the meta data for the Network Service

            - For layer3 services, Subnet, gateway and allocated IPs
              are updated/maintained fablib_data saved in UserData
              blob in the FIM model

            - For layer2 services, no action is taken
        """
        if not self.is_instantiated():
            self.set_instantiated(True)

        # init
        if self.get_layer() == NSLayer.L3:
            # init fablib data for fabnet networks
            self.set_subnet(self.get_subnet())
            self.set_gateway(self.get_gateway())
            allocated_ips = self.get_allocated_ips()
            if not allocated_ips:
                allocated_ips = []
            if self.get_gateway() not in allocated_ips:
                allocated_ips.append(self.get_gateway())
            self.set_allocated_ip(self.get_gateway())

    def peer(
        self,
        other: NetworkService,
        labels: Labels,
        peer_labels: Labels,
        capacities: Capacities,
    ):
        """
        Peer a network service; used for AL2S peering between FABRIC Networks and Cloud Networks
        Peer this network service to another. A few constraints are enforced like services being
        of the same type. Both services will have ServicePort interfaces facing each other over a link.
        It typically requires labels and capacities to put on the interface facing the other service

        :param other: network service to be peered
        :type other: NetworkService
        :param labels: labels
        :type labels: Labels
        :param peer_labels: peer labels
        :type peer_labels: Labels
        :param capacities: capacities
        :type capacities: Capacities

        """
        # Peer Cloud L3VPN with FABRIC L3VPN
        self.get_fim().peer(
            other.get_fim(),
            labels=labels,
            peer_labels=peer_labels,
            capacities=capacities,
        )

    def set_l2_route_hops(self, hops: List[str]):
        """
        Define the sequence of sites or hops to be used for a layer 2 connection.

        Maps site names to corresponding layer 2 loopback IPs used in Explicit Route Options (ERO)
        in the Network Service configuration.

        :param hops: A list of site names to be used as hops.
        :type hops: List[str]
        """
        if not hops:
            return  # Skip if no hops provided

        interfaces = self.get_interfaces()
        if len(interfaces) != 2 or self.get_type() not in {
            ServiceType.L2STS,
            ServiceType.L2PTP,
        }:
            raise Exception(
                "ERO can only be set for a Point-to-Point Layer2 connection."
            )

        src_site, dst_site = (ifs.get_site() for ifs in interfaces)
        resources = self.get_fablib_manager().get_resources()
        resources.validate_requested_ero_path(source=src_site, end=dst_site, hops=hops)

        path = Path()
        path.set_symmetric(hops)
        ero = ERO()
        ero.set(payload=path)

        ns_type = self.__calculate_l2_nstype(interfaces=interfaces, ero_enabled=True)
        self.get_fim().set_properties(type=ns_type, ero=ero)
        self._invalidate_cache()

    def set_bandwidth(self, bw: int):
        """
        Set the bandwidth for an L2PTP Network Service.

        This sets the bandwidth uniformly for the service and both connected interfaces.

        :param bw: Bandwidth in Gbps
        :type bw: int
        """
        if not bw:
            return self  # Return early if bw is 0 or None

        fim = self.get_fim()
        fim.capacities = Capacities(bw=bw)
        self._invalidate_cache()

        for interface in self.get_interfaces():
            interface.set_bandwidth(bw=bw)

        return self

    def get_bandwidth(self) -> int:
        """
        Get the bandwidth of the network service (L2PTP only).

        :return: Bandwidth in Gbps
        :rtype: int
        """
        fim = self.get_fim()
        return getattr(fim.capacities, "bw", 1) if fim and fim.capacities else 1
