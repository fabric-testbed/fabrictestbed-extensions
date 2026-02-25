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

"""Layout presets for the Cytoscape graph."""

LAYOUT_PRESETS = {
    "cola": {
        "name": "cola",
        "nodeSpacing": 60,
        "edgeLengthVal": 120,
        "padding": 40,
        "animate": True,
    },
    "dagre": {
        "name": "dagre",
        "rankDir": "TB",
        "nodeSep": 60,
        "edgeSep": 20,
        "rankSep": 100,
        "padding": 40,
    },
    "breadthfirst": {
        "name": "breadthfirst",
        "directed": False,
        "padding": 30,
        "spacingFactor": 1.5,
    },
    "grid": {
        "name": "grid",
        "padding": 30,
        "condense": True,
    },
    "concentric": {
        "name": "concentric",
        "padding": 30,
        "minNodeSpacing": 50,
    },
    "cose": {
        "name": "cose",
        "padding": 30,
        "nodeOverlap": 20,
        "idealEdgeLength": 80,
    },
}

AVAILABLE_LAYOUTS = list(LAYOUT_PRESETS.keys())
DEFAULT_LAYOUT = "dagre"


def get_layout(name: str, **overrides) -> dict:
    """Get a layout configuration by name, with optional overrides."""
    if name not in LAYOUT_PRESETS:
        raise ValueError(
            f"Unknown layout '{name}'. Available: {AVAILABLE_LAYOUTS}"
        )
    config = LAYOUT_PRESETS[name].copy()
    config.update(overrides)
    return config
