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
This module exports a :class:`FablibManager` class and a
:class:`fablib` class available, which allows you to, among other
things:

    - Query FABRIC testbed resources.

    - Create, modify, and delete slices.

    - Manage the SSH keys you use with FABRIC.

    - etc.

In most cases you would need to create a :class:`FablibManager`
instance to interact with FABRIC testbed::

    from fabrictestbed_extensions.fablib.fablib import FablibManager

    fablib = FablibManager()

    slice = fablib.new_slice(name="MySlice")
    node = slice.add_node(name="node1")
    slice.submit();

See FABRIC project's `Jupyter notebook examples <examples>`_ for more
complete code samples.

.. note::

    Some configuration in the form of a configuration file, environment
    variables, or :class:`FablibManager` constructor parameters is
    required for the library to work.  Please see the FABRIC project's
    `documentation on getting started <learn>`_.

.. _learn: https://learn.fabric-testbed.net/article-categories/getting-started/
.. _examples: https://github.com/fabric-testbed/jupyter-examples/
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import random
import traceback
import warnings

from fabrictestbed_extensions.fablib.site import Host, Site

warnings.filterwarnings("always", category=DeprecationWarning)

from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Network, IPv6Network
from typing import TYPE_CHECKING, Dict, List, Tuple

import pandas as pd
import paramiko
from IPython import get_ipython
from IPython.core.display_functions import display
from tabulate import tabulate

from fabrictestbed_extensions.fablib.config.config import Config, ConfigException
from fabrictestbed_extensions.fablib.constants import Constants
from fabrictestbed_extensions.utils.utils import Utils

if TYPE_CHECKING:
    from fabric_cf.orchestrator.swagger_client import Slice as OrchestratorSlice
    from fabrictestbed_extensions.fablib.node import Node

from fabrictestbed.slice_manager import SliceManager, SliceState, Status
from fim.user import Node as FimNode

from fabrictestbed_extensions.fablib.resources import FacilityPorts, Links, Resources
from fabrictestbed_extensions.fablib.slice import Slice


