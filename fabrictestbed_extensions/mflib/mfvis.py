import json
import traceback
import os
import sys
import time
import requests
import configparser
import urllib.parse
from ipywidgets import VBox, HTML, Output, interactive
import ipywidgets as widgets
from IPython.display import display
from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager
#from fabrictestbed_extensions.mflib.mflib import mflib
# For testing
from mflib import mflib

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class mfvis():
    sanity_version = "2.01"
    meas_net_info = {}
    prometheus_url = None
    
    def __init__(self, mf_obj=None, slice_name=None):
        """
        Constructor. Builds Manager for mfvis object.
        """
        super().__init__()
        #self._grafana_tunnel_host = ""
        # for current testing should be removed in future
        self._grafana_tunnel_host = "localhost:10010"
        
        if mf_obj:
            self._mf = mf_obj
        elif slice_name:
            self._mf = mflib()
            self._mf.init(slice_name)
        
        self.dashboard_info = {'dashboards':[]}
        self.slice_node_info={}
        self.get_node_and_interface_names()
        
        self.dashboard_info["time_filters"] = []
        self.dashboard_info["time_filters"].append({'name': 'Last 5 minutes', 'value': "5m", "refresh":"30s"})
        self.dashboard_info["time_filters"].append({'name': 'Last 15 minutes', 'value': 900000})
        self.dashboard_info["time_filters"].append({'name': 'Last 1 hour', 'value': 3600000})
        


        node_dashboard = { 'uid': 'rYdddlPWk', 'name': 'node-exporter-full', 'vars':[{'name':'job', 'default':'node'} , {'name':'DS_PROMETHEUS', 'default':'default'}, {'name':'diskdevices', 'default':'%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B'}, {'name':'node'}] }
        self.add_dashboard(node_dashboard)
        node_panels = [{'name': 'CPU Busy', 'id': 20}, {'name': 'Sys Load (5m avg)', 'id': 155}, {'name': 'Sys Load (15m avg)', 'id': 19}, {'name': 'RAM Used', 'id': 16}, {'name': 'SWAP Used', 'id': 21}, {'name': 'Root FS Used', 'id': 154}, {'name': 'CPU Cores', 'id': 14}, {'name': 'Uptime', 'id': 15}, {'name': 'RootFS Total', 'id': 23}, {'name': 'RAM Total', 'id': 75}, {'name': 'SWAP Total', 'id': 18}, {'name': 'CPU Basic', 'id': 77}, {'name': 'Memory Basic', 'id': 78}, {'name': 'Network Traffic Basic', 'id': 74}, {'name': 'Disk Space Used Basic', 'id': 152}, {'name': 'CPU', 'id': 3}, {'name': 'Memory Stack', 'id': 24}, {'name': 'Network Traffic', 'id': 84}, {'name': 'Disk Space Used', 'id': 156}, {'name': 'Disk IOps', 'id': 229}, {'name': 'I/O Usage Read / Write', 'id': 42}, {'name': 'I/O Utilization', 'id': 127}, {'name': 'Memory Active / Inactive', 'id': 136}, {'name': 'Memory Commited', 'id': 135}, {'name': 'Memory Active / Inactive Detail', 'id': 191}, {'name': 'Memory Writeback and Dirty', 'id': 130}, {'name': 'Memory Shared and Mapped', 'id': 138}, {'name': 'Memory Slab', 'id': 131}, {'name': 'Memory Vmalloc', 'id': 70}, {'name': 'Memory Bounce', 'id': 159}, {'name': 'Memory Anonymous', 'id': 129}, {'name': 'Memory Kernel / CPU', 'id': 160}, {'name': 'Memory HugePages Counter', 'id': 140}, {'name': 'Memory HugePages Size', 'id': 71}, {'name': 'Memory DirectMap', 'id': 128}, {'name': 'Memory Unevictable and MLocked', 'id': 137}, {'name': 'Memory NFS', 'id': 132}, {'name': 'Memory Pages In / Out', 'id': 176}, {'name': 'Memory Pages Swap In / Out', 'id': 22}, {'name': 'Memory Page Faults', 'id': 175}, {'name': 'OOM Killer', 'id': 307}, {'name': 'Time Syncronized Drift', 'id': 260}, {'name': 'Time PLL Adjust', 'id': 291}, {'name': 'Time Syncronized Status', 'id': 168}, {'name': 'Time Misc', 'id': 294}, {'name': 'Processes Status', 'id': 62}, {'name': 'Processes State', 'id': 315}, {'name': 'Processes  Forks', 'id': 148}, {'name': 'Processes Memory', 'id': 149}, {'name': 'PIDs Number and Limit', 'id': 313}, {'name': 'Process schedule stats Running / Waiting', 'id': 305}, {'name': 'Threads Number and Limit', 'id': 314}, {'name': 'Context Switches / Interrupts', 'id': 8}, {'name': 'System Load', 'id': 7}, {'name': 'Interrupts Detail', 'id': 259}, {'name': 'Schedule timeslices executed by each cpu', 'id': 306}, {'name': 'Entropy', 'id': 151}, {'name': 'CPU time spent in user and system contexts', 'id': 308}, {'name': 'File Descriptors', 'id': 64}, {'name': 'Hardware temperature monitor', 'id': 158}, {'name': 'Throttle cooling device', 'id': 300}, {'name': 'Power supply', 'id': 302}, {'name': 'Systemd Sockets', 'id': 297}, {'name': 'Systemd Units State', 'id': 298}, {'name': 'Disk IOps Completed', 'id': 9}, {'name': 'Disk R/W Data', 'id': 33}, {'name': 'Disk Average Wait Time', 'id': 37}, {'name': 'Average Queue Size', 'id': 35}, {'name': 'Disk R/W Merged', 'id': 133}, {'name': 'Time Spent Doing I/Os', 'id': 36}, {'name': 'Instantaneous Queue Size', 'id': 34}, {'name': 'Disk IOps Discards completed / merged', 'id': 301}, {'name': 'Filesystem space available', 'id': 43}, {'name': 'File Nodes Free', 'id': 41}, {'name': 'File Descriptor', 'id': 28}, {'name': 'File Nodes Size', 'id': 219}, {'name': 'Filesystem in ReadOnly / Error', 'id': 44}, {'name': 'Network Traffic by Packets', 'id': 60}, {'name': 'Network Traffic Errors', 'id': 142}, {'name': 'Network Traffic Drop', 'id': 143}, {'name': 'Network Traffic Compressed', 'id': 141}, {'name': 'Network Traffic Multicast', 'id': 146}, {'name': 'Network Traffic Fifo', 'id': 144}, {'name': 'Network Traffic Frame', 'id': 145}, {'name': 'Network Traffic Carrier', 'id': 231}, {'name': 'Network Traffic Colls', 'id': 232}, {'name': 'NF Contrack', 'id': 61}, {'name': 'ARP Entries', 'id': 230}, {'name': 'MTU', 'id': 288}, {'name': 'Speed', 'id': 280}, {'name': 'Queue Length', 'id': 289}, {'name': 'Softnet Packets', 'id': 290}, {'name': 'Softnet Out of Quota', 'id': 310}, {'name': 'Network Operational Status', 'id': 309}, {'name': 'Sockstat TCP', 'id': 63}, {'name': 'Sockstat UDP', 'id': 124}, {'name': 'Sockstat FRAG / RAW', 'id': 125}, {'name': 'Sockstat Memory Size', 'id': 220}, {'name': 'Sockstat Used', 'id': 126}, {'name': 'Netstat IP In / Out Octets', 'id': 221}, {'name': 'Netstat IP Forwarding', 'id': 81}, {'name': 'ICMP In / Out', 'id': 115}, {'name': 'ICMP Errors', 'id': 50}, {'name': 'UDP In / Out', 'id': 55}, {'name': 'UDP Errors', 'id': 109}, {'name': 'TCP In / Out', 'id': 299}, {'name': 'TCP Errors', 'id': 104}, {'name': 'TCP Connections', 'id': 85}, {'name': 'TCP SynCookie', 'id': 91}, {'name': 'TCP Direct Transition', 'id': 82}, {'name': 'Node Exporter Scrape Time', 'id': 40}, {'name': 'Node Exporter Scrape', 'id': 157}]
        self.add_panel('node-exporter-full', node_panels)

        network_traffic_dashboard = { 'uid': 'dHEquNzGz', 'name': 'network-traffic-dashboard', 'vars':[{'name':'job', 'default':'node'} , {'name':'DS_PROMETHEUS', 'default':'default'}, {'name':'device'}, {'name':'node'}] }
        self.add_dashboard(network_traffic_dashboard)
        traffic_panels = [{'name': 'Network Traffic by Packets', 'id': 8}, {'name': 'TCP In / Out', 'id': 13}, {'name': 'TCP Errors', 'id': 14}, {'name': 'UDP In / Out', 'id': 16}, {'name': 'UDP Errors', 'id': 17}, {'name': 'Network Traffic Received Errors', 'id': 10}, {'name': 'Network Traffic Send Errors', 'id': 11}]
        self.add_panel("network-traffic-dashboard", traffic_panels)
        ping_dashboard = {"name":"ping-status", "uid":"hqj_G5R4k", "vars":[],"panels":[{"name":"Ping", "id":2 }]}
        self.add_dashboard(ping_dashboard)

        self.dashboard_widget = None
        self.graph_widget = None
        self.time_widget = None
        self.node_widget = None
        self.device_widget = None
        
        
        
    @property
    def grafana_tunnel_host(self):
        """
        If a tunnel is used, this value must be set for the localhost:port"""
        return self._grafana_tunnel_host
        
    @grafana_tunnel_host.setter
    def grafana_tunnel_host(self, value):
        """ 
        Set to localhost:port_number if using tunnnel.
        """
        self._grafana_tunnel_host = value
        
    @property
    def grafana_base_url(self):
        """
        Gets the base url for grafana. If _grafana_tunnel_host is set then that value is used for the ip.
        Otherwise the meas_node_ip is used.
        """
        if self._grafana_tunnel_host:
            return f"https://{self._grafana_tunnel_host}/grafana"
        
        return f"https://{self.mf.meas_node_ip}/grafana"

    def grafana_dashboard_url(self, dashboard_name):
        """
        The url to go to the dashboard page.
        """
        ret_val = ""
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                ret_val = f'{self.grafana_base_url}/d/{d["uid"]}/{d["name"]}?orgId=1' 
        return ret_val
    
    def grafana_solo_dashboard_url(self, dashboard_name):
        """
        The base url to get just a panel.
        """
        ret_val = ""
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                ret_val = f'{self.grafana_base_url}/d-solo/{d["uid"]}/{d["name"]}?orgId=1' 
        return ret_val
    
    def grafana_panel_url(self, dashboard_name, panel_name):
        ret_val = self.grafana_solo_dashboard_url(dashboard_name)
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                #print(d["panels"])
                for p in d["panels"]:
                    if p["name"] == panel_name:
                        ret_val = f'{ret_val}&panelId={p["id"]}'
                        
                # add vars

                if "vars" in d:
                    for v in d["vars"]:
                        if "default" in v:
                            ret_val += f'&var-{v["name"]}={v["default"]}'
        return ret_val
        
    
    def add_dashboard(self, dashboard):
        """
        Adds given dashboard dictionary to the dashboard_info.
        """
        # add the dasboard info to list
        self.dashboard_info["dashboards"].append(dashboard)
        #TODO add check to prevent 2 with same name duplicates

    def add_panel(self, dashboard_name, panel):
        """
        Adds the given panel object or list of panel objects to the dashboard's panel list.
        No duplicate checks are done. TODO add duplicate checks.
        """
        
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                if "panels" not in d:
                    d["panels"] = []
                if isinstance(panel, list):
                    d["panels"].extend(panel)
                else:
                    d["panels"].append(panel)
        #TODO add check to avoid overwrite or duplicates
        
    def get_panel_names(self, dashboard_name):
        """
        Returns list of panel names for the given dashboard.
        """
        panels = []
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                
                for p in d["panels"]:
                    panels.append(p["name"])
        return panels
    
    def get_interface_names(self, node_name):
        """
        Returns list of interface names for the given node
        """
        interfaces = []
        if (node_name in self.slice_node_info.keys()):
            return self.slice_node_info[node_name]
            

    def get_dashboard_names(self):
        names = []
        for d in self.dashboard_info["dashboards"]:
            names.append( d["name"])
        return names
    


    @property
    def mf(self):
        """
        Gets the mflib object.
        """
        return self._mf

    @mf.setter
    def mf(self, value):
        """
        Sets the mflib object.
        """
        self._mf = value 
        
        
    def get_node_and_interface_names(self):
        """
        Uses fablib to get all the interface names of all the experiment nodes 
        """
        fablib = fablib_manager()
        #fablib.show_config()
        mfo = self._mf
        slice_name= mfo._slicename 
        try:
            slice = fablib.get_slice(name=slice_name)
            for node in slice.get_nodes():
                if node.get_name() != "_meas_node":
                    self.slice_node_info[node.get_name()]=[]
                    os_interface = []
                    interface_matching = {}
                    for interface in node.get_interfaces():
                        os_interface.append(interface.get_os_interface())
                        interface_matching[interface.get_os_interface()]=interface.get_name()
                    self.slice_node_info[node.get_name()].append(os_interface)
                    self.slice_node_info[node.get_name()].append(interface_matching)
            # for key, value in self.slice_node_info.items():
            #     print (f"{key}:{value[1]}")
            #print (self.slice_node_info")
            #return (self.slice_node_info)
        except Exception as e:
            print(f"Fail: {e}")
             

