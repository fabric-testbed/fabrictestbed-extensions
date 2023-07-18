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
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pandas as pd
from IPython.core.display_functions import display

from fabrictestbed_extensions.fablib.facility_port import FacilityPort

if TYPE_CHECKING:
    from fabric_cf.orchestrator.swagger_client import (
        Slice as OrchestratorSlice,
        Sliver as OrchestratorSliver,
    )
    from fabrictestbed_extensions.fablib.fablib import FablibManager

import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Address, ip_address
from typing import Dict, List, Union

from fabrictestbed.slice_editor import ExperimentTopology
from fabrictestbed.slice_manager import SliceState, Status
from tabulate import tabulate

from fabrictestbed_extensions.fablib.component import Component
from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.node import Node


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

        self.nodes = None
        self.interfaces = None

        self.slice_key = fablib_manager.get_default_slice_key()

        self.update_topology_count = 0
        self.update_slivers_count = 0
        self.update_slice_count = 0
        self.update_count = 0

    def get_fablib_manager(self):
        return self.fablib_manager

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the slice.

        Intended for printing slice information.

        :return: Tabulated string of slice information
        :rtype: String
        """
        table = [
            ["Slice Name", self.sm_slice.name],
            ["Slice ID", self.sm_slice.slice_id],
            ["Slice State", self.sm_slice.state],
            ["Lease End", self.sm_slice.lease_end_time],
        ]

        return tabulate(table)

    def save(self, filename):
        """
        Saves the slice topology to a file. The file can be loaded to create
        a new slice with the same topology.

        The slice topology can be saved before the original request has been submitted
        or after. If the slice is saved after it is instantiated, only the topology is
        saved.  Any configuration of nodes is not included.

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

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Show a table containing the current slice attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['Name','State']

        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param colors: True to specify state colors for pandas output
        :type colors: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        data = self.toDict()

        def state_color(val):
            if val == "StableOK":
                color = f"{self.get_fablib_manager().SUCCESS_LIGHT_COLOR}"
            elif val == "ModifyOK":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            elif val == "StableError":
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            elif val == "ModifyError":
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            elif val == "Configuring":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            elif val == "Modifying":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            else:
                color = ""
            return "background-color: %s" % color

        if pretty_names:
            pretty_names_dict = self.get_pretty_names_dict()
        else:
            pretty_names_dict = {}

        if colors and self.get_fablib_manager().is_jupyter_notebook():
            slice_table = self.get_fablib_manager().show_table(
                data,
                fields=fields,
                title="Slice",
                output="pandas",
                quiet=True,
                pretty_names_dict=pretty_names_dict,
            )
            slice_table.applymap(state_color)

            if quiet == False:
                display(slice_table)
        else:
            slice_table = self.get_fablib_manager().show_table(
                data,
                fields=fields,
                title="Slice",
                output=output,
                quiet=quiet,
                pretty_names_dict=pretty_names_dict,
            )

        return slice_table

    def list_components(
        self,
        output: str = None,
        fields: List[str] = None,
        quiet: bool = False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the components in the slice with their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','Model']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['Model'] == 'NIC_Basic'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :return: table in format specified by output parameter
        :rtype: Object
        """
        table = []
        for component in self.get_components():
            table.append(component.toDict())

        # if fields == None:
        #    fields = ["Name", "Details", "Disk",
        #              "Units", "PCI Address", "Model",
        #              "Type"]

        if pretty_names:
            pretty_names_dict = Component.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        table = self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Components",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

        return table

    def list_interfaces(
        self,
        output: str = None,
        fields: List[str] = None,
        quiet: bool = False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the interfaces in the slice with their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','Type', 'State']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['Type'] == 'FABNetv4'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :return: table in format specified by output parameter
        :rtype: Object
        """
        executor = ThreadPoolExecutor(64)

        net_name_threads = {}
        node_name_threads = {}
        physical_os_interface_name_threads = {}
        os_interface_threads = {}
        for iface in self.get_interfaces():
            if iface.get_network():
                logging.info(
                    f"Starting get network name thread for iface {iface.get_name()} "
                )
                net_name_threads[iface.get_name()] = executor.submit(
                    iface.get_network().get_name
                )

            if iface.get_node():
                logging.info(
                    f"Starting get node name thread for iface {iface.get_name()} "
                )
                node_name_threads[iface.get_name()] = executor.submit(
                    iface.get_node().get_name
                )

            logging.info(
                f"Starting get physical_os_interface_name_threads for iface {iface.get_name()} "
            )
            physical_os_interface_name_threads[iface.get_name()] = executor.submit(
                iface.get_physical_os_interface_name
            )

            logging.info(
                f"Starting get get_os_interface_threads for iface {iface.get_name()} "
            )
            os_interface_threads[iface.get_name()] = executor.submit(
                iface.get_device_name
            )

        table = []
        for iface in self.get_interfaces():
            if iface.get_network():
                # network_name = iface.get_network().get_name()
                logging.info(
                    f"Getting results from get network name thread for iface {iface.get_name()} "
                )
                network_name = net_name_threads[iface.get_name()].result()
            else:
                network_name = None

            if iface.get_node():
                # node_name = iface.get_node().get_name()
                logging.info(
                    f"Getting results from get node name thread for iface {iface.get_name()} "
                )
                node_name = node_name_threads[iface.get_name()].result()

            else:
                node_name = None

            table.append(iface.toDict())
            # table.append({"Name": iface.get_name(),
            #              "Node": node_name,
            #              "Network": network_name,
            #              "Bandwidth": iface.get_bandwidth(),
            #              "VLAN": iface.get_vlan(),
            #              "MAC": iface.get_mac(),
            #              "Physical Device": physical_os_interface_name_threads[iface.get_name()].result(),
            #              "Device": os_interface_threads[iface.get_name()].result(),
            #              })

        # if fields == None:
        #    fields = ["Name", "Node", "Network",
        #              "Bandwidth", "VLAN", "MAC",
        #              "Device"]
        if pretty_names:
            pretty_names_dict = Interface.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        table = self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Interfaces",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

        return table

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
            logging.error(
                f"Slice {slice.slice_name} could not update topology: slice.get_slice"
            )
            logging.error(e, exc_info=True)

        try:
            slice.update_slivers()
        except Exception as e:
            logging.error(
                f"Slice {slice.slice_name} could not update slivers: slice.get_slice"
            )
            logging.error(e, exc_info=True)

        return slice

    def toJson(self):
        """
        Returns the slice attributes as a json string

        :return: slice attributes as json string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_names_dict():
        return {
            "id": "ID",
            "name": "Name",
            "lease_end": "Lease Expiration (UTC)",
            "lease_start": "Lease Start (UTC)",
            "project_id": "Project ID",
            "state": "State",
        }

    def toDict(self, skip=[]):
        """
        Returns the slice attributes as a dictionary

        :return: slice attributes as dictionary
        :rtype: dict
        """
        return {
            "id": str(self.get_slice_id()),
            "name": str(self.get_name()),
            "lease_end": str(self.get_lease_end()),
            "lease_start": str(self.get_lease_start()),
            "project_id": str(self.get_project_id()),
            "state": str(self.get_state()),
        }

    def get_template_context(self, base_object=None, skip=[]):
        context = {}

        if base_object:
            context["_self_"] = base_object.generate_template_context()
        else:
            context["_self_"] = {}

        context["config"] = self.get_fablib_manager().get_config()
        context["slice"] = self.toDict()

        context["nodes"] = {}
        for node in self.get_nodes():
            node_context = node.generate_template_context()
            context["nodes"][node.get_name()] = node_context

        context["components"] = {}
        for component in self.get_components():
            context["components"][
                component.get_name()
            ] = component.generate_template_context()

        context["interfaces"] = {}
        for interface in self.get_interfaces():
            context["interfaces"][interface.get_name()] = interface.toDict()

        context["networks"] = {}
        for network in self.get_networks():
            context["networks"][
                network.get_name()
            ] = network.generate_template_context()

        return context

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
        Not recommended for most users.  See Slice.update() method.

        Updates this slice manager slice to store the most up-to-date
        slice manager slice

        :raises Exception: if slice manager slice no longer exists
        """
        self.update_slice_count += 1
        logging.info(
            f"update_slice: {self.get_name()}, count: {self.update_slice_count}"
        )

        if self.fablib_manager.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = self.fablib_manager.get_slice_manager().slices(
            excludes=[], slice_id=self.slice_id, name=self.slice_name
        )
        if self.fablib_manager.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(
                f"Running slice.update_slice() : fablib.get_slice_manager().slices(): "
                f"elapsed time: {end - start} seconds"
            )

        if return_status == Status.OK:
            self.sm_slice = list(filter(lambda x: x.slice_id == self.slice_id, slices))[
                0
            ]
        else:
            raise Exception(
                "Failed to get slice list: {}, {}".format(return_status, slices)
            )

    def update_topology(self):
        """
        Not recommended for most users.  See Slice.update() method.

        Updates the fabric slice topology with the slice manager slice's topology

        :raises Exception: if topology could not be gotten from slice manager
        """
        self.update_topology_count += 1
        logging.info(
            f"update_topology: {self.get_name()}, count: {self.update_topology_count}"
        )

        # Update topology
        if self.sm_slice.model is not None and self.sm_slice.model != "":
            self.topology = ExperimentTopology()
            self.topology.load(graph_string=self.sm_slice.model)
            return

        (
            return_status,
            new_topo,
        ) = self.fablib_manager.get_slice_manager().get_slice_topology(
            slice_object=self.sm_slice
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to get slice topology: {}, {}".format(return_status, new_topo)
            )

        # Set slice attibutes
        self.topology = new_topo

    def update_slivers(self):
        """
        Not recommended for most users.  See Slice.update() method.

        Updates the slivers with the current slice manager.

        :raises Exception: if topology could not be gotten from slice manager
        """
        self.update_slivers_count += 1
        logging.debug(
            f"update_slivers: {self.get_name()}, count: {self.update_slivers_count}"
        )

        if self.sm_slice is None:
            return
        status, slivers = self.fablib_manager.get_slice_manager().slivers(
            slice_object=self.sm_slice
        )
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
            logging.debug(f"get_slivers", stack_info=False)
            self.update_slivers()

        return self.slivers

    def update(self):
        """
        (re)Query the FABRIC services for updated information about this slice.

        :raises Exception: if updating topology fails
        """
        self.update_count += 1
        logging.info(f"update : {self.get_name()}, count: {self.update_count}")

        try:
            self.update_slice()
        except Exception as e:
            logging.warning(f"slice.update_slice failed: {e}")

        try:
            self.update_slivers()
        except Exception as e:
            logging.warning(f"slice.update_slivers failed: {e}")

        self.nodes = None
        self.interfaces = None
        self.update_topology()

        if self.get_state() == "ModifyOK":
            self.modify_accept()

    def get_private_key_passphrase(self) -> str:
        """
        Gets the slice private key passphrase.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the private key passphrase
        :rtype: String
        """
        if "slice_private_key_passphrase" in self.slice_key.keys():
            return self.slice_key["slice_private_key_passphrase"]
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
        if "slice_public_key" in self.slice_key.keys():
            return self.slice_key["slice_public_key"]
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
        if "slice_public_key_file" in self.slice_key.keys():
            return self.slice_key["slice_public_key_file"]
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
        if "slice_private_key_file" in self.slice_key.keys():
            return self.slice_key["slice_private_key_file"]
        else:
            return None

    def is_dead_or_closing(self):
        if self.get_state() in ["Closing", "Dead"]:
            return True
        else:
            return False

    def isStable(self) -> bool:
        """
        Tests is the slice is stable. Stable means all requests for
        to add/remove/modify slice resources have completed.  Both successful
        and failed slice requests are considered to be completed.

        :return: True if slice is stable, False otherwise
        :rtype: Bool
        """
        if self.get_state() in [
            "StableOK",
            "StableError",
            "ModifyOK",
            "ModifyError",
            "Closing",
            "Dead",
        ]:
            return True
        else:
            return False

    def get_state(self) -> str:
        """
        Gets the slice state.

        :return: the slice state
        :rtype: str
        """

        if self.sm_slice == None:
            state = None
        else:
            try:
                state = self.sm_slice.state
            except Exception as e:
                logging.warning(
                    f"Exception in get_state from non-None sm_slice. Returning None state: {e}"
                )
                state = None

        return state

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

        if self.sm_slice == None:
            lease_end_time = None
        else:
            try:
                lease_end_time = self.sm_slice.lease_end_time
            except Exception as e:
                logging.warning(
                    f"Exception in get_lease_end from non-None sm_slice. Returning None state: {e}"
                )
                lease_end_time = None

        return lease_end_time

    def get_lease_start(self) -> str:
        """
        Gets the timestamp at which the slice lease starts.

        :return: timestamp when lease starts
        :rtype: String
        """

        if self.sm_slice == None:
            lease_start_time = None
        else:
            try:
                lease_start_time = self.sm_slice.lease_start_time
            except Exception as e:
                logging.warning(
                    f"Exception in get_lease_start from non-None sm_slice. Returning None state: {e}"
                )
                lease_start_time = None

        return lease_start_time

    def get_project_id(self) -> str:
        """
        Gets the project id of the slice.

        :return: project id
        :rtype: String
        """
        return self.sm_slice.project_id

    def add_l2network(
        self,
        name: str = None,
        interfaces: List[Interface] = [],
        type: str = None,
        subnet: ipaddress = None,
        gateway: ipaddress = None,
        user_data: dict = {},
    ) -> NetworkService:
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
        self.nodes = None
        self.interfaces = None

        network_service = NetworkService.new_l2network(
            slice=self, name=name, interfaces=interfaces, type=type, user_data=user_data
        )
        if subnet:
            network_service.set_subnet(subnet)

        if gateway:
            network_service.set_gateway(gateway)
        return network_service

    def add_l3network(
        self,
        name: str = None,
        interfaces: List[Interface] = [],
        type: str = "IPv4",
        user_data: dict = {},
    ) -> NetworkService:
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
        self.nodes = None
        self.interfaces = None

        return NetworkService.new_l3network(
            slice=self,
            name=name,
            interfaces=interfaces,
            type=type,
            user_data=user_data,
        )

    def add_facility_port(
        self, name: str = None, site: str = None, vlan: str = None
    ) -> NetworkService:
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
        return FacilityPort.new_facility_port(
            slice=self, name=name, site=site, vlan=vlan
        )

    def add_node(
        self,
        name: str,
        site: str = None,
        cores: int = 2,
        ram: int = 8,
        disk: int = 10,
        image: str = None,
        instance_type: str = None,
        host: str = None,
        user_data: dict = {},
        avoid: List[str] = [],
    ) -> Node:
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

        node.init_fablib_data()

        user_data_working = node.get_user_data()
        for k, v in user_data.items():
            user_data_working[k] = v
        node.set_user_data(user_data_working)

        if instance_type:
            node.set_instance_type(instance_type)
        else:
            node.set_capacities(cores=cores, ram=ram, disk=disk)

        if image:
            node.set_image(image)

        if host:
            node.set_host(host)

        self.nodes = None
        self.interfaces = None

        return node

    def get_object_by_reservation(
        self, reservation_id: str
    ) -> Union[Node, NetworkService, Interface, None]:
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
        # strings to ignore
        cascade_notice_string1 = "Closing reservation due to failure in slice"
        cascade_notice_string2 = "is in a terminal state"

        origin_notices = []
        for reservation_id, notice in self.get_notices().items():
            if cascade_notice_string1 in notice or cascade_notice_string2 in notice:
                continue

            origin_notices.append(
                {
                    "reservation_id": reservation_id,
                    "notice": notice,
                    "sliver": self.get_object_by_reservation(reservation_id),
                }
            )

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
            notices[
                network_service.get_reservation_id()
            ] = network_service.get_error_message()

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
            logging.error(f"get_components: error {e}", exc_info=True)
            # traceback.print_exc()
            pass
        return return_components

    def get_nodes(self) -> List[Node]:
        """
        Gets a list of all nodes in this slice.

        :return: a list of fablib nodes
        :rtype: List[Node]
        """

        if not self.nodes:
            self.nodes = []
            # fails for topology that does not have nodes
            try:
                for node_name, node in self.get_fim_topology().nodes.items():
                    self.nodes.append(Node.get_node(self, node))
            except Exception as e:
                logging.info(f"get_nodes: exception {e}")
                pass

        return self.nodes

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
        if not self.interfaces:
            self.interfaces = []
            for node in self.get_nodes():
                logging.debug(f"Getting interfaces for node {node.get_name()}")
                for interface in node.get_interfaces():
                    logging.debug(
                        f"Getting interface {interface.get_name()} for node {node.get_name()}: \n{interface}"
                    )
                    self.interfaces.append(interface)
        return self.interfaces

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
            return NetworkService.get_l3network_service(self, name)
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
            return NetworkService.get_l2network_service(self, name)
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
                if (
                    str(net.get_property("type"))
                    in NetworkService.get_fim_network_service_types()
                ):
                    return_networks.append(
                        NetworkService(slice=self, fim_network_service=net)
                    )

        except Exception as e:
            logging.error(e, exc_info=True)
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
        return_status, result = self.fablib_manager.get_slice_manager().delete(
            slice_object=self.sm_slice
        )

        if return_status != Status.OK:
            raise Exception(
                "Failed to delete slice: {}, {}".format(return_status, result)
            )

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
        return_status, result = self.fablib_manager.get_slice_manager().renew(
            slice_object=self.sm_slice, new_lease_end_time=end_date
        )

        if return_status != Status.OK:
            raise Exception(
                "Failed to renew slice: {}, {}".format(return_status, result)
            )

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
            notice = error["notice"]
            sliver = error["sliver"]

            sliver_extra = ""
            if isinstance(sliver, Node):
                sliver_extra = (
                    f"Node: {sliver.get_name()}, Site: {sliver.get_site()}, "
                    f"State: {sliver.get_reservation_state()}, "
                )

            # skip errors that are caused by slice error
            if "Closing reservation due to failure in slice" in notice:
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
            print("Waiting for slice .", end="")
        while time.time() < timeout_start + timeout:
            return_status, slices = self.fablib_manager.get_slice_manager().slices(
                excludes=[], slice_id=self.slice_id, name=self.slice_name
            )
            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
                if slice.state == "StableOK" or slice.state == "ModifyOK":
                    if progress:
                        print(" Slice state: {}".format(slice.state))
                    return slice
                if (
                    slice.state == "Closing"
                    or slice.state == "Dead"
                    or slice.state == "StableError"
                    or slice.state == "ModifyError"
                ):
                    if progress:
                        print(" Slice state: {}".format(slice.state))
                    try:
                        exception_string = self.build_error_exception_string()
                    except Exception as e:
                        exception_string = "Exception while getting error messages"

                    raise Exception(str(exception_string))
            else:
                print(f"Failure: {slices}")

            if progress:
                print(".", end="")
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            raise Exception(
                " Timeout exceeded ({} sec). Slice: {} ({})".format(
                    timeout, slice.name, slice.state
                )
            )

        # Update the fim topology (wait to avoid get topology bug)
        # time.sleep(interval)
        self.update()

    def wait_ssh(self, timeout: int = 1800, interval: int = 20, progress: bool = False):
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
        self.wait(timeout=timeout, interval=interval, progress=progress)

        # Test ssh
        if progress:
            print("Waiting for ssh in slice .", end="")
        while time.time() < timeout_start + timeout:
            try:
                if self.test_ssh():
                    if progress:
                        print(" ssh successful")
                    return True

                if progress:
                    print(".", end="")

                if time.time() >= timeout_start + timeout:
                    if progress:
                        print(
                            f" Timeout exceeded ({timeout} sec). Slice: {slice.name} ({slice.state})"
                        )
                    raise Exception(
                        f" Timeout exceeded ({timeout} sec). Slice: {slice.name} ({slice.state})"
                    )
            except Exception as e:
                if not time.time() < timeout_start + timeout:
                    raise e
                logging.warning(f"wait ssh retrying: {e}")

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
                logging.debug(
                    f"test_ssh fail: {node.get_name()}: {node.get_management_ip()}"
                )
                return False
        return True

    def post_boot_config(self):
        """
        Run post boot configuration.  Typically, this is run automatically during
        a blocking call to submit.

        Only use this method after a non-blocking submit call and only call it
        once.
        """
        if self.is_dead_or_closing():
            print(
                f"FAILURE: Slice is in {self.get_state()} state; cannot do post boot config"
            )
            return

        logging.info(
            f"post_boot_config: slice_name: {self.get_name()}, slice_id {self.get_slice_id()}"
        )

        # node_threads = []
        # for node in self.get_nodes():
        #    logging.info(f"Starting thread: {node.get_name()}_network_manager_stop")
        #    node_thread = executor.submit(node.network_manager_stop)
        #    node_threads.append(node_thread)
        #    pass

        # for node_thread in node_threads:
        #    node_thread.result()

        for network in self.get_networks():
            network.config()

        for interface in self.get_interfaces():
            try:
                interface.config_vlan_iface()
            except Exception as e:
                logging.error(f"Interface: {interface.get_name()} failed to config")
                logging.error(e, exc_info=True)

        iface_threads = []
        for interface in self.get_interfaces():
            try:
                # iface_threads.append(executor.submit(interface.ip_link_toggle))
                interface.get_node().execute(
                    f"sudo nmcli device set {interface.get_device_name()} managed no",
                    quiet=True,
                )

                # interfaces are config in nodes (below)
                # interface.config()
            except Exception as e:
                logging.error(
                    f"Interface: {interface.get_name()} failed to become unmanaged"
                )
                logging.error(e, exc_info=True)

        # for iface_thread in iface_threads:
        #    iface_thread.result()

        # if self.get_state() == "ModifyOK":
        #    self.modify_accept()

        import time

        start = time.time()

        # from concurrent.futures import ThreadPoolExecutor
        my_thread_pool_executor = ThreadPoolExecutor(32)
        threads = {}

        for node in self.get_nodes():
            # print(f"Configuring {node.get_name()}")
            if not node.is_instantiated():
                thread = my_thread_pool_executor.submit(node.config)
                threads[thread] = node

        print(
            f"Running post boot config threads ..."
        )  # ({time.time() - start:.0f} sec)")

        for thread in concurrent.futures.as_completed(threads.keys()):
            try:
                node = threads[thread]
                result = thread.result()
                # print(result)
                print(
                    f"Post boot config {node.get_name()}, Done! ({time.time() - start:.0f} sec)"
                )
            except Exception as e:
                print(
                    f"Post boot config {node.get_name()}, Failed! ({time.time() - start:.0f} sec)"
                )
                logging.error(
                    f"Post boot config {node.get_name()}, Failed! ({time.time() - start:.0f} sec) {e}"
                )

        # print(f"ALL Nodes, Done! ({time.time() - start:.0f} sec)")

        # Push updates to user_data
        print("Saving fablib data... ", end="")
        self.submit(wait=True, progress=False, post_boot_config=False, wait_ssh=False)
        self.update()
        print(" Done!")

    def validIPAddress(self, IP: str) -> str:
        """
        Not intended as a API call.

        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def isReady(self, update=False):
        if not self.isStable():
            logging.debug(
                f"isReady: {self.get_name()} not stable ({self.get_state()}), returning false"
            )
            return False

        if update:
            self.update()

        for node in self.get_nodes():
            if (
                node.get_reservation_state() == "Ticketed"
                or not node.get_reservation_state()
                or node.get_reservation_state() == "None"
            ):
                logging.warning(
                    f"slice not ready: node {node.get_name()} status: {node.get_reservation_state()}"
                )
                return False

            if (
                node.get_reservation_state() == "Active"
                and node.get_management_ip() == None
            ):
                logging.warning(
                    f"slice not ready: node {node.get_name()} management ip: {node.get_management_ip()}"
                )
                return False

        for net in self.get_networks():
            if net.get_type() in ["FABNetv4", "FABNetv6", "FABNetv4Ext", "FABNetv6Ext"]:
                try:
                    if (
                        not type(net.get_subnet())
                        in [ipaddress.IPv4Network, ipaddress.IPv6Network]
                        or not type(net.get_gateway())
                        in [ipaddress.IPv4Address, ipaddress.IPv46ddress]
                        or net.get_available_ips() == None
                    ):
                        logging.warning(
                            f"slice not ready: net {net.get_name()}, subnet: {net.get_subnet()}, available_ips: {net.get_available_ips()}"
                        )

                        return False
                except Exception as e:
                    logging.warning(f"slice not ready: net {net.get_name()}, {e}")
                    return False

        return True

    def wait_jupyter(self, timeout: int = 1800, interval: int = 30, verbose=False):
        """
        Waits for the slice to be in a stable and displays jupyter compliant tables of the slice progress.

        :param timeout: how many seconds to wait on the slice
        :type timeout: int
        :param interval: how often in seconds to check on slice state
        :type interval: int
        :raises Exception: if the slice state is undesirable, or waiting times out
        :return: the stable slice on the slice manager
        :rtype: SMSlice
        """

        import time

        from IPython.display import clear_output

        logging.debug(f"wait_jupyter: slice {self.get_name()}")

        start = time.time()

        # if len(self.get_interfaces()) > 0:
        #    hasNetworks = True
        # else:
        #    hasNetworks = False

        count = 0
        # while not self.isStable():
        # while not self.isReady():
        while True:
            if time.time() > start + timeout:
                raise Exception(f"Timeout {timeout} sec exceeded in Jupyter wait")

            time.sleep(interval)

            stable = False
            self.update_slice()
            self.update_slivers()

            if self.isStable():
                stable = True
                self.update()
                if len(self.get_interfaces()) > 0:
                    hasNetworks = True
                else:
                    hasNetworks = False
                if self.isReady():
                    break
            else:
                if verbose:
                    self.update()
                    if len(self.get_interfaces()) > 0:
                        hasNetworks = True
                    else:
                        hasNetworks = False
                else:
                    self.update_slice()

            slice_show_table = self.show(colors=True, quiet=True)
            sliver_table = self.list_slivers(colors=True, quiet=True)

            logging.debug(f"sliver_table: {sliver_table}")
            if stable or verbose:
                node_table = self.list_nodes(colors=True, quiet=True)
                if hasNetworks:
                    network_table = self.list_networks(colors=True, quiet=True)

            time_string = f"{time.time() - start:.0f} sec"

            # Clear screen
            clear_output(wait=True)

            print(f"\nRetry: {count}, Time: {time_string}")
            logging.debug(
                f"{self.get_name()}, update_count: {self.update_count}, update_topology_count: {self.update_topology_count}, update_slivers_count: {self.update_slivers_count},  update_slice_count: {self.update_slice_count}"
            )

            if stable:
                if slice_show_table:
                    display(slice_show_table)
                if node_table:
                    display(node_table)
                if hasNetworks and network_table:
                    display(network_table)

            else:
                if slice_show_table:
                    display(slice_show_table)
                if sliver_table:
                    display(sliver_table)
                if verbose:
                    if node_table:
                        display(node_table)
                    if hasNetworks and network_table:
                        display(network_table)

            count += 1

        # self.update()

        # if len(self.get_interfaces()) > 0:
        #    hasNetworks = True
        # else:
        #    hasNetworks = False

        slice_show_table = self.show(colors=True, quiet=True)
        node_table = self.list_nodes(colors=True, quiet=True)
        if hasNetworks:
            network_table = self.list_networks(colors=True, quiet=True)

        clear_output(wait=True)

        display(slice_show_table)
        display(node_table)
        if hasNetworks and network_table:
            display(network_table)

        print(f"\nTime to stable {time.time() - start:.0f} seconds")

        print("Running post_boot_config ... ")
        self.post_boot_config()
        print(f"Time to post boot config {time.time() - start:.0f} seconds")

        # Last update to get final data for display
        # no longer needed because post_boot_config does this
        # self.update()

        slice_show_table = self.show(colors=True, quiet=True)
        node_table = self.list_nodes(colors=True, quiet=True)
        if hasNetworks:
            network_table = self.list_networks(colors=True, quiet=True)

        time_string = f"{time.time() - start:.0f} sec"

        # Clear screen
        clear_output(wait=True)

        print(f"\nRetry: {count}, Time: {time_string}")

        display(slice_show_table)
        display(node_table)
        if hasNetworks:
            display(network_table)

        if hasNetworks:
            self.list_interfaces()
            print(f"\nTime to print interfaces {time.time() - start:.0f} seconds")

    def submit(
        self,
        wait: bool = True,
        wait_timeout: int = 1800,
        wait_interval: int = 20,
        progress: bool = True,
        wait_jupyter: str = "text",
        post_boot_config: bool = True,
        wait_ssh: bool = True,
    ) -> str:
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

        if self.get_state() == None:
            modify = False
        else:
            modify = True

        if not wait:
            progress = False

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        if modify:
            (
                return_status,
                slice_reservations,
            ) = self.fablib_manager.get_slice_manager().modify(
                slice_id=self.slice_id, slice_graph=slice_graph
            )
        else:
            (
                return_status,
                slice_reservations,
            ) = self.fablib_manager.get_slice_manager().create(
                slice_name=self.slice_name,
                slice_graph=slice_graph,
                ssh_key=self.get_slice_public_key(),
            )
            if return_status == Status.OK:
                logging.info(
                    f"Submit request success: return_status {return_status}, slice_reservations: {slice_reservations}"
                )
                logging.debug(f"slice_reservations: {slice_reservations}")
                logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
                self.slice_id = slice_reservations[0].slice_id
            else:
                logging.error(
                    f"Submit request error: return_status {return_status}, slice_reservations: {slice_reservations}"
                )
                raise Exception(
                    f"Submit request error: return_status {return_status}, slice_reservations: {slice_reservations}"
                )

        if return_status != Status.OK:
            raise Exception(
                "Failed to submit slice: {}, {}".format(
                    return_status, slice_reservations
                )
            )

        # logging.debug(f"slice_reservations: {slice_reservations}")
        # logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
        # self.slice_id = slice_reservations[0].slice_id

        # time.sleep(1)
        # self.update()

        # if not wait:
        #    return self.slice_id

        if (
            progress
            and wait_jupyter == "text"
            and self.fablib_manager.is_jupyter_notebook()
        ):
            self.wait_jupyter(timeout=wait_timeout, interval=wait_interval)
            return self.slice_id

        elif wait:
            self.update()

            self.wait()

            if wait_ssh:
                self.wait_ssh(
                    timeout=wait_timeout, interval=wait_interval, progress=progress
                )

            if progress:
                print("Running post boot config ... ", end="")

            if post_boot_config:
                self.post_boot_config()
        else:
            self.update()
            return self.slice_id

        if progress:
            print("Done!")

        return self.slice_id

    def list_networks(
        self,
        output=None,
        fields=None,
        colors=False,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the networks in the slice.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','State']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['State'] == 'Active'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :param colors: True to add colors to the table when possible
        :type colors: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and not "TicketReviewPolicy" in val:
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Closed":
                # return [f'background-color: {self.get_fablib_manager().ERROR_LIGHT_COLOR}']*(len(fields))
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            # elif x.State == 'None':
            #    return ['opacity: 50%']*(len(fields))
            # else:
            #    return ['background-color: ']*(len(fields))

            return "background-color: %s" % color

        def state_color(val):
            if val == "Active":
                color = f"{self.get_fablib_manager().SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            elif val == "ActiveTicketed":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            elif val == "Failed":
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color
            return "background-color: %s" % color

        table = []
        for network in self.get_networks():
            table.append(network.toDict())

        table = sorted(table, key=lambda x: (x["name"]))

        if pretty_names:
            pretty_names_dict = NetworkService.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        logging.debug(f"network service: pretty_names_dict = {pretty_names_dict}")

        table = self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Networks",
            output=output,
            quiet=True,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

        if table and colors:
            if pretty_names:
                # table = table.apply(highlight, axis=1)
                table = table.applymap(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.applymap(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.apply(highlight, axis=1)
                table = table.applymap(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.applymap(error_color, subset=pd.IndexSlice[:, ["error"]])

        if table and not quiet:
            display(table)

        return table

    def list_slivers(
        self,
        output=None,
        fields=None,
        colors=False,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the slivers in the slice.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','State']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['State'] == 'Active'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :param colors: True to add colors to the table when possible
        :type colors: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and not "TicketReviewPolicy" in val:
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Ticketed":
                return [
                    f"background-color: {self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
                ] * (len(fields))
            elif x.State == "None":
                return ["opacity: 50%"] * (len(fields))
            else:
                return ["background-color: "] * (len(fields))

        def state_color(val):
            if val == "Active":
                color = f"{self.get_fablib_manager().SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed" or val == "Nascent" or val == "ActiveTicketed":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color
            return "background-color: %s" % color

        table = []
        for sliver in self.get_slivers():
            try:
                import json

                reservation_info = json.loads(sliver.sliver["ReservationInfo"])
                error = reservation_info["error_message"]
            except:
                error = ""

            if sliver.sliver_type == "NetworkServiceSliver":
                type = "network"
            elif sliver.sliver_type == "NodeSliver":
                type = "node"
            else:
                type = sliver.sliver_type

            if "Site" in sliver.sliver:
                site = sliver.sliver["Site"]
            else:
                site = ""

            table.append(
                {
                    "id": sliver.sliver_id,
                    "name": sliver.sliver["Name"],
                    "site": site,
                    "type": type,
                    "state": sliver.state,
                    "error": error,
                }
            )

            logging.debug(sliver)
        table = sorted(table, key=lambda x: ([-ord(c) for c in x["type"]], x["name"]))

        logging.debug(f"table: {table}")

        if pretty_names:
            pretty_names_dict = {
                "name": "Name",
                "id": "ID",
                "site": "Site",
                "type": "Type",
                "state": "State",
                "error": "Error",
            }
        else:
            pretty_names_dict = {}

        logging.debug(f"pretty_names_dict = {pretty_names_dict}")

        table = self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Slivers",
            output=output,
            quiet=True,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

        if table and colors:
            if pretty_names:
                # table = table.apply(highlight, axis=1)
                table = table.applymap(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.applymap(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.apply(highlight, axis=1)
                table = table.applymap(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.applymap(error_color, subset=pd.IndexSlice[:, ["error"]])

        if table and not quiet:
            display(table)

        return table

    def list_nodes(
        self,
        output=None,
        fields=None,
        colors=False,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the nodes in the slice.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','State']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['State'] == 'Active'

        :param output: output format
        :type output: str
        :param fields: list of fields (table columns) to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param filter_function: lambda function
        :type filter_function: lambda
        :param colors: True to add colors to the table when possible
        :type colors: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and not "TicketReviewPolicy" in val:
                color = f"{self.get_fablib_manager().ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Ticketed":
                return [
                    f"background-color: {self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
                ] * (len(fields))
            elif x.State == "None":
                return ["opacity: 50%"] * (len(fields))
            else:
                return ["background-color: "] * (len(fields))

        def state_color(val):
            if val == "Active":
                color = f"{self.get_fablib_manager().SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed":
                color = f"{self.get_fablib_manager().IN_PROGRESS_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color
            return "background-color: %s" % color

        table = []
        for node in self.get_nodes():
            table.append(node.toDict())

        table = sorted(table, key=lambda x: (x["name"]))

        # if fields == None:
        #    fields = ["ID", "Name", "Site", "Host",
        #              "Cores", "RAM", "Disk", "Image",
        #              "Username", "Management IP", "State", "Error"]

        if pretty_names:
            pretty_names_dict = Node.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        logging.debug(f"pretty_names_dict = {pretty_names_dict}")

        table = self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Nodes",
            output=output,
            quiet=True,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

        if table and colors:
            if pretty_names:
                # table = table.apply(highlight, axis=1)
                table = table.applymap(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.applymap(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.apply(highlight, axis=1)
                table = table.applymap(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.applymap(error_color, subset=pd.IndexSlice[:, ["error"]])
        if table and not quiet:
            display(table)

        return table

    def modify(
        self,
        wait: int = True,
        wait_timeout: int = 600,
        wait_interval: int = 10,
        progress: bool = True,
        wait_jupyter: str = "text",
        post_boot_config: bool = True,
    ):
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
        (
            return_status,
            slice_reservations,
        ) = self.fablib_manager.get_slice_manager().modify(
            slice_id=self.slice_id, slice_graph=slice_graph
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to submit modify slice: {}, {}".format(
                    return_status, slice_reservations
                )
            )

        logging.debug(f"slice_reservations: {slice_reservations}")
        # logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
        # self.slice_id = slice_reservations[0].slice_id

        # time.sleep(1)
        # self.update()

        if (
            progress
            and wait_jupyter == "text"
            and self.fablib_manager.is_jupyter_notebook()
        ):
            self.wait_jupyter(timeout=wait_timeout, interval=wait_interval)
            return self.slice_id

        elif wait:
            self.wait_ssh(
                timeout=wait_timeout, interval=wait_interval, progress=progress
            )

            if progress:
                print("Running post boot config ... ", end="")

            self.update()
            if post_boot_config:
                self.post_boot_config()
        else:
            self.update()

        if progress:
            print("Done!")

        return self.slice_id

    def modify_accept(self):
        """
        Submits an accept to accept the last modify slice request to FABRIC.
        """
        # Request slice from Orchestrator
        return_status, topology = self.fablib_manager.get_slice_manager().modify_accept(
            slice_id=self.slice_id
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to accept the last modify slice: {}, {}".format(
                    return_status, topology
                )
            )
        else:
            self.topology = topology

        logging.debug(f"modified topology: {topology}")

        self.update_slice()

    def get_user_data(self):
        user_data = {}
        for node in self.get_nodes():
            user_data[node.get_name()] = node.get_user_data()

        for network in self.get_networks():
            user_data[network.get_name()] = network.get_user_data()

        for iface in self.get_interfaces():
            user_data[iface.get_name()] = iface.get_user_data()

        for componenet in self.get_components():
            user_data[componenet.get_name()] = componenet.get_user_data()

        return user_data
