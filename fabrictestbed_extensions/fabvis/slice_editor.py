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

"""Interactive FABRIC slice editor — build and modify slices visually.

Extends the SliceVisualizer with editing capabilities: add/remove/configure
nodes, components, and networks, then submit or modify the slice.
"""

import logging
import select
import threading
from typing import Optional

import ipycytoscape as cy
import ipywidgets as widgets
from IPython.display import display

from .detail_panel import DetailPanel
from .graph_builder import GraphBuilder
from .layouts import AVAILABLE_LAYOUTS, DEFAULT_LAYOUT, get_layout
from .splitter import create_h_splitter, create_v_splitter
from .terminal_widget import XtermWidget
from .styles import (
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_DANGER,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FABRIC_PRIMARY_LIGHT,
    FABRIC_SUCCESS,
    FABRIC_WARNING,
    FONT_IMPORT_CSS,
    SITE_LOCATIONS,
    WIDGET_SOFT_CSS,
    build_stylesheet,
    get_logo_data_url,
)

logger = logging.getLogger(__name__)

# Available FABRIC sites (sorted)
FABRIC_SITES = sorted(SITE_LOCATIONS.keys())

# Component models users can add
COMPONENT_MODELS = [
    "NIC_Basic",
    "NIC_ConnectX_5",
    "NIC_ConnectX_6",
    "NIC_ConnectX_7_100",
    "NIC_ConnectX_7_400",
    "GPU_TeslaT4",
    "GPU_RTX6000",
    "GPU_A30",
    "GPU_A40",
    "FPGA_Xilinx_U280",
    "NVME_P4510",
]

# Network types
L2_NETWORK_TYPES = ["L2Bridge", "L2STS", "L2PTP"]
L3_NETWORK_TYPES = ["IPv4", "IPv6", "IPv4Ext", "IPv6Ext"]

# Common OS images
DEFAULT_IMAGES = [
    "default_rocky_8",
    "default_rocky_9",
    "default_ubuntu_20",
    "default_ubuntu_22",
    "default_ubuntu_24",
    "default_debian_11",
    "default_debian_12",
    "default_centos_9",
    "default_fedora_39",
]


