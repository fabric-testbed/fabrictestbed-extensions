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

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

from ipaddress import ip_address, IPv4Address

#from .abc_fablib import AbcFabLIB

from .. import images


#class NetworkService(AbcFabLIB):
class NetworkService():
    network_service_map = { 'L2Bridge': ServiceType.L2Bridge,
                            'L2PTP': ServiceType.L2PTP,
                            'L2STS': ServiceType.L2STS,
                            }

    #Type names used in fim network services
    fim_network_service_types = [ 'L2Bridge', 'L2PTP', 'L2STS']


    @staticmethod
    def calculate_l2_nstype(interfaces=None):

        sites = set([])
        for interface in interfaces:
            sites.add(interface.get_site())

        rtn_nstype = None
        if len(sites) == 1:
            rtn_nstype = NetworkService.network_service_map['L2Bridge']
        elif len(sites) == 2 and len(interfaces) == 2:
            rtn_nstype = NetworkService.network_service_map['L2PTP']
        elif len(sites) == 2  and len(interfaces) > 2:
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
            raise Exception(f"Invalid l2 network type: {type}. Please choose from {NetworkService.fim_network_service_types} or None for automatic selection")

        return True


    @staticmethod
    def new_l2network(slice=None, name=None, interfaces=[], type=None):
        if type == None:
            nstype=NetworkService.calculate_l2_nstype(interfaces=interfaces)
        else:
            if type in NetworkService.fim_network_service_types:
                nstype=NetworkService.network_service_map[type]
            else:
                raise Exception(f"Invalid l2 network type: {type}. Please choose from {NetworkService.fim_network_service_types} or None for automatic selection")

        #validate nstype and interface List
        NetworkService.validate_nstype(nstype, interfaces)

        return NetworkService.new_network_service(slice=slice, name=name, nstype=nstype, interfaces=interfaces)

    @staticmethod
    def new_network_service(slice=None, name=None, nstype=None, interfaces=[]):
        fim_interfaces = []
        for interface in interfaces:
            fim_interfaces.append(interface.get_fim_interface())

        fim_network_service = slice.topology.add_network_service(name=name,
                                                                 nstype=nstype,
                                                                 interfaces=fim_interfaces)

        return NetworkService(slice = slice, fim_network_service = fim_network_service)

    @staticmethod
    def get_l2network_services(slice=None):
        topology = slice.get_fim_topology()

        rtn_network_services = []
        fim_network_service = None
        for net_name, net in topology.network_services.items():
            if str(net.get_property('type')) in NetworkService.fim_network_service_types:
                rtn_network_services.append(NetworkService(slice = slice, fim_network_service = net))

        return rtn_network_services

    @staticmethod
    def get_l2network_service(slice=None, name=None):

        for net in NetworkService.get_l2network_services(slice=slice):
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

    def get_slice(self):
        return self.slice

    def get_fim_network_service(self):
        return self.fim_network_service

    def get_name(self):
        return self.get_fim_network_service().name

    def get_interfaces(self):
        interfaces = []
        for interface in self.get_fim_network_service().interface_list:
            interfaces.append(self.get_slice().get_interface(name=interface.name))

        return interfaces

    def get_interface(self, name=None):
        #print(f"network_service.get_interface: name {name}")
        for interface in self.get_interfaces():
            #print(f"network_service.get_interface: self.get_name() {self.get_name()}, interface.get_name(): {interface.get_name()}")

            #interface_name = f"{self.get_name()}-{interface.get_name()}"
            interface_name = f"{interface.get_name()}"
            #print(f"network_service.get_interface: interface_name {interface_name}, name: {name}")

            if interface_name == name:
                #print(f"returning iface: {interface.get_name()}")
                return interface

        return None
        #raise Exception(f"Interface not found: interface {name}")

    def has_interface(self, interface):

        if self.get_interface(name=interface.get_name()) == None:
            return False
        else:
            return True

    def find_nic_mapping(self, net_name, nodes):
        return_data = {}

        #copy scripts to nodes
        for node in nodes:
            #config node1
            file_attributes = upload_file(username, node, 'scripts/host_set_all_dataplane_ips.py','host_set_all_dataplane_ips.py')
            #print("file_attributes: {}".format(file_attributes))
            file_attributes = upload_file(username, node, 'scripts/find_nic_mapping.py','find_nic_mapping.py')
            #print("file_attributes: {}".format(file_attributes))


        #Config target node
        target_node = nodes[0]
        stdout = execute_script(username, target_node, 'sudo python3 host_set_all_dataplane_ips.py')
        #print("stdout: {}".format(stdout))
        #print(stdout)

        target_ifaces = json.loads(stdout.replace('\n',''))
        #print(ifaces)
        #for i in ifaces['management']:
        #    print(i)

        #for i in ifaces['dataplane']:
        #    print(i)
        #node1_map = { 'data' : {'ens6': '192.168.1.100', etc... }, 'management': { 'ens3': '10.1.1.1'}  }


        # Test s1 ifaces
        target_net_ip = None
        for node in nodes:
            #skip target node
            if node == target_node:
                continue

            #test node interfaces against target
            for target, ip in target_ifaces['dataplane']:
                node1_dataplane_ip = ip
                node2_dataplane_ip = ip.replace('100','101')
                node2_cidr = '24'
                #node2_management_ip = str(node2.management_ip)
                #print("S1 Name        : {}".format(node2.name))
                #print("Management IP    : {}".format(node2_management_ip))

                stdout = execute_script(username, node, 'python3 find_nic_mapping.py {} {} {} {}'.format('net',node2_dataplane_ip,node2_cidr,node1_dataplane_ip) )
                iface =  stdout.replace('\n','')
                #print("stdout: {}".format(stdout))
                if iface != 'None':
                    #print(iface)
                    #return iface
                    if target_net_ip == None:
                        return_data[target_node.name]=target
                    return_data[node.name]=iface
                    break



        return return_data

    def flush_dataplane_ips(nodes):

        for node in nodes:
            #config node1
            file_attributes = upload_file(username, node, 'scripts/host_flush_all_dataplane_ips.py','host_flush_all_dataplane_ips.py')
            #print("file_attributes: {}".format(file_attributes))

            stdout = execute_script(username, node, 'sudo python3 host_flush_all_dataplane_ips.py')
            #print("stdout: {}".format(stdout))
            #print(stdout)


    def flush_all_dataplane_ips():
        for node_name, node in experiment_topology.nodes.items():
            flush_dataplane_ips([node])
