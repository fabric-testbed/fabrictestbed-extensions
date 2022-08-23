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
import ipaddress

import time
import logging
from concurrent.futures import ThreadPoolExecutor

from typing import TYPE_CHECKING

from fabrictestbed_extensions.fablib.facility_port import FacilityPort

if TYPE_CHECKING:
    from fabric_cf.orchestrator.swagger_client import Slice as OrchestratorSlice, Sliver as OrchestratorSliver
    from fabrictestbed_extensions.fablib.fablib import FablibManager

from tabulate import tabulate

from ipaddress import ip_address, IPv4Address

from typing import List, Union, Dict

from fabrictestbed.slice_editor import ExperimentTopology
from fabrictestbed.slice_manager import Status, SliceState


from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.component import Component
from fabrictestbed_extensions.fablib.interface import Interface


class Slice:

    def __init__(self, fablib_manager: FablibManager, name: str = None):
        """
        Constructor. Sets the default slice state to be callable.

        :param name: the name of this fablib slice
        :type name: str
        """
        super().__init__()

        self.network_iface_map = None
        self.slice_name = name
        self.sm_slice = None
        self.slice_id = None
        self.topology = None
        self.slivers = []
        self.fablib_manager = fablib_manager

        self.slice_key = fablib_manager.get_default_slice_key()

    def get_fablib_manager(self):
        return self.fablib_manager

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the slice.

        Intended for printing slice information.

        :return: Tabulated string of slice information
        :rtype: String
        """
        table = [["Slice Name", self.sm_slice.name],
                 ["Slice ID", self.sm_slice.slice_id],
                 ["Slice State", self.sm_slice.state],
                 ["Lease End", self.sm_slice.lease_end_time]
                ]

        return tabulate(table)

    def save(self, filename):
        """
        Saves the slice topology to a file. The file can be loaded to create
        a new slice with the same topology.

        The slice topology can be saved before the original request has been submitted
        or after. If the slice is saved after it is instantiated, only the topology is
        save.  Any configuration of nodes is not included.

        :param filename: path to the file to save the slice.
        :type filename: String
        """

        self.get_fim_topology().serialize(filename)

    def load(self, filename):
        """
         Loads a slice request topology from file. The file can be loaded to create
         a new slice with the same topology as a previously saved slice.

         :param filename: path to the file to save the slice.
         :type filename: String
         """
        self.network_iface_map = None
        self.sm_slice = None
        self.slice_id = None

        self.get_fim_topology().load(file_name=filename)

    def list_nodes(self):
        """
        Creates a tabulated string describing all nodes in the slice.

        Intended for printing a list of all slices.

        :return: Tabulated srting of all slices information
        :rtype: String
        """
        table = []
        for node in self.get_nodes():
            table.append([node.get_reservation_id(),
                          node.get_name(),
                          node.get_site(),
                          node.get_host(),
                          node.get_cores(),
                          node.get_ram(),
                          node.get_disk(),
                          node.get_image(),
                          node.get_management_ip(),
                          node.get_reservation_state(),
                          node.get_error_message(),
                        ])

        return tabulate(table, headers=["ID", "Name",  "Site",  "Host", "Cores", "RAM", "Disk", "Image",
                                        "Management IP", "State", "Error"])

    def list_interfaces(self):
        """
        Creates a tabulated string describing all interfaces in the slice.

        Intended to print a list of all interfaces.

        :return: Tabulated string of all interfaces
        :rtype: String
        """
        executor = ThreadPoolExecutor(10)

        net_name_threads = {}
        node_name_threads = {}
        physical_os_interface_name_threads = {}
        os_interface_threads = {}
        for iface in self.get_interfaces():
            if iface.get_network():
                logging.info(f"Starting get network name thread for iface {iface.get_name()} ")
                net_name_threads[iface.get_name()] = executor.submit(iface.get_network().get_name)

            if iface.get_node():
                logging.info(f"Starting get node name thread for iface {iface.get_name()} ")
                node_name_threads[iface.get_name()] = executor.submit(iface.get_node().get_name)

            logging.info(f"Starting get physical_os_interface_name_threads for iface {iface.get_name()} ")
            physical_os_interface_name_threads[iface.get_name()] = executor.submit(iface.get_physical_os_interface_name)

            logging.info(f"Starting get get_os_interface_threads for iface {iface.get_name()} ")
            os_interface_threads[iface.get_name()] = executor.submit(iface.get_os_interface)

        table = []
        for iface in self.get_interfaces():

            if iface.get_network():
                #network_name = iface.get_network().get_name()
                logging.info(f"Getting results from get network name thread for iface {iface.get_name()} ")
                network_name = net_name_threads[iface.get_name()].result()
            else:
                network_name = None

            if iface.get_node():
                #node_name = iface.get_node().get_name()
                logging.info(f"Getting results from get node name thread for iface {iface.get_name()} ")
                node_name = node_name_threads[iface.get_name()].result()

            else:
                node_name = None

            table.append([iface.get_name(),
                          node_name,
                          network_name,
                          iface.get_bandwidth(),
                          iface.get_vlan(),
                          iface.get_mac(),
                          physical_os_interface_name_threads[iface.get_name()].result(),
                          os_interface_threads[iface.get_name()].result(),
                        ])

        return tabulate(table, headers=["Name", "Node", "Network", "Bandwidth", "VLAN", "MAC",
                                        "Physical OS Interface", "OS Interface"])

    @staticmethod
    def new_slice(fablib_manager: FablibManager, name: str = None):
        """
        Create a new slice
        :param fablib_manager:
        :param name:
        :return: Slice
        """
        slice = Slice(fablib_manager=fablib_manager, name=name)
        slice.topology = ExperimentTopology()
        return slice

    @staticmethod
    def get_slice(fablib_manager: FablibManager, sm_slice: OrchestratorSlice = None):
        """
        Not intended for API use.

        Gets an existing fablib slice using a slice manager slice
        :param fablib_manager:
        :param sm_slice:
        :return: Slice
        """
        logging.info("slice.get_slice()")

        slice = Slice(fablib_manager=fablib_manager, name=sm_slice.name)
        slice.sm_slice = sm_slice
        slice.slice_id = sm_slice.slice_id
        slice.slice_name = sm_slice.name

        try:
            slice.update_topology()
        except Exception as e:
            logging.error(f"Slice {slice.slice_name} could not update topology: slice.get_slice")
            logging.error(e, exc_info=True)

        try:
            slice.update_slivers()
        except Exception as e:
            logging.error(f"Slice {slice.slice_name} could not update slivers: slice.get_slice")
            logging.error(e, exc_info=True)

        return slice

    def get_fim_topology(self) -> ExperimentTopology:
        """
        Not recommended for most users.

        Gets the slice's FABRIC Information Model (fim) topology. This method
        is used to access data at a lower level than FABlib.

        :return: FABRIC experiment topology
        :rtype: ExperimentTopology
        """
        return self.topology

    def update_slice(self):
        """
        Note recommended for most users.  See Slice.update() method.

        Updates this slice manager slice to store the most up-to-date
        slice manager slice

        :raises Exception: if slice manager slice no longer exists
        """
        if self.fablib_manager.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = self.fablib_manager.get_slice_manager().slices(excludes=[], slice_id=self.slice_id,
                                                                               name=self.slice_name)
        if self.fablib_manager.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(f"Running slice.update_slice() : fablib.get_slice_manager().slices(): "
                          f"elapsed time: {end - start} seconds")

        if return_status == Status.OK:
            self.sm_slice = list(filter(lambda x: x.slice_id == self.slice_id, slices))[0]
        else:
            raise Exception("Failed to get slice list: {}, {}".format(return_status, slices))

    def update_topology(self):
        """
        Not recommended for most users.  See Slice.update() method.

        Updates the fabric slice topology with the slice manager slice's topology

        :raises Exception: if topology could not be gotten from slice manager
        """
        # Update topology
        if self.sm_slice.model is not None and self.sm_slice.model != '':
            self.topology = ExperimentTopology()
            self.topology.load(graph_string=self.sm_slice.model)
            return

        return_status, new_topo = self.fablib_manager.get_slice_manager().get_slice_topology(slice_object=self.sm_slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slice topology: {}, {}".format(return_status, new_topo))

        # Set slice attibutes
        self.topology = new_topo

    def update_slivers(self):
        """
        Not recommended for most users.  See Slice.update() method.

        Updates the slivers with the current slice manager.

        :raises Exception: if topology could not be gotten from slice manager
        """
        if self.sm_slice is None:
            return
        status, slivers = self.fablib_manager.get_slice_manager().slivers(slice_object=self.sm_slice)
        if status == Status.OK:
            self.slivers = slivers
            return

        raise Exception(f"{slivers}")

    def get_sliver(self, reservation_id: str) -> OrchestratorSliver:
        slivers = self.get_slivers()
        sliver = list(filter(lambda x: x.sliver_id == reservation_id, slivers))[0]
        return sliver

    def get_slivers(self) -> List[OrchestratorSliver]:
        if not self.slivers:
            self.update_slivers()

        return self.slivers

    def update(self):
        """
        Query the FABRIC services for updated information about this slice.

        :raises Exception: if updating topology fails
        """
        try:
            self.update_slice()
        except Exception as e:
            logging.warning(f"slice.update_slice failed: {e}")

        try:
            self.update_slivers()
        except Exception as e:
            logging.warning(f"slice.update_slivers failed: {e}")

        self.update_topology()

    def get_private_key_passphrase(self) -> str:
        """
        Gets the slice private key passphrase.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the private key passphrase
        :rtype: String
        """
        if 'slice_private_key_passphrase' in self.slice_key.keys():
            return self.slice_key['slice_private_key_passphrase']
        else:
            return None

    def get_slice_public_key(self) -> str:
        """
        Gets the slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the public key
        :rtype: String
        """
        if 'slice_public_key' in self.slice_key.keys():
            return self.slice_key['slice_public_key']
        else:
            return None

    def get_slice_public_key_file(self) -> str:
        """
        Gets the path to the slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: path to public key file
        :rtype: String
        """
        if 'slice_public_key_file' in self.slice_key.keys():
            return self.slice_key['slice_public_key_file']
        else:
            return None

    def get_slice_private_key_file(self) -> str:
        """
        Gets the path to the slice private key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: path to private key file
        :rtype: String
        """
        if 'slice_private_key_file' in self.slice_key.keys():
            return self.slice_key['slice_private_key_file']
        else:
            return None

    def is_dead_or_closing(self):
        if self.get_state() in ["Closing",
                                "Dead"]:
            return True
        else:
            return False

    def isStable(self) -> bool:
        """
        Tests is the slice is stable. Stable means all requests for
        to add/remove/modify slice resouces have completed.  Both successful
        and failed slice requests are considered to be completed.

        :return: True if slice is stable, False otherwise
        :rtype: Bool
        """
        if self.get_state() in ["StableOK",
                                "StableError",
                                "Closing",
                                "Dead"]:
            return True
        else:
            return False

    def get_state(self) -> str:
        """
        Gets the slice state off of the slice manager slice.

        :return: the slice state
        :rtype: SliceState
        """
        return self.sm_slice.state

    def get_name(self) -> str:
        """
        Gets the slice's name.

        :return: the slice name
        :rtype: String
        """
        return self.slice_name

    def get_slice_id(self) -> str:
        """
        Gets the slice's ID.

        :return: the slice ID
        :rtype: String
        """
        return self.slice_id

    def get_lease_end(self) -> str:
        """
        Gets the timestamp at which the slice lease ends.

        :return: timestamp when lease ends
        :rtype: String
        """
        return self.sm_slice.lease_end_time

    def add_l2network(self, name: str = None, interfaces: List[Interface] = [], type: str = None) -> NetworkService:
        """
        Adds a new L2 network service to this slice.

        L2 networks types include:

        - L2Bridge: a local Ethernet on a single site with unlimited interfaces.
        - L2STS: a wide-area Ethernet on exactly two sites with unlimited interfaces.
            Includes best effort performance and cannot, yet, support Basic NICs
            residing on a single physical.
        - L2PTP: a wide-area Ethernet on exactly two sites with exactly two interfaces.
            QoS performance guarantees (coming soon!). Does not support Basic NICs.
            Traffic arrives with VLAN tag and requires the node OS to configure
            a VLAN interface.

        If the type argument is not set, FABlib will automatically choose the
        L2 network type for you. In most cases the automatic network type is
        the one you want. You can force a specific network type by setting the
        type parameter to "L2Bridge", "L2STS", or "L2PTP".

        An exception will be raised if the set interfaces is not compatible
        with the specified network type or if there is not compatible network
        type for the given interface list.

        :param name: the name of the network service
        :type name: String
        :param interfaces: a list of interfaces to build the network with
        :type interfaces: List[Interface]
        :param type: optional L2 network type "L2Bridge", "L2STS", or "L2PTP"
        :type type: String
        :return: a new L2 network service
        :rtype: NetworkService
        """
        return NetworkService.new_l2network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_l3network(self, name: str = None, interfaces: List[Interface] = [], type: str = 'IPv4') -> NetworkService:
        """
        Adds a new L3 network service to this slice.

        L3 networks types include:

        - IPv4: An IPv4 network on the FABNetv4 internet
        - IPv6: An IPv6 network on the FABNetv6 internet

        The FABNet networks are internal IP internets that span the
        FABRIC testbed.  Adding a new L3 network to your FABRIC slice creates
        an isolated network at a single site.  FABRIC issues each isolated
        L3 network with an IP subnet (either IPv4 or IPv6) and a gateway used
        to route traffic to the FABNet internet.

        Like the public Internet, all FABNet networks can send traffic to all
        other FABnet networks of the same type. In other words, FABNet networks
        can be used to communicate between your slices and slices owned by
        other users.

        An exception will be raised if the set interfaces is not from a single
        FABRIC site.  If you want to use L3 networks to connect slices that
        are distributed across many site, you need to create a separate L3
        network for each site.

        It is important to note that by all nodes come with a default gateway
        on a management network that use used to access your nodes (i.e. to
        accept ssh connections).  To use an L3 dataplane network, you will need
        to add routes to your nodes that selectively route traffic across the
        new dataplane network. You must be careful to maintain the default
        gateway settings if you want to be able to access the node using the
        management network.

        :param name: the name of the network service
        :type name: String
        :param interfaces: a list of interfaces to build the network with
        :type interfaces: List[Interface]
        :param type: L3 network type "IPv4" or "IPv6"
        :type type: String
        :return: a new L3 network service
        :rtype: NetworkService
        """
        return NetworkService.new_l3network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_facility_port(self, name: str = None, site: str = None, vlan: str = None) -> NetworkService:
        """
                Adds a new L2 facility port to this slice

                :param name: name of the facility port
                :type name: String
                :param site: site
                :type site: String
                :param vlan: vlan
                :type vlan: String
                :return: a new L2 facility port
                :rtype: NetworkService
                """
        return FacilityPort.new_facility_port(slice=self, name=name, site=site, vlan=vlan)

    def add_node(self, name: str, site: str = None, cores: int = 2, ram: int = 8, disk: int = 10,
                 image: str = None, instance_type: str = None, docker_image: str = None,
                 host: str = None, avoid: List[str] = []) -> Node:
        """
        Creates a new node on this fablib slice.

        :param name: Name of the new node
        :type name: String
        :param site: (Optional) Name of the site to deploy the node on.
            Default to a random site.
        :type site: String
        :param cores: (Optional) Number of cores in the node. Default: 2 cores
        :type cores: int
        :param ram: (Optional) Amount of ram in the node. Default: 8 GB
        :type ram: int
        :param disk: (Optional) Amount of disk space n the node. Default: 10 GB
        :type disk: int
        :param image: (Optional) The image to uese for the node. Default: default_rocky_8
        :type image: String
        :param instance_type
        :param docker_image
        :param host: (Optional) The physical host to deploy the node. Each site
            has worker nodes numbered 1, 2, 3, etc. Host names follow the pattern
            in this example of STAR worker number 1: "star-w1.fabric-testbed.net".
            Default: unset
        :type host: String
        :param avoid: (Optional) A list of sites to avoid is allowing random site.
        :type avoid: List[String]

        :return: a new node
        :rtype: Node
        """
        node = Node.new_node(slice=self, name=name, site=site, avoid=avoid)

        if instance_type:
            node.set_instance_type(instance_type)
        else:
            node.set_capacities(cores=cores, ram=ram, disk=disk)

        if image:
            node.set_image(image)

        if host:
            node.set_host(host)

        if docker_image:
            node.set_docker_image(docker_image)

        return node

    def get_object_by_reservation(self, reservation_id: str) -> Union[Node, NetworkService, Interface, None]:
        """
        Gets an object associated with this slice by its reservation ID.

        :param reservation_id: the ID to search for
        :return: Object
        """
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

    def get_error_messages(self) -> List[dict]:
        """
        Gets the error messages found in the sliver notices.

        :return: a list of error messages
        :rtype: List[Dict[String, String]]
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

    def get_notices(self) -> Dict[str, str]:
        """
        Gets a dictionary all sliver notices keyed by reservation id.

        :return: dictionary of node IDs to error messages
        :rtype: dict[str, str]
        """
        notices = {}
        for node in self.get_nodes():
            notices[node.get_reservation_id()] = node.get_error_message()

        for network_service in self.get_network_services():
            notices[network_service.get_reservation_id()] = network_service.get_error_message()

        for component in self.get_components():
            notices[component.get_reservation_id()] = component.get_error_message()

        return notices

    def get_components(self) -> List[Component]:
        """
        Gets all components in this slice.

        :return: List of all components in this slice
        :rtype: List[Component]
        """
        return_components = []

        # fails for topology that does not have nodes
        try:
            for node in self.get_nodes():
                for component in node.get_components():
                    return_components.append(component)

        except Exception as e:
            print(f"get_components: exception {e}")
            #traceback.print_exc()
            pass
        return return_components

    def get_nodes(self) -> List[Node]:
        """
        Gets a list of all nodes in this slice.

        :return: a list of fablib nodes
        :rtype: List[Node]
        """
        return_nodes = []

        # fails for topology that does not have nodes
        try:
            for node_name, node in self.get_fim_topology().nodes.items():
                return_nodes.append(Node.get_node(self, node))
        except Exception as e:
            logging.info(f"get_nodes: exception {e}")
            #traceback.print_exc()
            pass
        return return_nodes

    def get_node(self, name: str) -> Node:
        """
        Gets a node from the slice by name.

        :param name: Name of the node
        :type name: String
        :return: a fablib node
        :rtype: Node
        """
        try:
            return Node.get_node(self, self.get_fim_topology().nodes[name])
        except Exception as e:
            logging.info(e, exc_info=True)
            raise Exception(f"Node not found: {name}")

    def get_interfaces(self) -> List[Interface]:
        """
        Gets all interfaces in this slice.

        :return: a list of interfaces on this slice
        :rtype: List[Interface]
        """
        interfaces = []
        for node in self.get_nodes():
            logging.debug(f"Getting interfaces for node {node.get_name()}")
            for interface in node.get_interfaces():
                logging.debug(f"Getting interface {interface.get_name()} for node {node.get_name()}: \n{interface}")
                interfaces.append(interface)
        return interfaces

    def get_interface(self, name: str = None) -> Interface:
        """
        Gets a particular interface from this slice.

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

    def get_l3networks(self) -> List[NetworkService]:
        """
        Gets all L3 networks services in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        try:
            return NetworkService.get_l3network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_l3network(self, name: str = None) -> NetworkService or None:
        """
        Gets a particular L3 network service from this slice.


        :param name: Name network
        :type name: String
        :return: network services on this slice
        :rtype: list[NetworkService]
        """
        try:
            return NetworkService.get_l3network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def get_l2networks(self) -> List[NetworkService]:
        """
        Gets a list of the L2 network services on this slice.

        :return: network services on this slice
        :rtype: list[NetworkService]
        """
        try:
            return NetworkService.get_l2network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_l2network(self, name: str = None) -> NetworkService or None:
        """
        Gets a particular L2 network service from this slice.

        :param name: the name of the network service to search for
        :type name: str
        :return: a particular network service
        :rtype: NetworkService
        """
        try:
            return NetworkService.get_l2network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def get_network_services(self) -> List[NetworkService]:
        """
        Not intended for API use. See: slice.get_networks()

        Gets all network services (L2 and L3) in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        return_networks = []

        # fails for topology that does not have nodes
        try:
            for net_name, net in self.get_fim_topology().network_services.items():
                if str(net.get_property('type')) in NetworkService.get_fim_network_service_types():
                    return_networks.append(NetworkService(slice=self, fim_network_service=net))

        except Exception as e:
            print(f"get_network_services: exception {e}")
            #traceback.print_exc()
            pass
        return return_networks

    def get_networks(self) -> List[NetworkService]:
        """
        Gets all network services (L2 and L3) in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        try:
            return NetworkService.get_network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_network(self, name: str = None) -> NetworkService or None:
        """
        Gest a particular network service from this slice.

        :param name: the name of the network service to search for
        :type name: str
        :return: a particular network service
        :rtype: NetworkService
        """
        try:
            return NetworkService.get_network_service(self, name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def delete(self):
        """
        Deletes this slice off of the slice manager and removes its topology.

        :raises Exception: if deleting the slice fails
        """
        return_status, result = self.fablib_manager.get_slice_manager().delete(slice_object=self.sm_slice)

        if return_status != Status.OK:
            raise Exception("Failed to delete slice: {}, {}".format(return_status, result))

        self.topology = None

    def renew(self, end_date: str):
        """
        Renews the FABRIC slice's lease to the new end date.

        Date is in UTC and of the form: "%Y-%m-%d %H:%M:%S %z"

        Example of formating a date for 1 day from now:

        end_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S %z")


        :param end_date: String
        :raises Exception: if renewal fails
        """
        return_status, result = self.fablib_manager.get_slice_manager().renew(slice_object=self.sm_slice,
                                                                              new_lease_end_time=end_date)

        if return_status != Status.OK:
            raise Exception("Failed to renew slice: {}, {}".format(return_status, result))

    def build_error_exception_string(self) -> str:
        """
        Not intended for API use

        Formats one string with all the error information on this slice's nodes.

        :return: a string with all the error information relevant to this slice
        :rtype: str
        """

        self.update()

        exception_string = f"Slice Exception: Slice Name: {self.get_name()}, Slice ID: {self.get_slice_id()}: "

        for error in self.get_error_messages():
            notice = error['notice']
            sliver = error['sliver']

            sliver_extra = ""
            if isinstance(sliver, Node):
                sliver_extra = f"Node: {sliver.get_name()}, Site: {sliver.get_site()}, " \
                               f"State: {sliver.get_reservation_state()}, "

            # skip errors that are caused by slice error
            if 'Closing reservation due to failure in slice' in notice:
                continue

            exception_string += f"{exception_string}{sliver_extra}{notice}\n"

        return exception_string

    def wait(self, timeout: int = 360, interval: int = 10, progress: bool = False):
        """
        Waits for the slice on the slice manager to be in a stable, running state.

        :param timeout: how many seconds to wait on the slice
        :type timeout: int
        :param interval: how often in seconds to check on slice state
        :type interval: int
        :param progress: indicator for whether to print wait progress
        :type progress: bool
        :raises Exception: if the slice state is undesirable, or waiting times out
        :return: the stable slice on the slice manager
        :rtype: SMSlice
        """
        slice_id = self.sm_slice.slice_id

        timeout_start = time.time()
        slice = self.sm_slice

        if progress:
            print("Waiting for slice .", end='')
        while time.time() < timeout_start + timeout:
            return_status, slices = self.fablib_manager.get_slice_manager().slices(excludes=[], slice_id=self.slice_id,
                                                                                   name=self.slice_name)
            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
                if slice.state == "StableOK":
                    if progress:
                        print(" Slice state: {}".format(slice.state))
                    return slice
                if slice.state == "Closing" or slice.state == "Dead" or slice.state == "StableError":
                    if progress: print(" Slice state: {}".format(slice.state))
                    try:
                        exception_string = self.build_error_exception_string()
                    except Exception as e:
                        exception_string = "Exception while getting error messages"

                    raise Exception(str(exception_string))
            else:
                print(f"Failure: {slices}")

            if progress:
                print(".", end='')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            raise Exception(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout, slice.name, slice.state))

        # Update the fim topology (wait to avoid get topology bug)
        # time.sleep(interval)
        self.update()

    def wait_ssh(self, timeout: int = 360, interval: int = 10, progress: bool = False):
        """
        Waits for all nodes to be accesible via ssh.

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

            if progress: print(".", end = '')

            if time.time() >= timeout_start + timeout:
                if progress:
                    print(f" Timeout exceeded ({timeout} sec). Slice: {slice.name} ({slice.state})")
                raise Exception(f" Timeout exceeded ({timeout} sec). Slice: {slice.name} ({slice.state})")

            time.sleep(interval)
            self.update()

    def test_ssh(self) -> bool:
        """
        Tests all nodes in the slices are accessible via ssh.

        :return: result of testing if all VMs in the slice are accessible via ssh
        :rtype: bool
        """
        for node in self.get_nodes():
            if not node.test_ssh():
                logging.debug(f"test_ssh fail: {node.get_name()}: {node.get_management_ip()}")
                return False
        return True

    def link(self):
        for node in self.get_nodes():
            if node.get_image() in ["rocky", "centos", "fedora"]:
                node.execute("sudo yum install -y -qq docker")

            if node.get_image() in ["ubuntu", "debian"]:
                node.execute("sudo apt-get install -y -q docker.io")

            ip = 6 if isinstance(node.get_management_ip(), ipaddress.IPv6Address) else 4
            node.execute(f"docker run -d -it --name Docker registry.ipv{ip}.docker.com/{node.get_docker_image()}")

            interfaces = [iface["ifname"] for iface in node.get_dataplane_os_interfaces()]
            NSPID = node.execute("docker inspect --format='{{ .State.Pid }}' Docker")[0]

            try:
                if node.get_image() in ["rocky", "centos", "fedora"]: node.execute("sudo yum install -y net-tools")
                if node.get_image() in ["ubuntu", "debian"]: node.execute("sudo apt-get install -y net-tools")
            except Exception as e:
                logging.error(f"Error installing docker on node {node.get_name()}")
                logging.error(e, exc_info=True)

            for iface in interfaces:
                try:
                        node.execute(f'sudo ip link set dev {iface} promisc on')
                        node.execute(f'sudo ip link set {iface} netns {NSPID}')
                        node.execute(f'docker exec Docker ip link set dev {iface} up')
                        node.execute(f'docker exec Docker ip link set dev {iface} promisc on')
                        node.execute(f'docker exec Docker sysctl net.ipv6.conf.{iface}.disable_ipv6=1')
                except Exception as e:
                        logging.error(f"Interface: {iface} failed to link")
                        logging.error("--> Try installing docker or docker.io on container <--")
                        logging.error(e, exc_info=True)
    
    def post_boot_config(self):
        """
        Run post boot configuration.  Typically, this is run automatically during
        a blocking call to submit.

        Only use this method after a non-blocking submit call and only call it
        once.
        """
        if self.is_dead_or_closing():
            print(f"FAILURE: Slice is in {self.get_state()} state; cannot do post boot config")
            return
        executor = ThreadPoolExecutor(10)

        logging.info(f"post_boot_config: slice_name: {self.get_name()}, slice_id {self.get_slice_id()}")

        node_threads = []
        for node in self.get_nodes():
            logging.info(f"Starting thread: {node.get_name()}_network_manager_stop")
            node_thread = executor.submit(node.network_manager_stop)
            node_threads.append(node_thread)
            pass

        for node_thread in node_threads:
            node_thread.result()

        for interface in self.get_interfaces():
            try:
                interface.config_vlan_iface()
            except Exception as e:
                logging.error(f"Interface: {interface.get_name()} failed to config")
                logging.error(e, exc_info=True)

        iface_threads = []
        for interface in self.get_interfaces():
            try:
                iface_threads.append(executor.submit(interface.ip_link_toggle))
            except Exception as e:
                logging.error(f"Interface: {interface.get_name()} failed to toggle")
                logging.error(e, exc_info=True)

        for iface_thread in iface_threads:
            iface_thread.result()

    def validIPAddress(self, IP: str) -> str:
        """
        Not intended as a API call.

        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def wait_jupyter(self, timeout: int = 600, interval: int = 10):
        from IPython.display import clear_output
        import time

        start = time.time()

        count = 0
        while not self.isStable():
            if time.time() > start + timeout:
                raise Exception(f"Timeout {timeout} sec exceeded in Jupyter wait")

            time.sleep(interval)
            self.update()

            #pre-get the strings for quicker screen update
            slice_string = str(self)
            list_nodes_string = self.list_nodes()
            time_string = f"{time.time() - start:.0f} sec"

            # Clear screen
            clear_output(wait=True)

            #Print statuses
            print(f"\n{slice_string}")
            print(f"\nRetry: {count}, Time: {time_string}")
            print(f"\n{list_nodes_string}")

            count += 1

        print(f"\nTime to stable {time.time() - start:.0f} seconds")

        #print("Running wait_ssh ... ", end="")
        #self.wait_ssh()
        #print(f"Time to ssh {time.time() - start:.0f} seconds")

        print("Running post_boot_config ... ", end="")
        self.post_boot_config()
        print(f"Time to post boot config {time.time() - start:.0f} seconds")

        if len(self.get_interfaces()) > 0:
            print(f"\n{self.list_interfaces()}")
            print(f"\nTime to print interfaces {time.time() - start:.0f} seconds")

    def submit(self, wait: bool = True, wait_timeout: int = 600, wait_interval: int = 10, progress: bool = True,
               wait_jupyter: str = "text") -> str:
        """
        Submits a slice request to FABRIC.

        Can be blocking or non-blocking.

        Blocking calls can, optionally,configure timeouts and intervals.

        Blocking calls can, optionally, print progress info.


        :param wait: indicator for whether to wait for the slice's resources to be active
        :param wait_timeout: how many seconds to wait on the slice resources
        :param wait_interval: how often to check on the slice resources
        :param progress: indicator for whether to show progress while waiting
        :param wait_jupyter: Special wait for jupyter notebooks.
        :return: slice_id
        """

        if not wait:
            progress = False

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = self.fablib_manager.get_slice_manager().create(slice_name=self.slice_name,
                                                                                           slice_graph=slice_graph,
                                                                                           ssh_key=self.get_slice_public_key())
        if return_status != Status.OK:
            raise Exception("Failed to submit slice: {}, {}".format(return_status, slice_reservations))

        logging.debug(f'slice_reservations: {slice_reservations}')
        logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
        self.slice_id = slice_reservations[0].slice_id

        time.sleep(1)
        self.update()

        if progress and wait_jupyter == 'text' and self.fablib_manager.is_jupyter_notebook():
            self.wait_jupyter(timeout=wait_timeout, interval=wait_interval)
            return self.slice_id

        if wait:
            self.wait_ssh(timeout=wait_timeout,interval=wait_interval,progress=progress)

            if progress:
                print("Running post boot config ... ",end="")

            self.update()
            self.post_boot_config()

        if progress:
            print("Done!")

        return self.slice_id

    def modify(self, wait: int = True, wait_timeout: int = 600, wait_interval: int = 10, progress: bool = True,
               wait_jupyter: str = "text"):
        """
        Submits a modify slice request to FABRIC.

        Can be blocking or non-blocking.

        Blocking calls can, optionally,configure timeouts and intervals.

        Blocking calls can, optionally, print progress info.


        :param wait: indicator for whether to wait for the slice's resources to be active
        :param wait_timeout: how many seconds to wait on the slice resources
        :param wait_interval: how often to check on the slice resources
        :param progress: indicator for whether to show progress while waiting
        :param wait_jupyter: Special wait for jupyter notebooks.
        """

        if not wait:
            progress = False

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = self.fablib_manager.get_slice_manager().modify(slice_id=self.slice_id,
                                                                                           slice_graph=slice_graph)
        if return_status != Status.OK:
            raise Exception("Failed to submit modify slice: {}, {}".format(return_status, slice_reservations))

        logging.debug(f'slice_reservations: {slice_reservations}')
        logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
        self.slice_id = slice_reservations[0].slice_id

        time.sleep(1)
        self.update()

        if progress and wait_jupyter == 'text' and self.fablib_manager.is_jupyter_notebook():
            self.wait_jupyter(timeout=wait_timeout, interval=wait_interval)
            return self.slice_id

        if wait:
            self.wait_ssh(timeout=wait_timeout,interval=wait_interval,progress=progress)

            if progress:
                print("Running post boot config ... ",end="")

            self.update()
            self.post_boot_config()

        if progress:
            print("Done!")

    def modify_accept(self):
        """
        Submits a accept to accept the last modify slice request to FABRIC.
        """
        # Request slice from Orchestrator
        return_status, topology = self.fablib_manager.get_slice_manager().modify_accept(slice_id=self.slice_id)
        if return_status != Status.OK:
            raise Exception("Failed to accept the last modify slice: {}, {}".format(return_status, topology))
        else:
            self.topology = topology

        logging.debug(f'modified topology: {topology}')

        self.update_slice()
