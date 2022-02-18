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

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState


from .abc_test import AbcTest

from .. import images


class NVMEBenchmark(AbcTest):

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()




    def create_slice(self, slice_name, site_name, node_count=1):
        image = 'default_centos_8'
        image_type = 'qcow2'
        cores = 4
        ram = 8
        disk = 50
        model_type = ComponentModelType.NVME_P4510
        #nvme_component_type = ComponentType.NVME
        #nvme_model = 'P4510'
        nvme_name = 'nvme1'

        self.topology = ExperimentTopology()

        cap = Capacities(core=cores, ram=ram, disk=disk)

        for node_num in range(0, node_count):
            node_name="nvme-"+str(site_name)+"-"+str(node_num)
            # Add node
            n1 = self.topology.add_node(name=node_name, site=site_name)

            # Set Properties
            n1.set_properties(capacities=cap, image_type=image_type, image_ref=image)

            # Add the PCI NVMe device
            n1.add_component(model_type=model_type, name=nvme_name)
            #n1.add_component(ctype=nvme_component_type, model=nvme_model, name=nvme_name)

        # Generate Slice Graph
        slice_graph = self.topology.serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = self.slice_manager.create(slice_name=slice_name,
                                                    slice_graph=slice_graph,
                                                    ssh_key=self.node_ssh_key)




        if return_status == Status.OK:
            slice_id = slice_reservations[0].get_slice_id()
            #print("Submitted slice creation request. Slice ID: {}".format(slice_id))
        else:
            print(f"Failure: {slice_reservations}")

        #time.sleep(30)

        return_status, slices = self.slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])

        if return_status == Status.OK:
            self.slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
            #self.slice = self.wait_for_slice(slice, progress=True)

        #print()
        #print("Slice Name : {}".format(self.slice.slice_name))
        #print("ID         : {}".format(self.slice.slice_id))
        #print("State      : {}".format(self.slice.slice_state))
        #print("Lease End  : {}".format(self.slice.lease_end))

    def config_test(self):
        pass

    def run_test(self):

        for node_name, node in self.topology.nodes.items():
            #print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            #print("Node:")
            print(str(node_name) + " | ", end = '')
            try:
                #print("   Name              : {}".format(node_name))
                #print("   Cores             : {}".format(node.get_property(pname='capacity_allocations').core))
                #print("   RAM               : {}".format(node.get_property(pname='capacity_allocations').ram))
                #print("   Disk              : {}".format(node.get_property(pname='capacity_allocations').disk))
                #print("   Image             : {}".format(node.image_ref))
                #print("   Image Type        : {}".format(node.image_type))
                #print("   Host              : {}".format(node.get_property(pname='label_allocations').instance_parent))
                #print("   Site              : {}".format(node.site))
                #print("   Management IP     : {}".format(node.management_ip))
                #print("   Reservation ID    : {}".format(node.get_property(pname='reservation_info').reservation_id))
                #print("   Reservation State : {}".format(node.get_property(pname='reservation_info').reservation_state))
                #print("   Components        : {}".format(node.components))
                #print("   Interfaces        : {}".format(node.interfaces))
                #print()
                name = node_name
                reservation_id = node.get_property(pname='reservation_info').reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + '-' + name.lower()

                expected_stdout = 'Hello, FABRIC from node ' + hostname + '\n'

                #print("------------------------- Test Output ---------------------------")
                script= '#!/bin/bash  \n' \
                'lspci | grep NVMe \n'
                stdout_str = self.execute_script(node_username='centos', node=node, script=script)
                print(str(stdout_str.replace('\n','')) + " | ", end = '')
                #print("-----------------------------------------------------------------")
                #stdout_str = str(stdout.read(),'utf-8').replace('\\n','\n')
                if stdout_str == expected_stdout:
                    print('Success')
                else:
                    print('Fail')
                    #print('Fail: --{}--  --{}--'.format(expected_stdout,stdout_str))
            except Exception as e:
                print ("Error in test: Error {}".format(e))
                traceback.print_exc()



    def delete_slice(self):
        status, result = self.slice_manager.delete(slice_id=self.slice.slice_id)

        #print("Response Status {}".format(status))
        #print("Response received {}".format(result))

    def get_existing_slice(self, slice_name):
        #Get existing slice
        return_status, slices = self.slice_manager.slices(excludes=[SliceState.Dead, SliceState.Closing])

        if return_status == Status.OK:
            #for slice in slices:
            #    print("{}:".format(slice.slice_name))
            #    print("   ID         : {}".format(slice.slice_id))
            #    print("   State      : {}".format(slice.slice_state))
            #    print("   Lease End  : {}".format(slice.lease_end))
            #print("got Slice")
            pass
        else:
            print(f"Failure: {slices}")

        self.slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
        status, self.topology = self.slice_manager.get_slice_topology(slice_object=self.slice)
        if return_status == Status.OK:
            #print("got topology")
            pass
        else:
            print(f"Failure: {self.topology}")

        #print("Slice Name : {}".format(self.slice.slice_name))
        #print("ID         : {}".format(self.slice.slice_id))
        #print("State      : {}".format(self.slice.slice_state))
        #print("Lease End  : {}".format(self.slice.lease_end))

    def run_all(self, slice_name, sites=[], create_slice=True, run_test=True, delete=True, node_count=1):
        for site in sites:
            self.run(slice_name + "-" + site, create_slice=create_slice, run_test=run_test, delete=delete, site=site, node_count=node_count)


    def run(self, slice_name, create_slice=True, run_test=True, delete=True, site=None, node_count=1):
        """
        Run the test
        :return:
        """
        print("NVMe test, slice_name: {}, site: {}".format(slice_name,site))
        if create_slice:
            #print("Creating Slice")
            try:
                self.create_slice(slice_name,site,node_count=node_count)
                time.sleep(5)

                self.slice = self.wait_for_slice(self.slice, progress=True, timeout=300+(20*node_count))
                #time.sleep(10)

            except Exception as e:
                print("Create Slice FAILED. Error {}".format(e))
                traceback.print_exc()


        time.sleep(5*node_count)
        self.get_existing_slice(slice_name)
        #time.sleep(60)

        if run_test:
            try:
                #print("Run Test")
                self.run_test()
            except Exception as e:
                print("Run test FAILED. Error {}".format(e))
                traceback.print_exc()
        if delete:
            try:
                #print("Delete Slice")
                self.delete_slice()
            except:
                print("Delete FAILED")
