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
Methods to manage FABRIC `slices`_.

.. _`slices`: https://learn.fabric-testbed.net/knowledge-base/glossary/#slice

You would create and use a slice like so::

    from ipaddress import IPv4Address
    from fabrictestbed_extensions.fablib.fablib import FablibManager

    fablib = FablibManager()

    # Create a slice and add resources to it, creating a topology.
    slice = fablib.new_slice(name="MySlice")
    node1 = slice.add_node(name="node1", site="TACC")
    net1 = slice.add_l2network(name="net1", subnet=IPv4Network("192.168.1.0/24"))

    # Do more setup, and then run your experiment.

    # Delete the slice after you are done.
    slice.delete()

"""

from __future__ import annotations

import ipaddress
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Tuple

import pandas as pd
from fim.user import Labels, NodeType
from fss_utils.sshkey import FABRICSSHKey
from IPython.core.display_functions import display

from fabrictestbed_extensions.fablib.constants import Constants
from fabrictestbed_extensions.fablib.facility_port import FacilityPort
from fabrictestbed_extensions.fablib.switch import Switch

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
from fabrictestbed.slice_manager import Status
from tabulate import tabulate

from fabrictestbed_extensions.fablib.attestable_switch import Attestable_Switch
from fabrictestbed_extensions.fablib.component import Component
from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.node import Node


class Slice:
    def __init__(
        self, fablib_manager: FablibManager, name: str = None, user_only: bool = True
    ):
        """
        Create a FABRIC slice, and set its state to be callable.

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

        self.nodes = {}
        self.facilities = {}
        self.interfaces = {}
        self.update_topology_count = 0
        self.update_slivers_count = 0
        self.update_slice_count = 0
        self.update_count = 0
        self.user_only = user_only

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
            ["Slice Name", self.get_name()],
            ["Slice ID", self.get_slice_id()],
            ["Slice State", self.get_state()],
            ["Lease End", self.get_lease_end()],
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
        :param pretty_names:
        :type pretty_names: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """

        data = self.toDict()

        def state_color(val):
            if val == "StableOK":
                color = f"{Constants.SUCCESS_LIGHT_COLOR}"
            elif val == "ModifyOK":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            elif val == "AllocatedOK":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            elif val == "StableError":
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            elif val == "ModifyError":
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            elif val == "AllocatedError":
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            elif val == "Configuring":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            elif val == "Modifying":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
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
            slice_table.map(state_color)

            if not quiet:
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
        refresh: bool = False,
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
        :param pretty_names:
        :type pretty_names: bool
        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """
        table = []
        for component in self.get_components(refresh=refresh):
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
        pretty_names: bool = True,
        refresh: bool = False,
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
        :param pretty_names:
        :type pretty_names: bool
        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """
        executor = ThreadPoolExecutor(64)

        net_name_threads = {}
        node_name_threads = {}
        physical_os_interface_name_threads = {}
        os_interface_threads = {}
        for iface in self.get_interfaces(refresh=refresh):
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
        if fablib_manager:
            fablib_manager.cache_slice(slice_object=slice)
        return slice

    @staticmethod
    def get_slice(
        fablib_manager: FablibManager,
        sm_slice: OrchestratorSlice = None,
        user_only: bool = True,
    ):
        """
        Not intended for API use.

        Gets an existing fablib slice using a slice manager slice
        :param fablib_manager:
        :param sm_slice:
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool
        :return: Slice
        """
        logging.info("slice.get_slice()")

        slice = Slice(fablib_manager=fablib_manager, name=sm_slice.name)
        slice.sm_slice = sm_slice
        slice.slice_id = sm_slice.slice_id
        slice.slice_name = sm_slice.name
        slice.user_only = user_only
        if fablib_manager:
            fablib_manager.cache_slice(slice_object=slice)

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
            "email": "Email",
            "user_id": "UserId",
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
            "email": str(self.get_email()),
            "user_id": str(self.get_user_id()),
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
        if "nodes" not in skip:
            for node in self.get_nodes():
                node_context = node.generate_template_context()
                context["nodes"][node.get_name()] = node_context

        context["components"] = {}
        if "components" not in skip:
            for component in self.get_components():
                context["components"][
                    component.get_name()
                ] = component.generate_template_context()

        context["interfaces"] = {}
        if "interfaces" not in skip:
            for interface in self.get_interfaces():
                context["interfaces"][interface.get_name()] = interface.toDict()

        context["networks"] = {}
        if "networks" not in skip:
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

    def get_fim(self) -> ExperimentTopology:
        """
        Get FABRIC Information Model (fim) object for the slice.
        """
        return self.get_fim_topology()

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

        return_status, slices = self.fablib_manager.get_manager().slices(
            excludes=[],
            slice_id=self.slice_id,
            name=self.slice_name,
            as_self=self.user_only,
            graph_format="NONE",
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
        if not self.sm_slice:
            return

        self.update_topology_count += 1
        logging.info(
            f"update_topology: {self.get_name()}, count: {self.update_topology_count}"
        )

        (
            return_status,
            new_topo,
        ) = self.fablib_manager.get_manager().get_slice_topology(
            slice_object=self.sm_slice, as_self=self.user_only
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to get slice topology: {}, {}".format(return_status, new_topo)
            )

        # Set slice attributes
        self.topology = new_topo
        self.get_nodes()
        self.get_facilities()
        self.get_interfaces(refresh=True)

    def update_slivers(self):
        """
        Not recommended for most users.  See Slice.update() method.

        Updates the slivers with the current slice manager.

        :raises Exception: if topology could not be gotten from slice manager
        """
        if self.sm_slice is None:
            return

        self.update_slivers_count += 1
        logging.debug(
            f"update_slivers: {self.get_name()}, count: {self.update_slivers_count}"
        )

        status, slivers = self.fablib_manager.get_manager().slivers(
            slice_object=self.sm_slice, as_self=self.user_only
        )
        if status == Status.OK:
            self.slivers = slivers
            return

        raise Exception(f"{slivers}")

    def get_sliver(self, reservation_id: str) -> OrchestratorSliver:
        """
        Returns the sliver associated with the reservation ID.
        """
        slivers = self.get_slivers()
        sliver = list(filter(lambda x: x.sliver_id == reservation_id, slivers))[0]
        return sliver

    def get_slivers(self) -> List[OrchestratorSliver]:
        """
        Returns slivers associated with the slice.
        """
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

        # self.nodes = None
        self.interfaces = {}
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
        return self.fablib_manager.get_default_slice_private_key_passphrase()

    def get_slice_public_key(self) -> str:
        """
        Gets the slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the public key
        :rtype: String
        """
        return self.fablib_manager.get_default_slice_public_key()

    def get_slice_public_key_file(self) -> str:
        """
        Gets the path to the slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: path to public key file
        :rtype: String
        """
        return self.fablib_manager.get_default_slice_public_key_file()

    def get_slice_private_key_file(self) -> str:
        """
        Gets the path to the slice private key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: path to private key file
        :rtype: String
        """
        return self.fablib_manager.get_default_slice_private_key_file()

    def get_slice_private_key(self) -> str:
        """
        Gets the string representing the slice private key.

        :return: public key
        :rtype: String
        """
        return self.fablib_manager.get_default_slice_private_key()

    def is_dead_or_closing(self):
        """
        Tests is the slice is Dead or Closing state.

        :return: True if slice is Dead or Closing state, False otherwise
        :rtype: Bool
        """
        if self.get_state() in ["Closing", "Dead"]:
            return True
        else:
            return False

    def is_advanced_allocation(self) -> bool:
        """
        Checks if slice is requested in future

        :return: True if slice is Allocated and starts in future, False otherwise
        :rtype: Bool
        """
        now = datetime.now(timezone.utc)
        lease_start = (
            datetime.strptime(self.get_lease_start(), Constants.LEASE_TIME_FORMAT)
            if self.get_lease_start()
            else None
        )
        if lease_start and lease_start > now and self.is_allocated():
            return True
        return False

    def is_allocated(self) -> bool:
        """
        Tests is the slice is in Allocated State.

        :return: True if slice is Allocated, False otherwise
        :rtype: Bool
        """
        if (
            self.get_state() in ["AllocatedOK", "AllocatedError"]
            and self.get_lease_start()
        ):
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

        try:
            if self.sm_slice is not None:
                return self.sm_slice.state
        except Exception as e:
            logging.warning(
                f"Exception in get_state from non-None sm_slice. Returning None state: {e}"
            )

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

        try:
            if self.sm_slice is not None:
                return self.sm_slice.lease_end_time
        except Exception as e:
            logging.warning(
                f"Exception in get_lease_end from non-None sm_slice. Returning None state: {e}"
            )

    def get_lease_start(self) -> str:
        """
        Gets the timestamp at which the slice lease starts.

        :return: timestamp when lease starts
        :rtype: String
        """
        try:
            if self.sm_slice is not None:
                return self.sm_slice.lease_start_time
        except Exception as e:
            logging.warning(
                f"Exception in get_lease_end from non-None sm_slice. Returning None state: {e}"
            )

    def get_email(self) -> str:
        """
        Gets the owner's email of the slice.

        :return: email
        :rtype: String
        """
        if self.sm_slice:
            return self.sm_slice.owner_email

    def get_user_id(self) -> str:
        """
        Gets the owner's user id of the slice.

        :return: user id
        :rtype: String
        """
        if self.sm_slice:
            return self.sm_slice.owner_user_id

    def get_project_id(self) -> str:
        """
        Gets the project id of the slice.

        :return: project id
        :rtype: String
        """
        if self.sm_slice:
            return self.sm_slice.project_id

    def add_port_mirror_service(
        self,
        name: str,
        mirror_interface_name: str,
        receive_interface: Interface or None = None,
        mirror_interface_vlan: str = None,
        mirror_direction: str = "both",
    ) -> NetworkService:
        """
        Adds a special PortMirror service.

        It receives data from the dataplane switch interface specified
        by ``mirror_interface`` into an interface specified by
        ``receive_interface``.

        :param name: Name of the service
        :param mirror_interface_name: Name of the interface on the
            dataplane switch to mirror
        :param mirror_interface_vlan: Vlan of the interface
        :param receive_interface: Interface in the topology belonging
            to a SmartNIC component
        :param mirror_direction: String 'rx', 'tx' or 'both'
            defaulting to 'both' which receives the data
        """
        self.nodes = None
        self.interfaces = {}
        port_mirror_service = NetworkService.new_portmirror_service(
            slice=self,
            name=name,
            mirror_interface_name=mirror_interface_name,
            mirror_interface_vlan=mirror_interface_vlan,
            receive_interface=receive_interface,
            mirror_direction=mirror_direction,
        )
        return port_mirror_service

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

            - L2Bridge: a local Ethernet on a single site with
              unlimited interfaces.

            - L2STS: a wide-area Ethernet on exactly two sites with
              unlimited interfaces.  Includes best effort performance
              and cannot, yet, support Basic NICs residing on a single
              physical.

            - L2PTP: a wide-area Ethernet on exactly two sites with
              exactly two interfaces.  QoS performance guarantees
              (coming soon!).  Does not support Basic NICs.  Traffic
              arrives with VLAN tag and requires the node OS to
              configure a VLAN interface.

        If the type argument is not set, FABlib will automatically
        choose the L2 network type for you.  In most cases the
        automatic network type is the one you want.  You can force a
        specific network type by setting the type parameter to
        "L2Bridge", "L2STS", or "L2PTP".

        An exception will be raised if the set interfaces is not
        compatible with the specified network type or if there is not
        compatible network type for the given interface list.

        :param name: the name of the network service
        :type name: String

        :param interfaces: a list of interfaces to build the network
            with
        :type interfaces: List[Interface]

        :param type: optional L2 network type "L2Bridge", "L2STS", or
            "L2PTP"
        :type type: String

        :param subnet:
        :type subnet: ipaddress

        :param gateway:
        :type gateway: ipaddress

        :param user_data:
        :type user_data: dict

        :return: a new L2 network service
        :rtype: NetworkService
        """
        self.nodes = None
        self.interfaces = {}

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
        technology: str = None,
        subnet: ipaddress.ip_network = None,
    ) -> NetworkService:
        """
        Adds a new L3 network service to this slice.

        L3 networks types include:

            - IPv4: An IPv4 network on the FABNetv4 internet

            - IPv6: An IPv6 network on the FABNetv6 internet

        The FABNet networks are internal IP internets that span the
        FABRIC testbed.  Adding a new L3 network to your FABRIC slice
        creates an isolated network at a single site.  FABRIC issues
        each isolated L3 network with an IP subnet (either IPv4 or
        IPv6) and a gateway used to route traffic to the FABNet
        internet.

        Like the public Internet, all FABNet networks can send traffic
        to all other FABnet networks of the same type.  In other
        words, FABNet networks can be used to communicate between your
        slices and slices owned by other users.

        An exception will be raised if the set interfaces is not from
        a single FABRIC site.  If you want to use L3 networks to
        connect slices that are distributed across many site, you need
        to create a separate L3 network for each site.

        It is important to note that by all nodes come with a default
        gateway on a management network that use used to access your
        nodes (i.e. to accept ssh connections).  To use an L3
        dataplane network, you will need to add routes to your nodes
        that selectively route traffic across the new dataplane
        network.  You must be careful to maintain the default gateway
        settings if you want to be able to access the node using the
        management network.

        :param name: the name of the network service
        :type name: String

        :param interfaces: a list of interfaces to build the network
            with
        :type interfaces: List[Interface]

        :param type: L3 network type "IPv4" or "IPv6"
        :type type: String

        :param user_data:
        :type user_data: dict

        :param technology: Specify the technology used should be set
            to AL2S when using for AL2S peering; otherwise None
        :type technology: str

        :param subnet: Request a specific subnet for FabNetv4,
            FabNetv6 or FabNetv6Ext services.  It's ignored for any
            other services.
        :type subnet: ipaddress.ip_network

        :return: a new L3 network service
        :rtype: NetworkService
        """
        self.nodes = None
        self.interfaces = {}

        return NetworkService.new_l3network(
            slice=self,
            name=name,
            interfaces=interfaces,
            type=type,
            user_data=user_data,
            technology=technology,
            subnet=subnet,
        )

    def add_facility_port(
        self,
        name: str = None,
        site: str = None,
        vlan: Union[str, list] = None,
        labels: Labels = None,
        peer_labels: Labels = None,
        bandwidth: int = 10,
        mtu: int = None,
    ) -> FacilityPort:
        """
        Adds a new L2 facility port to this slice

        :param name: name of the facility port
        :type name: String
        :param site: site
        :type site: String
        :param vlan: vlan
        :type vlan: String
        :param labels: labels for the facility port such as VLAN, ip sub net
        :type: labels: Labels
        :param peer_labels: peer labels for the facility port such as VLAN, ip sub net, bgp key - used for AL2S Peering
        :type: peer_labels: Labels
        :param bandwidth: bandwidth
        :type: bandwidth: int
        :param mtu: MTU size
        :type: mtu: int
        :return: a new L2 facility port
        :rtype: NetworkService
        """
        return FacilityPort.new_facility_port(
            slice=self,
            name=name,
            site=site,
            vlan=vlan,
            labels=labels,
            peer_labels=peer_labels,
            bandwidth=bandwidth,
            mtu=mtu,
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
        validate: bool = False,
        raise_exception: bool = False,
    ) -> Node:
        """
        Creates a new node on this fablib slice.

        :param name: Name of the new node
        :type name: String

        :param site: (Optional) Name of the site to deploy the node
            on.  Default to a random site.
        :type site: String

        :param cores: (Optional) Number of cores in the node.
            Default: 2 cores
        :type cores: int

        :param ram: (Optional) Amount of ram in the node.  Default: 8
            GB
        :type ram: int

        :param disk: (Optional) Amount of disk space in the node.
            Default: 10 GB
        :type disk: int

        :param image: (Optional) The image to use for the node.
            Default: default_rocky_8
        :type image: String

        :param instance_type:
        :type instance_type: String

        :param host: (Optional) The physical host to deploy the node.
            Each site has worker nodes numbered 1, 2, 3, etc.  Host
            names follow the pattern in this example of STAR worker
            number 1: "star-w1.fabric-testbed.net".  Default: unset
        :type host: String

        :param user_data:
        :type user_data: dict

        :param avoid: (Optional) A list of sites to avoid is allowing
            random site.
        :type avoid: List[String]

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :param raise_exception: Raise exception in case of Failure
        :type raise_exception: bool

        :return: a new node
        :rtype: Node
        """
        node = Node.new_node(
            slice=self,
            name=name,
            site=site,
            avoid=avoid,
            validate=validate,
            raise_exception=raise_exception,
        )

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
        self.interfaces = {}

        if validate:
            status, error = self.get_fablib_manager().validate_node(node=node)
            if not status:
                node.delete()
                node = None
                logging.warning(error)
                if raise_exception:
                    raise ValueError(error)
        return node

    def add_attestable_switch(
        self,
        name: str,
        site: str = None,
        cores: int = 4,
        ram: int = 8,
        disk: int = 50,
        image: str = Attestable_Switch.default_image,
        ports: List[str] = None,
        instance_type: str = None,
        host: str = None,
        user_data: dict = {},
        avoid: List[str] = [],
        validate: bool = False,
        raise_exception: bool = False,
        from_raw_image: bool = False,
        setup_and_configure: bool = True,
    ) -> Attestable_Switch:
        """
        Creates a new attestable switch on this fablib slice.
        """

        assert (
            ports
            and isinstance(ports, list)
            and all(isinstance(port, str) for port in ports)
        )

        name = Attestable_Switch.name(name)

        aswitch = Attestable_Switch.new_attestable_switch(
            slice=self,
            name=name,
            site=site,
            avoid=avoid,
            validate=validate,
            raise_exception=raise_exception,
            ports=ports,
            from_raw_image=from_raw_image,
            setup_and_configure=setup_and_configure,
        )

        aswitch.init_fablib_data()

        user_data_working = aswitch.get_user_data()
        for k, v in user_data.items():
            user_data_working[k] = v
        aswitch.set_user_data(user_data_working)

        if instance_type:
            aswitch.set_instance_type(instance_type)
        else:
            aswitch.set_capacities(cores=cores, ram=ram, disk=disk)

        if image:
            aswitch.set_image(image)

        if host:
            aswitch.set_host(host)

        self.nodes = None
        self.interfaces = {}

        if validate:
            status, error = self.get_fablib_manager().validate_node(node=aswitch)
            if not status:
                aswitch.delete()
                aswitch = None
                logging.warning(error)
                if raise_exception:
                    raise ValueError(error)

        return aswitch

    def add_switch(
        self,
        name: str,
        site: str = None,
        user_data: dict = None,
        avoid: List[str] = None,
        validate: bool = False,
        raise_exception: bool = False,
    ) -> Switch:
        """
        Creates a new switch on this fablib slice.

        :param name: Name of the new switch
        :type name: String

        :param site: (Optional) Name of the site to deploy the node
            on.  Default to a random site.
        :type site: String

        :param user_data:
        :type user_data: dict

        :param avoid: (Optional) A list of sites to avoid is allowing
            random site.
        :type avoid: List[String]

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :param raise_exception: Raise exception in case of Failure
        :type raise_exception: bool

        :return: a new node
        :rtype: Node
        """
        if not user_data:
            user_data = {}
        if not avoid:
            avoid = []

        node = Switch.new_switch(
            slice=self,
            name=name,
            site=site,
            avoid=avoid,
            validate=validate,
            raise_exception=raise_exception,
        )

        node.init_fablib_data()

        user_data_working = node.get_user_data()
        for k, v in user_data.items():
            user_data_working[k] = v
        node.set_user_data(user_data_working)

        self.nodes = None
        self.interfaces = {}

        if validate:
            status, error = self.get_fablib_manager().validate_node(node=node)
            if not status:
                node.delete()
                node = None
                logging.warning(error)
                if raise_exception:
                    raise ValueError(error)
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
            notices[network_service.get_reservation_id()] = (
                network_service.get_error_message()
            )

        for component in self.get_components():
            notices[component.get_reservation_id()] = component.get_error_message()

        return notices

    def get_components(self, refresh: bool = False) -> List[Component]:
        """
        Gets all components in this slice.

        :param refresh: Refresh the components with latest Fim info
        :type refresh: bool

        :return: List of all components in this slice
        :rtype: List[Component]
        """
        return_components = []

        # fails for topology that does not have nodes
        try:
            for node in self.get_nodes():
                return_components.extend(node.get_components(refresh=refresh))
        except Exception as e:
            logging.error(f"get_components: error {e}", exc_info=True)
            # traceback.print_exc()
            pass
        return return_components

    def __initialize_nodes(self):
        """
        Initializes the node objects for the current topology by populating
        the self.nodes dictionary with node instances.

        - If self.nodes is empty, it initializes it as an empty dictionary.
        - It iterates through the nodes in the FIM topology and adds them
          to self.nodes if they do not already exist.
        - If a node already exists in the dictionary, it updates its
          fim_node reference to match the current topology.
        - After processing, it removes any nodes from self.nodes that
          are no longer present in the current topology.

        https://github.com/fabric-testbed/fabrictestbed-extensions/issues/380

        :raises: Logs an exception if an error occurs during initialization.
        """
        # Initialize nodes dictionary if not already present
        if not self.nodes:
            self.nodes = {}

        try:
            # Get the current FIM topology nodes
            current_topology_nodes = self.get_fim_topology().nodes

            # Update the nodes dictionary with current topology nodes
            for node_name, node in current_topology_nodes.items():
                if node_name not in self.nodes:
                    if node.type == NodeType.Switch:
                        self.nodes[node_name] = Switch.get_node(self, node)
                    else:
                        # Add new node to the dictionary if it doesn't exist
                        self.nodes[node_name] = Node.get_node(self, node)
                else:
                    # Update existing node's fim_node reference
                    self.nodes[node_name].update(fim_node=node)

            # Remove nodes that are no longer present in the current topology
            self.__remove_deleted_nodes(current_topology_nodes)

        except Exception as e:
            logging.error(f"Error initializing nodes: {e}")

    def __remove_deleted_nodes(self, current_topology_nodes):
        """
        Removes nodes from self.nodes that are not present in the current topology.

        :param current_topology_nodes: A dictionary of nodes currently in the topology.
        """
        # Create a set of current node names for quick lookup
        current_node_names = set(current_topology_nodes.keys())

        # Identify and remove nodes that are not in the current topology
        nodes_to_remove = [
            node_name
            for node_name in self.nodes.keys()
            if node_name not in current_node_names
        ]

        for node_name in nodes_to_remove:
            for ifs in self.nodes[node_name].get_interfaces():
                if ifs.get_name() in self.interfaces:
                    self.interfaces.pop(ifs.get_name())
            self.nodes.pop(node_name)
            logging.debug(f"Removed extra node: {node_name}")

    def get_nodes(self) -> List[Node]:
        """
        Gets a list of all nodes in this slice.

        :return: a list of fablib nodes
        :rtype: List[Node]
        """
        self.__initialize_nodes()
        return list(self.nodes.values())

    def get_facility(self, name: str) -> FacilityPort:
        """
        Gets a facility port from the slice by name.

        :param name: Name of the facility Port
        :type name: String
        :return: a fablib FacilityPort
        :rtype: FacilityPort
        """
        try:
            if self.facilities and len(self.facilities) and name in self.facilities:
                return self.facilities.get(name)
            return FacilityPort.get_facility_port(
                self, self.get_fim_topology().facilities[name]
            )
        except Exception as e:
            logging.info(e, exc_info=True)
            raise Exception(f"Node not found: {name}")

    def get_facilities(self) -> List[FacilityPort]:
        """
        Gets a list of all nodes in this slice.

        :return: a list of fablib nodes
        :rtype: List[FacilityPort]
        """
        self.__initialize_facilities()
        return list(self.facilities.values())

    def __initialize_facilities(self):
        """
        Initializes the facilities objects for the current topology by populating
        the self.facilities dictionary with node instances.

        - If self.facilities is empty, it initializes it as an empty dictionary.
        - It iterates through the nodes in the FIM topology and adds them
          to self.facilities if they do not already exist.
        - If a facility already exists in the dictionary, it updates its
          fim_node reference to match the current topology.
        - After processing, it removes any facilities from self.facilities that
          are no longer present in the current topology.

        https://github.com/fabric-testbed/fabrictestbed-extensions/issues/380

        :raises: Logs an exception if an error occurs during initialization.
        """
        # Initialize facilities dictionary if not already present
        if not self.facilities:
            self.facilities = {}

        try:
            # Get the current FIM topology nodes
            current = self.get_fim_topology().facilities

            # Update the nodes dictionary with current topology nodes
            for fac_name, facility in current.items():
                if fac_name not in self.facilities:
                    self.facilities[fac_name] = FacilityPort.get_facility_port(
                        self, facility
                    )
                else:
                    # Update existing facility's fim_node reference
                    self.facilities[fac_name].update(fim_node=facility)

            # Remove nodes that are no longer present in the current topology
            self.__remove_deleted_facilities(current)

        except Exception as e:
            logging.error(f"Error initializing facilities: {e}")

    def __remove_deleted_facilities(self, current):
        """
        Removes nodes from self.facilities that are not present in the current topology.

        :param current: A dictionary of facilities currently in the topology.
        """
        # Create a set of current node names for quick lookup
        current_names = set(current.keys())

        # Identify and remove nodes that are not in the current topology
        facilities_to_remove = [
            fac_name
            for fac_name in self.facilities.keys()
            if fac_name not in current_names
        ]

        for fac_name in facilities_to_remove:
            for ifs in self.facilities[fac_name].get_interfaces():
                if ifs.get_name() in self.interfaces:
                    self.interfaces.pop(ifs.get_name())
            self.facilities.pop(fac_name)
            logging.debug(f"Removed extra facility: {fac_name}")

    def get_attestable_switches(self) -> List[Attestable_Switch]:
        """
        Get list of attestable switches in the fablib slice.
        """

        result = []
        for node in self.get_nodes():
            if "attestable_switch_config" in node.get_user_data():
                aswitch = self.get_attestable_switch(name=node.get_name())
                result.append(aswitch)
        return result

    def get_attestable_switch(self, name: str) -> Attestable_Switch:
        """
        Get reference to an attestable switch in the fablib slice.
        """

        name = Attestable_Switch.name(name)
        try:
            return Attestable_Switch.get_attestable_switch(
                self, self.get_fim_topology().nodes[name]
            )
        except Exception as e:
            logging.info(e, exc_info=True)
            raise Exception(f"Attestable Switch not found: {name}")

    def get_node(self, name: str) -> Node:
        """
        Gets a node from the slice by name.

        :param name: Name of the node
        :type name: String
        :return: a fablib node
        :rtype: Node
        """
        try:
            if self.nodes and len(self.nodes) and name in self.nodes:
                return self.nodes.get(name)
            if self.get_fim_topology().nodes[name].type == NodeType.Switch:
                return Switch.get_node(self, self.get_fim_topology().nodes[name])
            return Node.get_node(self, self.get_fim_topology().nodes[name])
        except Exception as e:
            logging.info(e, exc_info=True)
            raise Exception(f"Node not found: {name}")

    def get_interfaces(
        self, include_subs: bool = True, refresh: bool = False, output: str = "list"
    ) -> Union[dict[str, Interface], list[Interface]]:
        """
        Gets all interfaces in this slice.

        :param include_subs: Flag indicating if sub interfaces should be included
        :type include_subs: bool

        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :param output: Specify how the return type is expected; Possible values: list or dict
        :type output: str

        :return: a list of interfaces on this slice
        :rtype: Union[dict[str, Interface], list[Interface]]
        """
        if len(self.interfaces) == 0 or refresh:
            for node in self.get_nodes():
                logging.debug(f"Getting interfaces for node {node.get_name()}")
                n_ifaces = node.get_interfaces(
                    include_subs=include_subs, refresh=refresh, output="dict"
                )
                self.interfaces.update(n_ifaces)
            for fac in self.get_facilities():
                logging.debug(f"Getting interfaces for facility {fac.get_name()}")
                fac_ifaces = fac.get_interfaces(refresh=refresh, output="dict")
                self.interfaces.update(fac_ifaces)

        if output == "dict":
            return self.interfaces
        else:
            return list(self.interfaces.values())

    def get_interface(self, name: str = None, refresh: bool = False) -> Interface:
        """
        Gets a particular interface from this slice.

        :param name: the name of the interface to search for
        :type name: str

        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :raises Exception: if no interfaces with name are found
        :return: an interface on this slice
        :rtype: Interface
        """
        ret_val = self.get_interfaces(refresh=refresh, output="dict").get(name)
        if not ret_val:
            raise Exception("Interface not found: {}".format(name))
        return ret_val

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

    def get_l3network(self, name: str = None) -> Union[NetworkService or None]:
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

    def delete(self):
        """
        Deletes this slice off of the slice manager and removes its topology.

        :raises Exception: if deleting the slice fails
        """
        if self.get_fablib_manager():
            self.get_fablib_manager().remove_slice_from_cache(slice_object=self)

        if not self.sm_slice:
            self.topology = None
            return
        return_status, result = self.fablib_manager.get_manager().delete(
            slice_object=self.sm_slice
        )

        if return_status != Status.OK:
            raise Exception(
                "Failed to delete slice: {}, {}".format(return_status, result)
            )

        self.topology = None

    def renew(self, end_date: str = None, days: int = None, **kwargs):
        """
        Renews the FABRIC slice's lease to the new end date.

        Date is in UTC and of the form: "%Y-%m-%d %H:%M:%S %z"

        Example of formatting a date for 1 day from now:

        end_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S %z")


        :param end_date: String
        :param days: Integer
        :raises Exception: if renewal fails
        """
        if end_date is None and days is None:
            raise Exception("Either end_date or days must be specified!")

        if end_date is not None:
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S %z")
            days = (end - datetime.now(timezone.utc)).days

        # Directly pass the kwargs to submit
        self.submit(lease_in_hours=(days * 24), post_boot_config=False, **kwargs)

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
            return_status, slices = self.fablib_manager.get_manager().slices(
                excludes=[],
                slice_id=self.slice_id,
                name=self.slice_name,
                as_self=self.user_only,
            )
            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
                if slice.state == "StableOK" or slice.state == "ModifyOK":
                    if progress:
                        print(" Slice state: {}".format(slice.state))
                    break
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
        return slice

    def wait_ssh(self, timeout: int = 1800, interval: int = 20, progress: bool = False):
        """
        Waits for all nodes to be accessible via ssh.

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

        try:
            self.get_fablib_manager().probe_bastion_host()
        except Exception as e:
            print(f"Error when connecting to bastion host: {e}", file=sys.stderr)
            # There are two choices here when it comes to propagating
            # this error: (1) if we can continue functioning without
            # bastion, we can return False here; (2) if we can't, we
            # should re-raise the exception.
            #
            # It appears that post_boot_config(), which is invoked
            # after wait_ssh(), needs bastion, so re-throwing the
            # error might be the right thing to do.
            raise e

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
        if self.is_dead_or_closing() or self.is_allocated():
            print(
                f"FAILURE: Slice is in {self.get_state()} state; cannot do post boot config"
            )
            return

        logging.info(
            f"post_boot_config: slice_name: {self.get_name()}, slice_id {self.get_slice_id()}"
        )

        # Make sure we have the latest topology
        self.update()

        for network in self.get_networks():
            network.config()

        for interface in self.get_interfaces():
            try:
                interface.config_vlan_iface()
            except Exception as e:
                logging.error(f"Interface: {interface.get_name()} failed to config")
                logging.error(e, exc_info=True)

        for interface in self.get_interfaces():
            try:
                interface.get_node().execute(
                    f"sudo nmcli device set {interface.get_device_name()} managed no",
                    quiet=True,
                )
            except Exception as e:
                logging.error(
                    f"Interface: {interface.get_name()} failed to become unmanaged"
                )
                logging.error(e, exc_info=True)

        import time

        start = time.time()

        # from concurrent.futures import ThreadPoolExecutor
        my_thread_pool_executor = ThreadPoolExecutor(32)
        threads = {}

        for node in self.get_nodes():
            # Run configuration on newly created nodes and on modify.
            logging.info(
                f"Configuring {node.get_name()} "
                f"(instantiated: {node.is_instantiated()}, "
                f"modify: {self._is_modify()})"
            )
            if not node.is_instantiated() or self._is_modify():
                thread = my_thread_pool_executor.submit(node.config)
                threads[thread] = node

        print(
            f"Running post boot config threads ..."
        )  # ({time.time() - start:.0f} sec)")

        for thread in concurrent.futures.as_completed(threads.keys()):
            node = threads[thread]
            try:
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

        for node in self.get_nodes():
            if "attestable_switch_config" in node.get_user_data():
                logging.info(
                    f"switch config: {str(node.get_user_data()['attestable_switch_config'])}"
                )
                aswitch = self.get_attestable_switch(name=node.get_name())
                aswitch.switch_config()

        print(" Done!")

    def validIPAddress(self, IP: str) -> str:
        """
        Not intended as a API call.

        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def isReady(self, update=False) -> bool:
        """
        Returns `True` if the slice is ready; else returns `False`.
        """

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
                and node.get_management_ip() is None
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
                        in [ipaddress.IPv4Address, ipaddress.IPv6Address]
                        or net.get_available_ips() is None
                    ):
                        logging.warning(
                            f"slice not ready: net {net.get_name()}, subnet: {net.get_subnet()}, available_ips: {net.get_available_ips()}"
                        )

                        return False
                except Exception as e:
                    logging.warning(f"slice not ready: net {net.get_name()}, {e}")
                    return False

        return True

    def wait_jupyter(
        self,
        timeout: int = 1800,
        interval: int = 30,
        verbose=False,
        post_boot_config: bool = True,
    ):
        """
        Waits for the slice to be in a stable and displays jupyter compliant tables of the slice progress.

        :param timeout: how many seconds to wait on the slice
        :type timeout: int
        :param interval: how often in seconds to check on slice state
        :type interval: int
        :param verbose:
        :type verbose: bool

        :param post_boot_config:
        :type post_boot_config: bool

        :raises Exception: if the slice state is undesirable, or waiting times out
        :return: the stable slice on the slice manager
        :rtype: SMSlice
        """

        import time

        from IPython.display import clear_output

        logging.debug(f"wait_jupyter: slice {self.get_name()}")

        start = time.time()

        count = 0
        hasNetworks = False
        node_table = None
        network_table = None
        # while not self.isStable():
        # while not self.isReady():
        while True:
            if time.time() > start + timeout:
                raise Exception(f"Timeout {timeout} sec exceeded in Jupyter wait")

            time.sleep(interval)

            stable = False
            allocated = False
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
            elif self.is_advanced_allocation():
                allocated = True
                self.update()
                if len(self.get_interfaces()) > 0:
                    hasNetworks = True
                else:
                    hasNetworks = False
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
                f"{self.get_name()}, update_count: {self.update_count}, update_topology_count: "
                f"{self.update_topology_count}, update_slivers_count: {self.update_slivers_count},  "
                f"update_slice_count: {self.update_slice_count}"
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

        slice_show_table = self.show(colors=True, quiet=True)
        node_table = self.list_nodes(colors=True, quiet=True)
        if hasNetworks:
            network_table = self.list_networks(colors=True, quiet=True)

        clear_output(wait=True)

        display(slice_show_table)
        display(node_table)
        if hasNetworks and network_table:
            display(network_table)

        print(f"\nTime to {self.get_state()} {time.time() - start:.0f} seconds")

        if stable:
            if post_boot_config:
                print("Running post_boot_config ... ")
                self.post_boot_config()
                print(f"Time to post boot config {time.time() - start:.0f} seconds")
            else:
                self.update()
        elif allocated:
            print("Future allocation - skipping post_boot_config ... ")

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
        extra_ssh_keys: List[str] = None,
        lease_start_time: datetime = None,
        lease_end_time: datetime = None,
        lease_in_hours: int = None,
        validate: bool = False,
    ) -> str:
        """
        Submits a slice request to FABRIC.

        Can be blocking or non-blocking.

        Blocking calls can, optionally,configure timeouts and intervals.

        Blocking calls can, optionally, print progress info.


        :param wait: indicator for whether to wait for the slice's resources to be active
        :type wait: bool

        :param wait_timeout: how many seconds to wait on the slice resources
        :type wait_timeout: int

        :param wait_interval: how often to check on the slice resources
        :type wait_interval: int

        :param progress: indicator for whether to show progress while waiting
        :type progress: bool

        :param wait_jupyter: Special wait for jupyter notebooks.
        :type wait_jupyter: str

        :param post_boot_config:
        :type post_boot_config: bool

        :param wait_ssh:
        :type wait_ssh: bool

        :param extra_ssh_keys: Optional list of additional SSH public keys to be installed in the slivers of this slice
        :type extra_ssh_keys: List[str]

        :param lease_start_time: Optional lease start time in UTC format: %Y-%m-%d %H:%M:%S %z.
                           Specifies the beginning of the time range to search for available resources valid for `lease_in_hours`.
        :type lease_start_time: datetime

        :param lease_end_time: Optional lease end time in UTC format: %Y-%m-%d %H:%M:%S %z.
                         Specifies the end of the time range to search for available resources valid for `lease_in_hours`.
        :type lease_end_time: datetime

        :param lease_in_hours: Optional lease duration in hours. By default, the slice remains active for 24 hours (1 day).
                               This parameter is only applicable during creation.
        :type lease_in_hours: int

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :return: slice_id
        """
        slice_reservations = None

        if not wait:
            progress = False

        if validate:
            self.validate()

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        start_time_str = (
            lease_start_time.strftime("%Y-%m-%d %H:%M:%S %z")
            if lease_start_time
            else None
        )
        end_time_str = (
            lease_end_time.strftime("%Y-%m-%d %H:%M:%S %z") if lease_end_time else None
        )

        # Create slice now or Renew slice
        if lease_in_hours and not lease_start_time and not lease_end_time:
            end_time_str = (
                datetime.now(timezone.utc) + timedelta(hours=lease_in_hours)
            ).strftime("%Y-%m-%d %H:%M:%S %z")

        # Request slice from Orchestrator
        if self._is_modify():
            if lease_in_hours:
                return_status, result = self.fablib_manager.get_manager().renew(
                    slice_object=self.sm_slice, new_lease_end_time=end_time_str
                )
            else:
                (
                    return_status,
                    slice_reservations,
                ) = self.fablib_manager.get_manager().modify(
                    slice_id=self.slice_id, slice_graph=slice_graph
                )
        else:
            # retrieve and validate SSH keys
            ssh_keys = list()
            ssh_keys.append(self.get_slice_public_key().strip())
            if extra_ssh_keys:
                if isinstance(extra_ssh_keys, list):
                    ssh_keys.extend(extra_ssh_keys)
                else:
                    logging.error(
                        "Extra SSH keys must be provided as a list of strings."
                    )
                    raise Exception(
                        "Extra SSH keys must be provided as a list of strings."
                    )
            # validate each key - this will throw an exception
            for ssh_key in ssh_keys:
                # this will throw an informative exception
                FABRICSSHKey.get_key_length(ssh_key)

            (
                return_status,
                slice_reservations,
            ) = self.fablib_manager.get_manager().create(
                slice_name=self.slice_name,
                slice_graph=slice_graph,
                ssh_key=ssh_keys,
                lease_end_time=end_time_str,
                lease_start_time=start_time_str,
                lifetime=lease_in_hours,
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

        if (
            progress
            and wait_jupyter == "text"
            and self.fablib_manager.is_jupyter_notebook()
        ):
            self.wait_jupyter(
                timeout=wait_timeout,
                interval=wait_interval,
                post_boot_config=post_boot_config,
            )
            return self.slice_id

        elif wait:
            self.update()

            self.wait(timeout=wait_timeout, interval=wait_interval)

            if wait_ssh:
                self.wait_ssh(
                    timeout=wait_timeout, interval=wait_interval, progress=progress
                )

            advance_allocation = self.is_advanced_allocation()
            if progress:
                if advance_allocation:
                    print("Future allocation - skipping post_boot_config ... ")
                else:
                    print("Running post boot config ... ", end="")

            if not advance_allocation and post_boot_config:
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

        There are several output options: "text", "pandas", and "json"
        that determine the format of the output that is returned and
        (optionally) displayed/printed.

        output: 'text': string formatted with tabular 'pandas': pandas
        dataframe 'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','State']

        filter_function: A lambda function to filter data by field
        values.

        Example: filter_function=lambda s: s['State'] == 'Active'

        :param output: output format
        :type output: str

        :param fields: list of fields (table columns) to show
        :type fields: List[str]

        :param colors: True to add colors to the table when possible
        :type colors: bool

        :param quiet: True to specify printing/display
        :type quiet: bool

        :param filter_function: lambda function
        :type filter_function: lambda

        :param pretty_names: Use "nicer" names in column headers.
            Default is ``True``.
        :type pretty_names: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and not "TicketReviewPolicy" in val:
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Closed":
                color = f"{Constants.ERROR_LIGHT_COLOR}"

            return "background-color: %s" % color

        def state_color(val):
            if val == "Active":
                color = f"{Constants.SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            elif val == "ActiveTicketed":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            elif val == "Failed":
                color = f"{Constants.ERROR_LIGHT_COLOR}"
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
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["error"]])

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
        :param pretty_names:
        :type pretty_names: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and "TicketReviewPolicy" not in val:
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Ticketed":
                return [f"background-color: {Constants.IN_PROGRESS_LIGHT_COLOR}"] * (
                    len(fields)
                )
            elif x.State == "None":
                return ["opacity: 50%"] * (len(fields))
            else:
                return ["background-color: "] * (len(fields))

        def state_color(val):
            if val == "Active":
                color = f"{Constants.SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed" or val == "Nascent" or val == "ActiveTicketed":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
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
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["error"]])

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
        :param pretty_names:
        :type pretty_names: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and not "TicketReviewPolicy" in val:
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Ticketed":
                return [f"background-color: {Constants.IN_PROGRESS_LIGHT_COLOR}"] * (
                    len(fields)
                )
            elif x.State == "None":
                return ["opacity: 50%"] * (len(fields))
            else:
                return ["background-color: "] * (len(fields))

        def state_color(val):
            if val == "Active":
                color = f"{Constants.SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color
            return "background-color: %s" % color

        table = []
        for node in self.get_nodes():
            table.append(node.toDict())

        table = sorted(table, key=lambda x: (x["name"]))

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
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["error"]])
        if table and not quiet:
            display(table)

        return table

    def list_facilities(
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
        :param pretty_names:
        :type pretty_names: bool

        :return: table in format specified by output parameter
        :rtype: Object
        """

        def error_color(val):
            # if 'Failure' in val:
            if val != "" and not "TicketReviewPolicy" in val:
                color = f"{Constants.ERROR_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color

            return "background-color: %s" % color

        def highlight(x):
            if x.State == "Ticketed":
                return [f"background-color: {Constants.IN_PROGRESS_LIGHT_COLOR}"] * (
                    len(fields)
                )
            elif x.State == "None":
                return ["opacity: 50%"] * (len(fields))
            else:
                return ["background-color: "] * (len(fields))

        def state_color(val):
            if val == "Active":
                color = f"{Constants.SUCCESS_LIGHT_COLOR}"
            elif val == "Ticketed":
                color = f"{Constants.IN_PROGRESS_LIGHT_COLOR}"
            else:
                color = ""
            # return 'color: %s' % color
            return "background-color: %s" % color

        table = []
        for fac in self.get_facilities():
            table.append(fac.toDict())

        table = sorted(table, key=lambda x: (x["name"]))

        if pretty_names:
            pretty_names_dict = FacilityPort.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        logging.debug(f"pretty_names_dict = {pretty_names_dict}")

        table = self.get_fablib_manager().list_table(
            table,
            fields=fields,
            title="Facilities",
            output=output,
            quiet=True,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

        if table and colors:
            if pretty_names:
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["State"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["Error"]])
            else:
                # table = table.map(highlight, axis=1)
                table = table.map(state_color, subset=pd.IndexSlice[:, ["state"]])
                table = table.map(error_color, subset=pd.IndexSlice[:, ["error"]])
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
        :param post_boot_config: Flag indicating if post boot config should be applied
        """

        if not wait:
            progress = False

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        (
            return_status,
            slice_reservations,
        ) = self.fablib_manager.get_manager().modify(
            slice_id=self.slice_id, slice_graph=slice_graph
        )
        if return_status != Status.OK:
            raise Exception(
                "Failed to submit modify slice: {}, {}".format(
                    return_status, slice_reservations
                )
            )

        logging.debug(f"slice_reservations: {slice_reservations}")

        if (
            progress
            and wait_jupyter == "text"
            and self.fablib_manager.is_jupyter_notebook()
        ):
            self.wait_jupyter(
                timeout=wait_timeout,
                interval=wait_interval,
                post_boot_config=post_boot_config,
            )
            return self.slice_id

        elif wait:
            self.wait_ssh(
                timeout=wait_timeout, interval=wait_interval, progress=progress
            )

            if progress:
                print("Running post boot config ... ", end="")

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
        return_status, topology = self.fablib_manager.get_manager().modify_accept(
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
        """
        Retrieve user data associated with the slice.
        """
        user_data = {}
        for node in self.get_nodes():
            user_data[node.get_name()] = node.get_user_data()

        for network in self.get_networks():
            user_data[network.get_name()] = network.get_user_data()

        for iface in self.get_interfaces():
            user_data[iface.get_name()] = iface.get_user_data()

        for component in self.get_components():
            user_data[component.get_name()] = component.get_user_data()

        return user_data

    def _is_modify(self) -> bool:
        """
        Indicate if we should submit a modify request to orchestrator.
        """
        if self.get_state() is None:
            return False
        else:
            return True

    def validate(self, raise_exception: bool = True) -> Tuple[bool, Dict[str, str]]:
        """
        Validate the slice w.r.t available resources before submission

        :param raise_exception: raise exception if validation fails
        :type raise_exception: bool

        :return: Tuple indicating status for validation and dictionary of the errors corresponding to
                 each requested node
        :rtype: Tuple[bool, Dict[str, str]]
        """
        allocated = {}
        errors = {}
        nodes_to_remove = []
        for n in self.get_nodes():
            status, error = self.get_fablib_manager().validate_node(
                node=n, allocated=allocated
            )
            if not status:
                nodes_to_remove.append(n)
                errors[n.get_name()] = error
                logging.warning(f"{n.get_name()} - {error}")
        for n in nodes_to_remove:
            n.delete()
        if raise_exception and len(errors):
            raise Exception(f"Slice validation failed - {errors}!")
        return len(errors) == 0, errors
