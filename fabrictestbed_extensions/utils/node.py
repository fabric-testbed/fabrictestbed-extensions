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
from .abc_utils import AbcUtils


class NodeUtils(AbcUtils):
    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

    @staticmethod
    def validIPAddress(IP: str) -> str:
        try:
            return "IPv4" if type(ip_address(IP)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    @staticmethod
    def execute_script(node_username, node, script):
        import paramiko

        management_ip = str(node.get_property(pname="management_ip"))
        print("Node {0} IP {1}".format(node.name, management_ip))

        key = paramiko.RSAKey.from_private_key_file(AbcUtils.node_ssh_key_priv_file)

        bastion = paramiko.SSHClient()
        bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        bastion.connect(
            AbcUtils.bastion_public_addr,
            username=AbcUtils.bastion_username,
            key_filename=AbcUtils.bastion_key_filename,
        )

        bastion_transport = bastion.get_transport()
        if self.validIPAddress(management_ip) == "IPv4":
            src_addr = (self.bastion_private_ipv4_addr, 22)
        elif self.validIPAddress(management_ip) == "IPv6":
            src_addr = (self.bastion_private_ipv6_addr, 22)
        else:
            print("Management IP Invalid: {}".format(management_ip))
            return

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
            'echo "' + script + '" > script.sh; chmod +x script.sh; sudo ./script.sh'
        )
        print("")
        print(str(stdout.read(), "utf-8").replace("\\n", "\n"))

        client.close()
