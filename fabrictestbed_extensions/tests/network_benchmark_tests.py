import os
from fabrictestbed.slice_manager import SliceManager, Status, SliceState
import json
from fabrictestbed.slice_editor import ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, Labels
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


    def latency_test(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=False, info=None):
        if verbose: print("Testing Latency: {}".format(info),end='')

        #rtt min/avg/max/mdev = 0.063/0.119/0.189/0.053 ms
        #output = "Information about latency with ping: \n"

        #warm up
        stdin, stdout, stderr = ssh_client_n1.exec_command('ping -c 3 ' + dataplane_ip_n2 + ' | grep rtt')

        #Run test
        output = {}

        stdin, stdout, stderr = ssh_client_n1.exec_command('ping -c 10 ' + dataplane_ip_n2 + ' | grep rtt')
        raw_output = stdout.read().decode("utf-8")
        raw_data = raw_output.split(" ")[3]
        data_array = raw_data.split("/")
        output['rtt'] = {   'min': data_array[0],
                                'avg': data_array[1],
                                'max': data_array[2],
                                'mdev': data_array[3],
                            }
        if verbose: print(", avg rtt: {}".format(output['rtt']['avg']),end='')

        stdin, stdout, stderr = ssh_client_n2.exec_command('ping -c 10 ' + dataplane_ip_n1 + ' | grep rtt')
        #output += "\n" + stdout.read().decode("utf-8")
        raw_output = stdout.read().decode("utf-8")
        raw_data = raw_output.split(" ")[3]
        data_array = raw_data.split("/")
        output['rtt_rev'] = {   'min': data_array[0],
                                'avg': data_array[1],
                                'max': data_array[2],
                                'mdev': data_array[3],
                            }
        if verbose: print(", avg rtt_rev: {}".format(output['rtt_rev']['avg']))

        #return {'latency_test': output}
        return output

    def mtu_test(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=False, info=None):
        if verbose: print("Testing MTU: {}".format(info),end='')

        #Run test
        output = {}

        ping_packets_count = 3
        #ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
        max_success = -1
        min_fail = 10000

        #Test min ping
        current_size = 0

        stdin, stdout, stderr = ssh_client_n1.exec_command('ping -M do -s ' + str(current_size) + ' -c ' + str(ping_packets_count) + ' ' + dataplane_ip_n2 + " | grep transmitted")
        ping_string = stdout.read().decode("utf-8")

        data_array = ping_string.split(" ")
        recieved_packets = 0
        if len(data_array) > 3:
            recieved_packets = data_array[3]

        if(int(recieved_packets) == ping_packets_count):
            max_success = current_size
            min_fail = 10000
        else:
            min_fail = 0
            max_success = -1


        while max_success < min_fail - 1:

            current_size = int((min_fail+max_success)/2)
            #print("min_fail: {}, max_success: {}, current_size: {}".format(str(min_fail),str(max_success), str(current_size)))

            stdin, stdout, stderr = ssh_client_n1.exec_command('ping -M do -s ' + str(current_size) + ' -c ' + str(ping_packets_count) + ' ' + dataplane_ip_n2 + " | grep transmitted")
            ping_string = stdout.read().decode("utf-8")

            #print("current_size: {}, output: {}".format(str(current_size),ping_string))

            data_array = ping_string.split(" ")
            recieved_packets = 0
            if len(data_array) > 3:
                recieved_packets = data_array[3]

            #print("recieved_packets: {}, ping_packets_count: {}".format(str(recieved_packets),str(ping_packets_count)))
            if(int(recieved_packets) == int(ping_packets_count)):
                max_success = current_size
            else:
                min_fail = current_size

        if max_success > 0:
            output['mtu'] = str(max_success+28)
        else:
            output['mtu'] = 0

        if verbose: print(", mtu: {}".format(output['mtu']),end='')


        #Test reverse
        max_success = -1
        min_fail = 10000

        #Test min ping
        current_size = 0

        stdin, stdout, stderr = ssh_client_n2.exec_command('ping -M do -s ' + str(current_size) + ' -c ' + str(ping_packets_count) + ' ' + dataplane_ip_n1 + " | grep transmitted")
        ping_string = stdout.read().decode("utf-8")

        data_array = ping_string.split(" ")
        recieved_packets = 0
        if len(data_array) > 3:
            recieved_packets = data_array[3]

        if(int(recieved_packets) == ping_packets_count):
            max_success = current_size
            min_fail = 10000
        else:
            min_fail = 0
            max_success = -1


        while max_success < min_fail - 1:

            current_size = int((min_fail+max_success)/2)
            #print("min_fail: {}, max_success: {}, current_size: {}".format(str(min_fail),str(max_success), str(current_size)))

            stdin, stdout, stderr = ssh_client_n2.exec_command('ping -M do -s ' + str(current_size) + ' -c ' + str(ping_packets_count) + ' ' + dataplane_ip_n1 + " | grep transmitted")
            ping_string = stdout.read().decode("utf-8")

            #print("current_size: {}, output: {}".format(str(current_size),ping_string))

            data_array = ping_string.split(" ")
            recieved_packets = 0
            if len(data_array) > 3:
                recieved_packets = data_array[3]

            #print("recieved_packets: {}, ping_packets_count: {}".format(str(recieved_packets),str(ping_packets_count)))
            if(int(recieved_packets) == int(ping_packets_count)):
                max_success = current_size
            else:
                min_fail = current_size

        if max_success > 0:
            output['mtu_rev'] = str(max_success+28)
        else:
            output['mtu_rev'] = 0

        if verbose: print(", mtu_rev: {}  ".format(output['mtu_rev']))


        #return {'mtu_test': output}
        return output


    def bandwidth_test(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=False, info=None):
        if verbose: print("Testing Bandwidth: {}".format(info),end='')

        output = {}
        #stdin, stdout, stderr = ssh_client_n1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        #stdin, stdout, stderr = ssh_client_n2.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')

        stdin, stdout, stderr = ssh_client_n1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        stdin, stdout, stderr = ssh_client_n2.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')


        stdin, stdout, stderr = ssh_client_n1.exec_command('iperf3 -s > /dev/null 2>&1 &')
        stdin, stdout, stderr = ssh_client_n2.exec_command('iperf3 -s > /dev/null 2>&1 &')

        stdin, stdout, stderr = ssh_client_n2.exec_command('iperf3 -J -c ' + dataplane_ip_n1 + '-t 60 -P 1 -w 512M')
        try:
            results = json.loads(str(stdout.read(),'utf-8'))
            output['forward'] = results
        except Exception as e:
            print("error {}".format(e))
            print("iperf raw results: {}".format(results))

        if verbose:
            bps = output['forward']['end']['sum_received']['bits_per_second']
            gbps = float(bps)/1000000000
            print(", forward: {:.3f} gbps".format(gbps),end='')



        stdin, stdout, stderr = ssh_client_n1.exec_command('iperf3 -J -c ' + dataplane_ip_n2 + '-t 60 -P 1 -w 512M')
        try:
            results = json.loads(str(stdout.read(),'utf-8'))
            output['reverse'] = results
        except Exception as e:
            print("error {}".format(e))
            print("iperf raw results: {}".format(results))

        if verbose:
            bps = output['reverse']['end']['sum_received']['bits_per_second']
            gbps = float(bps)/1000000000
            print(", reverse: {:.3f} gbps".format(gbps))

        #return {'bandwidth_test': output}
        return output



    def network_card_information(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose):
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

    def processor_information(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose):
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



    def create_ptp_test_slice(self, test=None, verbose = True):

        slice_name = test['test_name']
        site1 = test['src']['site']
        site2 = test['dst']['site']


        #Create Topo
        t = ExperimentTopology()

        #Node1
        cap = Capacities(core=test['src']['core'], ram=test['src']['ram'], disk=test['src']['disk'])
        n1 = t.add_node(name='node1', site=site1)
        n1.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        if test['src']['nic'] == 'SmartNIC_ConnectX_6':
            n1.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name='n1-nic1')
        elif test['src']['nic'] == 'SmartNIC_ConnectX_5':
            n1.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name='n1-nic1')
        elif test['src']['nic'] == 'SharedNIC_ConnectX_6':
            n1.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name='n1-nic1')


        #Node2
        cap = Capacities(core=test['dst']['core'], ram=test['dst']['ram'], disk=test['dst']['disk'])
        n2 = t.add_node(name='node2', site=site2)
        n2.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        if test['dst']['nic'] == 'SmartNIC_ConnectX_6':
            n2.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name='n2-nic1')
        elif test['dst']['nic'] == 'SmartNIC_ConnectX_5':
            n2.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name='n2-nic1')
        elif test['dst']['nic'] == 'SharedNIC_ConnectX_6':
            n2.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name='n2-nic1')


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

    def configure_test_node(self, node, dataplane_ip=None, vlan=None, verbose = True):

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
        dataplane_iface = self.get_dataplane_interface(str(stdout.read(),'utf-8').replace('\\n','\n'))
        print("dataplane_iface: {}".format(dataplane_iface))

        if vlan:
            #dataplane_ip_n1 = "192.168.10.51"
            stdin, stdout, stderr = ssh_client.exec_command('sudo ip link add link ' + dataplane_iface + ' name ens7.200 type vlan id 200')
            stdin, stdout, stderr = ssh_client.exec_command('sudo ip link set dev ' + dataplane_iface + ' up mtu 9000')
            stdin, stdout, stderr = ssh_client.exec_command('sudo ip link set dev ens7.200 up mtu 9000')
            stdin, stdout, stderr = ssh_client.exec_command('sudo ip addr add ' + dataplane_ip + '/24 dev ens7.200')
        else:
            stdin, stdout, stderr = ssh_client.exec_command('sudo ip link set dev ens7 up mtu 9000')
            stdin, stdout, stderr = ssh_client.exec_command('sudo ip addr add ' + dataplane_ip + '/24 dev ens7')

        self.close_ssh_client(ssh_client)



    def run_tests(self, test_name, node1, node2, dataplane_ip_n1, dataplane_ip_n2, test_list, verbose = True):

        #Configure
        ssh_client_n1 = self.open_ssh_client('ubuntu', node1)
        ssh_client_n2 = self.open_ssh_client('ubuntu', node2)

        output = {}
        for test in test_list:
            #print("{}".format(str(test)))
            #print("running test")
            try:
                output[test.__name__] = test(ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=verbose, info="{}-{}".format(node1.name,node2.name))
            except Exception as e:
                print("Exception running test: {}".format(str(e)))


        #self.slice_manager .delete(slice_object=slice_object)

        self.close_ssh_client(ssh_client_n1)
        self.close_ssh_client(ssh_client_n2)

        #if(verbose):
            #for k in output:
                #print(k)
                #print(output[k])

        return output


    def run_tests_all_tests(self, test_name, site1, site2, verbose=True):
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

            self.configure_test_node(node, dataplane_ip,vlan=200)


        #self.run_tests(site1, site2, [self.latency_test])
        #self.run_tests(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
        n1 = nodes['node1']
        n2 = nodes['node2']
        self.run_tests(test_name, n1['node'], n2['node'], n1['dataplane_ip'], n2['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])


    def test_all_ptp(self, tests, verbose=True, create_slices=True):

        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']

        slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')

        # Initialize the slice manager
        slice_manager.initialize()

        #_status,resources = slice_manager.resources()

        #Get link pairs
        #site_pairs_list = []
        #for key in resources.links:
        #    site_pairs_list.append(resources.links[key].interface_list[0].name.split("_"))

        #tests = []
        #for test_pair in site_pairs:
        #    tests.append({ 'src': test_pair[0], 'dst': test_pair[1]})

        #Create Slices
        for test in tests:
            if create_slices:
                test['slice'] = self.create_ptp_test_slice(test=test, verbose = True)
            else:
                test['slice'] = self.get_slice(slice_name=test['test_name'],slice_manager=self.slice_manager)

        #wait for slices
        for test in tests:
            test['slice'] = self.wait_for_slice(test['slice'], progress=verbose, timeout=600)

        if create_slices:
            time.sleep(120)

        #Run tests
        all_results = {}
        for test in tests:
            #print("Process test: {}".format(str(test)))
            slice = test['slice']
            test_name = test['test_name']
            return_status, topology = self.slice_manager .get_slice_topology(slice_object=slice)
            if return_status != Status.OK:
                raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))

            node_num = 100
            nodes = {}
            for node_name, node in topology.nodes.items():
                dataplane_ip = '192.168.1.'+str(node_num)
                node_num = node_num + 1
                nodes[node_name] = { 'dataplane_ip': dataplane_ip, 'node': node}
                print("Config node: {}".format(str(node_name)))
                self.configure_test_node(node, dataplane_ip, vlan=200)


            #self.run_tests(site1, site2, [self.latency_test])
            #self.run_tests(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
            n1 = nodes['node1']
            n2 = nodes['node2']
            #print("Run test: {}".format(str(test['test_name'])))
            results = self.run_tests(test_name, n1['node'], n2['node'], n1['dataplane_ip'], n2['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])
            all_results[test_name]=results

        return all_results


    def print_summary(self, all_results):

        print("{:<60} | {:>9} | {:>9} | {:>11} | {:>11} | {:>10} | {:>10}".format(" ","rtt","rtt_rev","mtu","mtu_rev","bw","bw_rev"))
        print("------------------------------------------------------------------------------------------------------------------------------------------")
        for test_name, results in all_results.items():
            print("{:<60}".format(test_name), end='')

            rtt=''
            rtt_rev=''
            if 'latency_test' in results.keys():
                rtt=results['latency_test']['rtt']['avg']
                rtt_rev=results['latency_test']['rtt_rev']['avg']
            print(" | {:>6} ms".format(str(rtt)), end='')
            print(" | {:>6} ms".format(str(rtt_rev)), end='')

            mtu = ''
            mtu_rev = ''
            if 'mtu_test' in results.keys():
                mtu=results['mtu_test']['mtu']
                mtu_rev=results['mtu_test']['mtu_rev']
            print(" | {:>5} bytes".format(str(mtu)), end='')
            print(" | {:>5} bytes".format(str(mtu_rev)), end='')

            gbps_forward = 0.0
            gbps_reverse = 0.0
            if 'bandwidth_test' in results.keys():
                bps_reverse=results['bandwidth_test']['reverse']['end']['sum_received']['bits_per_second']
                bps_forward=results['bandwidth_test']['forward']['end']['sum_received']['bits_per_second']
                gbps_reverse = float(bps_reverse)/1000000000
                gbps_forward = float(bps_forward)/1000000000
            print(" | {:.3f} gbps".format(gbps_forward), end='')
            print(" | {:.3f} gbps".format(gbps_reverse), end='')
            print('')






    def get_dataplane_interface(self, stdout, ip=None):
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

    def create_s2s_test_slice(self, test_name, test=None, verbose = True):
        slice_name = test_name
        site = test['server']['site']

        #Create Topo
        t = ExperimentTopology()

        interface_list = []

        #server
        server = test['server']
        cap = Capacities(core=server['core'], ram=server['ram'], disk=server['disk'])
        node = t.add_node(name=server['node_name'], site=site)

        print("Create node: {}, core: {}, ram: {}, disk: {}".format(server['node_name'],server['core'],server['ram'],server['disk']))
        node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        if server['nic'] == 'SmartNIC_ConnectX_6':
            node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name=server['node_name']+'-nic1')
        elif server['nic'] == 'SmartNIC_ConnectX_5':
            node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name=server['node_name']+'-nic1')
        elif server['nic'] == 'SharedNIC_ConnectX_6':
            node.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name=server['node_name']+'-nic1')

        interface_list.append(node.interface_list[0])


        for client in test['clients']:
            site = client['site']
            #Node2
            cap = Capacities(core=client['core'], ram=client['ram'], disk=client['disk'])
            node = t.add_node(name=client['node_name'], site=site)

            print("Create node: {}, core: {}, ram: {}, disk: {}".format(client['node_name'],client['core'],client['ram'],client['disk']))
            node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
            if client['nic'] == 'SmartNIC_ConnectX_6':
                node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SmartNIC_ConnectX_5':
                node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SharedNIC_ConnectX_6':
                node.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name=client['node_name']+'-nic1')
            else:
                print("Error setting nic type: node: {}, nic: {}".format(client['node_name'],client['nic']))

            interface_list.append(node.interface_list[0])

        # Network
        t.add_network_service(name='l2br1', nstype=ServiceType.L2STS, interfaces=interface_list)

        #Submit
        slice_graph = t.serialize()

        status, reservations = self.slice_manager.create(slice_name=slice_name, slice_graph=slice_graph, ssh_key=self.node_ssh_key)
        if(status != Status.OK):
            print(status)
            print(reservations)
            raise Exception("Slice creation failed.")
        slice_id=reservations[0].slice_id
        print("slice_id: {}".format(slice_id))


        time.sleep(10)
        return_status, slices = self.slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        if(return_status != Status.OK):
            print(return_status)
            print(slices)
            raise Exception("Slice get failed.")
        slice = list(filter(lambda x : x.slice_name == slice_name, slices))[0]

        return slice

    def create_l2bridge_test_slice(self, test_name, test=None, verbose = True):
        slice_name = test_name
        site = test['site']

        #Create Topo
        t = ExperimentTopology()

        interface_list = []

        #server
        server = test['server']
        cap = Capacities(core=server['core'], ram=server['ram'], disk=server['disk'])
        node = t.add_node(name=server['node_name'], site=site)

        #temp for testign
        #labels = Labels()
        #labels.instance_parent = 'star-w5.fabric-testbed.net'


        print("Create node: {}, core: {}, ram: {}, disk: {}".format(server['node_name'],server['core'],server['ram'],server['disk']))
        #node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20',labels=labels)
        node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        if server['nic'] == 'SmartNIC_ConnectX_6':
            node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name=server['node_name']+'-nic1')
        elif server['nic'] == 'SmartNIC_ConnectX_5':
            node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name=server['node_name']+'-nic1')
        elif server['nic'] == 'SharedNIC_ConnectX_6':
            node.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name=server['node_name']+'-nic1')

        interface_list.append(node.interface_list[0])


        for client in test['clients']:

            #Node2
            cap = Capacities(core=client['core'], ram=client['ram'], disk=client['disk'])
            node = t.add_node(name=client['node_name'], site=site)

            #labels = Labels()
            #labels.instance_parent = 'star-w4.fabric-testbed.net'


            print("Create node: {}, core: {}, ram: {}, disk: {}".format(client['node_name'],client['core'],client['ram'],client['disk']))
            #node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20',labels=labels)
            node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
            if client['nic'] == 'SmartNIC_ConnectX_6':
                node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SmartNIC_ConnectX_5':
                node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SharedNIC_ConnectX_6':
                node.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name=client['node_name']+'-nic1')

            interface_list.append(node.interface_list[0])

        # Network
        t.add_network_service(name='l2br1', nstype=ServiceType.L2Bridge, interfaces=interface_list)

        #Submit
        slice_graph = t.serialize()

        status, reservations = self.slice_manager.create(slice_name=slice_name, slice_graph=slice_graph, ssh_key=self.node_ssh_key)
        if(status != Status.OK):
            print(status)
            print(reservations)
            raise Exception("Slice creation failed.")
        slice_id=reservations[0].slice_id
        print("slice_id: {}".format(slice_id))


        time.sleep(10)
        return_status, slices = self.slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        if(return_status != Status.OK):
            print(return_status)
            print(slices)
            raise Exception("Slice get failed.")
        slice = list(filter(lambda x : x.slice_name == slice_name, slices))[0]

        return slice

    def test_s2s(self, test_name, test=None, verbose=True, create_slice=True):
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        self.slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')
        self.slice_manager.initialize()


        if create_slice:
            slice = self.create_s2s_test_slice(test_name, test=test, verbose=verbose)
        else:
            slice = self.get_slice(slice_name=test_name,slice_manager=self.slice_manager)

        slice = self.wait_for_slice(slice, progress=verbose, timeout=600)

        if create_slice:
            time.sleep(120)

        return_status, topology = self.slice_manager.get_slice_topology(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))

        #print("topology: {}".format(str(topology)))


        server_node = topology.nodes[test['server']['node_name']]
        server_name = server_node.name
        server_dataplane_ip='192.168.1.1'
        print("Config server: {}".format(str(server_name)))
        self.configure_test_node(server_node, server_dataplane_ip)


        all_results = {}

        node_num = 100
        nodes = []
        for node_name, node in topology.nodes.items():
            if node_name == server_name:
                continue

            dataplane_ip = '192.168.1.'+str(node_num)
            node_num = node_num + 1
            nodes.append({ 'dataplane_ip': dataplane_ip, 'node': node})
            print("Config node: {}".format(str(node_name)))
            self.configure_test_node(node, dataplane_ip)


        for node in nodes:

            result_name = "{}_{}_{}".format(test_name, server_name, node['node'].name)
            #self.run_tests(site1, site2, [self.latency_test])
            #self.run_tests(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
            #print("Run test: {}".format(str(server_node)))
            #print("Run test: {}".format(str(node['node'])))
            #print("Run test: {}".format(str(server_dataplane_ip)))
            #print("Run test: {}".format(str(node['dataplane_ip'])))
            #print("Run test: {} {} {} {}".format(str(server_node), str(node['node']), str(server_dataplane_ip), str(node['dataplane_ip'])))
            all_results[result_name] = self.run_tests(test_name, server_node, node['node'], server_dataplane_ip, node['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])


        return all_results


    def test_l2bridge(self, test_name, test=None, verbose=True, create_slice=True):
        credmgr_host = os.environ['FABRIC_CREDMGR_HOST']
        orchestrator_host = os.environ['FABRIC_ORCHESTRATOR_HOST']
        self.slice_manager = SliceManager(oc_host=orchestrator_host, cm_host=credmgr_host, project_name='all', scope='all')
        self.slice_manager.initialize()

        site = test['site']

        if create_slice:
            slice = self.create_l2bridge_test_slice(test_name, test=test, verbose=verbose)
        else:
            slice = self.get_slice(slice_name=test_name,slice_manager=self.slice_manager)

        slice = self.wait_for_slice(slice, progress=verbose, timeout=600)

        if create_slice:
            time.sleep(120)

        return_status, topology = self.slice_manager.get_slice_topology(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("run_ssh_test failed to get topology. slice; {}, error {}".format(str(slice),str(topology)))

        #print("topology: {}".format(str(topology)))


        server_node = topology.nodes[test['server']['node_name']]
        server_name = server_node.name
        server_dataplane_ip='192.168.1.1'
        print("Config server: {}".format(str(server_name)))
        self.configure_test_node(server_node, server_dataplane_ip)

        node_num = 100
        nodes = []
        for node_name, node in topology.nodes.items():
            if node_name == server_name:
                continue

            dataplane_ip = '192.168.1.'+str(node_num)
            node_num = node_num + 1
            nodes.append({ 'dataplane_ip': dataplane_ip, 'node': node})
            print("Config node: {}".format(str(node_name)))
            self.configure_test_node(node, dataplane_ip)

        all_results = {}
        for node in nodes:
            result_name = "{}_{}_{}".format(test_name, server_name, node['node'].name)
            #self.run_tests(site1, site2, [self.latency_test])
            #self.run_tests(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
            #print("Run test: {}".format(str(server_node)))
            #print("Run test: {}".format(str(node['node'])))
            #print("Run test: {}".format(str(server_dataplane_ip)))
            #print("Run test: {}".format(str(node['dataplane_ip'])))
            #print("Run test: {} {} {} {}".format(str(server_node), str(node['node']), str(server_dataplane_ip), str(node['dataplane_ip'])))
            all_results[result_name] = self.run_tests(test_name, server_node, node['node'], server_dataplane_ip, node['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])
            #all_results[result_name] = self.run_tests(test_name, server_node, node['node'], server_dataplane_ip, node['dataplane_ip'], [self.latency_test])

        return all_results

    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
