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

from abc import ABC, abstractmethod
from typing import List

from fabric_cf.orchestrator.orchestrator_proxy import SliceState
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
from fabrictestbed.slice_editor import ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, ComponentCatalog

class AbcTopologyEditor(ABC):
    EXPERIMENT_STATE_UNSUBMITTED = "unsubmitted"
    EXPERIMENT_STATE_LIVE = "live"
    EXPERIMENT_STATE_ERROR = "error"
    EXPERIMENT_STATE_DELETED = "deleted or error"

    DEFAULT_SLICE_SELECT_VALUE = '<Choose Slice>'




    def __init__(self):
        self.slice_manager = SliceManager()
        self.advertised_topology = None
        self.experiments = []
        self.current_experiment = None
        self.site_detail = False
        self.ssh_key = None
        with open(os.environ['HOME'] + "/.ssh/id_rsa.pub", "r") as fd:
            self.ssh_key = fd.read().strip()

        self.pull_advertised_topology()
        self.update_experiment_list()

    def pull_advertised_topology(self):
        return_status, self.advertised_topology = self.slice_manager.resources()
        if return_status != Status.OK:
            print("Failed to get advertised_topology: {}".format(self.advertised_topology))


    def remove_experiment(self, experiment):
        """
        Remove and exeriment from the editor.
        Does not delete the slice.
        :param experiment:
        :return:
        """
        #Unset current experiment
        if(experiment == self.current_experiment):
            self.current_experiment = None

        #remove the experiment
        self.experiments.remove(experiment)

    def delete_experiment(self, experiment):
        print('Delete Slice')
        if experiment['editor_slice_state'] != self.EXPERIMENT_STATE_UNSUBMITTED:
            try:
                print("self.current_experiment: " + str(self.current_experiment))
                print("self.experiments: " + str(self.experiments))

                #delete the slice
                result = self.slice_manager.delete(slice_object=experiment['slice'])

                experiment['editor_slice_state'] = self.EXPERIMENT_STATE_DELETED

                # TODO eliminate race condition... need to update until delete instead of sleep
                import time
                time.sleep(1)

            except Exception as e:
                # TODO: Should create popup or other user facing error message
                print('Failed to delete slice. Error: ' + str(e))
                traceback.print_exc()

        #Remove experiment from editor
        self.remove_experiment(experiment)


    def create_experiment(self, slice_name):
        print('Create Experiment')

        experiment = self.get_experiment_by_name(slice_name)

        if experiment != None:
            # TODO: should raise Exception
            print('Failed to create new slice. Error: Name not unique or invalid ' + str(slice_name))
            return

        #New experiment
        self.experiments.append({'slice_name': slice_name,
                                 'editor_slice_state': self.EXPERIMENT_STATE_UNSUBMITTED,
                                 'topology': ExperimentTopology()
                                 #ssh_keys
                                 #detail_levels {'detail': HIGH, {'node1': LOW, 'node2': MED}}
                                 })

    def set_current_experiment(self, experiment):
        self.current_experiment = experiment

    def add_node(self, node_name):
        print("abc.add_node  node_name {}".format(node_name))

        # Add to FABRIC experiment topology
        new_node = self.current_experiment['topology'].add_node(name=node_name, site=self.DEFAULT_NODE_SITE_VALUE)
        cap = Capacities(core=self.DEFAULT_NODE_CORE_VALUE, ram=self.DEFAULT_NODE_RAM_VALUE,
                       disk=self.DEFAULT_NODE_DISK_VALUE)
        new_node.set_properties(capacities=cap, image_type=self.DEFAULT_NODE_IMAGE_TYPE_VALUE,
                                image_ref=self.DEFAULT_NODE_IMAGE_VALUE)

    def delete_node(self, node_name):
        """
        Delete node
        :param node_name: node name
        :return:
        """
        print('Delete Node')
        try:
            # Delete the node from experiment
            self.current_experiment['topology'].remove_node(node_name)
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to delete node. Error: ' + str(e))
            traceback.print_exc()

    def save_node(self, topology_node,
                        experiment=None,
                        node_name=None,
                        site_name=None,
                        cores=None,
                        ram=None,
                        disk=None,
                        image=None,
                        image_type=None):
        """
        Save node
        :param node_name:
        :param site_name:
        :param cores:
        :param ram:
        :param disk:
        :param image:
        :param image_type:
        :return:
        """
        print("ABC.save_node")
        print("save_node: topology_node {}".format(topology_node))
        print("save_node: experiment {}".format(experiment))
        print("save_node:  node_name {}".format(node_name))
        print("save_node:  site_name {}".format(site_name))
        print("save_node:  cores {}".format(cores))
        print("save_node:  ram {}".format(ram))
        print("save_node:  disk {}".format(disk))
        print("save_node:  image {}".format(image))
        print("save_node:  image_type {}".format(image_type))

        if experiment == None:
            experiment = self.current_experiment

        try:
            #node = experiment['topology'].nodes[node_name]

            # Save node properties to FABRIC topology
            if node_name:
                topology_node.set_property(pname="name", pval=node_name)
            if site_name:
                topology_node.set_property(pname="site", pval=site_name)

            # Set capacities
            cap = Capacities(core=cores, ram=ram, disk=disk)
            topology_node.set_properties(capacities=cap, image_type=image_type, image_ref=image)
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to save node. Error: ' + str(e))
            traceback.print_exc()

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

    def add_component(self, component_name, model_type, node=None):
        if node == None:
            node = self.current_node
        if component_name == None:
            component_name = self.get_unique_component_name()

        print("abc.add_component  component_name {}".format(component_name))
        node.add_component(model_type=model_type, name=component_name)

    def get_experiment_by_slice_id(self, slice_id):
        experiment = None
        try:
             experiment = list(filter(lambda x: x['slice_id'] == slice_id, self.experiments))[0]
        except:
            print("Slice {} not found".format(slice_id))
        return experiment

    def get_experiment_by_name(self, slice_name):
        experiment = None
        try:
             experiment = list(filter(lambda x: x['slice_name'] == slice_name, self.experiments))[0]
        except:
            print("Slice {} not found".format(slice_name))
        return experiment


    def pull_experiment_topology(self, experiment):
        #do not update if unsubmitted
        if experiment['editor_slice_state'] != self.EXPERIMENT_STATE_UNSUBMITTED:
            status, current_slice_topology = self.slice_manager.get_slice_topology(slice_object=experiment['slice'])
            experiment['topology'] = current_slice_topology

    def update_current_experiment(self):
        update_experiment_topology(self.current_experiment)

    def update_all_experiment_topologies(self):
        for experiment in self.experiments:
            update_experiment_topology(experiment)



    def update_experiment_list(self, current_slice_name=None, excludes=[SliceState.Dead, SliceState.Closing]) -> List[str]:
        """
        Update Slice list
        :param current_slice_name:
        :param excludes:
        :return:
        """
        print("XXXXXXXXXX update_experiment_list XXXXXXXXXX")

        # Get all existing slices from FABRIC slice_manager
        status, existing_slices = self.slice_manager.slices(excludes=excludes)

        # TODO: Remove this
        if status != Status.OK:
            print("slice_manager.slices: Status: {}, Error: {}".format(status,existing_slices))
            existing_slices = []



        # Create new list of slices
        #new_experiments_list = []
        for slice in existing_slices:
            experiment = self.get_experiment_by_name(slice.slice_name)

            if experiment == None:
                #New experiment
                print("Getting topology for new slice")
                experiment = {'slice_name': slice.slice_name,
                              'slice_id': slice.slice_id,
                              'editor_slice_state': self.EXPERIMENT_STATE_LIVE,
                              'slice': slice,
                              #ssh_keys
                              #detail_levels {'detail': HIGH, {'node1': LOW, 'node2': MED}}
                              }

                status, experiment['topology'] = self.slice_manager.get_slice_topology(slice_object=slice)
                if status != Status.OK:
                    print("Failed to get topology for slice found on FABRI: Status: {}, Error: {}".format(status,experiment['topology']))

                self.experiments.append(experiment)
            else:
                #Existing experiment
                print("Getting topology for old slice")

                experiment['slice'] = slice
                #experiment['editor_slice_state'] = slice.slice_state
                status, experiment['topology'] = self.slice_manager.get_slice_topology(slice_object=slice)
                if status != Status.OK:
                    print("Failed to get topology for existing slice: Status: {}, Error: {}".format(status,experiment['topology']))

        # Mark submitted slices that are missing from FABRIC with error or Deleted
        status, all_slices = self.slice_manager.slices(includes=excludes)
        if status != Status.OK:
            print("Failed to get all_slices: Status: {}, Error: {}".format(status,all_slices))

        for experiment in self.experiments:
            #Skip unsubmitted slices
            if experiment['editor_slice_state'] == self.EXPERIMENT_STATE_UNSUBMITTED:
                continue

            print("experiment: {} ".format(experiment))
            found_experiment = list(filter(lambda x: x.slice_id == experiment['slice_id'], all_slices))
            if len(found_experiment) > 0:
                found_experiment = found_experiment[0]
            if found_experiment:
                print("found_experiment state: {}".format(found_experiment.slice_state))
                if found_experiment.slice_state == str(SliceState.Dead) or found_experiment.slice_state == str(SliceState.Closing):
                    #TODO need to deistinguish between error and deleted
                    experiment['editor_slice_state'] = self.EXPERIMENT_STATE_DELETED
                    experiment['slice'] = found_experiment
                else:
                    experiment['editor_slice_state'] = self.EXPERIMENT_STATE_LIVE
                    experiment['slice'] = found_experiment






    def submit_slice(self, experiment):

        slice_name = self.current_experiment['slice_name']
        #ssh_key = self.current_experiment['ssh_key']
        slice_graph = self.current_experiment['topology'].serialize()

        # Request slice from Orchestrator
        status, reservations = self.slice_manager.create(slice_name=slice_name,
                                                         slice_graph=slice_graph,
                                                         ssh_key=self.ssh_key)
        print("Response Status {}".format(status))
        if status == Status.OK:
            print("Reservations created {}".format(reservations))
        else:
            print(f"Failure: {reservations}")

        self.current_experiment['slice_id'] = reservations[0].slice_id
        self.current_experiment['editor_slice_state'] = self.EXPERIMENT_STATE_LIVE

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

    # def get_unique_component_name(self):
    #     """
    #     Get unique component name
    #     :return:
    #     """
    #     num = 1
    #     name = 'dev' + str(num)
    #     while len(list(filter(lambda x: x['component_name_widget'].value == name,
    #                           self.dashboards['node_dashboard']['components']))) > 0:
    #         num += 1
    #         name = 'dev' + str(num)
    #
    #     return name

    def get_unique_component_name(self, node=None):
        """
        Get unique component name
        :return:
        """
        if node == None:
            node = self.current_node

        num = 1
        name = 'dev' + str(num)
        for component_name, component in node.components.items():
            if name == component_name:
                num += 1
                name = 'node' + str(num)
            else:
                break

        return name

    @abstractmethod
    def start(self):
        """
        Start the editors
        :return:
        """
