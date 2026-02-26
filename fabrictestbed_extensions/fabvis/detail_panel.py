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

"""Detail panel rendering for selected graph elements."""

import ipywidgets as widgets

from . import styles
from .styles import (
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FABRIC_PRIMARY_LIGHT,
    FABRIC_SUCCESS,
    FABRIC_DANGER,
    FABRIC_WARNING,
    FONT_IMPORT_CSS,
)


class DetailPanel:
    """Renders HTML detail views for selected graph elements."""

    PANEL_STYLE = f"""
    {FONT_IMPORT_CSS}
    <style>
        .fabvis-detail {{
            font-family: {FABRIC_BODY_FONT};
            font-size: 12px; padding: 12px; line-height: 1.6;
        }}
        .fabvis-detail h3 {{
            color: {FABRIC_PRIMARY_DARK}; margin: 0 0 12px 0; font-size: 14px;
            padding-bottom: 8px;
            border-bottom: 1.5px solid rgba(138,201,239,0.5);
            font-weight: 600;
        }}
        .fabvis-detail h4 {{
            color: {FABRIC_DARK}; margin: 12px 0 6px 0; font-size: 11px;
            text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;
            opacity: 0.8;
        }}
        .fabvis-detail table {{
            border-collapse: separate; border-spacing: 0; width: 100%;
            border-radius: 6px; overflow: hidden;
            border: 1px solid rgba(0,0,0,0.06);
        }}
        .fabvis-detail tr {{ border-bottom: 1px solid rgba(0,0,0,0.04); }}
        .fabvis-detail tr:last-child {{ border-bottom: none; }}
        .fabvis-detail td {{ padding: 5px 8px; vertical-align: top; }}
        .fabvis-detail td:first-child {{
            font-weight: 600; white-space: nowrap; color: {FABRIC_DARK};
            width: 80px; font-size: 11px; opacity: 0.85;
        }}
        .fabvis-detail td:last-child {{ color: #212121; }}
        .fabvis-detail .state-ok {{ color: {FABRIC_SUCCESS}; font-weight: 600; }}
        .fabvis-detail .state-err {{ color: {FABRIC_DANGER}; font-weight: 600; }}
        .fabvis-detail .state-prog {{ color: {FABRIC_WARNING}; font-weight: 600; }}
        .fabvis-detail .section {{
            border-top: 1px solid rgba(138,201,239,0.3);
            margin-top: 12px; padding-top: 10px;
        }}
        .fabvis-detail .cmp-item {{
            margin: 4px 0; padding: 5px 10px; background: {FABRIC_LIGHT};
            border-radius: 6px;
            border-left: 2.5px solid rgba(138,201,239,0.6);
            font-size: 11px;
        }}
    </style>
    """

    def __init__(self):
        self.widget = widgets.HTML(
            value=self._placeholder(),
            layout=widgets.Layout(
                width="100%",
                height="100%",
                overflow_y="auto",
                padding="4px",
            ),
        )

    def _placeholder(self) -> str:
        return (
            self.PANEL_STYLE
            + '<div class="fabvis-detail"><i>Click an element to inspect</i></div>'
        )

    def clear(self) -> None:
        """Reset to placeholder text."""
        self.widget.value = self._placeholder()

    def show_slice(self, slice_obj) -> None:
        """Display Slice details."""
        name = self._safe(slice_obj, "get_name")
        state = self._safe(slice_obj, "get_state")
        slice_id = self._safe(slice_obj, "get_slice_id")
        lease_end = self._safe(slice_obj, "get_lease_end")

        nodes = []
        try:
            nodes = slice_obj.get_nodes()
        except Exception:
            pass

        networks = []
        try:
            networks = slice_obj.get_network_services()
        except Exception:
            pass

        rows = self._table_rows([
            ("Name", name),
            ("State", self._state_span(state)),
            ("Slice ID", f"<small>{slice_id}</small>"),
            ("Lease End", str(lease_end) if lease_end else "—"),
            ("Nodes", str(len(nodes))),
            ("Networks", str(len(networks))),
        ])

        # Node summary list
        node_items = ""
        for n in nodes:
            n_name = self._safe(n, "get_name")
            n_site = self._safe(n, "get_site")
            node_items += f'<div class="cmp-item">{n_name} @ {n_site}</div>'

        net_items = ""
        for net in networks:
            n_name = self._safe(net, "get_name")
            n_type = self._safe(net, "get_type")
            net_items += f'<div class="cmp-item">{n_name} ({n_type})</div>'

        html = f"""
        {self.PANEL_STYLE}
        <div class="fabvis-detail">
            <h3>Slice: {name}</h3>
            <table>{rows}</table>
            <div class="section"><h4>Nodes</h4>{node_items or '<i>none</i>'}</div>
            <div class="section"><h4>Networks</h4>{net_items or '<i>none</i>'}</div>
        </div>
        """
        self.widget.value = html

    def show_node(self, node_obj) -> None:
        """Display Node details."""
        name = self._safe(node_obj, "get_name")
        site = self._safe(node_obj, "get_site")
        host = self._safe(node_obj, "get_host")
        cores = self._safe(node_obj, "get_cores")
        ram = self._safe(node_obj, "get_ram")
        disk = self._safe(node_obj, "get_disk")
        image = self._safe(node_obj, "get_image")
        mgmt_ip = self._safe(node_obj, "get_management_ip")
        state = self._safe(node_obj, "get_reservation_state")
        username = self._safe(node_obj, "get_username")

        rows = self._table_rows([
            ("Name", name),
            ("State", self._state_span(state)),
            ("Site", site),
            ("Host", host or "—"),
            ("Cores", str(cores)),
            ("RAM", f"{ram} GB"),
            ("Disk", f"{disk} GB"),
            ("Image", str(image)),
            ("User", str(username)),
            ("Mgmt IP", f"<small>{mgmt_ip}</small>" if mgmt_ip else "—"),
        ])

        # Components
        cmp_items = ""
        try:
            for c in node_obj.get_components():
                c_name = self._safe(c, "get_name")
                c_model = self._safe(c, "get_model")
                color = styles.get_component_color(str(c_model))
                cmp_items += (
                    f'<div class="cmp-item">'
                    f'<span style="color:{color};">&#9679;</span> '
                    f'{c_name} ({c_model})</div>'
                )
        except Exception:
            pass

        # Interfaces
        iface_items = ""
        try:
            for iface in node_obj.get_interfaces():
                i_name = self._safe(iface, "get_name")
                ip = self._safe(iface, "get_ip_addr")
                net = None
                try:
                    net_obj = iface.get_network()
                    if net_obj:
                        net = self._safe(net_obj, "get_name")
                except Exception:
                    pass
                parts = [i_name]
                if net:
                    parts.append(f"&rarr; {net}")
                if ip:
                    parts.append(f"({ip})")
                iface_items += f'<div class="cmp-item">{" ".join(parts)}</div>'
        except Exception:
            pass

        html = f"""
        {self.PANEL_STYLE}
        <div class="fabvis-detail">
            <h3>Node: {name}</h3>
            <table>{rows}</table>
            <div class="section"><h4>Components</h4>{cmp_items or '<i>none</i>'}</div>
            <div class="section"><h4>Interfaces</h4>{iface_items or '<i>none</i>'}</div>
        </div>
        """
        self.widget.value = html

    def show_component(self, component_obj) -> None:
        """Display Component details."""
        name = self._safe(component_obj, "get_name")
        model = self._safe(component_obj, "get_model")
        cmp_type = self._safe(component_obj, "get_type")
        details = self._safe(component_obj, "get_details")
        pci = self._safe(component_obj, "get_pci_addr")
        numa = self._safe(component_obj, "get_numa_node")
        device = self._safe(component_obj, "get_device_name")

        node_name = "—"
        try:
            node_name = self._safe(component_obj.get_node(), "get_name")
        except Exception:
            pass

        rows = self._table_rows([
            ("Name", name),
            ("Model", str(model)),
            ("Type", str(cmp_type)),
            ("Node", node_name),
            ("PCI Addr", str(pci) if pci else "—"),
            ("NUMA", str(numa) if numa else "—"),
            ("Device", str(device) if device else "—"),
            ("Details", str(details) if details else "—"),
        ])

        # Interfaces on this component
        iface_items = ""
        try:
            for iface in component_obj.get_interfaces():
                i_name = self._safe(iface, "get_name")
                mac = self._safe(iface, "get_mac")
                ip = self._safe(iface, "get_ip_addr")
                vlan = self._safe(iface, "get_vlan")
                parts = [i_name]
                if mac:
                    parts.append(f"MAC:{mac}")
                if ip:
                    parts.append(f"IP:{ip}")
                if vlan:
                    parts.append(f"VLAN:{vlan}")
                iface_items += f'<div class="cmp-item">{" | ".join(parts)}</div>'
        except Exception:
            pass

        color = styles.get_component_color(str(model))
        html = f"""
        {self.PANEL_STYLE}
        <div class="fabvis-detail">
            <h3><span style="color:{color};">&#9679;</span> Component: {name}</h3>
            <table>{rows}</table>
            <div class="section"><h4>Interfaces</h4>{iface_items or '<i>none</i>'}</div>
        </div>
        """
        self.widget.value = html

    def show_network(self, net_obj) -> None:
        """Display NetworkService details."""
        name = self._safe(net_obj, "get_name")
        net_type = self._safe(net_obj, "get_type")
        layer = self._safe(net_obj, "get_layer")
        subnet = self._safe(net_obj, "get_subnet")
        gateway = self._safe(net_obj, "get_gateway")
        site = self._safe(net_obj, "get_site")

        color = styles.get_network_color(str(net_type))
        rows = self._table_rows([
            ("Name", name),
            ("Type", f'<span style="color:{color};">{net_type}</span>'),
            ("Layer", str(layer) if layer else "—"),
            ("Site", str(site) if site else "—"),
            ("Subnet", str(subnet) if subnet else "—"),
            ("Gateway", str(gateway) if gateway else "—"),
        ])

        # Connected interfaces
        iface_items = ""
        try:
            for iface in net_obj.get_interfaces():
                i_name = self._safe(iface, "get_name")
                ip = self._safe(iface, "get_ip_addr")
                vlan = self._safe(iface, "get_vlan")
                node_name = "?"
                try:
                    node_name = self._safe(iface.get_node(), "get_name")
                except Exception:
                    pass
                parts = [f"{node_name}:{i_name}"]
                if ip:
                    parts.append(str(ip))
                if vlan:
                    parts.append(f"vlan:{vlan}")
                iface_items += f'<div class="cmp-item">{" | ".join(parts)}</div>'
        except Exception:
            pass

        html = f"""
        {self.PANEL_STYLE}
        <div class="fabvis-detail">
            <h3>Network: {name}</h3>
            <table>{rows}</table>
            <div class="section"><h4>Connected Interfaces</h4>{iface_items or '<i>none</i>'}</div>
        </div>
        """
        self.widget.value = html

    def show_interface(self, iface_obj) -> None:
        """Display Interface details (for edge clicks)."""
        name = self._safe(iface_obj, "get_name")
        mac = self._safe(iface_obj, "get_mac")
        ip = self._safe(iface_obj, "get_ip_addr")
        subnet = self._safe(iface_obj, "get_subnet")
        vlan = self._safe(iface_obj, "get_vlan")
        bandwidth = self._safe(iface_obj, "get_bandwidth")
        site = self._safe(iface_obj, "get_site")
        os_iface = self._safe(iface_obj, "get_physical_os_interface_name")
        state = self._safe(iface_obj, "get_reservation_state")

        node_name = "?"
        try:
            node_name = self._safe(iface_obj.get_node(), "get_name")
        except Exception:
            pass

        net_name = "?"
        try:
            net_obj = iface_obj.get_network()
            if net_obj:
                net_name = self._safe(net_obj, "get_name")
        except Exception:
            pass

        rows = self._table_rows([
            ("Name", name),
            ("State", self._state_span(state)),
            ("Node", node_name),
            ("Network", net_name),
            ("Site", str(site) if site else "—"),
            ("MAC", str(mac) if mac else "—"),
            ("IP", str(ip) if ip else "—"),
            ("Subnet", str(subnet) if subnet else "—"),
            ("VLAN", str(vlan) if vlan else "—"),
            ("Bandwidth", f"{bandwidth} Gbps" if bandwidth else "—"),
            ("OS Interface", str(os_iface) if os_iface else "—"),
        ])

        html = f"""
        {self.PANEL_STYLE}
        <div class="fabvis-detail">
            <h3>Interface</h3>
            <table>{rows}</table>
        </div>
        """
        self.widget.value = html

    @staticmethod
    def _table_rows(pairs: list) -> str:
        """Build HTML table rows from (label, value) pairs."""
        rows = ""
        for label, value in pairs:
            rows += f"<tr><td>{label}</td><td>{value or '—'}</td></tr>"
        return rows

    @staticmethod
    def _state_span(state) -> str:
        """Wrap a state string in a colored span."""
        state_str = str(state) if state else "Unknown"
        if state_str in ("Active", "StableOK"):
            cls = "state-ok"
        elif state_str in ("StableError", "ModifyError", "Failed"):
            cls = "state-err"
        elif state_str in ("Configuring", "Ticketed", "ModifyOK", "Nascent"):
            cls = "state-prog"
        else:
            cls = ""
        if cls:
            return f'<span class="{cls}">{state_str}</span>'
        return state_str

    @staticmethod
    def _safe(obj, method_name: str, default=""):
        """Safely call a getter, returning default on any failure."""
        try:
            method = getattr(obj, method_name, None)
            if method is None:
                return default
            result = method()
            return result if result is not None else default
        except Exception:
            return default
