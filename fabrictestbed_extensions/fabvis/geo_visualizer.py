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

"""Geographic map-based FABRIC slice visualizer using ipyleaflet.

Inspired by the legacy GeoTopologyEditor, this visualizer shows FABRIC
slice topologies on an interactive geographic map. Sites appear as markers,
nodes are shown at their site locations, and network connections between
sites are drawn as animated ant paths.
"""

import functools
import logging
from collections import defaultdict

import ipywidgets as widgets
from IPython.display import display
from ipyleaflet import (
    AntPath,
    CircleMarker,
    FullScreenControl,
    LayerGroup,
    Map,
    Marker,
    Popup,
    ZoomControl,
    basemaps,
)
from ipywidgets import HTML, Layout

from .detail_panel import DetailPanel
from .styles import (
    DEFAULT_MAP_CENTER,
    DEFAULT_MAP_ZOOM,
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FABRIC_PRIMARY_LIGHT,
    FABRIC_SUCCESS,
    FABRIC_WARNING,
    FONT_IMPORT_CSS,
    SITE_LOCATIONS,
    get_logo_data_url,
    get_site_location,
    get_state_color,
)

logger = logging.getLogger(__name__)


class GeoVisualizer:
    """Interactive geographic map visualizer for FABRIC slices.

    Shows FABRIC sites on an ipyleaflet map. When slices are loaded,
    nodes appear at their site locations and network connections are
    drawn as animated paths between sites.

    Usage:
        from fabrictestbed_extensions.fablib.fablib import FablibManager
        from fabrictestbed_extensions.fabvis import GeoVisualizer

        fablib = FablibManager()
        vis = GeoVisualizer(fablib)
        vis.show()  # presents slice picker, user selects and clicks Load

        # Or load specific slices directly:
        vis = GeoVisualizer(fablib)
        vis.load_slices(["my_experiment"])
        vis.show()
    """

    def __init__(self, fablib_manager):
        """Initialize with a FablibManager instance."""
        self._fablib = fablib_manager
        self._detail = DetailPanel()
        self._loaded_slices: dict = {}  # name -> Slice object

        # Layer groups for the map
        self._sites_layer = LayerGroup(layers=())
        self._slices_layer = LayerGroup(layers=())
        self._links_layer = LayerGroup(layers=())

        # Track objects for click handlers
        self._node_objects: dict = {}  # marker -> node FABlib object
        self._net_objects: dict = {}   # path -> network FABlib object

        self._build_widgets()

    def show(self) -> None:
        """Display the full widget UI in the notebook."""
        self._refresh_slice_list()
        self._draw_sites()
        display(self._container)

    def load_slices(self, slice_names: list) -> None:
        """Load specific slices by name and render them on the map."""
        self._loaded_slices.clear()
        errors = []

        for name in slice_names:
            try:
                s = self._fablib.get_slice(name)
                self._loaded_slices[name] = s
            except Exception as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"Failed to load slice '{name}': {e}")

        if errors:
            self._set_status(f"Loaded {len(self._loaded_slices)} slices, "
                             f"{len(errors)} errors")
        else:
            self._set_status(f"Loaded {len(self._loaded_slices)} slices")

        self._render_slices()

    def refresh(self) -> None:
        """Re-fetch slice data from FABRIC and re-render."""
        if not self._loaded_slices:
            self._set_status("No slices loaded")
            return
        names = list(self._loaded_slices.keys())
        self.load_slices(names)

    # ----------------------------------------------------------------
    # Widget construction
    # ----------------------------------------------------------------

    def _build_widgets(self) -> None:
        """Construct all ipywidgets that compose the UI."""

        # Slice selector
        self._slice_selector = widgets.SelectMultiple(
            options=[],
            description="",
            layout=widgets.Layout(width="300px", height="80px"),
        )

        self._load_btn = widgets.Button(
            description="Load",
            button_style="primary",
            layout=widgets.Layout(width="70px"),
        )
        self._load_btn.on_click(self._on_load_click)

        self._refresh_btn = widgets.Button(
            description="Refresh",
            button_style="",
            layout=widgets.Layout(width="80px"),
        )
        self._refresh_btn.on_click(self._on_refresh_click)

        self._refresh_list_btn = widgets.Button(
            description="↻ Slices",
            button_style="",
            tooltip="Refresh the slice list from FABRIC",
            layout=widgets.Layout(width="80px"),
        )
        self._refresh_list_btn.on_click(self._on_refresh_list_click)

        selector_label = widgets.HTML(
            value=(
                f'{FONT_IMPORT_CSS}'
                f'<b style="color:{FABRIC_PRIMARY_DARK}; '
                f'font-family:{FABRIC_BODY_FONT};">Select Slices:</b>'
            ),
            layout=widgets.Layout(width="100px"),
        )

        top_bar = widgets.HBox(
            [selector_label, self._slice_selector,
             self._load_btn, self._refresh_btn, self._refresh_list_btn],
            layout=widgets.Layout(
                padding="8px 12px",
                border_bottom=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                background=FABRIC_LIGHT,
                align_items="center",
                gap="8px",
            ),
        )

        # Map canvas
        self._map = Map(
            basemap=basemaps.Esri.WorldStreetMap,
            center=DEFAULT_MAP_CENTER,
            zoom=DEFAULT_MAP_ZOOM,
            zoom_control=False,
            layout=Layout(width="100%", height="550px"),
        )
        self._map.add_layer(self._sites_layer)
        self._map.add_layer(self._links_layer)
        self._map.add_layer(self._slices_layer)
        self._map.add_control(FullScreenControl(position="bottomleft"))
        self._map.add_control(ZoomControl(position="bottomleft"))

        map_box = widgets.Box(
            [self._map],
            layout=widgets.Layout(
                width="75%",
                height="550px",
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="4px",
            ),
        )

        # Detail panel
        detail_box = widgets.VBox(
            [
                widgets.HTML(
                    value=(
                        f'{FONT_IMPORT_CSS}'
                        f'<div style="background:{FABRIC_LIGHT}; padding:6px 10px; '
                        f'border-bottom:2px solid {FABRIC_PRIMARY}; '
                        f'font-family:{FABRIC_BODY_FONT};">'
                        f'<b style="color:{FABRIC_PRIMARY_DARK}; font-size:13px;">'
                        f'Details</b></div>'
                    ),
                    layout=widgets.Layout(padding="0px"),
                ),
                self._detail.widget,
            ],
            layout=widgets.Layout(
                width="25%",
                height="550px",
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="4px",
                overflow_y="auto",
            ),
        )

        main_area = widgets.HBox(
            [map_box, detail_box],
            layout=widgets.Layout(gap="4px"),
        )

        # Bottom bar
        self._status_label = widgets.HTML(
            value="<i>Ready</i>",
            layout=widgets.Layout(width="400px"),
        )

        self._show_sites_cb = widgets.Checkbox(
            value=True,
            description="Show all sites",
            layout=widgets.Layout(width="150px"),
        )
        self._show_sites_cb.observe(self._on_toggle_sites, names="value")

        bottom_bar = widgets.HBox(
            [self._show_sites_cb, self._status_label],
            layout=widgets.Layout(
                padding="8px 12px",
                border_top=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                background=FABRIC_LIGHT,
                align_items="center",
                gap="12px",
            ),
        )

        # Title bar with FABRIC logo
        logo_url = get_logo_data_url()
        if logo_url:
            logo_html = (
                f'<img src="{logo_url}" '
                f'style="height:28px; margin-right:12px; vertical-align:middle;" '
                f'alt="FABRIC">'
            )
        else:
            logo_html = ""

        title = widgets.HTML(
            value=(
                f'{FONT_IMPORT_CSS}'
                f'<div style="background:linear-gradient(135deg, {FABRIC_PRIMARY_DARK}, {FABRIC_PRIMARY}); '
                f'color:white; padding:10px 16px; font-size:16px; font-weight:600; '
                f'letter-spacing:0.5px; border-radius:4px 4px 0 0; '
                f'font-family:{FABRIC_BODY_FONT}; '
                f'display:flex; align-items:center;">'
                f'{logo_html}'
                f'<span>Geographic Slice Visualizer</span></div>'
            ),
        )

        # Main container
        self._container = widgets.VBox(
            [title, top_bar, main_area, bottom_bar],
            layout=widgets.Layout(
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="4px",
                box_shadow="0 2px 8px rgba(0,0,0,0.08)",
            ),
        )

    # ----------------------------------------------------------------
    # Event handlers
    # ----------------------------------------------------------------

    def _on_load_click(self, _btn) -> None:
        selected = list(self._slice_selector.value)
        if not selected:
            self._set_status("No slices selected")
            return
        self._set_status("Loading...")
        self.load_slices(selected)

    def _on_refresh_click(self, _btn) -> None:
        self._set_status("Refreshing...")
        self.refresh()

    def _on_refresh_list_click(self, _btn) -> None:
        self._refresh_slice_list()

    def _on_toggle_sites(self, change) -> None:
        if change["new"]:
            self._draw_sites()
        else:
            self._sites_layer.clear_layers()

    def _on_site_click(self, site_name, **kwargs):
        """Handle click on a site marker — show site info in detail panel."""
        html = (
            f'{self._detail.PANEL_STYLE}'
            f'<div class="fabvis-detail">'
            f'<h3>Site: {site_name}</h3>'
            f'<table>'
        )
        loc = get_site_location(site_name)
        if loc:
            html += f'<tr><td><b>Location</b></td><td>{loc[0]:.4f}, {loc[1]:.4f}</td></tr>'

        # Show nodes at this site from loaded slices
        nodes_here = []
        for slice_name, slice_obj in self._loaded_slices.items():
            try:
                for node in slice_obj.get_nodes():
                    try:
                        node_site = node.get_site()
                    except Exception:
                        node_site = None
                    if node_site == site_name:
                        nodes_here.append((slice_name, node))
            except Exception:
                pass

        html += f'<tr><td><b>Nodes here</b></td><td>{len(nodes_here)}</td></tr>'
        html += '</table>'

        if nodes_here:
            html += '<div class="section"><h4>Nodes</h4>'
            for sname, node in nodes_here:
                nname = "?"
                try:
                    nname = node.get_name()
                except Exception:
                    pass
                html += f'<div class="cmp-item">{nname} ({sname})</div>'
            html += '</div>'

        html += '</div>'
        self._detail.widget.value = html

    def _on_node_marker_click(self, node_obj, **kwargs):
        """Handle click on a node marker — show node details."""
        self._detail.show_node(node_obj)

    # ----------------------------------------------------------------
    # Drawing
    # ----------------------------------------------------------------

    def _draw_sites(self) -> None:
        """Draw all known FABRIC sites as circle markers on the map."""
        self._sites_layer.clear_layers()

        for site_name, (lat, lon) in SITE_LOCATIONS.items():
            marker = CircleMarker()
            marker.location = (lat, lon)
            marker.radius = 8
            marker.color = FABRIC_PRIMARY
            marker.fill_color = FABRIC_PRIMARY
            marker.fill_opacity = 0.6
            marker.weight = 2

            # Popup with site name
            popup = Popup(
                child=HTML(value=(
                    f'{FONT_IMPORT_CSS}'
                    f'<b style="color:{FABRIC_PRIMARY_DARK}; '
                    f'font-family:{FABRIC_BODY_FONT};">{site_name}</b>'
                )),
                close_button=False,
                auto_close=True,
                close_on_escape_key=True,
            )
            marker.popup = popup

            marker.on_click(functools.partial(self._on_site_click, site_name=site_name))
            self._sites_layer.add_layer(marker)

    def _render_slices(self) -> None:
        """Render loaded slices on the map — nodes as markers, networks as paths."""
        self._slices_layer.clear_layers()
        self._links_layer.clear_layers()
        self._node_objects.clear()
        self._net_objects.clear()

        if not self._loaded_slices:
            return

        # Collect all nodes grouped by site
        site_nodes: dict[str, list] = defaultdict(list)
        all_nodes = []  # (slice_name, node_obj)

        for slice_name, slice_obj in self._loaded_slices.items():
            try:
                for node in slice_obj.get_nodes():
                    site = self._safe_get(node, "get_site", None)
                    if site:
                        site_nodes[site].append((slice_name, node))
                        all_nodes.append((slice_name, node))
            except Exception as e:
                logger.warning(f"Error processing nodes for slice '{slice_name}': {e}")

        # Draw node markers at each site (offset slightly if multiple nodes)
        for site, nodes in site_nodes.items():
            loc = get_site_location(site)
            if loc is None:
                continue

            for idx, (slice_name, node) in enumerate(nodes):
                # Offset each node slightly so they don't stack
                offset_lat = idx * 0.15
                offset_lon = idx * 0.15
                node_loc = (loc[0] + offset_lat, loc[1] + offset_lon)

                node_name = self._safe_get(node, "get_name", "?")
                node_state = self._safe_get(node, "get_reservation_state", "Unknown")
                state_color = get_state_color(str(node_state))

                marker = CircleMarker()
                marker.location = node_loc
                marker.radius = 12
                marker.color = FABRIC_PRIMARY_DARK
                marker.fill_color = state_color
                marker.fill_opacity = 0.9
                marker.weight = 3

                popup = Popup(
                    child=HTML(
                        value=(
                            f'{FONT_IMPORT_CSS}'
                            f'<div style="font-family:{FABRIC_BODY_FONT};">'
                            f'<b style="color:{FABRIC_PRIMARY_DARK};">{node_name}</b><br>'
                            f'<small>{site} | {slice_name}</small><br>'
                            f'<small>State: {node_state}</small></div>'
                        )
                    ),
                    close_button=False,
                    auto_close=True,
                )
                marker.popup = popup

                marker.on_click(
                    functools.partial(self._on_node_marker_click, node_obj=node)
                )
                self._slices_layer.add_layer(marker)

        # Draw network connections as ant paths between sites
        drawn_links = set()  # avoid duplicate paths for the same site pair
        for slice_name, slice_obj in self._loaded_slices.items():
            try:
                for net in slice_obj.get_network_services():
                    self._draw_network_path(net, slice_name, drawn_links)
            except Exception as e:
                logger.warning(f"Error drawing networks for '{slice_name}': {e}")

        node_count = len(all_nodes)
        site_count = len(site_nodes)
        self._set_status(
            f"Showing {node_count} nodes across {site_count} sites "
            f"from {len(self._loaded_slices)} slices"
        )

    def _draw_network_path(self, net, slice_name: str, drawn_links: set) -> None:
        """Draw an ant path for a network service connecting multiple sites."""
        net_type = self._safe_get(net, "get_type", "unknown")

        # Collect unique sites connected by this network
        connected_sites = set()
        try:
            for iface in net.get_interfaces():
                site = self._safe_get(iface, "get_site", None)
                if not site:
                    # Try getting site from the node
                    try:
                        node = iface.get_node()
                        if node:
                            site = self._safe_get(node, "get_site", None)
                    except Exception:
                        pass
                if site:
                    connected_sites.add(site)
        except Exception:
            return

        if len(connected_sites) < 2:
            return

        # Draw paths between all pairs of connected sites
        sites = sorted(connected_sites)
        for i in range(len(sites)):
            for j in range(i + 1, len(sites)):
                site_a, site_b = sites[i], sites[j]
                link_key = (min(site_a, site_b), max(site_a, site_b))
                if link_key in drawn_links:
                    continue
                drawn_links.add(link_key)

                loc_a = get_site_location(site_a)
                loc_b = get_site_location(site_b)
                if loc_a is None or loc_b is None:
                    continue

                # Color based on L2 vs L3
                is_l2 = net_type in {"L2Bridge", "L2STS", "L2PTP", "PortMirror"}
                path_color = FABRIC_PRIMARY if is_l2 else FABRIC_SUCCESS

                ant_path = AntPath(
                    locations=[loc_a, loc_b],
                    dash_array=[1, 10],
                    delay=1000,
                    color="#7590ba",
                    pulse_color=path_color,
                    paused=False,
                    hardwareAccelerated=True,
                    weight=3,
                )

                net_name = self._safe_get(net, "get_name", "?")
                ant_path.on_click(
                    functools.partial(self._on_path_click, net_obj=net)
                )
                self._links_layer.add_layer(ant_path)

    def _on_path_click(self, net_obj, **kwargs):
        """Handle click on a network ant path — show network details."""
        self._detail.show_network(net_obj)

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------

    def _refresh_slice_list(self) -> None:
        """Fetch slice list from FABRIC and update the selector widget."""
        self._set_status("Fetching slice list...")
        try:
            slices = self._fablib.get_slices()
            options = []
            for s in slices:
                name = s.get_name()
                options.append(name)
            self._slice_selector.options = sorted(options)
            self._set_status(f"{len(options)} slices available")
        except Exception as e:
            self._set_status(f"Error listing slices: {e}")
            logger.error(f"Failed to list slices: {e}")

    def _set_status(self, text: str) -> None:
        self._status_label.value = (
            f'<small style="font-family:{FABRIC_BODY_FONT}; '
            f'color:{FABRIC_DARK};">{text}</small>'
        )

    @staticmethod
    def _safe_get(obj, method_name: str, default=None):
        """Safely call a getter method, returning default on failure."""
        try:
            method = getattr(obj, method_name, None)
            if method is None:
                return default
            result = method()
            return result if result is not None else default
        except Exception:
            return default
