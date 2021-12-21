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

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, CapacityHints, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState

#from .slicex import SliceX
#from .nodex import NodeX
#from .fabricx import FabricX

from .abc_fablib import AbcFabLIB

from .. import images

from fabrictestbed_extensions.fablib.fablib import fablib


class Slice(AbcFabLIB):

    def __init__(self, name=None):
        """
        Constructor
        :return:
        """
        super().__init__()
        #print(f"Creating Slice: Name: {name}, Slice: {slice}")
        self.slice_name = name
        self.sm_slice = None
        self.slice_id = None
        self.topology = None

    @staticmethod
    def new_slice(name=None):
         slice = Slice(name=name)
         slice.topology = ExperimentTopology()
         return slice

    @staticmethod
    def get_slice(sm_slice=None):
        slice = Slice(name=sm_slice.slice_name)
        slice.sm_slice = sm_slice
        slice.slice_id = sm_slice.slice_id
        slice.slice_name = sm_slice.slice_name
        slice.topology = fablib.slice_manager.get_slice_topology(slice_object=slice.sm_slice)

        slice.update()
        return slice

    def get_fim_topology(self):
        return self.topology

    def update_slice(self):
        #Update slice
        return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])
        if return_status == Status.OK:
            self.sm_slice = list(filter(lambda x: x.slice_name == self.slice_name, slices))[0]
            self.slice_id = self.sm_slice.slice_id
        else:
            raise Exception("Failed to get slice list: {}, {}".format(return_status, slices))


    def update_topology(self):
        #Update topology
        return_status, new_topo = fablib.get_slice_manager().get_slice_topology(slice_object=self.sm_slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slice topology: {}, {}".format(return_status, new_topo))

        #Set slice attibutes
        self.topology = new_topo

    def update(self):
        self.update_slice()
        self.update_topology()

    def get_name(self):
        return self.slice_name

    def get_slice_id(self):
        return self.slice_id

    def get_lease_end(self):
        return self.sm_slice.lease_end

    def add_l2network(self, name=None, interfaces=[]):
        from fabrictestbed_extensions.fablib.network_service import NetworkService
        return NetworkService.new_l2network(slice=self, name=name, interfaces=interfaces)

    def add_node(self, name, site):
        from fabrictestbed_extensions.fablib.node import Node
        return Node.new_node(slice=self, name=name, site=site)

    def get_nodes(self):
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()

        return_nodes = []

        #fails for topology that does not have nodes
        try:
            for node_name, node in self.topology.nodes.items():
                return_nodes.append(Node.get_node(self,node))
        except Exception as e:
            print("get_nodes: exception")
            traceback.print_exc()
            pass
        return return_nodes

    def get_node(self, name, verbose=False):
        from fabrictestbed_extensions.fablib.node import Node
        #self.update()
        try:
            return Node(self.topology.nodes[name])
        except Exception as e:
            if verbose:
                traceback.print_exc()
            raise Exception(f"Node not found: {name}")

    def get_l2networks(self, verbose=False):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_services(self)
        except Exception as e:
            if verbose:
                traceback.print_exc()
        return None

    def get_l2network(self, name=None, verbose=False):
        from fabrictestbed_extensions.fablib.network_service import NetworkService

        try:
            return NetworkService.get_l2network_service(self,name)
        except Exception as e:
            if verbose:
                traceback.print_exc()
        return None

    def submit(self, wait=False, wait_timeout=360, wait_interval=10, wait_progress=False):
        from fabrictestbed_extensions.fablib.fablib import fablib
        fabric = fablib()

        # Generate Slice Graph
        slice_graph = self.topology.serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = fablib.get_slice_manager().create(slice_name=self.slice_name,
                                                                slice_graph=slice_graph,
                                                                ssh_key=self.slice_public_key)
        if return_status != Status.OK:
            raise Exception("Failed to submit slice: {}, {}".format(return_status, slice_reservations))


        time.sleep(10)
        self.update_slice()

        if wait or wait_progress:
            self.wait(timeout=wait_timeout,interval=wait_interval,progress=wait_progress)

    def delete(self):
        return_status, result = fablib.get_slice_manager().delete(slice_object=self.sm_slice)

        if return_status != Status.OK:
            raise Exception("Failed to delete slice: {}, {}".format(return_status, result))

        self.topology = None

    def renew(self, end_date):

        return_status, result = fablib.get_slice_manager().renew(slice_object=self.sm_slice,
                                     new_lease_end_time = end_date)

        if return_status != Status.OK:
            raise Exception("Failed to renew slice: {}, {}".format(return_status, result))

    def wait(self, timeout=360,interval=10,progress=False):
        slice_name=self.sm_slice.slice_name
        slice_id=self.sm_slice.slice_id

        timeout_start = time.time()
        slice = self.sm_slice

        if progress: print("Waiting for slice .", end = '')
        while time.time() < timeout_start + timeout:
            return_status, slices = fablib.get_slice_manager().slices(excludes=[SliceState.Dead,SliceState.Closing])

            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
                if slice.slice_state == "StableOK":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if slice.slice_state == "Closing" or slice.slice_state == "Dead" or slice.slice_state == "StableError":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
            else:
                print(f"Failure: {slices}")

            if progress: print(".", end = '')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
            return slice

        #Update the fim topology (wait to avoid get topology bug)
        time.sleep(interval)
        self.update()
