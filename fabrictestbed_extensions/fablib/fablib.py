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
import logging
import random

from IPython import get_ipython

from typing import List, Dict

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fabric_cf.orchestrator.swagger_client import Slice as OrchestratorSlice, Sliver as OrchestratorSliver

from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fim.user import Node as FimNode

from fabrictestbed_extensions.fablib.abc_fablib import AbcFabLIB
from fabrictestbed_extensions.fablib.resources import Resources
from fabrictestbed_extensions.fablib.slice import Slice


class fablib(AbcFabLIB):

    log_level = logging.INFO

    def __init__(self):
        """
        Constructor. Builds SliceManager for fablib object.
        """
        super().__init__()

        self.slice_manager = None
        self.build_slice_manager()
        self.resources = None

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
                                              scope='all')

            # Initialize the slice manager
            self.slice_manager.initialize()
        except Exception as e:
            logging.error(f"{e}")

        return self.slice_manager

    @staticmethod
    def get_image_names() -> List[str]:
        """
        Gets a list of available image names.

        :return: list of image names as strings
        :rtype: List[String]
        """
        return [ 'default_centos8_stream' ,
                 'default_centos9_stream',
                 'default_centos_7',
                 'default_centos_8',
                 'default_cirros',
                 'default_debian_10',
                 'default_fedora_35',
                 'default_freebsd_13_zfs',
                 'default_openbsd_7',
                 'default_rocky_8' ,
                 'default_ubuntu_18',
                 'default_ubuntu_20',
                 'default_ubuntu_21',
                 'default_ubuntu_22'  ]


    @staticmethod
    def get_site_names() -> List[str]:
        """
        Gets a list of all available site names.

        :return: list of site names as strings
        :rtype: List[String]
        """
        return fablib.get_resources().get_site_names()

    @staticmethod
    def list_sites() -> str:
        """
        Get a string used to print a tabular list of sites with state

        :return: tabulated string of site state
        :rtype: String
        """
        return str(fablib.get_resources())

    @staticmethod
    def show_site(site_name: str) -> str:
        """
        Get a string used to print tabular info about a site

        :param site_name: the name of a site
        :type site_name: String
        :return: tabulated string of site state
        :rtype: String
        """
        return str(fablib.get_resources().show_site(site_name))

    @staticmethod
    def get_resources() -> Resources:
        """
        Get a reference to the resourcs object. The resouces obeject
        is used to query for availale resouces and capacities.

        :return: the resouces object
        :rtype: Resources
        """
        if not fablib.fablib_object.resources:
            fablib.get_available_resources()

        return fablib.fablib_object.resources

    @staticmethod
    def get_random_site(avoid: List[str] = []) -> str:
        """
        Get a random site.

        :param avoid: list of site names to avoid chosing
        :type site_name: List[String]
        :return: one site name
        :rtype: String
        """
        return fablib.get_random_sites(count=1, avoid=avoid)[0]

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
        # Need to avoid SALT and MASS for now.
        # Real fix is to check availability
        always_avoid=['SALT', 'MASS']

        for site in always_avoid:
            if site not in avoid:
                avoid.append(site)

        sites = fablib.get_resources().get_site_list()
        for site in avoid:
            if site in sites:
                sites.remove(site)

        rtn_sites = []
        for i in range(count):
            rand_site = random.choice(sites)
            sites.remove(rand_site)
            rtn_sites.append(rand_site)
        return rtn_sites

    @staticmethod
    def init_fablib():
        """
        Not intended to be called by the user.

        Static initializer for the fablib object.
        """
        if not hasattr(fablib, 'fablib_object'):
            fablib.fablib_object = fablib()

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
        return fablib.fablib_object.default_slice_key

    @staticmethod
    def get_config() -> Dict[str, str]:
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return {'credmgr_host': fablib.fablib_object.credmgr_host,
                'orchestrator_host': fablib.fablib_object.orchestrator_host,
                'fabric_token': fablib.fablib_object.fabric_token,
                'bastion_username': fablib.fablib_object.bastion_username,
                'bastion_key_filename': fablib.fablib_object.bastion_key_filename,
                'bastion_public_addr': fablib.fablib_object.bastion_public_addr,
                'bastion_private_ipv4_addr': fablib.fablib_object.bastion_private_ipv4_addr,
                'slice_public_key': fablib.get_default_slice_public_key(),
                'slice_public_key_file': fablib.get_default_slice_public_key_file(),
                'slice_private_key_file': fablib.get_default_slice_private_key_file(),
                'fabric_slice_private_key_passphrase': fablib.get_default_slice_private_key_passphrase()
                }

    @staticmethod
    def get_default_slice_public_key() -> str or None:
        """
        Gets the default slice public key.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the slice public key on this fablib object
        :rtype: String
        """
        if 'slice_public_key' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_public_key']
        else:
            return None

    @staticmethod
    def get_default_slice_public_key_file() -> str or None:
        """
        Gets the path to the default slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice public key on this fablib object
        :rtype: String
        """
        if 'slice_public_key_file' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_public_key_file']
        else:
            return None

    @staticmethod
    def get_default_slice_private_key_file() -> str or None:
        """
        Gets the path to the default slice private key file.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice private key on this fablib object
        :rtype: String
        """
        if 'slice_private_key_file' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_private_key_file']
        else:
            return None

    @staticmethod
    def get_default_slice_private_key_passphrase() -> str or None:
        """
        Gets the passphrase to the default slice private key.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the passphrase to the slice private key on this fablib object
        :rtype: String
        """
        if 'slice_private_key_passphrase' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_private_key_passphrase']
        else:
            return None

    @staticmethod
    def get_credmgr_host() -> str:
        """
        Gets the credential manager host site value.

        :return: the credential manager host site
        :rtype: String
        """
        return fablib.fablib_object.credmgr_host

    @staticmethod
    def get_orchestrator_host() -> str:
        """
        Gets the orchestrator host site value.

        :return: the orchestrator host site
        :rtype: String
        """
        return fablib.fablib_object.orchestrator_host

    @staticmethod
    def get_fabric_token() -> str:
        """
        Gets the FABRIC token location.

        :return: FABRIC token location
        :rtype: String
        """
        return fablib.fablib_object.fabric_token

    @staticmethod
    def get_bastion_username() -> str:
        """
        Gets the FABRIC Bastion username.

        :return: FABRIC Bastion username
        :rtype: String
        """
        return fablib.fablib_object.bastion_username

    @staticmethod
    def get_bastion_key_filename() -> str:
        """
        Gets the FABRIC Bastion key filename.

        :return: FABRIC Bastion key filename
        :rtype: String
        """
        return fablib.fablib_object.bastion_key_filename

    @staticmethod
    def get_bastion_public_addr() -> str:
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return fablib.fablib_object.bastion_public_addr

    @staticmethod
    def get_bastion_private_ipv4_addr() -> str:
        """
        Gets the FABRIC Bastion private IPv4 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv4 address
        :rtype: String
        """
        return fablib.fablib_object.bastion_private_ipv4_addr

    @staticmethod
    def get_bastion_private_ipv6_addr() -> str:
        """
        Gets the FABRIC Bastion private IPv6 host address. This is the
        internally faceing IPv4 address needed to use paramiko

        :return: Bastion private IPv6 address
        :rtype: String
        """
        return fablib.fablib_object.bastion_private_ipv6_addr

    @staticmethod
    def set_slice_manager(slice_manager: SliceManager) -> None:
        """
        Not intended as API call

        Sets the slice manager of this fablib object.

        :param slice_manager: the slice manager to set
        :type slice_manager: SliceManager
        """
        fablib.fablib_object.slice_manager = slice_manager

    @staticmethod
    def get_slice_manager() -> SliceManager:
        """
        Not intended as API call


        Gets the slice manager of this fablib object.

        :return: the slice manager on this fablib object
        :rtype: SliceManager
        """
        return fablib.fablib_object.slice_manager

    @staticmethod
    def new_slice(name: str) -> Slice:
        """
        Creates a new slice with the given name.

        :param name: the name to give the slice
        :type name: String
        :return: a new slice
        :rtype: Slice
        """
        # fabric = fablib()
        return Slice.new_slice(name=name)

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
        return_status, topology = fablib.get_slice_manager().resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))

        return topology.sites[site]

    @staticmethod
    def get_available_resources(update: bool = False) -> Resources:
        """
        Get the available resources.

        Optionally update the availalbe resources by querying the FABRIC
        services. Otherwise, this method returns the exisitng information.

        :param update: if True, update the available resources
        :type update: bool
        :return: Availalbe Resources object
        :rtype: Resources
        """
        from fabrictestbed_extensions.fablib.resources import Resources

        if fablib.fablib_object.resources == None:
            fablib.fablib_object.resources = Resources()

        if update:
            fablib.fablib_object.resources.update()

        return fablib.fablib_object.resources

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
        return_status, slices = fablib.get_slice_manager().slices(excludes=excludes)

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(slice)
        else:
            raise Exception(f"Failed to get slice list: {slices}")
        return return_slices

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
        from fabrictestbed_extensions.fablib.slice import Slice
        import time

        if fablib.get_log_level() == logging.DEBUG:
            start = time.time()

        return_status, slices = fablib.get_slice_manager().slices(excludes=excludes)

        if fablib.get_log_level() == logging.DEBUG:
            end = time.time()
            logging.debug(f"Running fablib.get_slice_manager().slices(): elapsed time: {end - start} seconds")

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(Slice.get_slice(sm_slice=slice, load_config=False))
        else:
            raise Exception(f"Failed to get slices: {slices}")
        return return_slices

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
        # Get the appropriat slices list
        if slice_id:
            # if getting by slice_id consider all slices
            slices = fablib.get_slices(excludes=[])

            for slice in slices:
                if slice_id is not None and slice.get_slice_id() == slice_id:
                    return slice
        elif name:
            # if getting by name then only consider active slices
            slices = fablib.get_slices(excludes=[SliceState.Dead, SliceState.Closing])

            for slice in slices:
                if name is not None and slice.get_name() == name:
                    return slice
        else:
            raise Exception("get_slice requires slice name (name) or slice id (slice_id)")

    @staticmethod
    def delete_slice(slice_name: str = None):
        """
        Deletes a slice by name.

        :param slice_name: the name of the slice to delete
        :type slice_name: String
        """
        slice = fablib.get_slice(slice_name)
        slice.delete()

    @staticmethod
    def delete_all(progress: bool = True):
        """
        Deletes all slices on the slice manager.

        :param progress: optional progess printing to stdout
        :type progress: Bool
        """
        slices = fablib.get_slices()

        for slice in slices:
            try:
                if progress: print(f"Deleting slice {slice.get_name()}", end='')
                slice.delete()
                if progress: print(f", Success!")
            except Exception as e:
                if progress: print(f", Failed!")

    @staticmethod
    def get_log_level():
        """
        Gets the current log level for logging
        """
        return fablib.log_level

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
        fablib.log_level = log_level

    @staticmethod
    def isJupyterNotebook():
        try:
            shell = get_ipython().__class__.__name__
            if shell == 'ZMQInteractiveShell':
                return True   # Jupyter notebook or qtconsole
            elif shell == 'TerminalInteractiveShell':
                return False  # Terminal running IPython
            else:
                return False  # Other type (?)
        except NameError:
            return False


fablib.set_log_level(logging.DEBUG)
try:
    os.makedirs("/tmp/fablib")
except:
    pass
try:
    os.makedirs("/tmp/fablib/fabric_data")
except:
    pass

logging.basicConfig(filename='/tmp/fablib/fablib.log',
                    level=fablib.get_log_level(),
                    format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')

# init fablib object
fablib.fablib_object = fablib()