#
#     def init(self,slicename):
#         """
#         Sets up the mfvis object to visualize prometheus graphs in grafana 
#         :param slicename: The name of the slice.
#         """
#         print(f"Initing slice {slicename} for visualization")
#         self.meas_net_info = self.get_meas_net_info(slicename=slicename)
#         self.dashboard_info = self.set_dashboard_info()
#         self.prometheus_url = self.get_prometheus_url()


#     def read_prometheus_ini_file(self, slicename):
#         """
#         Check the existence of prometheus hosts ini file 
#         Reads the node name and IP address from the file
#         """
#         local_storage_directory = "/tmp/mflib/"
#         local_slice_directory = os.path.join(local_storage_directory, slicename)
#         promhosts_file = os.path.join(local_slice_directory, "hosts.ini")
#         exp_node_lines=[]
#         exp_node_info = []
#         if not os.path.exists(promhosts_file):
#             try:
#                 mf=mflib()
#                 mf.init(slicename)
#                 print (f"File {promhosts_file} does not exist. Proceed to downlaod the file.")
#                 filename, filecontents = mf.download_common_hosts()
#             except Exception as e:
#                 print(f"Download fails: {e}")
#                 return []
#                 traceback.print_exc()
#         if os.path.exists(promhosts_file):
#             try:
#                 print (f"Found host file at {promhosts_file}")
#                 with open(promhosts_file) as pif:
#                     lines = pif.readlines()
#                     for line in lines:
#                         if "[Experiment_Nodes]" in line:
#                             index=lines.index(line)
#                             exp_nodes=lines[index+1:]
#             except Exception as e:
#                     print(f"Fail to read promhosts.ini")
#                     print(f"Fail: {e}")
#                     return []
#             for node in exp_nodes:
#                 node=node.strip()
#                 info={}
#                 node_name=node.split()[0]
#                 node_ip=node.split("=")[-1]
#                 info['node_name']=node_name
#                 info['node_ip']=node_ip
#                 exp_node_info.append(info)
#             return (exp_node_info)            
#         else:
#             return []


