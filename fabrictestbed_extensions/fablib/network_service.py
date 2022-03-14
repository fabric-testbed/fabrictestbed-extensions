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

import os
import traceback
import re

import functools
import time
import logging
from tabulate import tabulate



import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fim.slivers.network_service import NetworkServiceSliver, ServiceType, NSLayer

from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

#from .abc_fablib import AbcFabLIB

from .. import images


#class NetworkService(AbcFabLIB):
class NetworkService():
    network_service_map = { 'L2Bridge': ServiceType.L2Bridge,
                            'L2PTP': ServiceType.L2PTP,
                            'L2STS': ServiceType.L2STS,
                            }

    #Type names used in fim network services
    fim_l2network_service_types = [ 'L2Bridge', 'L2PTP', 'L2STS']
    fim_l3network_service_types = [ 'FABNetv4', 'FABNetv6']

    #fim_network_service_types = [ 'L2Bridge', 'L2PTP', 'L2STS']



    @staticmethod
    def get_fim_l2network_service_types():
        return NetworkService.fim_l2network_service_types

    @staticmethod
    def get_fim_l3network_service_types():
        return NetworkService.fim_l3network_service_types

    @staticmethod
    def get_fim_network_service_types():
        return NetworkService.get_fim_l2network_service_types() + NetworkService.get_fim_l3network_service_types()


    @staticmethod
    def calculate_l2_nstype(interfaces=None):
        #if there is a basic NIC, WAN must be STS
        basic_nic_count = 0

        sites = set([])
        for interface in interfaces:
            sites.add(interface.get_site())
            if interface.get_model()=="NIC_Basic":
                basic_nic_count += 1

        rtn_nstype = None
        if len(sites) == 1:
            rtn_nstype = NetworkService.network_service_map['L2Bridge']
        elif basic_nic_count == 0 and len(sites) == 2 and len(interfaces) == 2:
            #TODO: remove this when STS works on all links.
            rtn_nstype = NetworkService.network_service_map['L2PTP']
        elif len(sites) == 2  and basic_nic_count == 2 and len(interfaces) == 2:
            rtn_nstype = NetworkService.network_service_map['L2STS']
        else:
            raise Exception(f"Invalid Network Service: Networks are limited to 2 unique sites. Site requested: {sites}")

        return rtn_nstype

    @staticmethod
    def validate_nstype(type, interfaces):

        sites = set([])
        nics = set([])
        for interface in interfaces:
            sites.add(interface.get_site())
            nics.add(interface.get_model())

        #models: 'NIC_Basic', 'NIC_ConnectX_6', 'NIC_ConnectX_5'
        if type == NetworkService.network_service_map['L2Bridge']:
            if not len(sites) == 1:
                raise Exception(f"Network type {type} must include interfaces from exactly one site. {len(sites)} sites requested: {sites}")

        elif type == NetworkService.network_service_map['L2PTP']:
            if not len(sites) == 2:
                raise Exception(f"Network type {type} must include interfaces from exactly two sites. {len(sites)} sites requested: {sites}")
            if 'NIC_Basic' in nics:
                raise Exception(f"Network type {type} does not support interfaces of type 'NIC_Basic'")

        elif type == NetworkService.network_service_map['L2STS']:
            if not len(sites) == 2:
                raise Exception(f"Network type {type} must include interfaces from exactly two sites. {len(sites)} sites requested: {sites}")
        else:
            raise Exception(f"Invalid l2 network type: {type}. Please choose from {NetworkService.get_fim_l2network_service_types()} or None for automatic selection")

        return True

    @staticmethod
    def new_l3network(slice=None, name=None, interfaces=[], type=None):
        if type == "IPv6":
            nstype = ServiceType.FABNetv6
        else:
            nstype = ServiceType.FABNetv4

        # TODO: need a fabnet version of this
        # validate nstype and interface List
        #NetworkService.validate_nstype(nstype, interfaces)

        return NetworkService.new_network_service(slice=slice, name=name, nstype=nstype, interfaces=interfaces)

    @staticmethod
    def new_l2network(slice=None, name=None, interfaces=[], type=None):
        if type == None:
            nstype=NetworkService.calculate_l2_nstype(interfaces=interfaces)
        else:
            if type in NetworkService.get_fim_l2network_service_types():
                nstype=NetworkService.network_service_map[type]
            else:
                raise Exception(f"Invalid l2 network type: {type}. Please choose from {NetworkService.get_fim_l2network_service_types()} or None for automatic selection")

        #validate nstype and interface List
        NetworkService.validate_nstype(nstype, interfaces)

        #Set default VLANs for P2P networks that did not assing VLANs
        if nstype == ServiceType.L2PTP: # or nstype == ServiceType.L2STS:
            for interface in interfaces:
                if interface.get_model() != 'NIC_Basic' and not interface.get_vlan():
                    #TODO: Long term we might have muliple vlan on one property
                    # and will need to make sure they are unique.  For now this okay
                    interface.set_vlan("100")

        return NetworkService.new_network_service(slice=slice, name=name, nstype=nstype, interfaces=interfaces)

    @staticmethod
    def new_network_service(slice=None, name=None, nstype=None, interfaces=[]):
        fim_interfaces = []
        for interface in interfaces:
            fim_interfaces.append(interface.get_fim_interface())

        logging.info(f"Create Network Service: Slice: {slice.get_name()}, Network Name: {name}, Type: {nstype}")
        fim_network_service = slice.topology.add_network_service(name=name,
                                                                 nstype=nstype,
                                                                 interfaces=fim_interfaces)

        return NetworkService(slice = slice, fim_network_service = fim_network_service)

    @staticmethod
    def get_l3network_services(slice=None):
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
    def get_l3network_service(slice=None, name=None):

        for net in NetworkService.get_l3network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.name}, network {name}")


    @staticmethod
    def get_l2network_services(slice=None):
        topology = slice.get_fim_topology()

        rtn_network_services = []
        fim_network_service = None
        for net_name, net in topology.network_services.items():
            if str(net.get_property('type')) in NetworkService.get_fim_l2network_service_types():
                rtn_network_services.append(NetworkService(slice = slice, fim_network_service = net))

        return rtn_network_services

    @staticmethod
    def get_l2network_service(slice=None, name=None):

        for net in NetworkService.get_l2network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.name}, network {name}")


    @staticmethod
    def get_network_services(slice=None):
        topology = slice.get_fim_topology()

        rtn_network_services = []
        fim_network_service = None
        for net_name, net in topology.network_services.items():
            if str(net.get_property('type')) in NetworkService.get_fim_network_service_types():
                rtn_network_services.append(NetworkService(slice = slice, fim_network_service = net))

        return rtn_network_services

    @staticmethod
    def get_network_service(slice=None, name=None):

        for net in NetworkService.get_network_services(slice=slice):
            if net.get_name() == name:
                return net

        raise Exception(f"Network not found. Slice {slice.name}, network {name}")


    def __init__(self, slice=None, fim_network_service=None):
        """
        Constructor
        :return:
        """
        super().__init__()
        self.fim_network_service  = fim_network_service
        self.slice = slice

        try:
            self.sliver = slice.get_sliver(reservation_id=self.get_reservation_id())
        except:
            self.sliver = None


    def __str__(self):
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


    def get_slice(self):
        return self.slice

    def get_site(self):
        try:
            return self.get_sliver().sliver.site
        except Exception as e:
            logging.warning(f"Failed to get site: {e}")
            return None

    def get_layer(self):
        try:
            return self.get_sliver().sliver.layer
        except Exception as e:
            logging.warning(f"Failed to get layer: {e}")
            return None

    def get_type(self):
        try:
            return self.get_sliver().sliver.resource_type
        except Exception as e:
            logging.warning(f"Failed to get type: {e}")
            return None

    def get_sliver(self):
        return self.sliver

    def get_fim_network_service(self):
        return self.fim_network_service

    def get_error_message(self):
        try:
            return self.get_fim_network_service().get_property(pname='reservation_info').error_message
        except:
            return ""

    def get_gateway(self):
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

    def get_available_ips(self, count=100):
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

    def get_subnet(self):
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

    def get_reservation_id(self):
        try:
            return self.get_fim_network_service().get_property(pname='reservation_info').reservation_id
        except:
            logging.warning(f"Failed to get reservation_id: {e}")
            return None

    def get_reservation_state(self):
        try:
            return self.get_fim_network_service().get_property(pname='reservation_info').reservation_state
        except:
            logging.warning(f"Failed to get reservation_state: {e}")
            return None

    def get_name(self):
        return self.get_fim_network_service().name

    def get_interfaces(self):
        interfaces = []
        for interface in self.get_fim_network_service().interface_list:
            interfaces.append(self.get_slice().get_interface(name=interface.name))

        return interfaces

    def get_interface(self, name=None):
        for interface in self.get_fim_network_service().interface_list:
            if name in interface.name:
                return self.get_slice().get_interface(name=interface.name)

        return None

    def has_interface(self, interface):
        for fim_interface in self.get_fim_network_service().interface_list:
            #print(f"fim_interface.name: {fim_interface.name}, interface.get_name(): {interface.get_name()}")
            if fim_interface.name.endswith(interface.get_name()):
                return True

        return False
