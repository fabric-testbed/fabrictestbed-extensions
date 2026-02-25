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

"""Cytoscape style definitions and color constants for FABRIC visualization.

Colors and fonts match the official FABRIC portal branding:
https://portal.fabric-testbed.net/branding
"""

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Official FABRIC brand colors (from portal.fabric-testbed.net/branding) ──
FABRIC_PRIMARY = "#5798bc"
FABRIC_PRIMARY_LIGHT = "#8ac9ef"
FABRIC_PRIMARY_DARK = "#1f6a8c"
FABRIC_SECONDARY = "#838385"        # portal grey secondary
FABRIC_WARNING = "#ff8542"          # portal orange/warning
FABRIC_WARNING_LIGHT = "#ffa562"
FABRIC_SUCCESS = "#008e7a"          # portal teal/success
FABRIC_DANGER = "#b00020"           # portal red/danger
FABRIC_INFO = "#a8c9dc"             # portal info blue
FABRIC_DARK = "#374955"             # portal dark slate
FABRIC_BLACK = "#212121"
FABRIC_GREY = "#838385"
FABRIC_LIGHT = "#f8f9fa"
FABRIC_WHITE = "#ffffff"
FABRIC_BG_TINT = "#edf2f8"         # light blue-grey bg from portal

# ── FABRIC fonts ──
FABRIC_HEADING_FONT = "Montserrat"
FABRIC_BODY_FONT = ("'Montserrat', -apple-system, BlinkMacSystemFont, "
                     "'Segoe UI', Roboto, Helvetica, Arial, sans-serif")

# Google Fonts import tag for embedding in HTML widgets
FONT_IMPORT_CSS = (
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Montserrat:wght@400;500;600;700&display=swap" '
    'rel="stylesheet">'
)

# ── State colors (using FABRIC brand palette) ──
STATE_ACTIVE = FABRIC_SUCCESS       # teal #008e7a
STATE_CONFIGURING = FABRIC_WARNING  # orange #ff8542
STATE_ERROR = FABRIC_DANGER         # red #b00020
STATE_NASCENT = FABRIC_SECONDARY    # grey #838385
STATE_DEAD = "#616161"              # dark grey

# Lighter tints used as node backgrounds
STATE_ACTIVE_BG = "#e0f2f1"       # teal tint
STATE_CONFIGURING_BG = "#fff3e0"  # orange tint
STATE_ERROR_BG = "#fce4ec"        # red tint
STATE_NASCENT_BG = FABRIC_LIGHT
STATE_DEAD_BG = "#eeeeee"

# ── Component type colors ──
COLOR_NIC = FABRIC_PRIMARY          # brand blue
COLOR_GPU = "#e65100"               # deep orange (stronger)
COLOR_FPGA = "#7b1fa2"             # purple
COLOR_NVME = FABRIC_DARK           # dark slate
COLOR_STORAGE = FABRIC_DARK

# ── Network type colors ──
COLOR_NETWORK_L2 = FABRIC_PRIMARY_DARK   # brand dark blue #1f6a8c
COLOR_NETWORK_L3 = FABRIC_SUCCESS        # brand teal #008e7a
COLOR_NETWORK_L2_BG = "#ddeaf2"          # light brand blue bg
COLOR_NETWORK_L3_BG = "#e0f2f1"          # light teal bg

# Map component model prefixes to colors
COMPONENT_COLORS = {
    "NIC": COLOR_NIC,
    "GPU": COLOR_GPU,
    "FPGA": COLOR_FPGA,
    "NVME": COLOR_NVME,
    "SHARED": COLOR_NIC,
    "SMART": COLOR_NIC,
}

# Map component model prefixes to short display names
COMPONENT_ICONS = {
    "NIC": "NIC",
    "GPU": "GPU",
    "FPGA": "FPGA",
    "NVME": "NVM",
    "SHARED": "NIC",
    "SMART": "sNIC",
}

# Map slice/node states to accent colors (for borders)
STATE_COLORS = {
    "StableOK": STATE_ACTIVE,
    "Active": STATE_ACTIVE,
    "Configuring": STATE_CONFIGURING,
    "Ticketed": STATE_CONFIGURING,
    "ModifyOK": STATE_CONFIGURING,
    "Nascent": STATE_NASCENT,
    "StableError": STATE_ERROR,
    "ModifyError": STATE_ERROR,
    "Closing": STATE_DEAD,
    "Dead": STATE_DEAD,
}

