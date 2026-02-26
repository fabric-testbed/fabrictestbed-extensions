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

"""Static image rendering for FABRIC slice topologies.

Generates publication-quality PNG/PDF images of slice topologies without
requiring a running Jupyter widget. Two render modes:

- Graph view: networkx + matplotlib node-link diagram
- Geographic view: matplotlib scatter plot with site locations

Usage:
    from fabrictestbed_extensions.fabvis import render_slice_graph, render_slice_map

    # From a slice object:
    img = render_slice_graph(slice_obj)
    img.savefig("topology.png")

    # Save directly:
    render_slice_graph(slice_obj, save="topology.png")

    # From a FablibManager + slice name:
    render_slice_graph("my_slice", fablib=fablib_manager, save="topology.png")
"""

import io
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional, Union

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.figure import Figure

from . import styles
from .graph_builder import GraphBuilder

logger = logging.getLogger(__name__)

# Use non-interactive backend when saving headless
matplotlib.use("Agg")

# Try to load Montserrat; fall back gracefully
try:
    from matplotlib import font_manager
    _montserrat_available = any(
        "montserrat" in f.name.lower()
        for f in font_manager.fontManager.ttflist
    )
except Exception:
    _montserrat_available = False

_FONT_FAMILY = "Montserrat" if _montserrat_available else "sans-serif"


def _resolve_slices(slices, fablib=None) -> list:
    """Resolve input to a list of slice objects.

    Args:
        slices: A single slice object, a list of slice objects,
                a slice name (str), or a list of slice names.
        fablib: FablibManager instance (required if slices are names).

    Returns:
        List of FABlib Slice objects.
    """
    if isinstance(slices, str):
        slices = [slices]

    if isinstance(slices, list) and slices and isinstance(slices[0], str):
        if fablib is None:
            raise ValueError(
                "fablib parameter required when passing slice names"
            )
        resolved = []
        for name in slices:
            resolved.append(fablib.get_slice(name))
        return resolved

    if not isinstance(slices, list):
        return [slices]

    return slices


def _safe_get(obj, method_name: str, default=None):
    """Safely call a getter method."""
    try:
        method = getattr(obj, method_name, None)
        if method is None:
            return default
        result = method()
        return result if result is not None else default
    except Exception:
        return default


# ─── Graph rendering ───────────────────────────────────────────────

# Shape map for matplotlib markers
_NODE_SHAPES = {
    "vm": "s",              # square
    "switch": "^",          # triangle
    "facility_port": "p",   # pentagon
    "network": "H",         # hexagon
}


