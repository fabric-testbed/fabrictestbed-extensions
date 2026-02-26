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

"""FABRIC Visualization Suite — combines the slice editor and geographic
map viewer into a single interface with a mode selector.

Usage::

    from fabrictestbed_extensions.fabvis import FabVis

    fablib = FablibManager()

    # Full interactive GUI:
    fv = FabVis(fablib)
    fv.show()

    # Static image export (no GUI):
    from fabrictestbed_extensions.fabvis import render_slice_graph, render_slice_map
    fig = render_slice_graph(my_slice, save="topology.png")
    fig = render_slice_map(my_slice, save="geo.png")
"""

import logging
from typing import Optional

import ipywidgets as widgets
from IPython.display import display

from .styles import (
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FONT_IMPORT_CSS,
    WIDGET_SOFT_CSS,
    get_logo_data_url,
)

logger = logging.getLogger(__name__)

# View modes
_VIEW_EDITOR = "Editor"
_VIEW_GEO = "Geographic"


class FabVis:
    """FABRIC Visualization Suite.

    Combines the slice editor (Cytoscape graph + editing panels) and
    geographic map viewer into one widget. A single bottom bar provides
    slice selection, view switching, view-specific controls, and image
    export.

    Usage::

        from fabrictestbed_extensions.fabvis import FabVis

        fablib = FablibManager()
        fv = FabVis(fablib)
        fv.show()

        # Load slices:
        fv.load_slice("my_slice")

        # Switch modes:
        fv.set_view("Geographic")

        # Save images:
        fv.save_editor_image("topo.png")
        fv.save_geo_image("geo.png")
    """

    def __init__(self, fablib_manager=None):
        """Initialize with an optional FablibManager instance.

        Args:
            fablib_manager: An initialized FablibManager from fablib.
        """
        self._fablib = fablib_manager

        # Sub-tools (created lazily)
        self._geo_vis = None
        self._editor = None

        # Track which views have been initialized
        self._initialized = {
            _VIEW_EDITOR: False,
            _VIEW_GEO: False,
        }

        # Cached inner content (sub-tool containers without chrome)
        self._view_content = {}

        # View-specific bottom bar widgets (populated lazily)
        self._view_widgets = {
            _VIEW_EDITOR: [],
            _VIEW_GEO: [],
        }

        self._build_widgets()

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def show(self) -> None:
        """Display the unified visualizer in the notebook."""
        self._refresh_slice_list()
        self._ensure_view(_VIEW_EDITOR)
        self._switch_to_view(_VIEW_EDITOR)
        display(self._container)

    def load_slices(self, slice_names: list) -> None:
        """Load slices into both views.

        In the editor, loads the first slice. In geographic view, loads all.

        Args:
            slice_names: List of slice names to load.
        """
        if slice_names:
            self._ensure_view(_VIEW_EDITOR)
            self._editor.load_slice(slice_names[0])
        if self._initialized.get(_VIEW_GEO) and self._geo_vis:
            self._geo_vis.load_slices(slice_names)

    def load_slice(self, slice_name: str) -> None:
        """Load a slice into the editor view.

        Args:
            slice_name: Name of the slice to edit.
        """
        self._ensure_view(_VIEW_EDITOR)
        self._editor.load_slice(slice_name)

    def new_slice(self, slice_name: str) -> None:
        """Create a new empty slice in the editor view.

        Args:
            slice_name: Name for the new slice.
        """
        self._ensure_view(_VIEW_EDITOR)
        self._editor.new_slice(slice_name)

    def set_view(self, view_name: str) -> None:
        """Switch to a specific view.

        Args:
            view_name: One of "Editor" or "Geographic".
        """
        if view_name in (_VIEW_EDITOR, _VIEW_GEO):
            self._view_selector.value = view_name

    def save_editor_image(self, path: str, **kwargs) -> None:
        """Save the editor's slice as a topology image.

        Args:
            path: Output file path (png, pdf, svg).
            **kwargs: Passed to render_slice_graph().
        """
        self._ensure_view(_VIEW_EDITOR)
        if self._editor._slice is not None:
            from .image_export import render_slice_graph
            import matplotlib.pyplot as plt
            positions = self._editor._get_cytoscape_positions()
            fig = render_slice_graph(
                [self._editor._slice], save=path,
                positions=positions, **kwargs,
            )
            plt.close(fig)
        else:
            raise ValueError("No slice loaded in the editor.")

    def save_geo_image(self, path: str, **kwargs) -> None:
        """Save the geographic view as an image.

        Args:
            path: Output file path (png, pdf, svg).
            **kwargs: Passed to render_slice_map().
        """
        self._ensure_view(_VIEW_GEO)
        self._geo_vis.save_image(path, **kwargs)

    def get_geo_vis(self):
        """Return the underlying GeoVisualizer instance."""
        self._ensure_view(_VIEW_GEO)
        return self._geo_vis

    def get_editor(self):
        """Return the underlying SliceEditor instance."""
        self._ensure_view(_VIEW_EDITOR)
        return self._editor

    # ----------------------------------------------------------------
    # Widget construction
    # ----------------------------------------------------------------

    def _build_widgets(self) -> None:
        """Construct the unified UI shell."""

        # Logo
        logo_url = get_logo_data_url()
        self._logo_html = ""
        if logo_url:
            self._logo_html = (
                f'<img src="{logo_url}" '
                f'style="height:28px; margin-right:12px; vertical-align:middle;" '
                f'alt="FABRIC">'
            )

        # Title bar — updated dynamically to show the current mode
        self._title_widget = widgets.HTML(
            value=self._build_title(_VIEW_EDITOR),
        )

        # Content area — holds the active view's inner content
        self._content_area = widgets.VBox(
            [],
            layout=widgets.Layout(
                width="100%",
                min_height="600px",
            ),
        )

        # ── Bottom bar widgets ──

        # Slice selector
        self._slice_dropdown = widgets.Dropdown(
            options=[],
            value=None,
            description="Slice:",
            layout=widgets.Layout(width="220px"),
        )

        self._load_btn = widgets.Button(
            description="Load",
            button_style="primary",
            tooltip="Load the selected slice",
            layout=widgets.Layout(width="60px"),
        )
        self._load_btn.on_click(self._on_load_click)

        self._refresh_list_btn = widgets.Button(
            description="",
            button_style="",
            icon="refresh",
            tooltip="Refresh slice list from FABRIC",
            layout=widgets.Layout(width="32px"),
        )
        self._refresh_list_btn.on_click(self._on_refresh_list_click)

        # Separator
        self._sep1 = widgets.HTML(
            value=(
                f'<div style="width:1px; height:20px; '
                f'background:rgba(138,201,239,0.5);"></div>'
            ),
        )

        # View selector
        self._view_selector = widgets.Dropdown(
            options=[_VIEW_EDITOR, _VIEW_GEO],
            value=_VIEW_EDITOR,
            description="View:",
            layout=widgets.Layout(width="160px"),
        )
        self._view_selector.observe(self._on_view_change, names="value")

        # Separator
        self._sep2 = widgets.HTML(
            value=(
                f'<div style="width:1px; height:20px; '
                f'background:rgba(138,201,239,0.5);"></div>'
            ),
        )

        # View-specific controls placeholder — children swapped on view change
        self._view_controls = widgets.HBox(
            [],
            layout=widgets.Layout(gap="6px", align_items="center"),
        )

        # Separator
        self._sep3 = widgets.HTML(
            value=(
                f'<div style="width:1px; height:20px; '
                f'background:rgba(138,201,239,0.5);"></div>'
            ),
        )

        # Save controls
        self._save_path_input = widgets.Text(
            value="fabvis_export.png",
            placeholder="filename.png",
            description="",
            layout=widgets.Layout(width="150px"),
        )

        self._save_btn = widgets.Button(
            description="Save",
            button_style="",
            icon="camera",
            tooltip="Save the current view as an image",
            layout=widgets.Layout(width="70px"),
        )
        self._save_btn.on_click(self._on_save_click)

        self._save_status = widgets.HTML(
            value="",
            layout=widgets.Layout(flex="1"),
        )

        self._bottom_bar = widgets.HBox(
            [
                self._slice_dropdown,
                self._load_btn,
                self._refresh_list_btn,
                self._sep1,
                self._view_selector,
                self._sep2,
                self._view_controls,
                self._sep3,
                self._save_path_input,
                self._save_btn,
                self._save_status,
            ],
            layout=widgets.Layout(
                padding="6px 12px",
                border_top=f"1px solid rgba(138,201,239,0.4)",
                background=FABRIC_LIGHT,
                align_items="center",
                gap="8px",
            ),
        )

        # Inject soft CSS
        css_widget = widgets.HTML(value=WIDGET_SOFT_CSS)

        self._container = widgets.VBox(
            [css_widget, self._title_widget,
             self._content_area, self._bottom_bar],
            layout=widgets.Layout(
                border=f"1px solid rgba(138,201,239,0.4)",
                border_radius="10px",
                box_shadow="0 2px 12px rgba(0,0,0,0.06)",
                overflow="hidden",
            ),
        )
        self._container.add_class("fabvis-soft")

    def _build_title(self, mode: str) -> str:
        """Build the title bar HTML for a given mode name."""
        return (
            f'{FONT_IMPORT_CSS}'
            f'<div style="background:linear-gradient(135deg, {FABRIC_PRIMARY_DARK}, {FABRIC_PRIMARY}); '
            f'color:white; padding:10px 16px; font-size:16px; font-weight:600; '
            f'letter-spacing:0.5px; border-radius:8px 8px 0 0; '
            f'font-family:{FABRIC_BODY_FONT}; '
            f'display:flex; align-items:center; justify-content:space-between;">'
            f'<span>{self._logo_html}<span>FABRIC Visualization Suite</span></span>'
            f'<span style="font-size:13px; opacity:0.85;">{mode}</span>'
            f'</div>'
        )

    # ----------------------------------------------------------------
    # View management
    # ----------------------------------------------------------------

    def _ensure_view(self, view_name: str) -> None:
        """Lazily create the view's sub-tool if not yet initialized."""
        if self._initialized.get(view_name):
            return

        if view_name == _VIEW_GEO:
            from .geo_visualizer import GeoVisualizer
            self._geo_vis = GeoVisualizer(self._fablib)
            if self._fablib:
                self._geo_vis._load_resources()
            self._geo_vis._draw_sites()
            if self._geo_vis._show_links_cb.value:
                self._geo_vis._draw_infra_links()
            self._view_content[_VIEW_GEO] = self._strip_chrome(
                self._geo_vis._container
            )
            # Collect view-specific widgets from the geo visualizer
            self._view_widgets[_VIEW_GEO] = [
                self._geo_vis._show_sites_cb,
                self._geo_vis._show_links_cb,
            ]
            self._initialized[_VIEW_GEO] = True

        elif view_name == _VIEW_EDITOR:
            from .slice_editor import SliceEditor
            self._editor = SliceEditor(self._fablib)
            self._view_content[_VIEW_EDITOR] = self._strip_chrome(
                self._editor._container
            )
            # Collect view-specific widgets from the editor
            self._view_widgets[_VIEW_EDITOR] = [
                self._editor._layout_dropdown,
                self._editor._fit_btn,
            ]
            self._initialized[_VIEW_EDITOR] = True

    @staticmethod
    def _strip_chrome(container: widgets.VBox) -> widgets.VBox:
        """Return a VBox with the sub-tool's chrome removed.

        Strips the title bar (gradient HTML), bottom bar (HBox with
        border_top), and slice-picker top bar (HBox with border_bottom
        containing a SelectMultiple).
        """
        children = list(container.children)
        if len(children) < 2:
            return container

        filtered = []
        for child in children:
            # Skip gradient title bar
            if isinstance(child, widgets.HTML):
                val = child.value
                if "linear-gradient" in val and "font-size:16px" in val:
                    continue

            # Skip bottom bar (HBox with border_top in layout)
            if isinstance(child, widgets.HBox):
                bt = getattr(child.layout, "border_top", None)
                if bt and "solid" in str(bt):
                    continue

                # Skip slice-picker top bar (HBox with border_bottom
                # that contains a SelectMultiple)
                bb = getattr(child.layout, "border_bottom", None)
                if bb and "solid" in str(bb):
                    has_selector = any(
                        isinstance(c, widgets.SelectMultiple)
                        for c in child.children
                    )
                    if has_selector:
                        continue

            filtered.append(child)

        inner = widgets.VBox(
            filtered,
            layout=widgets.Layout(width="100%"),
        )
        inner.add_class("fabvis-soft")
        return inner

    def _switch_to_view(self, view_name: str) -> None:
        """Switch the content area to show the given view."""
        self._ensure_view(view_name)
        content = self._view_content.get(view_name)
        if content:
            self._content_area.children = [content]
        self._title_widget.value = self._build_title(view_name)
        self._save_status.value = ""

        # Swap view-specific controls in the bottom bar
        self._view_controls.children = self._view_widgets.get(view_name, [])

    # ----------------------------------------------------------------
    # Slice list management
    # ----------------------------------------------------------------

    def _refresh_slice_list(self) -> None:
        """Fetch slice list from FABRIC and populate the dropdown."""
        if not self._fablib:
            return
        try:
            slices = self._fablib.get_slices()
            names = sorted(s.get_name() for s in slices)
            self._slice_dropdown.options = names
            if names:
                self._slice_dropdown.value = names[0]
        except Exception as e:
            logger.warning(f"Failed to list slices: {e}")

    # ----------------------------------------------------------------
    # Event handlers
    # ----------------------------------------------------------------

    def _on_view_change(self, change) -> None:
        """Handle view selector change."""
        view_name = change.get("new")
        if view_name:
            self._switch_to_view(view_name)

    def _on_load_click(self, _btn) -> None:
        """Load the selected slice into the current view."""
        name = self._slice_dropdown.value
        if not name:
            self._save_status.value = (
                f'<small style="color:{FABRIC_DARK};">No slice selected</small>'
            )
            return

        view = self._view_selector.value
        try:
            if view == _VIEW_EDITOR:
                self._ensure_view(_VIEW_EDITOR)
                self._editor.load_slice(name)
            elif view == _VIEW_GEO:
                self._ensure_view(_VIEW_GEO)
                self._geo_vis.load_slices([name])
            self._save_status.value = (
                f'<small style="color:#008e7a;">Loaded: {name}</small>'
            )
        except Exception as e:
            self._save_status.value = (
                f'<small style="color:#b00020;">Error: {e}</small>'
            )
            logger.error(f"Load slice failed: {e}")

    def _on_refresh_list_click(self, _btn) -> None:
        """Refresh the slice list from FABRIC."""
        self._refresh_slice_list()

    def _on_save_click(self, _btn) -> None:
        """Save the current view as an image."""
        path = self._save_path_input.value.strip()
        if not path:
            self._save_status.value = (
                f'<small style="color:{FABRIC_DARK};">Enter a filename</small>'
            )
            return

        view = self._view_selector.value
        try:
            if view == _VIEW_GEO:
                self._ensure_view(_VIEW_GEO)
                self._geo_vis.save_image(path)
                self._save_status.value = (
                    f'<small style="color:#008e7a;">Saved: {path}</small>'
                )
            elif view == _VIEW_EDITOR:
                self._ensure_view(_VIEW_EDITOR)
                if self._editor._slice is not None:
                    from .image_export import render_slice_graph
                    import matplotlib.pyplot as plt
                    positions = self._editor._get_cytoscape_positions()
                    fig = render_slice_graph(
                        [self._editor._slice], save=path,
                        positions=positions,
                    )
                    plt.close(fig)
                    self._save_status.value = (
                        f'<small style="color:#008e7a;">Saved: {path}</small>'
                    )
                else:
                    self._save_status.value = (
                        f'<small style="color:{FABRIC_DARK};">No slice loaded</small>'
                    )
        except Exception as e:
            self._save_status.value = (
                f'<small style="color:#b00020;">Error: {e}</small>'
            )
            logger.error(f"Save image failed: {e}")
