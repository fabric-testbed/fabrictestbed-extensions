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

#from .slicex import SliceX
#from .nodex import NodeX
#from .fabricx import FabricX

#from .abc_fablib import AbcFabLIB

#from fabrictestbed_extensions.fablib.fablib import fablib

class Slice():

    """
    Class representing FABRIC slices.
    """

    def __init__(self, name=None):
        """
        Constructor. Sets the slice name if defined, and sets the remaining slice state to None.
        """
        super().__init__()
        #print(f"Creating Slice: Name: {name}, Slice: {slice}")
        self.slice_name = name
        self.sm_slice = None
        self.slice_id = None
        self.topology = None

        self.slice_key = fablib.get_default_slice_key()

    @staticmethod
    def new_slice(name=None):
        """
        Create a new slice

        :param name: Slice name.
        :type name: str
        :return: the new Slice.
        :rtype: Slice
        """

        slice = Slice(name=name)
        slice.topology = ExperimentTopology()
        return slice

    @staticmethod
    def get_slice(sm_slice=None, verbose=False, load_config=True):
        """
        Create a new slice

        :param name: Slice name.
        :type name: str
        :return: a fablib Slice object.
        :rtype: Slice
        """
        slice = Slice(name=sm_slice.slice_name)
        slice.sm_slice = sm_slice
        slice.slice_id = sm_slice.slice_id
        slice.slice_name = sm_slice.slice_name
        slice.topology = fablib.get_slice_manager().get_slice_topology(slice_object=slice.sm_slice)

        try:
            slice.update()
        except:
            if verbose:
                print(f"Slice {slice.slice_name} could not be updated: slice.get_slice")

        if load_config:
            try:
                slice.load_config()
            except:
                print(f"Slice {slice.slice_name} config could not loaded: slice.get_slice")

        return slice

    def get_fim_topology(self):
        """
        Gets the topology of this Slice.

        :return: the topology of this Slice.
        :rtype: ExperimentTopology
        """
        return self.topology

    def update_slice(self):
        """
        Updates this Slice's information with recent data.
        """
        #Update slice
        return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])
        if return_status == Status.OK:
            self.sm_slice = list(filter(lambda x: x.slice_name == self.slice_name, slices))[0]
            self.slice_id = self.sm_slice.slice_id
        else:
            raise Exception("Failed to get slice list: {}, {}".format(return_status, slices))


    def update_topology(self):
        """
        Updates this Slice's topology with recent data.
        """
        #Update topology
        return_status, new_topo = fablib.get_slice_manager().get_slice_topology(slice_object=self.sm_slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slice topology: {}, {}".format(return_status, new_topo))

        #Set slice attibutes
        self.topology = new_topo

    def update(self):
        """
        Updates Slice information.
        """
        self.update_slice()
        self.update_topology()

    def get_slice_public_key(self):
        """
        Gets the Slice's public key.

        :return: the Slice's public key
        :rtype: str
        """
        return self.slice_key['slice_public_key']

    def get_private_key_passphrase(self):
        """
        Gets the Slice's private key passphrase.

        :return: the Slice's private key passphrase
        :rtype: str
        """
        if 'slice_private_key_passphrase' in self.slice_key.keys():
            return self.slice_key['slice_private_key_passphrase']
        else:
            return None

    def get_slice_public_key(self):
        """
        Gets the Slice's public key.

        :return: the slice's public key.
        :rtype: str
        """
        if 'slice_public_key' in self.slice_key.keys():
            return self.slice_key['slice_public_key']
        else:
            return None

    def get_slice_public_key_file(self):
        """
        Gets the Slice's public key file.

        :return: the Slice's public key file.
        :rtype: File
        """
        if 'slice_public_key_file' in self.slice_key.keys():
            return self.slice_key['slice_public_key_file']
        else:
            return None

    def get_slice_private_key_file(self):
        """
        Gets the Slice's private key file.

        :return: the Slice's private key file.
        :rtype: File
        """
        if 'slice_private_key_file' in self.slice_key.keys():
            return self.slice_key['slice_private_key_file']
        else:
            return None

    def get_state(self):
        """
        Gets the slice state from the SliceManager.

        :return: the slice state
        :rtype: SliceState
        """
        return self.sm_slice.slice_state

    def get_name(self):
        """
        Gets the slice name.

        :return: the slice name
        :rtype: str
        """
        return self.slice_name

    def get_slice_id(self):
        """
        Gets the Slice ID.

        :return: the slice ID
        :rtype: str
        """
        return self.slice_id

    def get_lease_end(self):
        """
        Gets when the slice's lease ends from the SliceManager.

        :return: when the slice's lease ends
        :rtype: DateTimeFormat
        """
        return self.sm_slice.lease_end

    def add_l2network(self, name=None, interfaces=[], type=None):
        """
        Adds an L2 network to the Slice. Calls `NetworkService#new_l2network`.

        :param name: The name of the network.
        :type name: str
        :param interfaces: A list of the interfaces to put on the network.
        :type interfaces: list[Interface]
        :param type: The type of network (if specified).
        :type type: ServiceType
        :return: the new L2 network.
        :rtype: ServiceType
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        return NetworkService.new_l2network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_node(self, name, site):
        """
        Adds a new node to the slice.

        :param name: The name of the node.
        :type name: str
        :param site: The site the new node is on.
        :type site: str
        :return: the new node.
        :rtype: Node
        """
        from fabrictestbed_extensions.fablib.node import Node
        return Node.new_node(slice=self, name=name, site=site)

    def get_nodes(self):
        """
        Gets the nodes on the slice.

        :return: a list of all nodes on the slice.
        :rtype: list[Node]
        """
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()

        return_nodes = []

        #fails for topology that does not have nodes
        try:
            for node_name, node in self.get_fim_topology().nodes.items():
                return_nodes.append(Node.get_node(self,node))
        except Exception as e:
            print("get_nodes: exception")
            traceback.print_exc()
            pass
        return return_nodes

    def get_node(self, name, verbose=False):
        """
        Gets a particular node on the slice, or raises an exception if it is not found.

        :param name: The name of the node.
        :type name: str
        :param verbose: Indicator for whether or not to give verbose output.
        :type verbose: boolean
        :return: the desired node.
        :rtype: Node
        """
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()
        try:
            return Node.get_node(self,self.get_fim_topology().nodes[name])
        except Exception as e:
            if verbose:
                traceback.print_exc()
            raise Exception(f"Node not found: {name}")

    def get_interfaces(self):
        """
        Gets the interfaces attached to each node in this slice.

        :return: a list of interfaces associated with this slice.
        :rtype: list[Interface]
        """
        interfaces = []
        for node in self.get_nodes():
            for interface in node.get_interfaces():
                interfaces.append(interface)
        return interfaces

    def get_interface(self, name=None):
        """
        Gets a particular interface associated with this slice.

        :return: an interface on this slice
        :rtype: Interface
        """
        for interface in self.get_interfaces():
            if name.endswith(interface.get_name()):
                return interface

        raise Exception("Interface not found: {}".format(name))



    def get_l2networks(self, verbose=False):
        """
        Gets L2 networks associated with this slice.

        :return: a list of L2 networks on this slice
        :rtype: list[NetworkSevice]
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_services(self)
        except Exception as e:
            if verbose:
                traceback.print_exc()
        return None

    def get_l2network(self, name=None, verbose=False):
        """
        Gets a particular L2 networks associated with this slice.

        :return: an L2 networks on this slice
        :rtype: NetworkSevice
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_service(self,name)
        except Exception as e:
            if verbose:
                traceback.print_exc()
        return None


    def delete(self):
        """
        Deletes this slice from the SliceManager.
        """
        return_status, result = fablib.get_slice_manager().delete(slice_object=self.sm_slice)

        if return_status != Status.OK:
            raise Exception("Failed to delete slice: {}, {}".format(return_status, result))

        self.topology = None

    def renew(self, end_date):
        """
        Renews this slice until the provided end date.

        :param end_date: The new end date of the slice.
        :type end_date: DateTimeFormat
        """
        return_status, result = fablib.get_slice_manager().renew(slice_object=self.sm_slice,
                                     new_lease_end_time = end_date)

        if return_status != Status.OK:
            raise Exception("Failed to renew slice: {}, {}".format(return_status, result))

    def wait(self, timeout=360,interval=10,progress=False):
        """
        Waits for this slice to be active.

        :param timeout: How long (in seconds) to wait for the slice to be active.
        :type timeout: int
        :param interval: How often to check if the slice is active.
        :type interval: int
        :param progress: Indicator for whether or not to show progress.
        :type progress: boolean
        :return: the new slice.
        :rtype: Slice
        """
        slice_name=self.sm_slice.slice_name
        slice_id=self.sm_slice.slice_id

        timeout_start = time.time()
        slice = self.sm_slice

        if progress: print("Waiting for slice .", end = '')
        while time.time() < timeout_start + timeout:
            return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])

            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
                if slice.slice_state == "StableOK":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if slice.slice_state == "Closing" or slice.slice_state == "Dead" or slice.slice_state == "StableError":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
            else:
                print(f"Failure: {slices}")

            if progress: print(".", end = '')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
            return slice

        #Update the fim topology (wait to avoid get topology bug)
        time.sleep(interval)
        self.update()

    def get_interface_map(self):
        """
        Gets the interface map on this slice.

        :return: a map of key names to interfaces
        :rtype: dict(str->Interface)
        """
        if not hasattr(self, 'network_iface_map'):
            self.load_interface_map()

        return self.network_iface_map

    def post_boot_config(self, verbose=False):
        """
        Runs post-boot configuration for this slice.

        :param verbose: Indicator for whether or not to give verbose output.
        :type verbose: boolean
        """
        # Find the interface to network map
        self.build_interface_map()

        # Interface map in nodes
        for node in self.get_nodes():
            node.save_data()

        for interface in self.get_interfaces():
            interface.config_vlan_iface()

    def load_config(self):
        """
        Loads this slice's configuration.
        """
        self.load_interface_map()

    def load_interface_map(self, verbose=False):
        """
        Loads this slice's interface map.

        :param verbose: Indicator for whether or not to give verbose output.
        :type verbose: boolean
        """
        self.network_iface_map = {}
        for net in self.get_l2networks():
            self.network_iface_map[net.get_name()] = {}

        for node in self.get_nodes():
            node.load_data()


    def build_interface_map(self, verbose=False):
        """
        Builds this slice's interface map based on the L2 networks on this slice.

        :param verbose: Indicator for whether or not to give verbose output.
        :type verbose: boolean
        """
        self.network_iface_map = {}
        for net in self.get_l2networks():
            iface_map = {}

            if verbose == True:
                print(f"Buiding iface map for network: {net.get_name()}")
            ifaces = net.get_interfaces()

            #target iface/node
            target_iface =  ifaces.pop()
            target_node = target_iface.get_node()
            target_os_ifaces = target_node.get_dataplane_os_interfaces()
            target_node.clear_all_ifaces()

            #print(f"{target_node.get_ssh_command()}")

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


            #print(f"target_iface: {target_iface.get_name()}")
            #print(f"target_iface.get_vlan(): {target_iface.get_vlan()}")
            #print(f"target_node: {target_node.get_name()}")
            #print(f"target_os_ifaces: {target_os_ifaces}")


            for iface in ifaces:
                node = iface.get_node()
                node.clear_all_ifaces()
                node_os_ifaces = node.get_dataplane_os_interfaces()


                #print(f"test_node: {node.get_name()}")
                #print(f"test_iface: {iface.get_name()}")
                #print(f"node_os_ifaces: {node_os_ifaces}")
                #print(f"iface.get_vlan(): {iface.get_vlan()}")
                #print(f"{node.get_ssh_command()}")

                found = False
                for node_os_iface in node_os_ifaces:
                    node_os_iface_name = node_os_iface['ifname']
                    #print(f"target_iface_nums: {target_iface_nums}")
                    for net_num in target_iface_nums:
                        dst_ip=f'192.168.{net_num}.1'

                        ip=f'192.168.{net_num}.2'

                        #set interface
                        node.set_ip_os_interface(os_iface=node_os_iface_name,
                                                 vlan=iface.get_vlan(),
                                                 ip=ip,
                                                 cidr='24')

                        #ping test
                        #print(f"ping test {node.get_name()}:{node_os_iface_name} ->  - {ip} to {dst_ip}")
                        test_result = node.ping_test(dst_ip)
                        #print(f"Ping test result: {test_result}")

                        if iface.get_vlan() == None:
                            node.flush_os_interface(node_os_iface_name)
                        else:
                            node.remove_vlan_os_interface(os_iface=f"{node_os_iface_name}.{iface.get_vlan()}")

                        if test_result:
                            #print(f"test_result true: {test_result}")
                            target_iface_nums = [ net_num ]
                            found = True
                            iface_map[node.get_name()] = node_os_iface
                            iface_map[target_node.get_name()] = target_os_ifaces[net_num-1]
                            break

                    if found:
                        break

            self.network_iface_map[net.get_name()] = iface_map
            target_node.clear_all_ifaces()

        if verbose:
            print(f"network_iface_map: {self.network_iface_map}")

    def submit(self, wait=False, wait_timeout=360, wait_interval=10, wait_progress=False, wait_ssh=False):
        """
        Submits this slice state to the FABRIC API to be created.

        :param wait: Indicator for whether or not to wait for the slice to be created.
        :type wait: boolean
        :param wait_timeout: How long (in seconds) to wait for the slice to be active.
        :type wait_timeout: int
        :param wait_interval: How often (in seconds) to check if the slice is active.
        :param wait_progress: Indicator for whether or not to show slice waiting progress.
        :type wait_progress: boolean
        :param wait_ssh: Indicator for whether or not to wait for the slice to be SSH-able.
        :type wait_ssh: boolean
        """
        from fabrictestbed_extensions.fablib.fablib import fablib
        fabric = fablib()

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = fablib.get_slice_manager().create(slice_name=self.slice_name,
                                                                slice_graph=slice_graph,
                                                                ssh_key=self.get_slice_public_key())
        if return_status != Status.OK:
            raise Exception("Failed to submit slice: {}, {}".format(return_status, slice_reservations))

        time.sleep(10)
        self.update_slice()

        if wait or wait_progress:
            self.wait(timeout=wait_timeout,interval=wait_interval,progress=wait_progress)

            if wait_progress:
                print("Running post boot config ...",end="")

            time.sleep(30)
            self.update()

            for node in self.get_nodes():
                node.wait_for_ssh()

            self.post_boot_config()

        if wait_progress:
            print("Done!")
