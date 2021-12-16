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

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

#from fabrictestbed_extensions.fabricx.fabricx import FabricX
#from fabrictestbed_extensions.fabricx.slicex import SliceX
#from fabrictestbed_extensions.fabricx.nodex import NodeX
#from .slicex import SliceX
#from .nodex import NodeX
#from .fabricx import FabricX


from ipaddress import ip_address, IPv4Address


#from fim.user import node


from .abc_fablib import AbcFabLIB

from .. import images


class Node(AbcFabLIB):

    def __init__(self, node, username='centos'):
        """
        Constructor
        :return:
        """
        super().__init__()
        self.node = node
        self.username = username

    def set_capacities(self, cores=2, ram=2, disk=2):
        cap = Capacities()
        cap.set_fields(core=cores, ram=ram, disk=disk)
        self.node.set_properties(capacities=cap)

    def set_image(self, image, username, image_type='qcow2'):
        self.username = username
        self.node.set_properties(image_type=image_type, image_ref=image)

    def get_name(self):
        return self.node.name

    def get_cores(self):
        return self.node.get_property(pname='capacity_allocations').core

    def get_ram(self):
        return self.node.get_property(pname='capacity_allocations').ram

    def get_disk(self):
        return self.node.get_property(pname='capacity_allocations').disk

    def get_image(self):
        return self.node.image_ref

    def get_image_type(self):
        return self.node.image_type

    def get_host(self):
        return self.node.get_property(pname='label_allocations').instance_parent

    def get_site(self):
        return self.node.site

    def get_management_ip(self):
        return self.node.management_ip

    def get_reservation_id(self):
        return self.node.get_property(pname='reservation_info').reservation_id

    def get_reservation_state(self):
        return self.node.get_property(pname='reservation_info').reservation_state

    def get_components(self):
        #TODO: create fablib.component
        return self.node.components

    def get_interfaces(self):
        #TODO: create fablib.interface
        return self.node.interfaces

    def get_username(self):
        return self.username

    def get_ssh_command(self):
        return 'ssh -i {} -J {}@{} {}@{}'.format(self.slice_private_key_file,
                                           self.bastion_username,
                                           self.bastion_public_addr,
                                           self.get_username(),
                                           self.get_management_ip())

    def validIPAddress(self, IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def execute_script(self, script):
        import paramiko

        management_ip = str(self.node.get_property(pname='management_ip'))
        key = paramiko.RSAKey.from_private_key_file(self.slice_private_key_file)

        bastion=paramiko.SSHClient()
        bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        bastion.connect(self.bastion_public_addr, username=self.bastion_username, key_filename=self.bastion_key_filename)

        bastion_transport = bastion.get_transport()
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = (self.bastion_private_ipv4_addr, 22)
        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = (self.bastion_private_ipv6_addr, 22)
        else:
            print ('Management IP Invalid: {}'.format(management_ip))
            return

        dest_addr = (management_ip, 22)
        bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)


        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(management_ip,username=self.username,pkey = key, sock=bastion_channel)

        stdin, stdout, stderr = client.exec_command('echo \"' + script + '\" > script.sh; chmod +x script.sh; sudo ./script.sh')
        rtn_str = str(stdout.read(),'utf-8').replace('\\n','\n')

        client.close()

        return rtn_str
