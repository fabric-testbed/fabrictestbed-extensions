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
# furnished to do so, subject to the following nditions:
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

import ipaddress

from fabrictestbed.slice_editor import Flags
from tabulate import tabulate
from ipaddress import IPv4Address
import json

import logging

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabrictestbed_extensions.fablib.node import Node
    from fabrictestbed_extensions.fablib.network_service import NetworkService
    from fabrictestbed_extensions.fablib.component import Component

from fabrictestbed.slice_editor import UserData
from fim.user.interface import Interface as FimInterface


class Interface:
    def __init__(self, component: Component = None, fim_interface: FimInterface = None):
        """
        Constructor. Sets keyword arguments as instance fields.

        :param component: the component to set on this interface
        :type component: Component
        :param fim_interface: the FABRIC information model interface to set on this fablib interface
        :type fim_interface: FimInterface
        """
        super().__init__()
        self.fim_interface = fim_interface
        self.component = component
        self.network = None
        self.dev = None

    def get_fablib_manager(self):
        return self.get_slice().get_fablib_manager()

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the interface.

        Intended for printing interface information.

        :return: Tabulated string of interface information
        :rtype: String
        """
        if self.get_network():
            network_name = self.get_network().get_name()
        else:
            network_name = None

        table = [
            ["Name", self.get_name()],
            ["Network", network_name],
            ["Bandwidth", self.get_bandwidth()],
            ["Mode", self.get_mode()],
            ["VLAN", self.get_vlan()],
            ["MAC", self.get_mac()],
            ["Physical Device", self.get_physical_os_interface_name()],
            ["Device", self.get_os_interface()],
            ["Address", self.get_ip_addr()],
        ]

        return tabulate(table)

    def toJson(self):
        """
        Returns the interface attributes as a json string

        :return: slice attributes as json string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    @staticmethod
    def get_pretty_name_dict():
        return {
            "name": "Name",
            "short_name": "Short Name",
            "node": "Node",
            "network": "Network",
            "bandwidth": "Bandwidth",
            "vlan": "VLAN",
            "mac": "MAC",
            "physical_dev": "Physical Device",
            "dev": "Device",
            "username": "Username",
            "management_ip": "Management IP",
            "state": "State",
            "error": "Error",
            "ssh_command": "SSH Command",
            "public_ssh_key_file": "Public SSH Key File",
            "private_ssh_key_file": "Private SSH Key File",
            "mode": "Mode",
            "ip_addr": "IP Address",
        }

    def toDict(self, skip=[]):
        """
        Returns the interface attributes as a dictionary

        :return: slice attributes as dictionary
        :rtype: dict
        """
        if self.get_network():
            logging.info(
                f"Getting results from get network name thread for iface {self.get_name()} "
            )
            network_name = self.get_network().get_name()
        else:
            network_name = None

        if self.get_node():
            logging.info(
                f"Getting results from get node name thread for iface {self.get_name()} "
            )
            node_name = self.get_node().get_name()
        else:
            node_name = None

        if self.get_node() and str(self.get_node().get_reservation_state()) == "Active":
            mac = str(self.get_mac())
            physical_dev = str(self.get_physical_os_interface_name())
            dev = str(self.get_os_interface())
            ip_addr = str(self.get_ip_addr())
        else:
            mac = ""
            physical_dev = ""
            dev = ""
            ip_addr = ""

        return {
            "name": str(self.get_name()),
            "short_name": str(self.get_short_name()),
            "node": str(node_name),
            "network": str(network_name),
            "bandwidth": str(self.get_bandwidth()),
            "mode": str(self.get_mode()),
            "vlan": str(self.get_vlan())
            if self.get_vlan()
            else "",  # str(self.get_vlan()),
            "mac": mac,
            "physical_dev": physical_dev,
            "dev": dev,
            "ip_addr": ip_addr,
        }

    def generate_template_context(self):
        context = self.toDict()
        return context

    def get_template_context(self):
        return self.get_slice().get_template_context(self)

    def render_template(self, input_string):
        environment = jinja2.Environment()
        # environment.json_encoder = json.JSONEncoder(ensure_ascii=False)

        template = environment.from_string(input_string)
        output_string = template.render(self.get_template_context())

        return output_string

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Show a table containing the current interface attributes.

        There are several output options: "text", "pandas", and "json" that determine the format of the
        output that is returned and (optionally) displayed/printed.

        output:  'text': string formatted with tabular
                  'pandas': pandas dataframe
                  'json': string in json format

        fields: json output will include all available fields.

        Example: fields=['Name','MAC']

        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param colors: True to specify state colors for pandas output
        :type colors: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """

        data = self.toDict()

        # fields = ["Name", "Node", "Network", "Bandwidth", "VLAN",
        #        "MAC", "Device"
        #         ]

        if pretty_names:
            pretty_names_dict = self.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        table = self.get_fablib_manager().show_table(
            data,
            fields=fields,
            title="Interface",
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

        return table

    def set_auto_config(self):
        fim_iface = self.get_fim_interface()
        fim_iface.flags = Flags(auto_config=True)
        # fim_iface.labels = Labels.update(fim_iface.labels, ipv4.... )

        # labels = Labels()
        # labels.instance_parent = host_name
        # self.get_fim_node().set_properties(labels=labels)

        # if_labels = Labels.update(if_labels, ipv4=str(next(ips)), ipv4_subnet=str(network))
        # if_labels = Labels.update(if_labels, vlan="200", ipv4=str(next(ips)))
        # fim_iface.set_properties(labels=if_labels)

    def unset_auto_config(self):
        fim_iface = self.get_fim_interface()
        fim_iface.flags = Flags(auto_config=False)

    def get_device_name(self) -> str:
        """
        Gets a name of the device name on the node

        If the interface requires a FABRIC VLAN tag, the interface name returned
        will be the VLAN tagged interface name.

        :return: OS interface name
        :rtype: String
        """
        try:
            fablib_data = self.get_fablib_data()
            if "dev" in fablib_data:
                return fablib_data["dev"]
            else:
                # logging.debug(f"iface: {self}")
                os_iface = self.get_physical_os_interface_name()
                vlan = self.get_vlan()

                fablib_data["base_dev"] = os_iface
                if vlan is not None:
                    os_iface = f"{os_iface}.{vlan}"

                fablib_data["dev"] = os_iface

                self.set_fablib_data(fablib_data)

        except:
            os_iface = None

        return os_iface

    def get_os_interface(self) -> str:
        """
        Deprecated: see interface.get_device_name()

        Gets a name of the interface the operating system uses for this
        FABLib interface.

        If the interface requires a FABRIC VLAN tag, the interface name retruned
        will be the VLAN tagged.

        :return: OS interface name
        :rtype: String
        """
        try:
            # logging.debug(f"iface: {self}")
            os_iface = self.get_physical_os_interface_name()
            vlan = self.get_vlan()

            if vlan is not None:
                os_iface = f"{os_iface}.{vlan}"
        except:
            os_iface = None

        return os_iface

    def get_mac(self) -> str:
        """
        Gets the MAC address of the interface.

        :return: MAC address
        :rtype: String
        """
        try:
            # os_iface = self.get_physical_os_interface()
            # mac = os_iface['mac']
            mac = self.get_fim_interface().get_property(pname="label_allocations").mac
        except:
            mac = None

        return mac

    def get_os_dev(self):
        """
        Gets json output of 'ip addr list' for the interface.

        :return: device description
        :rtype: Dict
        """

        if not self.dev:
            ip_addr_list_json = self.get_node().ip_addr_list(output="json")

            mac = self.get_mac()
            for dev in ip_addr_list_json:
                if str(dev["address"].upper()) == str(mac.upper()):
                    self.dev = dev
                    return dev
        else:
            return self.dev

        return None

    def get_physical_os_interface(self):
        """
        Not intended for API use
        """

        if self.get_network() is None:
            return None

        network_name = self.get_network().get_name()
        node_name = self.get_node().get_name()

        try:
            return self.get_slice().get_interface_map()[network_name][node_name]
        except:
            return None

    def get_physical_os_interface_name(self) -> str:
        """
        Gets a name of the physical interface the operating system uses for this
        FABLib interface.

        If the interface requires a FABRIC VLAN tag, the base interface name
        will be returned (i.e. not the VLAN tagged interface)

        :return: physical OS interface name
        :rtype: String
        """
        try:
            return self.get_os_dev()["ifname"]
        except:
            return None

    def config_vlan_iface(self):
        """
        Not intended for API use
        """
        if self.get_vlan() is not None:
            self.get_node().add_vlan_os_interface(
                os_iface=self.get_physical_os_interface_name(),
                vlan=self.get_vlan(),
                interface=self,
            )

    def set_ip(self, ip=None, cidr=None, mtu=None):
        """
        Depricated
        """
        if cidr:
            cidr = str(cidr)
        if mtu:
            mtu = str(mtu)

        self.get_node().set_ip_os_interface(
            os_iface=self.get_physical_os_interface_name(),
            vlan=self.get_vlan(),
            ip=ip,
            cidr=cidr,
            mtu=mtu,
        )

    def ip_addr_add(self, addr, subnet):
        """
        Add an IP address to the interface in the node.

        :param addr: IP address
        :type addr: IPv4Address or IPv6Address
        :param subnet: subnet
        :type subnet: IPv4Network or IPv4Network
        """
        self.get_node().ip_addr_add(addr, subnet, self)

    def ip_addr_del(self, addr, subnet):
        """
        Delete an IP address to the interface in the node.

        :param addr: IP address
        :type addr: IPv4Address or IPv6Address
        :param subnet: subnet
        :type subnet: IPv4Network or IPv4Network
        """
        self.get_node().ip_addr_del(addr, subnet, self)

    def ip_link_up(self):
        """
        Bring up the link on the interface.

        """
        if self.get_network() == None:
            return

        self.get_node().ip_link_up(None, self)

    def ip_link_down(self):
        """
        Bring down the link on the interface.

        """
        self.get_node().ip_link_down(None, self)

    def ip_link_toggle(self):
        """
        Toggle the dev down then up.

        """
        self.get_node().ip_link_down(None, self)
        self.get_node().ip_link_up(None, self)

    def set_vlan(self, vlan: Any = None):
        """
        Set the VLAN on the FABRIC request.

        :param addr: vlan
        :type addr: String or int
        """
        if vlan:
            vlan = str(vlan)

        if_labels = self.get_fim_interface().get_property(pname="labels")
        if_labels.vlan = str(vlan)
        self.get_fim_interface().set_properties(labels=if_labels)

        return self

    def get_fim_interface(self) -> FimInterface:
        """
        Not recommended for most users.

        Gets the node's FABRIC Information Model (fim) object. This method
        is used to access data at a lower level than FABlib.

        :return: the FABRIC model node
        :rtype: fim interface
        """
        return self.fim_interface

    def get_bandwidth(self) -> str:
        """
        Gets the bandwidth of an interface. Basic NICs claim 0 bandwidth but
        are 100 Gbps shared by all Basic NICs on the host.

        :return: bandwith
        :rtype: String
        """
        if self.get_component().get_model() == "NIC_Basic":
            return 100
        else:
            return self.get_fim_interface().capacities.bw

    def get_vlan(self) -> str:
        """
        Gets the FABRIC VLAN of an interface.

        :return: VLAN
        :rtype: String
        """
        try:
            vlan = self.get_fim_interface().get_property(pname="labels").vlan
        except:
            vlan = None
        return vlan

    def get_reservation_id(self) -> str or None:
        try:
            # TODO THIS DOESNT WORK.
            # print(f"{self.get_fim_interface()}")
            return (
                self.get_fim_interface()
                .get_property(pname="reservation_info")
                .reservation_id
            )
        except:
            return None

    def get_reservation_state(self) -> str or None:
        """
        Gets the reservation state

        :return: VLAN
        :rtype: String
        """
        try:
            return (
                self.get_fim_interface()
                .get_property(pname="reservation_info")
                .reservation_state
            )
        except:
            return None

    def get_error_message(self) -> str:
        """
        Gets the error messages

        :return: error
        :rtype: String
        """
        try:
            return (
                self.get_fim_interface()
                .get_property(pname="reservation_info")
                .error_message
            )
        except:
            return ""

    def get_short_name(self):
        # strip of the extra parts of the name added by fim
        return self.get_name()[
            len(
                f"{self.get_node().get_name()}-{self.get_component().get_short_name()}-"
            ) :
        ]

    def get_name(self) -> str:
        """
        Gets the name of this interface.

        :return: the name of this interface
        :rtype: String
        """
        return self.get_fim_interface().name

    def get_component(self) -> Component:
        """
        Gets the component attached to this interface.

        :return: the component on this interface
        :rtype: Component
        """
        return self.component

    def get_model(self) -> str:
        """
        Gets the component model type on this interface's component.

        :return: the model of this interface's component
        :rtype: str
        """
        return self.get_component().get_model()

    def get_site(self) -> str:
        """
        Gets the site this interface's component is on.

        :return: the site this interface is on
        :rtype: str
        """
        return self.get_component().get_site()

    def get_slice(self) -> Slice:
        """
        Gets the FABLIB slice this interface's node is attached to.

        :return: the slice this interface is attached to
        :rtype: Slice
        """
        return self.get_node().get_slice()

    def get_node(self) -> Node:
        """
        Gets the node this interface's component is on.

        :return: the node this interface is attached to
        :rtype: Node
        """
        return self.get_component().get_node()

    def get_network(self) -> NetworkService:
        """
        Gets the network this interface is on.

        :return: the network service this interface is on
        :rtype: NetworkService
        """

        if self.network is not None:
            logging.debug(
                f"Interface known network. Returning known network for interface {self.get_name()}"
            )
            return self.network
        else:
            logging.debug(
                f"Interface does not known network. Finding network for interface {self.get_name()}"
            )

            for net in self.get_slice().get_networks():
                if net.has_interface(self):
                    self.network = net
                    logging.debug(
                        f"Interface network found. interface {self.get_name()}, network {self.network.get_name()}"
                    )
                    return self.network

        return None

    # fablib.Interface.get_ip_link()
    def get_ip_link(self):
        """
        Gets the ip link info for this interface.

        :return ip link info
        :rtype: str
        """
        try:
            stdout, stderr = self.get_node().execute("ip -j link list", quiet=True)

            links = json.loads(stdout)

            dev = self.get_os_interface()
            if dev == None:
                return links

            for link in links:
                if link["ifname"] == dev:
                    return link
            return None
        except Exception as e:
            print(f"Exception: {e}")

    def get_ip_addr_show(self, dev=None):
        try:
            if not dev:
                dev = self.get_os_interface()

            stdout, stderr = self.get_node().execute(
                f"ip -j addr show {dev}", quiet=True
            )
        except Exception as e:
            (f"Exception: {e}")
            logging.error(
                f"Failed to get ip addr show info for interface {self.get_name()}"
            )

        return stdout

    # fablib.Interface.get_ip_addr()
    def get_ip_addr_ssh(self, dev=None):
        """
        Gets the ip addr info for this interface.

        :return ip addr info
        :rtype: str
        """
        try:
            stdout, stderr = self.get_node().execute("ip -j addr list", quiet=True)

            addrs = json.loads(stdout)

            dev = self.get_os_interface()
            # print(f"dev: {dev}")

            if dev == None:
                return addrs

            for addr in addrs:
                if addr["ifname"] == dev:
                    # Hack to make it backward compatible. Should return an object
                    return str(ipaddress.ip_address(addr["addr_info"][0]["local"]))

            return None
        except Exception as e:
            print(f"Exception: {e}")

    # fablib.Interface.get_ip_addr()
    def get_ips(self, family=None):
        """
        Gets a list of ips assigned to this interface.

        :return list of ips
        :rtype: list[str]
        """
        return_ips = []
        try:
            dev = self.get_os_interface()

            ip_addr = self.get_ip_addr()

            # print(f"{ip_addr}")

            for addr_info in ip_addr["addr_info"]:
                if family == None:
                    return_ips.append(addr_info["local"])
                else:
                    if addr_info["family"] == family:
                        return_ips.append(addr_info["local"])
        except Exception as e:
            print(f"Exception: {e}")

        return return_ips

    def get_fim(self):
        return self.get_fim_interface()

    def set_user_data(self, user_data: dict):
        self.get_fim().set_property(
            pname="user_data", pval=UserData(json.dumps(user_data))
        )

    def get_user_data(self):
        try:
            return json.loads(str(self.get_fim().get_property(pname="user_data")))
        except Exception as e:
            return {}

    def get_fablib_data(self):
        try:
            return self.get_user_data()["fablib_data"]
        except:
            return {}

    def set_fablib_data(self, fablib_data: dict):
        user_data = self.get_user_data()
        user_data["fablib_data"] = fablib_data
        self.set_user_data(user_data)

    def set_network(self, network: NetworkService):
        current_network = self.get_network()
        if current_network:
            current_network.remove_interface(self)

        network.add_interface(self)

        return self

    def set_ip_addr(self, addr: ipaddress = None, mode: str = None):
        fablib_data = self.get_fablib_data()
        if mode:
            fablib_data["mode"] = str(mode)

        mode = fablib_data["mode"]
        if addr:
            fablib_data["addr"] = str(self.get_network().allocate_ip(addr))
        elif mode == "auto":
            if self.get_network():
                fablib_data["addr"] = str(self.get_network().allocate_ip())
        self.set_fablib_data(fablib_data)

        return self

    def get_ip_addr(self):
        fablib_data = self.get_fablib_data()
        if "addr" in fablib_data:
            try:
                addr = ipaddress.ip_address(fablib_data["addr"])
            except:
                addr = fablib_data["addr"]
            return addr
        else:
            # get_ip_addr_ssh()
            return self.get_ip_addr_ssh()

    def set_mode(self, mode: str = "config"):
        fablib_data = self.get_fablib_data()
        fablib_data["mode"] = mode
        self.set_fablib_data(fablib_data)

        return self

    def get_mode(self):
        fablib_data = self.get_fablib_data()
        if "mode" not in fablib_data:
            self.set_mode("config")
            fablib_data = self.get_fablib_data()

        return fablib_data["mode"]

    def config(self):
        network = self.get_network()
        if not network:
            logging.info(
                f"interface {self.get_name()} not connected to network, skipping config."
            )
            return

        fablib_data = self.get_fablib_data()
        if "configured" in fablib_data and bool(fablib_data["configured"]):
            logging.debug(
                f"interface {self.get_name()} already configured, skipping config."
            )
            return
        else:
            logging.debug(f"interface {self.get_name()} not configured, configuring.")

        fablib_data["configured"] = str(True)
        self.set_fablib_data(fablib_data)

        if "mode" in fablib_data:
            mode = fablib_data["mode"]
        else:
            mode = "manual"

        if mode == "auto":
            fablib_data["addr"] = str(self.get_network().allocate_ip())
            addr = fablib_data["addr"]

            # print(f"auto allocated addr: {addr}")

            self.set_fablib_data(fablib_data)

        if mode == "config" or mode == "auto":
            subnet = self.get_network().get_subnet()
            if "addr" in fablib_data:
                addr = fablib_data["addr"]
                if addr and subnet:
                    self.ip_addr_add(addr=addr, subnet=ipaddress.ip_network(subnet))
        else:
            # manual mode... do nothing
            pass

    def add_mirror(self, port_name: str, name: str = "mirror"):
        self.get_slice().get_fim_topology().add_port_mirror_service(
            name=name,
            from_interface_name=port_name,
            to_interface=self.get_fim_interface(),
        )

    def delete(self):
        net = self.get_network()

        net.remove_interface(self)
