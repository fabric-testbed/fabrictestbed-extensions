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

"""Converts FABlib Slice objects into Cytoscape-compatible graph data.

Design: Nodes and networks are shown as graph elements. Components are NOT
rendered as child nodes (they cluttered the layout); instead, component info
is summarized in the VM node label and shown in full on the detail panel.
"""

from collections import Counter
from typing import Any

from . import styles


class GraphBuilder:
    """Builds cytoscape graph data from FABlib Slice objects.

    Produces {"nodes": [...], "edges": [...]} for ipycytoscape.
    Also builds element_map mapping cytoscape IDs to FABlib objects.
    """

    def __init__(self):
        self._nodes: list[dict] = []
        self._edges: list[dict] = []
        self.element_map: dict[str, Any] = {}

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self.element_map.clear()

    def add_slice(self, slice_obj) -> None:
        """Add all elements from a FABlib Slice to the graph."""
        slice_id = slice_obj.get_slice_id() or slice_obj.get_name()
        slice_state = self._get_slice_state(slice_obj)

        slice_cy_id = f"slice:{slice_id}"
        self._add_node(
            cy_id=slice_cy_id,
            label=slice_obj.get_name(),
            classes="slice",
            data={
                "element_type": "slice",
                "state": slice_state,
                "state_color": styles.get_state_color(slice_state),
            },
        )
        self.element_map[slice_cy_id] = slice_obj

        # Maps interface name -> cytoscape source node ID (the VM node)
        iface_source_map: dict[str, str] = {}

        for node in slice_obj.get_nodes():
            self._add_vm_node(node, slice_id, slice_cy_id, iface_source_map)

        try:
            switches = slice_obj.get_switches() if hasattr(slice_obj, 'get_switches') else []
            for switch in switches:
                self._add_switch_node(switch, slice_id, slice_cy_id, iface_source_map)
        except Exception:
            pass

        try:
            for fp in slice_obj.get_facilities():
                self._add_facility_port_node(fp, slice_id, slice_cy_id, iface_source_map)
        except Exception:
            pass

        for net in slice_obj.get_network_services():
            self._add_network_node(net, slice_id, iface_source_map)

    def build(self) -> dict:
        return {
            "nodes": self._nodes.copy(),
            "edges": self._edges.copy(),
        }

    # ----------------------------------------------------------------
    # Node builders
    # ----------------------------------------------------------------

    def _add_vm_node(self, node, slice_id: str, slice_cy_id: str,
                     iface_source_map: dict) -> None:
        """Add a VM node to the graph. Components are summarized in the label."""
        node_name = node.get_name()
        node_cy_id = f"node:{slice_id}:{node_name}"
        node_state = self._get_node_state(node)

        site = str(self._safe_get(node, "get_site", "?"))
        cores = self._safe_get(node, "get_cores", "?")
        ram = self._safe_get(node, "get_ram", "?")
        disk = self._safe_get(node, "get_disk", "?")

        # Build component summary (e.g. "NIC GPU GPU NVM")
        cmp_summary = self._build_component_summary(node)

        # Multi-line label for the card
        lines = [node_name, f"@ {site}"]
        res_line = f"{cores}c / {ram}G / {disk}G"
        lines.append(res_line)
        if cmp_summary:
            lines.append(cmp_summary)
        label = "\n".join(lines)

        self._add_node(
            cy_id=node_cy_id,
            label=label,
            classes="vm",
            parent=slice_cy_id,
            data={
                "element_type": "node",
                "node_name": node_name,
                "site": site,
                "cores": cores,
                "ram": ram,
                "disk": disk,
                "state": node_state,
                "state_color": styles.get_state_color(node_state),
                "state_bg": styles.get_state_bg_color(node_state),
            },
        )
        self.element_map[node_cy_id] = node

        # Store component objects in element_map for detail panel clicks
        for component in node.get_components():
            cmp_name = component.get_name()
            cmp_cy_id = f"cmp:{slice_id}:{node_name}:{cmp_name}"
            self.element_map[cmp_cy_id] = component

            # Map component interfaces to the VM node for edge creation
            for iface in component.get_interfaces():
                iface_name = iface.get_name()
                iface_source_map[iface_name] = node_cy_id
                self.element_map[f"iface:{slice_id}:{iface_name}"] = iface

        # Map node-level interfaces (OpenStack NICs without explicit components)
        for iface in node.get_interfaces():
            iface_name = iface.get_name()
            if iface_name not in iface_source_map:
                iface_source_map[iface_name] = node_cy_id
                self.element_map[f"iface:{slice_id}:{iface_name}"] = iface

    def _add_switch_node(self, switch, slice_id: str, slice_cy_id: str,
                         iface_source_map: dict) -> None:
        name = switch.get_name()
        cy_id = f"switch:{slice_id}:{name}"
        state = self._get_node_state(switch)
        site = str(self._safe_get(switch, "get_site", "?"))

        self._add_node(
            cy_id=cy_id,
            label=f"{name}\nP4 @ {site}",
            classes="switch",
            parent=slice_cy_id,
            data={
                "element_type": "switch",
                "site": site,
                "state": state,
                "state_color": styles.get_state_color(state),
                "state_bg": styles.get_state_bg_color(state),
            },
        )
        self.element_map[cy_id] = switch

        for iface in switch.get_interfaces():
            iface_name = iface.get_name()
            iface_source_map[iface_name] = cy_id
            self.element_map[f"iface:{slice_id}:{iface_name}"] = iface

    def _add_facility_port_node(self, fp, slice_id: str, slice_cy_id: str,
                                iface_source_map: dict) -> None:
        name = fp.get_name()
        cy_id = f"fp:{slice_id}:{name}"
        site = str(self._safe_get(fp, "get_site", "?"))

        self._add_node(
            cy_id=cy_id,
            label=f"{name}\n@ {site}",
            classes="facility-port",
            parent=slice_cy_id,
            data={
                "element_type": "facility_port",
                "site": site,
            },
        )
        self.element_map[cy_id] = fp

        for iface in fp.get_interfaces():
            iface_name = iface.get_name()
            iface_source_map[iface_name] = cy_id
            self.element_map[f"iface:{slice_id}:{iface_name}"] = iface

    def _add_network_node(self, net, slice_id: str,
                          iface_source_map: dict) -> None:
        net_name = net.get_name()
        net_type = self._safe_get(net, "get_type", "unknown")
        net_cy_id = f"net:{slice_id}:{net_name}"

        net_type_str = str(net_type)
        is_l2 = net_type_str in styles.L2_NETWORK_TYPES
        net_class = "network-l2" if is_l2 else "network-l3"
        edge_class = "l2" if is_l2 else "l3"

        subnet = self._safe_get(net, "get_subnet", None)
        # Shorter label: just name and type
        label = f"{net_name}\n{net_type_str}"

        self._add_node(
            cy_id=net_cy_id,
            label=label,
            classes=net_class,
            data={
                "element_type": "network",
                "net_type": net_type_str,
                "subnet": str(subnet) if subnet else "",
                "net_color": styles.get_network_color(net_type_str),
            },
        )
        self.element_map[net_cy_id] = net

        # Edges from VMs to this network
        for iface in net.get_interfaces():
            iface_name = iface.get_name()
            source_cy_id = iface_source_map.get(iface_name)
            if source_cy_id is None:
                continue

            edge_label = self._build_edge_label(iface)
            edge_cy_id = f"edge:{slice_id}:{iface_name}"

            edge_data = self._sanitize_data({
                "id": edge_cy_id,
                "source": source_cy_id,
                "target": net_cy_id,
                "edge_label": edge_label,
                "element_type": "interface",
                "iface_name": iface_name,
            })
            self._edges.append({
                "data": edge_data,
                "classes": edge_class,
            })

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _add_node(self, cy_id: str, label: str, classes: str,
                  parent: str = None, data: dict = None) -> None:
        node_data = {
            "id": cy_id,
            "label": str(label),
            "name": str(label),
        }
        if parent:
            node_data["parent"] = parent
        if data:
            node_data.update(data)
        node_data = self._sanitize_data(node_data)
        self._nodes.append({"data": node_data, "classes": classes})

    def _build_component_summary(self, node) -> str:
        """Build a compact string summarizing the components on a node.

        Example outputs: "NIC x2  GPU"  or  "sNIC  GPU x2  NVM"
        """
        type_counts: Counter = Counter()
        try:
            for cmp in node.get_components():
                model = str(self._safe_get(cmp, "get_model", "unknown"))
                short = styles.get_component_short_name(model)
                type_counts[short] += 1
        except Exception:
            return ""

        if not type_counts:
            return ""

        parts = []
        for name, count in type_counts.items():
            if count > 1:
                parts.append(f"{name}x{count}")
            else:
                parts.append(name)
        return "  ".join(parts)

    def _build_edge_label(self, iface) -> str:
        parts = []
        vlan = self._safe_get(iface, "get_vlan", None)
        if vlan:
            parts.append(f"vlan:{vlan}")
        ip = self._safe_get(iface, "get_ip_addr", None)
        if ip:
            parts.append(str(ip))
        bandwidth = self._safe_get(iface, "get_bandwidth", None)
        if bandwidth and bandwidth != 0:
            parts.append(f"{bandwidth}G")
        return "  ".join(parts) if parts else ""

    @staticmethod
    def _get_slice_state(slice_obj) -> str:
        try:
            state = slice_obj.get_state()
            return str(state) if state else "Unknown"
        except Exception:
            return "Unknown"

    @staticmethod
    def _get_node_state(node) -> str:
        try:
            state = node.get_reservation_state()
            return str(state) if state else "Unknown"
        except Exception:
            return "Unknown"

    @staticmethod
    def _sanitize_data(data: dict) -> dict:
        """Ensure all dict values are JSON-serializable primitives."""
        clean = {}
        for key, val in data.items():
            if val is None or isinstance(val, (str, int, float, bool)):
                clean[key] = val
            else:
                clean[key] = str(val)
        return clean

    @staticmethod
    def _safe_get(obj, method_name: str, default=None):
        try:
            method = getattr(obj, method_name, None)
            if method is None:
                return default
            result = method()
            return result if result is not None else default
        except Exception:
            return default
