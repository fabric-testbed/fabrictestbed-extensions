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
from fabrictestbed_extensions.fablib.fablib import fablib


from .. import images

#class Node(AbcFabLIB):
class Node():
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

    def get_fim_node(self):
        return self.fim_node

    def set_capacities(self, cores=2, ram=2, disk=2):
        cap = Capacities(core=cores, ram=ram, disk=disk)
        self.get_fim_node().set_properties(capacities=cap)

    def set_instance_type(self, instance_type):
        self.get_fim_node().set_properties(capacity_hints=CapacityHints(instance_type=instance_type))

    def set_username(self, username=None):
        if 'centos' in self.get_image():
            self.username = 'centos'
        elif 'ubuntu' in self.get_image():
            self.username = 'ubuntu'
        else:
            self.username = None

    def set_image(self, image, username=None, image_type='qcow2'):
        self.get_fim_node().set_properties(image_type=image_type, image_ref=image)
        self.set_username(username=username)

    def set_host(self, host_name=None):
        #excample: host_name='renc-w2.fabric-testbed.net'
        labels = Labels()
        labels.instance_parent = host_name
        self.get_fim_node().set_properties(labels=labels)


    def get_slice(self):
        return self.slice

    def get_name(self):
        return self.get_fim_node().name

    def get_cores(self):
        return self.get_fim_node().get_property(pname='capacity_allocations').core

    def get_ram(self):
        return self.get_fim_node().get_property(pname='capacity_allocations').ram

    def get_disk(self):
        return self.get_fim_node().get_property(pname='capacity_allocations').disk

    def get_image(self):
        return self.get_fim_node().image_ref

    def get_image_type(self):
        return self.get_fim_node().image_type

    def get_host(self):
        return self.get_fim_node().get_property(pname='label_allocations').instance_parent

    def get_site(self):
        return self.get_fim_node().site

    def get_management_ip(self):
        return self.get_fim_node().management_ip

    def get_reservation_id(self):
        return self.get_fim_node().get_property(pname='reservation_info').reservation_id

    def get_reservation_state(self):
        return self.get_fim_node().get_property(pname='reservation_info').reservation_state

    def get_interfaces(self):
        from fabrictestbed_extensions.fablib.interface import Interface

        interfaces = []
        for component in self.get_components():
            for interface in component.get_interfaces():
                interfaces.append(interface)

        return interfaces

    def get_interface(self, name=None, network_name=None):
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
        return self.username

    def get_public_key(self):
        return self.get_slice().get_slice_public_key()

    def get_public_key_file(self):
        return self.get_slice().get_slice_public_key_file()

    def get_private_key(self):
        return self.get_slice().get_slice_private_key()

    def get_private_key_file(self):
        return self.get_slice().get_slice_private_key_file()

    def get_private_key_passphrase(self):
        return self.get_slice().get_private_key_passphrase()

    def add_component(self, model=None, name=None):
        from fabrictestbed_extensions.fablib.component import Component
        return Component.new_component(node=self, model=model, name=name)

    def get_components(self):
        from fabrictestbed_extensions.fablib.component import Component

        return_components = []
        for component_name, component in self.get_fim_node().components.items():
            #return_components.append(Component(self,component))
            return_components.append(Component(self,component))

        return return_components

    def get_component(self, name, verbose=False):
        from fabrictestbed_extensions.fablib.component import Component
        try:
            name = Component.calculate_name(node=self, name=name)
            return Component(self,self.get_fim_node().components[name])
        except Exception as e:
            if verbose:
                traceback.print_exc()
            raise Exception(f"Component not found: {name}")


    def get_ssh_command(self):
        return 'ssh -i {} -J {}@{} {}@{}'.format(self.get_private_key_file(),
                                           fablib.get_bastion_username(),
                                           fablib.get_bastion_public_addr(),
                                           self.get_username(),
                                           self.get_management_ip())

    def validIPAddress(self, IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def execute(self, command, retry=3, retry_interval=10):
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
        try:
            self.execute('ls', retry=1, retry_interval=10)
        except:
            return False
        return True

    def wait_for_ssh(self, retry=6, retry_interval=10):
        try:
            self.execute('echo hello, fabric', retry=retry, retry_interval=retry_interval)
        except:
            return False
        return True

    def get_management_os_interface(self):
        #Assumes that the default route uses the management network

        stdout, stderr = self.execute("sudo ip -j route list")
        stdout_json = json.loads(stdout)

        #print(pythonObj)
        for i in stdout_json:
            if i['dst'] == 'default':
                return  i['dev']

    def get_dataplane_os_interfaces(self):
        management_dev = self.get_management_os_interface()

        stdout, stderr = self.execute("sudo ip -j addr list")
        stdout_json = json.loads(stdout)
        dataplane_devs = []
        for i in stdout_json:
            if i['ifname'] != 'lo' and i['ifname'] !=  management_dev:
                dataplane_devs.append({'ifname': i['ifname'], 'mac': i['address']})

        return dataplane_devs

    def flush_all_os_interfaces(self):
        for iface in self.get_dataplane_os_interfaces():
            self.flush_os_interface(iface['ifname'])

    def flush_os_interface(self, os_iface):
        stdout, stderr = self.execute(f"sudo ip addr flush dev {os_iface}")

    def set_ip_os_interface(self, os_iface=None, vlan=None, ip=None, cidr=None, mtu=None):
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
        self.remove_all_vlan_os_interfaces()
        self.flush_all_os_interfaces()


    def remove_all_vlan_os_interfaces(self):
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
        command = f'sudo ip link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'
        stdout, stderr = self.execute(command)
        command = f'sudo ip link set dev {os_iface}.{vlan} up'
        stdout, stderr = self.execute(command)

        if ip != None and cidr != None:
            self.set_ip_os_interface(os_iface=f"{os_iface}.{vlan}", ip=ip, cidr=cidr, mtu=mtu)

    def ping_test(self, dst_ip):
        command = f'ping -c 3 {dst_ip}  2>&1 > /dev/null && echo Success'
        stdout, stderr = self.execute(command)
        if stdout.replace("\n","") == 'Success':
            return True
        else:
            return False
