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
from tabulate import tabulate


import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

from .abc_fablib import AbcFabLIB

from .. import images

class fablib(AbcFabLIB):

    log_level = logging.INFO

    #dafault_sites = [ 'TACC', 'MAX', 'UTAH', 'NCSA', 'MICH', 'WASH', 'DALL', 'SALT', 'STAR']

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.build_slice_manager()
        self.resources = None

    def build_slice_manager(self):
        self.slice_manager = SliceManager(oc_host=self.orchestrator_host,
                             cm_host=self.credmgr_host,
                             project_name='all',
                             scope='all')

        # Initialize the slice manager
        self.slice_manager.initialize()

        return self.slice_manager

    @staticmethod
    def get_site_names():
        return fablib.get_resources().get_site_names()

    @staticmethod
    def list_sites():
        return str(fablib.get_resources())

    @staticmethod
    def show_site(site_name):
        return str(fablib.get_resources().show_site(site_name))


    @staticmethod
    def get_resources():
        if not fablib.fablib_object.resources:
            fablib.get_available_resources()

        return fablib.fablib_object.resources

    @staticmethod
    def get_random_site(avoid=[]):
        return fablib.get_random_sites(count=1, avoid=avoid)[0]

    @staticmethod
    def get_random_sites(count=1, avoid=[]):
        # Need to avoid SALT and MASS for now.
        # Real fix is to check availability
        always_avoid=['SALT','MASS', 'NCSA']
        
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
        if not hasattr(fablib, 'fablib_object'):
            fablib.fablib_object = fablib()

    @staticmethod
    def get_default_slice_key():
        return fablib.fablib_object.default_slice_key

    @staticmethod
    def get_config():
        return { 'credmgr_host': fablib.fablib_object.credmgr_host,
                'orchestrator_host': fablib.fablib_object.orchestrator_host,
                'fabric_token': fablib.fablib_object.fabric_token,
                'bastion_username': fablib.fablib_object.bastion_username,
                'bastion_key_filename': fablib.fablib_object.bastion_key_filename,
                'bastion_public_addr': fablib.fablib_object.bastion_public_addr,
                'bastion_public_addr': fablib.fablib_object.bastion_public_addr,
                'bastion_private_ipv4_addr': fablib.fablib_object.bastion_private_ipv4_addr,
                'slice_public_key': fablib.get_default_slice_public_key(),
                'slice_public_key_file': fablib.get_default_slice_public_key_file(),
                'slice_private_key_file': fablib.get_default_slice_private_key_file(),
                'fabric_slice_private_key_passphrase': fablib.get_default_slice_private_key_passphrase()
               }
    @staticmethod
    def get_default_slice_public_key():
        if 'slice_public_key' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_public_key']
        else:
            return None

    @staticmethod
    def get_default_slice_public_key_file():
        if 'slice_public_key_file' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_public_key_file']
        else:
            return None

    @staticmethod
    def get_default_slice_private_key_file():
        if 'slice_private_key_file' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_private_key_file']
        else:
            return None

    @staticmethod
    def get_default_slice_private_key_passphrase():
        if 'slice_private_key_passphrase' in fablib.fablib_object.default_slice_key.keys():
            return fablib.fablib_object.default_slice_key['slice_private_key_passphrase']
        else:
            return None

    @staticmethod
    def get_credmgr_host():
        return fablib.fablib_object.credmgr_host

    @staticmethod
    def get_orchestrator_host():
        return fablib.fablib_object.orchestrator_host

    @staticmethod
    def get_fabric_token():
        return fablib.fablib_object.fabric_token

    @staticmethod
    def get_bastion_username():
        return fablib.fablib_object.bastion_username

    @staticmethod
    def get_bastion_key_filename():
        return fablib.fablib_object.bastion_key_filename

    @staticmethod
    def get_bastion_public_addr():
        return fablib.fablib_object.bastion_public_addr

    @staticmethod
    def get_bastion_private_ipv4_addr():
        return fablib.fablib_object.bastion_private_ipv4_addr

    @staticmethod
    def get_bastion_private_ipv6_addr():
        return fablib.fablib_object.bastion_private_ipv6_addr

    @staticmethod
    def set_slice_manager(slice_manager):
        fablib.fablib_object.slice_manager = slice_manager

    @staticmethod
    def get_slice_manager():
        return fablib.fablib_object.slice_manager

    @staticmethod
    def create_slice_manager():
        return fablib.fablib_object.create_slice_manager()

    @staticmethod
    def new_slice(name):
        #fabric = fablib()
        from fabrictestbed_extensions.fablib.slice import Slice
        return Slice.new_slice(name=name)

    @staticmethod
    def get_site_advertisment(site):
        return_status, topology = fablib.get_slice_manager().resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))


        return topology.sites[site]

    @staticmethod
    def get_available_resources(update=False):
        from fabrictestbed_extensions.fablib.resources import Resources

        if fablib.fablib_object.resources == None:
            fablib.fablib_object.resources = Resources()
            
        if update:
            fablib.fablib_object.resources.update()

        return fablib.fablib_object.resources

    @staticmethod
    def get_slice_list(excludes=[SliceState.Dead,SliceState.Closing]):
        return_status, slices = fablib.get_slice_manager().slices(excludes=excludes)

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                return_slices.append(slice)
        else:
            raise Exception(f"Failed to get slice list: {slices}")
        return return_slices

    @staticmethod
    def get_slices(excludes=[SliceState.Dead,SliceState.Closing]):
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
    def get_slice(name=None, slice_id=None):

        #Get the appropriat slices list
        if slice_id:
            #if getting by slice_id consider all slices
            slices = fablib.get_slices(excludes=[])

            for slice in slices:
                if slice_id != None and slice.get_slice_id() == slice_id:
                    return slice
        elif name:
            # if getting by name then only consider active slices
            slices = fablib.get_slices(excludes=[SliceState.Dead,SliceState.Closing])

            for slice in slices:
                if name != None and slice.get_name() == name:
                    return slice
        else:
            raise Exception("get_slice requires slice name (name) or slice id (slice_id)")

    @staticmethod
    def delete_slice(slice_name=None):
        slice = fablib.get_slice(slice_name)
        slice.delete()

    @staticmethod
    def delete_all():
        slices = fablib.get_slices()

        for slice in slices:
            try:
                print(f"Deleting slice {slice.get_name()}", end='')
                slice.delete()
                print(f", Success!")
            except Exception as e:
                print(f", Failed!")

    @staticmethod
    def get_log_level():
        return fablib.log_level

    @staticmethod
    def set_log_level(log_level):
        fablib.log_level = log_level


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


#init fablib object
fablib.fablib_object = fablib()
