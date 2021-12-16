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

#from fabrictestbed_extensions.fabricx.fabricx import FabricX
#from fabrictestbed_extensions.fabricx.slicex import SliceX
#from fabrictestbed_extensions.fabricx.nodex import NodeX

class AbcFabLIB(ABC):

    credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
    orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
    fabric_token=os.environ['FABRIC_TOKEN_LOCATION']

    #Basstion host setup
    bastion_username = os.environ['FABRIC_BASTION_USERNAME']
    bastion_key_filename = os.environ['FABRIC_BASTION_KEY_LOCATION']
    bastion_public_addr = os.environ['FABRIC_BASTION_HOST']
    bastion_private_ipv4_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV4']
    bastion_private_ipv6_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV6']

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        self.orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        self.fabric_token=os.environ['FABRIC_TOKEN_LOCATION']

        #Basstion host setup
        self.bastion_username = os.environ['FABRIC_BASTION_USERNAME']
        self.bastion_key_filename = os.environ['FABRIC_BASTION_KEY_LOCATION']
        self.bastion_public_addr = os.environ['FABRIC_BASTION_HOST']
        self.bastion_private_ipv4_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV4']
        self.bastion_private_ipv6_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV6']

        #Slice Keys
        self.slice_public_key = None
        with open(os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'], "r") as fd:
            self.slice_public_key = fd.read().strip()
        self.slice_private_key_file=os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']

        self.create_slice_manager()

    def set_slice_manager(self,slice_manager):
        self.slice_manager = slice_manager

    def get_slice_manager(self):
        return slice_manager

    def create_slice_manager(self):
        self.slice_manager = SliceManager(oc_host=self.orchestrator_host,
                             cm_host=self.credmgr_host,
                             project_name='all',
                             scope='all')

        # Initialize the slice manager
        self.slice_manager.initialize()

        return self.slice_manager
