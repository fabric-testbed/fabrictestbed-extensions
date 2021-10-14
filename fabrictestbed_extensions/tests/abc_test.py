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
from ipaddress import ip_address, IPv4Address


class AbcTest(ABC):

    def __init__(self):
        self.slice_manager = SliceManager()
        self.advertised_topology = None
        self.slice = None
        self.topology = None

        self.bastion_username = 'pruth'
        self.bastion_keyfile = ''

        self.bastion_public_addr = 'bastion-1.fabric-testbed.net'
        self.bastion_private_ipv4_addr = '192.168.11.226'
        self.bastion_private_ipv6_addr = '2600:2701:5000:a902::c'

        #self.bastion_key_filename = '/Users/pruth/FABRIC/TESTING/pruth_fabric_rsa'
        self.bastion_key_filename = os.environ['HOME'] + "/.ssh/pruth_fabric_rsa"

        self.node_ssh_key = None
        with open(os.environ['HOME'] + "/.ssh/id_rsa.pub", "r") as fd:
            self.node_ssh_key = fd.read().strip()
        self.node_ssh_key_priv_file=os.environ['HOME'] + "/.ssh/id_rsa"

        self.pull_advertised_topology()

    def pull_advertised_topology(self):
        return_status, self.advertised_topology = self.slice_manager.resources()
        if return_status != Status.OK:
            print("Failed to get advertised_topology: {}".format(self.advertised_topology))


    def wait_for_slice(self,slice,timeout=360,interval=10,progress=False):
        timeout_start = time.time()

        if progress: print("Waiting for slice {} .".format(self.slice.slice_name), end = '')
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

    @staticmethod
    def validIPAddress(IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"


    def execute_script(self, node_username, node, script):
        import paramiko

        try:
            management_ip = str(node.get_property(pname='management_ip'))
            #print("Node {0} IP {1}".format(node.name, management_ip))

            key = paramiko.RSAKey.from_private_key_file(self.node_ssh_key_priv_file)

            bastion=paramiko.SSHClient()
            bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            bastion.connect(self.bastion_public_addr, username=self.bastion_username, key_filename=self.bastion_key_filename)

            bastion_transport = bastion.get_transport()
            if self.validIPAddress(management_ip) == 'IPv4':
                src_addr = (self.bastion_private_ipv4_addr, 22)
            elif self.validIPAddress(management_ip) == 'IPv6':
                src_addr = (self.bastion_private_ipv6_addr, 22)
            else:
                return 'Management IP Invalid: {}'.format(management_ip)

            dest_addr = (management_ip, 22)
            bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)


            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(management_ip,username=node_username,pkey = key, sock=bastion_channel)

            stdin, stdout, stderr = client.exec_command('echo \"' + script + '\" > script.sh; chmod +x script.sh; sudo ./script.sh')
            stdout_str = str(stdout.read(),'utf-8').replace('\\n','\n')
            #print ('')
            #print (str(stdout.read(),'utf-8').replace('\\n','\n'))
            #print (stdout_str)

            client.close()
        except Exception as e:
            return str(e)

        return stdout_str


    @abstractmethod
    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
