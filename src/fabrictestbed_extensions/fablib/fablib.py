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
import os
import logging
import random
from concurrent.futures import ThreadPoolExecutor

from IPython import get_ipython

from typing import List, Dict

from typing import TYPE_CHECKING

from fabrictestbed.util.constants import Constants
import pandas as pd
from ipaddress import IPv4Network, IPv6Network
from tabulate import tabulate
import json


if TYPE_CHECKING:
    from fabric_cf.orchestrator.swagger_client import Slice as OrchestratorSlice

from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fim.user import Node as FimNode

from fabrictestbed_extensions.fablib.resources import Resources, Links, FacilityPorts
from fabrictestbed_extensions.fablib.slice import Slice


class fablib:
    default_fablib_manager = None

    @staticmethod
    def get_default_fablib_manager():
        if fablib.default_fablib_manager is None:
            fablib.default_fablib_manager = FablibManager()

        return fablib.default_fablib_manager

    @staticmethod
    def get_image_names() -> List[str]:
        """
        Gets a list of available image names.

        :return: list of image names as strings
        :rtype: list[str]
        """
        return fablib.get_default_fablib_manager().get_image_names()

    @staticmethod
    def get_site_names() -> List[str]:
        """
        Gets a list of all available site names.

        :return: list of site names as strings
        :rtype: list[str]
        """
        return fablib.get_default_fablib_manager().get_site_names()

    @staticmethod
    def list_sites() -> str:
        """
        Get a string used to print a tabular list of sites with state

        :return: tabulated string of site state
        :rtype: str
        """
        return fablib.get_default_fablib_manager().list_sites()

    @staticmethod
    def list_links() -> object:
        """
        Print the links in pretty format

        :return: Formatted list of links
        :rtype: object
        """
        return fablib.get_default_fablib_manager().list_links()

    @staticmethod
    def get_links() -> str:
        """
        Get a string used to print a tabular list of links

        :return: tabulated string of links
        :rtype: str
        """
        return fablib.get_default_fablib_manager().get_links()

    @staticmethod
    def list_facility_ports() -> object:
        """
        Print the facility ports in pretty format

        :return: Formatted list of facility ports
        :rtype: object
        """
        return fablib.get_default_fablib_manager().list_facility_ports()

    @staticmethod
    def get_facility_ports() -> str:
        """
        Get a string used to print a tabular list of facility ports

        :return: tabulated string of facility ports
        :rtype: str
        """
        return fablib.get_default_fablib_manager().get_facility_ports()

    @staticmethod
    def show_site(site_name: str):
        """
        Get a string used to print tabular info about a site

        :param site_name: the name of a site
        :type site_name: String
        :return: tabulated string of site state
        :rtype: String
        """
        return fablib.get_default_fablib_manager().show_site(site_name)

    @staticmethod
    def get_resources() -> Resources:
        """
        Get a reference to the resources object. The resources object
        is used to query for available resources and capacities.

        :return: the resources object
        :rtype: Resources
        """
        return fablib.get_default_fablib_manager().get_resources()

    @staticmethod
    def get_random_site(avoid: List[str] = []) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid choosing
        :type site_name: List[String]
        :return: one site name
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_random_site(avoid=avoid)

    @staticmethod
    def get_random_sites(count: int = 1, avoid: List[str] = []) -> List[str]:
        """
        Get a list of random sites names. Each site will be included at most once.

        :param count: number of sites to return.
        :type count: int
        :param avoid: list of site names to avoid chosing
        :type site_name: List[String]
        :return: list of random site names.
        :rtype: List[Sting]
        """
        return fablib.get_default_fablib_manager().get_random_sites(
            count=count, avoid=avoid
        )

    @staticmethod
    def init_fablib():
        """
        Not intended to be called by the user.

        Static initializer for the fablib object.
        """
        return fablib.get_default_fablib_manager().init_fablib()

    @staticmethod
    def get_default_slice_key() -> Dict[str, str]:
        """
        Gets the current default_slice_keys as a dictionary containg the
        public and private slice keys.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: default_slice_key dictionary from superclass
        :rtype: Dict[String, String]
        """
        return fablib.get_default_fablib_manager().get_default_slice_key()

    @staticmethod
    def show_config():
        return fablib.get_default_fablib_manager().show_config()

    @staticmethod
    def get_config() -> Dict[str, str]:
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return fablib.get_default_fablib_manager().get_config()

    @staticmethod
    def get_default_slice_public_key() -> str:
        """
        Gets the default slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the slice public key on this fablib object
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_default_slice_public_key()

    @staticmethod
    def get_default_slice_public_key_file() -> str:
        """
        Gets the path to the default slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice public key on this fablib object
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_default_slice_public_key_file()

    @staticmethod
    def get_default_slice_private_key_file() -> str:
        """
        Gets the path to the default slice private key file.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice private key on this fablib object
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_default_slice_private_key_file()

    @staticmethod
    def get_default_slice_private_key_passphrase() -> str:
        """
        Gets the passphrase to the default slice private key.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the passphrase to the slice private key on this fablib object
        :rtype: String
        """
        return (
            fablib.get_default_fablib_manager().get_default_slice_private_key_passphrase()
        )

    @staticmethod
    def get_credmgr_host() -> str:
        """
        Gets the credential manager host site value.

        :return: the credential manager host site
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_credmgr_host()

    @staticmethod
    def get_orchestrator_host() -> str:
        """
        Gets the orchestrator host site value.

        :return: the orchestrator host site
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_orchestrator_host()

    @staticmethod
    def get_fabric_token() -> str:
        """
        Gets the FABRIC token location.

        :return: FABRIC token location
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_fabric_token()

    @staticmethod
    def get_bastion_username() -> str:
        """
        Gets the FABRIC Bastion username.

        :return: FABRIC Bastion username
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_bastion_username()

    @staticmethod
    def get_bastion_key_filename() -> str:
        """
        Gets the FABRIC Bastion key filename.

        :return: FABRIC Bastion key filename
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_bastion_key_filename()

    @staticmethod
    def get_bastion_public_addr() -> str:
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_bastion_public_addr()

    @staticmethod
    def get_bastion_private_ipv4_addr() -> str:
        """
        Gets the FABRIC Bastion private IPv4 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv4 address
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_bastion_private_ipv4_addr()

    @staticmethod
    def get_bastion_private_ipv6_addr() -> str:
        """
        Gets the FABRIC Bastion private IPv6 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv6 address
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_bastion_private_ipv6_addr()

    @staticmethod
    def get_slice_manager() -> SliceManager:
        """
        Not intended as API call


        Gets the slice manager of this fablib object.

        :return: the slice manager on this fablib object
        :rtype: SliceManager
        """
        return fablib.get_default_fablib_manager().get_slice_manager()

    @staticmethod
    def new_slice(name: str) -> Slice:
        """
        Creates a new slice with the given name.

        :param name: the name to give the slice
        :type name: String
        :return: a new slice
        :rtype: Slice
        """
        return fablib.get_default_fablib_manager().new_slice(name)

    @staticmethod
    def get_site_advertisement(site: str) -> FimNode:
        """
        Not intended for API use.

        Given a site name, gets fim topology object for this site.

        :param site: a site name
        :type site: String
        :return: fim object for this site
        :rtype: Node
        """
        return fablib.get_default_fablib_manager().get_site_advertisement(site)

    @staticmethod
    def get_available_resources(update: bool = False) -> Resources:
        """
        Get the available resources.

        Optionally update the availalbe resources by querying the FABRIC
        services. Otherwise, this method returns the exisitng information.

        :param site: update
        :type site: Bool
        :return: Availalbe Resources object
        :rtype: Resources
        """
        return fablib.get_default_fablib_manager().get_available_resources(
            update=update
        )

    @staticmethod
    def get_fim_slice(
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing]
    ) -> List[OrchestratorSlice]:
        """
        Not intended for API use.

        Gets a list of fim slices from the slice manager.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :return: a list of slices
        :rtype: List[Slice]
        """
        return fablib.get_default_fablib_manager().get_fim_slice(excludes=excludes)

    @staticmethod
    def get_slices(
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing]
    ) -> List[Slice]:
        """
        Gets a list of slices from the slice manager.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :return: a list of slices
        :rtype: List[Slice]
        """
        return fablib.get_default_fablib_manager().get_slices(excludes=excludes)

    @staticmethod
    def get_slice(name: str = None, slice_id: str = None) -> Slice:
        """
        Gets a slice by name or slice_id. Dead and Closing slices may have
        non-unique names and must be queried by slice_id.  Slices in all other
        states are guaranteed to have unique names and can be queried by name.

        If both a name and slicd_id are provided, the slice matching the
        slice_id will be returned.

        :param name: The name of the desired slice
        :type name: String
        :param slice_id: The ID of the desired slice
        :type slice_id: String
        :raises: Exception: if slice name or slice id are not inputted
        :return: the slice, if found
        :rtype: Slice
        """
        return fablib.get_default_fablib_manager().get_slice(
            name=name, slice_id=slice_id
        )

    @staticmethod
    def delete_slice(slice_name: str = None):
        """
        Deletes a slice by name.

        :param slice_name: the name of the slice to delete
        :type slice_name: String
        """
        return fablib.get_default_fablib_manager().delete_slice(slice_name=slice_name)

    @staticmethod
    def delete_all(progress: bool = True):
        """
        Deletes all slices on the slice manager.

        :param progress: optional progess printing to stdout
        :type progress: Bool
        """
        return fablib.get_default_fablib_manager().delete_all(progress=progress)

    @staticmethod
    def get_log_level():
        """
        Gets the current log level for logging
        """
        return fablib.get_default_fablib_manager().get_log_level()

    @staticmethod
    def set_log_level(log_level):
        """
        Sets the current log level for logging

        Options:  logging.DEBUG
                  logging.INFO
                  logging.WARNING
                  logging.ERROR
                  logging.CRITICAL

        :param log_level: new log level
        :type progress: Level
        """
        return fablib.get_default_fablib_manager().set_log_level(log_level)

    @staticmethod
    def is_jupyter_notebook() -> bool:
        return fablib.get_default_fablib_manager().is_jupyter_notebook()