#     def get_meas_net_info(self, slicename):
#         """
#         Gets the info of the meas_net including the _meas_node IP, experiment node names and connected interface IPs 
#         :param slicename: The name of the slice.
#         :rtype: Dict
#         """
#         try:
#             slice = fablib.get_slice(name=slicename)
#             meas_node = slice.get_node(name="_meas_node")
#             meas_net_info = {}
#             meas_net_info['meas_node_ip'] = str(meas_node.get_management_ip())
#             meas_net_info['node_info']=self.read_prometheus_ini_file(slicename=slicename)
#             return (meas_net_info)
#         except Exception as e:
#             print(f"Fail: {e}")
#             traceback.print_exc()


#     def set_dashboard_info(self):
#         """
#         Sets the grafana prometheus dashboard info
#         and the graphs (panel_id) available to be displayed
#         Works for grafana dashboard 1860
#         :rtype: Dict
#         """
#         dashboard_info = {}
#         first_graph = {'name': 'prometheus network traffic', 'panel_id':'74'}
#         second_graph = {'name': 'prometheus cpu', 'panel_id':'77'}
#         first_time_filter = {'name': 'Last 15 minutes', 'value': 900000}
#         second_time_filter = {'name': 'Last 1 hour', 'value': 3600000}
#         dashboard_info['dashboard_info']= {'dashboard_uid': 'rYdddlPWk', 'dashboard_name': 'node-exporter-full'}
#         dashboard_info['graph_panels'] = [first_graph, second_graph]
#         dashboard_info['time_filters'] = [first_time_filter, second_time_filter]
#         return (dashboard_info)


    def get_available_time_filter_names(self):
        """
        Returns the names of the available time filters in the dropdown menu
        :rtype: List
        """
        available_time = []
        for timefilter in self.dashboard_info['time_filters']:
            available_time.append(timefilter['name'])
        return available_time
    
    
    def get_available_time_filter_info(self, filter_name):
        """
        Returns the details of the available time filters by name
        :rtype: Time Filter object
        """
        for timefilter in self.dashboard_info['time_filters']:
            if timefilter['name'] == filter_name:
                return timefilter
        return None
    
    
    
    def get_available_node_names(self):
        """
        Returns the available node names in dropdown menus excluding the meas_node 
        :rtype: List
        """
        
        return (list(self.slice_node_info.keys()))
        #return ['Node1', 'Node2']
        #node_names = list(self.slice_node_info.keys())
        #print (node_names)
        #return node_names
        #available_nodes = []
        #for node in self.meas_net_info['node_info']:
            #available_nodes.append(node['node_name'])
        #return available_nodes


