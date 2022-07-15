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
from typing import List

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabrictestbed_extensions.fablib.interface import Interface
    from fabric_cf.orchestrator.swagger_client import Sliver as OrchestratorSliver

from fabrictestbed.slice_editor import ServiceType, NetworkService as FimNetworkService
from fim.slivers.network_service import ServiceType, NSLayer

from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network


class NetworkService:
    network_service_map = {'L2Bridge': ServiceType.L2Bridge,
                           'L2PTP': ServiceType.L2PTP,
                           'L2STS': ServiceType.L2STS,
                          }

    # Type names used in fim network services
    fim_l2network_service_types = ['L2Bridge', 'L2PTP', 'L2STS']
    fim_l3network_service_types = ['FABNetv4', 'FABNetv6']


    @staticmethod
    def get_fim_l2network_service_types() -> List[str]:
        """
        Not inteded for API use
        """
        return NetworkService.fim_l2network_service_types

    @staticmethod
    def get_fim_l3network_service_types() -> List[str]:
        """
        Not inteded for API use
        """
        return NetworkService.fim_l3network_service_types

    @staticmethod
    def get_fim_network_service_types() -> List[str]:
        """
        Not inteded for API use
        """
        return NetworkService.get_fim_l2network_service_types() + NetworkService.get_fim_l3network_service_types()

    @staticmethod
    def calculate_l2_nstype(interfaces: List[Interface] = None) -> ServiceType:
        """
        Not inteded for API use

        Determines the L2 network service type based on the number of interfaces inputted.

        :param interfaces: a list of interfaces
        :type interfaces: list[Interface]
        :raises Exception: if no network service type is not appropriate for the number of interfaces
        :return: the network service type
        :rtype: ServiceType
        """

        from fabrictestbed_extensions.fablib.facility_port import FacilityPort

        # if there is a basic NIC, WAN must be STS
        basic_nic_count = 0

        sites = set([])
        includes_facility_port = False
        for interface in interfaces:
            sites.add(interface.get_site())
            if isinstance(interface.get_component(), FacilityPort):
                includes_facility_port = True
            if interface.get_model()=="NIC_Basic":
                basic_nic_count += 1

        rtn_nstype = None
        if len(sites) == 1:
            rtn_nstype = NetworkService.network_service_map['L2Bridge']
        #elif basic_nic_count == 0 and len(sites) == 2 and len(interfaces) == 2:
        #    #TODO: remove this when STS works on all links.
        #    rtn_nstype = NetworkService.network_service_map['L2PTP']
        elif len(sites) == 2:
            if includes_facility_port:
                # For now WAN FacilityPorts require L2PTP
                rtn_nstype = NetworkService.network_service_map['L2PTP']
            elif len(interfaces) >= 2:
                rtn_nstype = NetworkService.network_service_map['L2STS']
        else:
            raise Exception(f"Invalid Network Service: Networks are limited to 2 unique sites. Site requested: {sites}")

        return rtn_nstype

    @staticmethod
    def validate_nstype(type: ServiceType, interfaces: List[Interface]) -> bool:
        """
        Not inteded for API use


        Verifies the network service type against the number of interfaces.

        :param type: the network service type to check
        :type type: ServiceType
        :param interfaces: the list of interfaces to check
        :type interfaces: list[Interface]
        :raises Exception: if the network service type is invalid based on the number of interfaces
        :return: true if the network service type is valid based on the number of interfaces
        :rtype: bool
        """
        sites = set([])
        nics = set([])
        nodes = set([])
        for interface in interfaces:
            sites.add(interface.get_site())
            nics.add(interface.get_model())
            nodes.add(interface.get_node())

        # models: 'NIC_Basic', 'NIC_ConnectX_6', 'NIC_ConnectX_5'
        if type == NetworkService.network_service_map['L2Bridge']:
            if not len(sites) == 1:
                raise Exception(f"Network type {type} must include interfaces from exactly one site. "
                                f"{len(sites)} sites requested: {sites}")

        elif type == NetworkService.network_service_map['L2PTP']:
            if not len(sites) == 2:
                raise Exception(f"Network type {type} must include interfaces from exactly two sites. "
                                f"{len(sites)} sites requested: {sites}")
            if 'NIC_Basic' in nics:
                raise Exception(f"Network type {type} does not support interfaces of type 'NIC_Basic'")

        elif type == NetworkService.network_service_map['L2STS']:
            exception_list = []
            if len(sites) != 2:
                exception_list.append(f"Network type {type} must include interfaces from exactly two sites. "
                                      f"{len(sites)} sites requested: {sites}")
            if len(interfaces) > 2:
                hosts = set([])
                for interface in interfaces:
                    node = interface.get_node()
                    if interface.get_model() == 'NIC_Basic':
                        if node.get_host() is None:
                            exception_list.append(f"Network type {type} does not support multiple NIC_Basic "
                                                  f"interfaces on VMs residing on the same host. Please see "
                                                  f"Node.set_host(host_nane) to explicitily bind a nodes to a "
                                                  f"specific host. Node {node.get_name()} is unbound.")
                        elif node.get_host() in hosts:
                            exception_list.append(f"Network type {type} does not support multiple NIC_Basic interfaces "
                                                  f"on VMs residing on the same host. Please see "
                                                  f"Node.set_host(host_nane) to explicitily bind a nodes to a specific "
                                                  f"host. Multiple nodes bound to {node.get_host()}.")
                        else:
                            hosts.add(node.get_host())

            if len(exception_list) > 0:
                raise Exception(f"{exception_list}")
        else:
            raise Exception(f"Unknown network type {type}")

        return True

    @staticmethod
    def new_l3network(slice: Slice = None, name: str = None, interfaces: List[Interface] = [], type: str = None):
        """
        Not inteded for API use. See slice.add_l3network
        """
        if type == "IPv6":
            nstype = ServiceType.FABNetv6
        else:
            nstype = ServiceType.FABNetv4

        # TODO: need a fabnet version of this
        # validate nstype and interface List
        #NetworkService.validate_nstype(nstype, interfaces)

        return NetworkService.new_network_service(slice=slice, name=name, nstype=nstype, interfaces=interfaces)

    @staticmethod
    def new_l2network(slice: Slice = None, name: str = None, interfaces: List[Interface] = [], type: str = None):
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
            nstype = NetworkService.calculate_l2_nstype(interfaces=interfaces)
        else:
            if type in NetworkService.get_fim_l2network_service_types():
                nstype = NetworkService.network_service_map[type]
            else:
                raise Exception(f"Invalid l2 network type: {type}. Please choose from "
                                f"{NetworkService.get_fim_l2network_service_types()} or None for automatic selection")

        # validate nstype and interface List
        NetworkService.validate_nstype(nstype, interfaces)

        #Set default VLANs for P2P networks that did not assing VLANs
        if nstype == ServiceType.L2PTP: # or nstype == ServiceType.L2STS:
            vlan1 = interfaces[0].get_vlan()
            vlan2 = interfaces[1].get_vlan()

            if vlan1 == None and vlan2 == None:
                # TODO: Long term we might have multiple vlan on one property
                # and will need to make sure they are unique.  For now this okay
                interfaces[0].set_vlan("100")
                interfaces[1].set_vlan("100")
            elif vlan1 == None and vlan2 != None:
                # Match VLANs if one is set.
                interfaces[0].set_vlan(vlan2)
            elif vlan1 != None and vlan2 == None:
                # Match VLANs if one is set.
                interfaces[1].set_vlan(vlan1)


            #for interface in interfaces:
            #    if interface.get_model() != 'NIC_Basic' and not interface.get_vlan():
            #
            #        interface.set_vlan("100")

        return NetworkService.new_network_service(slice=slice, name=name, nstype=nstype, interfaces=interfaces)

    @staticmethod
    def new_network_service(slice: Slice = None, name: str = None, nstype: ServiceType = None,
                            interfaces: List[Interface] = []):
        """
        Not inteded for API use. See slice.add_l2network


        Creates a new FABRIC network service and returns the fablib instance.

        :param slice: the fabric slice to build the network service with
        :type slice: Slice
        :param name: the name of the new network service
        :type name: str
        :param nstype: the type of network service to create
        :type nstype: ServiceType
        :param interfaces: a list of interfaces to
        :return: the new fablib network service
        :rtype: NetworkService
        """
        fim_interfaces = []
        for interface in interfaces:
            fim_interfaces.append(interface.get_fim_interface())

        logging.info(f"Create Network Service: Slice: {slice.get_name()}, Network Name: {name}, Type: {nstype}")
        fim_network_service = slice.topology.add_network_service(name=name,
                                                                 nstype=nstype,
                                                                 interfaces=fim_interfaces)

        return NetworkService(slice=slice, fim_network_service=fim_network_service)

    @staticmethod
    def get_l3network_services(slice: Slice = None) -> list:
        """
        Not inteded for API use.
        """
        topology = slice.get_fim_topology()

        rtn_network_services = []
        fim_network_service = None
        logging.debug(f"NetworkService.get_fim_l3network_service_types(): {NetworkService.get_fim_l3network_service_types()}")

        for net_name, net in topology.network_services.items():
            logging.debug(f"scanning network: {net_name}, net: {net}")
            if str(net.get_property('type')) in NetworkService.get_fim_l3network_service_types():
                logging.debug(f"returning network: {net_name}, net: {net}")
                rtn_network_services.append(NetworkService(slice = slice, fim_network_service = net))

        return rtn_network_services

    @staticmethod
    def get_l3network_service(slice: Slice = None, name: str = None):
        """
        Not inteded for API use.
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
        fim_network_service = None
        for net_name, net in topology.network_services.items():
            if str(net.get_property('type')) in NetworkService.get_fim_l2network_service_types():
                rtn_network_services.append(NetworkService(slice=slice, fim_network_service=net))

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
    def get_network_services(slice: Slice = None) -> list:
        """
        Not inteded for API use.
        """

        topology = slice.get_fim_topology()

        rtn_network_services = []
        fim_network_service = None
        for net_name, net in topology.network_services.items():
            if str(net.get_property('type')) in NetworkService.get_fim_network_service_types():
                rtn_network_services.append(NetworkService(slice=slice, fim_network_service = net))

        return rtn_network_services

    @staticmethod
    def get_network_service(slice: Slice = None, name: str = None):
        """
        Not inteded for API use.
        """
        for net in NetworkService.get_network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.slice_name}, network {name}")

    def __init__(self, slice: Slice = None, fim_network_service: FimNetworkService =None):
        """
        Not inteded for API use.

        Constructor. Sets the fablib slice and the FABRIC network service.

        :param slice: the fablib slice to set as instance state
        :type slice: Slice
        :param fim_network_service: the FIM network service to set as instance state
        :type fim_network_service: FIMNetworkService
        """
        super().__init__()
        self.fim_network_service = fim_network_service
        self.slice = slice

        try:
            self.sliver = slice.get_sliver(reservation_id=self.get_reservation_id())
        except:
            self.sliver = None

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the network service.

        Intended for printing network service information.

        :return: Tabulated string of network service information
        :rtype: String
        """
        table = [ ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Layer", self.get_layer()],
            ["Type", self.get_type()],
            ["Site", self.get_site()],
            ["Gateway", self.get_gateway()],
            ["L3 Subnet", self.get_subnet()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ]

        return tabulate(table) #, headers=["Property", "Value"])

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice this network service is built on.

        :return: the slice this network is on
        :rtype: Slice
        """
        return self.slice

    def get_site(self) -> str or None:
        try:
            return self.get_sliver().sliver.site
        except Exception as e:
            logging.warning(f"Failed to get site: {e}")

            return None

    def get_layer(self) -> str or None:
        """
        Gets the layer of the network services (L2 or L3)

        :return: L2 or L3
        :rtype: String
        """
        try:
            return self.get_sliver().sliver.layer
        except Exception as e:
            logging.warning(f"Failed to get layer: {e}")
            return None

    def get_type(self):
        """
        Gets the type of the network services

        :return: network service types
        :rtype: String
        """
        try:
            return self.get_sliver().sliver.resource_type
        except Exception as e:
            logging.warning(f"Failed to get type: {e}")
            return None

    def get_sliver(self) -> OrchestratorSliver:
        return self.sliver

    def get_fim_network_service(self) -> FimNetworkService:
        """
        Not intended for API use

        Gets the FABRIC network service this instance represents.

        :return: the FIM network service
        :rtype: FIMNetworkService
        """
        return self.fim_network_service

    def get_error_message(self) -> str:
        """
        Gets the error messages

        :return: network service types
        :rtype: String
        """
        try:
            return self.get_fim_network_service().get_property(pname='reservation_info').error_message
        except:
            return ""

    def get_gateway(self) -> IPv4Address or IPv6Address or None:
        """
        Gets the assigend gateway for a FABnetv L3 IPv6 or IPv4 network

        :return: gateway IP
        :rtype: IPv4Address or IPv6Network
        """
        try:
            gateway = None
            if self.get_layer() == NSLayer.L3:
                if self.get_type() == ServiceType.FABNetv6:
                    gateway = IPv6Address(self.get_sliver().sliver.gateway.gateway)
                elif self.get_type() == ServiceType.FABNetv4:
                    gateway = IPv4Address(self.get_sliver().sliver.gateway.gateway)

            return gateway
        except Exception as e:
            logging.warning(f"Failed to get gateway: {e}")
            return None

    def get_available_ips(self, count: int = 256) -> List[IPv4Address or IPv6Address] or None:
        """
        Gets the IPs available for a FABnet L3 network.

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
                logging.debug(f"adding IP {i}")
                ip_list.append(gateway+i+1)
            return ip_list
        except Exception as e:
            logging.warning(f"Failed to get_available_ips: {e}")
            return None

    def get_subnet(self) -> IPv4Network or IPv6Network or None:
        """
        Gets the assigend subnet for a FABnetv L3 IPv6 or IPv4 network

        :return: gateway IP
        :rtype: IPv4Network or IPv6Network
        """
        try:
            subnet = None
            if self.get_layer() == NSLayer.L3:
                if self.get_type() == ServiceType.FABNetv6:
                    subnet = IPv6Network(self.get_sliver().sliver.gateway.subnet)
                elif self.get_type() == ServiceType.FABNetv4:
                    subnet = IPv4Network(self.get_sliver().sliver.gateway.subnet)
            return subnet
        except Exception as e:
            logging.warning(f"Failed to get subnet: {e}")
            return None

    def get_reservation_id(self) -> str or None:
        """
        Gets the reservation id of the network

        :return: reservation ID
        :rtype: String
        """
        try:
            return self.get_fim_network_service().get_property(pname='reservation_info').reservation_id
        except Exception as e:
            logging.warning(f"Failed to get reservation_id: {e}")
            return None

    def get_reservation_state(self) -> str or None:
        """
        Gets the reservation state of the network

        :return: reservation state
        :rtype: String
        """
        try:
            return self.get_fim_network_service().get_property(pname='reservation_info').reservation_state
        except Exception as e:
            logging.warning(f"Failed to get reservation_state: {e}")
            return None

    def get_name(self) -> str:
        """
        Gets the name of this network service.

        :return: the name of this network service
        :rtype: String
        """
        return self.get_fim_network_service().name

    def get_interfaces(self) -> List[Interface]:
        """
        Gets the interfaces on this network service.

        :return: the interfaces on this network service
        :rtype: List[Interfaces]
        """
        interfaces = []
        for interface in self.get_fim_network_service().interface_list:
            interfaces.append(self.get_slice().get_interface(name=interface.name))

        return interfaces

    def get_interface(self, name: str = None) -> Interface or None:
        """
        Gets a particular interface on this network service.

        :param name: the name of the interface to search for
        :type name: str
        :return: the particular interface
        :rtype: Interface
        """
        for interface in self.get_fim_network_service().interface_list:
            if name in interface.name:
                return self.get_slice().get_interface(name=interface.name)

        return None

    def has_interface(self, interface: Interface) -> bool:
        """
        Determines whether this network service has a particular interface.

        :param interface: the fablib interface to search for
        :type interface: Interface
        :return: whether this network service has interface
        :rtype: bool
        """
        for fim_interface in self.get_fim_network_service().interface_list:
            #print(f"fim_interface.name: {fim_interface.name}, interface.get_name(): {interface.get_name()}")
            if fim_interface.name.endswith(interface.get_name()):
                return True

        return False