class FablibManager:
    FABNETV4_SUBNET = IPv4Network("10.128.0.0/10")
    FABNETV6_SUBNET = IPv6Network("2602:FCFB:00::/40")

    FABRIC_BASTION_USERNAME = "FABRIC_BASTION_USERNAME"
    FABRIC_BASTION_KEY_LOCATION = "FABRIC_BASTION_KEY_LOCATION"
    FABRIC_BASTION_HOST = "FABRIC_BASTION_HOST"
    FABRIC_BASTION_KEY_PASSWORD = "FABRIC_BASTION_KEY_PASSWORD"
    FABRIC_BASTION_HOST_PRIVATE_IPV4 = "FABRIC_BASTION_HOST_PRIVATE_IPV4"
    FABRIC_BASTION_HOST_PRIVATE_IPV6 = "FABRIC_BASTION_HOST_PRIVATE_IPV6"
    FABRIC_SLICE_PUBLIC_KEY_FILE = "FABRIC_SLICE_PUBLIC_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_FILE = "FABRIC_SLICE_PRIVATE_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE = "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE"
    FABRIC_LOG_FILE = "FABRIC_LOG_FILE"
    FABRIC_LOG_LEVEL = "FABRIC_LOG_LEVEL"
    FABRIC_AVOID = "FABRIC_AVOID"
    FABRIC_SSH_COMMAND_LINE = "FABRIC_SSH_COMMAND_LINE"

    FABRIC_PRIMARY = "#27aae1"
    FABRIC_PRIMARY_LIGHT = "#cde4ef"
    FABRIC_PRIMARY_DARK = "#078ac1"
    FABRIC_SECONDARY = "#f26522"
    FABRIC_SECONDARY_LIGHT = "#ff8542"
    FABRIC_SECONDARY_DARK = "#d24502"
    FABRIC_BLACK = "#231f20"
    FABRIC_DARK = "#433f40"
    FABRIC_GREY = "#666677"
    FABRIC_LIGHT = "#f3f3f9"
    FABRIC_WHITE = "#ffffff"
    FABRIC_LOGO = "fabric_logo.png"

    FABRIC_PRIMARY_EXTRA_LIGHT = "#dbf3ff"

    SUCCESS_COLOR = "#8eff92"
    SUCCESS_LIGHT_COLOR = "#c3ffc4"
    SUCCESS_DARK_COLOR = "#59cb63"

    ERROR_COLOR = "#ff8589"
    ERROR_LIGHT_COLOR = "#ffb7b9"
    ERROR_DARK_COLOR = "#b34140"

    IN_PROGRESS_COLOR = "#ffff8c"
    IN_PROGRESS_LIGHT_COLOR = "#ffffbe"
    IN_PROGRESS_DARK_COLOR = "#c8555c"

    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    default_fabric_rc = os.environ["HOME"] + "/work/fabric_config/fabric_rc"
    default_log_level = "DEBUG"
    default_log_file = "/tmp/fablib/fablib.log"
    default_data_dir = "/tmp/fablib"

    fablib_object = None

    ssh_thread_pool_executor = None

    def read_fabric_rc(self, file_path: str):
        vars = {}

        # file_path = os.environ['HOME']+ "/work/fabric_config/fabric_rc"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    if line.startswith("export"):
                        var_name = line.split("=")[0].split("export")[1].strip()
                        var_value = line.split("=")[1].strip()
                        vars[var_name] = var_value
        return vars

    def __init__(
        self,
        fabric_rc: str = None,
        credmgr_host: str = None,
        orchestrator_host: str = None,
        fabric_token: str = None,
        project_id: str = None,
        bastion_username: str = None,
        bastion_key_filename: str = None,
        log_level: int = None,
        log_file: str = None,
        data_dir: str = None,
        output: str = None,
        execute_thread_pool_size: int = 64,
    ):
        """
        Constructor. Builds FablibManager.  Tries to get configuration from:

         - constructor parameters (high priority)
         - fabric_rc file (middle priority)
         - environment variables (low priority)
         - defaults (if needed and possible)

        """

        if output != None:
            self.output = output
        else:
            if self.is_jupyter_notebook():
                self.output = "pandas"
            else:
                self.output = "text"

        self.ssh_thread_pool_executor = ThreadPoolExecutor(execute_thread_pool_size)

        # Hack to avoid sites in maintence.  TODO: Make dynamic call to FABRIC API
        self.sites_in_maintenance = []

        # init attributes
        self.bastion_passphrase = None
        self.log_file = self.default_log_file
        self.log_level = self.default_log_level
        self.set_log_level(self.log_level)
        self.data_dir = None
        self.avoid = []
        self.ssh_command_line = "ssh ${Username}@${Management IP}"
        self.ssh_config_file = ""

        # Setup slice key dict
        # self.slice_keys = {}
        self.default_slice_key = {}

        # Set config values from env vars.
        self.credmgr_host = os.environ.get(Constants.FABRIC_CREDMGR_HOST)
        self.orchestrator_host = os.environ.get(Constants.FABRIC_ORCHESTRATOR_HOST)
        self.fabric_token = os.environ.get(Constants.FABRIC_TOKEN_LOCATION)
        self.project_id = os.environ.get(Constants.FABRIC_PROJECT_ID)

        # Bastion host setup.
        self.bastion_username = os.environ.get(self.FABRIC_BASTION_USERNAME)
        self.bastion_key_filename = os.environ.get(self.FABRIC_BASTION_KEY_LOCATION)
        self.bastion_public_addr = os.environ.get(self.FABRIC_BASTION_HOST)

        # if self.FABRIC_BASTION_HOST_PRIVATE_IPV4 in os.environ:
        #    self.bastion_private_ipv4_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV4]
        # if self.FABRIC_BASTION_HOST_PRIVATE_IPV6 in os.environ:
        #    self.bastion_private_ipv6_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV6]

        # Slice Keys
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in os.environ:
            self.default_slice_key["slice_public_key_file"] = os.environ[
                self.FABRIC_SLICE_PUBLIC_KEY_FILE
            ]
            with open(os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key["slice_public_key"] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in os.environ:
            # self.slice_private_key_file=os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']
            self.default_slice_key["slice_private_key_file"] = os.environ[
                self.FABRIC_SLICE_PRIVATE_KEY_FILE
            ]
        if "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE" in os.environ:
            # self.slice_private_key_passphrase = os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']
            self.default_slice_key["slice_private_key_passphrase"] = os.environ[
                self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE
            ]

        # Set config values from fabric_rc file
        if fabric_rc is None:
            fabric_rc = self.default_fabric_rc

        fabric_rc_dict = self.read_fabric_rc(fabric_rc)

        if Constants.FABRIC_CREDMGR_HOST in fabric_rc_dict:
            self.credmgr_host = fabric_rc_dict[Constants.FABRIC_CREDMGR_HOST]

        if Constants.FABRIC_ORCHESTRATOR_HOST in fabric_rc_dict:
            self.orchestrator_host = fabric_rc_dict[Constants.FABRIC_ORCHESTRATOR_HOST]

        if Constants.FABRIC_TOKEN_LOCATION in fabric_rc_dict:
            self.fabric_token = fabric_rc_dict[Constants.FABRIC_TOKEN_LOCATION]
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.fabric_token

        if Constants.FABRIC_PROJECT_ID in fabric_rc_dict:
            self.project_id = fabric_rc_dict[Constants.FABRIC_PROJECT_ID]
            os.environ[Constants.FABRIC_PROJECT_ID] = self.project_id

        # Basstion host setup
        if self.FABRIC_BASTION_HOST in fabric_rc_dict:
            self.bastion_public_addr = (
                fabric_rc_dict[self.FABRIC_BASTION_HOST].strip().strip('"')
            )
        if self.FABRIC_BASTION_USERNAME in fabric_rc_dict:
            self.bastion_username = (
                fabric_rc_dict[self.FABRIC_BASTION_USERNAME].strip().strip('"')
            )
        if self.FABRIC_BASTION_KEY_LOCATION in fabric_rc_dict:
            self.bastion_key_filename = (
                fabric_rc_dict[self.FABRIC_BASTION_KEY_LOCATION].strip().strip('"')
            )
        if self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE in fabric_rc_dict:
            self.bastion_key_filename = (
                fabric_rc_dict[self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]
                .strip()
                .strip('"')
            )

        # Slice keys
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in fabric_rc_dict:
            self.default_slice_key["slice_private_key_file"] = (
                fabric_rc_dict[self.FABRIC_SLICE_PRIVATE_KEY_FILE].strip().strip('"')
            )
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in fabric_rc_dict:
            self.default_slice_key["slice_public_key_file"] = (
                fabric_rc_dict[self.FABRIC_SLICE_PUBLIC_KEY_FILE].strip().strip('"')
            )
            with open(fabric_rc_dict[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key["slice_public_key"] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE in fabric_rc_dict:
            self.default_slice_key["slice_private_key_passphrase"] = fabric_rc_dict[
                self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE
            ]

        if self.FABRIC_LOG_FILE in fabric_rc_dict:
            self.set_log_file(fabric_rc_dict[self.FABRIC_LOG_FILE].strip().strip('"'))
        if self.FABRIC_LOG_LEVEL in fabric_rc_dict:
            self.set_log_level(fabric_rc_dict[self.FABRIC_LOG_LEVEL].strip().strip('"'))
        if self.FABRIC_AVOID in fabric_rc_dict:
            self.set_avoid_csv(
                fabric_rc_dict[self.FABRIC_AVOID].strip().strip('"').strip("'")
            )
        if self.FABRIC_SSH_COMMAND_LINE in fabric_rc_dict:
            self.set_ssh_command_line(
                fabric_rc_dict[self.FABRIC_SSH_COMMAND_LINE]
                .strip()
                .strip('"')
                .strip("'")
            )

        # Set config values from constructor arguments
        if credmgr_host is not None:
            self.credmgr_host = credmgr_host
        if orchestrator_host is not None:
            self.orchestrator_host = orchestrator_host
        if fabric_token is not None:
            self.fabric_token = fabric_token
        if project_id is not None:
            self.project_id = project_id
        if bastion_username is not None:
            self.bastion_username = bastion_username
        if bastion_key_filename is not None:
            self.bastion_key_filename = bastion_key_filename
        if log_level is not None:
            self.set_log_level(log_level)
        if log_file is not None:
            self.log_level = log_file
        if data_dir is not None:
            self.data_dir = data_dir

        self.set_log_file(log_file=self.log_file)

        # if self.log_file is not None and self.log_level is not None:
        #    logging.basicConfig(filename=self.log_file, level=self.LOG_LEVELS[self.log_level],
        #                        format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
        #                        datefmt='%H:%M:%S')

        self.bastion_private_ipv4_addr = "0.0.0.0"
        self.bastion_private_ipv6_addr = "0:0:0:0:0:0"

        self._validate_configuration()

        # Create slice manager
        self.slice_manager = None
        self.resources = None
        self.links = None
        self.facility_ports = None
        self.build_slice_manager()

    def _validate_configuration(self):
        """
        Raise an error if we don't have the required configuration.
        """
        errors = []

        required_attrs = {
            "orchestrator_host": "orchestrator host",
            "credmgr_host": "credmanager host",
            "fabric_token": "FABRIC token",
            "project_id": "project ID",
            "bastion_username": "bastion username",
            "bastion_key_filename": "bastion key file",
            "bastion_public_addr": "bastion host address",
        }

        for attr, value in required_attrs.items():
            if not hasattr(self, attr) or getattr(self, attr) is None:
                errors.append(f"{value} is not set")

        if errors:
            # TODO: define custom exception class to report errors,
            # and emit a more helpful error message with hints about
            # setting up environment variables or configuration file.
            raise AttributeError(
                f"Error initializing {self.__class__.__name__}: {errors}"
            )

    def get_ssh_thread_pool_executor(self) -> ThreadPoolExecutor:
        return self.ssh_thread_pool_executor

    # def set_data_dir(self, data_dir: str):
    #    """
    #    Sets the directory for fablib to store temporary data
    #
    #    :param data_dir: new log data_dir
    #    :type data_dir: String
    #    """
    #    self.data_dir = data_dir
    #
    #    try:
    #        if not os.path.isdir(self.data_dir):
    #            os.makedirs(self.data_dir)
    #    except Exception as e:
    #        logging.warning(f"Failed to create data dir: {self.data_dir}")

    def get_ssh_command_line(self):
        return self.ssh_command_line

    def set_ssh_command_line(self, command):
        self.ssh_command_line = command

    def set_avoid_csv(self, avoid_csv: str = ""):
        avoid_csv = avoid_csv.strip().strip('"').strip("'")

        avoid = []
        for site in avoid_csv.split(","):
            avoid.append(site.strip())

        self.set_avoid(avoid)

    def set_avoid(self, avoid: list = []):
        logging.info(f"Setting global avoid list: {avoid}")
        self.avoid = avoid

    def get_avoid(self):
        return self.avoid

    def set_log_level(self, log_level: str = "INFO"):
        """
        Sets the current log level for logging

        Options:  'DEBUG'
                  'INFO'
                  'WARNING'
                  'ERROR'
                  'CRITICAL'

        :param log_level: new log level
        :type str: Level
        """

        self.log_level = log_level

        try:
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
        except Exception as e:
            pass

        try:
            if self.log_file and not os.path.isdir(os.path.dirname(self.log_file)):
                os.makedirs(os.path.dirname(self.log_file))
        except Exception as e:
            pass
            # logging.warning(f"Failed to create log_file directory: {os.path.dirname(self.log_file)}")

        if self.log_file and self.log_level:
            logging.basicConfig(
                filename=self.log_file,
                level=self.LOG_LEVELS[self.log_level],
                format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )

    def get_log_level(self):
        """
        Get the current log level for logging

        :return log_file: new log level
        :rtype log_file: string
        """

        return self.log_level

    def get_log_file(self) -> str:
        """
        Gets the current log file for logging

        :return log_file: new log level
        :rtype log_file: string
        """

        return self.log_file

    def set_log_file(self, log_file: str):
        """
        Sets the current log file for logging

        :param log_file: new log level
        :type log_file: string
        """
        self.log_file = log_file

        try:
            if not os.path.isdir(os.path.dirname(self.log_file)):
                os.makedirs(os.path.dirname(self.log_file))
        except Exception as e:
            pass
            # logging.warning(f"Failed to create log_file directory: {os.path.dirname(self.log_file)}")

        try:
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
        except:
            pass

        logging.basicConfig(
            filename=self.log_file,
            level=self.LOG_LEVELS[self.log_level],
            format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )

    def build_slice_manager(self) -> SliceManager:
        """
        Not a user facing API call.

        Creates a new SliceManager object.

        :return: a new SliceManager
        :rtype: SliceManager
        """
        try:
            logging.info(
                f"oc_host={self.orchestrator_host},"
                f"cm_host={self.credmgr_host},"
                f"project_id={self.project_id},"
                f"token_location={self.fabric_token},"
                f"initialize=True,"
                f"scope='all'"
            )

            self.slice_manager = SliceManager(
                oc_host=self.orchestrator_host,
                cm_host=self.credmgr_host,
                project_id=self.project_id,
                token_location=self.fabric_token,
                initialize=True,
                scope="all",
            )

            # Initialize the slice manager
            self.slice_manager.initialize()
        except Exception as e:
            # logging.error(f"{e}")
            logging.error(e, exc_info=True)
            raise e

        return self.slice_manager

    def get_image_names(self) -> List[str]:
        """
        Gets a list of available image names.

        This is statically defined for now. Eventually, images will be managed dynamically.

        :return: list of image names as strings
        :rtype: list[str]
        """
        return [
            "default_centos8_stream",
            "default_centos9_stream",
            "default_centos_7",
            "default_centos_8",
            "default_cirros",
            "default_debian_10",
            "default_fedora_35",
            "default_freebsd_13_zfs",
            "default_openbsd_7",
            "default_rocky_8",
            "default_ubuntu_18",
            "default_ubuntu_20",
            "default_ubuntu_21",
            "default_ubuntu_22",
        ]

    def get_site_names(self) -> List[str]:
        """
        Gets a list of all available site names.

        :return: list of site names as strings
        :rtype: list[str]
        """
        return self.get_resources().get_site_names()

    def list_sites(
        self,
        output: str = None,
        fields: str = None,
        quiet: bool = False,
        filter_function=None,
        update: bool = True,
        pretty_names=True,
    ) -> object:
        """
        Lists all the sites and their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','ConnectX-5 Available', 'NVMe Total']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['ConnectX-5 Available'] > 3 and s['NVMe Available'] <= 10

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
        return self.get_resources(update=update).list_sites(
            output=output,
            fields=fields,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names=pretty_names,
        )

    def list_links(
        self,
        output: str = None,
        fields: str = None,
        quiet: bool = False,
        filter_function=None,
        update: bool = True,
        pretty_names=True,
    ) -> object:
        """
        Lists all the links and their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: TODO

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['ConnectX-5 Available'] > 3 and s['NVMe Available'] <= 10

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
        return self.get_links(update=update).list_links(
            output=output,
            fields=fields,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names=pretty_names,
        )

    def list_facility_ports(
        self,
        output: str = None,
        fields: str = None,
        quiet: bool = False,
        filter_function=None,
        update: bool = True,
        pretty_names=True,
    ) -> object:
        """
        Lists all the facility ports and their attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: TODO

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['ConnectX-5 Available'] > 3 and s['NVMe Available'] <= 10

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
        return self.get_facility_ports(update=update).list_facility_ports(
            output=output,
            fields=fields,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names=pretty_names,
        )

    def show_config(
        self,
        output: str = None,
        fields: list[str] = None,
        quiet: bool = False,
        pretty_names=True,
    ):
        """
        Show a table containing the current FABlib configuration parameters.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['credmgr_host','project_id', 'fablib_log_file']

        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        if pretty_names:
            pretty_names_dict = self.get_config_pretty_names_dict()
        else:
            pretty_names_dict = {}

        return self.show_table(
            self.get_config(),
            fields=fields,
            title="FABlib Config",
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

    def show_site(
        self,
        site_name: str,
        output: str = None,
        fields: list[str] = None,
        quiet: bool = False,
        pretty_names=True,
    ):
        """
        Show a table with all the properties of a specific site

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['credmgr_host','project_id', 'fablib_log_file']

        :param site_name: the name of a site
        :type site_name: str
        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """
        return str(
            self.get_resources().show_site(
                site_name,
                fields=fields,
                output=output,
                quiet=quiet,
                pretty_names=pretty_names,
            )
        )

    def get_links(self, update: bool = True) -> Links:
        """
        Get the links.

        Optionally update the available resources by querying the FABRIC
        services. Otherwise, this method returns the existing information.

        :param update:
        :return: Links
        """

        if self.links is None:
            self.links = Links(self)
        elif update:
            self.links.update()

        return self.links

    def get_facility_ports(self, update: bool = True) -> FacilityPorts:
        """
        Get the facility ports.

        Optionally update the available resources by querying the FABRIC
        services. Otherwise, this method returns the existing information.

        :param update:
        :return: Links
        """
        if self.facility_ports is None:
            self.facility_ports = FacilityPorts(self)
        elif update:
            self.facility_ports.update()

        return self.facility_ports

    def get_resources(self, update: bool = True) -> Resources:
        """
        Get a reference to the resources object. The resources object
        is used to query for available resources and capacities.

        :return: the resources object
        :rtype: Resources
        """
        if not self.resources:
            self.get_available_resources(update=update)

        return self.resources

    def get_random_site(
        self, avoid: List[str] = [], filter_function=None, update: bool = True
    ) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid choosing
        :type site_name: List[String]
        :return: one site name
        :rtype: String
        """
        return self.get_random_sites(
            count=1, avoid=avoid, filter_function=filter_function, update=update
        )[0]

    def get_random_sites(
        self,
        count: int = 1,
        avoid: List[str] = [],
        filter_function=None,
        update: bool = True,
        unique: bool = True,
    ) -> List[str]:
        """
        Get a list of random sites names. Each site will be included at most once.

        :param count: number of sites to return.
        :type count: int
        :param avoid: list of site names to avoid chosing
        :type site_name: List[String]
        :return: list of random site names.
        :rtype: List[Sting]
        """

        # Always filter out sites in maintenance and sites that can't support any VMs
        def combined_filter_function(site):
            if filter_function == None:
                if site["state"] == "Active" and site["hosts"] > 0:
                    return True
            else:
                if (
                    filter_function(site)
                    and site["state"] == "Active"
                    and site["hosts"] > 0
                ):
                    return True

            return False

        for site in self.get_avoid():
            if site not in avoid:
                avoid.append(site)

        site_list = self.list_sites(
            output="list",
            quiet=True,
            filter_function=combined_filter_function,
            update=update,
        )

        sites = list(map(lambda x: x["name"], site_list))

        # sites = self.get_resources().get_site_list()
        for site in avoid:
            if site in sites:
                sites.remove(site)

        rtn_sites = []
        for i in range(count):
            if len(sites) > 0:
                rand_site = random.choice(sites)
                sites.remove(rand_site)
                rtn_sites.append(rand_site)
            else:
                rtn_sites.append(None)
        return rtn_sites

    def get_default_slice_key(self) -> Dict[str, str]:
        """
        Gets the current default_slice_keys as a dictionary containg the
        public and private slice keys.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: default_slice_key dictionary from superclass
        :rtype: Dict[String, String]
        """
        return self.default_slice_key

    def get_config_pretty_names_dict(self):
        return {
            "credmgr_host": "Credential Manager",
            "orchestrator_host": "Orchestrator",
            "fabric_token": "Token File",
            "project_id": "Project ID",
            "bastion_username": "Bastion Username",
            "bastion_private_key_file": "Bastion Private Key File",
            "bastion_host": "Bastion Host",
            "bastion_private_key_passphrase": "Bastion Private Key Passphrase",
            "slice_public_key_file": "Slice Public Key File",
            "slice_private_key_file": "Slice Private Key File",
            "fabric_slice_private_key_passphrase": "Slice Private Key Passphrase",
            "fablib_log_file": "Log File",
            "fablib_log_level": "Log Level",
        }

    def get_config(self) -> Dict[str, Dict[str, str]]:
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return {
            "credmgr_host": self.credmgr_host,
            "orchestrator_host": self.orchestrator_host,
            "fabric_token": self.fabric_token,
            "project_id": self.project_id,
            "bastion_username": self.bastion_username,
            "bastion_private_key_file": self.bastion_key_filename,
            "bastion_host": self.bastion_public_addr,
            "bastion_private_key_passphrase": self.bastion_passphrase,
            "slice_public_key_file": self.get_default_slice_public_key_file(),
            "slice_private_key_file": self.get_default_slice_private_key_file(),
            "fabric_slice_private_key_passphrase": self.get_default_slice_private_key_passphrase(),
            "fablib_log_file": self.get_log_file(),
            "fablib_log_level": self.get_log_level(),
        }

    def get_configXXX(self) -> Dict[str, Dict[str, str]]:
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return {
            "credmgr_host": {
                "pretty_name": "Credential Manager",
                "value": self.credmgr_host,
            },
            "orchestrator_host": {
                "pretty_name": "Orchestrator",
                "value": self.orchestrator_host,
            },
            "fabric_token": {"pretty_name": "Token File", "value": self.fabric_token},
            "project_id": {"pretty_name": "Project ID", "value": self.project_id},
            "bastion_username": {
                "pretty_name": "Bastion Username",
                "value": self.bastion_username,
            },
            "bastion_private_key_file": {
                "pretty_name": "Bastion Private Key File",
                "value": self.bastion_key_filename,
            },
            "bastion_host": {
                "pretty_name": "Bastion Host",
                "value": self.bastion_public_addr,
            },
            "bastion_private_key_passphrase": {
                "pretty_name": "Bastion Private Key Passphrase",
                "value": self.bastion_passphrase,
            },
            "slice_public_key_file": {
                "pretty_name": "Slice Public Key File",
                "value": self.get_default_slice_public_key_file(),
            },
            "slice_private_key_file": {
                "pretty_name": "Slice Private Key File",
                "value": self.get_default_slice_private_key_file(),
            },
            "fabric_slice_private_key_passphrase": {
                "pretty_name": "Slice Private Key Passphrase",
                "value": self.get_default_slice_private_key_passphrase(),
            },
            "fablib_log_file": {
                "pretty_name": "Log File",
                "value": self.get_log_file(),
            },
            "fablib_log_level": {
                "pretty_name": "Log Level",
                "value": self.get_log_level(),
            },
        }

    def get_default_slice_public_key(self) -> str:
        """
        Gets the default slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the slice public key on this fablib object
        :rtype: String
        """
        if "slice_public_key" in self.default_slice_key.keys():
            return self.default_slice_key["slice_public_key"]
        else:
            return None

    def get_default_slice_public_key_file(self) -> str:
        """
        Gets the path to the default slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice public key on this fablib object
        :rtype: String
        """
        if "slice_public_key_file" in self.default_slice_key.keys():
            return self.default_slice_key["slice_public_key_file"]
        else:
            return None

    def get_default_slice_private_key_file(self) -> str:
        """
        Gets the path to the default slice private key file.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice private key on this fablib object
        :rtype: String
        """
        if "slice_private_key_file" in self.default_slice_key.keys():
            return self.default_slice_key["slice_private_key_file"]
        else:
            return None

    def get_default_slice_private_key_passphrase(self) -> str:
        """
        Gets the passphrase to the default slice private key.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the passphrase to the slice private key on this fablib object
        :rtype: String
        """
        if "slice_private_key_passphrase" in self.default_slice_key.keys():
            return self.default_slice_key["slice_private_key_passphrase"]
        else:
            return None

    def get_credmgr_host(self) -> str:
        """
        Gets the credential manager host site value.

        :return: the credential manager host site
        :rtype: String
        """
        return self.credmgr_host

    def get_orchestrator_host(self) -> str:
        """
        Gets the orchestrator host site value.

        :return: the orchestrator host site
        :rtype: String
        """
        return self.orchestrator_host

    def get_fabric_token(self) -> str:
        """
        Gets the FABRIC token location.

        :return: FABRIC token location
        :rtype: String
        """
        return self.fabric_token

    def get_bastion_username(self) -> str:
        """
        Gets the FABRIC Bastion username.

        :return: FABRIC Bastion username
        :rtype: String
        """
        return self.bastion_username

    def get_bastion_key_filename(self) -> str:
        """
        Gets the FABRIC Bastion key filename.

        :return: FABRIC Bastion key filename
        :rtype: String
        """
        return self.bastion_key_filename

    def get_bastion_public_addr(self) -> str:
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return self.bastion_public_addr

    def get_bastion_private_ipv4_addr(self) -> str:
        """
        Gets the FABRIC Bastion private IPv4 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv4 address
        :rtype: String
        """
        return self.bastion_private_ipv4_addr

    def get_bastion_private_ipv6_addr(self) -> str:
        """
        Gets the FABRIC Bastion private IPv6 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv6 address
        :rtype: String
        """
        return self.bastion_private_ipv6_addr

    def set_slice_manager(self, slice_manager: SliceManager):
        """
        Not intended as API call

        Sets the slice manager of this fablib object.

        :param slice_manager: the slice manager to set
        :type slice_manager: SliceManager
        """
        self.slice_manager = slice_manager

    def get_slice_manager(self) -> SliceManager:
        """
        Not intended as API call


        Gets the slice manager of this fablib object.

        :return: the slice manager on this fablib object
        :rtype: SliceManager
        """
        return self.slice_manager

    def new_slice(self, name: str) -> Slice:
        """
        Creates a new slice with the given name.

        :param name: the name to give the slice
        :type name: String
        :return: a new slice
        :rtype: Slice
        """
        # fabric = fablib()
        return Slice.new_slice(self, name=name)

    def get_site_advertisement(self, site: str) -> FimNode:
        """
        Not intended for API use.

        Given a site name, gets fim topology object for this site.

        :param site: a site name
        :type site: String
        :return: fim object for this site
        :rtype: Node
        """
        logging.info(f"Updating get_site_advertisement")
        return_status, topology = self.get_slice_manager().resources()
        if return_status != Status.OK:
            raise Exception(
                "Failed to get advertised_topology: {}, {}".format(
                    return_status, topology
                )
            )

        return topology.sites[site]

    def get_available_resources(self, update: bool = False) -> Resources:
        """
        Get the available resources.

        Optionally update the available resources by querying the FABRIC
        services. Otherwise, this method returns the existing information.

        :param update:
        :return: Available Resources object
        """
        from fabrictestbed_extensions.fablib.resources import Resources

        if self.resources is None:
            self.resources = Resources(self)
        elif update:
            self.resources.update()

        return self.resources

    def get_fim_slices(
        self, excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing]
    ) -> List[OrchestratorSlice]:
        """
        Gets a list of fim slices from the slice manager.

        This is not recommened for most users and should only be used to bypass fablib inorder
        to create custom low-level functionality.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :return: a list of fim models of slices
        :rtype: List[Slice]
        """
        return_status, slices = self.get_slice_manager().slices(
            excludes=excludes, limit=200
        )

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(slice)
        else:
            raise Exception(f"Failed to get slice list: {slices}")
        return return_slices

    # def tabulate_slices(self, slices):
    #     table = []
    #     for slice in slices:
    #         table.append([slice.get_slice_id(),
    #                       slice.get_name(),
    #                       slice.get_lease_end(),
    #                       slice.get_state(),
    #                       ])
    #
    #     return tabulate(table, headers=["ID", "Name", "Lease Expiration (UTC)", "State"])

    def list_slices(
        self,
        excludes=[SliceState.Dead, SliceState.Closing],
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        """
        Lists all the slices created by a user.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields/columns.

        Example: fields=['Name','State']

        filter_function:  A lambda function to filter data by field values.

        Example: filter_function=lambda s: s['State'] == 'Configuring'

        :param excludes: slice status to exclude
        :type excludes: list[slice.state]
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
        for slice in self.get_slices(excludes=excludes):
            table.append(slice.toDict())
            # table.append({"ID": slice.get_slice_id(),
            #              "Name": slice.get_name(),
            #              "Lease Expiration (UTC)": slice.get_lease_end(),
            #              "Lease Start (UTC)": slice.get_lease_start(),
            #              "Project ID": slice.get_project_id(),
            #              "State": slice.get_state(),
            #              })

        # if fields == None:
        #    fields = ["ID", "Name", "Lease Expiration (UTC)", "Lease Start (UTC)", "Project ID", "State"]

        if pretty_names:
            pretty_names_dict = Slice.get_pretty_names_dict()
        else:
            pretty_names_dict = {}

        return self.list_table(
            table,
            fields=fields,
            title="Slices",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

    def show_slice(
        self,
        name: str = None,
        id: str = None,
        output=None,
        fields=None,
        quiet=False,
        pretty_names=True,
    ):
        """
        Show a table with all the properties of a specific site

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['Name','State']

        :param name: the name of a slice
        :type name: str
        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        slice = self.get_slice(name=name, slice_id=id)

        return slice.show(
            output=output, fields=fields, quiet=quiet, pretty_names=pretty_names
        )

    def get_slices(
        self,
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing],
        slice_name: str = None,
        slice_id: str = None,
    ) -> List[Slice]:
        """
        Gets a list of slices from the slice manager.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :param slice_name
        :param slice_id
        :return: a list of slices
        :rtype: List[Slice]
        """
        import time

        if self.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = self.get_slice_manager().slices(
            excludes=excludes, name=slice_name, slice_id=slice_id, limit=200
        )

        if self.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(
                f"Running self.get_slice_manager().slices(): elapsed time: {end - start} seconds"
            )

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(Slice.get_slice(self, sm_slice=slice))
        else:
            raise Exception(f"Failed to get slices: {slices}")
        return return_slices

    def get_slice(self, name: str = None, slice_id: str = None) -> Slice:
        """
        Gets a slice by name or slice_id. Dead and Closing slices may have
        non-unique names and must be queried by slice_id.  Slices in all other
        states are guaranteed to have unique names and can be queried by name.

        If both a name and slicd_id are provided, the slice matching the
        slice_id will be returned.

        :param name: The name of the desired slice
        :type name: String
        :param slice_id: The ID of the desired slice
        :type slice_id: String
        :raises: Exception: if slice name or slice id are not inputted
        :return: the slice, if found
        :rtype: Slice
        """
        # Get the appropriate slices list
        if slice_id:
            # if getting by slice_id consider all slices
            slices = self.get_slices(excludes=[], slice_id=slice_id)

            if len(slices) == 1:
                return slices[0]
            else:
                raise Exception(f"More than 1 slice found with slice_id: {slice_id}")
        elif name:
            # if getting by name then only consider active slices
            slices = self.get_slices(
                excludes=[SliceState.Dead, SliceState.Closing], slice_name=name
            )

            return slices[0]
        else:
            raise Exception(
                "get_slice requires slice name (name) or slice id (slice_id)"
            )

    def delete_slice(self, slice_name: str = None):
        """
        Deletes a slice by name.

        :param slice_name: the name of the slice to delete
        :type slice_name: String
        """
        slice = self.get_slice(slice_name)
        slice.delete()

    def delete_all(self, progress: bool = True):
        """
        Deletes all slices on the slice manager.

        :param progress: optional progess printing to stdout
        :type progress: Bool
        """
        slices = self.get_slices()

        for slice in slices:
            try:
                if progress:
                    print(f"Deleting slice {slice.get_name()}", end="")
                slice.delete()
                if progress:
                    print(f", Success!")
            except Exception as e:
                if progress:
                    print(f", Failed!")

    def is_jupyter_notebook(self) -> bool:
        """
        Test for running inside a jupyter notebook

        :return: bool, True if in jupyter notebook
        :rtype: bool
        """
        try:
            shell = get_ipython().__class__.__name__
            if shell == "ZMQInteractiveShell":
                return True  # Jupyter notebook or qtconsole
            elif shell == "TerminalInteractiveShell":
                return False  # Terminal running IPython
            else:
                return False  # Other type (?)
        except NameError:
            return False

    def show_table_text(self, table, quiet=False):
        printable_table = tabulate(table)

        if not quiet:
            print(f"\n{printable_table}")

        return printable_table

    def show_table_jupyter(
        self, table, headers=None, title="", title_font_size="1.25em", quiet=False
    ):
        printable_table = pd.DataFrame(table)

        properties = {  # 'background-color': f'{FablibManager.FABRIC_LIGHT}',
            "text-align": "left",
            "border": f"1px {FablibManager.FABRIC_BLACK} solid !important",
        }

        printable_table = printable_table.style.set_caption(title)
        printable_table = printable_table.set_properties(**properties, overwrite=False)
        printable_table = printable_table.hide(axis="index")
        printable_table = printable_table.hide(axis="columns")

        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(even)",
                    "props": [
                        ("background", f"{FablibManager.FABRIC_PRIMARY_EXTRA_LIGHT}"),
                        ("color", f"{FablibManager.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )
        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(odd)",
                    "props": [
                        ("background", f"{FablibManager.FABRIC_WHITE}"),
                        ("color", f"{FablibManager.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )

        caption_props = [
            ("text-align", "center"),
            ("font-size", "150%"),
            # ("color", f'{FablibManager.FABRIC_BLACK}'),
            # ("background-color", f'{FablibManager.FABRIC_WHITE}'),
            # ("font-family", "courier"),
            # ("font-family", "montserrat"),
            # ("font-family", "IBM plex sans")'
        ]

        printable_table = printable_table.set_table_styles(
            [{"selector": "caption", "props": caption_props}], overwrite=False
        )

        if not quiet:
            display(printable_table)

        return printable_table

    def show_table_json(self, data, quiet=False):
        json_str = json.dumps(data, indent=4)

        if not quiet:
            print(f"{json_str}")

        return json_str

    def show_table_dict(self, data, quiet=False):
        if not quiet:
            print(f"{data}")

        return data

    def show_table(
        self,
        data,
        fields=None,
        title="",
        title_font_size="1.25em",
        output=None,
        quiet=False,
        pretty_names_dict={},
    ):
        if output == None:
            output = self.output.lower()

        table = self.create_show_table(
            data, fields=fields, pretty_names_dict=pretty_names_dict
        )

        if output == "text" or output == "default":
            return self.show_table_text(table, quiet=quiet)
        elif output == "json":
            return self.show_table_json(data, quiet=quiet)
        elif output == "dict":
            return self.show_table_dict(data, quiet=quiet)
        elif output == "pandas" or output == "jupyter_default":
            return self.show_table_jupyter(
                table,
                headers=fields,
                title=title,
                title_font_size=title_font_size,
                quiet=quiet,
            )
        else:
            logging.error(f"Unknown output type: {output}")

    def list_table_text(self, table, headers=None, quiet=False):
        if headers is not None:
            printable_table = tabulate(table, headers=headers)
        else:
            printable_table = tabulate(table)

        if not quiet:
            print(f"\n{printable_table}")

        return printable_table

    def list_table_jupyter(
        self,
        table,
        headers=None,
        title="",
        title_font_size="1.25em",
        output=None,
        quiet=False,
    ):
        if len(table) == 0:
            return None

        if headers is not None:
            printable_table = pd.DataFrame(table, columns=headers)
        else:
            printable_table = pd.DataFrame(table)

        # Table config (maybe some of this is unnecessary?
        # df.style.set_properties(**{'background-color': 'black',
        #                   'color': 'green'})

        properties = {  # 'background-color': f'{FablibManager.FABRIC_LIGHT}',
            "text-align": "left",
            "border": f"1px {FablibManager.FABRIC_BLACK} solid !important",
        }

        printable_table = printable_table.style.set_caption(title)
        printable_table = printable_table.hide(axis="index")
        # printable_table = printable_table.set_properties(**{'text-align': 'left'}, overwrite=False)
        printable_table = printable_table.set_properties(**properties, overwrite=False)

        caption_props = [
            ("text-align", "center"),
            ("font-size", "150%"),
            ("caption-side", "top"),
            # ("color", f'{FablibManager.FABRIC_BLACK}'),
            # ("background-color", f'{FablibManager.FABRIC_WHITE}'),
            # ("font-family", "courier"),
            # ("font-family", "montserrat"),
            # ("font-family", "IBM plex sans")'
        ]

        printable_table = printable_table.set_table_styles(
            [{"selector": "caption", "props": caption_props}], overwrite=False
        )

        printable_table = printable_table.set_table_styles(
            [dict(selector="th", props=[("text-align", "left")])], overwrite=False
        )
        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(even)",
                    "props": [
                        ("background", f"{FablibManager.FABRIC_WHITE}"),
                        ("color", f"{FablibManager.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )
        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(odd)",
                    "props": [
                        ("background", f"{FablibManager.FABRIC_PRIMARY_EXTRA_LIGHT}"),
                        ("color", f"{FablibManager.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )

        printable_table = printable_table.set_table_styles(
            [
                dict(
                    selector=".level0",
                    props=[
                        ("border", "1px black solid !important"),
                        ("background", f"{FablibManager.FABRIC_WHITE}"),
                        ("color", f"{FablibManager.FABRIC_BLACK}"),
                    ],
                )
            ],
            overwrite=False,
        )

        if not quiet:
            display(printable_table)

        return printable_table

    def list_table_json(self, data, quiet=False):
        json_str = json.dumps(data, indent=4)

        if not quiet:
            print(f"{json_str}")

        return json_str

    def list_table_list(self, data, quiet=False):
        if not quiet:
            print(f"{data}")

        return data

    def list_table(
        self,
        data,
        fields=None,
        title="",
        title_font_size="1.25em",
        output=None,
        quiet=False,
        filter_function=None,
        pretty_names_dict={},
    ):
        if filter_function:
            data = list(filter(filter_function, data))

        logging.debug(f"data: {data}\n\n")

        if output == None:
            output = self.output.lower()

        if fields == None and len(data) > 0:
            fields = list(data[0].keys())

        if fields == None:
            fields = []

        logging.debug(f"fields: {fields}\n\n")

        headers = []
        for field in fields:
            if field in pretty_names_dict:
                headers.append(pretty_names_dict[field])
            else:
                headers.append(field)

        logging.debug(f"headers: {headers}\n\n")

        if output == "text":
            table = self.create_list_table(data, fields=fields)
            return self.list_table_text(table, headers=headers, quiet=quiet)
        elif output == "json":
            return self.list_table_json(data, quiet=quiet)
        elif output == "list":
            return self.list_table_list(data, quiet=quiet)
        elif output == "pandas":
            table = self.create_list_table(data, fields=fields)

            return self.list_table_jupyter(
                table,
                headers=headers,
                title=title,
                title_font_size=title_font_size,
                output=output,
                quiet=quiet,
            )
        else:
            logging.error(f"Unknown output type: {output}")

    def create_list_table(self, data, fields=None):
        table = []
        for entry in data:
            row = []
            for field in fields:
                row.append(entry[field])

            table.append(row)
        return table

    def create_list_tableXXX(self, data, fields=None):
        table = []
        for entry in data:
            row = []
            for field in fields:
                row.append(entry[field])

            table.append(row)
        return table

    def create_show_table(self, data, fields=None, pretty_names_dict={}):
        table = []
        if fields == None:
            for key, value in data.items():
                if key in pretty_names_dict:
                    table.append([pretty_names_dict[key], value])
                else:
                    table.append([key, value])
        else:
            for field in fields:
                value = data[field]
                if field in pretty_names_dict:
                    table.append([pretty_names_dict[field], value])
                else:
                    table.append([field, value])

        return table

    def create_show_tableXXX(self, data, fields=None):
        table = []
        if fields == None:
            for key, value in data.items():
                table.append([key, value])
        else:
            for field in fields:
                table.append([field, data[field]])
        return table

    # @staticmethod
    # def remove_dict_pretty_names(dict):
    #    rtn_dict = {}
    #    for key, value in dict.items():
    #        rtn_dict[key] = value['value']
    #    return rtn_dict