#     def get_available_graph_name(self):
#         """
#         Returns the available graph names to be displayed in the dropdown menu
#         :rtype: List
#         """
#         available_graphs = []
#         for graph in self.dashboard_info['graph_panels']:
#             available_graphs.append(graph['name'])
#         return available_graphs


#     def get_prometheus_url(self):
#         """
#         Builds the basic url of the prometheus graphs in grafana
#         currently the url uses localhost:10010 for visualization and 
#         will be changed to the management IP of the meas_node in the future
#         :rtype: String
#         """
#         ###To be changed
#         #meas_node_ip = self.meas_net_info['meas_node_ip']
#         ###
#         meas_node_ip = "localhost:10010"
#         dashboard_uid = self.dashboard_info['dashboard_info']['dashboard_uid']
#         dashboard_name = self.dashboard_info['dashboard_info']['dashboard_name']
#         #url_sec1 = "https://"+meas_node_ip+"/grafana/d-solo/"
#         #url_sec2 = "?orgId=1&refresh=1m&var-DS_PROMETHEUS=Prometheus&var-job=node&"
#         #url = url_sec1+dashboard_uid+"/"+dashboard_name+url_sec2
#         url_first_sec = "https://{ip}/grafana/d-solo/{duid}/{dname}".format(ip=meas_node_ip, duid=dashboard_uid, dname=dashboard_name)
#         url_second_sec = "?orgId=1&refresh=1m&var-DS_PROMETHEUS=Prometheus&var-job=node&"
#         url = url_first_sec+url_second_sec
#         return (url)


    def get_system_time(self):
        """
        Gets OS time in the millisec format
        :rtype: Int
        """
        millisec = int(time.time() * 1000)
        return (millisec)
    
    
    def get_time_filter_value(self, time):
        """
        Helper function to map time filter values
        :param time: time expressed in natural language e.g, last 15 minutes  
        :rtype: Int
        """
        for timefilter in self.dashboard_info['time_filters']:
            #print(timefilter)
            if (timefilter['name'] == time):
                return (timefilter['value'])


