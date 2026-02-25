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

"""Main SliceVisualizer widget — orchestrates the full UI."""

import logging
from typing import Optional

import ipycytoscape as cy
import ipywidgets as widgets
from IPython.display import display

from .detail_panel import DetailPanel
from .graph_builder import GraphBuilder
from .layouts import AVAILABLE_LAYOUTS, DEFAULT_LAYOUT, get_layout
from .styles import (
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FABRIC_PRIMARY_LIGHT,
    FABRIC_WARNING,
    FONT_IMPORT_CSS,
    build_stylesheet,
    get_logo_data_url,
)

logger = logging.getLogger(__name__)


class SliceVisualizer:
    """Interactive FABRIC slice topology visualizer.

    Usage:
        from fabrictestbed_extensions.fablib.fablib import FablibManager
        from fabrictestbed_extensions.fabvis import SliceVisualizer

        fablib = FablibManager()
        vis = SliceVisualizer(fablib)
        vis.show()  # presents slice picker, user selects and clicks Load

        # Or load specific slices directly:
        vis = SliceVisualizer(fablib)
        vis.load_slices(["my_slice_1", "my_slice_2"])
        vis.show()
    """

    def __init__(self, fablib_manager):
        """Initialize with a FablibManager instance.

        Args:
            fablib_manager: An initialized FablibManager from fablib.
        """
        self._fablib = fablib_manager
        self._builder = GraphBuilder()
        self._detail = DetailPanel()
        self._loaded_slices: dict = {}  # name -> Slice object
        self._current_layout = DEFAULT_LAYOUT

        # Build widgets
        self._build_widgets()

    def show(self) -> None:
        """Display the full widget UI in the notebook."""
        self._refresh_slice_list()
        display(self._container)

    def load_slices(self, slice_names: list) -> None:
        """Load specific slices by name and render them.

        Args:
            slice_names: List of slice names to load and visualize.
        """
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

        self._render_graph()

    def refresh(self) -> None:
        """Re-fetch slice data from FABRIC and re-render."""
        if not self._loaded_slices:
            self._set_status("No slices loaded")
            return

        names = list(self._loaded_slices.keys())
        self.load_slices(names)

    def set_layout(self, name: str, **kwargs) -> None:
        """Change the graph layout algorithm.

        Args:
            name: Layout name (cola, dagre, breadthfirst, grid, concentric, cose).
            **kwargs: Additional layout parameters to override defaults.
        """
        self._current_layout = name
        layout_config = get_layout(name, **kwargs)
        self._cytoscape.set_layout(**layout_config)
        self._layout_dropdown.value = name

    # ----------------------------------------------------------------
    # Widget construction
    # ----------------------------------------------------------------

    def _build_widgets(self) -> None:
        """Construct all the ipywidgets that compose the UI."""

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

        # Cytoscape canvas
        self._cytoscape = cy.CytoscapeWidget()
        self._cytoscape.set_style(build_stylesheet())
        layout_config = get_layout(self._current_layout)
        self._cytoscape.set_layout(**layout_config)

        self._cytoscape.on("node", "click", self._on_node_click)
        self._cytoscape.on("edge", "click", self._on_edge_click)

        canvas_box = widgets.Box(
            [self._cytoscape],
            layout=widgets.Layout(
                width="75%",
                height="600px",
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
                height="600px",
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="4px",
                overflow_y="auto",
            ),
        )

        main_area = widgets.HBox(
            [canvas_box, detail_box],
            layout=widgets.Layout(gap="4px"),
        )

        # Bottom bar
        self._layout_dropdown = widgets.Dropdown(
            options=AVAILABLE_LAYOUTS,
            value=self._current_layout,
            description="Layout:",
            layout=widgets.Layout(width="180px"),
        )
        self._layout_dropdown.observe(self._on_layout_change, names="value")

        self._fit_btn = widgets.Button(
            description="Fit",
            tooltip="Zoom to fit all elements",
            layout=widgets.Layout(width="50px"),
        )
        self._fit_btn.on_click(self._on_fit_click)

        self._status_label = widgets.HTML(
            value="<i>Ready</i>",
            layout=widgets.Layout(width="300px"),
        )

        bottom_bar = widgets.HBox(
            [self._layout_dropdown, self._fit_btn, self._status_label],
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
                f'<span>Slice Visualizer</span></div>'
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
        """Handle Load button click."""
        selected = list(self._slice_selector.value)
        if not selected:
            self._set_status("No slices selected")
            return
        self._set_status("Loading...")
        self.load_slices(selected)

    def _on_refresh_click(self, _btn) -> None:
        """Handle Refresh button click."""
        self._set_status("Refreshing...")
        self.refresh()

    def _on_refresh_list_click(self, _btn) -> None:
        """Handle Refresh slice list button click."""
        self._refresh_slice_list()

    def _on_layout_change(self, change) -> None:
        """Handle layout dropdown change."""
        self.set_layout(change["new"])

    def _on_fit_click(self, _btn) -> None:
        """Handle Fit button click — zoom to fit."""
        # ipycytoscape doesn't expose fit() directly, but relayout achieves similar
        try:
            self._cytoscape.relayout()
        except Exception:
            pass

    def _on_node_click(self, node_data) -> None:
        """Handle click on a cytoscape node."""
        if not isinstance(node_data, dict):
            return

        data = node_data.get("data", node_data)
        cy_id = data.get("id", "")
        element_type = data.get("element_type", "")

        obj = self._builder.element_map.get(cy_id)
        if obj is None:
            self._detail.clear()
            return

        if element_type == "slice":
            self._detail.show_slice(obj)
        elif element_type == "node":
            self._detail.show_node(obj)
        elif element_type == "component":
            self._detail.show_component(obj)
        elif element_type in ("network", "network-l2", "network-l3"):
            self._detail.show_network(obj)
        elif element_type == "switch":
            self._detail.show_node(obj)  # switches share node-like properties
        elif element_type == "facility_port":
            # Facility ports have limited info; show what we can
            self._detail.show_node(obj)
        else:
            self._detail.clear()

    def _on_edge_click(self, edge_data) -> None:
        """Handle click on a cytoscape edge."""
        if not isinstance(edge_data, dict):
            return

        data = edge_data.get("data", edge_data)
        iface_name = data.get("iface_name", "")

        # Look up the interface object from element_map
        # Edge IDs are like "edge:slice_id:iface_name" but the iface is stored
        # under "iface:slice_id:iface_name"
        cy_id = data.get("id", "")
        iface_key = cy_id.replace("edge:", "iface:", 1) if cy_id.startswith("edge:") else ""
        obj = self._builder.element_map.get(iface_key)

        if obj is not None:
            self._detail.show_interface(obj)
        else:
            self._detail.clear()

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
                state = "?"
                try:
                    state = s.get_state()
                except Exception:
                    pass
                options.append(name)
            self._slice_selector.options = sorted(options)
            self._set_status(f"{len(options)} slices available")
        except Exception as e:
            self._set_status(f"Error listing slices: {e}")
            logger.error(f"Failed to list slices: {e}")

    def _render_graph(self) -> None:
        """Build and display the cytoscape graph from loaded slices."""
        self._builder.clear()

        for name, slice_obj in self._loaded_slices.items():
            try:
                self._builder.add_slice(slice_obj)
            except Exception as e:
                logger.error(f"Error building graph for slice '{name}': {e}")

        graph_data = self._builder.build()

        # Clear existing graph and load new data
        self._cytoscape.graph.clear()
        if graph_data["nodes"] or graph_data["edges"]:
            self._cytoscape.graph.add_graph_from_json(graph_data)

        # Apply layout
        layout_config = get_layout(self._current_layout)
        self._cytoscape.set_layout(**layout_config)

        self._detail.clear()

    def _set_status(self, text: str) -> None:
        """Update the status label."""
        self._status_label.value = (
            f'<small style="font-family:{FABRIC_BODY_FONT}; '
            f'color:{FABRIC_DARK};">{text}</small>'
        )
