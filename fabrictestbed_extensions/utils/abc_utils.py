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

class AbcTest(ABC):

    def __init__(self):
        self.slice_manager = SliceManager()
        self.advertised_topology = None
        self.slice = None
        self.topology = None
        self.ssh_key = None
        with open(os.environ['HOME'] + "/.ssh/id_rsa.pub", "r") as fd:
            self.ssh_key = fd.read().strip()
        self.ssh_key_priv_file=os.environ['HOME'] + "/.ssh/id_rsa"

        self.pull_advertised_topology()

    def pull_advertised_topology(self):
        return_status, self.advertised_topology = self.slice_manager.resources()
        if return_status != Status.OK:
            print("Failed to get advertised_topology: {}".format(self.advertised_topology))


    def wait_for_slice(self,slice,timeout=360,interval=10,progress=False):
        timeout_start = time.time()

        if progress: print("Waiting for slice .", end = '')
        while time.time() < timeout_start + timeout:
            return_status, slices = self.slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])

            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_name == self.slice.slice_name, slices))[0]
                if slice.slice_state == "StableOK":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if slice.slice_state == "Closing" or slice.slice_state == "Dead" or slice.slice_state == "StableError":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
            else:
                print(f"Failure: {slices}")

            if progress: print(".", end = '')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
            return slice

    def execute_script(self, node, script):
        import paramiko

        key = paramiko.RSAKey.from_private_key_file(self.ssh_key_priv_file)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        management_ip = str(node.get_property(pname='management_ip'))
        print("Node {0} IP {1}".format(node.name, management_ip))

        client.connect(management_ip,username='centos',pkey = key)

        stdin, stdout, stderr = client.exec_command('echo \"' + script + '\" > script.sh; chmod +x script.sh; sudo ./script.sh')
        print ('')
        print (str(stdout.read(),'utf-8').replace('\\n','\n'))

        client.close()


    @abstractmethod
    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
