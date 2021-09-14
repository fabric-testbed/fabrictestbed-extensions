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
from abc import ABC, abstractmethod
from typing import List

from fabric_cf.orchestrator.orchestrator_proxy import SliceState
from fabrictestbed.slice_editor import Capacities, ComponentType, ComponentCatalog
from fabrictestbed.slice_manager import SliceManager


class AbcTopologyEditor(ABC):
    EXPERIMENT_STATE_UNSUBMITTED = "Unsubmitted"
    EXPERIMENT_STATE_SUBMITTED = "Submitted"
    EXPERIMENT_STATE_DELETING = "Deleting"

    DEFAULT_SLICE_SELECT_VALUE = '<Choose Slice>'

    def __init__(self):
        self.slice_manager = SliceManager()
        self.advertised_topology = None
        self.experiments = []
        self.current_experiment = None
        self.site_detail = False
        self.current_slice_name = None
        self.ssh_key = None
        with open(os.environ['HOME'] + "/.ssh/id_rsa.pub", "r") as fd:
            self.ssh_key = fd.read().strip()

    def update_capacities(self):
        """
        Update capacities from the available resources information
        :return:
        """
        # CREATE CURRENT CAPACITIES DICT
        print('Update Capacities')
        capacities = {}

        for t in self.advertised_topology.sites.values():

            # name
            site_name = t.name
            # available capacities total vs. currently allocated ones
            available_capacities = t.get_property("capacities")
            allocated_capacities = t.get_property("capacity_allocations")

            if allocated_capacities is None:
                allocated_capacities = Capacities()

            if available_capacities is None:
                available_capacities = Capacities()

            d1 = available_capacities.__dict__.copy()
            d2 = allocated_capacities.__dict__.copy()

            # remove capacities that are not available
            for d in allocated_capacities.__dict__:
                if d1[d] == 0 and d2[d] == 0:
                    d1.pop(d)
                    d2.pop(d)

            # add available capacities to site
            site_capacities = {}
            for c in d1:
                site_capacities[c] = d1[c] - d2[c]

            capacities[site_name] = site_capacities

        return capacities

    def update_slice_list(self, current_slice_name=None, excludes=[SliceState.Dead, SliceState.Closing]) -> List[str]:
        """
        Update Slice list
        :param current_slice_name:
        :param excludes:
        :return:
        """
        # Get all existing slices from FABRIC slice_manager
        status, existing_slices = self.slice_manager.slices(excludes=excludes)

        # Create new list of slices
        new_experiments_list = []
        for slice in existing_slices:
            experiment = {'slice_name': slice.slice_name, 'slice_id': slice.slice_id, 'slice_state': slice.slice_state,
                          'lease_end': slice.lease_end, 'graph_id': slice.graph_id, 'slice': slice}

            status, current_slice_topology = self.slice_manager.get_slice_topology(slice_object=slice)
            experiment['topology'] = current_slice_topology

            new_experiments_list.append(experiment)

        # Add all unsubmitted experiments
        for experiment in self.experiments:
            if experiment['slice_state'] == self.EXPERIMENT_STATE_UNSUBMITTED:
                new_experiments_list.append(experiment)

        # Set experiments list
        self.experiments = new_experiments_list

        # Build slice name list for widget
        self.current_experiment = None
        slice_names = []
        for experiment in self.experiments:
            slice_names.append(experiment['slice_name'])
            if current_slice_name is not None and experiment['slice_name'] == current_slice_name:
                self.current_experiment = experiment

        if len(slice_names) == 0:
            slice_names = [self.DEFAULT_SLICE_SELECT_VALUE]

        # Set current experiment
        print("current_slice_name: " + str(current_slice_name))
        print("self.experiments: " + str(self.experiments))

        # If there is no slice to set then set the first one in the list
        if current_slice_name is None and self.experiments is not None and len(self.experiments) > 0:
            current_slice_name = sorted(slice_names)[0]

        if self.experiments is not None and len(self.experiments) > 0:
            self.current_experiment = list(filter(lambda experiment: experiment['slice_name'] == current_slice_name,
                                                  self.experiments))[0]

        return slice_names

    @staticmethod
    def get_component_type_list():
        """
        Get component type list
        :return:
        """
        return_list = []
        for type in ComponentType:
            return_list.append(type.name)
        return return_list

    @staticmethod
    def get_component_model_list(type=None):
        """
        Get component model list
        :param type:
        :return:
        """
        if type is None:
            return ComponentCatalog.catalog_instance.copy()
        else:
            return list(filter(lambda x: x['Type'] == type, ComponentCatalog.catalog_instance))

    @staticmethod
    def get_component_widget_options_list(type=None):
        """
        Get component widget options list
        :param type:
        :return:
        """
        return_list = []
        for component in AbcTopologyEditor.get_component_model_list(type):
            return_list.append(component['Model'] + " (" + component['Type'] + ")")

        return return_list

    def get_node_name_list(self):
        """
        Get node name list
        :return:
        """
        if self.current_experiment:
            return list(self.current_experiment['topology'].nodes)
        else:
            return []

    def get_unique_node_name(self):
        """
        Get Unique node name
        :return:
        """
        # need to go through all the nodes in the experiment
        num = 1
        name = 'node' + str(num)
        while name in self.current_experiment['topology'].nodes:
            num += 1
            name = 'node' + str(num)

        return name

    @abstractmethod
    def start(self):
        """
        Start the editors
        :return:
        """