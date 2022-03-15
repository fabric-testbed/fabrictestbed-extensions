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

from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState


#from .slicex import SliceX
#from .nodex import NodeX
#from .fabricx import FabricX

#from .abc_fablib import AbcFabLIB

from .. import images

from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.node import Node


class Slice():

    def __init__(self, name=None):
        """
        Constructor
        :return:
        """
        super().__init__()

        #print(f"Creating Slice: Name: {name}, Slice: {slice}")
        self.slice_name = name
        self.sm_slice = None
        self.slice_id = None
        self.topology = None

        self.slice_key = fablib.get_default_slice_key()

    def __str__(self):

        table = [   [ "Slice Name", self.sm_slice.slice_name ],
                    [ "Slice ID", self.sm_slice.slice_id ],
                    [ "Slice State", self.sm_slice.slice_state ],
                    [ "Lease End", self.sm_slice.lease_end ],
                    ]

        return tabulate(table)


    def list_nodes(self):

        table = []
        for node in self.get_nodes():

            table.append( [     node.get_name(),
                                node.get_cores(),
                                node.get_ram(),
                                node.get_disk(),
                                node.get_image(),
                                node.get_host(),
                                node.get_site(),
                                node.get_management_ip(),
                                node.get_reservation_id(),
                                node.get_reservation_state(),
                                node.get_error_message(),
                                ] )

        return tabulate(table, headers=["Name", "Cores", "RAM", "Disk", "Image", "Host", "Site", "Management IP", "ID", "State", "Error" ])

    def list_interfaces(self):
        table = []
        for iface in self.get_interfaces():

            if iface.get_network():
                network_name = iface.get_network().get_name()
            else:
                network_name = None

            if iface.get_node():
                node_name = iface.get_node().get_name()
            else:
                node_name = None

            table.append( [     iface.get_name(),
                                node_name,
                                network_name,
                                iface.get_bandwidth(),
                                iface.get_vlan(),
                                iface.get_mac(),
                                iface.get_physical_os_interface_name(),
                                iface.get_os_interface(),
                                ] )

        return tabulate(table, headers=["Name", "Node", "Network", "Bandwidth", "VLAN", "MAC", "Physical OS Interface", "OS Interface" ])



    @staticmethod
    def new_slice(name=None):
        """
        Create a new slice
        @param name slice name
        @return fablib Slice object
        """

        slice = Slice(name=name)
        slice.topology = ExperimentTopology()
        return slice

    @staticmethod
    def get_slice(sm_slice=None, load_config=True):
        """
        Create a new slice
        @param name slice name
        @return fablib Slice object
        """
        logging.info("slice.get_slice()")

        slice = Slice(name=sm_slice.slice_name)
        slice.sm_slice = sm_slice
        slice.slice_id = sm_slice.slice_id
        slice.slice_name = sm_slice.slice_name

        slice.topology = fablib.get_slice_manager().get_slice_topology(slice_object=slice.sm_slice)

        try:
            slice.update()
        except:
            logging.error(f"Slice {slice.slice_name} could not be updated: slice.get_slice")

        if load_config:
            try:
                slice.load_config()
            except:
                logging.error(f"Slice {slice.slice_name} config could not loaded: slice.get_slice")

        return slice

    def get_fim_topology(self):
        return self.topology

    def update_slice(self):
        #Update slice
        #return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])
        #return_status, slices = fablib.get_slice_manager().slices(excludes=[])

        import time
        if fablib.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = fablib.get_slice_manager().slices(excludes=[])
        if fablib.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(f"Running slice.update_slice() : fablib.get_slice_manager().slices(): elapsed time: {end - start} seconds")

        if return_status == Status.OK:
            self.sm_slice = list(filter(lambda x: x.slice_id == self.slice_id, slices))[0]
            #self.slice_name = self.sm_slice.slice_name
        else:
            raise Exception("Failed to get slice list: {}, {}".format(return_status, slices))

    def update_topology(self):
        #Update topology
        return_status, new_topo = fablib.get_slice_manager().get_slice_topology(slice_object=self.sm_slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slice topology: {}, {}".format(return_status, new_topo))

        #Set slice attibutes
        self.topology = new_topo

    def update_slivers(self):
        status, slivers = fablib.get_slice_manager().slivers(slice_object=self.sm_slice)
        if status == Status.OK:
            self.slivers = slivers
            return

        raise Exception(f"{slivers}")

    def get_sliver(self, reservation_id):
        #for sliver in self.get_slivers():
        #    if sliver.reservation_id == reservation_id:
        #        return sliver

        slivers = self.get_slivers()
        sliver = list(filter(lambda x: x.reservation_id == reservation_id, slivers ))[0]

        return sliver


    def get_slivers(self):

        if not hasattr(self, 'slivers') or not self.slivers:
            self.update_slivers()

        return self.slivers



    def update(self):
        try:
            self.update_slice()
        except Exception as e:
            logging.warning(f"slice.update_slice failed: {e}")

        try:
            self.update_slivers()
        except Exception as e:
            logging.warning(f"slice.update_slivers failed: {e}")


        self.update_topology()

    def get_slice_public_key(self):
        return self.slice_key['slice_public_key']

    def get_private_key_passphrase(self):
        if 'slice_private_key_passphrase' in self.slice_key.keys():
            return self.slice_key['slice_private_key_passphrase']
        else:
            return None

    def get_slice_public_key(self):
        if 'slice_public_key' in self.slice_key.keys():
            return self.slice_key['slice_public_key']
        else:
            return None

    def get_slice_public_key_file(self):
        if 'slice_public_key_file' in self.slice_key.keys():
            return self.slice_key['slice_public_key_file']
        else:
            return None

    def get_slice_private_key_file(self):
        if 'slice_private_key_file' in self.slice_key.keys():
            return self.slice_key['slice_private_key_file']
        else:
            return None

    def get_state(self):
        return self.sm_slice.slice_state

    def get_name(self):
        return self.slice_name

    def get_slice_id(self):
        return self.slice_id

    def get_lease_end(self):
        return self.sm_slice.lease_end

    def add_l2network(self, name=None, interfaces=[], type=None):
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        return NetworkService.new_l2network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_l3network(self, name=None, interfaces=[], type='IPv6'):
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        return NetworkService.new_l3network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_node(self, name, site=None, cores=None, ram=None, disk=None, image=None, host=None, avoid=[]):
        from fabrictestbed_extensions.fablib.node import Node
        node = Node.new_node(slice=self, name=name, site=site, avoid=avoid)

        if cores or ram or disk:
            node.set_capacities(cores=cores, ram=ram, disk=disk)

        if image:
            node.set_image(image)

        if host:
            node.set_host(host)


        return node

    def get_object_by_reservation(self, reservation_id):
        # test all nodes
        try:
            for node in self.get_nodes():
                if node.get_reservation_id() == reservation_id:
                    return node

            for network in self.get_network_services():
                if network.get_reservation_id() == reservation_id:
                    return network

            for iface in self.get_interfaces():
                if iface.get_reservation_id() == reservation_id:
                    return iface

                    # TODO: test other resource types.
        except:
            pass

        return None


    def get_error_messages(self):

        # strings to ingnor
        cascade_notice_string1 = 'Closing reservation due to failure in slice'
        cascade_notice_string2 = 'is in a terminal state'

        origin_notices = []
        for reservation_id,notice in self.get_notices().items():
            #print(f"XXXXX: reservation_id: {reservation_id}, notice {notice}")
            if cascade_notice_string1 in notice or cascade_notice_string2 in notice:
                continue

            origin_notices.append({'reservation_id': reservation_id, 'notice': notice, 'sliver': self.get_object_by_reservation(reservation_id)})

        return origin_notices



    def get_notices(self):

        notices = {}
        for node in self.get_nodes():
            notices[node.get_reservation_id()] = node.get_error_message()

        for network_service in self.get_network_services():
            notices[network_service.get_reservation_id()] = network_service.get_error_message()

        for component in self.get_components():
            notices[component.get_reservation_id()] = component.get_error_message()

        return notices

    def get_components(self):
        from fabrictestbed_extensions.fablib.component import Component
        #self.update()

        return_components = []

        #fails for topology that does not have nodes
        try:
            for node in self.get_nodes():
                for component in node.get_components():
                    return_components.append(component)

        except Exception as e:
            print("get_components: exception")
            #traceback.print_exc()
            pass
        return return_components


    def get_network_services(self):
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        #self.update()

        return_networks = []

        #fails for topology that does not have nodes
        try:
            for net_name, net in self.get_fim_topology().network_services.items():
                if str(net.get_property('type')) in NetworkService.fim_network_service_types:
                    return_networks.append(NetworkService(slice = self, fim_network_service = net))

        except Exception as e:
            print("get_network_services: exception")
            #traceback.print_exc()
            pass
        return return_networks

    def get_nodes(self):
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()

        return_nodes = []

        #fails for topology that does not have nodes
        try:
            for node_name, node in self.get_fim_topology().nodes.items():
                return_nodes.append(Node.get_node(self,node))
        except Exception as e:
            print("get_nodes: exception")
            #traceback.print_exc()
            pass
        return return_nodes

    def get_node(self, name):
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()
        try:
            return Node.get_node(self,self.get_fim_topology().nodes[name])
        except Exception as e:
            logging.info(e, exc_info=True)
            raise Exception(f"Node not found: {name}")

    def get_interfaces(self):
        interfaces = []
        for node in self.get_nodes():
            for interface in node.get_interfaces():
                interfaces.append(interface)
        return interfaces

    def get_interface(self, name=None):
        for interface in self.get_interfaces():
            if name.endswith(interface.get_name()):
                return interface

        raise Exception("Interface not found: {}".format(name))

    def get_l3networks(self):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l3network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_l3network(self, name=None):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l3network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def get_l2networks(self):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_l2network(self, name=None):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def get_networks(self):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_network(self, name=None):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def delete(self):
        return_status, result = fablib.get_slice_manager().delete(slice_object=self.sm_slice)

        if return_status != Status.OK:
            raise Exception("Failed to delete slice: {}, {}".format(return_status, result))

        self.topology = None

    def renew(self, end_date):

        return_status, result = fablib.get_slice_manager().renew(slice_object=self.sm_slice,
                                     new_lease_end_time = end_date)

        if return_status != Status.OK:
            raise Exception("Failed to renew slice: {}, {}".format(return_status, result))


    def build_error_exception_string(self):

        self.update()

        exception_string =  f"Slice Exception: Slice Name: {self.get_name()}, Slice ID: {self.get_slice_id()}: "
        for error in self.get_error_messages():
            notice = error['notice']
            sliver = error['sliver']

            sliver_extra = ""
            if isinstance(sliver, Node):
                sliver_extra = f"Node: {sliver.get_name()}, Site: {sliver.get_site()}, State: {sliver.get_reservation_state()}, "

            #skip errors that are caused by slice error
            if 'Closing reservation due to failure in slice' in notice:
                continue

            exception_string = f"{exception_string}{sliver_extra}{notice}\n"

        return exception_string

    def wait(self, timeout=360,interval=10,progress=False):
        slice_name=self.sm_slice.slice_name
        slice_id=self.sm_slice.slice_id

        timeout_start = time.time()
        slice = self.sm_slice

        if progress: print("Waiting for slice .", end = '')
        while time.time() < timeout_start + timeout:
            #return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])
            return_status, slices = fablib.get_slice_manager().slices(excludes=[])
            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
                if slice.slice_state == "StableOK":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if slice.slice_state == "Closing" or slice.slice_state == "Dead" or slice.slice_state == "StableError":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    try:
                        exception_string = self.build_error_exception_string()
                    except Exception as e:
                        exception_string = "Exception while getting error messages"
                        #traceback.print_exc()

                    raise Exception(str(exception_string))
            else:
                print(f"Failure: {slices}")

            if progress: print(".", end = '')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            #if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
            raise Exception(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
            return slice

        #Update the fim topology (wait to avoid get topology bug)
        #time.sleep(interval)
        self.update()

    def get_interface_map(self):
        if not hasattr(self, 'network_iface_map'):
            self.load_interface_map()

        return self.network_iface_map

    def wait_ssh(self, timeout=360,interval=10,progress=False):
        slice_name=self.sm_slice.slice_name
        slice_id=self.sm_slice.slice_id

        timeout_start = time.time()
        slice = self.sm_slice

        #Wait for the slice to be stable ok
        self.wait(timeout=timeout,interval=interval,progress=progress)

        #Test ssh
        if progress: print("Waiting for ssh in slice .", end = '')
        while time.time() < timeout_start + timeout:
            if self.test_ssh():
                if progress: print(" ssh successful")
                return True

            if progress: print(".", end = '')

            if time.time() >= timeout_start + timeout:
                if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
                raise Exception(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))

            time.sleep(interval)
            self.update()


    def test_ssh(self,):
        for node in self.get_nodes():
            if not node.test_ssh():
                logging.debug(f"test_ssh fail: {node.get_name()}: {node.get_management_ip()}")
                return False
        return True

    def post_boot_config(self):

        logging.info(f"post_boot_config: slice_name: {self.get_name()}, slice_id {self.get_slice_id()}")
        # Find the interface to network map
        logging.info(f"build_interface_map: slice_name: {self.get_name()}, slice_id {self.get_slice_id()}")
        self.build_interface_map()

        # Interface map in nodes

        for node in self.get_nodes():
            if fablib.get_log_level() == logging.DEBUG:
                try:
                    logging.debug(f"Node data {node.get_name()}: interface_map: {node.get_interface_map()}")
                except Exception as e:
                    logging.error(e, exc_info=True)

            node.save_data()

        for interface in self.get_interfaces():
            try:
                interface.config_vlan_iface()
            except Exception as e:
                logging.error(f"Interface: {interface.get_name()} failed to config")
                logging.error(e, exc_info=True)

    def load_config(self):
        self.load_interface_map()

    def load_interface_map(self):
        self.network_iface_map = {}
        for net in self.get_networks():
            self.network_iface_map[net.get_name()] = {}

        for node in self.get_nodes():
            node.load_data()

    def validIPAddress(self, IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def build_interface_map(self):
        self.network_iface_map = {}

        for net in self.get_l3networks():
            logging.debug(f"net: {net}")
            #gateway = IPv4Address(net.get_gateway())
            #test_ip = gateway + 1
            #subnet = IPv4Network(net.get_subnet())
            if self.validIPAddress(net.get_gateway()) == 'IPv4':
                gateway = IPv4Address(net.get_gateway())
                subnet = IPv4Network(net.get_subnet())
            elif self.validIPAddress(net.get_gateway()) == 'IPv6':
                gateway = IPv6Address(net.get_gateway())
                subnet = IPv6Network(net.get_subnet())
            else:
                raise Exception(f"FABNetv4: Gateway IP Invalid: {net.get_gateway()}")

            test_ip = gateway + 1
            #ip_base,cidr = net.get_subnet().split('/')
            #logging.debug(f"L3 gateway: {gateway}")
            #logging.debug(f"L3 test_ip: {test_ip}")

            logging.debug(f"L3 subnet: {subnet}")
            logging.debug(f"L3 gateway: {gateway}")
            logging.debug(f"L3 test_ip: {test_ip}")

            iface_map = {}

            logging.info(f"Buiding iface map for l3 network: {net.get_name()}")
            for iface in net.get_interfaces():
                logging.debug(f"iface: {iface.get_name()}")
                node = iface.get_node()
                #node.clear_all_ifaces()
                node_os_ifaces = node.get_dataplane_os_interfaces()

                logging.debug(f"Test_node: {node.get_name()}: {node.get_ssh_command()}")
                logging.debug(f"Test_tface: {iface.get_name()}")
                logging.debug(f"node_os_ifaces: {node_os_ifaces}")
                logging.debug(f"iface.get_vlan(): {iface.get_vlan()}")

                found = False
                for node_os_iface in node_os_ifaces:
                    node_os_iface_name = node_os_iface['ifname']

                    #set interface
                    node.set_ip_os_interface(os_iface=node_os_iface_name,
                                             vlan=iface.get_vlan(),
                                             ip=test_ip,
                                             cidr=subnet.prefixlen)

                    #ping test
                    #logging.debug(f"Node: {node.get_name()}: {node_os_iface_name}, {iface.get_vlan()}, {test_ip}")

                    logging.debug(f"ping test {node.get_name()}:{node_os_iface_name} ->  - {test_ip} to {gateway}")
                    test_result = node.ping_test(gateway)
                    logging.debug(f"Ping test result: {node.get_name()}:{node_os_iface_name} ->  - {test_ip} to {gateway}: {test_result}")

                    if iface.get_vlan() == None:
                        node.flush_os_interface(node_os_iface_name)
                    else:
                        node.remove_vlan_os_interface(os_iface=f"{node_os_iface_name}.{iface.get_vlan()}")

                    if test_result:
                        logging.debug(f"test_result true: {test_result}")
                        found = True
                        iface_map[node.get_name()] = node_os_iface
                        break

                if found:
                    break


            self.network_iface_map[net.get_name()] = iface_map

        for net in self.get_l2networks():
            iface_map = {}

            logging.info(f"Buiding iface map for l2 network: {net.get_name()}")
            ifaces = net.get_interfaces()

            #target iface/node
            target_iface =  ifaces.pop()

            target_node = target_iface.get_node()
            target_os_ifaces = target_node.get_dataplane_os_interfaces()
            target_node.clear_all_ifaces()

            logging.debug(f"{target_node.get_ssh_command()}")

            target_iface_nums = []
            for target_os_iface in target_os_ifaces:
                target_os_iface_name = target_os_iface['ifname']
                iface_num=target_os_ifaces.index(target_os_iface)+1
                target_node.set_ip_os_interface(os_iface=target_os_iface_name,
                                                  vlan=target_iface.get_vlan(),
                                                  ip=f'192.168.{iface_num}.1',
                                                  cidr = '24'
                                                 )
                target_iface_nums.append(iface_num)

            logging.debug(f"target_node: {target_node.get_name()}")
            logging.debug(f"target_iface: {target_iface.get_name()}")
            logging.debug(f"target_iface.get_vlan(): {target_iface.get_vlan()}")
            logging.debug(f"target_os_ifaces: {target_os_ifaces}")

            for iface in ifaces:
                node = iface.get_node()
                node.clear_all_ifaces()
                node_os_ifaces = node.get_dataplane_os_interfaces()

                logging.debug(f"test_node: {node.get_name()}: {node.get_ssh_command()}")
                logging.debug(f"test_iface: {iface.get_name()}")
                logging.debug(f"node_os_ifaces: {node_os_ifaces}")
                logging.debug(f"iface.get_vlan(): {iface.get_vlan()}")
                logging.debug(f"{node.get_ssh_command()}")

                found = False
                for node_os_iface in node_os_ifaces:
                    node_os_iface_name = node_os_iface['ifname']
                    logging.debug(f"target_iface_nums: {target_iface_nums}")
                    for net_num in target_iface_nums:
                        dst_ip=f'192.168.{net_num}.1'

                        ip=f'192.168.{net_num}.2'

                        #set interface
                        node.set_ip_os_interface(os_iface=node_os_iface_name,
                                                 vlan=iface.get_vlan(),
                                                 ip=ip,
                                                 cidr='24')

                        #ping test
                        logging.debug(f"Node: {node.get_name()}: {node_os_iface_name}, {iface.get_vlan()}, {ip}")

                        logging.debug(f"ping test {node.get_name()}:{node_os_iface_name} ->  - {ip} to {dst_ip}")
                        test_result = node.ping_test(dst_ip)
                        logging.debug(f"Ping test result: {node.get_name()}:{node_os_iface_name} ->  - {ip} to {dst_ip}: {test_result}")

                        if iface.get_vlan() == None:
                            node.flush_os_interface(node_os_iface_name)
                        else:
                            node.remove_vlan_os_interface(os_iface=f"{node_os_iface_name}.{iface.get_vlan()}")

                        if test_result:
                            logging.debug(f"test_result true: {test_result}")
                            target_iface_nums = [ net_num ]
                            found = True
                            iface_map[node.get_name()] = node_os_iface
                            iface_map[target_node.get_name()] = target_os_ifaces[net_num-1]
                            break

                    if found:
                        break


            self.network_iface_map[net.get_name()] = iface_map
            target_node.clear_all_ifaces()

        logging.debug(f"network_iface_map: {self.network_iface_map}")

    def submit(self, wait=True, wait_timeout=360, wait_interval=10, progress=True, delay_post_boot_config=60):
        from fabrictestbed_extensions.fablib.fablib import fablib
        fabric = fablib()

        if not wait:
            progress = False

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = fablib.get_slice_manager().create(slice_name=self.slice_name,
                                                                slice_graph=slice_graph,
                                                                ssh_key=self.get_slice_public_key())
        if return_status != Status.OK:
            raise Exception("Failed to submit slice: {}, {}".format(return_status, slice_reservations))

        logging.debug(f'slice_reservations: {slice_reservations}')
        logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
        self.slice_id = slice_reservations[0].slice_id

        time.sleep(1)
        #self.update_slice()
        self.update()

        if wait:
            self.wait_ssh(timeout=wait_timeout,interval=wait_interval,progress=progress)

            if progress:
                print("Running post boot config ... ",end="")

            #time.sleep(30)
            self.update()

            self.test_ssh()

            #Hack for now. needs to test for active nics before pbc
            time.sleep(delay_post_boot_config)
            self.post_boot_config()

        if progress:
            print("Done!")

        return self.slice_id
