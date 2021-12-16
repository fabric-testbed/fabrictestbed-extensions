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

class AbcUtils(ABC):


    #os.environ['FABRIC_CREDMGR_HOST']='cm.fabric-testbed.net'
    #os.environ['FABRIC_ORCHESTRATOR_HOST']='orchestrator.fabric-testbed.net'
    #os.environ['FABRIC_TOKEN_LOCATION']=os.environ['HOME']+'/work/fabric_token.json'

    #os.environ['FABRIC_BASTION_USERNAME']=<INSERT_YOUR_FABRIC_USERNAME>
    #os.environ['FABRIC_BASTION_KEY_LOCATION']=os.environ['HOME']+'/work/.ssh/id_rsa_fabric'

    #os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']=os.environ['HOME']+'/.ssh/id_rsa'
    #os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE']=os.environ['HOME']+'/.ssh/id_rsa.pub'



    bastion_username = os.environ['FABRIC_BASTION_USERNAME']
    #bastion_keyfile = ''

    bastion_public_addr = os.environ['FABRIC_BASTION_HOST']
    bastion_private_ipv4_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV4']
    bastion_private_ipv6_addr = os.environ['FABRIC_BASTION_HOST_PRIVATE_IPV6']

        #self.bastion_key_filename = '/Users/pruth/FABRIC/TESTING/pruth_fabric_rsa'
    bastion_key_filename = os.environ['HOME'] + "/.ssh/pruth_fabric_rsa"

    node_ssh_key = None
    with open(os.environ['HOME'] + "/.ssh/id_rsa.pub", "r") as fd:
        node_ssh_key = fd.read().strip()
    node_ssh_key_priv_file=os.environ['HOME'] + "/.ssh/id_rsa"

    @staticmethod
    def create_slice_manager():
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        print(f"FABRIC Credential Manager   : {credmgr_host}")

        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        print(f"FABRIC Orchestrator         : {orchestrator_host}")

        slice_manager = SliceManager(oc_host=orchestrator_host,
                             cm_host=credmgr_host,
                             project_name='all',
                             scope='all')

        # Initialize the slice manager
        slice_manager.initialize()

        return slice_manager





    @abstractmethod
    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