class fablib:
    """
    Convenience static methods to work with FABRIC testbed.
    """

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
    def list_sites(latlon: bool = True) -> object:
        """
        Get a string used to print a tabular list of sites with state

        :return: tabulated string of site state
        :rtype: str
        """
        return fablib.get_default_fablib_manager().list_sites(latlon=latlon)

    @staticmethod
    def list_hosts() -> object:
        """
        Get a string used to print a tabular list of sites with state

        :return: tabulated string of site state
        :rtype: str
        """
        return fablib.get_default_fablib_manager().list_hosts()

    @staticmethod
    def list_links() -> object:
        """
        Print the links in pretty format

        :return: Formatted list of links
        :rtype: object
        """
        return fablib.get_default_fablib_manager().list_links()

    @staticmethod
    def get_links() -> Links:
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
    def get_facility_ports() -> FacilityPorts:
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
        :param avoid: list of site names to avoid choosing
        :type avoid: List[String]
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
        Gets the current default_slice_keys as a dictionary containing the
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
        return fablib.get_default_fablib_manager().get_token_location()

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
        return fablib.get_default_fablib_manager().get_bastion_key_location()

    @staticmethod
    def get_bastion_host() -> str:
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return fablib.get_default_fablib_manager().get_bastion_host()

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

        Optionally update the available resources by querying the FABRIC
        services. Otherwise, this method returns the existing information.

        :param update: update
        :type update: Bool
        :return: Available Resources object
        :rtype: Resources
        """
        return fablib.get_default_fablib_manager().get_available_resources(
            update=update
        )

    @staticmethod
    def get_fim_slice(
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing],
        user_only: bool = True,
    ) -> List[OrchestratorSlice]:
        """
        Not intended for API use.

        Gets a list of fim slices from the slice manager.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool

        :return: a list of slices
        :rtype: List[Slice]
        """
        return fablib.get_default_fablib_manager().get_fim_slice(
            excludes=excludes, user_only=user_only
        )

    @staticmethod
    def get_slices(
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing],
        user_only: bool = True,
    ) -> List[Slice]:
        """
        Gets a list of slices from the slice manager.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool

        :return: a list of slices
        :rtype: List[Slice]
        """
        return fablib.get_default_fablib_manager().get_slices(
            excludes=excludes, user_only=user_only
        )

    @staticmethod
    def get_slice(
        name: str = None, slice_id: str = None, user_only: bool = True
    ) -> Slice:
        """
        Gets a slice by name or slice_id. Dead and Closing slices may have
        non-unique names and must be queried by slice_id.  Slices in all other
        states are guaranteed to have unique names and can be queried by name.

        If both a name and slice_id are provided, the slice matching the
        slice_id will be returned.

        :param name: The name of the desired slice
        :type name: String
        :param slice_id: The ID of the desired slice
        :type slice_id: String
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool
        :raises: Exception: if slice name or slice id are not inputted
        :return: the slice, if found
        :rtype: Slice
        """
        return fablib.get_default_fablib_manager().get_slice(
            name=name, slice_id=slice_id, user_only=user_only
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

        :param progress: optional progress printing to stdout
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
    def set_log_level(log_level: str):
        """
        Sets the current log level for logging

        Options:  logging.DEBUG
                  logging.INFO
                  logging.WARNING
                  logging.ERROR
                  logging.CRITICAL

        :param log_level: new log level
        :type log_level: Level
        """
        return fablib.get_default_fablib_manager().set_log_level(log_level)

    @staticmethod
    def is_jupyter_notebook() -> bool:
        return fablib.get_default_fablib_manager().is_jupyter_notebook()


class FablibManager(Config):
    FABNETV4_SUBNET = IPv4Network("10.128.0.0/10")
    FABNETV6_SUBNET = IPv6Network("2602:FCFB:00::/40")

    ssh_thread_pool_executor = None

    def __init__(
        self,
        fabric_rc: str = None,
        credmgr_host: str = None,
        orchestrator_host: str = None,
        core_api_host: str = None,
        token_location: str = None,
        project_id: str = None,
        bastion_username: str = None,
        bastion_key_location: str = None,
        log_level: str = Constants.DEFAULT_LOG_LEVEL,
        log_file: str = Constants.DEFAULT_LOG_FILE,
        data_dir: str = Constants.DEFAULT_DATA_DIR,
        output: str = None,
        execute_thread_pool_size: int = 64,
        offline: bool = False,
        auto_token_refresh: bool = True,
        **kwargs,
    ):
        """
        ``FablibManager`` is the main interface to FABRIC services.

        A ``FablibManager`` object is used to query FABRIC testbed for
        available resources, create and configure slices, manage SSH
        keys in nodes in slices and FABRIC's bastion host, etc.  This
        requires some configuration, which is gathered from:

            - constructor parameters (high priority)

            - a configuration file (medium priority)

            - environment variables (low priority)

            - defaults (if needed, and when possible)

        Typically you would use the configuration file located at
        ``"${HOME}/work/fabric_config/fabric_rc"``, and/or environment
        variables.

        :param fabric_rc: Path to fablib configuration file.  Defaults
            to ``"${HOME}/work/fabric_config/fabric_rc"``.
        :param credmgr_host: Name of credential manager host.
        :param orchestrator_host: Name of FABRIC orchestrator host.
        :param fabric_token: Path to the file that contains your
            FABRIC auth token.
        :param project_id: Your FABRIC project ID, obtained from
            https://cm.fabric-testbed.net/, usually via FABRIC portal.
        :param bastion_username: Your username on FABRIC bastion host,
            obtained from FABRIC portal.
        :param bastion_key_filename: Path to your bastion SSH key.
        :param log_file: Path where fablib logs are written; defaults
            to ``"/tmp/fablib/fablib.log"``.
        :param log_level: Level of detail in the logs written.
            Defaults to ``"DEBUG"``; other possible log levels are
            ``"INFO"``, ``"WARNING"``, ``"ERROR"``, and
            ``"CRITICAL"``, in reducing order of verbosity.
        :param data_dir: directory for fablib to store temporary data.
        :param output: Format of fablib output; can be either
            ``"pandas"`` or ``"text"``.  Defaults to ``"pandas"`` in a
            Jupyter notebook environment; ``"text"`` otherwise.
        :param execute_thread_pool_size: Number of worker threads in
            the thread pool fablib uses to execute commands in nodes.
            Defaults to 64.
        :param offline: Avoid using FABRIC services when initializing.
            This is ``False`` by default, and set to ``True`` only in
            some unit tests.
        :param auto_token_refresh: Auto refresh tokens
        """
        super().__init__(
            fabric_rc=fabric_rc,
            credmgr_host=credmgr_host,
            orchestrator_host=orchestrator_host,
            core_api_host=core_api_host,
            token_location=token_location,
            project_id=project_id,
            bastion_username=bastion_username,
            bastion_key_location=bastion_key_location,
            log_level=log_level,
            log_file=log_file,
            data_dir=data_dir,
            offline=offline,
            **kwargs,
        )

        if output is not None:
            self.output = output
        else:
            if self.is_jupyter_notebook():
                self.output = "pandas"
            else:
                self.output = "text"

        self.slice_manager = None
        self.resources = None
        self.links = None
        self.facility_ports = None
        self.auto_token_refresh = auto_token_refresh
        self.last_resources_filtered_by_time = False

        if not offline:
            self.ssh_thread_pool_executor = ThreadPoolExecutor(execute_thread_pool_size)
            self.setup_logging()
            self.__build_slice_manager()
        self.required_check()

    def validate_config(self):
        """
        Validate and create Fablib config - checks if all the required
        configuration exists for slice provisioning to work
        successfully

            - Checks Credential Manager Host is configured properly

            - Checks Orchestrator Host is configured properly

            - Checks Core API Host is configured properly

            - Checks Bastion Host is configured properly

            - Check Sliver keys exist; create sliver keys if they do
              not exist

            - Check Bastion keys exist and are not expired;
              update/create bastion keys if expired or do not exist

            - Check Bastion Username is configured

            - Check Project Id is configured

        .. deprecated:: 1.6.5 Use `verify_and_configure()` instead.

        @raises Exception if the configuration is invalid
        """
        warnings.warn(
            "This function is deprecated and will be removed in future releases, "
            "please use 'verify_and_configure' instead.",
            DeprecationWarning,
        )
        self.verify_and_configure()

    def verify_and_configure(self):
        """
        Validate and create Fablib config - checks if all the required configuration exists for slice
        provisioning to work successfully

        - Checks Credential Manager Host is configured properly

        - Checks Orchestrator Host is configured properly

        - Checks Core API Host is configured properly

        - Checks Bastion Host is configured properly

        - Check Sliver keys exist; create sliver keys if they do not exist

        - Check Bastion keys exist and are not expired; update/create bastion keys if expired or do not exist

        - Check Bastion Username is configured

        - Check Project Id is configured

        @raises Exception if the configuration is invalid
        """
        Utils.is_reachable(hostname=self.get_credmgr_host(), port=443)
        Utils.is_reachable(hostname=self.get_orchestrator_host(), port=443)
        Utils.is_reachable(hostname=self.get_core_api_host(), port=443)
        Utils.is_reachable(hostname=self.get_bastion_host(), port=22)

        self.validate_and_update_bastion_keys()

        if (
            self.get_default_slice_public_key() is None
            or self.get_default_slice_private_key() is None
        ):
            logging.info("Sliver keys do not exist! Please create sliver keys")
            self.create_sliver_keys()

        if self.get_bastion_username() is None:
            logging.info("Bastion User name is not specified")
            raise Exception("Bastion User name is not specified")

        if self.get_project_id() is None:
            logging.info("Project is not specified")
            raise Exception("Bastion User name is not specified")

        self.create_ssh_config(overwrite=True)

        print("Configuration is valid and please save the config!")

    def get_user_info(self) -> dict:
        """
        Get User information

        :return returns a dictionary containing User's Information
        :rtype: dict
        """
        return self.get_slice_manager().get_user_info()

    def determine_bastion_username(self):
        """
        Determine Bastion Username.
        Query User Information from Core API and updates the bastion username
        """
        # Fetch User Info and Projects
        if self.get_bastion_username() is not None:
            return

        logging.info("Fetching User's information")
        user_info = self.get_user_info()
        logging.debug("Updating Bastion User Name")
        self.set_bastion_username(
            bastion_username=user_info.get(Constants.BASTION_LOGIN)
        )

    def create_ssh_config(self, overwrite: bool = False):
        """
        Create SSH config file

        :param overwrite: overwrite the configuration if True, return otherwise
        :type overwrite: bool
        """
        bastion_ssh_config_file = self.get_bastion_ssh_config_file()
        if bastion_ssh_config_file is None:
            raise ConfigException("Bastion SSH Config File location not specified")

        if os.path.exists(bastion_ssh_config_file) and not overwrite:
            print("Bastion SSH Config file already exists, not making updates!")
            return

        dir_path = os.path.dirname(bastion_ssh_config_file)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except OSError as e:
                msg = (
                    f"Directory {dir_path} does not exist, Failed to create directory {dir_path}: {e}, "
                    f"can not create ssh_config file!"
                )
                print(msg)
                logging.error(msg)
                raise Exception(msg)

        with open(bastion_ssh_config_file, "w") as f:
            f.write(
                f"""UserKnownHostsFile /dev/null
