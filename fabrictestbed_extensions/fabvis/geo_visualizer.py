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
sites are drawn as animated ant paths. Infrastructure links between FABRIC
sites can be toggled independently.
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
    Polyline,
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
    WIDGET_SOFT_CSS,
    get_logo_data_url,
    get_site_location,
    get_state_color,
)

logger = logging.getLogger(__name__)


class GeoVisualizer:
    """Interactive geographic map visualizer for FABRIC slices.

    Shows FABRIC sites on an ipyleaflet map. When slices are loaded,
    nodes appear at their site locations and network connections are
    drawn as animated paths between sites. Infrastructure links between
    sites are shown as polylines and can be toggled independently.

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

    def __init__(self, fablib_manager=None):
        """Initialize with an optional FablibManager instance.

        Args:
            fablib_manager: An initialized FablibManager from fablib.
                            Not required if using show_slice() or passing
                            slice objects directly.
        """
        self._fablib = fablib_manager
        self._detail = DetailPanel()
        self._loaded_slices: dict = {}  # name -> Slice object
        self._picker_mode = fablib_manager is not None

        # Cached resources data
        self._resources = None
        self._links_data: list = []
        self._sites_data: dict = {}  # site_name -> site dict

        # Layer groups for the map
        self._sites_layer = LayerGroup(layers=())
        self._infra_links_layer = LayerGroup(layers=())
        self._slices_layer = LayerGroup(layers=())
        self._slice_links_layer = LayerGroup(layers=())

        # Track objects for click handlers
        self._node_objects: dict = {}  # marker -> node FABlib object
        self._net_objects: dict = {}   # path -> network FABlib object

        self._build_widgets()

    @classmethod
    def show_slice(cls, slice_obj):
        """Display a single slice on the map (no slice picker).

        Args:
            slice_obj: A FABlib Slice object.

        Returns:
            The GeoVisualizer instance.
        """
        return cls.show_slices([slice_obj])

    @classmethod
    def show_slices(cls, slice_objs: list):
        """Display one or more slices on the map (no slice picker).

        Args:
            slice_objs: List of FABlib Slice objects.

        Returns:
            The GeoVisualizer instance.
        """
        vis = cls()  # no fablib_manager → picker hidden
        for s in slice_objs:
            name = s.get_name() if hasattr(s, "get_name") else str(s)
            vis._loaded_slices[name] = s
        vis._draw_sites()
        vis._render_slices()
        display(vis._container)
        return vis

    def show(self) -> None:
        """Display the full widget UI in the notebook."""
        if self._fablib and self._picker_mode:
            self._refresh_slice_list()
            self._load_resources()
        self._draw_sites()
        if self._show_links_cb.value:
            self._draw_infra_links()
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

    def to_image(self, **kwargs):
        """Render loaded slices as a static matplotlib geographic Figure.

        Args:
            **kwargs: Passed to render_slice_map() (figsize, dpi, title,
                      show_all_sites, map_extent).

        Returns:
            matplotlib Figure object.
        """
        from .image_export import render_slice_map

        if not self._loaded_slices:
            raise ValueError("No slices loaded. Call load_slices() first.")
        return render_slice_map(
            list(self._loaded_slices.values()), **kwargs
        )

    def save_image(self, path: str, **kwargs) -> None:
        """Render loaded slices and save as an image file.

        Args:
            path: Output file path (png, pdf, svg).
            **kwargs: Passed to render_slice_map().
        """
        from .image_export import render_slice_map

        if not self._loaded_slices:
            raise ValueError("No slices loaded. Call load_slices() first.")
        fig = render_slice_map(
            list(self._loaded_slices.values()), save=path, **kwargs
        )
        import matplotlib.pyplot as plt
        plt.close(fig)

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
                border_bottom=f"1px solid rgba(138,201,239,0.4)",
                background=FABRIC_LIGHT,
                align_items="center",
                gap="8px",
            ),
        )

        # Map canvas — US-centric view (world_copy_jump wraps at date line)
        self._map = Map(
            basemap=basemaps.Esri.WorldStreetMap,
            center=DEFAULT_MAP_CENTER,
            zoom=DEFAULT_MAP_ZOOM,
            zoom_control=False,
            world_copy_jump=False,
            min_zoom=2,
            layout=Layout(width="100%", height="550px"),
        )
        self._map.add_layer(self._sites_layer)
        self._map.add_layer(self._infra_links_layer)
        self._map.add_layer(self._slice_links_layer)
        self._map.add_layer(self._slices_layer)
        self._map.add_control(FullScreenControl(position="bottomleft"))
        self._map.add_control(ZoomControl(position="bottomleft"))

        self._map_box = widgets.Box(
            [self._map],
            layout=widgets.Layout(
                flex="1",
                height="550px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
            ),
        )

        # Detail panel with toggle button
        self._detail_toggle = widgets.Button(
            description="",
            icon="angle-right",
            tooltip="Collapse Details panel",
            layout=widgets.Layout(width="24px", height="20px",
                                  padding="0px", margin="0px"),
        )
        self._detail_toggle.on_click(self._toggle_detail_panel)

        detail_header = widgets.HBox(
            [
                widgets.HTML(
                    value=(
                        f'{FONT_IMPORT_CSS}'
                        f'<b style="color:{FABRIC_PRIMARY_DARK}; font-size:13px; '
                        f'font-family:{FABRIC_BODY_FONT};">Details</b>'
                    ),
                ),
                self._detail_toggle,
            ],
            layout=widgets.Layout(
                background=FABRIC_LIGHT,
                padding="8px 12px",
                border_bottom=f"1.5px solid rgba(87,152,188,0.4)",
                border_radius="8px 8px 0 0",
                justify_content="space-between",
                align_items="center",
            ),
        )

        self._detail_box = widgets.VBox(
            [detail_header, self._detail.widget],
            layout=widgets.Layout(
                width="25%",
                height="550px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                overflow_y="auto",
            ),
        )
        self._detail_visible = True

        # Collapsed detail strip (shown when panel is hidden)
        self._detail_expand_btn = widgets.Button(
            description="",
            icon="angle-left",
            tooltip="Expand Details panel",
            layout=widgets.Layout(width="24px", height="24px",
                                  padding="0px", margin="0px"),
        )
        self._detail_expand_btn.on_click(self._toggle_detail_panel)

        self._detail_strip = widgets.VBox(
            [self._detail_expand_btn],
            layout=widgets.Layout(
                width="28px",
                height="550px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                align_items="center",
                padding="6px 0",
                display="none",
            ),
        )

        main_area = widgets.HBox(
            [self._map_box, self._detail_box, self._detail_strip],
            layout=widgets.Layout(gap="4px"),
        )

        # Bottom bar — separate toggles for sites and links
        self._status_label = widgets.HTML(
            value="<i>Ready</i>",
            layout=widgets.Layout(flex="1"),
        )

        self._show_sites_cb = widgets.Checkbox(
            value=True,
            description="Sites",
            layout=widgets.Layout(width="100px"),
        )
        self._show_sites_cb.observe(self._on_toggle_sites, names="value")

        self._show_links_cb = widgets.Checkbox(
            value=True,
            description="Links",
            layout=widgets.Layout(width="100px"),
        )
        self._show_links_cb.observe(self._on_toggle_links, names="value")

        bottom_bar = widgets.HBox(
            [self._show_sites_cb, self._show_links_cb, self._status_label],
            layout=widgets.Layout(
                padding="8px 12px",
                border_top=f"1px solid rgba(138,201,239,0.4)",
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
                f'letter-spacing:0.5px; border-radius:8px 8px 0 0; '
                f'font-family:{FABRIC_BODY_FONT}; '
                f'display:flex; align-items:center;">'
                f'{logo_html}'
                f'<span>Geographic Slice Visualizer</span></div>'
            ),
        )

        # Inject soft button/input CSS
        css_widget = widgets.HTML(value=WIDGET_SOFT_CSS)

        # Main container — hide the slice picker bar when no fablib
        if self._picker_mode:
            container_children = [css_widget, title, top_bar, main_area, bottom_bar]
        else:
            container_children = [css_widget, title, main_area, bottom_bar]

        self._container = widgets.VBox(
            container_children,
            layout=widgets.Layout(
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="10px",
                box_shadow="0 2px 12px rgba(0,0,0,0.06)",
                overflow="hidden",
            ),
        )
        self._container.add_class("fabvis-soft")

    # ----------------------------------------------------------------
    # Panel toggle
    # ----------------------------------------------------------------

    def _toggle_detail_panel(self, _btn) -> None:
        """Toggle the detail panel between expanded and collapsed."""
        self._detail_visible = not self._detail_visible
        if self._detail_visible:
            self._detail_box.layout.display = None
            self._detail_strip.layout.display = "none"
            self._detail_toggle.icon = "angle-right"
            self._detail_toggle.tooltip = "Collapse Details panel"
        else:
            self._detail_box.layout.display = "none"
            self._detail_strip.layout.display = None
            self._detail_toggle.icon = "angle-left"
            self._detail_toggle.tooltip = "Expand Details panel"

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
        self._load_resources()
        self.refresh()
        if self._show_sites_cb.value:
            self._draw_sites()
        if self._show_links_cb.value:
            self._draw_infra_links()

    def _on_refresh_list_click(self, _btn) -> None:
        self._refresh_slice_list()

    def _on_toggle_sites(self, change) -> None:
        if change["new"]:
            self._draw_sites()
        else:
            self._sites_layer.clear_layers()

    def _on_toggle_links(self, change) -> None:
        if change["new"]:
            self._draw_infra_links()
        else:
            self._infra_links_layer.clear_layers()

    def _on_site_click(self, site_name, **kwargs):
        """Handle click on a site marker — show site info with resources."""
        self._show_site_detail(site_name)

    def _on_node_marker_click(self, node_obj, **kwargs):
        """Handle click on a node marker — show node details."""
        self._detail.show_node(node_obj)

    def _on_link_click(self, link_data, **kwargs):
        """Handle click on an infrastructure link — show link info."""
        self._show_link_detail(link_data)

    # ----------------------------------------------------------------
    # Resource loading
    # ----------------------------------------------------------------

    def _load_resources(self) -> None:
        """Fetch site and link data from FABRIC via fablib."""
        if not self._fablib:
            return

        try:
            self._resources = self._fablib.get_resources()

            # Cache site data
            self._sites_data = {}
            for name in self._resources.get_site_names():
                site = self._resources.get_site(name)
                if site:
                    self._sites_data[name] = site

            # Cache link data
            self._links_data = []
            for link_name in self._resources.get_link_list():
                for link in self._resources._links_data:
                    if link.get("name") == link_name:
                        self._links_data.append(link)
                        break

            self._set_status(
                f"{len(self._sites_data)} sites, {len(self._links_data)} links"
            )
        except Exception as e:
            logger.warning(f"Failed to load resources: {e}")
            self._set_status(f"Resource fetch error: {e}")

    # ----------------------------------------------------------------
    # Detail panel: site info with resource availability
    # ----------------------------------------------------------------

    def _show_site_detail(self, site_name: str) -> None:
        """Show site properties and resource availability in detail panel."""
        html = (
            f'{self._detail.PANEL_STYLE}'
            f'<div class="fabvis-detail">'
            f'<h3>Site: {site_name}</h3>'
            f'<table>'
        )

        loc = get_site_location(site_name)
        if loc:
            html += (
                f'<tr><td>Location</td>'
                f'<td>{loc[0]:.4f}, {loc[1]:.4f}</td></tr>'
            )

        # Site state and address from resources
        site_info = self._sites_data.get(site_name, {})
        state = site_info.get("state", "")
        if state:
            cls = "state-ok" if state == "Active" else "state-prog"
            html += f'<tr><td>State</td><td><span class="{cls}">{state}</span></td></tr>'

        address = site_info.get("address", "")
        if address:
            html += f'<tr><td>Address</td><td>{address}</td></tr>'

        ptp = site_info.get("ptp_capable", None)
        if ptp is not None:
            html += f'<tr><td>PTP</td><td>{"Yes" if ptp else "No"}</td></tr>'

        html += '</table>'

        # Resource availability
        if self._resources and site_name in self._sites_data:
            html += '<div class="section"><h4>Resources (Available / Capacity)</h4><table>'
            try:
                cores_a = self._resources.get_core_available(site_name)
                cores_c = self._resources.get_core_capacity(site_name)
                ram_a = self._resources.get_ram_available(site_name)
                ram_c = self._resources.get_ram_capacity(site_name)
                disk_a = self._resources.get_disk_available(site_name)
                disk_c = self._resources.get_disk_capacity(site_name)

                pct_cores = int(100 * cores_a / cores_c) if cores_c else 0
                pct_ram = int(100 * ram_a / ram_c) if ram_c else 0
                pct_disk = int(100 * disk_a / disk_c) if disk_c else 0

                html += (
                    f'<tr><td>Cores</td>'
                    f'<td>{cores_a} / {cores_c} ({pct_cores}%)</td></tr>'
                )
                html += (
                    f'<tr><td>RAM</td>'
                    f'<td>{ram_a} / {ram_c} GB ({pct_ram}%)</td></tr>'
                )
                html += (
                    f'<tr><td>Disk</td>'
                    f'<td>{disk_a} / {disk_c} GB ({pct_disk}%)</td></tr>'
                )
            except Exception:
                pass
            html += '</table></div>'

            # Component availability
            components = site_info.get("components", {})
            if components:
                cmp_items = ""
                for cmp_name, cmp_data in sorted(components.items()):
                    avail = cmp_data.get("available", 0)
                    cap = cmp_data.get("capacity", 0)
                    if cap > 0:
                        cmp_items += (
                            f'<div class="cmp-item">'
                            f'{cmp_name}: {avail} / {cap}</div>'
                        )
                if cmp_items:
                    html += (
                        f'<div class="section">'
                        f'<h4>Components (Available / Capacity)</h4>'
                        f'{cmp_items}</div>'
                    )

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

        if nodes_here:
            html += '<div class="section"><h4>Nodes at Site</h4>'
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

    def _show_link_detail(self, link_data: dict) -> None:
        """Show link properties in the detail panel."""
        name = link_data.get("name", "?")
        sites = link_data.get("sites", ())
        layer = link_data.get("layer", "?")
        bw_cap = link_data.get("bandwidth", "?")
        bw_avail = link_data.get("available_bandwidth", "?")
        bw_alloc = link_data.get("allocated_bandwidth", "?")

        sites_str = " ↔ ".join(str(s) for s in sites) if sites else "?"

        html = (
            f'{self._detail.PANEL_STYLE}'
            f'<div class="fabvis-detail">'
            f'<h3>Link</h3>'
            f'<table>'
            f'<tr><td>Name</td><td><small>{name}</small></td></tr>'
            f'<tr><td>Sites</td><td>{sites_str}</td></tr>'
            f'<tr><td>Layer</td><td>{layer}</td></tr>'
            f'<tr><td>Capacity</td><td>{bw_cap} Gbps</td></tr>'
            f'<tr><td>Available</td><td>{bw_avail} Gbps</td></tr>'
            f'<tr><td>Allocated</td><td>{bw_alloc} Gbps</td></tr>'
            f'</table>'
        )

        # Show utilization bar
        try:
            cap = float(bw_cap)
            avail = float(bw_avail)
            if cap > 0:
                pct_used = int(100 * (cap - avail) / cap)
                bar_color = FABRIC_SUCCESS if pct_used < 70 else (
                    FABRIC_WARNING if pct_used < 90 else "#b00020"
                )
                html += (
                    f'<div class="section"><h4>Utilization</h4>'
                    f'<div style="background:rgba(0,0,0,0.06); border-radius:6px; '
                    f'height:14px; overflow:hidden; margin:4px 0;">'
                    f'<div style="background:{bar_color}; width:{pct_used}%; '
                    f'height:100%; border-radius:6px; '
                    f'transition:width 0.3s ease;"></div></div>'
                    f'<small>{pct_used}% used</small></div>'
                )
        except (ValueError, TypeError):
            pass

        html += '</div>'
        self._detail.widget.value = html

    # ----------------------------------------------------------------
    # Drawing
    # ----------------------------------------------------------------

    def _draw_sites(self) -> None:
        """Draw all FABRIC sites as circle markers on the map.

        Uses live data from fablib resources if available, falling back
        to the static SITE_LOCATIONS dict.
        """
        self._sites_layer.clear_layers()

        # Build the set of sites to draw — prefer live data, fall back to static
        sites_to_draw: dict = {}
        if self._resources:
            for name in self._resources.get_site_names():
                try:
                    lat, lon = self._resources.get_location_lat_long(name)
                    if lat and lon:
                        sites_to_draw[name] = (lat, self._normalize_lon(lon))
                        continue
                except Exception:
                    pass
                # Fall back to static
                loc = SITE_LOCATIONS.get(name)
                if loc:
                    sites_to_draw[name] = loc
        else:
            sites_to_draw = dict(SITE_LOCATIONS)

        for site_name, (lat, lon) in sites_to_draw.items():
            # Color by site state if available
            site_info = self._sites_data.get(site_name, {})
            state = site_info.get("state", "")
            if state == "Active":
                fill_color = FABRIC_PRIMARY
            elif state in ("Maintenance", "PreMaintenance"):
                fill_color = FABRIC_WARNING
            else:
                fill_color = FABRIC_PRIMARY

            marker = CircleMarker()
            marker.location = (lat, lon)
            marker.radius = 7
            marker.color = FABRIC_PRIMARY_DARK
            marker.fill_color = fill_color
            marker.fill_opacity = 0.5
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

    def _draw_infra_links(self) -> None:
        """Draw infrastructure links between sites as polylines."""
        self._infra_links_layer.clear_layers()

        if not self._links_data:
            return

        # Build location lookup — prefer live, fall back to static
        loc_lookup = {}
        if self._resources:
            for name in self._resources.get_site_names():
                try:
                    lat, lon = self._resources.get_location_lat_long(name)
                    if lat and lon:
                        loc_lookup[name] = (lat, self._normalize_lon(lon))
                        continue
                except Exception:
                    pass
                loc = SITE_LOCATIONS.get(name)
                if loc:
                    loc_lookup[name] = loc
        else:
            loc_lookup = dict(SITE_LOCATIONS)

        for link in self._links_data:
            sites = link.get("sites", ())
            if not sites or len(sites) < 2:
                continue

            site_a, site_b = str(sites[0]), str(sites[1])
            loc_a = loc_lookup.get(site_a)
            loc_b = loc_lookup.get(site_b)
            if loc_a is None or loc_b is None:
                continue

            # Color by utilization
            try:
                cap = float(link.get("bandwidth", 0))
                avail = float(link.get("available_bandwidth", 0))
                pct_used = (cap - avail) / cap if cap > 0 else 0
            except (ValueError, TypeError):
                pct_used = 0

            if pct_used > 0.9:
                line_color = "#b00020"
            elif pct_used > 0.7:
                line_color = FABRIC_WARNING
            else:
                line_color = "rgba(87,152,188,0.45)"

            polyline = Polyline(
                locations=[loc_a, loc_b],
                color=line_color,
                weight=2,
                opacity=0.6,
                dash_array="6 4",
            )

            polyline.on_click(
                functools.partial(self._on_link_click, link_data=link)
            )
            self._infra_links_layer.add_layer(polyline)

    def _render_slices(self) -> None:
        """Render loaded slices on the map — nodes as markers, networks as paths."""
        self._slices_layer.clear_layers()
        self._slice_links_layer.clear_layers()
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
                marker.radius = 11
                marker.color = FABRIC_PRIMARY_DARK
                marker.fill_color = state_color
                marker.fill_opacity = 0.8
                marker.weight = 2

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
                    dash_array=[1, 12],
                    delay=1200,
                    color="rgba(117,144,186,0.5)",
                    pulse_color=path_color,
                    paused=False,
                    hardwareAccelerated=True,
                    weight=3,
                    opacity=0.75,
                )

                net_name = self._safe_get(net, "get_name", "?")
                ant_path.on_click(
                    functools.partial(self._on_path_click, net_obj=net)
                )
                self._slice_links_layer.add_layer(ant_path)

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
    def _normalize_lon(lon: float) -> float:
        """Normalize longitude for a US-centered map view.

        Sites east of 100°E (e.g. Japan ~140) are shifted by -360
        so they appear to the left of the Americas. European sites
        (0-100°E) keep their positive longitude so they appear to
        the right of the US.
        """
        if lon > 100:
            return lon - 360
        return lon

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
