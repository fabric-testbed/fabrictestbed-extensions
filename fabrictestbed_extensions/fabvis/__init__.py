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

"""FABRIC Visualization Suite — interactive topology tools for Jupyter.

Primary entry point:

- FabVis: Unified tool with two modes — Editor (Cytoscape graph + editing
  panels) and Geographic (ipyleaflet map with sites, links, and slices).
  Includes a view selector and built-in image export.

Individual tools (also usable standalone):

- SliceVisualizer: Cytoscape-based graph topology viewer
- GeoVisualizer: Geographic map viewer using ipyleaflet
- SliceEditor: Interactive slice builder/editor

Static image renderers (no GUI required):

- render_slice_graph(): Generate a graph topology image from a slice object.
- render_slice_map(): Generate a geographic map image from a slice object.

Usage::

    from fabrictestbed_extensions.fabvis import FabVis

    fablib = FablibManager()
    fv = FabVis(fablib)
    fv.show()

    # Static images (no GUI):
    from fabrictestbed_extensions.fabvis import render_slice_graph, render_slice_map
    fig = render_slice_graph(my_slice, save="topology.png")
    fig = render_slice_map(my_slice, save="map.png")
"""

from .fabvis import FabVis
from .visualizer import SliceVisualizer
from .geo_visualizer import GeoVisualizer
from .slice_editor import SliceEditor
from .image_export import render_slice_graph, render_slice_map
from .configure_gui import ConfigureGUI
from .artifact_browser import ArtifactBrowser

__all__ = [
    "FabVis",
    "SliceVisualizer",
    "GeoVisualizer",
    "SliceEditor",
    "render_slice_graph",
    "render_slice_map",
    "ConfigureGUI",
    "ArtifactBrowser",
]
