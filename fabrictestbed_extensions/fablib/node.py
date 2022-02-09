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
import json

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

from ipaddress import ip_address, IPv4Address

#from .abc_fablib import AbcFabLIB
#from fabrictestbed_extensions.fablib.fablib import fablib

#class Node(AbcFabLIB):
class Node():
    """
    Class representing FABRIC nodes.
    """

    def __init__(self, slice, node):
        """
        Constructor. Sets the FIM Node and Slice of this Node.

        :param slice: The Slice to set.
        :type slice: Slice
        :param node: The FIM Node to set.
        :type node: Node
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
        """
        Creates and returns a new Node object based on the keyword parameters.

        :param slice: The Slice to create the new Node on.
        :type slice: Slice
        :param name: The name of the new Node.
        :type name: str
        :param site: The site to create the new Node on.
        :type site: str
        :return: a new Node.
        :rtype: Node
        """
        from fabrictestbed_extensions.fablib.node import Node
        return Node(slice, slice.topology.add_node(name=name, site=site))

    @staticmethod
    def get_node(slice=None, node=None):
        """
        Gets a particular Node.

        :param slice: The Slice to get the Node from.
        :type slice: Slice
        :param node: The Node to get.
        :type node: Node
        :return: the Node.
        :rtype: Node
        """
        from fabrictestbed_extensions.fablib.node import Node
        return Node(slice, node)

    def get_fim_node(self):
        """
        Gets the FIM Node on this Node instance.

        :return: the FIM Node.
        :rtype: Node
        """
        return self.fim_node

    def set_capacities(self, cores=2, ram=2, disk=2):
        """
        Sets the capacities of the Node.

        :param cores: The number of cores on the node.
        :type cores: int
        :param ram: The amoutn of RAM on the node.
        :type ram: int
        :param disk: The amount of disk space on the node.
        :type disk: int
        """
        cap = Capacities()
        cap.set_fields(core=cores, ram=ram, disk=disk)
        self.get_fim_node().set_properties(capacities=cap)

    def set_instance_type(self, instance_type):
        """
        Sets the instance type of the Node.

        :param instance_type: The instance type.
        :type instance_type: str
        """
        self.get_fim_node().set_properties(capacity_hints=CapacityHints().set_fields(instance_type=instance_type))

    def set_username(self, username=None):
        if 'centos' in self.get_image():
            self.username = 'centos'
        elif 'ubuntu' in self.get_image():
            self.username = 'ubuntu'
        else:
            self.username = None

    def set_image(self, image, username=None, image_type='qcow2'):
        """
        Sets the image of the Node.

        :param image: The image reference.
        :type image: str
        :param username: The username to set, if any.
        :type username: str
        :param image_type: The image type to set.
        :type image_type: str
        """
        self.get_fim_node().set_properties(image_type=image_type, image_ref=image)
        self.set_username(username=username)

    def set_host(self, host_name=None):
        """
        Sets the hostname of the Node.

        :param host_name: The hostname to set.
        :type host_name: str
        """
        #excample: host_name='renc-w2.fabric-testbed.net'
        labels = Labels()
        labels.instance_parent = host_name
        self.get_fim_node().set_properties(labels=labels)


    def get_slice(self):
        """
        Gets the Slice this Node is on.

        :return: the Slice this Node is on.
        :rtype: Slice
        """
        return self.slice

    def get_name(self):
        """
        Gets the name of this Node.

        :return: the name of this Node.
        :rtype: str
        """
        return self.get_fim_node().name

    def get_cores(self):
        """
        Gets the number of cores on this Node.

        :return: the number of cores on this Node.
        :rtype: int
        """
        return self.get_fim_node().get_property(pname='capacity_allocations').core

    def get_ram(self):
        """
        Gets the amount of RAM on this Node.

        :return: the amount of RAM on this Node.
        :rtype: int
        """
        return self.get_fim_node().get_property(pname='capacity_allocations').ram

    def get_disk(self):
        """
        Gets the amount of disk space on this Node.

        :return: the amount of disk space on this Node.
        :rtype: int
        """
        return self.get_fim_node().get_property(pname='capacity_allocations').disk

    def get_image(self):
        """
        Gets the image reference held by this Node.

        :return: the image reference held by this Node.
        :rtype: str
        """
        return self.get_fim_node().image_ref

    def get_image_type(self):
        """
        Gets the image type held by this Node.

        :return: the image type held by this Node.
        :rtype: str
        """
        return self.get_fim_node().image_type

    def get_host(self):
        """
        Gets the hostname of this Node.

        :return: the hostname of this Node.
        :rtype: str
        """
        return self.get_fim_node().get_property(pname='label_allocations').instance_parent

    def get_site(self):
        """
        Gets the site of this Node.

        :return: the site of this Node.
        :rtype: str
        """
        return self.get_fim_node().site

    def get_management_ip(self):
        """
        Gets the management IP of this Node.

        :return: the management IP of this Node.
        :rtype: str
        """
        return self.get_fim_node().management_ip

    def get_reservation_id(self):
        """
        Gets the reservation ID of this Node.

        :return: the reservation ID of this Node.
        :rtype: str
        """
        return self.get_fim_node().get_property(pname='reservation_info').reservation_id

    def get_reservation_state(self):
        """
        Gets the reservation state of this Node.

        :return: the reservation state of this Node.
        :rtype: str
        """
        return self.get_fim_node().get_property(pname='reservation_info').reservation_state

    def get_interfaces(self):
        """
        Gets a list of interfaces attached to this Node.

        :return: a list of interfaces attached to this Node.
        :rtype: list[Interface]
        """
        from fabrictestbed_extensions.fablib.interface import Interface

        interfaces = []
        for component in self.get_components():
            for interface in component.get_interfaces():
                interfaces.append(interface)

        return interfaces

    def get_interface(self, name=None, network_name=None):
        """
        Gets a particular interface attached to this Node.

        :param name: The name of the interface to get.
        :type name: str
        :param network_name: The network name that the interface is on.
        :type network_name: str
        :return: the particular interface.
        :rtype: Interface
        """
        from fabrictestbed_extensions.fablib.interface import Interface

        if name != None:
            for component in self.get_components():
                for interface in component.get_interfaces():
                    if interface.get_name() == name:
                        return interface
        elif network_name != None:
            for interface in self.get_interfaces():
                if interface != None and interface.get_network().get_name() == network_name:
                    return interface

        raise Exception("Interface not found: {}".format(name))


    def get_username(self):
        """
        Gets the username on this Node.

        :return: the username on this Node.
        :rtype: str
        """
        return self.username

    def get_public_key(self):
        """
        Gets the public key on this Node's slice.

        :return: the public key on this Node.
        :rtype: str
        """
        return self.get_slice().get_slice_public_key()

    def get_public_key_file(self):
        """
        Gets the public key file on this Node's slice.

        :return: the public key file on this Node.
        :rtype: File
        """
        return self.get_slice().get_slice_public_key_file()

    def get_private_key(self):
        """
        Gets the private key on this Node's slice.

        :return: the private key on this Node.
        :rtype: str
        """
        return self.get_slice().get_slice_private_key()

    def get_private_key_file(self):
        """
        Gets the private key file on this Node's slice.

        :return: the private key file on this Node.
        :rtype: File
        """
        return self.get_slice().get_slice_private_key_file()

    def get_private_key_passphrase(self):
        """
        Gets the private key passphrase on this Node's slice.

        :return: the private key passphrase on this Node.
        :rtype: str
        """
        return self.get_slice().get_private_key_passphrase()

    def add_component(self, model=None, name=None):
        """
        Adds a new component to this Node.

        :param model: The model key of the component model desired.
        :type model: str
        :param name: The name of the component.
        :type name: str
        :return: the new component.
        :rtype: Component
        """
        from fabrictestbed_extensions.fablib.component import Component
        return Component.new_component(node=self, model=model, name=name)

    def get_components(self):
        """
        Gets the components on this Node.

        :return: a list of components on this Node.
        :rtype: list[Component]
        """
        from fabrictestbed_extensions.fablib.component import Component

        return_components = []
        for component_name, component in self.get_fim_node().components.items():
            #return_components.append(Component(self,component))
            return_components.append(Component(self,component))

        return return_components

    def get_component(self, name, verbose=False):
        """
        Gets a particular component on this Node.

        :param name: The name of the component to get.
        :type name: str
        :param verbose: Indicator for whtehr or not to give verbose output.
        :type verbose: boolean
        :return: the particular component.
        :rtype: Component
        """
        from fabrictestbed_extensions.fablib.component import Component
        try:
            name = Component.calculate_name(node=self, name=name)
            return Component(self,self.get_fim_node().components[name])
        except Exception as e:
            if verbose:
                traceback.print_exc()
            raise Exception(f"Component not found: {name}")


    def get_ssh_command(self):
        """
        Gets the SSH command used to access this Node.

        :return: the SSH command to access this Node.
        :rtype: str
        """
        return 'ssh -i {} -J {}@{} {}@{}'.format(self.get_private_key_file(),
                                           fablib.get_bastion_username(),
                                           fablib.get_bastion_public_addr(),
                                           self.get_username(),
                                           self.get_management_ip())

    def validIPAddress(self, IP: str) -> str:
        """
        Cheks whether an IP address is valid.

        :param IP: the IP address to check.
        :type IP: str
        :return: a string representing the type of IP, or Invalid.
        :rtype: str
        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def execute(self, command, retry=3, retry_interval=10):
        """
        Executes the command on the node.

        :param command: The command to run.
        :type command: str
        :param retry: How many times to retry this execute if it fails.
        :type retry: int
        :param retry_interval: How many seconds to wait to retry this execute if it fails.
        :type retry_interval: int
        :return: the standard output and error of this command execution.
        :rtype: str, str
        """
        import paramiko
        import time

        #Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = (fablib.get_bastion_private_ipv4_addr(), 22)
        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = (fablib.get_bastion_private_ipv6_addr(), 22)
        else:
            raise Exception(f"upload_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(retry):
            try:
                if self.get_private_key_passphrase():
                    key = paramiko.RSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
                else:
                    key = paramiko.RSAKey.from_private_key_file(self.get_private_key_file())

                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(fablib.get_bastion_public_addr(), username=fablib.get_bastion_username(), key_filename=fablib.get_bastion_key_filename())

                bastion_transport = bastion.get_transport()
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
                #success, skip other tries
                break
            except Exception as e:
                if attempt+1 == retry:
                    raise e

                #Fail, try again
                print(f"SSH execute fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp download failed")


    def upload_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        """
        Uploads a local file to the Node.

        :param local_file_path: The path from the current directory to the target file.
        :type local_file_path: str
        :param remote_file_path: Where to place the target file in the Node.
        :type remote_file_path: str
        :param retry: How many times to retry this file upload if it fails.
        :type retry: int
        :param retry_interval: How many seconds to wait to retry file upload.
        :return: the file attributes.
        :rtype: SFTPAttributes
        """
        import paramiko
        import time

        #Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = (fablib.get_bastion_private_ipv4_addr(), 22)
        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = (fablib.get_bastion_private_ipv6_addr(), 22)
        else:
            raise Exception(f"upload_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(retry):
            try:

                if self.get_private_key_passphrase():
                    key = paramiko.RSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
                else:
                    key = paramiko.RSAKey.from_private_key_file(self.get_private_key_file())

                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(fablib.get_bastion_public_addr(), username=fablib.get_bastion_username(), key_filename=fablib.get_bastion_key_filename())

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)


                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(management_ip,username=self.username,pkey = key, sock=bastion_channel)

                ftp_client=client.open_sftp()
                file_attributes = ftp_client.put(local_file_path, remote_file_path)
                ftp_client.close()

                return file_attributes
                #success, skip other tries
                break
            except Exception as e:
                if attempt+1 == retry:
                    raise e

                #Fail, try again
                print(f"SCP upload fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp upload failed")


    def download_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        """
        Downloads a local file from the Node.

        :param local_file_path: Where to place the target file locally.
        :type local_file_path: str
        :param remote_file_path: The path from the Node root directory to the target file.
        :type remote_file_path: str
        :param retry: How many times to retry this file upload if it fails.
        :type retry: int
        :param retry_interval: How many seconds to wait to retry file upload.
        :return: the file attributes.
        :rtype: SFTPAttributes
        """
        import paramiko
        import time

        #Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = (fablib.get_bastion_private_ipv4_addr(), 22)
        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = (fablib.get_bastion_private_ipv6_addr(), 22)
        else:
            raise Exception(f"upload_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(retry):
            try:
                if self.get_private_key_passphrase():
                    key = paramiko.RSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
                else:
                    key = paramiko.RSAKey.from_private_key_file(self.get_private_key_file())

                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(fablib.get_bastion_public_addr(), username=fablib.get_bastion_username(), key_filename=fablib.get_bastion_key_filename())

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)

                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(management_ip,username=self.username,pkey = key, sock=bastion_channel)


                ftp_client=client.open_sftp()
                file_attributes = ftp_client.get(local_file_path, remote_file_path)
                ftp_client.close()

                return file_attributes
                #success, skip other tries
                break
            except Exception as e:
                if attempt+1 == retry:
                    raise e

                #Fail, try again
                print(f"SCP download fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp download failed")


    def test_ssh(self):
        """
        Tests that this Node's SSH works.

        :return: an indicator for whether or not SSH works.
        :rtype: boolean
        """
        try:
            self.execute('ls', retry=1, retry_interval=10)
        except:
            return False
        return True

    def wait_for_ssh(self, retry=6, retry_interval=10):
        """
        Waits for a node to be SSH-able.

        :param retry: How many times to retry SSH.
        :type retry: int
        :param retry_interval: How many seconds to wait between attempts to SSH.
        :type retry_interval: int
        :return: an indicator for whether or not the node is SSH-able.
        :rtype: boolean
        """
        try:
            self.execute('echo hello, fabric', retry=retry, retry_interval=retry_interval)
        except:
            return False
        return True

    def get_management_os_interface(self):
        """
        Gets the management operating system interface.

        :return: the management operating system interface.
        :rtype: str
        """
        #Assumes that the default route uses the management network

        stdout, stderr = self.execute("sudo ip -j route list")
        stdout_json = json.loads(stdout)

        #print(pythonObj)
        for i in stdout_json:
            if i['dst'] == 'default':
                return  i['dev']

    def get_dataplane_os_interfaces(self):
        """
        Gest the dataplane operating system interfaces.

        :return: a list of the dataplane OS interfaces on this Node.
        :rtype: list[str]
        """
        management_dev = self.get_management_os_interface()

        stdout, stderr = self.execute("sudo ip -j addr list")
        stdout_json = json.loads(stdout)
        dataplane_devs = []
        for i in stdout_json:
            if i['ifname'] != 'lo' and i['ifname'] !=  management_dev:
                dataplane_devs.append({'ifname': i['ifname'], 'mac': i['address']})

        return dataplane_devs

    def flush_all_os_interfaces(self):
        """
        Flush all operating system interfaces on the node.
        """
        for iface in self.get_dataplane_os_interfaces():
            self.flush_os_interface(iface['ifname'])

    def flush_os_interface(self, os_iface):
        """
        Flush a particular operating system interface on the node.

        :param os_iface: The OS interface key to flush.
        :type os_iface: str
        """
        stdout, stderr = self.execute(f"sudo ip addr flush dev {os_iface}")

    def set_ip_os_interface(self, os_iface=None, vlan=None, ip=None, cidr=None, mtu=None):
        """
        Sets the IP operating system interface.

        :param os_iface: The OS interface to set.
        :type os_iface: str
        :param vlan: The VLAN to set.
        :type vlan: str
        :param ip: The IP address to set.
        :type ip: str
        :param cidr: the CIDR address to set.
        :type cidr: str
        :param mtu: The MTU to set.
        :type mtu: str
        """
        #Bring up base iface
        #print(f"node.set_ip_os_interface: os_iface {os_iface}, vlan {vlan}")
        command = f'sudo ip link set dev {os_iface} up'
        if mtu != None:
            command += f" mtu {mtu}"
        stdout, stderr = self.execute(command)

        #config vlan iface
        if vlan != None:
            #create vlan iface
            command = f'sudo ip link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'
            stdout, stderr = self.execute(command)

            #bring up vlan iface
            os_iface = f"{os_iface}.{vlan}"
            command = f'sudo ip link set dev {os_iface} up'
            if mtu != None:
                command += f" mtu {mtu}"
            stdout, stderr = self.execute(command)

        if ip != None and cidr != None:
            #Set ip
            command = f"sudo ip addr add {ip}/{cidr} dev {os_iface}"
            stdout, stderr = self.execute(command)

    def clear_all_ifaces(self):
        """
        Removes all VLAN operating system interfaces and then flushes all operating system interfaces.
        """
        self.remove_all_vlan_os_interfaces()
        self.flush_all_os_interfaces()


    def remove_all_vlan_os_interfaces(self):
        """
        Removes all operating system interfaces.
        """
        management_os_iface = self.get_management_os_interface()

        stdout, stderr = self.execute("sudo ip -j addr list")
        stdout_json = json.loads(stdout)
        dataplane_devs = []
        for i in stdout_json:
            if i['ifname'] == management_os_iface or i['ifname'] == 'lo':
                stdout_json.remove(i)
                continue

            #If iface is vlan linked to base iface
            if 'link' in i.keys():
                self.remove_vlan_os_interface(os_iface=i['ifname'])

    def save_data(self):
        """
        Stores all interface data in a JSON file with this Node's name.
        """
        data = {}
        #Get interface data
        interfaces = {}
        for i in self.get_interfaces():
            #print(f"interface: {i.get_name()}")
            #print(f"os_interface: {i.get_physical_os_interface()}")
            if i.get_network() != None:
                network_name = i.get_network().get_name()
                #print(f"network: {i.get_network().get_name()}")
            else:
                network_name = None
                #print(f"network: None")

            interfaces[i.get_name()] =  { 'network':  network_name,
                         'os_interface':  i.get_physical_os_interface() }

        with open(f'{self.get_name()}.json', 'w') as outfile:
            json.dump(interfaces, outfile)

        #print(f"interfaces: {json.dumps(interfaces).replace('\"','\\"')}")

        self.upload_file(f'{self.get_name()}.json', f'{self.get_name()}.json')

    def load_data(self):
        """
        Loads all interface data from a JSON file with this Node's name.
        """
        self.download_file(f'{self.get_name()}.json', f'{self.get_name()}.json')

        interfaces=""
        with open(f'{self.get_name()}.json', 'r') as infile:
            interfaces = json.load(infile)


        interface_map = self.get_slice().network_iface_map #= self.get_slice().get_interface_map()
        #print(f"interfaces {interfaces}")
        for interface_name, net_map in interfaces.items():
            #print(f"interface_name: {net_map}:")
            if net_map['network'] != None:
                interface_map[net_map['network']][self.get_name()] = net_map['os_interface']

        self.get_slice().network_iface_map = interface_map

    def remove_vlan_os_interface(self, os_iface=None):
        """
        Removes all VLAN operating system interfaces.
        """
        command = f"sudo ip -j addr show {os_iface}"
        stdout, stderr = self.execute(command)
        try:
            [stdout_json] = json.loads(stdout)
        except Exception as e:
            print(f"os_iface: {os_iface}, stdout: {stdout}, stderr: {stderr}")
            raise e


        link = stdout_json['link']

        command = f"sudo ip link del link {link} name {os_iface}"
        stdout, stderr = self.execute(command)

    def add_vlan_os_interface(self, os_iface=None, vlan=None, ip=None, cidr=None, mtu=None):
        """
        Adds a VLAN operating system interface.
        """
        command = f'sudo ip link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'
        stdout, stderr = self.execute(command)
        command = f'sudo ip link set dev {os_iface}.{vlan} up'
        stdout, stderr = self.execute(command)

        if ip != None and cidr != None:
            self.set_ip_os_interface(os_iface=f"{os_iface}.{vlan}", ip=ip, cidr=cidr, mtu=mtu)

    def ping_test(self, dst_ip):
        """
        Runs a ping test from this Node to some other IP.

        :param dst_ip: The destination IP address.
        :type dst_ip: str
        :return: an indicator of whether or not the ping was successful.
        :rtype: boolean
        """
        command = f'ping -c 3 {dst_ip}  2>&1 > /dev/null && echo Success'
        stdout, stderr = self.execute(command)
        if stdout.replace("\n","") == 'Success':
            return True
        else:
            return False