#     def get_graph_panelid(self, graphname):
#         """
#         Helper function to map graph name to panel id
#         :param graphname: name of the graph to be displayed  
#         :rtype: String
#         """
#         for graph in self.dashboard_info['graph_panels']:
#             if (graph['name']== graphname):
#                 return (graph['panel_id'])


#     def add_filter(self, url, time, graphname):
#         """
#         Creates time and graph filters and appends the values to the url
#         :param url: formed url of the prometheus graphs
#         :param time: time filter
#         :param graphname: name of the graph to be displayed
#         :rtype: String
#         """
#         currentEpoch = self.get_system_time()
#         timeString = "from="+str(currentEpoch-self.get_time_filter_value(time=time))+"&to="+str(currentEpoch)
#         graphString = "&panelId="+self.get_graph_panelid(graphname=graphname)
#         finalUrl = url + timeString + graphString
#         return (finalUrl)

    def add_time_filter(self, url, filter_name):
        
        tf = self.get_available_time_filter_info(filter_name)
        if "refresh" in tf:
            time_string = f'from=now-{tf["value"]}&to=now&refresh={tf["refresh"]}'
        else: 
            current_epoch = self.get_system_time()
            time_string = f'from={current_epoch-tf["value"]}&to={str(current_epoch)}'
            #time_string = "from="+str(current_epoch-self.get_time_filter_value(time=time_filter))+"&to="+str(current_epoch)
        return f"{url}&{time_string}"