def render_slice_graph(
    slices,
    fablib=None,
    save: Optional[str] = None,
    figsize: tuple = (14, 10),
    dpi: int = 150,
    title: Optional[str] = None,
    show_edge_labels: bool = True,
    positions: Optional[dict] = None,
) -> Figure:
    """Render a slice topology as a static graph image.

    Args:
        slices: Slice object(s) or name(s) to render.
        fablib: FablibManager (required if slices are names).
        save: File path to save the image (png, pdf, svg).
        figsize: Figure size in inches.
        dpi: Resolution for raster output.
        title: Custom title (defaults to slice name(s)).
        show_edge_labels: Whether to show IP/VLAN labels on edges.
        positions: Optional dict mapping cytoscape node IDs to (x, y)
                   tuples. When provided, these positions are used
                   instead of computing a fresh layout (e.g. to capture
                   the user's current arrangement in the editor).

    Returns:
        matplotlib Figure object.
    """
    slice_objs = _resolve_slices(slices, fablib)

    # Build graph data using the existing GraphBuilder
    builder = GraphBuilder()
    for s in slice_objs:
        builder.add_slice(s)
    graph_data = builder.build()

    # Create networkx graph
    G = nx.Graph()

    node_colors = []
    node_edge_colors = []
    node_sizes = []
    node_labels = {}
    node_markers = {}  # id -> marker shape

    for n in graph_data["nodes"]:
        data = n["data"]
        cy_id = data["id"]
        classes = n.get("classes", "")

        # Skip slice container nodes (they're just grouping)
        if classes == "slice":
            continue

        G.add_node(cy_id)

        element_type = data.get("element_type", "")
        label = data.get("label", "").split("\n")[0]  # first line only
        node_labels[cy_id] = label

        if element_type == "node":
            bg = data.get("state_bg", styles.FABRIC_LIGHT)
            border = data.get("state_color", styles.FABRIC_PRIMARY)
            node_colors.append(bg)
            node_edge_colors.append(border)
            node_sizes.append(1800)
            node_markers[cy_id] = "vm"
        elif element_type == "network":
            net_type = str(data.get("net_type", ""))
            is_l2 = net_type in styles.L2_NETWORK_TYPES
            node_colors.append(
                styles.COLOR_NETWORK_L2_BG if is_l2
                else styles.COLOR_NETWORK_L3_BG
            )
            node_edge_colors.append(
                styles.COLOR_NETWORK_L2 if is_l2
                else styles.COLOR_NETWORK_L3
            )
            node_sizes.append(1200)
            node_markers[cy_id] = "network"
        elif element_type == "switch":
            bg = data.get("state_bg", styles.FABRIC_LIGHT)
            border = data.get("state_color", styles.FABRIC_PRIMARY)
            node_colors.append(bg)
            node_edge_colors.append(border)
            node_sizes.append(1000)
            node_markers[cy_id] = "switch"
        elif element_type == "facility_port":
            node_colors.append("#fff3e0")
            node_edge_colors.append(styles.FABRIC_WARNING)
            node_sizes.append(1000)
            node_markers[cy_id] = "facility_port"
        else:
            node_colors.append(styles.FABRIC_LIGHT)
            node_edge_colors.append(styles.FABRIC_PRIMARY)
            node_sizes.append(800)
            node_markers[cy_id] = "vm"

    edge_colors = []
    edge_styles = []
    edge_labels = {}

    for e in graph_data["edges"]:
        data = e["data"]
        source = data["source"]
        target = data["target"]
        classes = e.get("classes", "")

        # Only add edge if both endpoints exist in graph
        if source not in G.nodes or target not in G.nodes:
            continue

        G.add_edge(source, target)

        if classes == "l2":
            edge_colors.append(styles.COLOR_NETWORK_L2)
            edge_styles.append("solid")
        elif classes == "l3":
            edge_colors.append(styles.COLOR_NETWORK_L3)
            edge_styles.append("dashed")
        else:
            edge_colors.append("#bdbdbd")
            edge_styles.append("solid")

        if show_edge_labels:
            label = data.get("edge_label", "")
            if label:
                edge_labels[(source, target)] = label

    if len(G.nodes) == 0:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        ax.text(0.5, 0.5, "No elements to display",
                ha="center", va="center", fontsize=14, color="#999")
        ax.set_axis_off()
        if save:
            fig.savefig(save, dpi=dpi, bbox_inches="tight", facecolor="white")
        return fig

    # Layout — use provided positions if available, else compute
    if positions:
        # Use cytoscape positions; cytoscape y-axis is inverted (down=positive)
        pos = {}
        for nid in G.nodes():
            if nid in positions:
                cx, cy_ = positions[nid]
                pos[nid] = (cx, -cy_)  # flip y so up is positive in matplotlib
        # Fall back to auto-layout for any nodes missing positions
        missing = [n for n in G.nodes() if n not in pos]
        if missing:
            auto = nx.spring_layout(G, k=2, seed=42)
            for n in missing:
                pos[n] = auto[n]
    elif len(G.nodes) <= 3:
        pos = nx.spring_layout(G, k=3, seed=42)
    else:
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
            pos = nx.spring_layout(G, k=2, seed=42)

    # Draw
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafcfe")

    # Draw edges
    for idx, (u, v) in enumerate(G.edges()):
        color = edge_colors[idx] if idx < len(edge_colors) else "#bdbdbd"
        style = edge_styles[idx] if idx < len(edge_styles) else "solid"
        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)], ax=ax,
            edge_color=color, style=style, width=2.0, alpha=0.8,
        )

    # Draw nodes grouped by type for different markers
    node_list = list(G.nodes())
    type_groups = defaultdict(list)
    for i, nid in enumerate(node_list):
        mtype = node_markers.get(nid, "vm")
        type_groups[mtype].append(i)

    for mtype, indices in type_groups.items():
        marker = _NODE_SHAPES.get(mtype, "o")
        subset_nodes = [node_list[i] for i in indices]
        subset_colors = [node_colors[i] for i in indices]
        subset_edge_colors = [node_edge_colors[i] for i in indices]
        subset_sizes = [node_sizes[i] for i in indices]

        nx.draw_networkx_nodes(
            G, pos, nodelist=subset_nodes, ax=ax,
            node_color=subset_colors,
            edgecolors=subset_edge_colors,
            node_size=subset_sizes,
            node_shape=marker,
            linewidths=2.5,
        )

    # Labels
    nx.draw_networkx_labels(
        G, pos, labels=node_labels, ax=ax,
        font_size=9, font_family=_FONT_FAMILY,
        font_weight="bold",
    )

    if show_edge_labels and edge_labels:
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=edge_labels, ax=ax,
            font_size=7, font_family=_FONT_FAMILY,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor="none", alpha=0.8),
        )

    # Title
    if title is None:
        names = [_safe_get(s, "get_name", "?") for s in slice_objs]
        title = "FABRIC Topology: " + ", ".join(names)

    ax.set_title(title, fontsize=14, fontweight="bold",
                 color=styles.FABRIC_PRIMARY_DARK, fontfamily=_FONT_FAMILY,
                 pad=16)

    # Legend
    legend_items = [
        mpatches.Patch(facecolor=styles.STATE_ACTIVE_BG,
                       edgecolor=styles.STATE_ACTIVE,
                       linewidth=2, label="VM Node"),
        mpatches.Patch(facecolor=styles.COLOR_NETWORK_L2_BG,
                       edgecolor=styles.COLOR_NETWORK_L2,
                       linewidth=2, label="L2 Network"),
        mpatches.Patch(facecolor=styles.COLOR_NETWORK_L3_BG,
                       edgecolor=styles.COLOR_NETWORK_L3,
                       linewidth=2, label="L3 Network"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=8,
              framealpha=0.9, edgecolor="#e0e0e0")

    ax.set_axis_off()
    fig.tight_layout()

    if save:
        fig.savefig(save, dpi=dpi, bbox_inches="tight", facecolor="white")
        logger.info(f"Saved graph image to {save}")

    return fig


# ─── Geographic map rendering ─────────────────────────────────────

def render_slice_map(
    slices,
    fablib=None,
    save: Optional[str] = None,
    figsize: tuple = (16, 10),
    dpi: int = 150,
    title: Optional[str] = None,
    show_all_sites: bool = True,
    map_extent: Optional[tuple] = None,
) -> Figure:
    """Render a slice topology on a geographic map as a static image.

    Args:
        slices: Slice object(s) or name(s) to render.
        fablib: FablibManager (required if slices are names).
        save: File path to save the image (png, pdf, svg).
        figsize: Figure size in inches.
        dpi: Resolution for raster output.
        title: Custom title (defaults to slice name(s)).
        show_all_sites: Whether to show all FABRIC sites as background dots.
        map_extent: (lon_min, lon_max, lat_min, lat_max) or None for auto.

    Returns:
        matplotlib Figure object.
    """
    slice_objs = _resolve_slices(slices, fablib)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eef4f8")

    # Draw all FABRIC sites as background markers
    if show_all_sites:
        site_lons = [loc[1] for loc in styles.SITE_LOCATIONS.values()]
        site_lats = [loc[0] for loc in styles.SITE_LOCATIONS.values()]
        ax.scatter(
            site_lons, site_lats,
            s=60, c=styles.FABRIC_PRIMARY_LIGHT, edgecolors=styles.FABRIC_PRIMARY,
            linewidths=1.0, zorder=2, alpha=0.6,
        )
        for name, (lat, lon) in styles.SITE_LOCATIONS.items():
            ax.annotate(
                name, (lon, lat), fontsize=6, fontfamily=_FONT_FAMILY,
                color=styles.FABRIC_SECONDARY, fontweight="bold",
                ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points",
                zorder=3,
            )

    # Collect nodes by site
    site_nodes: dict[str, list] = defaultdict(list)
    all_node_lats = []
    all_node_lons = []

    for slice_obj in slice_objs:
        try:
            for node in slice_obj.get_nodes():
                site = str(_safe_get(node, "get_site", ""))
                if not site:
                    continue
                loc = styles.get_site_location(site)
                if loc is None:
                    continue
                site_nodes[site].append((slice_obj, node))
        except Exception as e:
            logger.warning(f"Error processing slice nodes: {e}")

    # Draw node markers at sites
    for site, nodes in site_nodes.items():
        loc = styles.get_site_location(site)
        if loc is None:
            continue

        for idx, (slice_obj, node) in enumerate(nodes):
            # Offset nodes at the same site
            offset_lat = idx * 0.3
            offset_lon = idx * 0.3
            lat = loc[0] + offset_lat
            lon = loc[1] + offset_lon
            all_node_lats.append(lat)
            all_node_lons.append(lon)

            node_name = str(_safe_get(node, "get_name", "?"))
            node_state = str(_safe_get(node, "get_reservation_state", "Unknown"))
            state_color = styles.get_state_color(node_state)

            ax.scatter(
                lon, lat, s=200,
                c=state_color, edgecolors=styles.FABRIC_PRIMARY_DARK,
                linewidths=2, zorder=5, alpha=0.9,
            )
            ax.annotate(
                node_name, (lon, lat), fontsize=8, fontfamily=_FONT_FAMILY,
                fontweight="bold", color=styles.FABRIC_DARK,
                ha="center", va="bottom",
                xytext=(0, 10), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor=state_color, alpha=0.85),
                zorder=6,
            )

    # Draw network connections between sites
    drawn_links = set()
    for slice_obj in slice_objs:
        try:
            for net in slice_obj.get_network_services():
                net_type = str(_safe_get(net, "get_type", ""))
                is_l2 = net_type in styles.L2_NETWORK_TYPES

                connected_sites = set()
                try:
                    for iface in net.get_interfaces():
                        site = _safe_get(iface, "get_site", None)
                        if not site:
                            try:
                                n = iface.get_node()
                                if n:
                                    site = _safe_get(n, "get_site", None)
                            except Exception:
                                pass
                        if site:
                            connected_sites.add(str(site))
                except Exception:
                    continue

                if len(connected_sites) < 2:
                    continue

                sites_list = sorted(connected_sites)
                for i in range(len(sites_list)):
                    for j in range(i + 1, len(sites_list)):
                        pair = (sites_list[i], sites_list[j])
                        if pair in drawn_links:
                            continue
                        drawn_links.add(pair)

                        loc_a = styles.get_site_location(pair[0])
                        loc_b = styles.get_site_location(pair[1])
                        if loc_a is None or loc_b is None:
                            continue

                        color = styles.COLOR_NETWORK_L2 if is_l2 else styles.COLOR_NETWORK_L3
                        linestyle = "-" if is_l2 else "--"
                        ax.plot(
                            [loc_a[1], loc_b[1]], [loc_a[0], loc_b[0]],
                            color=color, linewidth=2.5, linestyle=linestyle,
                            alpha=0.7, zorder=4,
                        )
        except Exception as e:
            logger.warning(f"Error drawing networks: {e}")

    # Set map extent
    if map_extent:
        ax.set_xlim(map_extent[0], map_extent[1])
        ax.set_ylim(map_extent[2], map_extent[3])
    elif all_node_lats:
        # Zoom to show loaded nodes with padding
        lat_pad = max(3, (max(all_node_lats) - min(all_node_lats)) * 0.3)
        lon_pad = max(5, (max(all_node_lons) - min(all_node_lons)) * 0.3)
        ax.set_xlim(min(all_node_lons) - lon_pad, max(all_node_lons) + lon_pad)
        ax.set_ylim(min(all_node_lats) - lat_pad, max(all_node_lats) + lat_pad)
    else:
        # Default: US-centric view
        ax.set_xlim(-130, -60)
        ax.set_ylim(18, 52)

    # Grid
    ax.grid(True, linestyle=":", alpha=0.3, color="#999")
    ax.set_xlabel("Longitude", fontsize=9, fontfamily=_FONT_FAMILY,
                  color=styles.FABRIC_DARK)
    ax.set_ylabel("Latitude", fontsize=9, fontfamily=_FONT_FAMILY,
                  color=styles.FABRIC_DARK)

    # Title
    if title is None:
        names = [_safe_get(s, "get_name", "?") for s in slice_objs]
        title = "FABRIC Geographic View: " + ", ".join(names)

    ax.set_title(title, fontsize=14, fontweight="bold",
                 color=styles.FABRIC_PRIMARY_DARK, fontfamily=_FONT_FAMILY,
                 pad=16)

    # Legend
    legend_items = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=styles.FABRIC_PRIMARY_LIGHT,
                   markeredgecolor=styles.FABRIC_PRIMARY,
                   markersize=8, label="FABRIC Site"),
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=styles.STATE_ACTIVE,
                   markeredgecolor=styles.FABRIC_PRIMARY_DARK,
                   markersize=10, label="Active Node"),
        plt.Line2D([0], [0], color=styles.COLOR_NETWORK_L2,
                   linewidth=2, label="L2 Network"),
        plt.Line2D([0], [0], color=styles.COLOR_NETWORK_L3,
                   linewidth=2, linestyle="--", label="L3 Network"),
    ]
    ax.legend(handles=legend_items, loc="lower left", fontsize=8,
              framealpha=0.9, edgecolor="#e0e0e0")

    fig.tight_layout()

    if save:
        fig.savefig(save, dpi=dpi, bbox_inches="tight", facecolor="white")
        logger.info(f"Saved map image to {save}")

    return fig
