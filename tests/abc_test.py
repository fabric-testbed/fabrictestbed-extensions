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

from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from ipaddress import ip_address, IPv4Address


class AbcTest(ABC):
    def __init__(self):
        self.slice_manager = SliceManager()
        self.advertised_topology = None
        self.slice = None
        self.slices = []
        self.topology = None

        self.bastion_username = os.environ["FABRIC_BASTION_USERNAME"]
        self.bastion_keyfile = ""

        self.bastion_public_addr = "bastion-1.fabric-testbed.net"
        self.bastion_private_ipv4_addr = "192.168.11.226"
        self.bastion_private_ipv6_addr = "2600:2701:5000:a902::c"

        # self.bastion_key_filename = '/Users/pruth/FABRIC/TESTING/pruth_fabric_rsa'
        self.bastion_key_filename = os.environ["HOME"] + "/.ssh/pruth_fabric_rsa"
        self.bastion_key_filename = os.environ["FABRIC_BASTION_KEY_LOCATION"]

        self.node_ssh_key_priv_file = os.environ["SLICE_PRIVATE_KEY_FILE"]
        self.node_ssh_key_pub_file = os.environ["SLICE_PUBLIC_KEY_FILE"]

        self.node_ssh_key = None
        with open(self.node_ssh_key_pub_file, "r") as fd:
            self.node_ssh_key = fd.read().strip()

        self.pull_advertised_topology()

    def pull_advertised_topology(self):
        return_status, self.advertised_topology = self.slice_manager.resources()
        if return_status != Status.OK:
            print(
                "Failed to get advertised_topology: {}".format(self.advertised_topology)
            )

    def get_slice(self, slice_name=None, slice_id=None, slice_manager=None):
        if not slice_manager:
            slice_manager = AbcUtils.create_slice_manager()

        return_status, slices = slice_manager.slices(
            excludes=[SliceState.Dead, SliceState.Closing]
        )
        if return_status != Status.OK:
            raise Exception("Failed to get slices: {}".format(slices))
        try:
            if slice_id:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
            elif slice_name:
                slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
            else:
                raise Exception(
                    "Slice not found. Slice name or id requried. name: {}, slice_id: {}".format(
                        str(slice_name), str(slice_id)
                    )
                )
        except:
            raise Exception(
                "Slice not found name: {}, slice_id: {}".format(
                    str(slice_name), str(slice_id)
                )
            )

        return slice

    def wait_for_slice(self, slice, timeout=360, interval=10, progress=False):
        self.slice = slice
        timeout_start = time.time()

        if progress:
            print("Waiting for slice {} .".format(self.slice.slice_name), end="")
        while time.time() < timeout_start + timeout:
            return_status, slices = self.slice_manager.slices(
                excludes=[SliceState.Dead, SliceState.Closing]
            )

            if return_status == Status.OK:
                slice = list(
                    filter(lambda x: x.slice_name == self.slice.slice_name, slices)
                )[0]
                if slice.slice_state == "StableOK":
                    if progress:
                        print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if (
                    slice.slice_state == "Closing"
                    or slice.slice_state == "Dead"
                    or slice.slice_state == "StableError"
                ):
                    if progress:
                        print(" Slice state: {}".format(slice.slice_state))
                    return slice
            else:
                print(f"Failure: {slices}")

            if progress:
                print(".", end="")
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            if progress:
                print(
                    " Timeout exceeded ({} sec). Slice: {} ({})".format(
                        timeout, slice.slice_name, slice.slice_state
                    )
                )
            return slice

    @staticmethod
    def validIPAddress(IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def run_ssh_test(self, slice):
        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "run_ssh_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            # print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            # print("Node:")
            print(
                " Test: ssh | "
                + str(slice.slice_name)
                + " | "
                + str(node_name)
                + " | ",
                end="",
            )
            try:
                # print("   Name              : {}".format(node_name))
                # print("   Cores             : {}".format(node.get_property(pname='capacity_allocations').core))
                # print("   RAM               : {}".format(node.get_property(pname='capacity_allocations').ram))
                # print("   Disk              : {}".format(node.get_property(pname='capacity_allocations').disk))
                # print("   Image             : {}".format(node.image_ref))
                # print("   Image Type        : {}".format(node.image_type))
                # print("   Host              : {}".format(node.get_property(pname='label_allocations').instance_parent))
                # print("   Site              : {}".format(node.site))
                # print("   Management IP     : {}".format(node.management_ip))
                # print("   Reservation ID    : {}".format(node.get_property(pname='reservation_info').reservation_id))
                # print("   Reservation State : {}".format(node.get_property(pname='reservation_info').reservation_state))
                # print("   Components        : {}".format(node.components))
                # print("   Interfaces        : {}".format(node.interfaces))
                # print()

                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                expected_stdout = "Hello, FABRIC from node " + hostname
                # print("expected_stdout: XX{}XX".format(expected_stdout.replace('\n','')))

                # print("------------------------- Test Output ---------------------------")
                script = (
                    "#!/bin/bash  \n" "echo Hello, FABRIC from node `hostname -s`   \n"
                )
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", "")) + " | ", end="")
                # print("-----------------------------------------------------------------")
                # stdout_str = str(stdout.read(),'utf-8').replace('\\n','\n')
                if expected_stdout in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    # print('Fail: --{}--  --{}--'.format(expected_stdout,stdout_str))
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def open_ssh_client_direct(
        self, node_username, node, timeout=10, interval=10, progress=True
    ):
        import paramiko

        timeout_start = time.time()

        client = None
        if progress:
            print("Waiting for ssh client connection {} .".format(node.name), end="")
        while time.time() < timeout_start + timeout:
            try:
                management_ip = str(node.get_property(pname="management_ip"))
                # print("Node {0} IP {1}".format(node.name, management_ip))

                key = paramiko.RSAKey.from_private_key_file(self.node_ssh_key_priv_file)

                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(management_ip, username=node_username, pkey=key)

                break
            except Exception as e:
                # print (str(e))
                # return str(e)
                pass

            if progress:
                print(".", end="")
            time.sleep(interval)

        return client

    def open_ssh_client(self, node_username, node):
        import paramiko

        try:
            management_ip = str(node.get_property(pname="management_ip"))
            # print("Node {0} IP {1}".format(node.name, management_ip))

            key = paramiko.RSAKey.from_private_key_file(self.node_ssh_key_priv_file)

            bastion = paramiko.SSHClient()
            bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            bastion.connect(
                self.bastion_public_addr,
                username=self.bastion_username,
                key_filename=self.bastion_key_filename,
            )

            bastion_transport = bastion.get_transport()
            if self.validIPAddress(management_ip) == "IPv4":
                src_addr = (self.bastion_private_ipv4_addr, 22)
            elif self.validIPAddress(management_ip) == "IPv6":
                src_addr = (self.bastion_private_ipv6_addr, 22)
            else:
                return "Management IP Invalid: {}".format(management_ip)

            dest_addr = (management_ip, 22)
            bastion_channel = bastion_transport.open_channel(
                "direct-tcpip", dest_addr, src_addr
            )

            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                management_ip, username=node_username, pkey=key, sock=bastion_channel
            )

        except Exception as e:
            return str(e)

        return client

    def close_ssh_client(self, ssh_client):
        import paramiko

        ssh_client.close()

    def execute_script(self, node_username, node, script):
        import paramiko

        try:
            management_ip = str(node.get_property(pname="management_ip"))
            # print("Node {0} IP {1}".format(node.name, management_ip))

            key = paramiko.RSAKey.from_private_key_file(self.node_ssh_key_priv_file)

            bastion = paramiko.SSHClient()
            bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            bastion.connect(
                self.bastion_public_addr,
                username=self.bastion_username,
                key_filename=self.bastion_key_filename,
            )

            bastion_transport = bastion.get_transport()
            if self.validIPAddress(management_ip) == "IPv4":
                src_addr = (self.bastion_private_ipv4_addr, 22)
            elif self.validIPAddress(management_ip) == "IPv6":
                src_addr = (self.bastion_private_ipv6_addr, 22)
            else:
                return "Management IP Invalid: {}".format(management_ip)

            dest_addr = (management_ip, 22)
            bastion_channel = bastion_transport.open_channel(
                "direct-tcpip", dest_addr, src_addr
            )

            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                management_ip, username=node_username, pkey=key, sock=bastion_channel
            )

            stdin, stdout, stderr = client.exec_command(
                'echo "'
                + script
                + '" > script.sh; chmod +x script.sh; sudo ./script.sh'
            )
            stdout_str = str(stdout.read(), "utf-8").replace("\\n", "\n")
            # print ('')
            # print (str(stdout.read(),'utf-8').replace('\\n','\n'))
            # print (stdout_str)

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