#     def find_node_IP(self, nodename):
#         """
#         Helper function to get the IP address based on the node name 
#         :param nodename: name of the node
#         :rtype: String
#         """
#         for node in self.meas_net_info['node_info']:
#             if (node['node_name']== nodename):
#                 return (node['node_ip'])


#     def add_node_and_disk(self, url, nodename):
#         """
#         Converts node name to the corresponding IP used in meas_net
#         appends the disk name and node IP to the url
#         :param url: formed url of the prometheus graphsdisplay
#         :param nodename: name of the node
#         :rtype: String
#         """
#         diskdevice = "&var-diskdevices=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B&"
#         finalurl = url+"var-node="+self.find_node_IP(nodename=nodename)+"%3A9100&"+diskdevice
#         return (finalurl)

    def add_node_name(self, url, node_name):
        return f"{url}&var-node={node_name}"
    
    def add_interface_name(self, url, interface_name):
        return f"{url}&var-device={interface_name}"

    def add_var(self, url, var_name, var_value):
        return f"{url}&var-{var_name}={var_value}"        
    
    def convert_to_iframe(self, url):
        """
        Wraps the url in the iframe code 
        :param url: formed url of the prometheus graphs
        :rtype: String
        """
        return '<iframe src="'+ url + '" width="900" height="500" frameborder="0"></iframe>'
    
    
    def determine_dropdown_values(self, dashboard_name):
        """
        Sets the available panel names in the dropdown based on the dashboard name
        Controls the visibility of the interface name dropdown and only shows it for network traffic dashboard  
        :param dashboard_name: the selected dashboard name in the dropdown
        :rtype: String
        """
        if (dashboard_name == '------'):
            self.graph_widget.options = ['------']
            self.device_widget.layout.visibility= 'hidden'
        else:
            self.graph_widget.options = self.get_panel_names(dashboard_name)
            if dashboard_name =='network-traffic-dashboard':
                self.device_widget.layout.visibility = 'visible'
            else:
                self.device_widget.layout.visibility= 'hidden'
    
    def determine_interface_names_dropdown(self, node_name):
        """
        Calculates the available interface names in the dropdown based on the selection of node name
        """
        self.device_widget.options = self.get_interface_names(node_name)[0]
            
    
    
    def imageViewer(self, dashboard_name, panel_name, time_filter, node_name, interface_name):
        """
        Generates the url of the prometheus graphs based on user's selection in the dropdown menu
        displays the url in the HTML format
        """
        #print(time_filter)
        if (dashboard_name=='------' or panel_name=='------' or time_filter=='------' or node_name=='------' or interface_name=='------'):
            display(HTML())
        else:     
            url = self.grafana_panel_url(dashboard_name, panel_name)
            #print(url)
            url = self.add_time_filter(url, time_filter)
            #print(url)
            url = self.add_node_name(url, node_name)
            #print(url)
            #iframe = self.convert_to_iframe(url)
            if (interface_name!='------' and self.device_widget.layout.visibility == 'visible'):
                url = self.add_interface_name(url, interface_name)
            print(url)
            finalHTML = HTML(self.convert_to_iframe(url))
            display(finalHTML)


