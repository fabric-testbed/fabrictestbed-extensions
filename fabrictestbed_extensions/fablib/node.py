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

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
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

    def __init__(self, slice, node):
        """
        Constructor
        :return:
        """
        super().__init__()
        self.fim_node = node
        self.slice = slice

        #Try to set the username.
        try:
            self.set_username()
        except:
            self.username = None

    @staticmethod
    def new_node(slice=None, name=None, site=None):
        from fabrictestbed_extensions.fablib.node import Node
        return Node(slice, slice.topology.add_node(name=name, site=site))

    @staticmethod
    def get_node(slice=None, node=None):
        from fabrictestbed_extensions.fablib.node import Node
        return Node(slice, node)

    def set_capacities(self, cores=2, ram=2, disk=2):
        cap = Capacities()
        cap.set_fields(core=cores, ram=ram, disk=disk)
        self.fim_node.set_properties(capacities=cap)

    def set_instance_type(self, instance_type):
        self.fim_node.set_properties(capacity_hints=CapacityHints().set_fields(instance_type=instance_type))

    def set_username(self, username=None):
        if 'centos' in self.get_image():
            self.username = 'centos'
        elif 'ubuntu' in self.get_image():
            self.username = 'ubuntu'
        else:
            self.username = None

    def set_image(self, image, username=None, image_type='qcow2'):
        self.fim_node.set_properties(image_type=image_type, image_ref=image)
        self.set_username(username=username)

    def get_slice(self):
        return self.slice

    def get_name(self):
        return self.fim_node.name

    def get_cores(self):
        return self.fim_node.get_property(pname='capacity_allocations').core

    def get_ram(self):
        return self.fim_node.get_property(pname='capacity_allocations').ram

    def get_disk(self):
        return self.fim_node.get_property(pname='capacity_allocations').disk

    def get_image(self):
        return self.fim_node.image_ref

    def get_image_type(self):
        return self.fim_node.image_type

    def get_host(self):
        return self.fim_node.get_property(pname='label_allocations').instance_parent

    def get_site(self):
        return self.fim_node.site

    def get_management_ip(self):
        return self.fim_node.management_ip

    def get_reservation_id(self):
        return self.fim_node.get_property(pname='reservation_info').reservation_id

    def get_reservation_state(self):
        return self.fim_node.get_property(pname='reservation_info').reservation_state

    def get_interfaces(self):
        from fabrictestbed_extensions.fablib.interface import Interface

        interfaces = []
        for component in self.get_components():
            for interface in component.get_interfaces():
                interfaces.append(interface)

        return interfaces

    def get_username(self):
        return self.username

    def add_component(self, model=None, name=None):
        from fabrictestbed_extensions.fablib.component import Component
        return Component.new_component(node=self, model=model, name=name)

    def get_components(self):
        from fabrictestbed_extensions.fablib.component import Component

        return_components = []
        for component_name, component in self.fim_node.components.items():
            return_components.append(Component(self,component))

        return return_components

    def get_component(self, name):
        from fabrictestbed_extensions.fablib.component import Component
        try:
            return Component(self,self.fim_node.components[name])
        except Exception as e:
            if verbose:
                traceback.print_exc()
            raise Exception(f"Component not found: {name}")


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

    def execute(self, command):
        import paramiko

        management_ip = str(self.fim_node.get_property(pname='management_ip'))
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

        stdin, stdout, stderr = client.exec_command('echo \"' + command + '\" > script.sh; chmod +x script.sh; sudo ./script.sh')
        rtn_stdout = str(stdout.read(),'utf-8').replace('\\n','\n')
        rtn_stderr = str(stderr.read(),'utf-8').replace('\\n','\n')


        client.close()

        return rtn_stdout, rtn_stderr
