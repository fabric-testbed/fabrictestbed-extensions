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

"""
Methods to work with FABRIC network interfaces.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING, Any, List, Union, Optional

from fabrictestbed.slice_editor import Flags
from fabrictestbed_extensions.utils.utils import Utils
from fim.user import Capacities, InterfaceType, Labels
from tabulate import tabulate

from fabrictestbed_extensions.fablib.constants import Constants
from fabrictestbed_extensions.fablib.template_mixin import TemplateMixin

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice
    from fabrictestbed_extensions.fablib.node import Node
    from fabrictestbed_extensions.fablib.network_service import NetworkService
    from fabrictestbed_extensions.fablib.component import Component
    from fabrictestbed_extensions.fablib.facility_port import FacilityPort
    from fabrictestbed_extensions.fablib.switch import Switch

from fabrictestbed.slice_editor import UserData
from fim.user.interface import Interface as FimInterface

log = logging.getLogger("fablib")


class Interface(TemplateMixin):
    _show_title = "Interface"

    CONFIGURED = "configured"
    MODE = "mode"
    AUTO = "auto"
    MANUAL = "manual"
    ADDR = "addr"
    CONFIG = "config"

    def __init__(
        self,
        component: Component = None,
        fim_interface: FimInterface = None,
        node: Union[Switch, FacilityPort] = None,
        model: str = None,
        parent: Interface = None,
    ):
        """
        .. note::

            Objects of this class are not created directly.

        :param component: the component to set on this interface
        :type component: Component

        :param fim_interface: the FABRIC information model interface
            to set on this fablib interface
        :type fim_interface: FimInterface

        :param node: the facility Port to which interface is assoicated with
        :type node: FacilityPort
        """
        super().__init__()
        self.fim_interface = fim_interface
        self.component = component
        self.network = None
        self.dev = None
        self.node = node
        self.model = model
        self.interfaces = {}
        self.parent = parent

        # V2 specific: cached FIM properties
        self._cached_mac: Optional[str] = None
        self._cached_vlan: Optional[str] = None
        self._cached_bandwidth: Optional[int] = None
        self._cached_site: Optional[str] = None
        self._cached_physical_os_interface: Optional[str] = None
        self._cached_switch_port: Optional[str] = None
        self._cached_flag: Optional[bool] = False
        self._cached_peer_port_name: Optional[str] = None
        self._cached_fim_type: Optional[str] = None
        self._cached_peer_account_id: Optional[str] = None
        self._cached_peer_bgp_key: Optional[str] = None
        self._cached_peer_asn: Optional[str] = None
        self._cached_peer_subnet: Optional[str] = None
        self._cached_subnet: Optional[str] = None
        self._cached_peer_port_vlan: Optional[str] = None


    def _invalidate_cache(self):
        """Invalidate all cached properties."""
        super(Interface, self)._invalidate_cache()

        self._cached_mac = None
        self._cached_vlan = None
        self._cached_bandwidth = None
        self._cached_site = None
        self._cached_physical_os_interface = None
        self._cached_switch_port = None
        self._cached_flag = False
        self._cached_peer_port_name = None
        self._cached_fim_type = None
        self._cached_peer_account_id = None
        self._cached_peer_bgp_key = None
        self._cached_peer_asn = None
        self._cached_peer_subnet = None
        self._cached_subnet = None
        self._cached_peer_port_vlan = None
        self.interfaces = {}

    def update(self, fim_interface: FimInterface = None):
        """
        Update the interface with new FIM data.

        :param fim_interface: The new FIM interface data
        :type fim_interface: FimInterface
        """
        if fim_interface:
            self.fim_interface = fim_interface
            self._invalidate_cache()
            self._fim_dirty = False

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
            ["Device", self.get_device_name()],
            ["Address", self.get_ip_addr()],
            ["Numa Node", self.get_numa_node()],
            ["Switch Port", self.get_switch_port()],
        ]

        subnet = self.get_subnet()
        if subnet:
            table.append(["Subnet", subnet])
        peer_subnet = self.get_peer_subnet()
        if peer_subnet:
            table.append(["Peer Subnet", peer_subnet])

        peer_asn = self.get_peer_asn()
        if peer_asn:
            table.append(["Peer ASN", peer_asn])

        peer_bgp = self.get_peer_bgp_key()
        if peer_bgp:
            table.append(["Peer BGP Key", peer_bgp])

        peer_account_id = self.get_peer_account_id()
        if peer_account_id:
            table.append(["Peer Account Id", peer_account_id])

        return tabulate(table)

    @staticmethod
    def get_pretty_name_dict() -> dict[str, str]:
        """
        Return a mapping used when rendering table headers.
        """
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
            "mode": "Mode",
            "ip_addr": "IP Address",
            "numa": "Numa Node",
            "switch_port": "Switch Port",
        }

    def toDict(self, skip: Optional[List[str]] = None) -> dict[str, str]:
        """
        Returns the interface attributes as a dictionary.

        Results are cached. Cache is invalidated when ``_invalidate_cache()``
        is called.

        :param skip: list of keys to exclude
        :type skip: List[str]
        :return: interface attributes as dictionary
        :rtype: dict
        """
        if skip is None:
            skip = []

        if self._cached_dict is None:
            if self.get_network():
                log.info(
                    f"Getting results from get network name thread for iface {self.get_name()} "
                )
                network_name = self.get_network().get_name()
            else:
                network_name = None

            if self.get_node():
                log.info(
                    f"Getting results from get node name thread for iface {self.get_name()} "
                )
                node_name = self.get_node().get_name()
            else:
                node_name = None

            from fabrictestbed_extensions.fablib.node import Node

            if (
                self.get_node()
                and isinstance(self.get_node(), Node)
                and str(self.get_node().get_reservation_state()) == "Active"
            ):
                mac = str(self.get_mac())
                physical_dev = str(self.get_physical_os_interface_name())
                dev = str(self.get_device_name())
                ip_addr = str(self.get_ip_addr())
                numa = str(self.get_numa_node())
            else:
                mac = ""
                physical_dev = ""
                dev = ""
                ip_addr = ""
                numa = ""

            d = {}
            d["name"] = str(self.get_name())
            d["short_name"] = str(self.get_short_name())
            d["node"] = str(node_name)
            d["network"] = str(network_name)
            d["bandwidth"] = str(self.get_bandwidth())
            d["mode"] = str(self.get_mode())
            d["vlan"] = (str(self.get_vlan()) if self.get_vlan() else "")
            d["mac"] = mac
            d["physical_dev"] = physical_dev
            d["dev"] = dev
            d["ip_addr"] = ip_addr
            d["numa"] = numa
            d["switch_port"] = str(self.get_switch_port())
            self._cached_dict = d

        if not skip:
            return dict(self._cached_dict)
        return {k: v for k, v in self._cached_dict.items() if k not in skip}

    def get_switch_port(self) -> Optional[str]:
        """
        Get the name of the port on the switch corresponding to this interface

        :return: name of the port on switch
        :rtype: String
        """
        if self._cached_switch_port is None:
            network = self.get_network()
            if network and network.get_fim():
                ifs = None
                for ifs_name in network.get_fim().interfaces.keys():
                    if self.get_name() in ifs_name:
                        ifs = network.get_fim().interfaces[ifs_name]
                        break
                if ifs and ifs.labels and ifs.labels.local_name:
                    self._cached_switch_port = ifs.labels.local_name
        return self._cached_switch_port

    def get_numa_node(self) -> Optional[str]:
        """
        Retrieve the NUMA node of the component linked to the interface.

        :return: NUMA node of the linked component.
        :rtype: str
        """
        if self.get_component() is not None:
            return self.get_component().get_numa_node()
        return None

    def set_auto_config(self):
        """
        Enable autoconfiguration for the interface.

        This method sets the `auto_config` flag to `True` for the interface
        associated with the current instance. The `auto_config` flag enables
        automatic configuration of the interface by Control Framework.

        :return: None
        """
        fim_iface = self.get_fim()
        fim_iface.flags = Flags(auto_config=True)
        self._cached_flag = True

    def unset_auto_config(self):
        """
        Disable autoconfiguration for the interface.

        This method sets the `auto_config` flag to `False` for the interface
        associated with the current instance. The `auto_config` flag disables
        automatic configuration of the interface by Control Framework.

        :return: None
        """
        fim_iface = self.get_fim()
        fim_iface.flags = Flags(auto_config=False)
        self._cached_flag = False

    def get_peer_port_name(self) -> Optional[str]:
        """
        If available provide the name of the attached port on the dataplane switch.
        Only possible once the slice has been instantiated.
        """
        if self._cached_peer_port_name is None:
            if (
                self.fim_interface
                and self.fim_interface.get_peers()
                and self.fim_interface.get_peers()[0]
            ):
                self._cached_peer_port_name = self.fim_interface.get_peers()[0].labels.local_name
        return self._cached_peer_port_name

    def get_peer_port_vlan(self) -> Optional[str]:
        """
        Returns the VLAN associated with the interface.
        For shared NICs extracts it from label_allocations.

        :return: VLAN to be used for Port Mirroring
        :rtype: String
        """
        if self._cached_peer_port_vlan is None:
            self._cached_peer_port_vlan = self.get_vlan()
            if not self._cached_peer_port_vlan:
                label_allocations = self.get_fim().get_property(pname="label_allocations")
                if label_allocations:
                    self._cached_peer_port_vlan = label_allocations.vlan

        return self._cached_peer_port_vlan

    def get_device_name(self) -> Optional[str]:
        """
        Gets a name of the device name on the node

        If the interface requires a FABRIC VLAN tag, the interface name returned
        will be the VLAN tagged interface name.

        :return: OS interface name
        :rtype: String
        """
        try:
            from fabrictestbed_extensions.fablib.switch import Switch

            if self.node and isinstance(self.node, Switch):
                match = re.search(
                    r"\d+", self.get_name()
                )  # Find digits in the string
                if match:
                    return match.group()

                return self.get_name()

            fablib_data = self.get_fablib_data()
            if "dev" in fablib_data and fablib_data.get("dev"):
                return fablib_data.get("dev")
            else:
                # log.debug(f"iface: {self}")
                os_iface = self.get_physical_os_interface_name()
                vlan = self.get_vlan()

                fablib_data["base_dev"] = os_iface

                if os_iface and vlan and not self.__is_shared_nic():
                    os_iface = f"{os_iface}.{vlan}"

                fablib_data["dev"] = os_iface

                if os_iface:
                    self.set_fablib_data(fablib_data)
            return os_iface

        except Exception as e:
            log.error(f"get_device_name: error occurred - e: {e}")

    def get_os_dev(self) -> Optional[dict[str, str]]:
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

    def config_vlan_iface(self):
        """
        Configure vlan interface

        NOTE: Not intended for API use
        """
        if self.get_vlan() is not None and not self.__is_shared_nic():
            self.get_node().add_vlan_os_interface(
                os_iface=self.get_physical_os_interface_name(),
                vlan=self.get_vlan(),
                interface=self,
            )

    def ip_addr_add(self, addr: Union[IPv4Address, IPv6Address],
                    subnet: Union[ipaddress.IPv4Network, ipaddress.IPv6Network]):
        """
        Add an IP address to the interface in the node.

        :param addr: IP address
        :type addr: IPv4Address or IPv6Address
        :param subnet: subnet
        :type subnet: IPv4Network or IPv6Network
        """
        self.get_node().ip_addr_add(addr, subnet, self)

    def ip_addr_del(self, addr: Union[IPv4Address, IPv6Address],
                    subnet: Union[ipaddress.IPv4Network, ipaddress.IPv6Network]):
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
        if self.get_network():
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

    def un_manage_interface(self):
        """
        Mark an interface unmanaged by Network Manager;
        This is needed to be run on rocky* images to avoid the
        network configuration from being overwritten by NetworkManager
        """
        if self.get_network() is None:
            return

        self.get_node().un_manage_interface(self)

    def set_vlan(self, vlan: Any = None):
        """
        Set the VLAN on the FABRIC request.

        :param vlan: vlan
        :type vlan: String or int
        """
        if vlan:
            vlan = str(vlan)

        if_labels = self.get_fim().get_property(pname="labels")
        if_labels.vlan = str(vlan)
        self.get_fim().set_properties(labels=if_labels)

        return self

    def set_bandwidth(self, bw: int):
        """
        Set the Bandwidths on the FABRIC request.

        :param bw: bw
        :type bw: int
        """
        if not bw:
            return None

        if_capacities = self.get_fim().get_property(pname="capacities")
        if_capacities.bw = int(bw)
        self.get_fim().set_properties(capacities=if_capacities)

        if (
            self.get_fim().get_peers()
            and self.get_fim().get_peers()[0]
            and self.get_fim().get_peers()[0].capacities
        ):
            existing = self.get_fim().get_peers()[0].capacities
            existing.bw = int(bw)
            self.get_fim().get_peers()[0].set_properties(capacities=existing)

        return self

    def get_reservation_id(self) -> str or None:
        """
        Gets the reservation id

        :return: reservation id
        :rtype: String
        """
        if self.get_network():
            return self.get_network().get_reservation_id()
        elif self.get_node():
            return self.get_node().get_reservation_id()
        return None

    def get_reservation_state(self) -> Optional[str]:
        """
        Gets the reservation state

        :return: reservation state
        :rtype: String
        """
        if self.get_network():
            return self.get_network().get_reservation_state()
        elif self.get_node():
            return self.get_node().get_reservation_state()
        return None

    def get_error_message(self) -> str:
        """
        Gets the error messages

        :return: error
        :rtype: String
        """
        if self.get_network():
            return self.get_network().get_error_message()
        elif self.get_node():
            return self.get_node().get_error_message()
        return None

    def get_short_name(self):
        """
        Retrieve the shortened name of the interface.

        This method strips off the extra parts of the name added by the FIM. Specifically, it removes the
        prefix formed by concatenating the node name and the component's short name
        followed by a hyphen.

        :return: Shortened name of the interface.
        :rtype: str
        """
        if self.parent or not self.get_component():
            return self.get_name()

        # Strip off the extra parts of the name added by FIM
        prefix_length = len(
            f"{self.get_node().get_name()}-{self.get_component().get_short_name()}-"
        )
        return self.get_name()[prefix_length:]

    def get_mac(self) -> str:
        """
        Gets the MAC address of the interface.

        Results are cached for performance.

        :return: the MAC address
        :rtype: str
        """
        if self._cached_mac is None:
            try:
                if self.fim_interface:
                    label_allocations = self.fim_interface.get_property(
                        pname="label_allocations"
                    )
                    if label_allocations:
                        self._cached_mac = label_allocations.mac
            except Exception:
                self._cached_mac = None
        return self._cached_mac if self._cached_mac else ""

    def get_vlan(self) -> str:
        """
        Gets the VLAN of the interface.

        Results are cached for performance.

        :return: the VLAN
        :rtype: str
        """
        if self._cached_vlan is None:
            try:
                if self.fim_interface:
                    label_allocations = self.fim_interface.get_property(
                        pname="label_allocations"
                    )
                    if label_allocations and label_allocations.vlan:
                        self._cached_vlan = str(label_allocations.vlan)
            except Exception:
                self._cached_vlan = None
        return self._cached_vlan if self._cached_vlan else ""

    def get_bandwidth(self) -> int:
        """
        Gets the bandwidth of the interface in Gbps.

        Basic NICs claim 0 bandwidth but are 100 Gbps shared by all
        Basic NICs on the host.

        Results are cached for performance.

        :return: the bandwidth in Gbps
        :rtype: int
        """
        if self._cached_bandwidth is None:
            try:
                bw = 0
                if self.fim_interface:
                    capacities = self.fim_interface.get_property(pname="capacities")
                    if capacities and capacities.bw:
                        bw = int(capacities.bw)
                    if (
                        not bw
                        and self.fim_interface.get_peers()
                        and self.fim_interface.get_peers()[0]
                        and self.fim_interface.get_peers()[0].capacities
                        and self.fim_interface.get_peers()[0].capacities.bw
                    ):
                        bw = int(self.fim_interface.get_peers()[0].capacities.bw)
                    if (
                        not bw
                        and self.get_component()
                        and self.get_component().get_model() == "NIC_Basic"
                    ):
                        bw = 100
                self._cached_bandwidth = bw
            except Exception:
                self._cached_bandwidth = 0
        return self._cached_bandwidth

    def get_site(self) -> str:
        """
        Gets the site where the interface is located.

        Results are cached for performance.

        :return: the site name
        :rtype: str
        """
        if self._cached_site is None:
            try:
                if self.get_node():
                    self._cached_site = self.get_node().get_site()
            except Exception:
                self._cached_site = None
        return self._cached_site if self._cached_site else ""

    def get_physical_os_interface_name(self) -> str:
        """
        Gets the physical OS interface name.

        Results are cached for performance.

        :return: the physical OS interface name
        :rtype: str
        """
        if self._cached_physical_os_interface is None:
            try:
                if self.fim_interface:
                    label_allocations = self.fim_interface.get_property(
                        pname="label_allocations"
                    )
                    if label_allocations and label_allocations.local_name:
                        self._cached_physical_os_interface = label_allocations.local_name
            except Exception:
                self._cached_physical_os_interface = None
        return self._cached_physical_os_interface if self._cached_physical_os_interface else ""

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
        try:
            if self.model:
                return self.model
            elif self.node:
                return self.node.get_model()
            else:
                return self.get_component().get_model()
        except Exception:
            return ""

    def get_slice(self) -> Slice:
        """
        Gets the FABLIB slice this interface's node is attached to.

        :return: the slice this interface is attached to
        :rtype: Slice
        """
        return self.get_node().get_slice()

    def get_node(self) -> Union[Node, FacilityPort]:
        """
        Gets the node this interface's component is on.

        :return: the node this interface is attached to
        :rtype: Node
        """
        if self.node:
            return self.node
        else:
            return self.get_component().get_node()

    def get_network(self) -> Optional[NetworkService]:
        """
        Gets the network this interface is on.

        :return: the network service this interface is on
        :rtype: NetworkService
        """

        if self.network is not None:
            log.debug(
                f"Interface known network. Returning known network for interface {self.get_name()}"
            )
            return self.network
        else:
            log.debug(
                f"Interface does not known network. Finding network for interface {self.get_name()}"
            )

            for net in self.get_slice().get_networks():
                if net.has_interface(self):
                    self.network = net
                    log.debug(
                        f"Interface network found. interface {self.get_name()}, network {self.network.get_name()}"
                    )
                    return self.network
            return None

    # fablib.Interface.get_ip_link()
    def get_ip_link(self):
        """
        Gets the ip link info for this interface.

        :return: ip link info
        :rtype: str
        """
        try:
            stdout, stderr = self.get_node().execute("ip -j link list", quiet=True)

            links = json.loads(stdout)

            dev = self.get_device_name()
            if dev is None:
                return links

            for link in links:
                if link["ifname"] == dev:
                    return link
            return None
        except Exception as e:
            log.warning(f"{e}")

    def get_ip_addr_show(self, dev=None):
        """
        Retrieve the IP address information for a specified network device.

        This method executes the `ip -j addr show` command on the node to get
        the IP address information in JSON format for the specified device.
        If no device is specified, it defaults to the device name associated
        with the current instance.

        :param dev: The name of the network device (optional).
        :type dev: str, optional
        :return: The JSON output of the `ip -j addr show` command.
        :rtype: str
        :raises: Logs an error message if the command execution fails.
        """
        try:
            if not dev:
                dev = self.get_device_name()

            stdout, stderr = self.get_node().execute(
                f"ip -j addr show {dev}", quiet=True
            )
            return stdout
        except Exception as e:
            log.error(
                f"Failed to get IP address show info for interface {self.get_name()}. Exception: {e}"
            )

    # fablib.Interface.get_ip_addr()
    def get_ip_addr_ssh(self, dev=None):
        """
        Gets the ip addr info for this interface.

        :return: ip addr info
        :rtype: str
        """
        try:
            stdout, stderr = self.get_node().execute("ip -j addr list", quiet=True)
            if not stdout:
                return None

            addrs = json.loads(stdout)

            dev = self.get_device_name()

            if dev is None:
                return addrs

            for addr in addrs:
                if addr["ifname"] == dev:
                    # Hack to make it backward compatible. Should return an object
                    return str(ipaddress.ip_address(addr["addr_info"][0]["local"]))

            return None
        except Exception as e:
            log.warning(f"{e}")

    # fablib.Interface.get_ip_addr()
    def get_ips(self, family=None):
        """
        Gets a list of ips assigned to this interface.

        :return: list of ips
        :rtype: list[str]
        """
        return_ips = []
        try:
            ip_addr = self.get_ip_addr()

            # print(f"{ip_addr}")

            for addr_info in ip_addr["addr_info"]:
                if family is None:
                    return_ips.append(addr_info["local"])
                else:
                    if addr_info["family"] == family:
                        return_ips.append(addr_info["local"])
        except Exception as e:
            log.warning(f"{e}")

        return return_ips

    def get_fim(self):
        """
        Gets the node's FABRIC Information Model (fim) object. This method
        is used to access data at a lower level than FABlib.

        :return: the FABRIC model node
        :rtype: fim interface
        """
        return self.fim_interface

    def set_network(self, network: NetworkService):
        """
        Set the network for the interface.

        This method assigns the interface to the specified network. If the
        interface is already part of another network, it will be removed from
        the current network before being added to the new one.

        :param network: The network service to assign the interface to.
        :type network: NetworkService
        :return: The current instance with the updated network.
        :rtype: self
        """
        current_network = self.get_network()
        if current_network:
            current_network.remove_interface(self)

        network.add_interface(self)

        return self

    def set_ip_addr(self, addr: Optional[ipaddress] = None, mode: str = None):
        """
        Set the IP address for the interface.

        This method assigns an IP address to the interface based on the provided
        address or allocation mode. If an address is provided, it will be allocated
        to the interface. If the mode is set to 'AUTO' and no address is provided,
        an IP address will be automatically allocated by the network.

        :param addr: The IP address to assign to the interface (optional).
        :type addr: ipaddress.IPv4Address or ipaddress.IPv6Address, optional
        :param mode: The mode for IP address allocation, e.g., `"auto"`, `"manual"`, or `"config"`.
        :type mode: str, optional
        :return: The current instance with the updated IP address.
        :rtype: self
        """
        fablib_data = self.get_fablib_data()
        if mode:
            fablib_data[self.MODE] = str(mode)

        mode = fablib_data[self.MODE]
        if addr:
            fablib_data[self.ADDR] = str(self.get_network().allocate_ip(addr))
        elif mode == self.AUTO:
            if self.get_network():
                fablib_data[self.ADDR] = str(self.get_network().allocate_ip())

        self.set_fablib_data(fablib_data)

        return self

    def get_ip_addr(self):
        """
        Retrieve the IP address assigned to the interface.

        This method returns the IP address assigned to the interface, either
        from the 'fablib_data' or by fetching it via SSH if not available in
        the stored data. If the MAC address is not available, it returns None.

        :return: The IP address assigned to the interface.
        :rtype: ipaddress.IPv4Address or ipaddress.IPv6Address or str or None
        """
        fablib_data = self.get_fablib_data()
        if self.ADDR in fablib_data:
            try:
                addr = ipaddress.ip_address(fablib_data[self.ADDR])
            except:
                addr = fablib_data[self.ADDR]
            return addr
        else:
            # get_ip_addr_ssh()
            if self.get_mac() is None:
                return None
            return self.get_ip_addr_ssh()

    def set_mode(self, mode: str = "config"):
        """
        Set the mode for the interface.

        This method sets the mode for the interface in the 'fablib_data'
        dictionary. The mode determines the configuration behavior of the
        interface.

        :param mode: The mode to set for the interface (default is "config"). Allowed values: `"auto"`, `"manual"`, or `"config"`..
        :type mode: str
        :return: The current instance with the updated mode.
        :rtype: self
        """
        fablib_data = self.get_fablib_data()
        fablib_data[self.MODE] = mode
        self.set_fablib_data(fablib_data)

        return self

    def get_mode(self):
        """
        Retrieve the mode of the interface.

        This method returns the current mode of the interface from the 'fablib_data'
        dictionary. If the mode is not set, it defaults to "config" and updates the
        'fablib_data' accordingly.

        :return: The mode of the interface.
        :rtype: str
        """
        fablib_data = self.get_fablib_data()
        if self.MODE not in fablib_data:
            self.set_mode(self.CONFIG)
            fablib_data = self.get_fablib_data()

        return fablib_data[self.MODE]

    def is_configured(self):
        """
        Check if the interface is configured.

        This method checks the 'fablib_data' dictionary to determine if the
        interface is marked as configured.

        :return: True if the interface is configured, False otherwise.
        :rtype: bool
        """
        fablib_data = self.get_fablib_data()
        if fablib_data:
            is_configured = fablib_data.get(self.CONFIGURED)
            if is_configured is None or not bool(is_configured):
                return False

        return True

    def config(self):
        """
        Configure the interface based on its mode and network settings. Called when a `.Node` is configured.

        This method configures the interface by setting its IP address and
        bringing it up. It checks the configuration mode and acts accordingly:
        - If the mode is 'AUTO' and no address is set, it automatically allocates an IP address.
        - If the mode is 'CONFIG' or 'AUTO', it configures the interface with the assigned IP address and subnet.
        - If the mode is 'MANUAL', it does not perform any automatic configuration.

        :return: None
        """
        self.config_vlan_iface()
        network = self.get_network()
        if not network:
            log.info(
                f"Interface {self.get_name()} not connected to a network, skipping configuration."
            )
            return

        fablib_data = self.get_fablib_data()
        addr = None
        if self.is_configured():
            addr = fablib_data.get(self.ADDR)
        else:
            fablib_data[self.CONFIGURED] = str(True)
            self.set_fablib_data(fablib_data)

        mode = fablib_data.get(self.MODE, self.MANUAL)

        if mode == self.AUTO and addr is None:
            fablib_data[self.ADDR] = str(self.get_network().allocate_ip())
            self.set_fablib_data(fablib_data)

        self.ip_link_up()

        if mode in [self.CONFIG, self.AUTO]:
            subnet = self.get_network().get_subnet()
            addr = fablib_data.get(self.ADDR)
            if addr and subnet:
                self.un_manage_interface()
                self.ip_link_up()
                self.ip_addr_add(addr=addr, subnet=ipaddress.ip_network(subnet))
        else:
            # Manual mode; do nothing.
            pass

    def add_mirror(self, port_name: str, name: str = "mirror", vlan: str = None):
        """
        Add Port Mirror Service

        :param port_name: Mirror Port Name
        :type port_name: String
        :param vlan: Mirror Port vlan
        :type vlan: String
        :param name: Name of the Port Mirror service
        :type name: String
        """
        self.get_slice().get_fim_topology().add_port_mirror_service(
            name=name,
            from_interface_name=port_name,
            from_interface_vlan=vlan,
            to_interface=self.get_fim(),
        )

    def delete(self):
        """
        Delete the interface by removing it from the corresponding network service
        """
        net = self.get_network()
        if net:
            net.remove_interface(self)
        if self.parent and self.parent.get_fim():
            self.parent.get_fim().remove_child_interface(name=self.get_name())

    def set_subnet(self, ipv4_subnet: str = None, ipv6_subnet: str = None):
        """
        Set subnet for the interface.
        Used only for interfaces connected to L3VPN service where each interface
        could be connected to multiple subnets

        :param ipv4_subnet: ipv4 subnet
        :type ipv4_subnet: str

        :param ipv6_subnet: ipv6 subnet
        :type ipv6_subnet: str

        :raises Exception in case invalid subnet string is specified.
        """
        try:
            labels = self.get_fim().labels
            if not labels:
                labels = Labels()
            if ipv4_subnet:
                ipaddress.ip_network(ipv4_subnet, strict=False)
                labels = Labels.update(labels, ipv4_subnet=ipv4_subnet)
            elif ipv6_subnet:
                ipaddress.ip_network(ipv6_subnet, strict=False)
                labels = Labels.update(labels, ipv6_subnet=ipv6_subnet)

            self.get_fim().set_property("labels", labels)
        except Exception as e:
            log.error(f"Failed to set the ip subnet e: {e}")
            raise e

    def get_subnet(self):
        """
        Get Subnet associated with the interface

        :return: ipv4/ipv6 subnet associated with the interface
        :rtype: String
        """
        if self._cached_subnet is None:
            if self.get_fim() and self.get_fim().labels:
                if self.get_fim().labels.ipv4_subnet:
                    self._cached_subnet = self.get_fim().labels.ipv4_subnet
                if self.get_fim().labels.ipv6_subnet:
                    self._cached_subnet = self.get_fim().labels.ipv6_subnet
        return self._cached_subnet

    def get_peer_subnet(self):
        """
        Get Peer Subnet associated with the interface

        :return: peer ipv4/ipv6 subnet associated with the interface
        :rtype: String
        """
        if self._cached_peer_subnet is None:
            if self.get_fim() and self.get_fim().peer_labels:
                if self.get_fim().peer_labels.ipv4_subnet:
                    self._cached_peer_subnet = self.get_fim().peer_labels.ipv4_subnet
                if self.get_fim().peer_labels.ipv6_subnet:
                    self._cached_peer_subnet = self.get_fim().peer_labels.ipv6_subnet
        return self._cached_peer_subnet

    def get_peer_asn(self):
        """
        Get Peer ASN; Set only for Peered Interface using L3Peering via AL2S

        :return: peer asn
        :rtype: String
        """
        if self._cached_peer_asn is None:
            if self.get_fim() and self.get_fim().peer_labels:
                self._cached_peer_asn = self.get_fim().peer_labels.asn
        return self._cached_peer_asn

    def get_peer_bgp_key(self):
        """
        Get Peer BGP Key; Set only for Peered Interface using L3Peering via AL2S

        :return: peer BGP Key
        :rtype: String
        """
        if self._cached_peer_bgp_key is None:
            if self.get_fim() and self.get_fim().peer_labels:
                self._cached_peer_bgp_key = self.get_fim().peer_labels.bgp_key
        return self._cached_peer_bgp_key

    def get_peer_account_id(self):
        """
        Get Peer Account Id associated with the interface

        :return: peer account id associated with the interface (Used when interface is peered to AWS via AL2S)
        :rtype: String
        """
        if self._cached_peer_account_id is None:
            if self.get_fim() and self.get_fim().peer_labels:
                self._cached_peer_account_id = self.get_fim().peer_labels.account_id
        return self._cached_peer_account_id

    def get_interfaces(
        self, refresh: bool = False, output: str = "list"
    ) -> Union[dict[str, Interface], list[Interface]]:
        """
        Gets the interfaces attached to this fablib component's FABRIC component.

        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool

        :param output: Specify how the return type is expected; Possible values: list or dict
        :type output: str

        :return: a list or dict of the interfaces on this component.
        :rtype: Union[dict[str, Interface], list[Interface]]
        """

        if self.interfaces and not refresh and not self._fim_dirty:
            if output == "dict":
                return self.interfaces
            return list(self.interfaces.values())

        self.interfaces = {}
        if self.get_fim().interface_list:
            for fim_interface in self.get_fim().interface_list:
                ch_iface = Interface(
                    component=self.get_component(),
                    fim_interface=fim_interface,
                    model=str(InterfaceType.SubInterface),
                    parent=self,
                )
                self.interfaces[ch_iface.get_name()] = ch_iface

        if output == "dict":
            return self.interfaces
        else:
            return list(self.interfaces.values())

    def add_sub_interface(self, name: str, vlan: str, bw: int = 10):
        """
        Add a sub-interface to a dedicated NIC.

        This method adds a sub-interface to a NIC (Network Interface Card) with the specified
        name, VLAN (Virtual Local Area Network) ID, and bandwidth. It supports only specific
        NIC models.

        :param name: The name of the sub-interface.
        :type name: str

        :param vlan: The VLAN ID for the sub-interface.
        :type vlan: str

        :param bw: The bandwidth allocated to the sub-interface, in Gbps. Default is 10 Gbps.
        :type bw: int

        :raises Exception: If the NIC model does not support sub-interfaces.
        """
        if self.get_model() not in [
            Constants.CMP_NIC_ConnectX_5,
            Constants.CMP_NIC_ConnectX_6,
        ]:
            raise Exception(
                f"Sub interfaces are only supported for the following NIC models: "
                f"{Constants.CMP_NIC_ConnectX_5}, {Constants.CMP_NIC_ConnectX_6}"
            )

        # Hack for finding interfaces
        name = f"{self.get_name()}-{name}"

        if self.get_fim():
            child_interface = self.get_fim().add_child_interface(
                name=name, labels=Labels(vlan=vlan)
            )
            child_if_capacities = child_interface.get_property(pname="capacities")
            if not child_if_capacities:
                child_if_capacities = Capacities()
            child_if_capacities.bw = int(bw)
            child_interface.set_properties(capacities=child_if_capacities)

            ch_iface = Interface(
                component=self.get_component(),
                fim_interface=child_interface,
                model=str(InterfaceType.SubInterface),
            )
            self.interfaces[ch_iface.get_name()] = ch_iface
            return ch_iface
        return None

    def get_type(self) -> Optional[str]:
        """
        Get Interface type

        :return: get interface type
        :rtype: String
        """
        if self._cached_fim_type is None:
            if self.get_fim():
                self._cached_fim_type = str(self.get_fim().type)
        return self._cached_fim_type

    def __is_shared_nic(self) -> bool:
        if self.get_type() == "SharedPort":
            return True
        return False
