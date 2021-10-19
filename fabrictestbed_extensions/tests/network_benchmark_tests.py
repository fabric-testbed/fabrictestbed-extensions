import os
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
import json
from fabrictestbed.slice_editor import ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType
import time
import paramiko
import re

import importlib.resources as pkg_resources
from typing import List

from .abc_test import AbcTest

from .. import images

class NetworkBencharks(AbcTest):

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()


    def latency_test(self, clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose):
        output = "Information about latency with ping: \n"
        stdin, stdout, stderr = clientn1.exec_command('ping -c 5 ' + ip_of_interface_on_n2 + ' | grep rtt')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('ping -c 5 ' + ip_of_interface_on_n1 + ' | grep rtt')
        output += "\n" + stdout.read().decode("utf-8")

        return {"Latency" : output}

    def mtu_test(self, clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose):
        output = "Information about mtu with ping: \n"
        ping_packets_count = 3
        ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = clientn1.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_n2)
            ping_string = stdout.read().decode("utf-8")
            ping_string = re.findall("[0-9] received", ping_string)
            ping_string = re.findall("[0-9]", ping_string[0])
            if(int(ping_string[0]) == ping_packets_count):
                output += "Packet size " + str(ping_packet_size + 8) + " is enabled."
                break
            else:
                if(verbose):
                    print("Packet " + str(ping_packet_size + 8) + " too large.")
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = clientn2.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_n1)
            ping_string = stdout.read().decode("utf-8")
            ping_string = re.findall("[0-9] received", ping_string)
            ping_string = re.findall("[0-9]", ping_string[0])
            if(int(ping_string[0]) == ping_packets_count):
                output += "\n" + "Packet size " + str(ping_packet_size + 8) + " is enabled."
                break
            else:
                if(verbose):
                    print("Packet " + str(ping_packet_size + 8) + " too large.")

        return {"MTU" : output}

    def bandwidth_test(self, clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose):
        output = "Information about bandwidth with iperf: \n"
        stdin, stdout, stderr = clientn1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        stdin, stdout, stderr = clientn2.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        stdin, stdout, stderr = clientn1.exec_command('iperf3 -s > /dev/null 2>&1 &')
        stdin, stdout, stderr = clientn2.exec_command('iperf3 -s > /dev/null 2>&1 &')
        stdin, stdout, stderr = clientn2.exec_command('iperf3 -c ' + ip_of_interface_on_n1 + ' -P 32 -w 512M -R')
        iperf_string = stdout.read().decode("utf-8")
        output += "n2 to n1:\n"
        iperf_strings = iperf_string.splitlines()
        if(len(iperf_strings) > 3):
            output += iperf_string.splitlines()[-4] + "\n"
            output += iperf_string.splitlines()[-3] + "\n"
        stdin, stdout, stderr = clientn1.exec_command('iperf3 -c ' + ip_of_interface_on_n2 + ' -P 32 -w 512M -R')
        iperf_string = stdout.read().decode("utf-8")
        # iperf_string2 = re.findall("^(.*)\n^(.*)\n^(.*)\n^(.*)$\z", iperf_string)
        output += "n1 to n2:\n"
        iperf_strings = iperf_string.splitlines()
        if(len(iperf_strings) > 3):
            output += iperf_string.splitlines()[-4] + "\n"
            output += iperf_string.splitlines()[-3]

        return {"Bandwidth" : output}

    def network_card_information(self, clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose):
        output = "n1\n\n"

        output += "lspci -xxxvvv\n\n"
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep V2')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep SN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep V3')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep VA')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn1.exec_command('sudo lspci -xxxvvv | grep V0')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nip a\n\n"
        stdin, stdout, stderr = clientn1.exec_command('ip a')
        output += stdout.read().decode("utf-8")

        output += "\n\n\n\nn2\n\n"

        output += "lspci -xxxvvv\n\n"
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep V2')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep SN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep V3')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep VA')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('sudo lspci -xxxvvv | grep V0')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nip a\n\n"
        stdin, stdout, stderr = clientn2.exec_command('ip a')
        output += stdout.read().decode("utf-8")

        return {"NetworkCardInformation" : output}

    def processor_information(self, clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose):
        output = "n1\n\n"

        output += 'sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"'
        stdin, stdout, stderr = clientn1.exec_command('sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"')
        output += stdout.read().decode("utf-8")

        output += '\n\n\ndmesg | grep -i dmi: | cut -d ":" -f 2-\n\n'
        stdin, stdout, stderr = clientn1.exec_command('dmesg | grep -i dmi: | cut -d ":" -f 2-')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nsudo dmidecode -s system-serial-number\n\n"
        stdin, stdout, stderr = clientn1.exec_command('sudo dmidecode -s system-serial-number')
        output += stdout.read().decode("utf-8")

        output += "\n\n\n\nn2\n\n"

        output += 'sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"'
        stdin, stdout, stderr = clientn2.exec_command('sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"')
        output += stdout.read().decode("utf-8")

        output += '\n\n\ndmesg | grep -i dmi: | cut -d ":" -f 2-\n\n'
        stdin, stdout, stderr = clientn2.exec_command('dmesg | grep -i dmi: | cut -d ":" -f 2-')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nsudo dmidecode -s system-serial-number\n\n"
        stdin, stdout, stderr = clientn2.exec_command('sudo dmidecode -s system-serial-number')
        output += stdout.read().decode("utf-8")

        return {"ProcessorInformation" : output}


    def test_ptp_across_two_sites(self, site1, site2, test_list, verbose = True):
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')
        slice_manager.initialize()

        t = ExperimentTopology()
        cap = Capacities()
        cap.set_fields(core=32, ram=128, disk=10)
        n1 = t.add_node(name='n1', site=site1)
        n1.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n2 = t.add_node(name='n2', site=site2)
        n2.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n1.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name='n1-nic1')
        n2.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name='n2-nic1')
        t.add_network_service(name='ptp1', nstype=ServiceType.L2PTP, interfaces=[n1.interface_list[0], n2.interface_list[0]])
        if_labels = n1.interface_list[0].get_property(pname="labels")
        if_labels.vlan = "200"
        n1.interface_list[0].set_properties(labels=if_labels)
        if_labels = n2.interface_list[0].get_property(pname="labels")
        if_labels.vlan = "200"
        n2.interface_list[0].set_properties(labels=if_labels)
        slice_graph = t.serialize()

        status, reservations = slice_manager.create(slice_name="test_harness_latency_mtu_bandwidth", slice_graph=slice_graph, ssh_key=self.node_ssh_key)
        if(status != Status.OK):
            print(status)
            print(reservations)
            raise Exception("Slice creation failed. One thing to do: try renaming it?")
        slice_id=reservations[0].slice_id



        time.sleep(10)
        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead])
        slice = list(filter(lambda x : x.slice_id == slice_id, slices))[0]

        slice = self.wait_for_slice(slice, progress=verbose, timeout=300)

        return_status, topology = slice_manager.get_slice_topology(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))

        n1 = topology.nodes['n1']
        n2 = topology.nodes['n2']

        n1_ip = n1.management_ip
        n2_ip = n2.management_ip
        if(verbose):
            print("n1 IP: " + n1_ip)
            print("n2 IP: " + n2_ip)


        #output = {"SliceInformation" : slice_information}

        clientn1 = self.open_ssh_client('ubuntu', n1)
        clientn2 = self.open_ssh_client('ubuntu', n2)

        def get_interface_before_last(stdout):
            interface = re.findall(r"[0-9]: [A-Za-z][A-Za-z][A-Za-z][0-9]", stdout.read().decode("utf-8"))
            interface = interface[-2:-1]
            interface = re.findall("[A-Za-z][A-Za-z][A-Za-z][0-9]", interface[0])
            return interface[0]

        stdin, stdout, stderr = clientn1.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')
        stdin, stdout, stderr = clientn2.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')

        ################################Setting up the IP addresses and activating the interfaces
        stdin, stdout, stderr = clientn1.exec_command('ip a')
        interface_n1 = get_interface_before_last(stdout)
        ip_of_interface_on_n1 = "192.168.10.51"
        stdin, stdout, stderr = clientn1.exec_command('sudo ip link add link ' + interface_n1 + ' name ens7.200 type vlan id 200')
        stdin, stdout, stderr = clientn1.exec_command('sudo ip link set dev ' + interface_n1 + ' up mtu 9000')
        stdin, stdout, stderr = clientn1.exec_command('sudo ip link set dev ens7.200 up mtu 9000')
        stdin, stdout, stderr = clientn1.exec_command('sudo ip addr add ' + ip_of_interface_on_n1 + '/24 dev ens7.200')
        stdin, stdout, stderr = clientn2.exec_command('ip a')
        interface_n2 = get_interface_before_last(stdout)
        ip_of_interface_on_n2 = "192.168.10.52"
        stdin, stdout, stderr = clientn2.exec_command('sudo ip link add link ' + interface_n2 + ' name ens7.200 type vlan id 200')
        stdin, stdout, stderr = clientn2.exec_command('sudo ip link set dev ' + interface_n2 + ' up mtu 9000')
        stdin, stdout, stderr = clientn2.exec_command('sudo ip link set dev ens7.200 up mtu 9000')
        stdin, stdout, stderr = clientn2.exec_command('sudo ip addr add ' + ip_of_interface_on_n2 + '/24 dev ens7.200')

        for test in test_list:
            output.update(test(clientn1, clientn2, ip_of_interface_on_n1, ip_of_interface_on_n2, verbose))

        slice_manager.delete(slice_object=slice_object)

        if(verbose):
            for k in output:
                print(k)
                print(output[k])
                print("---")

        return output


    def test_ptp_across_two_sites_all_tests(self, site1, site2):
        test_ptp_accross_two_sites(site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])

    def test_all_links_ptp(self):

        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']

        slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')

        # Initialize the slice manager
        slice_manager.initialize()

        _status,resources = slice_manager.resources()

        site_pairs_list = []
        for key in resources.links:
            site_pairs_list.append(resources.links[key].interface_list[0].name.split("_"))

        for pair in site_pairs_list:
            print("Testing link: " + pair[0] + "-" + pair[1])
            test_ptp_across_two_sites_all_tests(pair[0], pair[1])
            time.sleep(240)

    def test_bridge_one_site(self, site, verbose=True):
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')
        slice_manager.initialize()

        t = ExperimentTopology()
        cap = Capacities()
        cap.set_fields(core=4, ram=8, disk=10)
        n1 = t.add_node(name='n1', site=site)
        n1.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n2 = t.add_node(name='n2', site=site)
        n2.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n1.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name='n1-nic1')
        #n1.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name='n1-nic1')
        n2.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name='n2-nic1')
        #n2.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name='n2-nic1')

        t.add_network_service(name='bridge1', nstype=ServiceType.L2Bridge, interfaces=[n1.interface_list[0], n2.interface_list[0],n1.interface_list[1], n2.interface_list[1]])
        #t.add_network_service(name='bridge1', nstype=ServiceType.L2Bridge, interfaces=[n1.interface_list[0], n2.interface_list[0]])

        slice_graph = t.serialize()

        status, reservations = slice_manager.create(slice_name="test_harness_latency_mtu_bandwidth", slice_graph=slice_graph, ssh_key=self.node_ssh_key)
        if(status != Status.OK):
            print(status)
            print(reservations)
            raise Exception("Slice creation failed. One thing to do: try renaming it?")
        slice_id=reservations[0].slice_id

        print("slice id: {}".format(slice_id))

        time.sleep(10)
        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        slice = list(filter(lambda x : x.slice_id == slice_id, slices))[0]

        slice = self.wait_for_slice(slice, progress=verbose, timeout=600)


        time.sleep(120)
        return_status, topology = slice_manager.get_slice_topology(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))

        n1 = topology.nodes['n1']
        n2 = topology.nodes['n2']

        n1_ip = n1.management_ip
        n2_ip = n2.management_ip
        if(verbose):
            print("n1 IP: " + str(n1_ip))
            print("n2 IP: " + str(n2_ip))


        #output = {"SliceInformation" : slice_information}

        clientn1 = self.open_ssh_client_direct('ubuntu', n1)
        clientn2 = self.open_ssh_client_direct('ubuntu', n2)


        def get_interface_before_last(stdout):
            print("XXX")
            print(stdout)
            print("XXX")
            interfaces = json.loads(str(stdout))
            for iface in  interfaces:
                if iface['link_type'] != 'loopback' and iface['operstate'] != 'UP':
                    #print ('{}'.format(iface['ifname']))
                    break
            return iface['ifname']

        stdin, stdout, stderr = clientn1.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')
        stdin, stdout, stderr = clientn2.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')

        ################################Setting up the IP addresses and activating the interfaces
        stdin, stdout, stderr = clientn1.exec_command('ip -j a')
        interface_n1 = get_interface_before_last(str(stdout.read(),'utf-8').replace('\\n','\n'))
        print("interface_n1: {}".format(interface_n1))
        ip_of_interface_on_n1 = "192.168.10.51"
        stdin, stdout, stderr = clientn1.exec_command('sudo ip addr add ' + ip_of_interface_on_n1 + '/24 dev ' + interface_n1)
        stdin, stdout, stderr = clientn1.exec_command('sudo ip link set dev ' + interface_n1 + ' up mtu 9000')
        stdin, stdout, stderr = clientn2.exec_command('ip -j a')
        interface_n2 = get_interface_before_last(str(stdout.read(),'utf-8').replace('\\n','\n'))
        print("interface_n2: {}".format(interface_n2))
        ip_of_interface_on_n2 = "192.168.10.52"
        stdin, stdout, stderr = clientn2.exec_command('sudo ip addr add ' + ip_of_interface_on_n2 + '/24 dev ' + interface_n2)
        stdin, stdout, stderr = clientn2.exec_command('sudo ip link set dev ' + interface_n2 + ' up mtu 9000')

        ################################Latency
        stdin, stdout, stderr = clientn1.exec_command('ping -c 5 ' + ip_of_interface_on_n2 + ' | grep rtt')
        output1 = stdout.read().decode("utf-8")
        stdin, stdout, stderr = clientn2.exec_command('ping -c 5 ' + ip_of_interface_on_n1 + ' | grep rtt')
        output1 += "\n" + stdout.read().decode("utf-8")

        ################################MTU
        output2 = ""
        ping_packets_count = 3
        ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = clientn1.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_n2)
            ping_string = stdout.read().decode("utf-8")
        #     print(ping_string)
            ping_string = re.findall("[0-9] received", ping_string)
            ping_string = re.findall("[0-9]", ping_string[0])
            if(int(ping_string[0]) == ping_packets_count):
                out = "Packet size " + str(ping_packet_size + 8) + " is enabled."
                output2 += out
                break
            else:
                print("Packet " + str(ping_packet_size + 8) + " too large.")
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = clientn2.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_n1)
            ping_string = stdout.read().decode("utf-8")
        #     print(ping_string)
            ping_string = re.findall("[0-9] received", ping_string)
            ping_string = re.findall("[0-9]", ping_string[0])
            if(int(ping_string[0]) == ping_packets_count):
                out = "Packet size " + str(ping_packet_size + 8) + " is enabled."
                output2 += "\n" + out
                break
            else:
                print("Packet " + str(ping_packet_size + 8) + " too large.")

        ################################Bandwidth
        stdin, stdout, stderr = clientn1.exec_command('iperf -s > /dev/null 2>&1 &')
        output3 = ""
        stdin, stdout, stderr = clientn2.exec_command('iperf -c ' + ip_of_interface_on_n1 + ' -P 32 -w 32M')
        iperf_string = stdout.read().decode("utf-8")
        iperf_string2 = re.findall("........../sec", iperf_string)
        if(len(iperf_string2) > 0):
            output3 = iperf_string2[-1]
        else:
            output3 = iperf_string

        ################################Printing
        print("#####Information about latency with ping: \n" + output1)
        print("#####Information about mtu with ping: \n" + output2)
        print("#####Information about bandwidth with iperf: \n" + output3)

        slice_manager.delete(slice_object=slice_object)

    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