# Map states to light background tints
STATE_BG_COLORS = {
    "StableOK": STATE_ACTIVE_BG,
    "Active": STATE_ACTIVE_BG,
    "Configuring": STATE_CONFIGURING_BG,
    "Ticketed": STATE_CONFIGURING_BG,
    "ModifyOK": STATE_CONFIGURING_BG,
    "Nascent": STATE_NASCENT_BG,
    "StableError": STATE_ERROR_BG,
    "ModifyError": STATE_ERROR_BG,
    "Closing": STATE_DEAD_BG,
    "Dead": STATE_DEAD_BG,
}

# L2 network service types
L2_NETWORK_TYPES = {"L2Bridge", "L2STS", "L2PTP", "PortMirror"}

# L3 network service types
L3_NETWORK_TYPES = {"FABNetv4", "FABNetv6", "FABNetv4Ext", "FABNetv6Ext", "L3VPN"}


def get_state_color(state) -> str:
    """Return the accent/border color for a given state."""
    return STATE_COLORS.get(str(state), STATE_NASCENT)


def get_state_bg_color(state) -> str:
    """Return the light background tint for a given state."""
    return STATE_BG_COLORS.get(str(state), FABRIC_LIGHT)


def get_component_color(model) -> str:
    """Return the color for a component based on its model name prefix."""
    model_str = str(model).upper()
    for prefix, color in COMPONENT_COLORS.items():
        if model_str.startswith(prefix):
            return color
    return FABRIC_GREY


def get_component_short_name(model) -> str:
    """Return a short display name for a component type."""
    model_str = str(model).upper()
    for prefix, icon in COMPONENT_ICONS.items():
        if model_str.startswith(prefix):
            return icon
    return "DEV"


def get_network_color(network_type) -> str:
    """Return the color for a network based on its type."""
    nt = str(network_type)
    if nt in L2_NETWORK_TYPES:
        return COLOR_NETWORK_L2
    if nt in L3_NETWORK_TYPES:
        return COLOR_NETWORK_L3
    return FABRIC_GREY


# ── Known FABRIC site locations ──
SITE_LOCATIONS = {
    "LOSA": (34.0490803, -118.259534),
    "DALL": (32.7990816, -96.8206903),
    "TACC": (30.3899405, -97.7261807),
    "KANS": (39.1004885, -94.5823448),
    "SALT": (40.7570751, -111.9534664),
    "CLEM": (34.5865435, -82.8212889),
    "NCSA": (40.09584, -88.2415369),
    "RUTG": (40.5224962, -74.4405719),
    "MICH": (42.2931086, -83.7101319),
    "INDI": (39.7737312, -86.1674868),
    "PSC": (40.4343887, -79.750207),
    "CERN": (46.2338702, 6.0469869),
    "HAWI": (21.2989762, -157.8163991),
    "TOKY": (35.7115097, 139.7640619),
    "SRI": (37.4566052, -122.174686),
    "EDUKY": (38.0325, -84.502801),
    "UCSD": (32.8886802, -117.239324),
    "STAR": (42.2359989, -88.1575427),
    "GATECH": (33.7753991, -84.3875488),
    "UTAH": (40.7503666, -111.893838),
    "GPN": (39.0342627, -94.5826075),
    "BRIST": (51.457119, -2.607297),
    "PRIN": (40.3461201, -74.616073),
    "ATLA": (33.758551, -84.387703),
    "SEAT": (47.6143548, -122.3388637),
    "MAX": (38.9886345, -76.9434794),
    "FIU": (25.7542948, -80.3702894),
    "EDC": (40.09584, -88.2415369),
    "AMST": (52.3544941, 4.9557553),
    "NEWY": (40.7383575, -73.9992012),
    "MASS": (42.202493, -72.6078766),
    "WASH": (38.9208836, -77.2111974),
    "RENC": (35.7721, -78.6386),
    "UKY": (38.0406, -84.5037),
    "LBNL": (37.8755, -122.2477),
}

DEFAULT_MAP_CENTER = (38.12, -85.71)
DEFAULT_MAP_ZOOM = 4


def get_site_location(site_name: str):
    """Return (lat, lon) for a FABRIC site, or None if unknown."""
    return SITE_LOCATIONS.get(site_name)


# ── Logo helper ──
_logo_data_url_cache: str = ""


def get_logo_data_url() -> str:
    """Return a base64 data URL for the FABRIC brand logo.

    Loads from the images directory next to this package.
    Cached after first call.
    """
    global _logo_data_url_cache
    if _logo_data_url_cache:
        return _logo_data_url_cache

    # Try the images directory in fabrictestbed_extensions
    img_dir = Path(__file__).resolve().parent.parent / "images"
    for name in ("fabric_brand.png", "fabric_logo.png"):
        logo_path = img_dir / name
        if logo_path.exists():
            try:
                raw = logo_path.read_bytes()
                b64 = base64.b64encode(raw).decode("ascii")
                _logo_data_url_cache = f"data:image/png;base64,{b64}"
                return _logo_data_url_cache
            except Exception as e:
                logger.debug(f"Could not load logo from {logo_path}: {e}")

    return ""


