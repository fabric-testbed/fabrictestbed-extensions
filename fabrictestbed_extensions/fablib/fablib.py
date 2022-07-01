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
import random

from IPython import get_ipython
from tabulate import tabulate

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, \
    ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)

from fabrictestbed.util.constants import Constants
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from concurrent.futures import ThreadPoolExecutor

# from .abc_fablib import AbcFabLIB
#from fabrictestbed_extensions.fablib.fablib_manager import FablibManager


# from .. import images


class fablib():
    default_fablib_manager = None

    @staticmethod
    def get_fablib_manager():
        return

    @staticmethod
    def get_image_names() -> list[str]:
        """
        Gets a list of available image names.

        :return: list of image names as strings
        :rtype: list[str]
        """
        return fablib.default_fablib_manager.get_image_names()

    @staticmethod
    def get_site_names() -> list[str]:
        """
        Gets a list of all available site names.

        :return: list of site names as strings
        :rtype: list[str]
        """
        return fablib.default_fablib_manager().get_site_names()

    @staticmethod
    def list_sites() -> str:
        """
        Get a string used to print a tabular list of sites with state

        :return: tabulated string of site state
        :rtype: str
        """
        return fablib.default_fablib_manager.list_sites()

    @staticmethod
    def show_site(site_name):
        """
        Get a string used to print tabular info about a site

        :param site_name: the name of a site
        :type site_name: String
        :return: tabulated string of site state
        :rtype: String
        """
        return fablib.default_fablib_manager.show_site(site_name)

    @staticmethod
    def get_resources():
        """
        Get a reference to the resources object. The resources object
        is used to query for available resources and capacities.

        :return: the resources object
        :rtype: Resources
        """
        return fablib.default_fablib_manager.get_resources()

    @staticmethod
    def get_random_site(avoid: list[str] = []) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid choosing
        :type site_name: List[String]
        :return: one site name
        :rtype: String
        """
        return fablib.default_fablib_manager.get_random_site(avoid=avoid)

    @staticmethod
    def get_random_sites(count: int = 1, avoid: list[str] = []) -> list[str]:
        """
        Get a list of random sites names. Each site will be included at most once.

        :param count: number of sites to return.
        :type count: int
        :param avoid: list of site names to avoid chosing
        :type site_name: List[String]
        :return: list of random site names.
        :rtype: List[Sting]
        """
        return fablib.default_fablib_manager.get_random_sites(count=count, avoid=avoid)

    @staticmethod
    def init_fablib():
        """
        Not intended to be called by the user.

        Static initializer for the fablib object.
        """
        return fablib.default_fablib_manager.init_fablib()

    @staticmethod
    def get_default_slice_key():
        """
        Gets the current default_slice_keys as a dictionary containg the
        public and private slice keys.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: default_slice_key dictionary from superclass
        :rtype: Dict[String, String]
        """
        return fablib.default_fablib_manager.get_default_slice_key()

    @staticmethod
    def show_config():
        return fablib.default_fablib_manager.show_config()

    @staticmethod
    def get_config():
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return fablib.default_fablib_manager.get_config()

    @staticmethod
    def get_default_slice_public_key():
        """
        Gets the default slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the slice public key on this fablib object
        :rtype: String
        """
        return fablib.default_fablib_manager.get_default_slice_public_key()

    @staticmethod
    def get_default_slice_public_key_file():
        """
        Gets the path to the default slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice public key on this fablib object
        :rtype: String
        """
        return fablib.default_fablib_manager.get_default_slice_public_key_file()

    @staticmethod
    def get_default_slice_private_key_file():
        """
        Gets the path to the default slice private key file.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice private key on this fablib object
        :rtype: String
        """
        return fablib.default_fablib_manager.get_default_slice_private_key_file()

    @staticmethod
    def get_default_slice_private_key_passphrase():
        """
        Gets the passphrase to the default slice private key.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the passphrase to the slice private key on this fablib object
        :rtype: String
        """
        return fablib.default_fablib_manager.get_default_slice_private_key_passphrase()

    @staticmethod
    def get_credmgr_host():
        """
        Gets the credential manager host site value.

        :return: the credential manager host site
        :rtype: String
        """
        return fablib.default_fablib_manager.get_credmgr_host()

    @staticmethod
    def get_orchestrator_host():
        """
        Gets the orchestrator host site value.

        :return: the orchestrator host site
        :rtype: String
        """
        return fablib.default_fablib_manager.get_orchestrator_host()

    @staticmethod
    def get_fabric_token():
        """
        Gets the FABRIC token location.

        :return: FABRIC token location
        :rtype: String
        """
        return fablib.default_fablib_manager.get_fabric_token()

    @staticmethod
    def get_bastion_username():
        """
        Gets the FABRIC Bastion username.

        :return: FABRIC Bastion username
        :rtype: String
        """
        return fablib.default_fablib_manager.get_bastion_username()

    @staticmethod
    def get_bastion_key_filename():
        """
        Gets the FABRIC Bastion key filename.

        :return: FABRIC Bastion key filename
        :rtype: String
        """
        return fablib.default_fablib_manager.get_bastion_key_filename()

    @staticmethod
    def get_bastion_public_addr():
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return fablib.default_fablib_manager.get_bastion_public_addr()

    @staticmethod
    def get_bastion_private_ipv4_addr():
        """
        Gets the FABRIC Bastion private IPv4 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv4 address
        :rtype: String
        """
        return fablib.default_fablib_manager.get_bastion_private_ipv4_addr()

    @staticmethod
    def get_bastion_private_ipv6_addr():
        """
        Gets the FABRIC Bastion private IPv6 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv6 address
        :rtype: String
        """
        return fablib.default_fablib_manager.get_bastion_private_ipv6_addr()

    @staticmethod
    def get_slice_manager():
        """
        Not intended as API call


        Gets the slice manager of this fablib object.

        :return: the slice manager on this fablib object
        :rtype: SliceManager
        """
        return fablib.default_fablib_manager.get_slice_manager()

    @staticmethod
    def new_slice(name):
        """
        Creates a new slice with the given name.

        :param name: the name to give the slice
        :type name: String
        :return: a new slice
        :rtype: Slice
        """
        return fablib.default_fablib_manager.new_slice(name)

    @staticmethod
    def get_site_advertisment(site):
        """
        Not intended for API use.

        Given a site name, gets fim topology object for this site.

        :param site: a site name
        :type site: String
        :return: fim object for this site
        :rtype: Node
        """
        return fablib.default_fablib_manager.get_site_advertisment(site)

    @staticmethod
    def get_available_resources(update=False):
        """
        Get the available resources.

        Optionally update the availalbe resources by querying the FABRIC
        services. Otherwise, this method returns the exisitng information.

        :param site: update
        :type site: Bool
        :return: Availalbe Resources object
        :rtype: Resources
        """
        return fablib.default_fablib_manager.get_available_resources(update=update)

    @staticmethod
    def get_fim_slice(excludes=[SliceState.Dead, SliceState.Closing]):
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
        return fablib.default_fablib_manager.get_fim_slice(excludes=excludes)

    @staticmethod
    def get_slices(excludes=[SliceState.Dead, SliceState.Closing]):
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
        return fablib.default_fablib_manager.XXget_slices(excludes=excludes)

    @staticmethod
    def get_slice(name=None, slice_id=None):
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
        return fablib.default_fablib_manager.get_slice(name=name, slice_id=slice_id)

    @staticmethod
    def delete_slice(slice_name=None):
        """
        Deletes a slice by name.

        :param slice_name: the name of the slice to delete
        :type slice_name: String
        """
        return fablib.default_fablib_manager.delete_slice(slice_name=slice_name)

    @staticmethod
    def delete_all(progress=True):
        """
        Deletes all slices on the slice manager.

        :param progress: optional progess printing to stdout
        :type progress: Bool
        """
        return fablib.default_fablib_manager.delete_all(progress=progress)

    @staticmethod
    def get_log_level():
        """
        Gets the current log level for logging
        """
        return fablib.default_fablib_manager.get_log_level()

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
        return fablib.default_fablib_manager.set_log_level(log_level)

    @staticmethod
    def isJupyterNotebook():
        return fablib.default_fablib_manager.isJupyterNotebook()


class FablibManager():
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


    def read_fabric_rc(self, file_path):
        vars = {}

        # file_path = os.environ[‘HOME’]+”/work/fabric_config/fabric_rc”
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('export'):
                        var_name = line.split('=')[0].split('export')[1].strip()
                        var_value = line.split('=')[1].strip()
                        vars[var_name] = var_value
        return vars

    def __init__(self,
                 fabric_rc=None,
                 credmgr_host=None,
                 orchestrator_host=None,
                 fabric_token=None,
                 project_id=None,
                 bastion_username=None,
                 bastion_key_filename=None,
                 log_level=None,
                 log_file=None,
                 data_dir=None):
        """
        Constructor. Builds FablibManager.  Tries to get configuration from:

         - constructor parameters (high priority)
         - fabric_rc file (middle priority)
         - environment variables (low priority)
         - defaults (if needed and possible)

        """
        super().__init__()

        #initialized thread pool for ssh connections
        self.ssh_thread_pool_executor = ThreadPoolExecutor(10)

        # init attributes
        self.bastion_passphrase = None
        self.log_file = self.default_log_file
        self.log_level = self.default_log_level
        self.set_log_level(self.log_level)

        #self.set_log_file(log_file)
        self.data_dir = data_dir

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
        if fabric_rc == None:
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
        if credmgr_host != None:
            self.credmgr_host = credmgr_host
        if orchestrator_host != None:
            self.orchestrator_host = orchestrator_host
        if fabric_token != None:
            self.fabric_token = fabric_token
        if project_id != None:
            self.project_id = project_id
        if bastion_username != None:
            self.bastion_username = bastion_username
        if bastion_key_filename != None:
            self.bastion_key_filename = bastion_key_filename
        if log_level != None:
            self.set_log_level(log_level)
        if log_file != None:
            self.set_log_file(log_file)
        if data_dir != None:
            self.data_dir = data_dir




        # self.bastion_private_ipv4_addr = '0.0.0.0'
        # self.bastion_private_ipv6_addr = '0:0:0:0:0:0'

        # Create slice manager
        self.slice_manager = None
        self.resources = None
        self.build_slice_manager()


    def get_ssh_thread_pool_executor(self):
        return self.ssh_thread_pool_executor

    def set_data_dir(self, data_dir):
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

        logging.basicConfig(filename=self.log_file, level=self.LOG_LEVELS[self.log_level],
                            format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                            datefmt='%H:%M:%S')

    def get_log_file(self):
        return self.log_file

    def set_log_file(self, log_file):
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

    def build_slice_manager(self):
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

        return self.slice_manager

    def get_image_names(self) -> list[str]:
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

    def get_site_names(self) -> list[str]:
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

    def show_site(self, site_name):
        """
        Get a string used to print tabular info about a site

        :param site_name: the name of a site
        :type site_name: String
        :return: tabulated string of site state
        :rtype: String
        """
        return str(self.get_resources().show_site(site_name))

    def get_resources(self):
        """
        Get a reference to the resources object. The resouces obeject
        is used to query for available resources and capacities.

        :return: the resouces object
        :rtype: Resources
        """
        if not self.resources:
            self.get_available_resources()

        return self.resources

    def get_random_site(self, avoid: list[str] = []) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid chosing
        :type site_name: List[String]
        :return: one site name
        :rtype: String
        """
        return self.get_random_sites(count=1, avoid=avoid)[0]

    def get_random_sites(self, count: int = 1, avoid: list[str] = []) -> list[str]:
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

    def get_default_slice_key(self):
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
        for var, val in self.get_config().items():
            print(f"{var} = {val}")

        return

    def get_config(self):
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

    def get_default_slice_public_key(self):
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

    def get_default_slice_public_key_file(self):
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

    def get_default_slice_private_key_file(self):
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

    def get_default_slice_private_key_passphrase(self):
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

    def get_credmgr_host(self):
        """
        Gets the credential manager host site value.

        :return: the credential manager host site
        :rtype: String
        """
        return self.credmgr_host

    def get_orchestrator_host(self):
        """
        Gets the orchestrator host site value.

        :return: the orchestrator host site
        :rtype: String
        """
        return self.orchestrator_host

    def get_fabric_token(self):
        """
        Gets the FABRIC token location.

        :return: FABRIC token location
        :rtype: String
        """
        return self.fabric_token

    def get_bastion_username(self):
        """
        Gets the FABRIC Bastion username.

        :return: FABRIC Bastion username
        :rtype: String
        """
        return self.bastion_username

    def get_bastion_key_filename(self):
        """
        Gets the FABRIC Bastion key filename.

        :return: FABRIC Bastion key filename
        :rtype: String
        """
        return self.bastion_key_filename

    def get_bastion_public_addr(self):
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return self.bastion_public_addr

    def get_bastion_private_ipv4_addr(self):
        """
        Gets the FABRIC Bastion private IPv4 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv4 address
        :rtype: String
        """
        return self.bastion_private_ipv4_addr

    def get_bastion_private_ipv6_addr(self):
        """
        Gets the FABRIC Bastion private IPv6 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv6 address
        :rtype: String
        """
        return self.bastion_private_ipv6_addr

    def set_slice_manager(self, slice_manager):
        """
        Not intended as API call

        Sets the slice manager of this fablib object.

        :param slice_manager: the slice manager to set
        :type slice_manager: SliceManager
        """
        self.slice_manager = slice_manager

    def get_slice_manager(self):
        """
        Not intended as API call


        Gets the slice manager of this fablib object.

        :return: the slice manager on this fablib object
        :rtype: SliceManager
        """
        return self.slice_manager

    def new_slice(self, name):
        """
        Creates a new slice with the given name.

        :param name: the name to give the slice
        :type name: String
        :return: a new slice
        :rtype: Slice
        """
        # fabric = fablib()
        from fabrictestbed_extensions.fablib.slice import Slice
        return Slice.new_slice(self, name=name)

    def get_site_advertisment(self, site):
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

    def get_available_resources(self, update=False):
        """
        Get the available resources.

        Optionally update the availalbe resources by querying the FABRIC
        services. Otherwise, this method returns the exisitng information.

        :param site: update
        :type site: Bool
        :return: Availalbe Resources object
        :rtype: Resources
        """
        from fabrictestbed_extensions.fablib.resources import Resources

        if self.resources == None:
            self.resources = Resources(self)

        if update:
            self.resources.update()

        return self.resources

    def get_fim_slice(self, excludes=[SliceState.Dead, SliceState.Closing]):
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

    def get_slices(self, excludes=[SliceState.Dead, SliceState.Closing]):
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
        from fabrictestbed_extensions.fablib.slice import Slice
        import time

        if self.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = self.get_slice_manager().slices(excludes=excludes)

        if self.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(f"Running self.get_slice_manager().slices(): elapsed time: {end - start} seconds")

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(Slice.get_slice(self, sm_slice=slice, load_config=False))
        else:
            raise Exception(f"Failed to get slices: {slices}")
        return return_slices

    def get_slice(self, name=None, slice_id=None):
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
        # Get the appropriat slices list
        if slice_id:
            # if getting by slice_id consider all slices
            slices = self.get_slices(excludes=[])

            for slice in slices:
                if slice_id != None and slice.get_slice_id() == slice_id:
                    return slice
        elif name:
            # if getting by name then only consider active slices
            slices = self.get_slices(excludes=[SliceState.Dead, SliceState.Closing])

            for slice in slices:
                if name != None and slice.get_name() == name:
                    return slice
        else:
            raise Exception("get_slice requires slice name (name) or slice id (slice_id)")

    def delete_slice(self, slice_name=None):
        """
        Deletes a slice by name.

        :param slice_name: the name of the slice to delete
        :type slice_name: String
        """
        slice = self.get_slice(slice_name)
        slice.delete()

    def delete_all(self, progress=True):
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

    def isJupyterNotebook(self):
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


# fablib.set_log_level(logging.DEBUG)
# try:
#    os.makedirs("/tmp/fablib")
# except:
#    pass
# try:
#    os.makedirs("/tmp/fablib/fabric_data")
# except:
#   pass

# logging.basicConfig(filename='/tmp/fablib/fablib.log',
#                    level=fablib.get_log_level(),
#                    format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
#                    datefmt='%H:%M:%S')

# init fablib object
fablib.default_fablib_manager = FablibManager()
