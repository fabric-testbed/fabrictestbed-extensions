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

from fabrictestbed.slice_editor import ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
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




    def create_slice(self):
        slice_name="NVMEBenchmark"
        site_name="MAX"
        node_name='Node1'
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


        # Add node
        n1 = self.topology.add_node(name=node_name, site=site_name)

        # Set capacities
        cap = Capacities()
        cap.set_fields(core=cores, ram=ram, disk=disk)

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
                                                    ssh_key=self.ssh_key)




        if return_status == Status.OK:
            slice_id = slice_reservations[0].get_slice_id()
            print("Submitted slice creation request. Slice ID: {}".format(slice_id))
        else:
            print(f"Failure: {slice_reservations}")

        time.sleep(30)

        return_status, slices = self.slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])

        if return_status == Status.OK:
            self.slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
            self.slice = self.wait_for_slice(slice, progress=True)

        print()
        print("Slice Name : {}".format(self.slice.slice_name))
        print("ID         : {}".format(self.slice.slice_id))
        print("State      : {}".format(self.slice.slice_state))
        print("Lease End  : {}".format(self.slice.lease_end))

    def config_test(self):
        pass

    def run_test(self):
        pass

    def delete_slice(self):
        status, result = self.slice_manager.delete(slice_id=self.slice.slice_id)

        print("Response Status {}".format(status))
        print("Response received {}".format(result))


    def run(self):
        """
        Run the test
        :return:
        """
        print( list(ComponentModelType))
        print(self.advertised_topology)
        self.create_slice()
