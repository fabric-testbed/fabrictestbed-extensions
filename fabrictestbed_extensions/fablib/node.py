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
from __future__ import annotations
import json
import threading
import time
import paramiko
import logging

from tabulate import tabulate

from typing import List, Union, Tuple

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabric_cf.orchestrator.swagger_client import Sliver as OrchestratorSliver

from fim.slivers.network_service import NSLayer

from fabrictestbed.slice_editor import Labels, CapacityHints, ServiceType
from fabrictestbed.slice_editor import Capacities
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.component import Component
from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed.slice_editor import Node as FimNode


class Node:
    default_cores = 2
    default_ram = 8
    default_disk = 10
    default_image = 'default_rocky_8'

    def __init__(self, slice: Slice, node: FimNode):
        """
        Constructor. Sets the fablib slice and FIM node based on arguments.
        :param slice: the fablib slice to have this node on
        :type slice: Slice
        :param node: the FIM node that this Node represents
        :type node: Node
        """
        super().__init__()
        self.fim_node = node
        self.slice = slice
        self.host = None
        self.ip_addr_list_json = None

        # Try to set the username.
        try:
            self.set_username()
        except:
            self.username = None

        try:
            self.sliver = slice.get_sliver(reservation_id=self.get_reservation_id())
        except:
            self.sliver = None

        logging.getLogger("paramiko").setLevel(logging.WARNING)

    def get_fablib_manager(self):
        return self.slice.get_fablib_manager()

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the node.
        Intended for printing node information.
        :return: Tabulated string of node information
        :rtype: String
        """
        table = [ ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Cores", self.get_cores()],
            ["RAM", self.get_ram()],
            ["Disk", self.get_disk()],
            ["Image", self.get_image()],
            ["Image Type", self.get_image_type()],
            ["Host", self.get_host()],
            ["Site", self.get_site()],
            ["Management IP", self.get_management_ip()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ["SSH Command ", self.get_ssh_command()],
            ]

        return tabulate(table) #, headers=["Property", "Value"])

    def get_sliver(self) -> OrchestratorSliver:
        """
        Not intended as API call
        Gets the node SM sliver
        :return: SM sliver for the node
        :rtype: Sliver
        """
        return self.sliver

    @staticmethod
    def new_node(slice: Slice = None, name: str = None, site: str = None, avoid: List[str] = []):
        """
        Not intended for API call. See: Slice.add_node()
        Creates a new FABRIC node and returns a fablib node with the new node.
        :param slice: the fablib slice to build the new node on
        :type slice: Slice
        :param name: the name of the new node
        :type name: str
        :param site: the name of the site to build the node on
        :type site: str
        :param avoid: a list of node names to avoid
        :type avoid: List[str]
        :return: a new fablib node
        :rtype: Node
        """
        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(avoid=avoid)

        logging.info(f"Adding node: {name}, slice: {slice.get_name()}, site: {site}")
        node = Node(slice, slice.topology.add_node(name=name, site=site))
        node.set_capacities(cores=Node.default_cores, ram=Node.default_ram, disk=Node.default_disk)
        node.set_image(Node.default_image)

        return node

    @staticmethod
    def get_node(slice: Slice = None, node=None):
        """
        Not intended for API call.
        Returns a new fablib node using existing FABRIC resources.
        :param slice: the fablib slice storing the existing node
        :type slice: Slice
        :param node: the FIM node stored in this fablib node
        :type node: Node
        :return: a new fablib node storing resources
        :rtype: Node
        """
        return Node(slice, node)

    def get_fim_node(self) -> FimNode:
        """
        Not intended for API call.
        Gets the FABRIC node associated with this fablib node.
        :return: the real FABRIC node
        :rtype: FIMNode
        """
        return self.fim_node

    def set_capacities(self, cores: int = 2, ram: int = 2, disk: int = 10):
        """
        Sets the capacities of the FABRIC node.
        :param cores: the number of cores to set on this node
        :type cores: int
        :param ram: the amount of RAM to set on this node
        :type ram: int
        :param disk: the amount of disk space to set on this node
        :type disk: int
        """
        cores = int(cores)
        ram = int(ram)
        disk = int(disk)

        cap = Capacities(core=cores, ram=ram, disk=disk)
        self.get_fim_node().set_properties(capacities=cap)

    def set_instance_type(self, instance_type: str):
        """
        Sets the instance type of this fablib node on the FABRIC node.
        :param instance_type: the name of the instance type to set
        :type instance_type: String
        """
        self.get_fim_node().set_properties(capacity_hints=CapacityHints(instance_type=instance_type))

    def set_username(self, username: str = None):
        """
        Not intended as an API call.
        Sets this fablib node's username
        Optional username parameter. The username likely should be picked
        to match the image type.
        :param username: username
        """
        if username is not None:
            self.username = username
        elif 'centos' in self.get_image():
            self.username = 'centos'
        elif 'ubuntu' in self.get_image():
            self.username = 'ubuntu'
        elif 'rocky'in self.get_image():
            self.username = 'rocky'
        elif 'fedora'in self.get_image():
            self.username = 'fedora'
        elif 'cirros'in self.get_image():
            self.username = 'cirros'
        elif 'debian'in self.get_image():
            self.username = 'debian'
        elif 'freebsd'in self.get_image():
            self.username = 'freebsd'
        elif 'openbsd'in self.get_image():
            self.username = 'openbsd'
        else:
            self.username = None

    def set_image(self, image: str, username: str = None, image_type: str = 'qcow2'):
        """
        Sets the image information of this fablib node on the FABRIC node.
        :param image: the image reference to set
        :type image: String
        :param username: the username of this fablib node. Currently unused.
        :type username: String
        :param image_type: the image type to set
        :type image_type: String
        """
        self.get_fim_node().set_properties(image_type=image_type, image_ref=image)
        self.set_username(username=username)

    def set_host(self, host_name: str = None):
        """
        Sets the hostname of this fablib node on the FABRIC node.
        :param host_name: the hostname. example: host_name='renc-w2.fabric-testbed.net'
        :type host_name: String
        """
        # example: host_name='renc-w2.fabric-testbed.net'
        labels = Labels()
        labels.instance_parent = host_name
        self.get_fim_node().set_properties(labels=labels)

        # set an attribute used to get host before Submit
        self.host = host_name

    def set_site(self, site):
        """
        Sets the hostname of this fablib node on the FABRIC node.
        :param host_name: the hostname. example: host_name='renc-w2.fabric-testbed.net'
        :type host_name: String
        """
        # example: host_name='renc-w2.fabric-testbed.net'
        self.get_fim_node().site = site

    def get_slice(self) -> Slice:
        """
        Gets the fablib slice associated with this node.
        :return: the fablib slice on this node
        :rtype: Slice
        """
        return self.slice

    def get_name(self) -> str or None:
        """
        Gets the name of the FABRIC node.
        :return: the name of the node
        :rtype: String
        """
        try:
            return self.get_fim_node().name
        except:
            return None

    def get_cores(self) -> int or None:
        """
        Gets the number of cores on the FABRIC node.
        :return: the number of cores on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname='capacity_allocations').core
        except:
            return None

    def get_ram(self) -> int or None:
        """
        Gets the amount of RAM on the FABRIC node.
        :return: the amount of RAM on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname='capacity_allocations').ram
        except:
            return None

    def get_disk(self) -> int or None:
        """
        Gets the amount of disk space on the FABRIC node.
        :return: the amount of disk space on the node
        :rtype: int
        """
        try:
            return self.get_fim_node().get_property(pname='capacity_allocations').disk
        except:
            return None

    def get_image(self) -> str or None:
        """
        Gets the image reference on the FABRIC node.
        :return: the image reference on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().image_ref
        except:
            return None

    def get_image_type(self) -> str or None:
        """
        Gets the image type on the FABRIC node.
        :return: the image type on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().image_type
        except:
            return None

    def get_host(self) -> str or None:
        """
        Gets the hostname on the FABRIC node.
        :return: the hostname on the node
        :rtype: String
        """
        try:
            if self.host is not None:
                return self.host
            return self.get_fim_node().get_property(pname='label_allocations').instance_parent
        except:
            return None

    def get_site(self) -> str or None:
        """
        Gets the sitename on the FABRIC node.
        :return: the sitename on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().site
        except:
            return None

    def get_management_ip(self) -> str or None:
        """
        Gets the management IP on the FABRIC node.
        :return: management IP
        :rtype: String
        """
        try:
            return self.get_fim_node().management_ip
        except:
            return None

    def get_reservation_id(self) -> str or None:
        """
        Gets the reservation ID on the FABRIC node.
        :return: reservation ID on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().get_property(pname='reservation_info').reservation_id
        except:
            return None

    def get_reservation_state(self) -> str or None:
        """
        Gets the reservation state on the FABRIC node.
        :return: the reservation state on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().get_property(pname='reservation_info').reservation_state
        except:
            return None

    def get_error_message(self) -> str or None:
        """
        Gets the error message on the FABRIC node.
        :return: the error message on the node
        :rtype: String
        """
        try:
            return self.get_fim_node().get_property(pname='reservation_info').error_message
        except:
            return ""

    def get_interfaces(self) -> List[Interface] or None:
        """
        Gets a list of the interfaces associated with the FABRIC node.
        :return: a list of interfaces on the node
        :rtype: List[Interface]
        """
        interfaces = []
        for component in self.get_components():
            for interface in component.get_interfaces():
                interfaces.append(interface)

        return interfaces

    def get_interface(self, name: str = None, network_name: str = None) -> Interface or None:
        """
        Gets a particular interface associated with a FABRIC node.
        Accepts either the interface name or a network_name. If a network name
        is used this method will return the interface on the node that is
        connected to the network specified.
        If a name and network_name are both used, the interface name will
        take precedence.
        :param name: interface name to search for
        :type name: str
        :param network_name: network name to search for
        :type name: str
        :raise Exception: if interface is not found
        :return: an interface on the node
        :rtype: Interface
        """
        if name is not None:
            for component in self.get_components():
                for interface in component.get_interfaces():
                    if interface.get_name() == name:
                        return interface
        elif network_name is not None:
            for interface in self.get_interfaces():
                if interface is not None and interface.get_network() is not None and \
                        interface.get_network().get_name() == network_name:
                    return interface

        raise Exception("Interface not found: {}".format(name))

    def get_username(self) -> str:
        """
        Gets the username on this fablib node.
        :return: the username on this node
        :rtype: String
        """
        return self.username

    def get_public_key(self) -> str:
        """
        Gets the public key on fablib node.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the public key on the node
        :rtype: String
        """
        return self.get_slice().get_slice_public_key()

    def get_public_key_file(self) -> str:
        """
        Gets the public key file path on the fablib node.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the public key path
        :rtype: String
        """
        return self.get_slice().get_slice_public_key_file()

    def get_private_key(self) -> str:
        """
        Gets the private key on the fablib node.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the private key on the node
        :rtype: String
        """
        return self.get_slice().get_slice_private_key()

    def get_private_key_file(self) -> str:
        """
        Gets the private key file path on the fablib slice.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the private key path
        :rtype: String
        """
        return self.get_slice().get_slice_private_key_file()

    def get_private_key_passphrase(self) -> str:
        """
        Gets the private key passphrase on the FABLIB slice.
        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.
        :return: the private key passphrase
        :rtype: String
        """
        return self.get_slice().get_private_key_passphrase()

    def add_component(self, model: str = None, name: str = None) -> Component:
        """
        Creates a new FABRIC component using this fablib node.
        Example model include:
        - NIC_Basic: A single port 100 Gbps SR-IOV Virtual Function on a Mellanox ConnectX-6
        - NIC_ConnectX_5: A dual port 25 Gbps Mellanox ConnectX-5
        - NIC_ConnectX_6: A dual port 100 Gbps Mellanox ConnectX-6
        - NVME_P4510: NVMe Storage Device
        - GPU_TeslaT4: Tesla T4 GPU
        - GPU_RTX6000: RTX6000 GPU
        :param model: the name of the component model to add
        :type model: String
        :param name: the name of the new component
        :type name: String
        :return: the new component
        :rtype: Component
        """
        return Component.new_component(node=self, model=model, name=name)

    def add_storage(self, name: str, auto_mount: bool = False) -> Component:
        """
        Creates a new FABRIC Storage component and attaches it to the Node
        :param name: Name of the Storage volume created for the project outside the scope of the Slice
        :param auto_mount: Mount the storage volume
        :rtype: Component
        """
        return Component.new_storage(node=self, name=name, auto_mount=auto_mount)

    def get_components(self) -> List[Component]:
        """
        Gets a list of components associated with this node.
        :return: a list of components on this node
        :rtype: List[Component]
        """
        return_components = []
        for component_name, component in self.get_fim_node().components.items():
            return_components.append(Component(self, component))

        return return_components

    def get_component(self, name: str) -> Component:
        """
        Gets a particular component associated with this node.
        :param name: the name of the component to search for
        :type name: String
        :raise Exception: if component not found by name
        :return: the component on the FABRIC node
        :rtype: Component
        """
        try:
            name = Component.calculate_name(node=self, name=name)
            return Component(self, self.get_fim_node().components[name])
        except Exception as e:
            logging.error(e, exc_info=True)
            raise Exception(f"Component not found: {name}")

    def get_ssh_command(self) -> str:
        """
        Gets a SSH command used to access this node node from a terminal.
        :return: the SSH command to access this node
        :rtype: str
        """
        return 'ssh -i {} -J {}@{} {}@{}'.format(self.get_private_key_file(),
                                           self.get_fablib_manager().get_bastion_username(),
                                           self.get_fablib_manager().get_bastion_public_addr(),
                                           self.get_username(),
                                           self.get_management_ip())

    def validIPAddress(self, IP: str) -> str:
        """
        Checks if the IP string is a valid IP address.
        :param IP: the IP string to check
        :type IP: String
        :return: the type of IP address the IP string is, or 'Invalid'
        :rtype: String
        """
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def __get_paramiko_key(self, private_key_file: str = None, get_private_key_passphrase: str = None) -> paramiko.PKey:
        #TODO: This is a bit of a hack and should probably test he keys for their types
        # rather than relying on execptions
        if get_private_key_passphrase:
            try:
                return paramiko.RSAKey.from_private_key_file(self.get_private_key_file(),
                                                             password=self.get_private_key_passphrase())
            except:
                pass

            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(self.get_private_key_file(),
                                                                        password=self.get_private_key_passphrase())
            except:
                pass
        else:
            try:
                return paramiko.RSAKey.from_private_key_file(self.get_private_key_file())
            except:
                pass

            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(self.get_private_key_file())
            except:
                pass

        raise Exception(f"ssh key invalid: FABRIC requires RSA or ECDSA keys")

    def execute_thread(self, command: str, retry: int = 3, retry_interval: int = 10, username: str = None,
                       private_key_file: str = None, private_key_passphrase: str = None) -> threading.Thread:
        """
        Creates a thread that calls node.execute().  Results (i.e. stdout, stderr) from the thread can be
        retrieved with by calling thread.result()
        :param command: the command to run
        :param retry: the number of times to retry SSH upon failure
        :param retry_interval: the number of seconds to wait before retrying SSH upon failure
        :param username: username
        :param private_key_file: private key file
        :param private_key_passphrase: pass phrase
        :return: a thread that called node.execute()
        :raise Exception: if management IP is invalid
        """

        return self.get_fablib_manager().get_ssh_thread_pool_executor().submit(self.execute,
                                                                               command,
                                                                               retry=retry,
                                                                               retry_interval=retry_interval,
                                                                               username=username,
                                                                               private_key_file=private_key_file,
                                                                               private_key_passphrase=private_key_passphrase)

    def execute(self, command: str, retry: int = 3, retry_interval: int = 10, username: str = None,
                private_key_file:str = None, private_key_passphrase:str = None) -> Tuple[str, str]:
        """
        Runs a command on the FABRIC node.
        :param command: the command to run
        :type command: str
        :param retry: the number of times to retry SSH upon failure
        :type retry: int
        :param retry_interval: the number of seconds to wait before retrying SSH upon failure
        :type retry_interval: int
        :param username
        :param private_key_file
        :param private_key_passphrase
        :return: a tuple of  (stdout[Sting],stderr[String])
        :rtype: Tuple
        :raise Exception: if management IP is invalid
        """
        import logging

        logging.debug(f"execute node: {self.get_name()}, management_ip: {self.get_management_ip()}, command: {command}")

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        # Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = ('0.0.0.0', 22)

        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = ('0:0:0:0:0:0:0:0', 22)
        else:
            raise Exception(f"node.execute: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        bastion_username = self.get_fablib_manager().get_bastion_username()
        bastion_key_file = self.get_fablib_manager().get_bastion_key_filename()

        if username is not None:
            node_username = username
        else:
            node_username = self.username

        if private_key_file is not None:
            node_key_file = private_key_file
        else:
            node_key_file = self.get_private_key_file()

        if private_key_passphrase is not None:
            node_key_passphrase = private_key_passphrase
        else:
            node_key_passphrase=self.get_private_key_passphrase()

        for attempt in range(retry):
            try:
                key = self.__get_paramiko_key(private_key_file=node_key_file,
                                              get_private_key_passphrase=node_key_passphrase)
                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(self.get_fablib_manager().get_bastion_public_addr(), username=bastion_username,
                                key_filename=bastion_key_file)

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(management_ip,username=node_username,pkey = key, sock=bastion_channel)

                stdin, stdout, stderr = client.exec_command(command)
                rtn_stdout = str(stdout.read(),'utf-8').replace('\\n','\n')
                rtn_stderr = str(stderr.read(),'utf-8').replace('\\n','\n')

                client.close()
                bastion_channel.close()

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(f"Running node.execute(): command: {command}, elapsed time: {end - start} seconds")

                logging.debug(f"rtn_stdout: {rtn_stdout}")
                logging.debug(f"rtn_stderr: {rtn_stderr}")

                return rtn_stdout, rtn_stderr
                #success, skip other tries
                break
            except Exception as e:
                try:
                    client.close()
                except:
                    logging.debug("Exception in client.close")
                    pass
                try:
                    bastion_channel.close()
                except:
                    logging.debug("Exception in bastion_channel.close()")
                    pass


                if attempt+1 == retry:
                    raise e

                #Fail, try again
                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    logging.debug(f"SSH execute fail. Slice: {self.get_slice().get_name()}, "
                                  f"Node: {self.get_name()}, trying again")
                    logging.debug(e, exc_info=True)

                time.sleep(retry_interval)
                pass

        raise Exception("ssh failed: Should not get here")

    def upload_file_thread(self, local_file_path: str, remote_file_path: str, retry: int = 3, retry_interval: int = 10):
        """
        Creates a thread that calls node.upload_file().  Results from the thread can be
        retrieved with by calling thread.result()
        :param local_file_path: the path to the file to upload
        :type local_file_path: str
        :param remote_file_path: the destination path of the file on the node
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :return: a thread that called node.execute()
        :rtype: Thread
        :raise Exception: if management IP is invalid
        """
        return self.get_fablib_manager().get_ssh_thread_pool_executor().submit(self.upload_file,
                                                                               local_file_path,
                                                                               remote_file_path,
                                                                               retry=retry,
                                                                               retry_interval=retry_interval)

    def upload_file(self, local_file_path: str, remote_file_path: str, retry: int = 3, retry_interval: int = 10):
        """
        Upload a local file to a remote location on the node.
        :param local_file_path: the path to the file to upload
        :type local_file_path: str
        :param remote_file_path: the destination path of the file on the node
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        logging.debug(f"upload node: {self.get_name()}, local_file_path: {local_file_path}")

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        # Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = ('0.0.0.0', 22)
        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = ('0:0:0:0:0:0:0:0', 22)
        else:
            raise Exception(f"upload_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(retry):
            try:
                key = self.__get_paramiko_key(private_key_file=self.get_private_key_file(),
                                              get_private_key_passphrase=self.get_private_key_file())

                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(self.get_fablib_manager().get_bastion_public_addr(),
                                username=self.get_fablib_manager().get_bastion_username(),
                                key_filename=self.get_fablib_manager().get_bastion_key_filename())

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

                bastion_channel.close()

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(f"Running node.upload_file(): file: {local_file_path}, "
                                  f"elapsed time: {end - start} seconds")

                return file_attributes
            except Exception as e:
                try:
                    client.close()
                except:
                    logging.debug("Exception in client.close")
                    pass
                try:
                    bastion_channel.close()
                except:
                    logging.debug("Exception in bastion_channel.close()")
                    pass

                if attempt+1 == retry:
                    raise e

                #Fail, try again
                print(f"SCP upload fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp upload failed")

    def download_file_thread(self, local_file_path: str, remote_file_path: str, retry: int = 3, retry_interval: int = 10):
        """"
        Creates a thread that calls node.download_file().  Results from the thread can be
        retrieved with by calling thread.result()
        :param local_file_path: the destination path for the remote file
        :type local_file_path: str
        :param remote_file_path: the path to the remote file to download
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP upon failure
        :type retry_interval: int
        :return: a thread that called node.download_file()
        :rtype: Thread
        :raise Exception: if management IP is invalid
        """
        return self.get_fablib_manager().get_ssh_thread_pool_executor().submit(self.download_file,
                                                                               local_file_path,
                                                                               remote_file_path,
                                                                               retry=retry,
                                                                               retry_interval=retry_interval)

    def download_file(self, local_file_path: str, remote_file_path: str, retry: int = 3, retry_interval: int = 10):
        """
        Download a remote file from the node to a local destination.
        :param local_file_path: the destination path for the remote file
        :type local_file_path: str
        :param remote_file_path: the path to the remote file to download
        :type remote_file_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP upon failure
        :type retry_interval: int
        """
        logging.debug(f"download node: {self.get_name()}, remote_file_path: {remote_file_path}")

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        # Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = ('0.0.0.0', 22)

        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = ('0:0:0:0:0:0:0:0', 22)
        else:
            raise Exception(f"upload_file: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(retry):
            try:
                key = self.__get_paramiko_key(private_key_file=self.get_private_key_file(),
                                              get_private_key_passphrase=self.get_private_key_file())

                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(self.get_fablib_manager().get_bastion_public_addr(),
                                username=self.get_fablib_manager().get_bastion_username(),
                                key_filename=self.get_fablib_manager().get_bastion_key_filename())

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)

                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(management_ip,username=self.username,pkey = key, sock=bastion_channel)

                ftp_client = client.open_sftp()
                file_attributes = ftp_client.get(remote_file_path, local_file_path)
                ftp_client.close()

                bastion_channel.close()

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(f"Running node.download(): file: {remote_file_path}, "
                                  f"elapsed time: {end - start} seconds")

                return file_attributes
            except Exception as e:
                try:
                    client.close()
                except:
                    logging.debug("Exception in client.close")
                    pass
                try:
                    bastion_channel.close()
                except:
                    logging.debug("Exception in bastion_channel.close()")
                    pass

                if attempt+1 == retry:
                    raise e

                #Fail, try again
                print(f"SCP download fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp download failed")

    def upload_directory_thread(self, local_directory_path: str, remote_directory_path: str, retry: int = 3,
                                retry_interval: int = 10):
        """"
        Creates a thread that calls node.upload_directory. Results from the thread can be
        retrieved with by calling thread.result()
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :return: a thread that called node.download_file()
        :rtype: Thread
        :raise Exception: if management IP is invalid
        """
        return self.get_fablib_manager().get_ssh_thread_pool_executor().submit(self.upload_directory,
                                                                               local_directory_path,
                                                                               remote_directory_path,
                                                                               retry=retry,
                                                                               retry_interval=retry_interval)

    def upload_directory(self, local_directory_path: str, remote_directory_path: str, retry: int = 3,
                         retry_interval: int = 10):
        """
        Upload a directory to remote location on the node.
        Makes a gzipped tarball of a directory and uploades it to a node. Then
        unzips and tars the directory at the remote_directory_path
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        import tarfile
        import os

        logging.debug(f"upload node: {self.get_name()}, local_directory_path: {local_directory_path}")

        output_filename = local_directory_path.split('/')[-1]
        root_size = len(local_directory_path) - len(output_filename)
        temp_file = "/tmp/" + output_filename + ".tar.gz"

        with tarfile.open(temp_file, "w:gz") as tar_handle:
            for root, dirs, files in os.walk(local_directory_path):
                for file in files:
                    tar_handle.add(os.path.join(root, file), arcname = os.path.join(root, file)[root_size:])

        self.upload_file(temp_file, temp_file, retry, retry_interval)
        os.remove(temp_file)
        self.execute("mkdir -p "+remote_directory_path + "; tar -xf " + temp_file + " -C " +
                     remote_directory_path + "; rm " + temp_file, retry, retry_interval)
        return "success"

    def download_directory_thread(self, local_directory_path: str, remote_directory_path: str, retry: int = 3,
                                  retry_interval: int = 10):
        """"
        Creates a thread that calls node.download_directory. Results from the thread can be
        retrieved with by calling thread.result()
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        return self.get_fablib_manager().get_ssh_thread_pool_executor().submit(self.download_directory,
                                                                               local_directory_path,
                                                                               remote_directory_path,
                                                                               retry=retry,
                                                                               retry_interval=retry_interval)

    def download_directory(self, local_directory_path: str, remote_directory_path: str, retry: int = 3,
                           retry_interval: int = 10):
        """
        Downloads a directory from remote location on the node.
        Makes a gzipped tarball of a directory and downloads it from a node. Then
        unzips and tars the directory at the local_directory_path
        :param local_directory_path: the path to the directory to upload
        :type local_directory_path: str
        :param remote_directory_path: the destination path of the directory on the node
        :type remote_directory_path: str
        :param retry: how many times to retry SCP upon failure
        :type retry: int
        :param retry_interval: how often to retry SCP on failure
        :type retry_interval: int
        :raise Exception: if management IP is invalid
        """
        import tarfile
        import os
        logging.debug(f"upload node: {self.get_name()}, local_directory_path: {local_directory_path}")

        temp_file = "/tmp/unpackingfile.tar.gz"
        self.execute("tar -czf " + temp_file + " " + remote_directory_path, retry, retry_interval)

        self.download_file(temp_file, temp_file, retry, retry_interval)
        tar_file = tarfile.open(temp_file)
        tar_file.extractall(local_directory_path)

        self.execute("rm " + temp_file, retry, retry_interval)
        os.remove(temp_file)
        return "success"

    def test_ssh(self) -> bool:
        """
        Test whether SSH is functional on the node.
        :return: true if SSH is working, false otherwise
        :rtype: bool
        """
        logging.debug(f"test_ssh: node {self.get_name()}")

        try:
            if self.get_management_ip() is None:
                logging.debug(f"Node: {self.get_name()} failed test_ssh because management_ip == None" )

            self.execute(f'echo test_ssh from {self.get_name()}', retry=1, retry_interval=10)
        except Exception as e:
            #logging.debug(f"{e}")
            logging.debug(e, exc_info=True)
            return False
        return True

    def get_management_os_interface(self) -> str or None:
        """
        Gets the name of the management interface used by the node's operating
        system.
        :return: interface name
        :rtype: String
        """
        # TODO: Add docstring after doc networking classes
        # Assumes that the default route uses the management network
        logging.debug(f"{self.get_name()}->get_management_os_interface")
        stdout, stderr = self.execute("sudo ip -j route list")
        stdout_json = json.loads(stdout)

        #print(pythonObj)
        for i in stdout_json:
            if i['dst'] == 'default':
                logging.debug(f"{self.get_name()}->get_management_os_interface: management_os_interface {i['dev']}")
                return i['dev']
        return None

    def get_dataplane_os_interfaces(self) -> List[dict]:
        """
        Gets a list of all the dataplane interface names used by the node's
        operating system.
        :return: interface names
        :rtype: List[String]
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
        Flushes the configuration of all dataplane interfaces in the node.
        """
        for iface in self.get_dataplane_os_interfaces():
            self.flush_os_interface(iface['ifname'])

    def flush_os_interface(self, os_iface: str):
        """
        Flush the configuration of an interface in the node
        :param os_iface: the name of the interface to flush
        :type os_iface: String
        """
        stdout, stderr = self.execute(f"sudo ip addr flush dev {os_iface}")
        stdout, stderr = self.execute(f"sudo ip -6 addr flush dev {os_iface}")

    def ip_addr_list(self, output='json', update=False):

        try:
            if self.ip_addr_list_json is not None and update == False:
                return self.ip_addr_list_json
            else:
                if output == 'json':
                    stdout, stderr = self.execute(f"sudo  ip -j addr list")
                    self.ip_addr_list_json = json.loads(stdout)
                    return self.ip_addr_list_json
                else:
                    stdout, stderr = self.execute(f"sudo ip list")
                    return stdout
        except Exception as e:
            logging.warning(f"Failed to get ip addr list: {e}")
            raise e

    def ip_route_add(self, subnet: Union[IPv4Network, IPv6Network], gateway: Union[IPv4Address, IPv6Address]):
        """
        Add a route on the node.
        :param subnet: The destination subnet
        :type subnet:  IPv4Network or IPv6Network
        :param gateway: The next hop gateway.
        :type gateway: IPv4Address or IPv6Address
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} route add {subnet} via {gateway}")
        except Exception as e:
            logging.warning(f"Failed to add route: {e}")
            raise e

    def network_manager_stop(self):
        try:
            # for iface in self.get_interfaces():
            #     dev = iface.get_os_interface()
            #     if dev != None:
            #         logging.info(f"nmcli delete con for {dev}")
            #         logging.info(f"sudo nmcli -t -g GENERAL.CONNECTION device show {dev}")
            #         stdout, stderr = self.execute(f"sudo nmcli -t -g GENERAL.CONNECTION device show {dev}")
            #         logging.info(f"stdout: {stdout}, stderr: {stderr}")
            #
            #         conn = stdout.rstrip('\n')
            #         if conn != '':
            #             logging.info(f"sudo nmcli conn delete '{conn}'")
            #             stdout, stderr = self.execute(f"sudo nmcli conn delete '{conn}'")
            #             logging.info(f"stdout: {stdout}, stderr: {stderr}")
            #         else:
            #             logging.info(f"No conn for device. conn: '{conn}'")

            stdout, stderr = self.execute(f"sudo systemctl stop NetworkManager")
            logging.info(f"Stopped NetworkManager with 'sudo systemctl stop "
                         f"NetworkManager': stdout: {stdout}\nstderr: {stderr}")

            #for iface in self.get_interfaces():
            #    try:
            #        iface.ip_link_down()
            #    except Exception as e:
            #        logging.info(f"Attempt to bring down dev failed")
            #
            #    try:
            #        iface.ip_link_up()
            #    except Exception as e:
            #        logging.info(f"Attempt to bring up dev failed")
        except Exception as e:
            logging.warning(f"Failed to stop network manager: {e}")
            raise e

    def network_manager_start(self):
        try:
            stdout, stderr = self.execute(f"sudo systemctl start NetworkManager")
            logging.info(f"Started NetworkManager with 'sudo systemctl start NetworkManager': stdout: {stdout}\nstderr: {stderr}")
        except Exception as e:
            logging.warning(f"Failed to start network manager: {e}")
            raise e

    def ip_route_del(self, subnet: Union[IPv4Network, IPv6Network], gateway: Union[IPv4Address, IPv6Address]):
        """
        Delete a route on the node.
        :param subnet: The destination subnet
        :type subnet:  IPv4Network or IPv6Network
        :param gateway: The next hop gateway.
        :type gateway: IPv4Address or IPv6Address
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} route del {subnet} via {gateway}")
        except Exception as e:
            logging.warning(f"Failed to del route: {e}")
            raise e

    def ip_addr_add(self, addr: Union[IPv4Address, IPv6Address], subnet: Union[IPv4Network, IPv6Network],
                    interface: Interface):
        """
        Add an IP to an interface on the node.
        :param addr: IP address
        :type addr:  IPv4Address or IPv6Address
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} addr add {addr}/{subnet.prefixlen} dev {interface.get_os_interface()} ")
        except Exception as e:
            logging.warning(f"Failed to add addr: {e}")
            raise e

    def ip_addr_del(self, addr: Union[IPv4Address, IPv6Address], subnet: Union[IPv4Network, IPv6Network],
                    interface: Interface):
        """
        Delete an IP to an interface on the node.
        :param addr: IP address
        :type addr:  IPv4Address or IPv6Address
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        ip_command = ""
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} addr del {addr}/{subnet.prefixlen} dev {interface.get_os_interface()} ")
        except Exception as e:
            logging.warning(f"Failed to del addr: {e}")
            raise e

    def ip_link_up(self, subnet: Union[IPv4Network, IPv6Network], interface: Interface):
        """
        Bring up a link on an interface on the node.
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        try:
            if interface.get_network().get_layer() == NSLayer.L3:
                if interface.get_network().get_type() == ServiceType.FABNetv6:
                    ip_command = "sudo ip -6"
                elif interface.get_network().get_type() == ServiceType.FABNetv4:
                    ip_command = "sudo ip"
            else:
                ip_command = "sudo ip"
        except Exception as e:
            logging.warning(f"Failed to down link: {e}")
            return

        try:
            self.execute(f"{ip_command} link set dev {interface.get_physical_os_interface()} up")
        except Exception as e:
            logging.warning(f"Failed to up link: {e}")
            raise e

        try:
            self.execute(f"{ip_command} link set dev {interface.get_os_interface()} up")
        except Exception as e:
            logging.warning(f"Failed to up link: {e}")
            raise e

    def ip_link_down(self, subnet: Union[IPv4Network, IPv6Network], interface: Interface):
        """
        Bring down a link on an interface on the node.
        :param subnet: subnet.
        :type subnet: IPv4Network or IPv6Network
        :param interface: the FABlib interface.
        :type interface: Interface
        """
        try:
            if interface.get_network().get_layer() == NSLayer.L3:
                if interface.get_network().get_type() == ServiceType.FABNetv6:
                    ip_command = "sudo ip -6"
                elif interface.get_network().get_type() == ServiceType.FABNetv4:
                    ip_command = "sudo ip"
            else:
                ip_command = "sudo ip"
        except Exception as e:
            #logging.warning(f"Failed to down link: {e}")
            return

        try:
            self.execute(f"{ip_command} link set dev {interface.get_os_interface()} down")
        except Exception as e:
            logging.warning(f"Failed to down link: {e}")
            raise e

    def set_ip_os_interface(self, os_iface: str = None, vlan: str = None, ip: str = None, cidr: str = None,
                            mtu: str = None):
        """
        Depricated
        """
        # TODO: Add docstring after doc networking classes
        if cidr:
            cidr = str(cidr)
        if mtu:
            mtu = str(mtu)

        if self.validIPAddress(ip) == "IPv4":
            ip_command = "sudo ip"
        elif self.validIPAddress(ip) == "IPv6":
            ip_command = "sudo ip -6"
        else:
            raise Exception(f"Invalid IP {ip}. IP must be vaild IPv4 or IPv6 string.")

        # Bring up base iface
        logging.debug(f"{self.get_name()}->set_ip_os_interface: os_iface {os_iface}, vlan {vlan}, ip {ip}, cidr {cidr}, mtu {mtu}")
        command = f'{ip_command} link set dev {os_iface} up'

        if mtu is not None:
            command += f" mtu {mtu}"
        stdout, stderr = self.execute(command)

        # config vlan iface
        if vlan is not None:
            # create vlan iface
            command = f'{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'
            stdout, stderr = self.execute(command)

            # bring up vlan iface
            os_iface = f"{os_iface}.{vlan}"
            command = f'{ip_command} link set dev {os_iface} up'
            if mtu != None:
                command += f" mtu {mtu}"
            stdout, stderr = self.execute(command)

        if ip is not None and cidr is not None:
            #Set ip
            command = f"{ip_command} addr add {ip}/{cidr} dev {os_iface}"
            stdout, stderr = self.execute(command)

        stdout, stderr = self.execute(command)

    def clear_all_ifaces(self):
        """
        Flush all interfaces and delete VLAN os interfaces
        """
        # TODO: Add docstring after doc networking classes
        self.remove_all_vlan_os_interfaces()
        self.flush_all_os_interfaces()

    def remove_all_vlan_os_interfaces(self):
        """
        Delete all VLAN os interfaces
        """
        # TODO: Add docstring after doc networking classes
        management_os_iface = self.get_management_os_interface()

        stdout, stderr = self.execute("sudo ip -j addr list")
        stdout_json = json.loads(stdout)
        dataplane_devs = []
        for i in stdout_json:
            if i['ifname'] == management_os_iface or i['ifname'] == 'lo':
                stdout_json.remove(i)
                continue

            # If iface is vlan linked to base iface
            if 'link' in i.keys():
                self.remove_vlan_os_interface(os_iface=i['ifname'])


    def remove_vlan_os_interface(self, os_iface: str = None):
        """
        Remove one VLAN OS interface
        """
        # TODO: Add docstring after doc networking classes
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

    def add_vlan_os_interface(self, os_iface: str = None, vlan: str = None, ip: str = None, cidr: str = None,
                              mtu: str = None, interface: str = None):
        """
        Depricated
        """
        # TODO: Add docstring after doc networking classes

        if vlan: vlan=str(vlan)
        if cidr: cidr=str(cidr)
        if mtu: mtu=str(mtu)

        try:
            gateway = None
            if interface.get_network().get_layer() == NSLayer.L3:
                if interface.get_network().get_type() == ServiceType.FABNetv6:
                    ip_command = "sudo ip -6"
                elif interface.get_network().get_type() == ServiceType.FABNetv4:
                    ip_command = "sudo ip"
            else:
                ip_command = "sudo ip"
        except Exception as e:
            logging.warning(f"Failed to get network layer and/or type: {e}")
            ip_command = "sudo ip"

        command = f'{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'
        stdout, stderr = self.execute(command)

        command = f'{ip_command} link set dev {os_iface} up'
        stdout, stderr = self.execute(command)

        command = f'{ip_command} link set dev {os_iface}.{vlan} up'
        stdout, stderr = self.execute(command)

        if ip != None and cidr != None:
            self.set_ip_os_interface(os_iface=f"{os_iface}.{vlan}", ip=ip, cidr=cidr, mtu=mtu)

    def ping_test(self, dst_ip: str) -> bool:
        """
        Test a ping from the node to a destination IP
        :param dst_ip: destination IP String.
        :type dst_ip: String
        """
        # TODO: Add docstring after doc networking classes
        logging.debug(f"ping_test: node {self.get_name()}")

        command = f'ping -c 1 {dst_ip}  2>&1 > /dev/null && echo Success'
        stdout, stderr = self.execute(command)
        if stdout.replace("\n","") == 'Success':
            return True
        else:
            return False
