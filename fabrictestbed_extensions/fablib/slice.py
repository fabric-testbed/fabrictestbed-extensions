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
from typing import List, Union

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fabrictestbed.slice_manager import Slice as SMSlice

from fabrictestbed_extensions.fablib.network_service import NetworkService


#from .slicex import SliceX
#from .nodex import NodeX
#from .fabricx import FabricX

#from .abc_fablib import AbcFabLIB
from .interface import Interface

from .. import images

from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.node import Node


class Slice():

    def __init__(self, name=None):
        """
        Constructor. Sets the default slice state to be callable.

        :param name: the name of this fablib slice
        :type name: str
        """
        super().__init__()
        #print(f"Creating Slice: Name: {name}, Slice: {slice}")
        self.network_iface_map = None
        self.slice_name = name
        self.sm_slice = None
        self.slice_id = None
        self.topology = None

        self.slice_key = fablib.get_default_slice_key()

    @staticmethod
    def new_slice(name=None):
        """
        Create a new slice

        :param name: slice name
        :type name: str
        :return: fablib slice
        :rtype: Slice
        """

        slice = Slice(name=name)
        slice.topology = ExperimentTopology()
        return slice

    @staticmethod
    def get_slice(sm_slice=None, verbose=False, load_config=True):
        """
        Create a new fablib slice using a slice already on the slice manager.

        :param sm_slice: the slice on the slice manager
        :type sm_slice: SMSlice
        :param verbose: indicator for verbose output
        :type verbose: bool
        :param load_config: indicator for whether to load the FABRIC slice configuration
        :type load_config: bool
        :return: fablib slice
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

    def get_fim_topology(self) -> ExperimentTopology:
        """
        Gets the slice's experiment topology

        :return: FABRIC experiment topology
        :rtype: ExperimentTopology
        """
        return self.topology

    def update_slice(self, verbose=False):
        """
        Updates this fablib slice to store the most up-to-date slice manager slice

        :param verbose: indicator for verbose output
        :type verbose: bool
        :raises Exception: if slice manager slice no longer exists
        """
        #Update slice
        #return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])
        #return_status, slices = fablib.get_slice_manager().slices(excludes=[])

        import time
        if verbose:
            start = time.time()
            print("Running slice.update_slice() : fablib.get_slice_manager().slices(): ", end="")
        return_status, slices = fablib.get_slice_manager().slices(excludes=[])
        if verbose:
            end = time.time()
            print(f"elapsed time: {end - start} seconds")

        if return_status == Status.OK:
            self.sm_slice = list(filter(lambda x: x.slice_id == self.slice_id, slices))[0]
            #self.slice_name = self.sm_slice.slice_name
        else:
            raise Exception("Failed to get slice list: {}, {}".format(return_status, slices))

    def update_topology(self):
        """
        Updates the fabric slice topology with the slice manager slice's topolofy

        :raises Exception: if topology could not be gotten from slice manager
        """
        #Update topology
        return_status, new_topo = fablib.get_slice_manager().get_slice_topology(slice_object=self.sm_slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slice topology: {}, {}".format(return_status, new_topo))

        #Set slice attibutes
        self.topology = new_topo

    def update(self):
        """
        Updates both the physical slice and topology state of this fablib slice.

        :raises Exception: if updating topology fails
        """
        try:
            self.update_slice()
        except:
            pass
            # print('update slice error')

        self.update_topology()

    def get_slice_public_key(self) -> str:
        """
        Gets the slice public key.

        :return: the public key
        :rtype: str
        """
        return self.slice_key['slice_public_key']

    def get_private_key_passphrase(self) -> str:
        """
        Gets the slice private key passphrase.

        :return: the private key passphrase
        :rtype: str
        """
        if 'slice_private_key_passphrase' in self.slice_key.keys():
            return self.slice_key['slice_private_key_passphrase']
        else:
            return None

    def get_slice_public_key(self) -> str:
        """
        Gets the slice public key.

        :return: the public key
        :rtype: str
        """
        if 'slice_public_key' in self.slice_key.keys():
            return self.slice_key['slice_public_key']
        else:
            return None

    def get_slice_public_key_file(self) -> str:
        """
        Gets the path to the slice public key file.

        :return: path to public key file
        :rtype: str
        """
        if 'slice_public_key_file' in self.slice_key.keys():
            return self.slice_key['slice_public_key_file']
        else:
            return None

    def get_slice_private_key_file(self) -> str:
        """
        Gets the path to the slice private key file.

        :return: path to private key file
        :rtype: str
        """
        if 'slice_private_key_file' in self.slice_key.keys():
            return self.slice_key['slice_private_key_file']
        else:
            return None

    def get_state(self) -> SliceState:
        """
        Gets the slice state off of the slice manager slice.

        :return: the slice state
        :rtype: SliceState
        """
        return self.sm_slice.slice_state

    def get_name(self)-> str:
        """
        Gets the slice's name.

        :return: the slice name
        :rtype: str
        """
        return self.slice_name

    def get_slice_id(self):
        """
        Gets the slice's ID.

        :return: the slice ID
        :rtype: str
        """
        return self.slice_id

    def get_lease_end(self) -> str:
        """
        Gets the timestamp at which the slice lease ends.

        :return: timestamp when lease ends
        :rtype: str
        """
        return self.sm_slice.lease_end

    def add_l2network(self, name=None, interfaces=[], type=None) -> NetworkService:
        """
        Creates a new L2 network service using this fablib slice.

        :param name: the name of the network service
        :type name: str
        :param interfaces: a list of interfaces to build the network with
        :type interfaces: list[Interface]
        :param type: optional L2 network type specification
        :return: a new L2 network service
        :rtype: NetworkService
        """
        return NetworkService.new_l2network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_node(self, name, site) -> Node:
        """
        Creates a new node on this fablib slice.

        :param name: the name of the new node
        :type name: str
        :param site: the name of the site to construct the node on
        :type site: str
        :return: a new node
        :rtype: Node
        """
        return Node.new_node(slice=self, name=name, site=site)

    def get_object_by_reservation(self, reservation_id) -> Union[Node]:
        """
        Gets an object associated with this slice by its reservation ID. Currently, this method can find Node objects.

        :param reservation_id: the ID to search for
        :return: Node
        """
        # test all nodes
        try:
            for node in self.get_nodes():
                if node.get_reservation_id() == reservation_id:
                    return node

                    # TODO: test other resource types.
        except:
            pass

        return None

    def get_error_messages(self) -> list[dict[str, str]]:
        """
        Gets the error messages found in the slice notices.

        :return: a list of error messages
        :rtype: list[dict[str, str]]
        """
        # strings to ingnor
        cascade_notice_string1 = 'Closing reservation due to failure in slice'
        cascade_notice_string2 = 'is in a terminal state'

        origin_notices = []
        for reservation_id, notice in self.get_notices().items():
            # print(f"XXXXX: reservation_id: {reservation_id}, notice {notice}")
            if cascade_notice_string1 in notice or cascade_notice_string2 in notice:
                continue

            origin_notices.append({'reservation_id': reservation_id, 'notice': notice,
                                   'sliver': self.get_object_by_reservation(reservation_id)})

        return origin_notices

    def get_notices(self) -> dict[str, str]:
        """
        Gets a dictionary of node reservation IDs to node error messages.

        :return: dictionary of node IDs to error messages
        :rtype: dict[str, str]
        """
        notices = {}
        for node in self.get_nodes():
            notices[node.get_reservation_id()] = node.get_error_message()

        return notices

    def get_nodes(self) -> list[Node]:
        """
        Gets a list of fablib nodes based on the existing FABRIC nodes on the slice.

        :return: a list of fablib nodes
        :rtype: list[Node]
        """
        # self.update()

        return_nodes = []

        # fails for topology that does not have nodes
        try:
            for node_name, node in self.get_fim_topology().nodes.items():
                return_nodes.append(Node.get_node(self, node))
        except Exception as e:
            print("get_nodes: exception")
            traceback.print_exc()
            pass
        return return_nodes

    def get_node(self, name, verbose=False) -> Node:
        """
        Gets a particular fablib node based on the existing FABRIC nodes.

        :param name: the name of the node
        :type name: str
        :param verbose: indicator for verbose output
        :type verbose: bool
        :return: a fablib node
        :rtype: Node
        """
        # self.update()
        try:
            return Node.get_node(self, self.get_fim_topology().nodes[name])
        except Exception as e:
            if verbose:
                traceback.print_exc()
            raise Exception(f"Node not found: {name}")

    def get_interfaces(self) -> list[Interface]:
        """
        Gets a list of fablib interfaces on this slice's nodes.

        :return: a list of interfaces on this slice
        :rtype: list[Interface]
        """
        interfaces = []
        for node in self.get_nodes():
            for interface in node.get_interfaces():
                interfaces.append(interface)
        return interfaces

    def get_interface(self, name=None) -> Interface:
        """
        Gets a particular fablib interface from this slice's nodes.

        :param name: the name of the interface to search for
        :type name: str
        :raises Exception: if no interfaces with name are found
        :return: an interface on this slice
        :rtype: Interface
        """
        for interface in self.get_interfaces():
            if name.endswith(interface.get_name()):
                return interface

        raise Exception("Interface not found: {}".format(name))

    def get_l2networks(self, verbose=False) -> list[NetworkService]:
        """
        Gets a list of the L2 network services on this slice.

        :param verbose: indicator for verbose output
        :type verbose: bool
        :return: network services on this slice
        :rtype: list[NetworkService]
        """
        try:
            return NetworkService.get_l2network_services(self)
        except Exception as e:
            if verbose:
                traceback.print_exc()
        return None

    def get_l2network(self, name=None, verbose=False) -> NetworkService:
        """
        Gest a particular L2 network service on this slice.

        :param name: the name of the network service to search for
        :type name: str
        :param verbose: indicator for verbose output
        :type verbose: bool
        :return: a particular network service
        :rtype: NetworkService
        """

        try:
            return NetworkService.get_l2network_service(self,name)
        except Exception as e:
            if verbose:
                traceback.print_exc()
        return None

    def delete(self):
        """
        Deletes this slice off of the slice manager and removes its topology.

        :raises Exception: if deleting the slice fails
        """
        return_status, result = fablib.get_slice_manager().delete(slice_object=self.sm_slice)

        if return_status != Status.OK:
            raise Exception("Failed to delete slice: {}, {}".format(return_status, result))

        self.topology = None

    def renew(self, end_date):
        """
        Renews the FABRIC slice's lease to the new end date.

        :param end_date: str
        :raises Exception: if renewal fails
        """
        return_status, result = fablib.get_slice_manager().renew(slice_object=self.sm_slice,
                                                                 new_lease_end_time=end_date)

        if return_status != Status.OK:
            raise Exception("Failed to renew slice: {}, {}".format(return_status, result))

    def build_error_exception_string(self) -> str:
        """
        Formats one string with all the error information on this slice's nodes.

        :return: a string with all the error information relevant to this slice
        :rtype: str
        """
        exception_string = ""
        for error in self.get_error_messages():
            notice = error['notice']
            sliver = error['sliver']

            sliver_extra = ""
            if isinstance(sliver, Node):
                sliver_extra = f"Node: {sliver.get_name()}, Site: {sliver.get_site()}, State: {sliver.get_reservation_state()}, "

            # skip errors that are caused by slice error
            if 'Closing reservation due to failure in slice' in notice:
                continue

            exception_string += f"{exception_string}{sliver_extra}{notice}\n"

        return exception_string

    def wait(self, timeout=360, interval=10, progress=False) -> SMSlice:
        """
        Waits for the slice on the slice manager to be in a stable, running state.

        :param timeout: how many seconds to wait on the slice
        :type timeout: int
        :param interval: how often in seconds to check on slice state
        :type interval: int
        :param progress: indicator for whether to print wait progress
        :type progress: bool
        :raises Exception: if the slice state is undesireable, or waiting times out
        :return: the stable slice on the slice manager
        :rtype: SMSlice
        """
        slice_id = self.sm_slice.slice_id

        timeout_start = time.time()
        slice = self.sm_slice

        if progress:
            print("Waiting for slice .", end='')
        while time.time() < timeout_start + timeout:
            # return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])
            return_status, slices = fablib.get_slice_manager().slices(excludes=[])
            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
                if slice.slice_state == "StableOK":
                    if progress:
                        print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if slice.slice_state == "Closing" or slice.slice_state == "Dead" or slice.slice_state == "StableError":
                    if progress:
                        print(" Slice state: {}".format(slice.slice_state))
                    exception_string = self.build_error_exception_string()
                    raise Exception(str(exception_string))
            else:
                print(f"Failure: {slices}")

            if progress:
                print(".", end='')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            raise Exception(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout, slice.slice_name,
                                                                                slice.slice_state))

        # Update the fim topology (wait to avoid get topology bug)
        # time.sleep(interval)
        self.update()

    def get_interface_map(self):
        # TODO: Add docstring after doc networking classes
        if not hasattr(self, 'network_iface_map'):
            self.load_interface_map()

        return self.network_iface_map

    def wait_ssh(self, timeout=360, interval=10, progress=False) -> bool:
        """
        Checks that this slice's resources are ssh-able.

        :param timeout: how long to wait on slice ssh
        :type timeout: int
        :param interval: how often to check on slice ssh
        :type interval: int
        :param progress: indicator for verbose output
        :type progress: bool
        :raises Exception: if timeout threshold reached
        :return: true when slice ssh successful
        :rtype: bool
        """
        timeout_start = time.time()
        slice = self.sm_slice

        # Wait for the slice to be stable ok
        self.wait(timeout=timeout,interval=interval,progress=progress)

        # Test ssh
        if progress:
            print("Waiting for ssh in slice .", end='')
        while time.time() < timeout_start + timeout:

            if self.test_ssh():
                if progress:
                    print(" ssh successful")
                return True

            if progress:
                print(".", end = '')

            if time.time() >= timeout_start + timeout:
                # if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout, slice.slice_name,
                #                                                                        slice.slice_state))
                raise Exception(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout, slice.slice_name,
                                                                                    slice.slice_state))

            time.sleep(interval)
            self.update()

    def test_ssh(self, verbose=False) -> bool:
        """
        Tests whether each node on this slice is ssh-able.

        :param verbose: indicator for verbose output
        :type verbose: bool
        :return: indicator for whether or not all nodes were ssh-able
        :rtype: bool
        """
        for node in self.get_nodes():
            if not node.test_ssh():
                if verbose:
                    print(f"test_ssh fail: {node.get_name()}: {node.get_management_ip()}")
                return False
        return True

    def post_boot_config(self, verbose=False):
        # TODO: Add docstring after doc networking classes
        if verbose: print(f"post_boot_config")
        # Find the interface to network map

        if verbose: print(f"build_interface_map")
        self.build_interface_map(verbose=verbose)

        # Interface map in nodes
        for node in self.get_nodes():
            if verbose:
                print(f"Node data {node.get_name()}")
                try:
                    print(f"{node.get_interface_map()}")
                except Exception as e:
                    print(f"{e}")



            node.save_data()

        for interface in self.get_interfaces():
            try:
                interface.config_vlan_iface()
            except Exception as e:
                if verbose: print(f"Interface: {interface.get_name()} failed to config")

    def load_config(self):
        """
        Loads the slice configuration.
        """
        self.load_interface_map()

    def load_interface_map(self, verbose=False):
        """
        Generates an empty network interface map.

        :param verbose: Indicator for verbose output. Currently, unused.
        :type verbose: bool
        """
        self.network_iface_map = {}
        for net in self.get_l2networks():
            self.network_iface_map[net.get_name()] = {}

        for node in self.get_nodes():
            node.load_data()

    def build_interface_map(self, verbose=False):
        # TODO: Add docstring after doc networking classes
        self.network_iface_map = {}
        for net in self.get_l2networks():
            iface_map = {}

            if verbose == True:
                print(f"Buiding iface map for network: {net.get_name()}")
            ifaces = net.get_interfaces()

            #target iface/node
            target_iface =  ifaces.pop()
            #for iface in ifaces:
            #    print(f"iface name: {iface.get_name()}")
            #    if iface.get_name() == 'lbnl-w3_NIC_ConnectX_51-lbnl-w3_NIC_ConnectX_51NIC-p1':
            #        target_iface=iface
            #        ifaces.remove(iface)

            target_node = target_iface.get_node()
            target_os_ifaces = target_node.get_dataplane_os_interfaces()
            target_node.clear_all_ifaces()

            if verbose: print(f"{target_node.get_ssh_command()}")

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

            #if verbose:
                #print(f"Target Node: {target_node.get_name()}:")
                #stdout, stderr = target_node.execute(f'ip addr list')
                #print(stdout)


            if verbose:
                print(f"target_node: {target_node.get_name()}")
                print(f"target_iface: {target_iface.get_name()}")
                print(f"target_iface.get_vlan(): {target_iface.get_vlan()}")
                print(f"target_os_ifaces: {target_os_ifaces}")


            for iface in ifaces:
                node = iface.get_node()
                node.clear_all_ifaces()
                node_os_ifaces = node.get_dataplane_os_interfaces()

                if verbose:
                    print(f"test_node: {node.get_name()}: {node.get_ssh_command()}")
                    #print(f"test_iface: {iface.get_name()}")
                    #print(f"node_os_ifaces: {node_os_ifaces}")
                    #print(f"iface.get_vlan(): {iface.get_vlan()}")
                    #print(f"{node.get_ssh_command()}")

                found = False
                for node_os_iface in node_os_ifaces:
                    node_os_iface_name = node_os_iface['ifname']
                    #if verbose: print(f"target_iface_nums: {target_iface_nums}")
                    for net_num in target_iface_nums:
                        dst_ip=f'192.168.{net_num}.1'

                        ip=f'192.168.{net_num}.2'

                        #set interface
                        node.set_ip_os_interface(os_iface=node_os_iface_name,
                                                 vlan=iface.get_vlan(),
                                                 ip=ip,
                                                 cidr='24')

                        #ping test
                        #if verbose:
                        #    print(f"Node: {node.get_name()}: {node_os_iface_name}, {iface.get_vlan()}, {ip}")
                        #    stdout, stderr = node.execute(f'ip addr list')
                        #    print(stdout)
                        #if verbose: print(f"ping test {node.get_name()}:{node_os_iface_name} ->  - {ip} to {dst_ip}")
                        test_result = node.ping_test(dst_ip)
                        if verbose: print(f"Ping test result: {node.get_name()}:{node_os_iface_name} ->  - {ip} to {dst_ip}: {test_result}")

                        if iface.get_vlan() == None:
                            node.flush_os_interface(node_os_iface_name)
                        else:
                            node.remove_vlan_os_interface(os_iface=f"{node_os_iface_name}.{iface.get_vlan()}")

                        if test_result:
                            #if verbose: print(f"test_result true: {test_result}")
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
        Submits this fablib slice to be built on the slice manager.

        :param wait: indicator for whether to wait for the slice's resources to be active
        :type wait: bool
        :param wait_timeout: how many seconds to wait on the slice resources
        :type wait_timeout: int
        :param wait_interval: how often to check on the slice resources
        :type wait_interval: int
        :param wait_progress: indicator for whether to show progress while waiting
        :type wait_progress: bool
        :param wait_ssh: indicator for whether to wait onslice resources to be ssh-able. Currently, unused.
        :type wait_ssh: bool
        """
        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = fablib.get_slice_manager().create(slice_name=self.slice_name,
                                                                slice_graph=slice_graph,
                                                                ssh_key=self.get_slice_public_key())
        if return_status != Status.OK:
            raise Exception("Failed to submit slice: {}, {}".format(return_status, slice_reservations))

        # print(f'slice_reservations: {slice_reservations}')
        # print(f"slice_id: {slice_reservations[0].slice_id}")
        self.slice_id = slice_reservations[0].slice_id

        time.sleep(5)
        #self.update_slice()
        self.update()

        if wait or wait_progress:
            self.wait(timeout=wait_timeout,interval=wait_interval,progress=wait_progress)

            if wait_progress:
                print("Running post boot config ...",end="")

            # time.sleep(30)
            self.update()

            for node in self.get_nodes():
                node.wait_for_ssh()

            self.post_boot_config()

        if wait_progress:
            print("Done!")
