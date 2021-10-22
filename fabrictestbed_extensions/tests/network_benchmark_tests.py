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


    def latency_test(self, ssh_client_n1, ssh_client_n2, dataplan_ip_n1, dataplan_ip_n2, verbose):
        output = "Information about latency with ping: \n"
        stdin, stdout, stderr = ssh_client_n1.exec_command('ping -c 5 ' + dataplan_ip_n2 + ' | grep rtt')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('ping -c 5 ' + dataplan_ip_n1 + ' | grep rtt')
        output += "\n" + stdout.read().decode("utf-8")

        return {"Latency" : output}

    def mtu_test(self, ssh_client_n1, ssh_client_n2, dataplan_ip_n1, dataplan_ip_n2, verbose):
        output = "Information about mtu with ping: \n"
        ping_packets_count = 3
        ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
        for ping_packet_size in ping_packet_sizes:
            stdin, stdout, stderr = ssh_client_n1.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + dataplan_ip_n2)
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
            stdin, stdout, stderr = ssh_client_n2.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + dataplan_ip_n1)
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

    def bandwidth_test(self, ssh_client_n1, ssh_client_n2, dataplan_ip_n1, dataplan_ip_n2, verbose):
        output = "Information about bandwidth with iperf: \n"
        stdin, stdout, stderr = ssh_client_n1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        stdin, stdout, stderr = ssh_client_n2.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        stdin, stdout, stderr = ssh_client_n1.exec_command('iperf3 -s > /dev/null 2>&1 &')
        stdin, stdout, stderr = ssh_client_n2.exec_command('iperf3 -s > /dev/null 2>&1 &')
        stdin, stdout, stderr = ssh_client_n2.exec_command('iperf3 -c ' + dataplan_ip_n1 + ' -P 32 -w 512M -R')
        iperf_string = stdout.read().decode("utf-8")
        output += "n2 to n1:\n"
        iperf_strings = iperf_string.splitlines()
        if(len(iperf_strings) > 3):
            output += iperf_string.splitlines()[-4] + "\n"
            output += iperf_string.splitlines()[-3] + "\n"
        stdin, stdout, stderr = ssh_client_n1.exec_command('iperf3 -c ' + dataplan_ip_n2 + ' -P 32 -w 512M -R')
        iperf_string = stdout.read().decode("utf-8")
        # iperf_string2 = re.findall("^(.*)\n^(.*)\n^(.*)\n^(.*)$\z", iperf_string)
        output += "n1 to n2:\n"
        iperf_strings = iperf_string.splitlines()
        if(len(iperf_strings) > 3):
            output += iperf_string.splitlines()[-4] + "\n"
            output += iperf_string.splitlines()[-3]

        return {"Bandwidth" : output}

    def network_card_information(self, ssh_client_n1, ssh_client_n2, dataplan_ip_n1, dataplan_ip_n2, verbose):
        output = "n1\n\n"

        output += "lspci -xxxvvv\n\n"
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep V2')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep SN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep V3')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep VA')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo lspci -xxxvvv | grep V0')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nip a\n\n"
        stdin, stdout, stderr = ssh_client_n1.exec_command('ip a')
        output += stdout.read().decode("utf-8")

        output += "\n\n\n\nn2\n\n"

        output += "lspci -xxxvvv\n\n"
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep V2')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep SN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep PN')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep V3')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep VA')
        output += stdout.read().decode("utf-8")
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo lspci -xxxvvv | grep V0')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nip a\n\n"
        stdin, stdout, stderr = ssh_client_n2.exec_command('ip a')
        output += stdout.read().decode("utf-8")

        return {"NetworkCardInformation" : output}

    def processor_information(self, ssh_client_n1, ssh_client_n2, dataplan_ip_n1, dataplan_ip_n2, verbose):
        output = "n1\n\n"

        output += 'sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"'
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"')
        output += stdout.read().decode("utf-8")

        output += '\n\n\ndmesg | grep -i dmi: | cut -d ":" -f 2-\n\n'
        stdin, stdout, stderr = ssh_client_n1.exec_command('dmesg | grep -i dmi: | cut -d ":" -f 2-')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nsudo dmidecode -s system-serial-number\n\n"
        stdin, stdout, stderr = ssh_client_n1.exec_command('sudo dmidecode -s system-serial-number')
        output += stdout.read().decode("utf-8")

        output += "\n\n\n\nn2\n\n"

        output += 'sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"'
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo dmidecode | grep -w ID | sed "s/^.ID\: //g"')
        output += stdout.read().decode("utf-8")

        output += '\n\n\ndmesg | grep -i dmi: | cut -d ":" -f 2-\n\n'
        stdin, stdout, stderr = ssh_client_n2.exec_command('dmesg | grep -i dmi: | cut -d ":" -f 2-')
        output += stdout.read().decode("utf-8")

        output += "\n\n\nsudo dmidecode -s system-serial-number\n\n"
        stdin, stdout, stderr = ssh_client_n2.exec_command('sudo dmidecode -s system-serial-number')
        output += stdout.read().decode("utf-8")

        return {"ProcessorInformation" : output}



    def create_ptp_test_slice(self, test_name, site1, site2, verbose = True):


        slice_name = "{}_{}_{}".format(test_name,str(site1),str(site2))

        #Create Topo
        t = ExperimentTopology()

        #Node1
        cap = Capacities()
        cap.set_fields(core=4, ram=16, disk=10)
        n1 = t.add_node(name='node1', site=site1)
        n1.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n1.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name='n1-nic1')

        #Node2
        cap = Capacities()
        cap.set_fields(core=4, ram=16, disk=10)
        n2 = t.add_node(name='node2', site=site2)
        n2.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n2.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name='n2-nic1')


        # Network
        t.add_network_service(name='ptp1', nstype=ServiceType.L2PTP, interfaces=[n1.interface_list[0], n2.interface_list[0]])
        if_labels = n1.interface_list[0].get_property(pname="labels")
        if_labels.vlan = "200"
        n1.interface_list[0].set_properties(labels=if_labels)
        if_labels = n2.interface_list[0].get_property(pname="labels")
        if_labels.vlan = "200"
        n2.interface_list[0].set_properties(labels=if_labels)

        #Submit
        slice_graph = t.serialize()

        status, reservations = self.slice_manager .create(slice_name=slice_name, slice_graph=slice_graph, ssh_key=self.node_ssh_key)
        if(status != Status.OK):
            print(status)
            print(reservations)
            raise Exception("Slice creation failed.")
        slice_id=reservations[0].slice_id
        print("slice_id: {}".format(slice_id))


        time.sleep(10)
        return_status, slices = self.slice_manager .slices(excludes=[SliceState.Dead,SliceState.Closing])
        if(return_status != Status.OK):
            print(return_status)
            print(slices)
            raise Exception("Slice get failed.")
        slice = list(filter(lambda x : x.slice_name == slice_name, slices))[0]

        return slice

    def configure_test_node(self, node, dataplane_ip=None, verbose = True):

        node_ip = node.management_ip

        if(verbose):
            print('Server: {}'.format(node.name))
            print("   Cores             : {}".format(node.get_property(pname='capacity_allocations').core))
            print("   RAM               : {}".format(node.get_property(pname='capacity_allocations').ram))
            print("   Disk              : {}".format(node.get_property(pname='capacity_allocations').disk))
            print("   Image             : {}".format(node.image_ref))
            print("   Host              : {}".format(node.get_property(pname='label_allocations').instance_parent))
            print("   Site              : {}".format(node.site))
            print("   Management IP     : {}".format(node.management_ip))
            print("   Components        :")
            for component_name, component in node.components.items():
                print("      Name             : {}".format(component.name))
                print("      Model            : {}".format(component.model))
                print("      Type             : {}".format(component.type))

        #Configure
        ssh_client = self.open_ssh_client('ubuntu', node)

        #Configure node1
        stdin, stdout, stderr = ssh_client.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')
        stdin, stdout, stderr = ssh_client.exec_command('ip -j a')
        dataplane_iface = self.get_interface_before_last(str(stdout.read(),'utf-8').replace('\\n','\n'))

        #dataplan_ip_n1 = "192.168.10.51"
        stdin, stdout, stderr = ssh_client.exec_command('sudo ip link add link ' + dataplane_iface + ' name ens7.200 type vlan id 200')
        stdin, stdout, stderr = ssh_client.exec_command('sudo ip link set dev ' + dataplane_iface + ' up mtu 9000')
        stdin, stdout, stderr = ssh_client.exec_command('sudo ip link set dev ens7.200 up mtu 9000')
        stdin, stdout, stderr = ssh_client.exec_command('sudo ip addr add ' + dataplane_ip + '/24 dev ens7.200')

        self.close_ssh_client(ssh_client)



    def test_ptp_across_two_sites(self, test_name, node1, node2, dataplan_ip_n1, dataplan_ip_n2, test_list, verbose = True):

        #Configure
        ssh_client_n1 = self.open_ssh_client('ubuntu', node1)
        ssh_client_n2 = self.open_ssh_client('ubuntu', node2)

        output = []
        for test in test_list:
            #print("{}".format(str(test)))
            print("running test")
            output.append(test(ssh_client_n1, ssh_client_n2, dataplan_ip_n1, dataplan_ip_n2, verbose))

        #self.slice_manager .delete(slice_object=slice_object)

        self.close_ssh_client(ssh_client_n1)
        self.close_ssh_client(ssh_client_n2)

        if(verbose):
            for k in output:
                print(k)
                #print(output[k])
                print("---")

        return output


    def test_ptp_across_two_sites_all_tests(self, test_name, site1, site2, verbose=True):
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        self.slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')
        self.slice_manager .initialize()


        slice = self.create_ptp_test_slice(test_name, site1, site2, verbose = True)

        slice = self.wait_for_slice(slice, progress=verbose, timeout=600)

        time.sleep(120)
        return_status, topology = self.slice_manager .get_slice_topology(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))

        node_num = 100
        nodes = {}
        for node_name, node in topology.nodes.items():
            dataplane_ip = '192.168.1.'+str(node_num)
            node_num = node_num + 1
            nodes[node_name] = { 'dataplane_ip': dataplane_ip, 'node': node}

            self.configure_test_node(node, dataplane_ip)


        #self.test_ptp_across_two_sites(site1, site2, [self.latency_test])
        #self.test_ptp_across_two_sites(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
        n1 = nodes['node1']
        n2 = nodes['node2']
        self.test_ptp_across_two_sites(test_name, n1['node'], n2['node'], n1['dataplane_ip'], n2['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])


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

    def get_interface_before_last(self, stdout, ip=None):
        try:
            interfaces = json.loads(str(stdout))
            for iface in  interfaces:
                if iface['link_type'] != 'loopback' and iface['operstate'] != 'UP':
                    addr_info = iface['addr_info']
                    for addr in addr_info:
                        if iface['local'] == ip:
                            return iface['ifname']
                    #print ('{}'.format(iface['ifname']))
                    break

        except Exception as e:
            print("stdout: {}".format(stdout))
            raise e
        return iface['ifname']


    def test_bridge_one_site(self, test_name, site, clients=None, verbose=True, create_slice=True):
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')
        slice_manager.initialize()

        t = ExperimentTopology()
        cap = Capacities()
        cap.set_fields(core=16, ram=16, disk=10)
        server1 = t.add_node(name='server1', site=site)
        server1.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        server1.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name='server1-nic1')

        for client in clients:
            client_node = t.add_node(name=client['node_name'], site=site)
            cap = Capacities()
            cap.set_fields(core=int(client['core']), ram=int(client['ram']), disk=int(client['disk']))
            print("Create node: {}, core: {}, ram: {}, disk: {}".format(client['node_name'],client['core'],client['ram'],client['disk']))
            client_node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
            if client['nic'] == 'SmartNIC_ConnectX_6':
                client_node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SmartNIC_ConnectX_5':
                client_node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SharedNIC_ConnectX_6':
                client_node.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name=client['node_name']+'-nic1')


        t.add_network_service(name='bridge1', nstype=ServiceType.L2Bridge, interfaces=t.interface_list)

        slice_graph = t.serialize()

        if create_slice:
            status, reservations = slice_manager.create(slice_name=test_name, slice_graph=slice_graph, ssh_key=self.node_ssh_key)
            if(status != Status.OK):
                print(status)
                print(reservations)
                raise Exception("Slice creation failed. One thing to do: try renaming it?")
            slice_id=reservations[0].slice_id

        if create_slice:
            print("slice id: {}".format(slice_id))
            time.sleep(10)

        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        slice = list(filter(lambda x : x.slice_name == test_name, slices))[0]

        slice = self.wait_for_slice(slice, progress=verbose, timeout=600)

        if create_slice:
            time.sleep(120)
        return_status, topology = slice_manager.get_slice_topology(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))



        server1 = topology.nodes['server1']
        server1_ip = server1.management_ip
        if(verbose):
            print("server1 IP: " + str(server1_ip))




        #Configure server
        ssh_client_server1 = None
        while ssh_client_server1 == None:
            try:
                ssh_client_server1 = self.open_ssh_client('ubuntu', server1)
            except Exception as e:
                print("failed to get ssh client: {}".format(str(e)))
                time.sleep(20)

        ip_of_interface_on_server1 = "192.168.10.1"


        try:
            stdin, stdout, stderr = ssh_client_server1.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')
            stdin, stdout, stderr = ssh_client_server1.exec_command('ip -j a')
            interface_server1 = self.get_interface_before_last(str(stdout.read(),'utf-8').replace('\\n','\n'))
            print("interface_server1: {}".format(interface_server1))

            stdin, stdout, stderr = ssh_client_server1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
            print("interface_server1: {}".format(interface_server1))
            stdin, stdout, stderr = ssh_client_server1.exec_command('sudo ip addr add ' + ip_of_interface_on_server1 + '/24 dev ' + interface_server1)
            stdin, stdout, stderr = ssh_client_server1.exec_command('sudo ip link set dev ' + interface_server1 + ' up mtu 9000')

            if(verbose):
                print('Server: {}'.format(server1.name))
                print("   Cores             : {}".format(server1.get_property(pname='capacity_allocations').core))
                print("   RAM               : {}".format(server1.get_property(pname='capacity_allocations').ram))
                print("   Disk              : {}".format(server1.get_property(pname='capacity_allocations').disk))
                print("   Image             : {}".format(server1.image_ref))
                print("   Host              : {}".format(server1.get_property(pname='label_allocations').instance_parent))
                print("   Site              : {}".format(server1.site))
                print("   Management IP     : {}".format(server1.management_ip))
                print("   Components        :")
                for component_name, component in server1.components.items():
                    print("      Name             : {}".format(component.name))
                    print("      Model            : {}".format(component.model))
                    print("      Type             : {}".format(component.type))
        except Exception as e:
            print("Error configuring server: {}".format(str(e)))

        print('Client | host | management_ip | NIC | cores/ram/disk | lat | lat (rev) | mtu | mtu (rev) |  bw (gbps) | bw (gbps) (rev) ')
        count=100
        for client in clients:
            try:
                node_name = client['node_name']
                client_node = topology.nodes[node_name]
                client_node_ip = client_node.management_ip

                print('{} '.format(client_node.name), end='')
                print('| {} '.format(client_node.get_property(pname='label_allocations').instance_parent), end='')
                print('| {} '.format(client_node.management_ip), end='')
                print('| {} '.format(client['nic']), end='')
                print('| {}'.format(client_node.get_property(pname='capacity_allocations').core), end='')
                print('/{}'.format(client_node.get_property(pname='capacity_allocations').ram), end='')
                print('/{} '.format(client_node.get_property(pname='capacity_allocations').disk), end='')


                ssh_client_node = self.open_ssh_client('ubuntu', client_node)
                ip_of_interface_on_node = "192.168.10."+str(count)
                count = count + 1

                stdin, stdout, stderr = ssh_client_node.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')

                stdin, stdout, stderr = ssh_client_node.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')


                ################################Setting up the IP addresses and activating the interfaces
                if create_slice:
                    stdin, stdout, stderr = ssh_client_node.exec_command('ip -j a')
                    interface_node = self.get_interface_before_last(str(stdout.read(),'utf-8').replace('\\n','\n'))
                    stdin, stdout, stderr = ssh_client_node.exec_command('sudo ip addr add ' + ip_of_interface_on_node + '/24 dev ' + interface_node)
                    stdin, stdout, stderr = ssh_client_node.exec_command('sudo ip link set dev ' + interface_node + ' up mtu 9000')

                    #print("interface_node: {}".format(interface_node))
            except Exception as e:
                print("Error configuring client {}: {}".format(client_node.name,str(e)))


            try:
                ################################Latency
                stdin, stdout, stderr = ssh_client_server1.exec_command('ping -c 5 ' + ip_of_interface_on_node + ' | grep rtt')
                #output1 = stdout.read().decode("utf-8")
                print('| {} '.format(stdout.read().decode("utf-8").replace('\n','')), end='')
                stdin, stdout, stderr = ssh_client_node.exec_command('ping -c 5 ' + ip_of_interface_on_server1 + ' | grep rtt')
                #output1 += "\n" + stdout.read().decode("utf-8")
                print('| {} '.format(stdout.read().decode("utf-8").replace('\n','')), end='')
            except Exception as e:
                print("Error running latency tests client {}: {}".format(client_node.name,str(e)))



            ################################MTU
            try:
                output2 = ""
                ping_packets_count = 3
                ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
                for ping_packet_size in ping_packet_sizes:
                    stdin, stdout, stderr = ssh_client_server1.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_node)
                    ping_string = stdout.read().decode("utf-8")
                #     print(ping_string)
                    ping_string = re.findall("[0-9] received", ping_string)
                    ping_string = re.findall("[0-9]", ping_string[0])
                    if(int(ping_string[0]) == ping_packets_count):
                        print('| {} '.format(str(ping_packet_size + 8)), end='')
                        #out = "Packet size " + str(ping_packet_size + 8) + " is enabled."
                        #output2 += out
                        break
                    else:
                        pass
                        #print("Packet " + str(ping_packet_size + 8) + " too large.")
                for ping_packet_size in ping_packet_sizes:
                    stdin, stdout, stderr = ssh_client_node.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_server1)
                    ping_string = stdout.read().decode("utf-8")
                #     print(ping_string)
                    ping_string = re.findall("[0-9] received", ping_string)
                    ping_string = re.findall("[0-9]", ping_string[0])
                    if(int(ping_string[0]) == ping_packets_count):
                        print('| {} '.format(str(ping_packet_size + 8)), end='')

                        #out = "Packet size " + str(ping_packet_size + 8) + " is enabled."
                        #output2 += "\n" + out
                        break
                    else:
                        #print("Packet " + str(ping_packet_size + 8) + " too large.")
                        pass
            except Exception as e:
                print("Error running mtu tests client {}: {}".format(client_node.name,str(e)))


            try:
                ################################Bandwidth
                output3 = ""
                stdin, stdout, stderr = ssh_client_server1.exec_command('iperf3 -s > /dev/null 2>&1 &')

                #stdin, stdout, stderr = ssh_client_node.exec_command('iperf3 -J -c ' + ip_of_interface_on_server1 + ' -P 32 -w 32M')
                stdin, stdout, stderr = ssh_client_node.exec_command('iperf3 -J -c ' + ip_of_interface_on_server1 + ' -P 16 ')
                #results = str(stdout.read())
                try:
                    results = json.loads(str(stdout.read(),'utf-8'))
                    #for key, value in results.items():
                    #    print("key: {}, value: {}".format(key,value))
                    #print('| {} '.format(str(results['end'])), end='')

                    bps = results['end']['sum_received']['bits_per_second']
                    gbps = float(bps)/1000000000
                    print('| {} '.format(str(gbps)), end='')
                except Exception as e:
                    print("iperf raw results: {}".format(results))
                    print("error {}".format(e))
            except Exception as e:
                print("Error running bandwidth tests client {}: {}".format(client_node.name,str(e)))


            #iperf_string = stdout.read().decode("utf-8")
            #iperf_string2 = re.findall("........../sec", iperf_string)
            #if(len(iperf_string2) > 0):
            #    output3 = iperf_string2[-1]
            #else:
            #    output3 = iperf_string

            ################################Printing
            print(' | ... done')
            #print("#####Information about latency with ping: \n" + output1)
            #print("#####Information about mtu with ping: \n" + output2)
            #print("#####Information about bandwidth with iperf: \n" + output3)

        #slice_manager.delete(slice_object=slice_object)

    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