class SliceEditor:
    """Interactive FABRIC slice editor with visual topology.

    Usage:
        from fabrictestbed_extensions.fablib.fablib import FablibManager
        from fabrictestbed_extensions.fabvis import SliceEditor

        fablib = FablibManager()

        # Create a new slice:
        editor = SliceEditor(fablib)
        editor.new_slice("my_experiment")
        editor.show()

        # Edit an existing slice:
        editor = SliceEditor(fablib)
        editor.load_slice("my_existing_slice")
        editor.show()
    """

    def __init__(self, fablib_manager):
        """Initialize with a FablibManager instance.

        Args:
            fablib_manager: An initialized FablibManager from fablib.
        """
        self._fablib = fablib_manager
        self._builder = GraphBuilder()
        self._detail = DetailPanel()
        self._slice = None
        self._slice_name = None
        self._is_new = False  # True = not yet submitted
        self._current_layout = DEFAULT_LAYOUT
        self._selected_node_name = None  # Currently selected node for editing

        # Track the currently selected (clicked) element for delete
        self._selected_element = None   # (element_type, name, parent_name)
        self._selected_node_obj = None  # FABlib Node object for terminal

        self._build_widgets()

    def new_slice(self, name: str) -> None:
        """Create a new (empty) slice for editing.

        Args:
            name: Name for the new slice.
        """
        self._slice = self._fablib.new_slice(name=name)
        self._slice_name = name
        self._is_new = True
        self._render_graph()
        self._set_status(f"New slice: {name}")
        self._update_title()

    def load_slice(self, name: str) -> None:
        """Load an existing slice for editing.

        Args:
            name: Name of the slice to load.
        """
        try:
            self._slice = self._fablib.get_slice(name)
            self._slice_name = name
            self._is_new = False
            self._render_graph()
            self._set_status(f"Loaded: {name}")
            self._update_title()
        except Exception as e:
            self._set_status(f"Error loading slice: {e}")
            logger.error(f"Failed to load slice '{name}': {e}")

    @classmethod
    def edit_slice(cls, fablib_manager, slice_name: str):
        """Create editor and load an existing slice.

        Args:
            fablib_manager: FablibManager instance.
            slice_name: Name of slice to edit.

        Returns:
            The SliceEditor instance (already displayed).
        """
        editor = cls(fablib_manager)
        editor.load_slice(slice_name)
        editor.show()
        return editor

    @classmethod
    def create_slice(cls, fablib_manager, slice_name: str):
        """Create editor with a new empty slice.

        Args:
            fablib_manager: FablibManager instance.
            slice_name: Name for the new slice.

        Returns:
            The SliceEditor instance (already displayed).
        """
        editor = cls(fablib_manager)
        editor.new_slice(slice_name)
        editor.show()
        return editor

    def show(self) -> None:
        """Display the editor in the notebook."""
        display(self._container)

    def get_slice(self):
        """Return the underlying FABlib Slice object.

        Returns:
            The Slice object being edited.
        """
        return self._slice

    # ----------------------------------------------------------------
    # Widget construction
    # ----------------------------------------------------------------

    def _build_widgets(self) -> None:
        """Construct the full editor UI."""

        # ── Title bar ──
        logo_url = get_logo_data_url()
        logo_html = (
            f'<img src="{logo_url}" '
            f'style="height:28px; margin-right:12px; vertical-align:middle;" '
            f'alt="FABRIC">'
        ) if logo_url else ""

        self._title_widget = widgets.HTML(
            value=self._build_title_html(logo_html, "Slice Editor"),
            layout=widgets.Layout(width="100%"),
        )
        self._logo_html = logo_html

        # ── Toolbar ──
        self._build_toolbar()

        # ── Editor panel (left side, replaces detail panel for editing) ──
        self._build_editor_panel()

        # ── Cytoscape canvas ──
        self._cytoscape = cy.CytoscapeWidget(
            layout=widgets.Layout(flex="1", min_height="200px"),
        )
        self._cytoscape.set_style(build_stylesheet())
        layout_config = get_layout(self._current_layout)
        self._cytoscape.set_layout(**layout_config)
        self._cytoscape.on("node", "click", self._on_node_click)
        self._cytoscape.on("edge", "click", self._on_edge_click)

        # ── Terminal panel (below cytoscape, initially hidden) ──
        self._build_terminal_panel()

        self._terminal_splitter = create_v_splitter(resize_side="next")
        self._terminal_splitter.layout.display = "none"

        self._canvas_box = widgets.VBox(
            [self._cytoscape, self._terminal_splitter, self._terminal_panel],
            layout=widgets.Layout(
                flex="1",
                min_width="0",
                height="650px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                overflow="hidden",
            ),
        )

        # ── Right side: detail panel ──

        # Detail panel toggle button
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
                width="20%",
                min_width="0",
                height="650px",
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
                height="650px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                align_items="center",
                padding="6px 0",
                display="none",
            ),
        )

        # ── Editor panel (left side) ──

        # Editor panel toggle button
        self._editor_toggle = widgets.Button(
            description="",
            icon="angle-left",
            tooltip="Collapse Editor panel",
            layout=widgets.Layout(width="24px", height="20px",
                                  padding="0px", margin="0px"),
        )
        self._editor_toggle.on_click(self._toggle_editor_panel)

        editor_header = widgets.HBox(
            [
                widgets.HTML(
                    value=(
                        f'{FONT_IMPORT_CSS}'
                        f'<b style="color:{FABRIC_PRIMARY_DARK}; font-size:13px; '
                        f'font-family:{FABRIC_BODY_FONT};">Editor</b>'
                    ),
                ),
                self._editor_toggle,
            ],
            layout=widgets.Layout(
                background=FABRIC_LIGHT,
                padding="8px 12px",
                border_bottom=f"1.5px solid rgba(255,133,66,0.4)",
                border_radius="8px 8px 0 0",
                justify_content="space-between",
                align_items="center",
            ),
        )

        self._editor_box = widgets.VBox(
            [editor_header, self._editor_tabs],
            layout=widgets.Layout(
                width="25%",
                min_width="0",
                height="650px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                overflow_y="auto",
                overflow_x="hidden",
            ),
        )
        self._editor_visible = True

        # Collapsed editor strip (shown when panel is hidden)
        self._editor_expand_btn = widgets.Button(
            description="",
            icon="angle-right",
            tooltip="Expand Editor panel",
            layout=widgets.Layout(width="24px", height="24px",
                                  padding="0px", margin="0px"),
        )
        self._editor_expand_btn.on_click(self._toggle_editor_panel)

        self._editor_strip = widgets.VBox(
            [self._editor_expand_btn],
            layout=widgets.Layout(
                width="28px",
                height="650px",
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="8px",
                align_items="center",
                padding="6px 0",
                display="none",
            ),
        )

        self._editor_splitter = create_h_splitter(resize_side="prev")
        self._detail_splitter = create_h_splitter(resize_side="next")

        main_area = widgets.HBox(
            [self._editor_strip, self._editor_box,
             self._editor_splitter, self._canvas_box,
             self._detail_splitter,
             self._detail_box, self._detail_strip],
            layout=widgets.Layout(gap="0px"),
        )

        # ── Bottom bar ──
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
            layout=widgets.Layout(flex="1"),
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

        # Inject soft button/input CSS
        css_widget = widgets.HTML(value=WIDGET_SOFT_CSS)

        # ── Main container ──
        self._container = widgets.VBox(
            [css_widget, self._title_widget, self._toolbar, main_area, bottom_bar],
            layout=widgets.Layout(
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="10px",
                box_shadow="0 2px 12px rgba(0,0,0,0.06)",
                overflow="hidden",
            ),
        )
        self._container.add_class("fabvis-soft")

    def _build_title_html(self, logo_html: str, subtitle: str) -> str:
        name = self._slice_name or "No Slice"
        return (
            f'{FONT_IMPORT_CSS}'
            f'<div style="background:linear-gradient(135deg, {FABRIC_PRIMARY_DARK}, {FABRIC_PRIMARY}); '
            f'color:white; padding:10px 16px; font-size:16px; font-weight:600; '
            f'letter-spacing:0.5px; border-radius:8px 8px 0 0; '
            f'font-family:{FABRIC_BODY_FONT}; '
            f'display:flex; align-items:center; justify-content:space-between;">'
            f'<span>{logo_html}<span>{subtitle}</span></span>'
            f'<span style="font-size:13px; opacity:0.9;">{name}</span></div>'
        )

    def _update_title(self) -> None:
        mode = "New Slice" if self._is_new else "Edit Slice"
        self._title_widget.value = self._build_title_html(
            self._logo_html, f"Slice Editor — {mode}"
        )

    def _build_toolbar(self) -> None:
        """Build the toolbar with submit/modify/refresh/delete buttons."""
        self._submit_btn = widgets.Button(
            description="Submit",
            button_style="success",
            tooltip="Submit this slice to FABRIC",
            icon="check",
            layout=widgets.Layout(width="100px"),
        )
        self._submit_btn.on_click(self._on_submit_click)

        self._modify_btn = widgets.Button(
            description="Modify",
            button_style="warning",
            tooltip="Submit modifications to FABRIC",
            icon="pencil",
            layout=widgets.Layout(width="100px"),
        )
        self._modify_btn.on_click(self._on_modify_click)

        self._refresh_btn = widgets.Button(
            description="Refresh",
            button_style="",
            tooltip="Re-fetch slice state from FABRIC",
            icon="refresh",
            layout=widgets.Layout(width="100px"),
        )
        self._refresh_btn.on_click(self._on_refresh_click)

        self._delete_slice_btn = widgets.Button(
            description="Delete Slice",
            button_style="danger",
            tooltip="Delete this slice from FABRIC",
            icon="trash",
            layout=widgets.Layout(width="120px"),
        )
        self._delete_slice_btn.on_click(self._on_delete_slice_click)

        self._delete_selected_btn = widgets.Button(
            description="Delete",
            button_style="danger",
            tooltip="Delete the selected element",
            icon="trash",
            disabled=True,
            layout=widgets.Layout(width="100px"),
        )
        self._delete_selected_btn.on_click(self._on_delete_selected_click)

        self._terminal_btn = widgets.Button(
            description="Terminal",
            button_style="",
            tooltip="Open SSH terminal to selected node",
            icon="terminal",
            disabled=True,
            layout=widgets.Layout(width="110px"),
        )
        self._terminal_btn.on_click(self._on_terminal_click)

        # Confirmation area for destructive actions
        self._confirm_area = widgets.HBox(
            [],
            layout=widgets.Layout(gap="4px"),
        )

        self._toolbar = widgets.HBox(
            [self._submit_btn, self._modify_btn, self._refresh_btn,
             self._terminal_btn, self._delete_selected_btn,
             self._delete_slice_btn, self._confirm_area],
            layout=widgets.Layout(
                padding="6px 12px",
                border_bottom=f"1px solid rgba(138,201,239,0.4)",
                background=FABRIC_LIGHT,
                align_items="center",
                gap="8px",
            ),
        )

    def _build_editor_panel(self) -> None:
        """Build the tabbed editor panel for adding/editing elements."""

        # ── Tab 1: Add Node ──
        self._node_name_input = widgets.Text(
            value="",
            placeholder="node1",
            description="Name:",
            layout=widgets.Layout(width="100%"),
        )
        self._node_site_dropdown = widgets.Dropdown(
            options=["(auto)"] + FABRIC_SITES,
            value="(auto)",
            description="Site:",
            layout=widgets.Layout(width="100%"),
        )
        self._node_cores_input = widgets.IntSlider(
            value=2, min=1, max=64, step=1,
            description="Cores:",
            layout=widgets.Layout(width="100%"),
        )
        self._node_ram_input = widgets.IntSlider(
            value=8, min=2, max=256, step=2,
            description="RAM (GB):",
            layout=widgets.Layout(width="100%"),
        )
        self._node_disk_input = widgets.IntSlider(
            value=10, min=10, max=500, step=10,
            description="Disk (GB):",
            layout=widgets.Layout(width="100%"),
        )
        self._node_image_input = widgets.Combobox(
            options=DEFAULT_IMAGES,
            value="default_rocky_8",
            description="Image:",
            ensure_option=False,
            layout=widgets.Layout(width="100%"),
        )

        self._add_node_btn = widgets.Button(
            description="Add Node",
            button_style="primary",
            icon="plus",
            layout=widgets.Layout(width="100%"),
        )
        self._add_node_btn.on_click(self._on_add_node)

        node_tab = widgets.VBox(
            [
                self._node_name_input,
                self._node_site_dropdown,
                self._node_cores_input,
                self._node_ram_input,
                self._node_disk_input,
                self._node_image_input,
                self._add_node_btn,
            ],
            layout=widgets.Layout(padding="8px", gap="4px"),
        )

        # ── Tab 2: Add Component ──
        self._cmp_node_dropdown = widgets.Dropdown(
            options=[],
            description="To Node:",
            layout=widgets.Layout(width="100%"),
        )
        self._cmp_model_dropdown = widgets.Dropdown(
            options=COMPONENT_MODELS,
            value="NIC_Basic",
            description="Model:",
            layout=widgets.Layout(width="100%"),
        )
        self._cmp_name_input = widgets.Text(
            value="",
            placeholder="(auto)",
            description="Name:",
            layout=widgets.Layout(width="100%"),
        )

        self._add_cmp_btn = widgets.Button(
            description="Add Component",
            button_style="primary",
            icon="plus",
            layout=widgets.Layout(width="100%"),
        )
        self._add_cmp_btn.on_click(self._on_add_component)

        cmp_tab = widgets.VBox(
            [
                self._cmp_node_dropdown,
                self._cmp_model_dropdown,
                self._cmp_name_input,
                self._add_cmp_btn,
            ],
            layout=widgets.Layout(padding="8px", gap="4px"),
        )

        # ── Tab 3: Add Network ──
        self._net_name_input = widgets.Text(
            value="",
            placeholder="net1",
            description="Name:",
            layout=widgets.Layout(width="100%"),
        )
        self._net_layer_toggle = widgets.ToggleButtons(
            options=["L2", "L3"],
            value="L2",
            description="Layer:",
            layout=widgets.Layout(width="100%"),
        )
        self._net_layer_toggle.observe(self._on_net_layer_change, names="value")

        self._net_type_dropdown = widgets.Dropdown(
            options=L2_NETWORK_TYPES,
            description="Type:",
            layout=widgets.Layout(width="100%"),
        )
        self._net_iface_selector = widgets.SelectMultiple(
            options=[],
            description="Interfaces:",
            layout=widgets.Layout(width="100%", height="100px"),
        )

        self._add_net_btn = widgets.Button(
            description="Add Network",
            button_style="primary",
            icon="plus",
            layout=widgets.Layout(width="100%"),
        )
        self._add_net_btn.on_click(self._on_add_network)

        net_tab = widgets.VBox(
            [
                self._net_name_input,
                self._net_layer_toggle,
                self._net_type_dropdown,
                self._net_iface_selector,
                self._add_net_btn,
            ],
            layout=widgets.Layout(padding="8px", gap="4px"),
        )

        # ── Tab 4: Remove Elements ──
        self._remove_node_dropdown = widgets.Dropdown(
            options=[],
            description="Node:",
            layout=widgets.Layout(width="100%"),
        )
        self._remove_node_btn = widgets.Button(
            description="Remove Node",
            button_style="danger",
            icon="trash",
            layout=widgets.Layout(width="100%"),
        )
        self._remove_node_btn.on_click(self._on_remove_node)

        self._remove_net_dropdown = widgets.Dropdown(
            options=[],
            description="Network:",
            layout=widgets.Layout(width="100%"),
        )
        self._remove_net_btn = widgets.Button(
            description="Remove Network",
            button_style="danger",
            icon="trash",
            layout=widgets.Layout(width="100%"),
        )
        self._remove_net_btn.on_click(self._on_remove_network)

        self._remove_cmp_dropdown = widgets.Dropdown(
            options=[],
            description="Component:",
            layout=widgets.Layout(width="100%"),
        )
        self._remove_cmp_btn = widgets.Button(
            description="Remove Component",
            button_style="danger",
            icon="trash",
            layout=widgets.Layout(width="100%"),
        )
        self._remove_cmp_btn.on_click(self._on_remove_component)

        remove_tab = widgets.VBox(
            [
                widgets.HTML(
                    f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:11px; '
                    f'color:{FABRIC_DARK}; padding:4px 0;"><b>Remove Node</b></div>'
                ),
                self._remove_node_dropdown,
                self._remove_node_btn,
                widgets.HTML(
                    f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:11px; '
                    f'color:{FABRIC_DARK}; padding:8px 0 4px 0; '
                    f'border-top:1px solid rgba(138,201,239,0.3);"><b>Remove Network</b></div>'
                ),
                self._remove_net_dropdown,
                self._remove_net_btn,
                widgets.HTML(
                    f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:11px; '
                    f'color:{FABRIC_DARK}; padding:8px 0 4px 0; '
                    f'border-top:1px solid rgba(138,201,239,0.3);"><b>Remove Component</b></div>'
                ),
                self._remove_cmp_dropdown,
                self._remove_cmp_btn,
            ],
            layout=widgets.Layout(padding="8px", gap="4px"),
        )

        # ── Tab 5: Configure Node ──
        self._cfg_node_dropdown = widgets.Dropdown(
            options=[],
            description="Node:",
            layout=widgets.Layout(width="100%"),
        )
        self._cfg_node_dropdown.observe(self._on_cfg_node_change, names="value")

        self._cfg_site_dropdown = widgets.Dropdown(
            options=["(keep)"] + FABRIC_SITES,
            value="(keep)",
            description="Site:",
            layout=widgets.Layout(width="100%"),
        )
        self._cfg_cores_input = widgets.IntSlider(
            value=2, min=1, max=64, step=1,
            description="Cores:",
            layout=widgets.Layout(width="100%"),
        )
        self._cfg_ram_input = widgets.IntSlider(
            value=8, min=2, max=256, step=2,
            description="RAM (GB):",
            layout=widgets.Layout(width="100%"),
        )
        self._cfg_disk_input = widgets.IntSlider(
            value=10, min=10, max=500, step=10,
            description="Disk (GB):",
            layout=widgets.Layout(width="100%"),
        )
        self._cfg_image_input = widgets.Combobox(
            options=DEFAULT_IMAGES,
            value="default_rocky_8",
            ensure_option=False,
            description="Image:",
            layout=widgets.Layout(width="100%"),
        )

        self._apply_cfg_btn = widgets.Button(
            description="Apply Changes",
            button_style="warning",
            icon="pencil",
            layout=widgets.Layout(width="100%"),
        )
        self._apply_cfg_btn.on_click(self._on_apply_node_config)

        config_tab = widgets.VBox(
            [
                self._cfg_node_dropdown,
                self._cfg_site_dropdown,
                self._cfg_cores_input,
                self._cfg_ram_input,
                self._cfg_disk_input,
                self._cfg_image_input,
                self._apply_cfg_btn,
            ],
            layout=widgets.Layout(padding="8px", gap="4px"),
        )

        # ── Assemble tabs ──
        self._editor_tabs = widgets.Tab(
            children=[node_tab, cmp_tab, net_tab, remove_tab, config_tab],
            layout=widgets.Layout(width="100%"),
        )
        self._editor_tabs.set_title(0, "Node")
        self._editor_tabs.set_title(1, "Component")
        self._editor_tabs.set_title(2, "Network")
        self._editor_tabs.set_title(3, "Remove")
        self._editor_tabs.set_title(4, "Configure")

    # ----------------------------------------------------------------
    # Terminal panel
    # ----------------------------------------------------------------

    def _build_terminal_panel(self) -> None:
        """Build the SSH terminal panel (hidden by default).

        Uses an embedded xterm.js terminal for a real terminal experience
        with inline typing, ANSI color support, and auto-scrolling.
        """
        self._terminal_node = None
        self._terminal_ssh_client = None
        self._terminal_bastion = None
        self._terminal_channel = None
        self._terminal_reader_thread = None
        self._terminal_stop = threading.Event()

        # Close button
        close_btn = widgets.Button(
            description="",
            icon="times",
            tooltip="Close terminal",
            layout=widgets.Layout(width="24px", height="20px",
                                  padding="0px", margin="0px"),
        )
        close_btn.on_click(self._on_terminal_close)

        self._terminal_title = widgets.HTML(
            value=self._terminal_title_html(""),
        )

        terminal_header = widgets.HBox(
            [self._terminal_title, close_btn],
            layout=widgets.Layout(
                background="#1e1e1e",
                padding="4px 10px",
                border_bottom="1px solid #333",
                justify_content="space-between",
                align_items="center",
            ),
        )

        # xterm.js terminal widget
        self._xterm = XtermWidget()
        self._xterm.on_data = self._on_terminal_data
        self._xterm.on_resize = self._on_terminal_resize

        self._terminal_panel = widgets.VBox(
            [terminal_header, self._xterm.widget],
            layout=widgets.Layout(
                width="100%",
                border_top=f"1px solid rgba(138,201,239,0.4)",
                display="none",
            ),
        )

    def _terminal_title_html(self, node_name: str) -> str:
        label = f"SSH: {node_name}" if node_name else "Terminal"
        return (
            f'<span style="color:#00ff41; font-family:\'Courier New\',monospace; '
            f'font-size:12px; font-weight:600;">'
            f'&#9638; {label}</span>'
        )

    def _term_write(self, text: str) -> None:
        """Write text to the xterm.js terminal (thread-safe)."""
        self._xterm.write(text)

    def _on_terminal_data(self, data: str) -> None:
        """Handle raw keystrokes from xterm.js — send to SSH channel."""
        if self._terminal_channel is None or self._terminal_channel.closed:
            return
        try:
            self._terminal_channel.send(data)
        except Exception as e:
            self._xterm.write(f"\r\n\x1b[31mSend failed: {e}\x1b[0m\r\n")

    def _on_terminal_resize(self, cols: int, rows: int) -> None:
        """Handle terminal resize — update SSH PTY size."""
        if self._terminal_channel is not None and not self._terminal_channel.closed:
            try:
                self._terminal_channel.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def _on_terminal_click(self, _btn) -> None:
        """Open the terminal panel and establish an SSH shell session."""
        node = self._selected_node_obj
        if node is None:
            return

        # Close any existing session first
        self._terminal_disconnect()

        node_name = self._safe_get(node, "get_name", "?")
        self._terminal_node = node
        self._terminal_title.value = self._terminal_title_html(node_name)
        self._xterm.clear()
        self._terminal_splitter.layout.display = None
        self._terminal_panel.layout.display = None

        self._term_write(f"Connecting to {node_name}...\r\n")

        # Connect in a background thread so the UI stays responsive
        thread = threading.Thread(
            target=self._terminal_connect, args=(node,), daemon=True
        )
        thread.start()

    def _terminal_connect(self, node) -> None:
        """Establish SSH connection through bastion and open interactive shell."""
        import paramiko

        try:
            fablib_manager = node.get_fablib_manager()
            management_ip = node.get_management_ip()

            bastion_username = fablib_manager.get_bastion_username()
            bastion_key_file = fablib_manager.get_bastion_key_location()
            node_username = node.username
            node_key_file = node.get_private_key_file()
            node_key_passphrase = node.get_private_key_passphrase()

            ip_type = node.validIPAddress(management_ip)
            src_addr = ("0.0.0.0", 22) if ip_type == "IPv4" else ("::", 22)
            dest_addr = (str(management_ip), 22)

            key = node.get_paramiko_key(
                private_key_file=node_key_file,
                get_private_key_passphrase=node_key_passphrase,
            )

            # Connect to bastion
            bastion = paramiko.SSHClient()
            bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            bastion.connect(
                fablib_manager.get_bastion_host(),
                username=bastion_username,
                key_filename=bastion_key_file,
            )

            bastion_transport = bastion.get_transport()
            bastion_channel = bastion_transport.open_channel(
                "direct-tcpip", dest_addr, src_addr
            )

            # Connect to node through bastion
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                management_ip,
                username=node_username,
                pkey=key,
                sock=bastion_channel,
            )

            # Open interactive shell with xterm emulation for full
            # ANSI support (colors, cursor movement, etc.)
            channel = client.invoke_shell(term="xterm-256color", width=120, height=40)
            channel.settimeout(0.0)

            self._terminal_ssh_client = client
            self._terminal_bastion = bastion
            self._terminal_channel = channel
            self._terminal_stop.clear()

            # Start reader thread
            self._terminal_reader_thread = threading.Thread(
                target=self._terminal_reader_loop, daemon=True
            )
            self._terminal_reader_thread.start()

        except Exception as e:
            self._term_write(f"SSH connection failed: {e}\n")

    def _terminal_reader_loop(self) -> None:
        """Background thread: read from SSH channel and display in HTML widget."""
        channel = self._terminal_channel
        if channel is None:
            return

        while not self._terminal_stop.is_set():
            try:
                ready, _, _ = select.select([channel], [], [], 0.3)
                if ready:
                    data = channel.recv(4096)
                    if not data:
                        self._term_write("\n[Connection closed]\n")
                        break
                    text = data.decode("utf-8", errors="replace")
                    self._term_write(text)
            except Exception:
                if not self._terminal_stop.is_set():
                    self._term_write("\n[Connection lost]\n")
                break

    def _on_terminal_close(self, _btn) -> None:
        """Close the terminal panel and disconnect SSH."""
        self._terminal_disconnect()
        self._terminal_splitter.layout.display = "none"
        self._terminal_panel.layout.display = "none"

    def _terminal_disconnect(self) -> None:
        """Tear down the SSH session cleanly."""
        self._terminal_stop.set()

        if self._terminal_channel is not None:
            try:
                self._terminal_channel.close()
            except Exception:
                pass
            self._terminal_channel = None

        if self._terminal_ssh_client is not None:
            try:
                self._terminal_ssh_client.close()
            except Exception:
                pass
            self._terminal_ssh_client = None

        if self._terminal_bastion is not None:
            try:
                self._terminal_bastion.close()
            except Exception:
                pass
            self._terminal_bastion = None

        self._terminal_node = None
        self._terminal_reader_thread = None

    # ----------------------------------------------------------------
    # Dropdown population
    # ----------------------------------------------------------------

    def _refresh_dropdowns(self) -> None:
        """Update all editor dropdowns from current slice state."""
        if self._slice is None:
            return

        # Node names
        node_names = []
        try:
            node_names = [n.get_name() for n in self._slice.get_nodes()]
        except Exception:
            pass

        self._cmp_node_dropdown.options = node_names
        self._remove_node_dropdown.options = node_names
        self._cfg_node_dropdown.options = node_names

        # Network names
        net_names = []
        try:
            net_names = [n.get_name() for n in self._slice.get_network_services()]
        except Exception:
            pass
        self._remove_net_dropdown.options = net_names

        # Component list (node:component format)
        cmp_items = []
        try:
            for node in self._slice.get_nodes():
                n_name = node.get_name()
                for cmp in node.get_components():
                    c_name = cmp.get_name()
                    cmp_items.append(f"{n_name}:{c_name}")
        except Exception:
            pass
        self._remove_cmp_dropdown.options = cmp_items

        # Available interfaces for network connections
        iface_items = []
        try:
            for node in self._slice.get_nodes():
                n_name = node.get_name()
                for cmp in node.get_components():
                    for iface in cmp.get_interfaces():
                        i_name = iface.get_name()
                        # Only show interfaces not already in a network
                        try:
                            net = iface.get_network()
                            if net is not None:
                                continue
                        except Exception:
                            pass
                        iface_items.append(i_name)
                # Also node-level interfaces
                for iface in node.get_interfaces():
                    i_name = iface.get_name()
                    if i_name not in [x for x in iface_items]:
                        try:
                            net = iface.get_network()
                            if net is not None:
                                continue
                        except Exception:
                            pass
                        iface_items.append(i_name)
        except Exception:
            pass
        self._net_iface_selector.options = iface_items

    # ----------------------------------------------------------------
    # Panel toggle handlers
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

    def _toggle_editor_panel(self, _btn) -> None:
        """Toggle the editor panel between expanded and collapsed."""
        self._editor_visible = not self._editor_visible
        if self._editor_visible:
            self._editor_box.layout.display = None
            self._editor_splitter.layout.display = None
            self._editor_strip.layout.display = "none"
            self._editor_toggle.icon = "angle-left"
            self._editor_toggle.tooltip = "Collapse Editor panel"
        else:
            self._editor_box.layout.display = "none"
            self._editor_splitter.layout.display = "none"
            self._editor_strip.layout.display = None
            self._editor_toggle.icon = "angle-right"
            self._editor_toggle.tooltip = "Expand Editor panel"

    # ----------------------------------------------------------------
    # Event handlers — editing
    # ----------------------------------------------------------------

    def _on_add_node(self, _btn) -> None:
        """Add a new node to the slice."""
        if self._slice is None:
            self._set_status("No slice loaded")
            return

        name = self._node_name_input.value.strip()
        if not name:
            self._set_status("Node name required")
            return

        site = self._node_site_dropdown.value
        if site == "(auto)":
            site = None

        cores = self._node_cores_input.value
        ram = self._node_ram_input.value
        disk = self._node_disk_input.value
        image = self._node_image_input.value.strip() or None

        try:
            kwargs = dict(name=name, cores=cores, ram=ram, disk=disk)
            if site:
                kwargs["site"] = site
            if image:
                kwargs["image"] = image

            node = self._slice.add_node(**kwargs)
            self._render_graph()
            self._set_status(f"Added node: {name}")
            self._node_name_input.value = ""
        except Exception as e:
            self._set_status(f"Error adding node: {e}")
            logger.error(f"Failed to add node '{name}': {e}")

    def _on_add_component(self, _btn) -> None:
        """Add a component to a node."""
        if self._slice is None:
            self._set_status("No slice loaded")
            return

        node_name = self._cmp_node_dropdown.value
        if not node_name:
            self._set_status("Select a node first")
            return

        model = self._cmp_model_dropdown.value
        cmp_name = self._cmp_name_input.value.strip() or None

        try:
            node = self._slice.get_node(node_name)
            kwargs = dict(model=model)
            if cmp_name:
                kwargs["name"] = cmp_name
            node.add_component(**kwargs)
            self._render_graph()
            self._set_status(f"Added {model} to {node_name}")
            self._cmp_name_input.value = ""
        except Exception as e:
            self._set_status(f"Error adding component: {e}")
            logger.error(f"Failed to add component: {e}")

    def _on_add_network(self, _btn) -> None:
        """Add a network service."""
        if self._slice is None:
            self._set_status("No slice loaded")
            return

        net_name = self._net_name_input.value.strip()
        if not net_name:
            self._set_status("Network name required")
            return

        layer = self._net_layer_toggle.value
        net_type = self._net_type_dropdown.value
        selected_ifaces = list(self._net_iface_selector.value)

        # Resolve interface objects
        iface_objs = []
        if selected_ifaces:
            try:
                for node in self._slice.get_nodes():
                    for cmp in node.get_components():
                        for iface in cmp.get_interfaces():
                            if iface.get_name() in selected_ifaces:
                                iface_objs.append(iface)
                    for iface in node.get_interfaces():
                        if iface.get_name() in selected_ifaces:
                            if iface not in iface_objs:
                                iface_objs.append(iface)
            except Exception as e:
                self._set_status(f"Error resolving interfaces: {e}")
                return

        try:
            if layer == "L2":
                net = self._slice.add_l2network(
                    name=net_name,
                    interfaces=iface_objs,
                    type=net_type if net_type != "L2Bridge" else None,
                )
            else:
                net = self._slice.add_l3network(
                    name=net_name,
                    interfaces=iface_objs,
                    type=net_type,
                )
            self._render_graph()
            self._set_status(f"Added network: {net_name} ({net_type})")
            self._net_name_input.value = ""
        except Exception as e:
            self._set_status(f"Error adding network: {e}")
            logger.error(f"Failed to add network '{net_name}': {e}")

    def _on_remove_node(self, _btn) -> None:
        """Remove a node from the slice."""
        if self._slice is None:
            return

        node_name = self._remove_node_dropdown.value
        if not node_name:
            self._set_status("Select a node to remove")
            return

        try:
            node = self._slice.get_node(node_name)
            node.delete()
            self._render_graph()
            self._set_status(f"Removed node: {node_name}")
        except Exception as e:
            self._set_status(f"Error removing node: {e}")
            logger.error(f"Failed to remove node '{node_name}': {e}")

    def _on_remove_network(self, _btn) -> None:
        """Remove a network from the slice."""
        if self._slice is None:
            return

        net_name = self._remove_net_dropdown.value
        if not net_name:
            self._set_status("Select a network to remove")
            return

        try:
            for net in self._slice.get_network_services():
                if net.get_name() == net_name:
                    net.delete()
                    break
            self._render_graph()
            self._set_status(f"Removed network: {net_name}")
        except Exception as e:
            self._set_status(f"Error removing network: {e}")
            logger.error(f"Failed to remove network '{net_name}': {e}")

    def _on_remove_component(self, _btn) -> None:
        """Remove a component from a node."""
        if self._slice is None:
            return

        selection = self._remove_cmp_dropdown.value
        if not selection:
            self._set_status("Select a component to remove")
            return

        try:
            node_name, cmp_name = selection.split(":", 1)
            node = self._slice.get_node(node_name)
            cmp = node.get_component(cmp_name)
            cmp.delete()
            self._render_graph()
            self._set_status(f"Removed component: {cmp_name} from {node_name}")
        except Exception as e:
            self._set_status(f"Error removing component: {e}")
            logger.error(f"Failed to remove component '{selection}': {e}")

    def _on_apply_node_config(self, _btn) -> None:
        """Apply configuration changes to a node."""
        if self._slice is None:
            return

        node_name = self._cfg_node_dropdown.value
        if not node_name:
            self._set_status("Select a node to configure")
            return

        try:
            node = self._slice.get_node(node_name)

            # Site
            site = self._cfg_site_dropdown.value
            if site != "(keep)":
                node.set_site(site)

            # Capacities
            node.set_capacities(
                cores=self._cfg_cores_input.value,
                ram=self._cfg_ram_input.value,
                disk=self._cfg_disk_input.value,
            )

            # Image
            image = self._cfg_image_input.value.strip()
            if image:
                node.set_image(image)

            self._render_graph()
            self._set_status(f"Updated node: {node_name}")
        except Exception as e:
            self._set_status(f"Error configuring node: {e}")
            logger.error(f"Failed to configure node '{node_name}': {e}")

    def _on_cfg_node_change(self, change) -> None:
        """When a node is selected in config tab, populate its current values."""
        node_name = change.get("new")
        if not node_name or self._slice is None:
            return

        try:
            node = self._slice.get_node(node_name)
            site = self._safe_get(node, "get_site")
            cores = self._safe_get(node, "get_cores", 2)
            ram = self._safe_get(node, "get_ram", 8)
            disk = self._safe_get(node, "get_disk", 10)
            image = self._safe_get(node, "get_image", "default_rocky_8")

            if site and site in FABRIC_SITES:
                self._cfg_site_dropdown.value = site
            else:
                self._cfg_site_dropdown.value = "(keep)"

            self._cfg_cores_input.value = int(cores) if cores else 2
            self._cfg_ram_input.value = int(ram) if ram else 8
            self._cfg_disk_input.value = int(disk) if disk else 10
            self._cfg_image_input.value = str(image) if image else "default_rocky_8"
        except Exception:
            pass

    def _on_net_layer_change(self, change) -> None:
        """Update network type options when layer toggle changes."""
        if change.get("new") == "L2":
            self._net_type_dropdown.options = L2_NETWORK_TYPES
        else:
            self._net_type_dropdown.options = L3_NETWORK_TYPES

    # ----------------------------------------------------------------
    # Event handlers — slice operations
    # ----------------------------------------------------------------

    def _on_submit_click(self, _btn) -> None:
        """Submit the slice to FABRIC."""
        if self._slice is None:
            self._set_status("No slice to submit")
            return

        self._request_confirmation(
            "Submit this slice to FABRIC?",
            self._do_submit,
        )

    def _do_submit(self) -> None:
        """Actually submit the slice."""
        self._set_status("Submitting slice...")
        self._submit_btn.disabled = True
        try:
            self._slice.submit(wait=False, progress=False)
            self._is_new = False
            self._set_status("Slice submitted! Waiting for provisioning...")
            self._update_title()
        except Exception as e:
            self._set_status(f"Submit failed: {e}")
            logger.error(f"Slice submit failed: {e}")
        finally:
            self._submit_btn.disabled = False

    def _on_modify_click(self, _btn) -> None:
        """Submit modifications to FABRIC."""
        if self._slice is None:
            self._set_status("No slice to modify")
            return

        if self._is_new:
            self._set_status("Use Submit for new slices")
            return

        self._request_confirmation(
            "Submit modifications to FABRIC?",
            self._do_modify,
        )

    def _do_modify(self) -> None:
        """Actually modify the slice."""
        self._set_status("Submitting modifications...")
        self._modify_btn.disabled = True
        try:
            self._slice.modify(wait=False, progress=False)
            self._set_status("Modifications submitted!")
        except Exception as e:
            self._set_status(f"Modify failed: {e}")
            logger.error(f"Slice modify failed: {e}")
        finally:
            self._modify_btn.disabled = False

    def _on_refresh_click(self, _btn) -> None:
        """Re-fetch slice data from FABRIC."""
        if self._slice is None:
            return
        self._set_status("Refreshing...")
        try:
            self._slice = self._fablib.get_slice(self._slice_name)
            self._render_graph()
            self._set_status(f"Refreshed: {self._slice_name}")
        except Exception as e:
            self._set_status(f"Refresh failed: {e}")
            logger.error(f"Slice refresh failed: {e}")

    def _on_delete_slice_click(self, _btn) -> None:
        """Delete the slice from FABRIC."""
        if self._slice is None:
            self._set_status("No slice to delete")
            return

        self._request_confirmation(
            f"DELETE slice '{self._slice_name}'? This cannot be undone!",
            self._do_delete_slice,
            danger=True,
        )

    def _do_delete_slice(self) -> None:
        """Actually delete the slice."""
        self._set_status("Deleting slice...")
        try:
            self._slice.delete()
            self._slice = None
            name = self._slice_name
            self._slice_name = None
            self._is_new = False
            self._builder.clear()
            self._cytoscape.graph.clear()
            self._detail.clear()
            self._refresh_dropdowns()
            self._update_title()
            self._set_status(f"Deleted slice: {name}")
        except Exception as e:
            self._set_status(f"Delete failed: {e}")
            logger.error(f"Slice delete failed: {e}")

    # ----------------------------------------------------------------
    # Confirmation dialog
    # ----------------------------------------------------------------

    def _request_confirmation(self, message: str, callback, danger: bool = False) -> None:
        """Show an inline confirmation prompt."""
        label = widgets.HTML(
            f'<span style="font-family:{FABRIC_BODY_FONT}; font-size:12px; '
            f'color:{FABRIC_DANGER if danger else FABRIC_DARK}; font-weight:600;">'
            f'{message}</span>'
        )

        yes_btn = widgets.Button(
            description="Confirm",
            button_style="danger" if danger else "success",
            layout=widgets.Layout(width="80px"),
        )
        no_btn = widgets.Button(
            description="Cancel",
            button_style="",
            layout=widgets.Layout(width="80px"),
        )

        def on_yes(_):
            self._confirm_area.children = []
            callback()

        def on_no(_):
            self._confirm_area.children = []
            self._set_status("Cancelled")

        yes_btn.on_click(on_yes)
        no_btn.on_click(on_no)

        self._confirm_area.children = [label, yes_btn, no_btn]

    # ----------------------------------------------------------------
    # Event handlers — visualization
    # ----------------------------------------------------------------

    def _on_node_click(self, node_data) -> None:
        """Handle click on a cytoscape node — show details + enable delete."""
        if not isinstance(node_data, dict):
            return

        data = node_data.get("data", node_data)
        cy_id = data.get("id", "")
        element_type = data.get("element_type", "")

        obj = self._builder.element_map.get(cy_id)
        if obj is None:
            self._detail.clear()
            self._clear_selection()
            return

        if element_type == "slice":
            self._detail.show_slice(obj)
            self._clear_selection()
        elif element_type == "node":
            self._detail.show_node(obj)
            node_name = self._safe_get(obj, "get_name", "?")
            self._select_element("node", node_name)
            self._selected_node_obj = obj
            self._terminal_btn.disabled = False
            self._terminal_btn.tooltip = f"Open SSH terminal to {node_name}"
        elif element_type == "component":
            self._detail.show_component(obj)
            cmp_name = self._safe_get(obj, "get_name", "?")
            node_name = "?"
            try:
                node_obj = obj.get_node()
                node_name = self._safe_get(node_obj, "get_name", "?")
                self._selected_node_obj = node_obj
                self._terminal_btn.disabled = False
                self._terminal_btn.tooltip = f"Open SSH terminal to {node_name}"
            except Exception:
                pass
            self._select_element("component", cmp_name, node_name)
        elif element_type in ("network", "network-l2", "network-l3"):
            self._detail.show_network(obj)
            net_name = self._safe_get(obj, "get_name", "?")
            self._select_element("network", net_name)
        elif element_type == "switch":
            self._detail.show_node(obj)
            self._clear_selection()
        elif element_type == "facility_port":
            self._detail.show_node(obj)
            self._clear_selection()
        else:
            self._detail.clear()
            self._clear_selection()

    def _on_edge_click(self, edge_data) -> None:
        """Handle click on a cytoscape edge."""
        if not isinstance(edge_data, dict):
            return

        data = edge_data.get("data", edge_data)
        cy_id = data.get("id", "")
        iface_key = cy_id.replace("edge:", "iface:", 1) if cy_id.startswith("edge:") else ""
        obj = self._builder.element_map.get(iface_key)

        if obj is not None:
            self._detail.show_interface(obj)
            # Allow deleting the network this interface belongs to
            try:
                net_obj = obj.get_network()
                if net_obj:
                    net_name = self._safe_get(net_obj, "get_name")
                    if net_name:
                        self._select_element("network", net_name)
                        return
            except Exception:
                pass
        else:
            self._detail.clear()
        self._clear_selection()

    def _select_element(self, elem_type: str, name: str, parent: str = None) -> None:
        """Mark an element as selected and enable the Delete button."""
        self._selected_element = (elem_type, name, parent)
        label = name if elem_type != "component" else f"{parent}/{name}"
        self._delete_selected_btn.description = f"Delete"
        self._delete_selected_btn.tooltip = f"Delete {elem_type}: {label}"
        self._delete_selected_btn.disabled = False

    def _clear_selection(self) -> None:
        """Clear element selection and disable the Delete/Terminal buttons."""
        self._selected_element = None
        self._selected_node_obj = None
        self._delete_selected_btn.description = "Delete"
        self._delete_selected_btn.tooltip = "Select an element to delete"
        self._delete_selected_btn.disabled = True
        self._terminal_btn.disabled = True
        self._terminal_btn.tooltip = "Open SSH terminal to selected node"

    # ----------------------------------------------------------------
    # Delete selected element
    # ----------------------------------------------------------------

    def _on_delete_selected_click(self, _btn) -> None:
        """Handle Delete button click — confirm then remove selected element."""
        if not self._selected_element:
            return
        elem_type, name, parent = self._selected_element

        if elem_type == "node":
            self._request_confirmation(
                f"Remove node '{name}'?",
                lambda: self._do_delete_node(name),
                danger=True,
            )
        elif elem_type == "component":
            self._request_confirmation(
                f"Remove '{name}' from '{parent}'?",
                lambda: self._do_delete_component(parent, name),
                danger=True,
            )
        elif elem_type == "network":
            self._request_confirmation(
                f"Remove network '{name}'?",
                lambda: self._do_delete_network(name),
                danger=True,
            )

    def _do_delete_node(self, node_name: str) -> None:
        try:
            node = self._slice.get_node(node_name)
            node.delete()
            self._render_graph()
            self._set_status(f"Removed node: {node_name}")
        except Exception as e:
            self._set_status(f"Error removing node: {e}")

    def _do_delete_component(self, node_name: str, cmp_name: str) -> None:
        try:
            node = self._slice.get_node(node_name)
            cmp = node.get_component(cmp_name)
            cmp.delete()
            self._render_graph()
            self._set_status(f"Removed {cmp_name} from {node_name}")
        except Exception as e:
            self._set_status(f"Error removing component: {e}")

    def _do_delete_network(self, net_name: str) -> None:
        try:
            for net in self._slice.get_network_services():
                if net.get_name() == net_name:
                    net.delete()
                    break
            self._render_graph()
            self._set_status(f"Removed network: {net_name}")
        except Exception as e:
            self._set_status(f"Error removing network: {e}")

    def _on_layout_change(self, change) -> None:
        self._current_layout = change["new"]
        layout_config = get_layout(change["new"])
        self._cytoscape.set_layout(**layout_config)

    def _on_fit_click(self, _btn) -> None:
        try:
            self._cytoscape.relayout()
        except Exception:
            pass

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------

    def _render_graph(self) -> None:
        """Build and display the cytoscape graph from the current slice."""
        self._builder.clear()

        if self._slice is not None:
            try:
                self._builder.add_slice(self._slice)
            except Exception as e:
                logger.error(f"Error building graph: {e}")

        graph_data = self._builder.build()

        self._cytoscape.graph.clear()
        if graph_data["nodes"] or graph_data["edges"]:
            self._cytoscape.graph.add_graph_from_json(graph_data)

        layout_config = get_layout(self._current_layout)
        self._cytoscape.set_layout(**layout_config)

        self._detail.clear()
        self._clear_selection()
        self._on_terminal_close(None)  # close terminal when slice changes
        self._refresh_dropdowns()

    def _get_cytoscape_positions(self) -> dict:
        """Extract current node positions from the cytoscape widget.

        Returns:
            Dict mapping cytoscape node IDs to (x, y) tuples.
            Positions are in cytoscape coordinate space.
        """
        positions = {}
        try:
            for node in self._cytoscape.graph.nodes:
                nid = node.data.get("id", "")
                pos = node.position
                if pos and "x" in pos and "y" in pos:
                    positions[nid] = (pos["x"], pos["y"])
        except Exception as e:
            logger.warning(f"Could not read cytoscape positions: {e}")
        return positions

    def _set_status(self, text: str) -> None:
        self._status_label.value = (
            f'<small style="font-family:{FABRIC_BODY_FONT}; '
            f'color:{FABRIC_DARK};">{text}</small>'
        )

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
