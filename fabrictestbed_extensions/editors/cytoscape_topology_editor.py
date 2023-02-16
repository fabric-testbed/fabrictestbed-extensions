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

import os
import traceback
import re

import functools

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities,
    ComponentType,
    ComponentModelType,
    ServiceType,
    ComponentCatalog,
)
from fabrictestbed.slice_editor import ExperimentTopology, Capacities
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

import ipycytoscape as cy
from IPython.display import display
from ipywidgets import Output

from .abc_topology_editor import AbcTopologyEditor

from .. import images


class CytoscapeTopologyEditor(AbcTopologyEditor):
    # FABRIC design elements https://fabric-testbed.net/branding/style/
    FABRIC_PRIMARY = "#27aae1"
    FABRIC_PRIMARY_LIGHT = "#cde4ef"
    FABRIC_PRIMARY_DARK = "#078ac1"
    FABRIC_SECONDARY = "#f26522"
    FABRIC_SECONDARY_LIGHT = "#ff8542"
    FABRIC_SECONDARY_DARK = "#d24502"
    FABRIC_BLACK = "#231f20"
    FABRIC_DARK = "#433f40"
    FABRIC_GREY = "#666677"
    FABRIC_LIGHT = "#f3f3f9"
    FABRIC_WHITE = "#ffffff"
    FABRIC_LOGO = "fabric_logo.png"

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.out = Output()

        self.cytoscapeobj = cy.CytoscapeWidget()
        self.data = {"nodes": [], "edges": []}

        self.style = "secondary"

    def toggle_style(self):
        if self.style == "primary":
            self.style = "secondary"
            color = self.FABRIC_SECONDARY
            dark_color = self.FABRIC_SECONDARY_DARK
        elif self.style == "secondary":
            self.style = "primary"
            color = self.FABRIC_PRIMARY
            dark_color = self.FABRIC_PRIMARY_DARK

        self.cytoscapeobj.set_style(
            [
                {
                    "selector": "node",
                    "css": {
                        "content": "data(name)",
                        "text-valign": "center",
                        "color": "white",
                        "text-outline-width": 2,
                        "text-outline-color": dark_color,
                        "background-color": color,
                    },
                },
                {
                    "selector": ":selected",
                    "css": {
                        "background-color": dark_color,
                        "line-color": dark_color,
                        "target-arrow-color": color,
                        "source-arrow-color": color,
                        "text-outline-color": color,
                    },
                },
            ]
        )

    def build_data(self):
        cy_nodes = self.data["nodes"]
        cy_edges = self.data["edges"]

        # Build Site
        for site_name, site in self.advertised_topology.sites.items():
            print("site_name: {}".format(site_name))
            cy_nodes.append(
                {
                    "data": {
                        "id": site_name,
                        "name": site_name,
                        "href": "http://cytoscape.org",
                    }
                }
            )

        # cy_edges.append({'data': { 'source': 'RENC', 'target': 'UKY' }})
        # cy_edges.append({'data': { 'source': 'UKY', 'target': 'LBNL' }})
        # cy_edges.append({'data': { 'source': 'LBNL', 'target': 'RENC' }})

        for link_name, link in self.advertised_topology.links.items():
            print("link_name {}, {}".format(link_name, link))
            print("\n\n Interfaces {}".format(link.interface_list))

            # Source
            source_interface = link.interface_list[0]
            source_parent = self.advertised_topology.get_parent_element(
                source_interface
            )
            source_node = self.advertised_topology.get_owner_node(source_parent)

            # Target
            target_interface = link.interface_list[1]
            target_parent = self.advertised_topology.get_parent_element(
                target_interface
            )
            target_node = self.advertised_topology.get_owner_node(target_parent)

            # Build edge
            cy_edges.append(
                {"data": {"source": source_node.name, "target": target_node.name}}
            )

    def setup_interaction(self):
        # out = Output()
        self.cytoscapeobj.on("node", "click", self.on_click)
        self.cytoscapeobj.on("node", "mouseover", self.on_mouseover)

    def on_click(self, node):
        with self.out:
            print("click: {}".format(str(node)))
            self.toggle_style()

    def on_mouseover(self, node):
        with self.out:
            print("mouseovers: {}".format(str(node)))

    def start(self):
        """
        Start the cytoeditor editors
        :return:
        """

        self.toggle_style()
        self.setup_interaction()
        self.build_data()
        self.cytoscapeobj.graph.add_graph_from_json(self.data)

        display(self.cytoscapeobj)
        display(self.out)

        # return self.out, self.cytoscapeobj
