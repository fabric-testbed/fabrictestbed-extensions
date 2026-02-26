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
from .splitter import create_h_splitter
from .styles import (
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FABRIC_PRIMARY_LIGHT,
    FABRIC_WARNING,
    FONT_IMPORT_CSS,
    WIDGET_SOFT_CSS,
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

    def __init__(self, fablib_manager=None):
        """Initialize with an optional FablibManager instance.

        Args:
            fablib_manager: An initialized FablibManager from fablib.
                            Not required if using show_slice() or passing
                            slice objects directly.
        """
        self._fablib = fablib_manager
        self._builder = GraphBuilder()
        self._detail = DetailPanel()
        self._loaded_slices: dict = {}  # name -> Slice object
        self._current_layout = DEFAULT_LAYOUT
        self._picker_mode = fablib_manager is not None

        # Build widgets
        self._build_widgets()

    @classmethod
    def show_slice(cls, slice_obj, layout: str = None):
        """Display a single slice in a compact viewer (no slice picker).

        Args:
            slice_obj: A FABlib Slice object.
            layout: Optional layout name (default: dagre).

        Returns:
            The SliceVisualizer instance.
        """
        return cls.show_slices([slice_obj], layout=layout)

    @classmethod
    def show_slices(cls, slice_objs: list, layout: str = None):
        """Display one or more slices in a compact viewer (no slice picker).

        Args:
            slice_objs: List of FABlib Slice objects.
            layout: Optional layout name (default: dagre).

        Returns:
            The SliceVisualizer instance.
        """
        vis = cls()  # no fablib_manager → picker hidden
        for s in slice_objs:
            name = s.get_name() if hasattr(s, "get_name") else str(s)
            vis._loaded_slices[name] = s
        if layout:
            vis._current_layout = layout
        vis._render_graph()
        names = ", ".join(vis._loaded_slices.keys())
        vis._set_status(f"Showing: {names}")
        display(vis._container)
        return vis

    def show(self) -> None:
        """Display the full widget UI in the notebook."""
        if self._fablib and self._picker_mode:
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

    def to_image(self, **kwargs):
        """Render loaded slices as a static matplotlib Figure.

        Uses the current node positions from the cytoscape widget so
        the exported image matches the on-screen layout.

        Args:
            **kwargs: Passed to render_slice_graph() (figsize, dpi, title,
                      show_edge_labels).

        Returns:
            matplotlib Figure object.
        """
        from .image_export import render_slice_graph

        if not self._loaded_slices:
            raise ValueError("No slices loaded. Call load_slices() first.")
        positions = self._get_cytoscape_positions()
        return render_slice_graph(
            list(self._loaded_slices.values()),
            positions=positions, **kwargs,
        )

    def save_image(self, path: str, **kwargs) -> None:
        """Render loaded slices and save as an image file.

        Uses the current node positions from the cytoscape widget.

        Args:
            path: Output file path (png, pdf, svg).
            **kwargs: Passed to render_slice_graph().
        """
        from .image_export import render_slice_graph

        if not self._loaded_slices:
            raise ValueError("No slices loaded. Call load_slices() first.")
        positions = self._get_cytoscape_positions()
        fig = render_slice_graph(
            list(self._loaded_slices.values()), save=path,
            positions=positions, **kwargs,
        )
        import matplotlib.pyplot as plt
        plt.close(fig)

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
                border_bottom=f"1px solid rgba(138,201,239,0.4)",
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

        self._canvas_box = widgets.Box(
            [self._cytoscape],
            layout=widgets.Layout(
                flex="1",
                min_width="0",
                height="600px",
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
                min_width="0",
                height="600px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                overflow_y="auto",
                overflow_x="hidden",
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
                height="600px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                align_items="center",
                padding="6px 0",
                display="none",
            ),
        )

        self._detail_splitter = create_h_splitter(resize_side="next")

        main_area = widgets.HBox(
            [self._canvas_box, self._detail_splitter,
             self._detail_box, self._detail_strip],
            layout=widgets.Layout(gap="0px"),
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
                f'<span>Slice Visualizer</span></div>'
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
            self._detail_splitter.layout.display = None
            self._detail_strip.layout.display = "none"
            self._detail_toggle.icon = "angle-right"
            self._detail_toggle.tooltip = "Collapse Details panel"
        else:
            self._detail_box.layout.display = "none"
            self._detail_splitter.layout.display = "none"
            self._detail_strip.layout.display = None
            self._detail_toggle.icon = "angle-left"
            self._detail_toggle.tooltip = "Expand Details panel"

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

    def _get_cytoscape_positions(self) -> dict:
        """Extract current node positions from the cytoscape widget.

        Returns:
            Dict mapping cytoscape node IDs to (x, y) tuples.
        """
        positions = {}
        try:
            for node in self._cytoscape.graph.nodes:
                nid = node.data.get("id", "")
                pos = node.position
                if pos and "x" in pos and "y" in pos:
                    positions[nid] = (pos["x"], pos["y"])
        except Exception:
            pass
        return positions

    def _set_status(self, text: str) -> None:
        """Update the status label."""
        self._status_label.value = (
            f'<small style="font-family:{FABRIC_BODY_FONT}; '
            f'color:{FABRIC_DARK};">{text}</small>'
        )
