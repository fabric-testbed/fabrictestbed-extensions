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
import ipaddress

import time
import logging
from tabulate import tabulate

from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from typing import List

from fabrictestbed.slice_editor import ExperimentTopology
from fabrictestbed.slice_manager import Status, SliceState


from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.interface import Interface


class Slice:

    def __init__(self, name=None):
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

        self.slice_key = fablib.get_default_slice_key()

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the slice.

        Intended for printing slice information.

        :return: Tabulated string of slice information
        :rtype: String
        """
        table = [["Slice Name", self.sm_slice.slice_name],
                 ["Slice ID", self.sm_slice.slice_id],
                 ["Slice State", self.sm_slice.slice_state],
                 ["Lease End", self.sm_slice.lease_end]
                ]

        return tabulate(table)

    def list_nodes(self):
        """
        Creates a tabulated string describing all nodes in the slice.

        Intended for printing a list of all slices.

        :return: Tabulated srting of all slices information
        :rtype: String
        """
        table = []
        for node in self.get_nodes():

            table.append( [     node.get_reservation_id(),
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
                                ] )

        return tabulate(table, headers=["ID", "Name",  "Site",  "Host", "Cores", "RAM", "Disk", "Image",
                                        "Management IP", "State", "Error"])

    def list_interfaces(self):
        """
        Creates a tabulated string describing all interfaces in the slice.

        Intended to print a list of all interfaces.

        :return: Tabulated string of all interfaces
        :rtype: String
        """
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

        return tabulate(table, headers=["Name", "Node", "Network", "Bandwidth", "VLAN", "MAC",
                                        "Physical OS Interface", "OS Interface"])

    @staticmethod
    def new_slice(name=None):
        """
        Create a new slice

        :param name: slice name
        :type name: String
        :return: fablib slice
        :rtype: Slice
        """

        slice = Slice(name=name)
        slice.topology = ExperimentTopology()
        return slice

    @staticmethod
    def get_slice(sm_slice=None, load_config=True):
        """
        Not intended for API use.

        Gets an existing fablib slice using a slice manager slice

        :param sm_slice: the slice on the slice manager
        :type sm_slice: SMSlice
        :param verbose: indicator for verbose output
        :type verbose: bool
        :param load_config: indicator for whether to load the FABRIC slice configuration
        :type load_config: bool
        :return: fablib slice
        :rtype: Slice
        """
        logging.info("slice.get_slice()")

        slice = Slice(name=sm_slice.slice_name)
        slice.sm_slice = sm_slice
        slice.slice_id = sm_slice.slice_id
        slice.slice_name = sm_slice.slice_name

        slice.topology = fablib.get_slice_manager().get_slice_topology(slice_object=slice.sm_slice)

        try:
            slice.update()
        except Exception as e:
            logging.error(f"Slice {slice.slice_name} could not be updated: slice.get_slice")
            logging.error(e, exc_info=True)

        if load_config:
            try:
                slice.load_config()
            except Exception as e:
                logging.error(f"Slice {slice.slice_name} config could not loaded: slice.get_slice")
                logging.error(e, exc_info=True)
        return slice

    def get_fim_topology(self):
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

        :param verbose: indicator for verbose output
        :type verbose: bool
        :raises Exception: if slice manager slice no longer exists
        """
        import time
        if fablib.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = fablib.get_slice_manager().slices(excludes=[])
        if fablib.get_log_level() == logging.DEBUG:
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


        Updates the fabric slice topology with the slice manager slice's topolofy

        :raises Exception: if topology could not be gotten from slice manager
        """
        #Update topology
        return_status, new_topo = fablib.get_slice_manager().get_slice_topology(slice_object=self.sm_slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slice topology: {}, {}".format(return_status, new_topo))

        #Set slice attibutes
        self.topology = new_topo

    def update_slivers(self):
        """
        Not recommended for most users.  See Slice.update() method.

        Updates the slivers with the current slice manager.

        :raises Exception: if topology could not be gotten from slice manager
        """
        status, slivers = fablib.get_slice_manager().slivers(slice_object=self.sm_slice)
        if status == Status.OK:
            self.slivers = slivers
            return

        raise Exception(f"{slivers}")

    def get_sliver(self, reservation_id):
        slivers = self.get_slivers()
        sliver = list(filter(lambda x: x.reservation_id == reservation_id, slivers ))[0]
        return sliver

    def get_slivers(self):
        if not hasattr(self, 'slivers') or not self.slivers:
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

    def get_private_key_passphrase(self):
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

    def get_slice_public_key(self):
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

    def get_slice_public_key_file(self):
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

    def get_slice_private_key_file(self):
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

    def isStable(self):
        """
        Tests is the slice is stable. Stable means all requests for
        to add/remove/modify slice resouces have completed.  Both successful
        and failed slice requests are considered to be completed.

        :return: True if slice is stable, False otherwise
        :rtype: Bool
        """
        if self.get_state() in [ "StableOK",
                                 "StableError",
                                 "Closing",
                                 "Dead"]:
            return True
        else:
            return False

    def get_state(self):
        """
        Gets the slice state off of the slice manager slice.

        :return: the slice state
        :rtype: SliceState
        """
        return self.sm_slice.slice_state

    def get_name(self):
        """
        Gets the slice's name.

        :return: the slice name
        :rtype: String
        """
        return self.slice_name

    def get_slice_id(self):
        """
        Gets the slice's ID.

        :return: the slice ID
        :rtype: String
        """
        return self.slice_id

    def get_lease_end(self):
        """
        Gets the timestamp at which the slice lease ends.

        :return: timestamp when lease ends
        :rtype: String
        """
        return self.sm_slice.lease_end

    def add_l2network(self, name=None, interfaces=[], type=None):
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
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        return NetworkService.new_l2network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_l3network(self, name=None, interfaces=[], type='IPv4'):
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
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        return NetworkService.new_l3network(slice=self, name=name, interfaces=interfaces, type=type)

    def add_node(self, name, site=None, cores=2, ram=8, disk=10, image=None, docker_image=None, host=None, avoid=[]):
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
        from fabrictestbed_extensions.fablib.node import Node
        node = Node.new_node(slice=self, name=name, site=site, avoid=avoid)
        node.set_capacities(cores=cores, ram=ram, disk=disk)

        if image:
            node.set_image(image)

        if host:
            node.set_host(host)

        if docker_image:
            node.set_docker_image(docker_image)

        return node

    def get_object_by_reservation(self, reservation_id):
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

    def get_error_messages(self):
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

    def get_notices(self):
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

    def get_components(self):
        """
        Gets all components in this slice.

        :return: List of all components in this slice
        :rtype: List[Component]
        """
        from fabrictestbed_extensions.fablib.component import Component
        #self.update()

        return_components = []

        #fails for topology that does not have nodes
        try:
            for node in self.get_nodes():
                for component in node.get_components():
                    return_components.append(component)

        except Exception as e:
            print(f"get_components: exception {e}")
            #traceback.print_exc()
            pass
        return return_components

    def get_nodes(self):
        """
        Gets a list of all nodes in this slice.

        :return: a list of fablib nodes
        :rtype: List[Node]
        """
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()

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

    def get_node(self, name):
        """
        Gets a node from the slice by name.

        :param name: Name of the node
        :type name: String
        :return: a fablib node
        :rtype: Node
        """
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()
        try:
            return Node.get_node(self, self.get_fim_topology().nodes[name])
        except Exception as e:
            logging.info(e, exc_info=True)
            raise Exception(f"Node not found: {name}")

    def get_interfaces(self):
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

    def get_interface(self, name=None):
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

    def get_l3networks(self):
        """
        Gets all L3 networks services in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l3network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_l3network(self, name=None):
        """
        Gets a particular L3 network service from this slice.


        :param name: Name network
        :type name: String
        :return: network services on this slice
        :rtype: list[NetworkService]
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l3network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None

    def get_l2networks(self):
        """
        Gets a list of the L2 network services on this slice.

        :return: network services on this slice
        :rtype: list[NetworkService]
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_l2network(self, name=None):
        """
        Gets a particular L2 network service from this slice.

        :param name: the name of the network service to search for
        :type name: str
        :return: a particular network service
        :rtype: NetworkService
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
        return None


    def get_network_services(self):
        """
        Not intended for API use. See: slice.get_networks()

        Gets all network services (L2 and L3) in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        #self.update()

        return_networks = []

        #fails for topology that does not have nodes
        try:
            for net_name, net in self.get_fim_topology().network_services.items():
                if str(net.get_property('type')) in NetworkService.fim_network_service_types:
                    return_networks.append(NetworkService(slice = self, fim_network_service = net))

        except Exception as e:
            print(f"get_network_services: exception {e}")
            #traceback.print_exc()
            pass
        return return_networks

    def get_networks(self):
        """
        Gets all network services (L2 and L3) in this slice

        :return: List of all network services in this slice
        :rtype: List[NetworkService]
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_network_services(self)
        except Exception as e:
            logging.info(e, exc_info=True)

        return []

    def get_network(self, name=None):
        """
        Gest a particular network service from this slice.

        :param name: the name of the network service to search for
        :type name: str
        :return: a particular network service
        :rtype: NetworkService
        """
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_network_service(self,name)
        except Exception as e:
            logging.info(e, exc_info=True)
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

        Date is of the form: "%Y-%m-%d %H:%M:%S"

        Example of formating a date for 1 day from now:

        end_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")


        :param end_date: String
        :raises Exception: if renewal fails
        """
        return_status, result = fablib.get_slice_manager().renew(slice_object=self.sm_slice,
                                                                 new_lease_end_time=end_date)

        if return_status != Status.OK:
            raise Exception("Failed to renew slice: {}, {}".format(return_status, result))

    def build_error_exception_string(self):
        """
        Not intended for API use

        Formats one string with all the error information on this slice's nodes.

        :return: a string with all the error information relevant to this slice
        :rtype: str
        """

        self.update()

        exception_string =  f"Slice Exception: Slice Name: {self.get_name()}, Slice ID: {self.get_slice_id()}: "

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

    def wait(self, timeout=360, interval=10, progress=False):
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
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    try:
                        exception_string = self.build_error_exception_string()
                    except Exception as e:
                        exception_string = "Exception while getting error messages"
                        #traceback.print_exc()

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
        """
        Not intended for API use. Will change as the testbed funtionallity
        developes.

        Gets the map of OS interfaces to networks.

        :return: true when slice ssh successful
        :rtype: Dict
        """
        # TODO: Add docstring after doc networking classes
        if not hasattr(self, 'network_iface_map') or self.network_iface_map == None:
            logging.debug(f'Slice {self.get_name()}, loading interface map')
            self.load_interface_map()
        else:
            logging.debug(f'Slice {self.get_name()}, NOT loading interface map')

        return self.network_iface_map

    def wait_ssh(self, timeout=360, interval=10, progress=False):
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
        slice_name=self.sm_slice.slice_name
        slice_id=self.sm_slice.slice_id

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
                    print(f" Timeout exceeded ({timeout} sec). Slice: {slice.slice_name} ({slice.slice_state})")
                raise Exception(f" Timeout exceeded ({timeout} sec). Slice: {slice.slice_name} ({slice.slice_state})")

            time.sleep(interval)
            self.update()

    def test_ssh(self):
        """
        Tests all nodes in the slices are accessible via ssh.

        :return: indicator for whether or not all nodes were ssh-able
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
        # TODO: Add docstring after doc networking classes
        logging.info(f"post_boot_config: slice_name: {self.get_name()}, slice_id {self.get_slice_id()}")

        for node in self.get_nodes():
            #logging.info(f"Stopping NetworkManager on node {node.get_name()}")"
            stdout, stderr = node.execute(f"sudo systemctl stop NetworkManager")
            logging.info(f"Stopped NetworkManager with 'sudo systemctl stop NetworkManager': stdout: {stdout}\nstderr: {stderr}")
            pass

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

        #for node in self.get_nodes(): link(node)

    def load_config(self):
        """
        Not intended as a API call.

        Loads the slice configuration.
        """
        self.load_interface_map()

    def load_interface_map(self):
        """
        Not intended as a API call.

        Generates an empty network interface map.
        """
        self.network_iface_map = {}
        for net in self.get_networks():
            self.network_iface_map[net.get_name()] = {}

        for node in self.get_nodes():
            node.load_data()

    def validIPAddress(self, IP: str):
        """
        Not intended as a API call.

        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def build_interface_map(self):
        """
        Not intended as a API call.

        """
        # TODO: Add docstring after doc networking classes
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

    def wait_jupyter(self, timeout=600, interval=10):
        from IPython.display import clear_output
        import time
        import random

        start = time.time()

        count = 0
        while not self.isStable():
            if time.time() > start + timeout:
                raise Exception(f"Timeout {timeout} sec exceeded in Jupyter wait")

            time.sleep(interval)
            self.update()
            node_list = self.list_nodes()

            #pre-get the strings for quicker screen update
            slice_string=str(self)
            list_nodes_string=self.list_nodes()
            time_string = f"{time.time() - start:.0f} sec"

            # Clear screen
            clear_output(wait=True)

            #Print statuses
            print(f"\n{slice_string}")
            print(f"\nRetry: {count}, Time: {time_string}")
            print(f"\n{list_nodes_string}")

            count += 1

        print(f"\nTime to stable {time.time() - start:.0f} seconds")

        print("Running wait_ssh ... ", end="")
        self.wait_ssh()
        print(f"Time to ssh {time.time() - start:.0f} seconds")

        print("Running post_boot_config ... ", end="")
        self.post_boot_config()
        print(f"Time to post boot config {time.time() - start:.0f} seconds")

        if len(self.get_interfaces()) > 0:
            print(f"\n{self.list_interfaces()}")

    def submit(self, wait=True, wait_timeout=600, wait_interval=10, progress=True, wait_jupyter="text"):
        """
        Submits a slice request to FABRIC.

        Can be blocking or non-blocking.

        Blocking calls can, optionally,configure timeouts and intervals.

        Blocking calls can, optionally, print progess info.


        :param wait: indicator for whether to wait for the slice's resources to be active
        :type wait: bool
        :param wait_timeout: how many seconds to wait on the slice resources
        :type wait_timeout: int
        :param wait_interval: how often to check on the slice resources
        :type wait_interval: int
        :param progress: indicator for whether to show progress while waiting
        :type progress: bool
        :param wait_jupyter: Sepecial wait for jupyter notebooks.
        :type wait_jupyter: Sring
        :return: slice_id
        :rtype: String
        """
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

        if progress and wait_jupyter == 'text' and fablib.isJupyterNotebook():
            self.wait_jupyter(timeout=wait_timeout, interval=wait_interval)
            return self.slice_id

        if wait:
            self.wait_ssh(timeout=wait_timeout,interval=wait_interval,progress=progress)

            if progress:
                print("Running post boot config ... ",end="")

            self.update()
            self.test_ssh()
            self.post_boot_config()

        if progress:
            print("Done!")

        return self.slice_id
