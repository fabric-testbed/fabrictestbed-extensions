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
import paramiko
import logging
from tabulate import tabulate


import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

#from .abc_fablib import AbcFabLIB
from fabrictestbed_extensions.fablib.fablib import fablib


from .. import images

#+------------------------+--------+
#| Name                   | Status |
#+------------------------+--------+
#| default_centos8_stream | active |
#| default_centos9_stream | active |
#| default_centos_7       | active |
#| default_centos_8       | active |
#| default_cirros         | active |
#| default_debian_10      | active |
#| default_fedora_35      | active |
#| default_freebsd_13_zfs | active |
#| default_openbsd_7      | active |
#| default_rocky_8        | active |
#| default_ubuntu_18      | active |
#| default_ubuntu_20      | active |
#| default_ubuntu_21      | active |
#| default_ubuntu_22      | active |
#+------------------------+--------+

#class Node(AbcFabLIB):
class Node():
    default_cores = 2
    default_ram = 8
    default_disk = 10
    default_image = 'default_rocky_8'


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

        try:
            self.sliver = slice.get_sliver(reservation_id=self.get_reservation_id())
        except:
            self.sliver = None


        logging.getLogger("paramiko").setLevel(logging.WARNING)

    def __str__(self):
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

    def get_subnet(self):
        try:
            return self.get_fim_node().gateway.subnet
        except:
            return None

    def get_sliver(self):
        return self.sliver

    @staticmethod
    def new_node(slice=None, name=None, site=None, avoid=[]):
        from fabrictestbed_extensions.fablib.node import Node

        if site==None:
            [site] = fablib.get_random_sites(avoid=avoid)

        logging.info(f"Adding node: {name}, slice: {slice.get_name()}, site: {site}")
        node = Node(slice, slice.topology.add_node(name=name, site=site))
        node.set_capacities(cores=Node.default_cores, ram=Node.default_ram, disk=Node.default_disk)
        node.set_image(Node.default_image)

        return node

    @staticmethod
    def get_node(slice=None, node=None):
        from fabrictestbed_extensions.fablib.node import Node
        return Node(slice, node)

    def get_fim_node(self):
        return self.fim_node

    def set_capacities(self, cores=2, ram=2, disk=2):
        cores=int(cores)
        ram=int(ram)
        disk=int(disk)

        cap = Capacities(core=cores, ram=ram, disk=disk)
        self.get_fim_node().set_properties(capacities=cap)

    def set_instance_type(self, instance_type):
        self.get_fim_node().set_properties(capacity_hints=CapacityHints(instance_type=instance_type))

    def set_username(self, username=None):
        if 'centos' in self.get_image():
            self.username = 'centos'
        elif 'ubuntu' in self.get_image():
            self.username = 'ubuntu'
        elif 'rocky'in self.get_image():
            self.username = 'rocky'
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
        try:
            return self.get_fim_node().name
        except:
            return None

    def get_cores(self):
        try:
            return self.get_fim_node().get_property(pname='capacity_allocations').core
        except:
            return None

    def get_ram(self):
        try:
            return self.get_fim_node().get_property(pname='capacity_allocations').ram
        except:
            return None

    def get_disk(self):
        try:
            return self.get_fim_node().get_property(pname='capacity_allocations').disk
        except:
            return None

    def get_image(self):
        try:
            return self.get_fim_node().image_ref
        except:
            return None

    def get_image_type(self):
        try:
            return self.get_fim_node().image_type
        except:
            return None

    def get_host(self):
        try:
            return self.get_fim_node().get_property(pname='label_allocations').instance_parent
        except:
            return None

    def get_site(self):
        try:
            return self.get_fim_node().site
        except:
            return None

    def get_management_ip(self):
        try:
            return self.get_fim_node().management_ip
        except:
            return None

    def get_reservation_id(self):
        try:
            return self.get_fim_node().get_property(pname='reservation_info').reservation_id
        except:
            return None

    def get_reservation_state(self):
        try:
            return self.get_fim_node().get_property(pname='reservation_info').reservation_state
        except:
            return None

    def get_error_message(self):
        try:
            return self.get_fim_node().get_property(pname='reservation_info').error_message
        except:
            return ""

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
                if interface != None and interface.get_network() != None and interface.get_network().get_name() == network_name:
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

    def get_component(self, name):
        from fabrictestbed_extensions.fablib.component import Component
        try:
            name = Component.calculate_name(node=self, name=name)
            return Component(self,self.get_fim_node().components[name])
        except Exception as e:
            logging.error(e, exc_info=True)
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

    def __get_paramiko_key(self, private_key_file=None, get_private_key_passphrase=None):
        #TODO: This is a bit of a hack and should probably test he keys for their types
        # rather than relying on execptions
        if get_private_key_passphrase:
            try:
                return paramiko.RSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
            except:
                pass

            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
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

    def execute(self, command, retry=3, retry_interval=10):
        import logging

        logging.debug(f"execute node: {self.get_name()}, management_ip: {self.get_management_ip()}, command: {command}")

        if fablib.get_log_level() == logging.DEBUG:
            start = time.time()

        #Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            src_addr = (fablib.get_bastion_private_ipv4_addr(), 22)
        elif self.validIPAddress(management_ip) == 'IPv6':
            src_addr = (fablib.get_bastion_private_ipv6_addr(), 22)
        else:
            raise Exception(f"node.execute: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)

        for attempt in range(retry):
            try:
                key = self.__get_paramiko_key(private_key_file=self.get_private_key_file(), get_private_key_passphrase=self.get_private_key_file())
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

                stdin, stdout, stderr = client.exec_command('echo \"' + command + '\" > /tmp/fabric_execute_script.sh; chmod +x /tmp/fabric_execute_script.sh; /tmp/fabric_execute_script.sh')
                rtn_stdout = str(stdout.read(),'utf-8').replace('\\n','\n')
                rtn_stderr = str(stderr.read(),'utf-8').replace('\\n','\n')


                client.close()
                bastion_channel.close()

                if fablib.get_log_level() == logging.DEBUG:
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
                if fablib.get_log_level() == logging.DEBUG:
                    logging.debug(f"SSH execute fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                    logging.debug(e, exc_info=True)

                time.sleep(retry_interval)
                pass

        raise Exception("ssh failed: Should not get here")


    def upload_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        import paramiko
        import time

        logging.debug(f"upload node: {self.get_name()}, local_file_path: {local_file_path}")

        if fablib.get_log_level() == logging.DEBUG:
            start = time.time()

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
                key = self.__get_paramiko_key(private_key_file=self.get_private_key_file(), get_private_key_passphrase=self.get_private_key_file())

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

                bastion_channel.close()

                if fablib.get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(f"Running node.upload_file(): file: {local_file_path}, elapsed time: {end - start} seconds")

                return file_attributes
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
                print(f"SCP upload fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp upload failed")



    def download_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        import paramiko
        import time

        logging.debug(f"download node: {self.get_name()}, remote_file_path: {remote_file_path}")


        if fablib.get_log_level() == logging.DEBUG:
            start = time.time()

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
                key = self.__get_paramiko_key(private_key_file=self.get_private_key_file(), get_private_key_passphrase=self.get_private_key_file())

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

                bastion_channel.close()

                if fablib.get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(f"Running node.download(): file: {remote_file_path}, elapsed time: {end - start} seconds")

                return file_attributes
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
                print(f"SCP download fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                print(f"Fail: {e}")
                #traceback.print_exc()
                time.sleep(retry_interval)
                pass

        raise Exception("scp download failed")

    def upload_directory(self,local_directory_path, remote_directory_path, retry=3, retry_interval=10):
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
        self.execute("mkdir -p "+remote_directory_path + "; tar -xf " + temp_file + " -C " + remote_directory_path + "; rm " + temp_file, retry, retry_interval)
        return "success"

    def download_directory(self,local_directory_path, remote_directory_path, retry=3, retry_interval=10):
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

    def test_ssh(self):
        logging.debug(f"test_ssh: node {self.get_name()}")

        try:
            self.execute(f'echo test_ssh from {self.get_name()}', retry=1, retry_interval=10)
        except Exception as e:
            #logging.debug(f"{e}")
            logging.debug(e, exc_info=True)
            return False
        return True

    #def wait_for_ssh(self, retry=6, retry_interval=10):
    #    try:
    #        self.execute('echo hello, fabric', retry=retry, retry_interval=retry_interval)
    #    except:
    #        return False
    #    return True

    def get_management_os_interface(self):
        #Assumes that the default route uses the management network
        logging.debug(f"{self.get_name()}->get_management_os_interface")
        stdout, stderr = self.execute("sudo ip -j route list")
        stdout_json = json.loads(stdout)

        #print(pythonObj)
        for i in stdout_json:
            if i['dst'] == 'default':
                logging.debug(f"{self.get_name()}->get_management_os_interface: management_os_interface {i['dev']}")
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
        stdout, stderr = self.execute(f"sudo ip -6 addr flush dev {os_iface}")



    def validIPAddress(self, IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"


    def ip_route_add(self, subnet, gateway):
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} route add {subnet} via {gateway}")
        except Exception as e:
            logging.warning(f"Failed to add route: {e}")
            raise e


    def ip_route_del(self, subnet, gateway):
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} route del {subnet} via {gateway}")
        except Exception as e:
            logging.warning(f"Failed to del route: {e}")
            raise e

    def ip_addr_add(self, addr, subnet, interface):
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} addr add {addr}/{subnet.prefixlen} dev {interface.get_os_interface()} ")
        except Exception as e:
            logging.warning(f"Failed to add addr: {e}")
            raise e

    def ip_addr_del(self, addr, subnet, interface):
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} addr del {addr}/{subnet.prefixlen} dev {iface.get_os_interface()} ")
        except Exception as e:
            logging.warning(f"Failed to del addr: {e}")
            raise e

    def ip_link_up(self, interface):
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} link set dev {iface.get_os_interface()} up")
        except Exception as e:
            logging.warning(f"Failed to up link: {e}")
            raise e

    def ip_link_down(self, interface):
        if type(subnet) == IPv6Network:
            ip_command = "sudo ip -6"
        elif type(subnet) == IPv4Network:
            ip_command = "sudo ip"

        try:
            self.execute(f"{ip_command} link set dev {iface.get_os_interface()} down")
        except Exception as e:
            logging.warning(f"Failed to up link: {e}")
            raise e



    def set_ip_os_interface(self, os_iface=None, vlan=None, ip=None, cidr=None, mtu=None):
        if cidr: cidr=str(cidr)
        if mtu: mtu=str(mtu)

        if self.validIPAddress(ip) == "IPv4":
            ip_command = "sudo ip"
        elif self.validIPAddress(ip) == "IPv6":
            ip_command = "sudo ip -6"
        else:
            raise Exception(f"Invalid IP {ip}. IP must be vaild IPv4 or IPv6 string.")

        #Bring up base iface
        logging.debug(f"{self.get_name()}->set_ip_os_interface: os_iface {os_iface}, vlan {vlan}, ip {ip}, cidr {cidr}, mtu {mtu}")
        command = f'{ip_command} link set dev {os_iface} up'

        if mtu != None:
            command += f" mtu {mtu}"
        stdout, stderr = self.execute(command)

        #config vlan iface
        if vlan != None:
            #create vlan iface
            command = f'{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'
            stdout, stderr = self.execute(command)

            #bring up vlan iface
            os_iface = f"{os_iface}.{vlan}"
            command = f'{ip_command} link set dev {os_iface} up'
            if mtu != None:
                command += f" mtu {mtu}"
            stdout, stderr = self.execute(command)

        if ip != None and cidr != None:
            #Set ip
            command = f"{ip_command} addr add {ip}/{cidr} dev {os_iface}"
            stdout, stderr = self.execute(command)

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

    def get_interface_map(self):
        #data = {}
        #Get interface data
        logging.debug(f"get_interface_map: node {self.get_name()}")

        interfaces = {}
        for i in self.get_interfaces():
            logging.debug(f"get_interface_map: i: {i}")

            #print(f"interface: {i.get_name()}")
            #print(f"os_interface: {i.get_physical_os_interface()}")
            if i.get_network() != None:
                logging.debug(f"i.get_network().get_name(): {i.get_network().get_name()}")
                network_name = i.get_network().get_name()
                #print(f"network: {i.get_network().get_name()}")
            else:
                logging.debug(f"i.get_network(): None")
                network_name = None
                #print(f"network: None")

            interfaces[i.get_name()] =  { 'network':  network_name,
                         'os_interface':  i.get_physical_os_interface() }
        return interfaces

    def save_data(self):
        logging.debug(f"save_data: node {self.get_name()}")

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

        with open(f'/tmp/fablib/fabric_data/{self.get_name()}.json', 'w') as outfile:
            json.dump(interfaces, outfile)

        #print(f"interfaces: {json.dumps(interfaces).replace('\"','\\"')}")

        self.upload_file(f'/tmp/fablib/fabric_data/{self.get_name()}.json', f'{self.get_name()}.json')


    def load_data(self):
        logging.debug(f"load_data: node {self.get_name()}")

        try:
            self.download_file(f'{self.get_name()}.json', f'/tmp/fablib/fabric_data/{self.get_name()}.json')

            interfaces=""
            with open(f'/tmp/fablib/fabric_data/{self.get_name()}.json', 'r') as infile:
                interfaces = json.load(infile)


            interface_map = self.get_slice().network_iface_map #= self.get_slice().get_interface_map()
            #print(f"interfaces {interfaces}")
            for interface_name, net_map in interfaces.items():
                logging.debug(f"interface_name: {interface_name}, {net_map}")
                if net_map['network'] != None:
                    interface_map[net_map['network']][self.get_name()] = net_map['os_interface']

            self.get_slice().network_iface_map = interface_map
            logging.debug(f"{self.get_slice().network_iface_map}")
        except Exception as e:
            logging.error(f"load data failes: {e}")
            logging.error(e, exc_info=True)
            raise e



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


    def add_vlan_os_interface(self, os_iface=None, vlan=None, ip=None, cidr=None, mtu=None, interface=None):

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


        #if interface. == "IPv4":
        #    ip_command = "sudo ip"
        #elif self.validIPAddress(ip) == "IPv6":
        #    ip_command = "sudo ip -6"
        #else:
        #    logging.debug(f"Invalid IP {ip}. IP must be vaild IPv4 or IPv6 string. Config VLAN interface only.")

        command = f'{ip_command} link add link {os_iface} name {os_iface}.{vlan} type vlan id {vlan}'

        stdout, stderr = self.execute(command)
        command = f'{ip_command} link set dev {os_iface}.{vlan} up'
        stdout, stderr = self.execute(command)

        if ip != None and cidr != None:
            self.set_ip_os_interface(os_iface=f"{os_iface}.{vlan}", ip=ip, cidr=cidr, mtu=mtu)

    def ping_test(self, dst_ip):
        logging.debug(f"ping_test: node {self.get_name()}")

        command = f'ping -c 1 {dst_ip}  2>&1 > /dev/null && echo Success'
        stdout, stderr = self.execute(command)
        if stdout.replace("\n","") == 'Success':
            return True
        else:
            return False
