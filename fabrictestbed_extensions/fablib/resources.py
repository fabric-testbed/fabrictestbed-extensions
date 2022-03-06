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
import time
import logging
from tabulate import tabulate


import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState


from .. import images

from fabrictestbed_extensions.fablib.fablib import fablib


class Resources():

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.topology = None
        self.update()

    def __str__(self):
        return str(self.topology)

    def update(self):
        return_status, topology = fablib.get_slice_manager().resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))

        self.topology = topology

    def get_topology(self, update=False):
        if update or self.topology == None: self.update()

        return self.topology

    def get_site_list(self, update=False):
        if update or self.topology == None: self.update()

        rtn_sites = []
        for site_name, site in self.topology.sites.items():
            rtn_sites.append(site_name)
            # site.get_property("location").to_latlon()
            #site.get_property("name")
            #print(f"{ site.get_property('cores')}")

        return rtn_sites

    def get_link_list(self, update=False):
        if update: self.update()

        rtn_links = []
        for link_name, link in self.topology.links.items():
            rtn_links.append(link_name)

        return rtn_links

        #Source
        #source_interface = link.interface_list[0]
        #source_parent = self.advertised_topology.get_parent_element(source_interface)
        #source_node=self.advertised_topology.get_owner_node(source_parent)
        #Target
        #target_interface = link.interface_list[1]
        #target_parent = self.advertised_topology.get_parent_element(target_interface)
        #target_node=self.advertised_topology.get_owner_node(target_parent)
