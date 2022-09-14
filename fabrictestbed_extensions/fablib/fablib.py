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
from tabulate import tabulate

if TYPE_CHECKING:
    from fabric_cf.orchestrator.swagger_client import Slice as OrchestratorSlice

from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fim.user import Node as FimNode

from fabrictestbed_extensions.fablib.resources import Resources
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
        return fablib.get_default_fablib_manager().get_random_sites(count=count, avoid=avoid)

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
        return fablib.get_default_fablib_manager().get_default_slice_private_key_passphrase()

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
    def get_site_advertisment(site: str) -> FimNode:
        """
        Not intended for API use.

        Given a site name, gets fim topology object for this site.

        :param site: a site name
        :type site: String
        :return: fim object for this site
        :rtype: Node
        """
        return fablib.get_default_fablib_manager().get_site_advertisment(site)

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
        return fablib.get_default_fablib_manager().get_available_resources(update=update)

    @staticmethod
    def get_fim_slice(excludes: List[SliceState] = [SliceState.Dead,SliceState.Closing]) -> List[OrchestratorSlice]:
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
    def get_slices(excludes: List[SliceState] = [SliceState.Dead,SliceState.Closing]) -> List[Slice]:
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
        return fablib.get_default_fablib_manager().get_slice(name=name, slice_id=slice_id)

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
    FABRIC_BASTION_USERNAME = "FABRIC_BASTION_USERNAME"
    FABRIC_BASTION_KEY_LOCATION = "FABRIC_BASTION_KEY_LOCATION"
    FABRIC_BASTION_HOST = "FABRIC_BASTION_HOST"
    FABRIC_BASTION_KEY_PASSWORD = "FABRIC_BASTION_KEY_PASSWORD"
    FABRIC_BASTION_HOST_PRIVATE_IPV4 = "FABRIC_BASTION_HOST_PRIVATE_IPV4"
    FABRIC_BASTION_HOST_PRIVATE_IPV6 = "FABRIC_BASTION_HOST_PRIVATE_IPV6"
    FABRIC_SLICE_PUBLIC_KEY_FILE = "FABRIC_SLICE_PUBLIC_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_FILE = "FABRIC_SLICE_PRIVATE_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE = "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE"
    FABRIC_LOG_FILE = 'FABRIC_LOG_FILE'
    FABRIC_LOG_LEVEL = 'FABRIC_LOG_LEVEL'

    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    default_fabric_rc = os.environ['HOME'] + '/work/fabric_config/fabric_rc'
    default_log_level = 'INFO'
    default_log_file = '/tmp/fablib/fablib.log'
    default_data_dir = '/tmp/fablib'

    fablib_object = None

    ssh_thread_pool_executor = None

    def read_fabric_rc(self, file_path: str):
        vars = {}

        # file_path = os.environ['HOME']+ "/work/fabric_config/fabric_rc"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('export'):
                        var_name = line.split('=')[0].split('export')[1].strip()
                        var_value = line.split('=')[1].strip()
                        vars[var_name] = var_value
        return vars

    def __init__(self,
                 fabric_rc: str = None,
                 credmgr_host: str = None,
                 orchestrator_host: str = None,
                 fabric_token: str = None,
                 project_id: str = None,
                 bastion_username: str = None,
                 bastion_key_filename: str = None,
                 log_level=None,
                 log_file: str = None,
                 data_dir: str = None):
        """
        Constructor. Builds FablibManager.  Tries to get configuration from:

         - constructor parameters (high priority)
         - fabric_rc file (middle priority)
         - environment variables (low priority)
         - defaults (if needed and possible)

        """
        self.ssh_thread_pool_executor = ThreadPoolExecutor(10)

        # init attributes
        self.bastion_passphrase = None
        self.log_file = self.default_log_file
        self.log_level = self.default_log_level
        self.set_log_level(self.log_level)
        self.data_dir = None

        # Setup slice key dict
        # self.slice_keys = {}
        self.default_slice_key = {}

        # Set config values from env vars
        if Constants.FABRIC_CREDMGR_HOST in os.environ:
            self.credmgr_host = os.environ[Constants.FABRIC_CREDMGR_HOST]

        if Constants.FABRIC_ORCHESTRATOR_HOST in os.environ:
            self.orchestrator_host = os.environ[Constants.FABRIC_ORCHESTRATOR_HOST]

        if Constants.FABRIC_TOKEN_LOCATION in os.environ:
            self.fabric_token = os.environ[Constants.FABRIC_TOKEN_LOCATION]

        if Constants.FABRIC_PROJECT_ID in os.environ:
            self.project_id = os.environ[Constants.FABRIC_PROJECT_ID]

        # Basstion host setup
        if self.FABRIC_BASTION_USERNAME in os.environ:
            self.bastion_username = os.environ[self.FABRIC_BASTION_USERNAME]
        if self.FABRIC_BASTION_KEY_LOCATION in os.environ:
            self.bastion_key_filename = os.environ[self.FABRIC_BASTION_KEY_LOCATION]
        if self.FABRIC_BASTION_HOST in os.environ:
            self.bastion_public_addr = os.environ[self.FABRIC_BASTION_HOST]
        # if self.FABRIC_BASTION_HOST_PRIVATE_IPV4 in os.environ:
        #    self.bastion_private_ipv4_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV4]
        # if self.FABRIC_BASTION_HOST_PRIVATE_IPV6 in os.environ:
        #    self.bastion_private_ipv6_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV6]

        # Slice Keys
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in os.environ:
            self.default_slice_key['slice_public_key_file'] = os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE]
            with open(os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key['slice_public_key'] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in os.environ:
            # self.slice_private_key_file=os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']
            self.default_slice_key['slice_private_key_file'] = os.environ[self.FABRIC_SLICE_PRIVATE_KEY_FILE]
        if "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE" in os.environ:
            # self.slice_private_key_passphrase = os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']
            self.default_slice_key['slice_private_key_passphrase'] = os.environ[
                self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]

        # Set config values from fabric_rc file
        if fabric_rc is None:
            fabric_rc = self.default_fabric_rc

        fabric_rc_dict = self.read_fabric_rc(fabric_rc)

        if Constants.FABRIC_CREDMGR_HOST in fabric_rc_dict:
            self.credmgr_host = fabric_rc_dict[Constants.FABRIC_CREDMGR_HOST]

        if Constants.FABRIC_ORCHESTRATOR_HOST in fabric_rc_dict:
            self.orchestrator_host = fabric_rc_dict[Constants.FABRIC_ORCHESTRATOR_HOST]

        if 'FABRIC_TOKEN_LOCATION' in fabric_rc_dict:
            self.fabric_token = fabric_rc_dict['FABRIC_TOKEN_LOCATION']
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.fabric_token

        if 'FABRIC_PROJECT_ID' in fabric_rc_dict:
            self.project_id = fabric_rc_dict['FABRIC_PROJECT_ID']
            os.environ['FABRIC_PROJECT_ID'] = self.project_id

        # Basstion host setup
        if self.FABRIC_BASTION_HOST in fabric_rc_dict:
            self.bastion_public_addr = fabric_rc_dict[self.FABRIC_BASTION_HOST]
        if self.FABRIC_BASTION_USERNAME in fabric_rc_dict:
            self.bastion_username = fabric_rc_dict[self.FABRIC_BASTION_USERNAME]
        if self.FABRIC_BASTION_KEY_LOCATION in fabric_rc_dict:
            self.bastion_key_filename = fabric_rc_dict[self.FABRIC_BASTION_KEY_LOCATION]
        if self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE in fabric_rc_dict:
            self.bastion_key_filename = fabric_rc_dict[self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]

        # Slice keys
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in fabric_rc_dict:
            self.default_slice_key['slice_private_key_file'] = fabric_rc_dict[self.FABRIC_SLICE_PRIVATE_KEY_FILE]
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in fabric_rc_dict:
            self.default_slice_key['slice_public_key_file'] = fabric_rc_dict[self.FABRIC_SLICE_PUBLIC_KEY_FILE]
            with open(fabric_rc_dict[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key['slice_public_key'] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE in fabric_rc_dict:
            self.default_slice_key['slice_private_key_passphrase'] = fabric_rc_dict[
                self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]

        if self.FABRIC_LOG_FILE in fabric_rc_dict:
            self.set_log_file(fabric_rc_dict[self.FABRIC_LOG_FILE])
        if self.FABRIC_LOG_LEVEL in fabric_rc_dict:
            self.set_log_level(fabric_rc_dict[self.FABRIC_LOG_LEVEL])

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
        self.set_data_dir(data_dir=self.data_dir)

        if self.log_file is not None and self.log_level is not None:
            logging.basicConfig(filename=self.log_file, level=self.LOG_LEVELS[self.log_level],
                                format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                                datefmt='%H:%M:%S')

        self.bastion_private_ipv4_addr = '0.0.0.0'
        self.bastion_private_ipv6_addr = '0:0:0:0:0:0'

        # Create slice manager
        self.slice_manager = None
        self.resources = None
        self.build_slice_manager()

    def get_ssh_thread_pool_executor(self) -> ThreadPoolExecutor:
        return self.ssh_thread_pool_executor

    def set_data_dir(self, data_dir: str):
        """
        Sets the directory for fablib to store temporary data

        :param data_dir: new log data_dir
        :type data_dir: String
        """
        self.data_dir = data_dir

        try:
            if not os.path.isdir(self.data_dir):
                os.makedirs(self.data_dir)
        except Exception as e:
            logging.warning(f"Failed to create data dir: {self.data_dir}")

    def set_log_level(self, log_level):
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

        self.log_level = log_level

    def get_log_file(self) -> str:
        """
        Gets the current log file for logging

        :return log_file: new log level
        :rtype log_file: string
        """
        try:
            if not os.path.isdir(os.path.dirname(self.log_file)):
                os.makedirs(os.path.dirname(self.log_file))
        except Exception as e:
            logging.warning(f"Failed to create log_file directory: {os.path.dirname(self.log_file)}")

        logging.basicConfig(filename=self.log_file, level=self.LOG_LEVELS[self.log_level],
                            format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                            datefmt='%H:%M:%S')
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
            logging.warning(f"Failed to create log_file directory: {os.path.dirname(self.log_file)}")

        logging.basicConfig(filename=self.log_file, level=self.LOG_LEVELS[self.log_level],
                            format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                            datefmt='%H:%M:%S')

    def build_slice_manager(self) -> SliceManager:
        """
        Not a user facing API call.

        Creates a new SliceManager object.

        :return: a new SliceManager
        :rtype: SliceManager
        """
        try:
            self.slice_manager = SliceManager(oc_host=self.orchestrator_host,
                                              cm_host=self.credmgr_host,
                                              project_id=self.project_id,
                                              token_location=self.fabric_token,
                                              initialize=True,
                                              scope='all')

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

        :return: list of image names as strings
        :rtype: list[str]
        """
        return ['default_centos8_stream',
                'default_centos9_stream',
                'default_centos_7',
                'default_centos_8',
                'default_cirros',
                'default_debian_10',
                'default_fedora_35',
                'default_freebsd_13_zfs',
                'default_openbsd_7',
                'default_rocky_8',
                'default_ubuntu_18',
                'default_ubuntu_20',
                'default_ubuntu_21',
                'default_ubuntu_22']

    def get_site_names(self) -> List[str]:
        """
        Gets a list of all available site names.

        :return: list of site names as strings
        :rtype: list[str]
        """
        return self.get_resources().get_site_names()

    def list_sites(self) -> str:
        """
        Get a string used to print a tabular list of sites with state

        :return: tabulated string of site state
        :rtype: str
        """
        return str(self.get_resources())

    def show_site(self, site_name: str):
        """
        Get a string used to print tabular info about a site

        :param site_name: the name of a site
        :type site_name: String
        :return: tabulated string of site state
        :rtype: String
        """
        return str(self.get_resources().show_site(site_name))

    def get_resources(self) -> Resources:
        """
        Get a reference to the resources object. The resouces obeject
        is used to query for available resources and capacities.

        :return: the resouces object
        :rtype: Resources
        """
        if not self.resources:
            self.get_available_resources()

        return self.resources

    def get_random_site(self, avoid: List[str] = []) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid choosing
        :type site_name: List[String]
        :return: one site name
        :rtype: String
        """
        return self.get_random_sites(count=1, avoid=avoid)[0]

    def get_random_sites(self, count: int = 1, avoid: List[str] = []) -> List[str]:
        """
        Get a list of random sites names. Each site will be included at most once.

        :param count: number of sites to return.
        :type count: int
        :param avoid: list of site names to avoid chosing
        :type site_name: List[String]
        :return: list of random site names.
        :rtype: List[Sting]
        """
        # Hack to always avoid a list of sites. Real fix is to check availability
        always_avoid = []

        for site in always_avoid:
            if site not in avoid:
                avoid.append(site)

        sites = self.get_resources().get_site_list()
        for site in avoid:
            if site in sites:
                sites.remove(site)

        rtn_sites = []
        for i in range(count):
            rand_site = random.choice(sites)
            sites.remove(rand_site)
            rtn_sites.append(rand_site)
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

    def show_config(self):
        table = []
        for var, val in self.get_config().items():
            table.append([str(var), str(val)])

        print(f"{tabulate(table)}")

        return

    def get_config(self) -> Dict[str, str]:
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return {'credmgr_host': self.credmgr_host,
                'orchestrator_host': self.orchestrator_host,
                'fabric_token': self.fabric_token,
                'project_id': self.project_id,
                'bastion_username': self.bastion_username,
                'bastion_key_filename': self.bastion_key_filename,
                'bastion_public_addr': self.bastion_public_addr,
                'bastion_passphrase': self.bastion_passphrase,
                # 'bastion_private_ipv4_addr': self.bastion_private_ipv4_addr,
                # 'slice_public_key': self.get_default_slice_public_key(),
                'slice_public_key_file': self.get_default_slice_public_key_file(),
                'slice_private_key_file': self.get_default_slice_private_key_file(),
                'fabric_slice_private_key_passphrase': self.get_default_slice_private_key_passphrase(),
                'fablib_log_file': self.get_log_file(),
                'fablib_log_level': self.get_log_level()

                }

    def get_default_slice_public_key(self) -> str:
        """
        Gets the default slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the slice public key on this fablib object
        :rtype: String
        """
        if 'slice_public_key' in self.default_slice_key.keys():
            return self.default_slice_key['slice_public_key']
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
        if 'slice_public_key_file' in self.default_slice_key.keys():
            return self.default_slice_key['slice_public_key_file']
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
        if 'slice_private_key_file' in self.default_slice_key.keys():
            return self.default_slice_key['slice_private_key_file']
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
        if 'slice_private_key_passphrase' in self.default_slice_key.keys():
            return self.default_slice_key['slice_private_key_passphrase']
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

    def get_site_advertisment(self, site: str) -> FimNode:
        """
        Not intended for API use.

        Given a site name, gets fim topology object for this site.

        :param site: a site name
        :type site: String
        :return: fim object for this site
        :rtype: Node
        """
        return_status, topology = self.get_slice_manager().resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))

        return topology.sites[site]

    def get_available_resources(self, update: bool = False) -> Resources:
        """
        Get the available resources.

        Optionally update the availalbe resources by querying the FABRIC
        services. Otherwise, this method returns the exisitng information.

        :param update:
        :return: Availalbe Resources object
        """
        from fabrictestbed_extensions.fablib.resources import Resources

        if self.resources is None:
            self.resources = Resources(self)

        if update:
            self.resources.update()

        return self.resources

    def get_fim_slice(self, excludes: List[SliceState] = [SliceState.Dead,SliceState.Closing]) -> List[OrchestratorSlice]:
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
        return_status, slices = self.get_slice_manager().slices(excludes=excludes)

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(slice)
        else:
            raise Exception(f"Failed to get slice list: {slices}")
        return return_slices

    def get_slices(self, excludes: List[SliceState] = [SliceState.Dead,SliceState.Closing],
                   slice_name: str = None, slice_id: str = None) -> List[Slice]:
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

        return_status, slices = self.get_slice_manager().slices(excludes=excludes, name=slice_name, slice_id=slice_id)

        if self.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(f"Running self.get_slice_manager().slices(): elapsed time: {end - start} seconds")

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
            slices = self.get_slices(excludes=[SliceState.Dead, SliceState.Closing], slice_name=name)

            return slices[0]
        else:
            raise Exception("get_slice requires slice name (name) or slice id (slice_id)")

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
                if progress: print(f"Deleting slice {slice.get_name()}", end='')
                slice.delete()
                if progress: print(f", Success!")
            except Exception as e:
                if progress: print(f", Failed!")

    def get_log_level(self):
        """
        Gets the current log level for logging
        """
        return self.log_level

    def is_jupyter_notebook(self) -> bool:
        try:
            shell = get_ipython().__class__.__name__
            if shell == 'ZMQInteractiveShell':
                return True  # Jupyter notebook or qtconsole
            elif shell == 'TerminalInteractiveShell':
                return False  # Terminal running IPython
            else:
                return False  # Other type (?)
        except NameError:
            return False