def build_stylesheet() -> list:
    """Build the complete Cytoscape stylesheet.

    Design principles:
    - Clean, card-style VM nodes with colored left borders for state
    - No component child nodes (shown in detail panel instead)
    - Larger network shapes with strong contrast
    - Readable edge labels
    - Subtle slice containers
    """
    return [
        # ── Slice containers ──
        {
            "selector": "node.slice",
            "css": {
                "shape": "roundrectangle",
                "background-color": "#f8f9fa",
                "background-opacity": 0.5,
                "border-width": 2,
                "border-color": FABRIC_PRIMARY,
                "border-style": "dashed",
                "content": "data(label)",
                "text-valign": "top",
                "text-halign": "center",
                "font-size": 16,
                "font-weight": "bold",
                "color": FABRIC_PRIMARY_DARK,
                "text-margin-y": 8,
                "padding": "30px",
            },
        },

        # ── VM / compute nodes — card style ──
        {
            "selector": "node.vm",
            "css": {
                "shape": "roundrectangle",
                "background-color": "data(state_bg)",
                "border-width": 3,
                "border-color": "data(state_color)",
                "content": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": FABRIC_BLACK,
                "width": 180,
                "height": 70,
                "font-size": 11,
                "text-wrap": "wrap",
                "text-max-width": "170px",
                "padding": "12px",
            },
        },

        # ── Switch nodes ──
        {
            "selector": "node.switch",
            "css": {
                "shape": "triangle",
                "background-color": "data(state_bg)",
                "border-width": 3,
                "border-color": "data(state_color)",
                "content": "data(label)",
                "text-valign": "bottom",
                "text-margin-y": 6,
                "color": FABRIC_BLACK,
                "width": 70,
                "height": 70,
                "font-size": 11,
                "text-wrap": "wrap",
                "text-max-width": "80px",
                "padding": "12px",
            },
        },

        # ── Facility port nodes ──
        {
            "selector": "node.facility-port",
            "css": {
                "shape": "pentagon",
                "background-color": "#fff3e0",
                "border-width": 3,
                "border-color": FABRIC_WARNING,
                "content": "data(label)",
                "text-valign": "center",
                "color": FABRIC_BLACK,
                "width": 70,
                "height": 70,
                "font-size": 10,
                "text-wrap": "wrap",
                "text-max-width": "65px",
                "padding": "12px",
            },
        },

        # ── L2 network nodes — hexagon ──
        {
            "selector": "node.network-l2",
            "css": {
                "shape": "hexagon",
                "background-color": COLOR_NETWORK_L2_BG,
                "border-width": 3,
                "border-color": COLOR_NETWORK_L2,
                "content": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": COLOR_NETWORK_L2,
                "width": 80,
                "height": 80,
                "font-size": 10,
                "font-weight": "bold",
                "text-wrap": "wrap",
                "text-max-width": "72px",
            },
        },

        # ── L3 network nodes — hexagon ──
        {
            "selector": "node.network-l3",
            "css": {
                "shape": "hexagon",
                "background-color": COLOR_NETWORK_L3_BG,
                "border-width": 3,
                "border-color": COLOR_NETWORK_L3,
                "content": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": COLOR_NETWORK_L3,
                "width": 80,
                "height": 80,
                "font-size": 10,
                "font-weight": "bold",
                "text-wrap": "wrap",
                "text-max-width": "72px",
            },
        },

        # ── Edges (interface connections) ──
        {
            "selector": "edge",
            "style": {
                "width": 2.5,
                "line-color": "#bdbdbd",
                "curve-style": "bezier",
                "target-arrow-shape": "none",
                "label": "data(edge_label)",
                "font-size": 9,
                "color": FABRIC_DARK,
                "text-rotation": "autorotate",
                "text-margin-y": -12,
                "text-background-color": "#ffffff",
                "text-background-opacity": 0.85,
                "text-background-padding": "2px",
                "text-background-shape": "roundrectangle",
            },
        },

        # ── L2 edges — solid blue ──
        {
            "selector": "edge.l2",
            "style": {
                "line-color": COLOR_NETWORK_L2,
                "line-style": "solid",
                "width": 3,
            },
        },

        # ── L3 edges — dashed green ──
        {
            "selector": "edge.l3",
            "style": {
                "line-color": COLOR_NETWORK_L3,
                "line-style": "dashed",
                "width": 3,
            },
        },

        # ── Selected elements — orange highlight ──
        {
            "selector": ":selected",
            "css": {
                "border-width": 4,
                "border-color": FABRIC_WARNING,
                "line-color": FABRIC_WARNING,
            },
        },
    ]
