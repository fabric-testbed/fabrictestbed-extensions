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

import importlib.resources as pkg_resources
import json
import os
import re
import time
import traceback
from typing import List

import paramiko
from fabrictestbed.slice_editor import (
    Capacities,
    ComponentCatalog,
    ComponentModelType,
    ComponentType,
    ExperimentTopology,
    ServiceType,
)
from fabrictestbed.slice_manager import SliceManager, SliceState, Status
from fabrictestbed.util.constants import Constants

from fabrictestbed_extensions import images
from tests.integration.abc_test import AbcTest


class LinkBenchmark(AbcTest):
    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

    @staticmethod
    def latency_test(
        clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose
    ):
        output = "Information about latency with ping: \n"
        stdin, stdout, stderr = clientn1.exec_command(
            "ping -c 5 " + ip_of_interface_on_n2 + " | grep rtt"
        )
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command(
            "ping -c 5 " + ip_of_interface_on_n1 + " | grep rtt"
        )
        output += "\n" + stdout.read().decode("utf-8")

        return {"Latency": output}

    @staticmethod
    def mtu_test(
        clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose
    ):
        output = "Information about mtu with ping: \n"
        ping_packets_count = 3
        ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = clientn1.exec_command(
                "ping -M do -s "
                + str(ping_packet_size)
                + " -c "
                + str(ping_packets_count)
                + " "
                + ip_of_interface_on_n2
            )
            ping_string = stdout.read().decode("utf-8")
            ping_string = re.findall("[0-9] received", ping_string)
            ping_string = re.findall("[0-9]", ping_string[0])
            if int(ping_string[0]) == ping_packets_count:
                output += "Packet size " + str(ping_packet_size + 8) + " is enabled."
                break
            else:
                if verbose:
                    print("Packet " + str(ping_packet_size + 8) + " too large.")
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = clientn2.exec_command(
                "ping -M do -s "
                + str(ping_packet_size)
                + " -c "
                + str(ping_packets_count)
                + " "
                + ip_of_interface_on_n1
            )
            ping_string = stdout.read().decode("utf-8")
            ping_string = re.findall("[0-9] received", ping_string)
            ping_string = re.findall("[0-9]", ping_string[0])
            if int(ping_string[0]) == ping_packets_count:
                output += (
                    "\n" + "Packet size " + str(ping_packet_size + 8) + " is enabled."
                )
                break
            else:
                if verbose:
                    print("Packet " + str(ping_packet_size + 8) + " too large.")

        return {"MTU": output}

    @staticmethod
    def bandwidth_test(
        clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose
    ):
        output = "Information about bandwidth with iperf: \n"
        stdin, stdout, stderr = clientn1.exec_command(
            'echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p'
        )
        stdin, stdout, stderr = clientn2.exec_command(
            'echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p'
        )
        stdin, stdout, stderr = clientn1.exec_command("iperf3 -s > /dev/null 2>&1 &")
        stdin, stdout, stderr = clientn2.exec_command("iperf3 -s > /dev/null 2>&1 &")
        stdin, stdout, stderr = clientn2.exec_command(
            "iperf3 -c " + ip_of_interface_on_n1 + " -P 32 -w 512M -R"
        )
        iperf_string = stdout.read().decode("utf-8")
        output += "n2 to n1:\n"
        iperf_strings = iperf_string.splitlines()
        if len(iperf_strings) > 3:
            output += iperf_string.splitlines()[-4] + "\n"
            output += iperf_string.splitlines()[-3] + "\n"
        stdin, stdout, stderr = clientn1.exec_command(
            "iperf3 -c " + ip_of_interface_on_n2 + " -P 32 -w 512M -R"
        )
        iperf_string = stdout.read().decode("utf-8")
        # iperf_string2 = re.findall("^(.*)\n^(.*)\n^(.*)\n^(.*)$\z", iperf_string)
        output += "n1 to n2:\n"
        iperf_strings = iperf_string.splitlines()
        if len(iperf_strings) > 3:
            output += iperf_string.splitlines()[-4] + "\n"
            output += iperf_string.splitlines()[-3]

        return {"Bandwidth": output}

    @staticmethod
    def network_card_information(
        clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose
    ):
        output = ""
        output += "lspci -xxxvvv\n\n"
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep PN")
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep V2")
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep SN")
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep PN")
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep V3")
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep VA")
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command("sudo lspci -xxxvvv | grep V0")
        output += stdout.read().decode("utf-8")

        output += "\n\n\nip a\n\n"
        stdin, stdout, stderr = clientn1.exec_command("ip a")
        output += stdout.read().decode("utf-8")

        return {"NetworkCardInformation": output}

    @staticmethod
    def processor_information(
        clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose
    ):
        output = ""

        output += 'sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"'
        stdin, stdout, stderr = clientn1.exec_command(
            'sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"'
        )
        output += stdout.read().decode("utf-8")

        output += '\n\n\ndmesg | grep -i dmi: | cut -d ":" -f 2-\n\n'
        stdin, stdout, stderr = clientn1.exec_command(
            'dmesg | grep -i dmi: | cut -d ":" -f 2-'
        )
        output += stdout.read().decode("utf-8")

        output += "\n\n\nsudo dmidecode -s system-serial-number\n\n"
        stdin, stdout, stderr = clientn1.exec_command(
            "sudo dmidecode -s system-serial-number"
        )
        output += stdout.read().decode("utf-8")

        return {"ProcessorInformation": output}

    @staticmethod
    def test_ptp_accross_two_sites(site1, site2, test_list, verbose=True):
        credmgr_host = os.environ[Constants.FABRIC_CREDMGR_HOST]
        orchestrator_host = os.environ[Constants.FABRIC_ORCHESTRATOR_HOST]
        project_id = os.environ[Constants.FABRIC_PROJECT_ID]
        slice_manager = SliceManager(
            oc_host=orchestrator_host,
            cm_host=credmgr_host,
            project_id=project_id,
            scope="all",
        )
        slice_manager.initialize()

        t = ExperimentTopology()
        cap = Capacities(core=32, ram=128, disk=10)
        n1 = t.add_node(name="n1", site=site1)
        n1.set_properties(
            capacities=cap, image_type="qcow2", image_ref="default_ubuntu_20"
        )
        n2 = t.add_node(name="n2", site=site2)
        n2.set_properties(
            capacities=cap, image_type="qcow2", image_ref="default_ubuntu_20"
        )
        n1.add_component(
            model_type=ComponentModelType.SmartNIC_ConnectX_6, name="n1-nic1"
        )
        n2.add_component(
            model_type=ComponentModelType.SmartNIC_ConnectX_6, name="n2-nic1"
        )
        if site1 == site2:
            t.add_network_service(
                name="net1",
                nstype=ServiceType.L2Bridge,
                interfaces=[n1.interface_list[0], n2.interface_list[0]],
            )
        else:
            t.add_network_service(
                name="net1",
                nstype=ServiceType.L2PTP,
                interfaces=[n1.interface_list[0], n2.interface_list[0]],
            )

        if_labels = n1.interface_list[0].get_property(pname="labels")
        if_labels.vlan = "200"
        n1.interface_list[0].set_properties(labels=if_labels)
        if_labels = n2.interface_list[0].get_property(pname="labels")
        if_labels.vlan = "200"
        n2.interface_list[0].set_properties(labels=if_labels)
        slice_graph = t.serialize()
        ssh_key = None
        with open("/Users/pruth/.ssh/id_rsa.pub", "r") as myfile:
            ssh_key = myfile.read()
            ssh_key = ssh_key.strip()
        status, reservations = slice_manager.create(
            slice_name="test_harness_latency_mtu_bandwidth",
            slice_graph=slice_graph,
            ssh_key=ssh_key,
        )
        if status != Status.OK:
            print(status)
            print(reservations)
            raise Exception("Slice creation failed. One thing to do: try renaming it?")
        slice_id = reservations[0].slice_id

        seconds_to_sleep = 15.0
        while True:
            return_status, slices = slice_manager.slices(excludes=[SliceState.Dead])
            if (
                list(filter(lambda x: x.slice_id == slice_id, slices))[0].slice_state
                == "StableOK"
            ):
                if verbose:
                    print("Slice is StableOK.")
                break
            elif (
                list(filter(lambda x: x.slice_id == slice_id, slices))[0].slice_state
                != "Configuring"
            ):
                print(
                    "Slice state: "
                    + list(filter(lambda x: x.slice_id == slice_id, slices))[
                        0
                    ].slice_state
                )
                #         print(slice_manager.slivers(slice_id=slice_id))
                slice_object = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
                status, slivers = slice_manager.slivers(slice_object=slice_object)
                for s in slivers:
                    status, sliver_status = slice_manager.sliver_status(sliver=s)
                    print("Response Status {}".format(status))
                    print("Sliver Status {}".format(sliver_status))
                raise Exception("Slice creation failed.")
            else:
                if verbose:
                    print(
                        "Slice is configuring. Trying again in "
                        + str(seconds_to_sleep)
                        + " seconds."
                    )
            time.sleep(seconds_to_sleep)

        slice_object = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
        status, slivers = slice_manager.slivers(slice_object=slice_object)
        n1_ip = list(filter(lambda sliver: sliver.name == "n1", slivers))[
            0
        ].management_ip
        n2_ip = list(filter(lambda sliver: sliver.name == "n2", slivers))[
            0
        ].management_ip
        if verbose:
            print("n1 IP: " + n1_ip)
            print("n2 IP: " + n2_ip)

        slice_information = "SliceID: " + slice_id + "\nSlivers:\n" + str(slivers)

        output = {"SliceInformation": slice_information}

        key = paramiko.RSAKey.from_private_key_file("/Users/pruth/.ssh/id_rsa")
        clientn1 = paramiko.SSHClient()
        clientn1.load_system_host_keys()
        clientn1.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        clientn1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connection_attempts = 0
        while True:
            try:
                clientn1.connect(n1_ip, username="ubuntu", pkey=key)
                break
            except Exception as exception:
                print(exception)
                connection_attempts += 1
                if connection_attempts < 10:
                    if verbose:
                        print(
                            "Connection failed. Will try to connect again in a few seconds."
                        )
                    time.sleep(5)
                else:
                    raise Exception("Connection to server failed.")
        clientn2 = paramiko.SSHClient()
        clientn2.load_system_host_keys()
        clientn2.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        clientn2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connection_attempts = 0
        while True:
            try:
                clientn2.connect(n2_ip, username="ubuntu", pkey=key)
                break
            except Exception as exception:
                print(exception)
                connection_attempts += 1
                if connection_attempts < 10:
                    if verbose:
                        print(
                            "Connection failed. Will try to connect again in a few seconds."
                        )
                    time.sleep(5)
                else:
                    raise Exception("Connection to server failed.")

        def get_interface_before_last(stdout):
            interface = re.findall(
                r"[0-9]: [A-Za-z][A-Za-z][A-Za-z][0-9]", stdout.read().decode("utf-8")
            )
            interface = interface[-2:-1]
            interface = re.findall("[A-Za-z][A-Za-z][A-Za-z][0-9]", interface[0])
            return interface[0]

        stdin, stdout, stderr = clientn1.exec_command(
            "sudo apt-get update && sudo apt-get install -y iperf iperf3"
        )
        stdin, stdout, stderr = clientn2.exec_command(
            "sudo apt-get update && sudo apt-get install -y iperf iperf3"
        )

        ################################Setting up the IP addresses and activating the interfaces
        stdin, stdout, stderr = clientn1.exec_command("ip a")
        interface_n1 = get_interface_before_last(stdout)
        ip_of_interface_on_n1 = "192.168.10.51"
        stdin, stdout, stderr = clientn1.exec_command(
            "sudo ip link add link " + interface_n1 + " name ens7.200 type vlan id 200"
        )
        stdin, stdout, stderr = clientn1.exec_command(
            "sudo ip link set dev " + interface_n1 + " up mtu 9000"
        )
        stdin, stdout, stderr = clientn1.exec_command(
            "sudo ip link set dev ens7.200 up mtu 9000"
        )
        stdin, stdout, stderr = clientn1.exec_command(
            "sudo ip addr add " + ip_of_interface_on_n1 + "/24 dev ens7.200"
        )
        stdin, stdout, stderr = clientn2.exec_command("ip a")
        interface_n2 = get_interface_before_last(stdout)
        ip_of_interface_on_n2 = "192.168.10.52"
        stdin, stdout, stderr = clientn2.exec_command(
            "sudo ip link add link " + interface_n2 + " name ens7.200 type vlan id 200"
        )
        stdin, stdout, stderr = clientn2.exec_command(
            "sudo ip link set dev " + interface_n2 + " up mtu 9000"
        )
        stdin, stdout, stderr = clientn2.exec_command(
            "sudo ip link set dev ens7.200 up mtu 9000"
        )
        stdin, stdout, stderr = clientn2.exec_command(
            "sudo ip addr add " + ip_of_interface_on_n2 + "/24 dev ens7.200"
        )

        for test in test_list:
            output.update(
                test(
                    clientn1,
                    clientn2,
                    ip_of_interface_on_n1,
                    ip_of_interface_on_n2,
                    verbose,
                )
            )

        # slice_manager.delete(slice_object=slice_object)

        if verbose:
            for k in output:
                print(k)
                print(output[k])
                print("---")

        return output

    def create_slice(self):
        slice_name = "NVMEBenchmark"
        site_name = "STAR"
        node_name = "Node1"
        image = "default_centos_8"
        image_type = "qcow2"
        cores = 4
        ram = 8
        disk = 50
        model_type = ComponentModelType.NVME_P4510
        # nvme_component_type = ComponentType.NVME
        # nvme_model = 'P4510'
        nvme_name = "nvme1"

        self.topology = ExperimentTopology()

        # Add node
        n1 = self.topology.add_node(name=node_name, site=site_name)

        # Set capacities
        cap = Capacities(core=cores, ram=ram, disk=disk)

        # Set Properties
        n1.set_properties(capacities=cap, image_type=image_type, image_ref=image)

        # Add the PCI NVMe device
        n1.add_component(model_type=model_type, name=nvme_name)
        # n1.add_component(ctype=nvme_component_type, model=nvme_model, name=nvme_name)

        # Generate Slice Graph
        slice_graph = self.topology.serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = self.slice_manager.create(
            slice_name=slice_name, slice_graph=slice_graph, ssh_key=self.ssh_key
        )

        if return_status == Status.OK:
            slice_id = slice_reservations[0].get_slice_id()
            print("Submitted slice creation request. Slice ID: {}".format(slice_id))
        else:
            print(f"Failure: {slice_reservations}")

        time.sleep(30)

        return_status, slices = self.slice_manager.slices(
            excludes=[SliceState.Dead, SliceState.Closing]
        )

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
        # print( list(ComponentModelType))
        # print(self.advertised_topology)
        # self.create_slice()

        d1 = LinkBenchmark.test_ptp_accross_two_sites(
            "TACC",
            "MAX",
            test_list=[
                LinkBenchmark.latency_test,
                LinkBenchmark.mtu_test,
                LinkBenchmark.bandwidth_test,
                LinkBenchmark.network_card_information,
                LinkBenchmark.processor_information,
            ],
        )
