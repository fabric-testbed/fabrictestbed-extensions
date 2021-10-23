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


    def latency_test(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=False, info=None):
        if verbose: print("Testing Latency: {}".format(info),end='')

        #rtt min/avg/max/mdev = 0.063/0.119/0.189/0.053 ms
        #output = "Information about latency with ping: \n"

        #warm up
        stdin, stdout, stderr = ssh_client_n1.exec_command('ping -c 10 ' + dataplane_ip_n2 + ' | grep rtt')

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

        return {'latency_test': output}

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


        return {'mtu_test': output}

    def bandwidth_test(self, ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=False, info=None):
        if verbose: print("Testing Bandwidth: {}".format(info),end='')

        output = {}
        stdin, stdout, stderr = ssh_client_n1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        stdin, stdout, stderr = ssh_client_n2.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')

        stdin, stdout, stderr = ssh_client_n1.exec_command('iperf3 -s > /dev/null 2>&1 &')
        stdin, stdout, stderr = ssh_client_n2.exec_command('iperf3 -s > /dev/null 2>&1 &')

        stdin, stdout, stderr = ssh_client_n2.exec_command('iperf3 -J -c ' + dataplane_ip_n1 + ' -P 32 -w 512M -R')
        #results = stdout.read().decode("utf-8")
        try:
            results = json.loads(str(stdout.read(),'utf-8'))
            #for key, value in results.items():
            #    print("key: {}, value: {}".format(key,value))
            #print('| {} '.format(str(results['end'])), end='')

            #bps = results['end']['sum_received']['bits_per_second']
            #gbps = float(bps)/1000000000
            #print('| {} '.format(str(gbps)), end='')
            output['forward'] = results
        except Exception as e:
            print("error {}".format(e))
            print("iperf raw results: {}".format(results))

        if verbose:
            bps = output['forward']['end']['sum_received']['bits_per_second']
            gbps = float(bps)/1000000000
            print(", forward: {:.3f} gbps".format(gbps),end='')



        stdin, stdout, stderr = ssh_client_n1.exec_command('iperf3 -J -c ' + dataplane_ip_n2 + ' -P 32 -w 512M -R')
        #results = stdout.read().decode("utf-8")
        try:
            results = json.loads(str(stdout.read(),'utf-8'))
            #for key, value in results.items():
            #    print("key: {}, value: {}".format(key,value))
            #print('| {} '.format(str(results['end'])), end='')

            #bps = results['end']['sum_received']['bits_per_second']
            #gbps = float(bps)/1000000000
            #print('| {} '.format(str(gbps)), end='')
            output['reverse'] = results
        except Exception as e:
            print("error {}".format(e))
            print("iperf raw results: {}".format(results))

        if verbose:
            bps = output['reverse']['end']['sum_received']['bits_per_second']
            gbps = float(bps)/1000000000
            print(", reverse: {:.3f} gbps".format(gbps))

        return {'bandwidth_test': output}



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



    def create_ptp_test_slice(self, test_name, site1, site2, verbose = True):


        slice_name = test_name

        #Create Topo
        t = ExperimentTopology()

        #Node1
        cap = Capacities()
        cap.set_fields(core=2, ram=8, disk=10)
        n1 = t.add_node(name='node1', site=site1)
        n1.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n1.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name='n1-nic1')

        #Node2
        cap = Capacities()
        cap.set_fields(core=2, ram=8, disk=10)
        n2 = t.add_node(name='node2', site=site2)
        n2.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
        n2.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name='n2-nic1')


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

        output = []
        for test in test_list:
            #print("{}".format(str(test)))
            #print("running test")
            output.append(test(ssh_client_n1, ssh_client_n2, dataplane_ip_n1, dataplane_ip_n2, verbose=verbose, info="{}-{}".format(node1.name,node2.name)))

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
                test['slice'] = self.create_ptp_test_slice(test['test_name'], test['src']['site'], test['dst']['site'], verbose = True)
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
            print("Run test: {}".format(str(test['test_name'])))
            results = self.run_tests(test_name, n1['node'], n2['node'], n1['dataplane_ip'], n2['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])
            all_results[test_name]=results

        print("{:<30} | {:>9} | {:>9} | {:>11} | {:>11} | {:>10} | {:>10}".format("Test","rtt","rtt_rev","mtu","mtu_rev","bw","bw_rev"))
        for test_name, results in all_results.items():
            print("{:<30}".format(test_name), end='')
            for result in results:
                if 'latency_test' in result.keys():
                    rtt=result['latency_test']['rtt']['avg']
                    rtt_rev=result['latency_test']['rtt_rev']['avg']
                    print(" | {:>6} ms".format(str(rtt)), end='')
                    print(" | {:>6} ms".format(str(rtt_rev)), end='')

                if 'mtu_test' in result.keys():
                    mtu=result['mtu_test']['mtu']
                    mtu_rev=result['mtu_test']['mtu_rev']
                    print(" | {:>5} bytes".format(str(mtu)), end='')
                    print(" | {:>5} bytes".format(str(mtu_rev)), end='')

                if 'bandwidth_test' in result.keys():
                    bps_reverse=result['bandwidth_test']['reverse']['end']['sum_received']['bits_per_second']
                    bps_forward=result['bandwidth_test']['forward']['end']['sum_received']['bits_per_second']
                    gbps_reverse = float(bps_reverse)/1000000000
                    gbps_forward = float(bps_forward)/1000000000
                    print(" | {:.3f} gbps".format(gbps_forward), end='')
                    print(" | {:.3f} gbps".format(gbps_reverse), end='')






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
        cap = Capacities()
        cap.set_fields(core=server['core'], ram=server['ram'], disk=server['disk'])
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
            cap = Capacities()
            cap.set_fields(core=client['core'], ram=client['ram'], disk=client['disk'])
            node = t.add_node(name=client['node_name'], site=site)

            print("Create node: {}, core: {}, ram: {}, disk: {}".format(client['node_name'],client['core'],client['ram'],client['disk']))
            node.set_properties(capacities=cap, image_type='qcow2', image_ref='default_ubuntu_20')
            if client['nic'] == 'SmartNIC_ConnectX_6':
                node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_6, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SmartNIC_ConnectX_5':
                node.add_component(model_type=ComponentModelType.SmartNIC_ConnectX_5, name=client['node_name']+'-nic1')
            elif client['nic'] == 'SharedNIC_ConnectX_6':
                node.add_component(model_type=ComponentModelType.SharedNIC_ConnectX_6, name=client['node_name']+'-nic1')

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
        cap = Capacities()
        cap.set_fields(core=server['core'], ram=server['ram'], disk=server['disk'])
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

            #Node2
            cap = Capacities()
            cap.set_fields(core=client['core'], ram=client['ram'], disk=client['disk'])
            node = t.add_node(name=client['node_name'], site=site)

            print("Create node: {}, core: {}, ram: {}, disk: {}".format(client['node_name'],client['core'],client['ram'],client['disk']))
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

        site = test['site']

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
            #self.run_tests(site1, site2, [self.latency_test])
            #self.run_tests(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
            print("Run test: {}".format(str(server_node)))
            print("Run test: {}".format(str(node['node'])))
            print("Run test: {}".format(str(server_dataplane_ip)))
            print("Run test: {}".format(str(node['dataplane_ip'])))
            #print("Run test: {} {} {} {}".format(str(server_node), str(node['node']), str(server_dataplane_ip), str(node['dataplane_ip'])))
            self.run_tests(test_name, server_node, node['node'], server_dataplane_ip, node['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])



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


        for node in nodes:
            #self.run_tests(site1, site2, [self.latency_test])
            #self.run_tests(test_name, site1, site2, [self.latency_test, self.mtu_test, self.bandwidth_test, self.network_card_information, self.processor_information])
            print("Run test: {}".format(str(server_node)))
            print("Run test: {}".format(str(node['node'])))
            print("Run test: {}".format(str(server_dataplane_ip)))
            print("Run test: {}".format(str(node['dataplane_ip'])))
            #print("Run test: {} {} {} {}".format(str(server_node), str(node['node']), str(server_dataplane_ip), str(node['dataplane_ip'])))
            self.run_tests(test_name, server_node, node['node'], server_dataplane_ip, node['dataplane_ip'], [self.latency_test, self.mtu_test, self.bandwidth_test])




        #
        #
        # #Configure server
        # ssh_client_server1 = None
        # while ssh_client_server1 == None:
        #     try:
        #         ssh_client_server1 = self.open_ssh_client('ubuntu', server1)
        #     except Exception as e:
        #         print("failed to get ssh client: {}".format(str(e)))
        #         time.sleep(20)
        #
        # ip_of_interface_on_server1 = "192.168.10.1"
        #
        #
        # try:
        #     stdin, stdout, stderr = ssh_client_server1.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')
        #     stdin, stdout, stderr = ssh_client_server1.exec_command('ip -j a')
        #     interface_server1 = self.get_dataplane_interface(str(stdout.read(),'utf-8').replace('\\n','\n'))
        #     print("interface_server1: {}".format(interface_server1))
        #
        #     stdin, stdout, stderr = ssh_client_server1.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        #     print("interface_server1: {}".format(interface_server1))
        #     stdin, stdout, stderr = ssh_client_server1.exec_command('sudo ip addr add ' + ip_of_interface_on_server1 + '/24 dev ' + interface_server1)
        #     stdin, stdout, stderr = ssh_client_server1.exec_command('sudo ip link set dev ' + interface_server1 + ' up mtu 9000')
        #
        #     if(verbose):
        #         print('Server: {}'.format(server1.name))
        #         print("   Cores             : {}".format(server1.get_property(pname='capacity_allocations').core))
        #         print("   RAM               : {}".format(server1.get_property(pname='capacity_allocations').ram))
        #         print("   Disk              : {}".format(server1.get_property(pname='capacity_allocations').disk))
        #         print("   Image             : {}".format(server1.image_ref))
        #         print("   Host              : {}".format(server1.get_property(pname='label_allocations').instance_parent))
        #         print("   Site              : {}".format(server1.site))
        #         print("   Management IP     : {}".format(server1.management_ip))
        #         print("   Components        :")
        #         for component_name, component in server1.components.items():
        #             print("      Name             : {}".format(component.name))
        #             print("      Model            : {}".format(component.model))
        #             print("      Type             : {}".format(component.type))
        # except Exception as e:
        #     print("Error configuring server: {}".format(str(e)))
        #
        # print('Client | host | management_ip | NIC | cores/ram/disk | lat | lat (rev) | mtu | mtu (rev) |  bw (gbps) | bw (gbps) (rev) ')
        # count=100
        # for client in clients:
        #     try:
        #         node_name = client['node_name']
        #         client_node = topology.nodes[node_name]
        #         client_node_ip = client_node.management_ip
        #
        #         print('{} '.format(client_node.name), end='')
        #         print('| {} '.format(client_node.get_property(pname='label_allocations').instance_parent), end='')
        #         print('| {} '.format(client_node.management_ip), end='')
        #         print('| {} '.format(client['nic']), end='')
        #         print('| {}'.format(client_node.get_property(pname='capacity_allocations').core), end='')
        #         print('/{}'.format(client_node.get_property(pname='capacity_allocations').ram), end='')
        #         print('/{} '.format(client_node.get_property(pname='capacity_allocations').disk), end='')
        #
        #
        #         ssh_client_node = self.open_ssh_client('ubuntu', client_node)
        #         ip_of_interface_on_node = "192.168.10."+str(count)
        #         count = count + 1
        #
        #         stdin, stdout, stderr = ssh_client_node.exec_command('sudo apt-get update && sudo apt-get install -y iperf iperf3')
        #
        #         stdin, stdout, stderr = ssh_client_node.exec_command('echo "net.core.rmem_max = 2147483647\nnet.core.wmem_max = 2147483647\nnet.ipv4.tcp_rmem = 4096 87380 2147483647\nnet.ipv4.tcp_wmem = 4096 65536 2147483647\nnet.ipv4.tcp_congestion_control=htcp\nnet.ipv4.tcp_mtu_probing=1\nnet.core.default_qdisc = fq\n" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p')
        #
        #
        #         ################################Setting up the IP addresses and activating the interfaces
        #         if create_slice:
        #             stdin, stdout, stderr = ssh_client_node.exec_command('ip -j a')
        #             interface_node = self.get_dataplane_interface(str(stdout.read(),'utf-8').replace('\\n','\n'))
        #             stdin, stdout, stderr = ssh_client_node.exec_command('sudo ip addr add ' + ip_of_interface_on_node + '/24 dev ' + interface_node)
        #             stdin, stdout, stderr = ssh_client_node.exec_command('sudo ip link set dev ' + interface_node + ' up mtu 9000')
        #
        #             #print("interface_node: {}".format(interface_node))
        #     except Exception as e:
        #         print("Error configuring client {}: {}".format(client_node.name,str(e)))
        #
        #
        #     try:
        #         ################################Latency
        #         stdin, stdout, stderr = ssh_client_server1.exec_command('ping -c 5 ' + ip_of_interface_on_node + ' | grep rtt')
        #         #output1 = stdout.read().decode("utf-8")
        #         print('| {} '.format(stdout.read().decode("utf-8").replace('\n','')), end='')
        #         stdin, stdout, stderr = ssh_client_node.exec_command('ping -c 5 ' + ip_of_interface_on_server1 + ' | grep rtt')
        #         #output1 += "\n" + stdout.read().decode("utf-8")
        #         print('| {} '.format(stdout.read().decode("utf-8").replace('\n','')), end='')
        #     except Exception as e:
        #         print("Error running latency tests client {}: {}".format(client_node.name,str(e)))
        #
        #
        #
        #     ################################MTU
        #     try:
        #         output2 = ""
        #         ping_packets_count = 3
        #         ping_packet_sizes = [9000, 8950, 8000, 1500, 1450, 1400, 1000, 500, 100, 50]
        #         for ping_packet_size in ping_packet_sizes:
        #             stdin, stdout, stderr = ssh_client_server1.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_node)
        #             ping_string = stdout.read().decode("utf-8")
        #         #     print(ping_string)
        #             ping_string = re.findall("[0-9] received", ping_string)
        #             ping_string = re.findall("[0-9]", ping_string[0])
        #             if(int(ping_string[0]) == ping_packets_count):
        #                 print('| {} '.format(str(ping_packet_size + 8)), end='')
        #                 #out = "Packet size " + str(ping_packet_size + 8) + " is enabled."
        #                 #output2 += out
        #                 break
        #             else:
        #                 pass
        #                 #print("Packet " + str(ping_packet_size + 8) + " too large.")
        #         for ping_packet_size in ping_packet_sizes:
        #             stdin, stdout, stderr = ssh_client_node.exec_command('ping -M do -s ' + str(ping_packet_size) + ' -c ' + str(ping_packets_count) + ' ' + ip_of_interface_on_server1)
        #             ping_string = stdout.read().decode("utf-8")
        #         #     print(ping_string)
        #             ping_string = re.findall("[0-9] received", ping_string)
        #             ping_string = re.findall("[0-9]", ping_string[0])
        #             if(int(ping_string[0]) == ping_packets_count):
        #                 print('| {} '.format(str(ping_packet_size + 8)), end='')
        #
        #                 #out = "Packet size " + str(ping_packet_size + 8) + " is enabled."
        #                 #output2 += "\n" + out
        #                 break
        #             else:
        #                 #print("Packet " + str(ping_packet_size + 8) + " too large.")
        #                 pass
        #     except Exception as e:
        #         print("Error running mtu tests client {}: {}".format(client_node.name,str(e)))
        #
        #
        #     try:
        #         ################################Bandwidth
        #         output3 = ""
        #         stdin, stdout, stderr = ssh_client_server1.exec_command('iperf3 -s > /dev/null 2>&1 &')
        #
        #         #stdin, stdout, stderr = ssh_client_node.exec_command('iperf3 -J -c ' + ip_of_interface_on_server1 + ' -P 32 -w 32M')
        #         stdin, stdout, stderr = ssh_client_node.exec_command('iperf3 -J -c ' + ip_of_interface_on_server1 + ' -P 16 ')
        #         #results = str(stdout.read())
        #         try:
        #             results = json.loads(str(stdout.read(),'utf-8'))
        #             #for key, value in results.items():
        #             #    print("key: {}, value: {}".format(key,value))
        #             #print('| {} '.format(str(results['end'])), end='')
        #
        #             bps = results['end']['sum_received']['bits_per_second']
        #             gbps = float(bps)/1000000000
        #             print('| {} '.format(str(gbps)), end='')
        #         except Exception as e:
        #             print("iperf raw results: {}".format(results))
        #             print("error {}".format(e))
        #     except Exception as e:
        #         print("Error running bandwidth tests client {}: {}".format(client_node.name,str(e)))
        #
        #
        #     #iperf_string = stdout.read().decode("utf-8")
        #     #iperf_string2 = re.findall("........../sec", iperf_string)
        #     #if(len(iperf_string2) > 0):
        #     #    output3 = iperf_string2[-1]
        #     #else:
        #     #    output3 = iperf_string
        #
        #     ################################Printing
        #     print(' | ... done')
        #     #print("#####Information about latency with ping: \n" + output1)
        #     #print("#####Information about mtu with ping: \n" + output2)
        #     #print("#####Information about bandwidth with iperf: \n" + output3)
        #
        # #slice_manager.delete(slice_object=slice_object)

    def run(self, create_slice=True, run_test=True, delete=True):
        """
        Run the test
        :return:
        """
