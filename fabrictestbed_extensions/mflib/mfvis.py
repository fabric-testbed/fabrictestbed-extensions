import json
import traceback
import os
import time
import configparser
from ipywidgets import VBox, HTML, Output, interactive
import ipywidgets as widgets
from IPython.display import display
from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.mflib.mflib import mflib

class mfvis():
    meas_net_info = {}
    dashboard_info = {}
    prometheus_url = None
    
    
    def __init__(self):
        """
        Constructor. Builds Manager for mfvis object.
        """
        super().__init__()
    
    
    def init(self,slicename):
        """
        Sets up the mfvis object to visualize prometheus graphs in grafana 
        :param slicename: The name of the slice.
        """
        print(f"Initing slice {slicename} for visualization")
        self.meas_net_info = self.get_meas_net_info(slicename=slicename)
        self.dashboard_info = self.set_dashboard_info()
        self.prometheus_url = self.get_prometheus_url()
        
    
    def read_prometheus_ini_file(self, slicename):
        """
        Check the existence of prometheus hosts ini file 
        Reads the node name and IP address from the file
        """
        local_storage_directory = "/tmp/mflib/"
        local_slice_directory = os.path.join(local_storage_directory, slicename)
        promhosts_file = os.path.join(local_slice_directory, "hosts.ini")
        exp_node_lines=[]
        exp_node_info = []
        if not os.path.exists(promhosts_file):
            try:
                mf=mflib()
                mf.init(slicename)
                print (f"File {promhosts_file} does not exist. Proceed to downlaod the file.")
                filename, filecontents = mf.download_common_hosts()
            except Exception as e:
                print(f"Download fails: {e}")
                return []
                traceback.print_exc()
        if os.path.exists(promhosts_file):
            try:
                print (f"Found host file at {promhosts_file}")
                with open(promhosts_file) as pif:
                    lines = pif.readlines()
                    for line in lines:
                        if "[Experiment_Nodes]" in line:
                            index=lines.index(line)
                            exp_nodes=lines[index+1:]
            except Exception as e:
                    print(f"Fail to read promhosts.ini")
                    print(f"Fail: {e}")
                    return []
            for node in exp_nodes:
                node=node.strip()
                info={}
                node_name=node.split()[0]
                node_ip=node.split("=")[-1]
                info['node_name']=node_name
                info['node_ip']=node_ip
                exp_node_info.append(info)
            return (exp_node_info)            
        else:
            return []
            
            
    def get_meas_net_info(self, slicename):
        """
        Gets the info of the meas_net including the _meas_node IP, experiment node names and connected interface IPs 
        :param slicename: The name of the slice.
        :rtype: Dict
        """
        try:
            slice = fablib.get_slice(name=slicename)
            meas_node = slice.get_node(name="_meas_node")
            meas_net_info = {}
            meas_net_info['meas_node_ip'] = str(meas_node.get_management_ip())
            meas_net_info['node_info']=self.read_prometheus_ini_file(slicename=slicename)
            return (meas_net_info)
        except Exception as e:
            print(f"Fail: {e}")
            traceback.print_exc()
         
        
    def set_dashboard_info(self):
        """
        Sets the grafana prometheus dashboard info
        and the graphs (panel_id) available to be displayed
        Works for grafana dashboard 1860
        :rtype: Dict
        """
        dashboard_info = {}
        first_graph = {'name': 'prometheus network traffic', 'panel_id':'74'}
        second_graph = {'name': 'prometheus cpu', 'panel_id':'77'}
        first_time_filter = {'name': 'Last 15 minutes', 'value': 900000}
        second_time_filter = {'name': 'Last 1 hour', 'value': 3600000}
        dashboard_info['dashboard_info']= {'dashboard_uid': 'rYdddlPWk', 'dashboard_name': 'node-exporter-full'}
        dashboard_info['graph_panels'] = [first_graph, second_graph]
        dashboard_info['time_filters'] = [first_time_filter, second_time_filter]
        return (dashboard_info)
    
    
    def get_available_time_filter(self):
        """
        Returns the available time filters in the dropdown menu
        :rtype: List
        """
        available_time = []
        for timefilter in self.dashboard_info['time_filters']:
            available_time.append(timefilter['name'])
        return available_time
    
    
    def get_available_node_name(self):
        """
        Returns the available node names in dropdown menus excluding the meas_node 
        :rtype: List
        """
        available_nodes = []
        for node in self.meas_net_info['node_info']:
            available_nodes.append(node['node_name'])
        return available_nodes
    
    
    def get_available_graph_name(self):
        """
        Returns the available graph names to be displayed in the dropdown menu
        :rtype: List
        """
        available_graphs = []
        for graph in self.dashboard_info['graph_panels']:
            available_graphs.append(graph['name'])
        return available_graphs
     
        
    def get_prometheus_url(self):
        """
        Builds the basic url of the prometheus graphs in grafana
        currently the url uses localhost:10010 for visualization and 
        will be changed to the management IP of the meas_node in the future
        :rtype: String
        """
        ###To be changed
        #meas_node_ip = self.meas_net_info['meas_node_ip']
        ###
        meas_node_ip = "localhost:10010"
        dashboard_uid = self.dashboard_info['dashboard_info']['dashboard_uid']
        dashboard_name = self.dashboard_info['dashboard_info']['dashboard_name']
        #url_sec1 = "https://"+meas_node_ip+"/grafana/d-solo/"
        #url_sec2 = "?orgId=1&refresh=1m&var-DS_PROMETHEUS=Prometheus&var-job=node&"
        #url = url_sec1+dashboard_uid+"/"+dashboard_name+url_sec2
        url_first_sec = "https://{ip}/grafana/d-solo/{duid}/{dname}".format(ip=meas_node_ip, duid=dashboard_uid, dname=dashboard_name)
        url_second_sec = "?orgId=1&refresh=1m&var-DS_PROMETHEUS=Prometheus&var-job=node&"
        url = url_first_sec+url_second_sec
        return (url)
    
    
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
            if (timefilter['name']== time):
                return (timefilter['value'])
     
    
    def get_graph_panelid(self, graphname):
        """
        Helper function to map graph name to panel id
        :param graphname: name of the graph to be displayed  
        :rtype: String
        """
        for graph in self.dashboard_info['graph_panels']:
            if (graph['name']== graphname):
                return (graph['panel_id'])
    
    
    def add_filter(self, url, time, graphname):
        """
        Creates time and graph filters and appends the values to the url
        :param url: formed url of the prometheus graphs
        :param time: time filter
        :param graphname: name of the graph to be displayed
        :rtype: String
        """
        currentEpoch = self.get_system_time()
        timeString = "from="+str(currentEpoch-self.get_time_filter_value(time=time))+"&to="+str(currentEpoch)
        graphString = "&panelId="+self.get_graph_panelid(graphname=graphname)
        finalUrl = url + timeString + graphString
        return (finalUrl)
    
    
    def find_node_IP(self, nodename):
        """
        Helper function to get the IP address based on the node name 
        :param nodename: name of the node
        :rtype: String
        """
        for node in self.meas_net_info['node_info']:
            if (node['node_name']== nodename):
                return (node['node_ip'])
    
    
    def add_node_and_disk(self, url, nodename):
        """
        Converts node name to the corresponding IP used in meas_net
        appends the disk name and node IP to the url
        :param url: formed url of the prometheus graphs
        :param nodename: name of the node
        :rtype: String
        """
        diskdevice = "&var-diskdevices=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B&"
        finalurl = url+"var-node="+self.find_node_IP(nodename=nodename)+"%3A9100&"+diskdevice
        return (finalurl)
    
    
    def convert_to_iframe(self, url):
        """
        Wraps the url in the iframe code 
        :param url: formed url of the prometheus graphs
        :rtype: String
        """
        return '<iframe src="'+ url + '" width="900" height="500" frameborder="0"></iframe>'
    
    
    def imageViewer(self, graphType, timeFilter, nodeName):
        """
        Generates the url of the prometheus graphs based on user's selection in the dropdown menu
        displays the url in the HTML format
        """
        url = self.prometheus_url
        available_graph = []
        for graph in self.dashboard_info['graph_panels']:
            available_graph.append(graph['name'])
        if (graphType in available_graph):
            intermediateurl = self.add_node_and_disk(url=url, nodename=nodeName)
            finalUrl = self.add_filter(url=intermediateurl, time=timeFilter, graphname=graphType)
            finalHTML = HTML(self.convert_to_iframe(finalUrl))
            display(finalHTML)
        else:
            display(HTML())
     
    
    def visualize_prometheus(self):
        """
        Creates the UI 
        """
        tab = widgets.Tab()
        tab.set_title(0, 'graph viewer')
        graphList = ['------']+self.get_available_graph_name()
        graph_widget = widgets.Dropdown(options=graphList)
        timeFilterList = self.get_available_time_filter()
        nodeNameList = self.get_available_node_name()
        node_widget = widgets.Dropdown(options=nodeNameList)
        time_widget = widgets.Dropdown(options=timeFilterList)
        function = interactive(self.imageViewer,graphType=graph_widget, timeFilter = time_widget, nodeName = node_widget)
        tab.children = [VBox(list(function.children))]
        display(tab)
    
    
    
    
        
    