#     def imageViewer(self, graphType, timeFilter, nodeName):
#         """
#         Generates the url of the prometheus graphs based on user's selection in the dropdown menu
#         displays the url in the HTML format
#         """
#         url = self.prometheus_url
#         available_graph = []
#         for p in self.get_panel_names("node-exporter-full"):
#             available_graph.append(p)
#         # for graph in self.dashboard_info['graph_panels']:
#         #     available_graph.append(graph['name'])
#         if (graphType in available_graph):
#             intermediateurl = self.add_node_and_disk(url=url, nodename=nodeName)
#             finalUrl = self.add_filter(url=intermediateurl, time=timeFilter, graphname=graphType)
#             finalHTML = HTML(self.convert_to_iframe(finalUrl))
#             display(finalHTML)
#         else:
#             display(HTML())


    def visualize_live_prometheus(self):
        """
        Creates the UI 
        """
        tab = widgets.Tab()
        self.dashboard_widget = widgets.Dropdown(options=(['------']+self.get_dashboard_names()))
        self.graph_widget = widgets.Dropdown(description='panel_name', options=['------'])
        self.time_widget = widgets.Dropdown(options=['------']+self.get_available_time_filter_names())
        self.node_widget = widgets.Dropdown(options=['------']+list(self.slice_node_info.keys()))
        self.device_widget = widgets.Dropdown(description='interface_name', options=['------'])
        self.device_widget.layout.visibility= 'hidden'
        
        i = interactive(self.determine_dropdown_values, dashboard_name = self.dashboard_widget)
        j = interactive(self.determine_interface_names_dropdown, node_name = self.node_widget)
        k = interactive(self.imageViewer,dashboard_name=self.dashboard_widget, panel_name=self.graph_widget, time_filter=self.time_widget, node_name=self.node_widget, interface_name = self.device_widget)
        tab.children = [VBox(list(k.children))]
        # deprecated version of set title
        #tab.set_title(0, "graph viewer")
        tab.titles=['Graph Viewer'] 
        display(tab)
        
        
    def get_available_panel_names(self):
        """
        Returns a list of available panel names for all dashboards
        :rtype:List
        """
        panel_list=[]
        for d in self.get_dashboard_names():
            panel_list+=self.get_panel_names(dashboard_name=d)
        panel_list.sort()
        return (panel_list)
    
    def check_parameters(self, dashboard_name, panel_name, node_name, interface_name):
        """
        Checks the input parameters
        if panel_name belongs to network-traffic-dashboard, then interface_name cannot be none
        """
        if (dashboard_name not in self.get_dashboard_names()):
            raise Exception(f"{dashboard_name} is not supported. See supported ones using: print(mfv.get_dashboard_names())")
        if (panel_name not in self.get_panel_names(dashboard_name)):
            raise Exception(f"{dashboard_name} does not have panel called {panel_name}. See available panels using: print(mfv.get_panel_names('{dashboard_name}'))")
        if (panel_name in self.get_panel_names(dashboard_name='network-traffic-dashboard') and (dashboard_name=='network-traffic-dashboard') and interface_name is None):
            raise Exception(f"Please specify interface_name=interface name in the call argument. To get interface names, run print(mfv.get_interface_names('{node_name}'))")
        if ((dashboard_name=='node-exporter-full') and interface_name is not None):
            raise Exception(f"This panel does not require interface_name. Please remove interface_name from the call")
        
    def check_time_filters(self, time_filter):
        """
        Checks whether the input time filter is supported by the library
        """
        if (time_filter not in self.get_available_time_filter_names()):
            raise Exception(f"The input time filter is not supported. See supported ones using: print(mfv.get_available_time_filter_names())")
        
    def check_node_names(self, node_name, interface_name):
        """
        Checks whether the input node name is monitored by the measurement framework
        """
        if (node_name not in self.get_available_node_names()):
            raise Exception(f"This node name is not in the slice. See supported ones using: print(mfv.get_available_node_names())")
        if (interface_name is not None and interface_name not in self.get_interface_names(node_name)[0]):
            raise Exception(f"{node_name} does not have interface {interface_name}. See available interfaces using: print(mfv.get_interface_names('{node_name}')[0])")
            
    
    
    def grafana_solo_dashboard_url_download(self, dashboard_name):
        """
        The base url to get just a panel.
        """
        ret_val = ""
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                ret_val = f'{self.grafana_base_url}/render/d-solo/{d["uid"]}/{d["name"]}?orgId=1' 
        return ret_val
    
    def grafana_panel_url_download(self, dashboard_name, panel_name):
        ret_val = self.grafana_solo_dashboard_url_download(dashboard_name)
        for d in self.dashboard_info["dashboards"]:
            if d["name"] == dashboard_name:
                #print(d["panels"])
                for p in d["panels"]:
                    if p["name"] == panel_name:
                        ret_val = f'{ret_val}&panelId={p["id"]}'
                # add vars
                for v in d["vars"]:
                    if "default" in v:
                        ret_val += f'&var-{v["name"]}={v["default"]}'
        return ret_val
    
    def generate_download_url(self, dashboard_name, panel_name, time_filter, node_name, interface_name=None):
        """
        Method that calculates the download url of the graph
        """
        self.check_node_names(node_name, interface_name)
        self.check_parameters(dashboard_name, panel_name, node_name, interface_name)
        self.check_time_filters(time_filter=time_filter)
        url = self.grafana_panel_url_download(dashboard_name, panel_name)
        url = self.add_time_filter(url, time_filter)
        url = self.add_node_name(url, node_name)
        if interface_name:
            url = self.add_interface_name(url, interface_name)
        return url
    
    def add_timezone_to_url(self, url, timezone):
        encoded_tz= urllib.parse.quote(timezone, safe='')
        return (f'{url}&tz={encoded_tz}')
        
    def download_graph(self, dashboard_name, panel_name, time_filter, node_name, interface_name=None, file_name=None, time_zone=None):
        if file_name:
            file = file_name
        else:
            name = panel_name.replace(" ", "-")
            file = f'/home/fabric/work/{name}.png'
        if interface_name:
            url = self.generate_download_url(dashboard_name, panel_name, time_filter, node_name, interface_name=interface_name)
        else:
            url = self.generate_download_url(dashboard_name, panel_name, time_filter, node_name)
        if time_zone:
            final_url = self.add_timezone_to_url(url, time_zone)
        else:
            final_url=url
        print (final_url)
        r = requests.get(final_url, verify=False)
        print (r.status_code)
        if r.status_code == 200:
            with open(file, 'wb') as f:
                f.write(r.content)
    