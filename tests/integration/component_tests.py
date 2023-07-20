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

import functools
import importlib.resources as pkg_resources
import os
import re
import time
import traceback
from typing import List

from abc_test import AbcTest
from fabrictestbed.slice_editor import (
    Capacities,
    ComponentCatalog,
    ComponentModelType,
    ComponentType,
    ExperimentTopology,
    Labels,
    ServiceType,
)
from fabrictestbed.slice_manager import SliceManager, SliceState, Status

from fabrictestbed_extensions import images

from .abc_test import AbcTest


class ComponentTest(AbcTest):
    COMPONENT_MODELS = {
        "GPU_Tesla_T4": ComponentModelType.GPU_Tesla_T4,
        "GPU_RTX6000": ComponentModelType.GPU_RTX6000,
        "GPU_A30": ComponentModelType.GPU_A30,
        "GPU_A40": ComponentModelType.GPU_A40,
        "SharedNIC_ConnectX_6": ComponentModelType.SharedNIC_ConnectX_6,
        "SmartNIC_ConnectX_6": ComponentModelType.SmartNIC_ConnectX_6,
        "SmartNIC_ConnectX_5": ComponentModelType.SmartNIC_ConnectX_5,
        "NVME_P4510": ComponentModelType.NVME_P4510,
        "FPGA_Xilinx_U280": ComponentModelType.FPGA_Xilinx_U280,
    }

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

    def create_slice(
        self, name_prefix="component_test", model_type=None, site_name="", node_count=1
    ):
        image = "default_centos_8"
        image_type = "qcow2"
        cores = 2
        ram = 2
        disk = 2
        # model_type = ComponentModelType.GPU_Tesla_T4
        # Tesla_T4_component_type = ComponentType.Tesla_T4
        # Tesla_T4_model = 'P4510'
        # Tesla_T4_name = 'gpu1'
        component_name = "dev1"
        component_model_name = str(model_type).split(".", 1)[1]

        topology = ExperimentTopology()

        cap = Capacities(core=cores, ram=ram, disk=disk)

        slice_name = name_prefix + "-" + component_model_name + "-" + str(site_name)

        for node_num in range(0, node_count):
            # node_name=slice_name+"-"+str(node_num)
            node_name = "node" + str(node_num)
            # Add node
            n1 = topology.add_node(name=node_name, site=site_name)

            # Set Properties
            n1.set_properties(capacities=cap, image_type=image_type, image_ref=image)

            # Add the PCI Tesla_T4 device
            n1.add_component(model_type=model_type, name=component_name)
            # n1.add_component(ctype=Tesla_T4_component_type, model=Tesla_T4_model, name=Tesla_T4_name)

        # Generate Slice Graph
        slice_graph = topology.serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = self.slice_manager.create(
            slice_name=slice_name, slice_graph=slice_graph, ssh_key=self.node_ssh_key
        )

        if return_status == Status.OK:
            slice_id = slice_reservations[0].get_slice_id()
            # print("Submitted slice creation request. Slice ID: {}".format(slice_id))
        else:
            print(f"Failure: {slice_reservations}")

        # time.sleep(30)

        return_status, slices = self.slice_manager.slices(
            excludes=[SliceState.Dead, SliceState.Closing]
        )

        if return_status == Status.OK:
            self.slices.append(
                list(filter(lambda x: x.slice_name == slice_name, slices))[0]
            )
            # self.slice = self.wait_for_slice(slice, progress=True)

        # print()
        # print("Slice Name : {}".format(self.slice.slice_name))
        # print("ID         : {}".format(self.slice.slice_id))
        # print("State      : {}".format(self.slice.slice_state))
        # print("Lease End  : {}".format(self.slice.lease_end))

    def config_test_GPU_RTX6000(self, node):
        node_name = node.name
        try:
            name = node_name
            management_ip = node.management_ip

            # print("------------------------- Test Output ---------------------------")
            script = "#!/bin/bash  \n" "sudo yum install -y pciutils \n"
            try:
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print("Config Done | ", end="")
            except Exception as e:
                print("Config Fail {} | ".format(str(e)), end="")
        except Exception as e:
            print("Error in test: Error {}".format(e), end="")
            traceback.print_exc()

    def run_test_GPU_RTX6000(self, slice):
        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "config_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            print(str(slice.slice_name) + " | " + str(node_name) + " | ", end="")
            self.config_test_GPU_RTX6000(node)
            try:
                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                expected_stdout = "3D controller: NVIDIA Corporation TU102GL [Quadro RTX 6000/8000] (rev a1)"

                script = "#!/bin/bash  \n" """lspci | grep NVIDIA \n"""
                #'lspci \| grep \"3D controller: NVIDIA Corporation TU104GL [Tesla T4]\" \n'
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", ""))[0:45] + "... | ", end="")
                if expected_stdout in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    print(stdout_str)
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def config_test_NVME_P4510(self, node):
        node_name = node.name
        try:
            name = node_name
            management_ip = node.management_ip

            # print("------------------------- Test Output ---------------------------")
            script = "#!/bin/bash  \n" "sudo yum install -y pciutils \n"
            try:
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print("Config Done | ", end="")
            except Exception as e:
                print("Config Fail {} | ".format(str(e)), end="")
        except Exception as e:
            print("Error in test: Error {}".format(e), end="")
            traceback.print_exc()

    def run_test_NVME_P4510(self, slice):
        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "config_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            print(str(slice.slice_name) + " | " + str(node_name) + " | ", end="")
            self.config_test_NVME_P4510(node)
            try:
                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                # There are two types of NVMe
                expected_stdout1 = "Non-Volatile memory controller: Intel Corporation NVMe Datacenter SSD [3DNAND, Beta Rock Controller]"
                expected_stdout2 = "Non-Volatile memory controller: Toshiba Corporation NVMe SSD Controller Cx5 (rev 01)"
                script = "#!/bin/bash  \n" """lspci | grep NVMe \n"""
                #'lspci \| grep \"3D controller: NVIDIA Corporation TU104GL [Tesla T4]\" \n'
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", ""))[0:45] + "... | ", end="")
                if expected_stdout1 in stdout_str or expected_stdout2 in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    print(stdout_str)
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def config_test_SmartNIC_ConnectX_5(self, node):
        node_name = node.name
        try:
            name = node_name
            management_ip = node.management_ip

            # print("------------------------- Test Output ---------------------------")
            script = "#!/bin/bash  \n" "sudo yum install -y pciutils \n"
            try:
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print("Config Done | ", end="")
            except Exception as e:
                print("Config Fail {} | ".format(str(e)), end="")
        except Exception as e:
            print("Error in test: Error {}".format(e), end="")
            traceback.print_exc()

    def run_test_SmartNIC_ConnectX_5(self, slice):
        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "config_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            print(str(slice.slice_name) + " | " + str(node_name) + " | ", end="")
            self.config_test_SmartNIC_ConnectX_5(node)
            try:
                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                expected_stdout = "Ethernet controller: Mellanox Technologies MT27800 Family [ConnectX-5]"

                script = "#!/bin/bash  \n" """lspci | grep ConnectX \n"""
                #'lspci \| grep \"3D controller: NVIDIA Corporation TU104GL [Tesla T4]\" \n'
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", ""))[0:45] + "... | ", end="")
                if expected_stdout in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    print(stdout_str)
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def config_test_SmartNIC_ConnectX_6(self, node):
        node_name = node.name
        try:
            name = node_name
            management_ip = node.management_ip

            # print("------------------------- Test Output ---------------------------")
            script = "#!/bin/bash  \n" "sudo yum install -y pciutils \n"
            try:
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print("Config Done | ", end="")
            except Exception as e:
                print("Config Fail {} | ".format(str(e)), end="")
        except Exception as e:
            print("Error in test: Error {}".format(e), end="")
            traceback.print_exc()

    def run_test_SmartNIC_ConnectX_6(self, slice):
        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "config_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            # print(" Test: SmartNIC_ConnectX_6 | " + str(slice.slice_name) + " | " + str(node_name) + " | ", end = '')
            print(str(slice.slice_name) + " | " + str(node_name) + " | ", end="")

            self.config_test_SmartNIC_ConnectX_6(node)
            try:
                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                expected_stdout = "Ethernet controller: Mellanox Technologies MT28908 Family [ConnectX-6]"

                script = "#!/bin/bash  \n" """lspci | grep ConnectX-6 \n"""
                #'lspci \| grep \"3D controller: NVIDIA Corporation TU104GL [Tesla T4]\" \n'
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", ""))[0:45] + "...  | ", end="")
                if expected_stdout in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    print(stdout_str)
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def config_test_SharedNIC_ConnectX_6(self, node):
        node_name = node.name
        try:
            name = node_name
            management_ip = node.management_ip

            # print("------------------------- Test Output ---------------------------")
            script = "#!/bin/bash  \n" "sudo yum install -y pciutils \n"
            try:
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print("Config Done | ", end="")
            except Exception as e:
                print("Config Fail {} | ".format(str(e)), end="")
        except Exception as e:
            print("Error in test: Error {}".format(e), end="")
            traceback.print_exc()

    def run_test_SharedNIC_ConnectX_6(self, slice):
        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "config_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            print(str(slice.slice_name) + " | " + str(node_name) + " | ", end="")
            self.config_test_SharedNIC_ConnectX_6(node)
            try:
                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                expected_stdout = "Ethernet controller: Mellanox Technologies MT28908 Family [ConnectX-6 Virtual Function]"

                script = "#!/bin/bash  \n" """lspci | grep ConnectX-6 \n"""
                #'lspci \| grep \"3D controller: NVIDIA Corporation TU104GL [Tesla T4]\" \n'
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", ""))[0:45] + "... | ", end="")
                if expected_stdout in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    print(stdout_str)
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def config_test_GPU_Tesla_T4(self, node):
        node_name = node.name
        # print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        # print("Node:")
        # print("Config | ", end = '')
        # print(str(node_name) + " | ", end = '')
        try:
            # print("{}".format(str(node_name)) + " | ", end = '')

            # print("   Name              : {}".format(node_name))
            # print("   Cores             : {}".format(node.get_property(pname='capacity_allocations').core))
            # print("   RAM               : {}".format(node.get_property(pname='capacity_allocations').ram))
            # print("   Disk              : {}".format(node.get_property(pname='capacity_allocations').disk))
            # print("   Image             : {}".format(node.image_ref))
            # print("   Image Type        : {}".format(node.image_type))
            # print("   Host              : {}".format(node.get_property(pname='label_allocations').instance_parent))
            # print("{}".format(str(node.get_property(pname='label_allocations').instance_parent)).replace('\n','') + " | ", end = '')
            # print("   Site              : {}".format(node.site))
            # print("{}".format(str(node.management_ip)).replace('\n','') + " | ", end = '')

            # print("   Management IP     : {}".format(node.management_ip))
            # print("   Reservation ID    : {}".format(node.get_property(pname='reservation_info').reservation_id))
            # print("   Reservation State : {}".format(node.get_property(pname='reservation_info').reservation_state))
            # print("   Components        : {}".format(node.components))
            # print("   Interfaces        : {}".format(node.interfaces))
            # print()
            name = node_name
            management_ip = node.management_ip

            # print("------------------------- Test Output ---------------------------")
            script = "#!/bin/bash  \n" "sudo yum install -y pciutils \n"
            try:
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print("Config Done | ", end="")
            except Exception as e:
                print("Config Fail {} | ".format(str(e)), end="")
            # print(str(stdout_str.replace('\n','')) + " | ", end = '')
            # print("-----------------------------------------------------------------")
            # stdout_str = str(stdout.read(),'utf-8').replace('\\n','\n')
        except Exception as e:
            print("Error in test: Error {}".format(e), end="")
            traceback.print_exc()

    def run_test_GPU_Tesla_T4(self, slice):
        # self.config_test(slice)

        return_status, topology = self.slice_manager.get_slice_topology(
            slice_object=slice
        )
        if return_status != Status.OK:
            raise Exception(
                "config_test failed to get topology. slice; {}, error {}".format(
                    str(slice), str(topology)
                )
            )

        for node_name, node in topology.nodes.items():
            # print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            # print("Node:")
            # print(str(node_name) + " | ", end = '')
            print(str(slice.slice_name) + " | " + str(node_name) + " | ", end="")
            self.config_test_GPU_Tesla_T4(node)
            try:
                # print("   Name              : {}".format(node_name))
                # print("   Cores             : {}".format(node.get_property(pname='capacity_allocations').core))
                # print("   RAM               : {}".format(node.get_property(pname='capacity_allocations').ram))
                # print("   Disk              : {}".format(node.get_property(pname='capacity_allocations').disk))
                # print("   Image             : {}".format(node.image_ref))
                # print("   Image Type        : {}".format(node.image_type))
                # print("   Host              : {}".format(node.get_property(pname='label_allocations').instance_parent))
                # print("   Site              : {}".format(node.site))
                # print("   Management IP     : {}".format(node.management_ip))
                # print("   Reservation ID    : {}".format(node.get_property(pname='reservation_info').reservation_id))
                # print("   Reservation State : {}".format(node.get_property(pname='reservation_info').reservation_state))
                # print("   Components        : {}".format(node.components))
                # print("   Interfaces        : {}".format(node.interfaces))
                # print()
                print(
                    "{}".format(
                        str(
                            node.get_property(pname="label_allocations").instance_parent
                        )
                    ).replace("\n", "")
                    + " | ",
                    end="",
                )
                print(
                    "{}".format(str(node.management_ip)).replace("\n", "") + " | ",
                    end="",
                )

                name = node_name
                reservation_id = node.get_property(
                    pname="reservation_info"
                ).reservation_id
                management_ip = node.management_ip

                hostname = reservation_id + "-" + name.lower()

                expected_stdout = (
                    "3D controller: NVIDIA Corporation TU104GL [Tesla T4] (rev a1)"
                )

                # print("------------------------- Test Output ---------------------------")
                script = "#!/bin/bash  \n" """lspci | grep Tesla \n"""
                #'lspci \| grep \"3D controller: NVIDIA Corporation TU104GL [Tesla T4]\" \n'
                stdout_str = self.execute_script(
                    node_username="centos", node=node, script=script
                )
                print(str(stdout_str.replace("\n", ""))[0:45] + "... | ", end="")
                # print("-----------------------------------------------------------------")
                # stdout_str = str(stdout.read(),'utf-8').replace('\\n','\n')
                if expected_stdout in stdout_str:
                    print("Success")
                else:
                    print("Fail")
                    print(stdout_str)
            except Exception as e:
                print("Error in test: Error {}".format(e))
                traceback.print_exc()

    def delete_slice(self):
        status, result = self.slice_manager.delete(slice_id=self.slice.slice_id)

        # print("Response Status {}".format(status))
        # print("Response received {}".format(result))

    def get_existing_slice(self, slice_name):
        # Get existing slice
        return_status, slices = self.slice_manager.slices(
            excludes=[SliceState.Dead, SliceState.Closing]
        )

        if return_status == Status.OK:
            # for slice in slices:
            #    print("{}:".format(slice.slice_name))
            #    print("   ID         : {}".format(slice.slice_id))
            #    print("   State      : {}".format(slice.slice_state))
            #    print("   Lease End  : {}".format(slice.lease_end))
            # print("got Slice")
            pass
        else:
            print(f"Failure: {slices}")

        self.slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
        status, self.topology = self.slice_manager.get_slice_topology(
            slice_object=self.slice
        )
        if return_status == Status.OK:
            # print("got topology")
            pass
        else:
            print(f"Failure: {self.topology}")

        # print("Slice Name : {}".format(self.slice.slice_name))
        # print("ID         : {}".format(self.slice.slice_id))
        # print("State      : {}".format(self.slice.slice_state))
        # print("Lease End  : {}".format(self.slice.lease_end))

    def run_all(
        self,
        test_name="component_test",
        tests=[],
        create_slice=True,
        run_test=True,
        delete=True,
        node_count=1,
    ):
        self.test_name = test_name

        # Create slices
        if create_slice:
            for site, model_type, node_count in tests:
                print(
                    "Create slice:  site: {}, component: {}, node_count: {}. Nodes: ".format(
                        site, model_type, node_count
                    ),
                    end="",
                )
                # print("Creating Slice")
                for node_num in range(0, node_count):
                    try:
                        print(" {}".format(node_num), end="")

                        self.create_slice(
                            name_prefix=test_name + "-" + str(node_num),
                            model_type=ComponentTest.COMPONENT_MODELS[model_type],
                            site_name=site,
                            node_count=1,
                        )
                        # time.sleep(2)

                        # self.slice = self.wait_for_slice(self.slice, progress=True, timeout=300+(20*node_count))
                        # time.sleep(10)

                    except Exception as e:
                        print("Create Slice FAILED. Error {}".format(e))
                        traceback.print_exc()
                print(", Done")

            for slice in self.slices:
                try:
                    s = self.wait_for_slice(slice, progress=True, timeout=300)
                except Exception as e:
                    print("Slice failed wait_for_slice. {}".format(slice))
                    print(str(e))
                    # self.slices.remove(slice)

            time.sleep(120)
            # test ssh conectivity
            for slice in self.slices:
                try:
                    self.run_ssh_test(slice)
                except Exception as e:
                    # print("Failed to get topology: {}".format(slice))
                    # print(str(e))
                    print(
                        " Test: ssh | "
                        + str(slice.slice_name)
                        + " | slice closing | Fail "
                    )

        # Run tests
        if run_test:
            print("Run tests")
            for site, model_type, node_count in tests:
                # print("Run test:  site: {}, component: {}, node_count: {}".format(site,model_type,node_count))
                # print("Creating Slice")
                for node_num in range(0, node_count):
                    try:
                        # print("Running test  site: {}, component: {}, node_num: {}".format(site,model_type,node_num))
                        name_prefix = test_name + "-" + str(node_num)
                        component_model_name = str(model_type)  # .split(".",1)[1]
                        slice_name = (
                            name_prefix + "-" + component_model_name + "-" + str(site)
                        )
                        # print("Running test, slice_name: {}".format(slice_name))
                        from fabrictestbed_extensions.utils.slice import SliceUtils

                        slice = SliceUtils.get_slice(
                            slice_name=slice_name, slice_manager=self.slice_manager
                        )

                        if model_type == "GPU_Tesla_T4":
                            self.run_test_GPU_Tesla_T4(slice)
                        elif model_type == "GPU_RTX6000":
                            self.run_test_GPU_RTX6000(slice)
                        elif model_type == "SharedNIC_ConnectX_6":
                            self.run_test_SharedNIC_ConnectX_6(slice)
                        elif model_type == "SmartNIC_ConnectX_6":
                            self.run_test_SmartNIC_ConnectX_6(slice)
                        elif model_type == "SmartNIC_ConnectX_5":
                            self.run_test_SmartNIC_ConnectX_5(slice)
                        elif model_type == "NVME_P4510":
                            self.run_test_NVME_P4510(slice)
                        else:
                            print(
                                " Test: XXX | "
                                + str(slice_name)
                                + " | unknown test | Skipped"
                            )

                    except Exception as e:
                        print(
                            " Test: XXX | "
                            + str(slice_name)
                            + " | "
                            + str(e)
                            + " | Failed"
                        )

                        # print("Run test FAILED. Error {}".format(e))
                        # traceback.print_exc()

        # self.run(slice_name + "-" + site, create_slice=False, run_test=run_test, delete=delete, site=site, node_count=node_count)

    def run(
        self,
        test_name="component_test",
        create_slice=True,
        run_test=True,
        delete=True,
        site=None,
        node_count=1,
    ):
        """
        Run the test
        :return:
        """
        self.test_name = test_name
        print("Tesla_T4 test, slice_name: {}, site: {}".format(slice_name, site))
        if create_slice:
            # print("Creating Slice")
            try:
                self.create_slice(
                    model_type=ComponentModelType.GPU_Tesla_T4,
                    site_name=site,
                    node_count=node_count,
                )
                # time.sleep(5)

                self.slice = self.wait_for_slice(
                    self.slice, progress=True, timeout=300 + (20 * node_count)
                )
                # time.sleep(10)

            except Exception as e:
                print("Create Slice FAILED. Error {}".format(e))
                traceback.print_exc()
            time.sleep(5 * node_count)

        self.get_existing_slice(slice_name)
        # time.sleep(60)

        if run_test:
            try:
                # print("Run Test")
                self.run_test_tesla_t4()
            except Exception as e:
                print("Run test FAILED. Error {}".format(e))
                traceback.print_exc()
        if delete:
            try:
                # print("Delete Slice")
                self.delete_slice()
            except:
                print("Delete FAILED")
