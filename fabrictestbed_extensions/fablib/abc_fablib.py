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
import time

from abc import ABC, abstractmethod
from typing import List

from fabric_cf.orchestrator.orchestrator_proxy import SliceState
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fabrictestbed.slice_editor import ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, ComponentCatalog

class AbcFabLIB(ABC):

    #credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
    #orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
    #fabric_token=os.environ['FABRIC_TOKEN_LOCATION']

    #fabric_slice_private_key_passphrase = os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']

    #Basstion host setup
    #bastion_username = os.environ['FABRIC_BASTION_USERNAME']
    #bastion_key_filename = os.environ['FABRIC_BASTION_KEY_LOCATION']
    #bastion_public_addr = os.environ['FABRIC_BASTION_HOST']
    #bastion_private_ipv4_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV4']
    #bastion_private_ipv6_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV6']

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.credmgr_host = None
        self.orchestrator_host = None
        self.fabric_token = None

        self.bastion_username = None
        self.bastion_key_filename = None
        self.bastion_public_addr = None
        self.bastion_private_ipv4_addr = '0.0.0.0'
        self.bastion_private_ipv6_addr = '0:0:0:0:0:0'

        #self.slice_public_key = None
        #self.slice_public_key_file = None
        #self.slice_private_key = None
        #self.slice_private_key_file = None
        #self.slice_private_key_passphrase = None

        self.slice_keys = {}
        self.default_slice_key = {}
        self.slice_keys['default'] = self.default_slice_key


        if "FABRIC_CREDMGR_HOST" in os.environ:
            self.credmgr_host = os.environ['FABRIC_CREDMGR_HOST']

        if "FABRIC_ORCHESTRATOR_HOST" in os.environ:
            self.orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']

        if "FABRIC_TOKEN_LOCATION" in os.environ:
            self.fabric_token=os.environ['FABRIC_TOKEN_LOCATION']

        #Basstion host setup
        if "FABRIC_BASTION_USERNAME" in os.environ:
            self.bastion_username = os.environ['FABRIC_BASTION_USERNAME']
        if "FABRIC_BASTION_KEY_LOCATION" in os.environ:
            self.bastion_key_filename = os.environ['FABRIC_BASTION_KEY_LOCATION']
        if "FABRIC_BASTION_HOST" in os.environ:
            self.bastion_public_addr = os.environ['FABRIC_BASTION_HOST']
        if "FABRIC_BASTION_HOST_PRIVATE_IPV4" in os.environ:
            self.bastion_private_ipv4_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV4']
        if "FABRIC_BASTION_HOST_PRIVATE_IPV6" in os.environ:
            self.bastion_private_ipv6_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV6']

        #Slice Keys
        if "FABRIC_SLICE_PUBLIC_KEY_FILE" in os.environ:
            self.default_slice_key['slice_public_key_file'] = os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE']
            with open(os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'], "r") as fd:
                self.default_slice_key['slice_public_key'] = fd.read().strip()
        if "FABRIC_SLICE_PRIVATE_KEY_FILE" in os.environ:
            #self.slice_private_key_file=os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']
            self.default_slice_key['slice_private_key_file'] = os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']
        if "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE" in os.environ:
            #self.slice_private_key_passphrase = os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']
            self.default_slice_key['slice_private_key_passphrase'] = os.environ['slice_private_key_passphrase']