StrictHostKeyChecking no
ServerAliveInterval 120 

Host bastion.fabric-testbed.net
     User {self.get_bastion_username()}
     ForwardAgent yes
     Hostname %h
     IdentityFile {self.get_bastion_key_location()}
     IdentitiesOnly yes

Host * !bastion.fabric-testbed.net
     ProxyJump {self.get_bastion_username()}@bastion.fabric-testbed.net:22
    """
            )

    def validate_and_update_bastion_keys(self):
        """
        Validate Bastion Key; if key does not exist or is expired, it create bastion keys
        """
        logging.info("Fetching User's information")
        user_info = self.get_user_info()
        logging.debug("Updating Bastion User Name")
        ssh_keys = user_info.get(Constants.SSH_KEYS)

        current_bastion_key = self.get_bastion_key()
        current_bastion_key_file = self.get_bastion_key_location()

        keys_to_remove = []
        for key in ssh_keys:
            expires_on = key.get(Constants.EXPIRES_ON)
            expires_on_dt = datetime.datetime.fromisoformat(expires_on)
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if now > expires_on_dt:
                keys_to_remove.append(key)
                continue

        for key in keys_to_remove:
            ssh_keys.remove(key)

        found = False
        if current_bastion_key_file is not None:
            current_bastion_key_name = os.path.basename(current_bastion_key_file)
            found = any(
                item["comment"] == current_bastion_key_name for item in ssh_keys
            )

        if current_bastion_key is not None and found:
            logging.info(
                f"User: {user_info.get(Constants.EMAIL)} bastion key is valid!"
            )
            print(f"User: {user_info.get(Constants.EMAIL)} bastion key is valid!")
            return

        logging.info(
            f"User: {user_info.get(Constants.EMAIL)} bastion keys do not exist or are expired"
        )
        print(
            f"User: {user_info.get(Constants.EMAIL)} bastion keys do not exist or are expired"
        )
        self.create_bastion_keys(overwrite=True)

    def create_bastion_keys(
        self,
        *,
        bastion_key_location: str = None,
        store_pubkey: bool = True,
        overwrite: bool = False,
    ):
        """
        Create Bastion Keys

        :param bastion_key_location: bastion key location
        :type bastion_key_location: str

        :param store_pubkey: flag indicating if the public key should be saved
        :type store_pubkey: bool

        :param overwrite: overwrite the bastion key file if it exists already
        :type overwrite: bool
        """
        if bastion_key_location is None:
            bastion_key_location = self.get_bastion_key_location()

        if os.path.exists(bastion_key_location) and not overwrite:
            logging.info(
                f"Bastion keys already exist at the location: {bastion_key_location}"
            )
            print(f"Bastion keys already exist at the location: {bastion_key_location}")
            return

        logging.info("Bastion Key does not exist, creating a bastion key!")
        self.__create_and_save_key(
            private_file_path=bastion_key_location,
            description="Bastion Key Fablib",
            key_type=Constants.KEY_TYPE_BASTION,
            store_pubkey=store_pubkey,
        )
        logging.info(f"Bastion Key saved at location: {bastion_key_location}")
        print(f"Bastion Key saved at location: {bastion_key_location}")

    def create_sliver_keys(
        self,
        *,
        sliver_priv_key_location: str = None,
        store_pubkey: bool = True,
        overwrite: bool = False,
    ):
        """
        Create Sliver Keys

        :param sliver_priv_key_location: sliver key location
        :type sliver_priv_key_location: str

        :param store_pubkey: flag indicating if the public key should be saved
        :type store_pubkey: bool

        :param overwrite: overwrite the bastion key file if it exists already
        :type overwrite: bool
        """
        if sliver_priv_key_location is None:
            sliver_priv_key_location = self.get_default_slice_private_key_file()

        if os.path.exists(sliver_priv_key_location) and not overwrite:
            logging.info(
                f"Sliver keys already exist at the location: {sliver_priv_key_location}"
            )
            print(
                f"Sliver keys already exist at the location: {sliver_priv_key_location}"
            )
            return

        logging.info("Creating sliver key!")
        self.__create_and_save_key(
            private_file_path=sliver_priv_key_location,
            description="Sliver Key Fablib",
            store_pubkey=store_pubkey,
            key_type=Constants.KEY_TYPE_SLIVER,
        )
        logging.info(f"Sliver Keys saved at location: {sliver_priv_key_location}")
        print(f"Sliver Keys saved at location: {sliver_priv_key_location}")

    def __create_and_save_key(
        self,
        private_file_path: str,
        description: str,
        key_type: str,
        public_file_path: str = None,
        store_pubkey: bool = False,
    ):
        """
        Create Key and save key
        :param private_file_path: private key location
        :type private_file_path: str

        :param description: description
        :type description: str

        :param key_type: key type bastion or sliver
        :type key_type: str

        :param public_file_path: public key location
        :type public_file_path: str

        :param store_pubkey flag indicating if the public key should be saved
        :type store_pubkey: bool
        """
        dir_path = os.path.dirname(private_file_path)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except OSError as e:
                msg = (
                    f"Directory {dir_path} does not exist! Failed to create directory {dir_path}: {e}, "
                    f"cannot create {key_type} keys!"
                )
                print(msg)
                logging.error(msg)
                raise Exception(msg)

        comment = os.path.basename(private_file_path)
        ssh_keys = self.get_slice_manager().create_ssh_keys(
            key_type=key_type,
            description=description,
            comment=comment,
            store_pubkey=store_pubkey,
        )
        if public_file_path is None:
            public_file_path = f"{private_file_path}.pub"

        Utils.save_to_file(
            file_path=private_file_path, data=ssh_keys[0].get(Constants.PRIVATE_OPENSSH)
        )
        Utils.save_to_file(
            file_path=public_file_path, data=ssh_keys[0].get(Constants.PUBLIC_OPENSSH)
        )
        # Set the permissions to the files
        # Private Key file permissions
        os.chmod(private_file_path, 0o600)
        # Public Key file permissions
        os.chmod(public_file_path, 0o644)

    def get_ssh_thread_pool_executor(self) -> ThreadPoolExecutor:
        return self.ssh_thread_pool_executor

    def __build_slice_manager(self) -> SliceManager:
        """
        Not a user facing API call.

        Creates a new SliceManager object.

        :return: a new SliceManager
        :rtype: SliceManager
        """
        try:
            logging.info(
                f"orchestrator_host={self.get_orchestrator_host()},"
                f"credmgr_host={self.get_credmgr_host()},"
                f"core_api_host={self.get_core_api_host()},"
                f"project_id={self.get_project_id()},"
                f"token_location={self.get_token_location()},"
                f"initialize=True,"
                f"scope='all'"
            )
            Utils.is_reachable(hostname=self.get_credmgr_host())
            Utils.is_reachable(hostname=self.get_orchestrator_host())
            Utils.is_reachable(hostname=self.get_core_api_host())

            self.slice_manager = SliceManager(
                oc_host=self.get_orchestrator_host(),
                cm_host=self.get_credmgr_host(),
                core_api_host=self.get_core_api_host(),
                project_id=self.get_project_id(),
                token_location=self.get_token_location(),
                initialize=True,
                scope="all",
                auto_refresh=self.auto_token_refresh,
            )
            self.slice_manager.initialize()
            logging.debug("Slice manager initialized!")
            # Update Project ID to be same as in Slice Manager
            self.set_project_id(project_id=self.slice_manager.project_id)
            self.determine_bastion_username()
        except Exception as e:
            logging.error(e, exc_info=True)
            raise e

        return self.slice_manager

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
        update: bool = False,
        pretty_names: bool = True,
        force_refresh: bool = False,
        latlon: bool = True,
        start: datetime = None,
        end: datetime = None,
        avoid: List[str] = None,
        includes: List[str] = None,
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
        :param update:
        :type update: bool
        :param pretty_names:
        :type pretty_names: bool
        :param force_refresh:
        :type force_refresh: bool
        :param latlon: convert address to latlon, makes online call to openstreetmaps.org
        :type: Object
        :param start: start time in UTC format: %Y-%m-%d %H:%M:%S %z
        :type: datetime
        :param end: end time in UTC format:  %Y-%m-%d %H:%M:%S %z
        :type: datetime
        :param avoid: list of sites to avoid
        :type: list of string
        :param includes: list of sites to include
        :type: list of string

        """
        return self.get_resources(
            update=update,
            force_refresh=force_refresh,
            start=start,
            end=end,
            avoid=avoid,
            includes=includes,
        ).list_sites(
            output=output,
            fields=fields,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names=pretty_names,
            latlon=latlon,
        )

    def list_hosts(
        self,
        output: str = None,
        fields: str = None,
        quiet: bool = False,
        filter_function=None,
        update: bool = True,
        pretty_names: bool = True,
        force_refresh: bool = False,
        start: datetime = None,
        end: datetime = None,
        avoid: List[str] = None,
        includes: List[str] = None,
    ) -> object:
        """
        Lists all the hosts and their attributes.

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
        :param update:
        :type update: bool
        :param pretty_names:
        :type pretty_names: bool
        :param force_refresh:
        :type force_refresh: bool
        :param start: start time in UTC format: %Y-%m-%d %H:%M:%S %z
        :type: datetime
        :param end: end time in UTC format:  %Y-%m-%d %H:%M:%S %z
        :type: datetime
        :param avoid: list of sites to avoid
        :type: list of string
        :param includes: list of sites to include
        :type: list of string

        """
        return self.get_resources(
            update=update,
            force_refresh=force_refresh,
            start=start,
            end=end,
            avoid=avoid,
            includes=includes,
        ).list_hosts(
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
        :param update:
        :type update: bool
        :param pretty_names:
        :type pretty_names: bool
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
        :param update:
        :type update: bool
        :param pretty_names:
        :type pretty_names: bool
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
        :param pretty_names:
        :type pretty_names: bool
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
        latlon=True,
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
        :param pretty_names:
        :type pretty_names: bool
        :param latlon: convert address to lat/lon
        :type latlon: bool
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
                latlon=latlon,
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

    def get_resources(
        self,
        update: bool = False,
        force_refresh: bool = False,
        start: datetime = None,
        end: datetime = None,
        avoid: List[str] = None,
        includes: List[str] = None,
    ) -> Resources:
        """
        Get a reference to the resources object. The resources object
        is used to query for available resources and capacities.

        :param update:
        :type update: bool

        :param force_refresh:
        :type force_refresh: bool

        :param start: start time in UTC format: %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param end: end time in UTC format:  %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param avoid: list of sites to avoid
        :type: list of string

        :param includes: list of sites to include
        :type: list of string

        :return: the resources object
        :rtype: Resources
        """
        if not update:
            if start or end:
                update = True
                self.last_resources_filtered_by_time = True
            elif self.last_resources_filtered_by_time:
                update = True
                self.last_resources_filtered_by_time = False

        return self.get_available_resources(
            update=update,
            force_refresh=force_refresh,
            start=start,
            end=end,
            avoid=avoid,
            includes=includes,
        )

    def get_random_site(
        self, avoid: List[str] = [], filter_function=None, update: bool = True
    ) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid choosing
        :type avoid: List[String]
        :param filter_function: filter_function
        :type filter_function:
        :param update: flag indicating if fetch latest availability information
        :type update: bool
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
        :type avoid: List[String]
        :param filter_function: filter_function
        :type filter_function:
        :param update: flag indicating if fetch latest availability information
        :type update: bool
        :return: one site name
        :param unique:
        :return: list of random site names.
        :rtype: List[Sting]
        """

        # Always filter out sites in maintenance and sites that can't support any VMs
        def combined_filter_function(site):
            if filter_function is None:
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
            # if filter function is not specified, no need for latlon
            latlon=True if filter_function else False,
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

    def probe_bastion_host(self) -> bool:
        """
        See if bastion will admit us with our configuration.

        Bastion hosts are configured to block hosts that attempts to
        use it with too many repeated authentication failures.  We
        want to avoid that.

        Returns ``True`` if connection attempt succeeds.  Raises an
        error in the event of failure.
        """

        bastion_client = paramiko.SSHClient()
        bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        bastion_host = self.get_bastion_host()
        bastion_username = self.get_bastion_username()
        bastion_key_path = self.get_bastion_key_location()
        bastion_key_passphrase = self.get_bastion_key_passphrase()

        try:
            logging.info(
                f"Probing bastion host {bastion_host} with "
                f"username: {bastion_username}, key: {bastion_key_path}, "
                f"key passphrase: {'hidden' if bastion_key_passphrase else None}"
            )

            result = bastion_client.connect(
                hostname=bastion_host,
                username=bastion_username,
                key_filename=bastion_key_path,
                passphrase=bastion_key_passphrase,
                allow_agent=False,
                look_for_keys=False,
            )

            # Things should be fine if we are here.
            if result is None:
                logging.info(f"Connection with {bastion_host} appears to be working")
                return True

        except paramiko.SSHException as e:
            logging.error(
                f"Error connecting to bastion host {bastion_host} "
                f"(hint: check your bastion key setup?): {e}"
            )
            raise e
        except Exception as e:
            logging.error(f"Error connecting to bastion host {bastion_host}: {e}")
            raise e

        finally:
            bastion_client.close()

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

    def get_available_resources(
        self,
        update: bool = False,
        force_refresh: bool = False,
        start: datetime = None,
        end: datetime = None,
        avoid: List[str] = None,
        includes: List[str] = None,
    ) -> Resources:
        """
        Get the available resources.

        Optionally update the available resources by querying the
        FABRIC services.  Otherwise, this method returns the existing
        information.

        :param update:
        :type update: bool

        :param force_refresh:
        :type force_refresh: bool

        :param start: start time in UTC format: %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param end: end time in UTC format:  %Y-%m-%d %H:%M:%S %z
        :type: datetime

        :param avoid: list of sites to avoid
        :type: list of string

        :param includes: list of sites to include
        :type: list of string

        :return: Available Resources object
        """
        if start and end and (end - start) < datetime.timedelta(minutes=60):
            raise Exception("Time range should be at least 60 minutes long!")

        from fabrictestbed_extensions.fablib.resources import Resources

        if self.resources is None:
            self.resources = Resources(
                self,
                force_refresh=force_refresh,
                start=start,
                end=end,
                avoid=avoid,
                includes=includes,
            )
        elif update:
            self.resources.update(
                force_refresh=force_refresh,
                start=start,
                end=end,
                avoid=avoid,
                includes=includes,
            )

        return self.resources

    def get_fim_slices(
        self,
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing],
        user_only: bool = True,
    ) -> List[OrchestratorSlice]:
        """
        Gets a list of fim slices from the slice manager.

        This is not recommended for most users and should only be used to bypass fablib inorder
        to create custom low-level functionality.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool
        :return: a list of fim models of slices
        :rtype: List[Slice]
        """
        return_status, slices = self.get_slice_manager().slices(
            excludes=excludes, limit=200, as_self=user_only
        )

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(slice)
        else:
            raise Exception(f"Failed to get slice list: {slices}")
        return return_slices

    def list_slices(
        self,
        excludes=[SliceState.Dead, SliceState.Closing],
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
        user_only: bool = True,
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
        :param pretty_names: pretty_names
        :type pretty_names: bool
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool
        :rtype: Object
        """
        table = []
        for slice in self.get_slices(excludes=excludes, user_only=user_only):
            table.append(slice.toDict())

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
        user_only: bool = True,
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
        :param id: the slice id
        :type name: str
        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param pretty_names: pretty_names
        :type pretty_names: bool
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        slice = self.get_slice(name=name, slice_id=id, user_only=user_only)

        return slice.show(
            output=output, fields=fields, quiet=quiet, pretty_names=pretty_names
        )

    def get_slices(
        self,
        excludes: List[SliceState] = [SliceState.Dead, SliceState.Closing],
        slice_name: str = None,
        slice_id: str = None,
        user_only: bool = True,
    ) -> List[Slice]:
        """
        Gets a list of slices from the slice manager.

        By default this method ignores Dead and Closing slices. Optional,
        parameter allows excluding a different list of slice states.  Pass
        an empty list (i.e. excludes=[]) to get a list of all slices.

        :param excludes: A list of slice states to exclude from the output list
        :type excludes: List[SliceState]
        :param slice_name:
        :param slice_id:
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool

        :return: a list of slices
        :rtype: List[Slice]
        """
        import time

        if self.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = self.get_slice_manager().slices(
            excludes=excludes,
            name=slice_name,
            slice_id=slice_id,
            limit=200,
            as_self=user_only,
        )

        if self.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(
                f"Running self.get_slice_manager().slices(): elapsed time: {end - start} seconds"
            )

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(
                    Slice.get_slice(self, sm_slice=slice, user_only=user_only)
                )
        else:
            raise Exception(f"Failed to get slices: {slices}")
        return return_slices

    def get_slice(
        self, name: str = None, slice_id: str = None, user_only: bool = True
    ) -> Slice:
        """
        Gets a slice by name or slice_id. Dead and Closing slices may have
        non-unique names and must be queried by slice_id.  Slices in all other
        states are guaranteed to have unique names and can be queried by name.

        If both a name and slice_id are provided, the slice matching the
        slice_id will be returned.

        :param name: The name of the desired slice
        :type name: String
        :param slice_id: The ID of the desired slice
        :type slice_id: String
        :param user_only: True indicates return own slices; False indicates return project slices
        :type user_only: bool
        :raises: Exception: if slice name or slice id are not inputted
        :return: the slice, if found
        :rtype: Slice
        """
        # Get the appropriate slices list
        if slice_id:
            # if getting by slice_id consider all slices
            slices = self.get_slices(
                excludes=[], slice_id=slice_id, user_only=user_only
            )

            if len(slices) == 1:
                return slices[0]
            else:
                raise Exception(f"More than 1 slice found with slice_id: {slice_id}")
        elif name:
            # if getting by name then only consider active slices
            slices = self.get_slices(
                excludes=[SliceState.Dead, SliceState.Closing],
                slice_name=name,
                user_only=user_only,
            )

            if len(slices) > 0:
                return slices[0]
            else:
                raise Exception(
                    f'Unable to find slice "{name}" for this project. Check slice name spelling and project id.'
                )
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

        :param progress: optional progress printing to stdout
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

    @staticmethod
    def is_jupyter_notebook() -> bool:
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

    @staticmethod
    def show_table_text(table, quiet=False):
        printable_table = tabulate(table)

        if not quiet:
            print(f"\n{printable_table}")

        return printable_table

    @staticmethod
    def show_table_jupyter(
        table, headers=None, title="", title_font_size="1.25em", quiet=False
    ):
        printable_table = pd.DataFrame(table)

        properties = {
            "text-align": "left",
            "border": f"1px {Constants.FABRIC_BLACK} solid !important",
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
                        ("background", f"{Constants.FABRIC_PRIMARY_EXTRA_LIGHT}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
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
                        ("background", f"{Constants.FABRIC_WHITE}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )

        caption_props = [
            ("text-align", "center"),
            ("font-size", "150%"),
        ]

        printable_table = printable_table.set_table_styles(
            [{"selector": "caption", "props": caption_props}], overwrite=False
        )

        if not quiet:
            display(printable_table)

        return printable_table

    @staticmethod
    def show_table_json(data, quiet=False):
        json_str = json.dumps(data, indent=4)

        if not quiet:
            print(f"{json_str}")

        return json_str

    @staticmethod
    def show_table_dict(data, quiet=False):
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
        if output is None:
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

    @staticmethod
    def list_table_text(table, headers=None, quiet=False):
        if headers is not None:
            printable_table = tabulate(table, headers=headers)
        else:
            printable_table = tabulate(table)

        if not quiet:
            print(f"\n{printable_table}")

        return printable_table

    @staticmethod
    def list_table_jupyter(
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

        properties = {
            "text-align": "left",
            "border": f"1px {Constants.FABRIC_BLACK} solid !important",
        }

        printable_table = printable_table.style.set_caption(title)
        printable_table = printable_table.hide(axis="index")
        printable_table = printable_table.set_properties(**properties, overwrite=False)

        caption_props = [
            ("text-align", "center"),
            ("font-size", "150%"),
            ("caption-side", "top"),
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
                        ("background", f"{Constants.FABRIC_WHITE}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
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
                        ("background", f"{Constants.FABRIC_PRIMARY_EXTRA_LIGHT}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
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
                        ("background", f"{Constants.FABRIC_WHITE}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                )
            ],
            overwrite=False,
        )

        if not quiet:
            display(printable_table)

        return printable_table

    @staticmethod
    def list_table_json(data, quiet=False):
        json_str = json.dumps(data, indent=4)

        if not quiet:
            print(f"{json_str}")

        return json_str

    @staticmethod
    def list_table_list(data, quiet=False):
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

        if output is None:
            output = self.output.lower()

        if fields is None and len(data) > 0:
            fields = list(data[0].keys())

        if fields is None:
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

    @staticmethod
    def create_list_table(data, fields=None):
        table = []
        for entry in data:
            row = []
            for field in fields:
                row.append(entry[field])

            table.append(row)
        return table

    @staticmethod
    def create_show_table(data, fields=None, pretty_names_dict={}):
        table = []
        if fields is None:
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

    @staticmethod
    def __can_allocate_node_in_host(
        host: Host, node: Node, allocated: dict, site: Site
    ) -> Tuple[bool, str]:
        """
        Check if a node can be provisioned on a host node on a site w.r.t available resources on that site

        :return: Tuple indicating status for validation and error message in case of failure
        :rtype: Tuple[bool, str]
        """
        if host is None or site is None:
            return (
                True,
                f"Ignoring validation: Host: {host}, Site: {site} not available.",
            )

        msg = f"Node can be allocated on the host: {host.get_name()}."

        if host.get_state() != "Active":
            msg = f"Node cannot be allocated on {host.get_name()}, {host.get_name()} is in {host.get_state()}!"
            return False, msg

        allocated_core = allocated.setdefault("core", 0)
        allocated_ram = allocated.setdefault("ram", 0)
        allocated_disk = allocated.setdefault("disk", 0)
        available_cores = host.get_core_available()
        available_ram = host.get_ram_available()
        available_disk = host.get_disk_available()

        if (
            node.get_requested_cores() > available_cores
            or node.get_requested_disk() > available_disk
            or node.get_requested_ram() > available_ram
        ):
            msg = f"Insufficient Resources: Host: {host.get_name()} does not meet core/ram/disk requirements."
            return False, msg

        # Check if there are enough components available
        for c in node.get_components():
            comp_model_type = f"{c.get_type()}-{c.get_fim_model()}"
            substrate_component = host.get_component(comp_model_type=comp_model_type)
            if not substrate_component:
                msg = f"Invalid Request: Host: {host.get_name()} does not have the requested component: {comp_model_type}."
                return False, msg

            allocated_comp_count = allocated.setdefault(comp_model_type, 0)
            available_comps = (
                substrate_component.capacities.unit
                - (
                    substrate_component.capacity_allocations.unit
                    if substrate_component.capacity_allocations
                    else 0
                )
                - allocated_comp_count
            )
            if available_comps <= 0:
                msg = f"Insufficient Resources: Host: {host.get_name()} has reached the limit for component: {comp_model_type}."
                return False, msg

            allocated[comp_model_type] += 1

        allocated["core"] += node.get_requested_cores()
        allocated["ram"] += node.get_requested_ram()
        allocated["disk"] += node.get_requested_disk()

        return True, msg

    def validate_node(self, node: Node, allocated: dict = None) -> Tuple[bool, str]:
        """
        Validate a node w.r.t available resources on a site before submission

        :return: Tuple indicating status for validation and error message in case of failure
        :rtype: Tuple[bool, str]
        """
        try:
            error = None
            if allocated is None:
                allocated = {}
            site = self.get_resources().get_site(site_name=node.get_site())

            if not site:
                logging.warning(
                    f"Ignoring validation: Site: {node.get_site()} not available in resources."
                )
                return (
                    True,
                    f"Ignoring validation: Site: {node.get_site()} not available in resources.",
                )

            site_state = site.get_state()
            if site_state != "Active":
                msg = f"Node cannot be allocated on {node.get_site()}, {node.get_site()} is in {site_state}."
                logging.error(msg)
                return False, msg
            hosts = site.get_hosts()
            if not hosts:
                msg = f"Node cannot be validated, host information not available for {site}."
                logging.error(msg)
                return False, msg

            if node.get_host():
                if node.get_host() not in hosts:
                    msg = f"Invalid Request: Requested Host {node.get_host()} does not exist on site: {node.get_site()}."
                    logging.error(msg)
                    return False, msg

                host = hosts.get(node.get_host())

                allocated_comps = allocated.setdefault(node.get_host(), {})
                status, error = self.__can_allocate_node_in_host(
                    host=host, node=node, allocated=allocated_comps, site=site
                )

                if not status:
                    logging.error(error)
                    return status, error

            for host in hosts.values():
                allocated_comps = allocated.setdefault(host.get_name(), {})
                status, error = self.__can_allocate_node_in_host(
                    host=host, node=node, allocated=allocated_comps, site=site
                )
                if status:
                    return status, error

            msg = f"Invalid Request: Requested Node cannot be accommodated by any of the hosts on site: {site.get_name()}."
            if error:
                msg += f" Details: {error}"
            logging.error(msg)
            return False, msg
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
            return False, str(e)
