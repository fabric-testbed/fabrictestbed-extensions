from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager
import ipywidgets as widgets
from ipywidgets import HTML, Layout
import threading, paramiko
import logging
import threading
import time

#This class will create an IPYWidgets terminal that will interface with a node
class Terminal():
    #Class Variable
    node = None
    
    #Initializer, with a node input
    def __init__(self,node,username=None,private_key_file=None,private_key_passphrase=None,height = "300px"):
        self.node = node
        self.lastline = ""
        
        #Initialize Connection
        self.connect(username=username,private_key_file=private_key_file,private_key_passphrase=private_key_passphrase)
        #Style
        display(widgets.HTML(value="<style>.out_box{ border: 1px solid black; height: "+height+";display: flex;flex-direction: column-reverse; width: 99%; overflow: auto;display: flex;flex-direction: column-reverse;}</style>"))
        
        #Output
        self.out = widgets.Output()
        self.out.add_class('out_box')
        self.out.append_stdout("Connected to node: "+self.node.get_name()+"\n")
        #display(self.out)
        
        #Input
        self.inputcmd = widgets.Text(layout=Layout(width='80%'),description = self.node.get_name()+"$")
        self.inputcmd.on_submit(self.submit)
        self.inputcmd.add_class('inputt')
        self.uploadbtn = widgets.FileUpload(layout=Layout(width='10%'),multiple=True)
        self.uploadbtn.observe(self.upload_files)
        self.submitbtn = widgets.Button(description="submit",layout=Layout(width='10%'))
        
        self.inputs = widgets.HBox([self.inputcmd,self.uploadbtn,self.submitbtn])
        
        #display(self.inputs)
        self.submitbtn.on_click(self.submit)
        
        #Start Threading
        self.console_thread = threading.Thread(target=self.update_console)
        self.console_thread.start()
        
        self.consoleerr_thread = threading.Thread(target=self.update_err)
        self.consoleerr_thread.start()
        
        #Assemble Terminal
        self.TerminalItems = [self.out,self.inputs]     
        self.terminal = widgets.VBox(self.TerminalItems)
        
    #Upload files from upload button
    def upload_files(self,change):
        for i in self.uploadbtn.value:
            with open('/tmp/'+i.name, 'wb') as output_file: 
                content = i['content']   
                output_file.write(content)
                
            self.node.upload_file('/tmp/'+i.name,i.name)
            
        self.uploadbtn.value = list()
        return
    
    #Return the terminal
    def get_terminal(self):
        return self.terminal
    
    #Display Terminal
    def display_terminal(self):
        display(self.terminal)
        
    #Send command to node
    def submit(self,*args):
        self.lastcmd = self.inputcmd.value + "\n"
        self.inputcmd.value=""
        
        
        self.stdin.write(self.lastcmd)
        self.stdin.flush()     
        return
    
    #Execute a command
    def execute(self,cmd):
        self.lastcmd = cmd + "\n"
        
        self.stdin.write(self.lastcmd)
        self.stdin.flush()     
        return
    
    #Threaded Function to Update the Console
    def update_console(self):
        out=""
        for line in self.stdout:
            self.out.append_stdout(line)
            out +=line
            
    #Update from error
    def update_err(self):
        out=""
        for line in self.stderr:
            self.out.append_stdout(line)
            out +=line
            
    #Connect to Node
    def connect(self,username=None,private_key_file=None,private_key_passphrase=None):
        #Get and test src and management_ips
        management_ip = str(self.node.get_fim_node().get_property(pname='management_ip'))
        if self.node.validIPAddress(management_ip) == 'IPv4':
            src_addr = ('0.0.0.0',22)

        elif self.node.validIPAddress(management_ip) == 'IPv6':
            src_addr = ('0:0:0:0:0:0:0:0',22)
        else:
            raise Exception(f"node.execute: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)
        
        bastion_username=self.node.get_fablib_manager().get_bastion_username()
        bastion_key_file=self.node.get_fablib_manager().get_bastion_key_filename()

        if username != None:
            node_username = username
        else:
            node_username=self.node.username

        if private_key_file != None:
            node_key_file = private_key_file
        else:
            node_key_file=self.node.get_private_key_file()

        if private_key_passphrase != None:
            node_key_passphrase = private_key_passphrase
        else:
            node_key_passphrase=self.node.get_private_key_file()
            
        try:
            key = self.node.get_paramiko_key(private_key_file=node_key_file, get_private_key_passphrase=node_key_passphrase)
            self.bastion=paramiko.SSHClient()
            self.bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.bastion.connect(self.node.get_fablib_manager().get_bastion_public_addr(), username=bastion_username, key_filename=bastion_key_file)

            bastion_transport = self.bastion.get_transport()
            bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)

            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(management_ip,username=node_username,pkey = key, sock=bastion_channel)
            
            self.channel = self.client.invoke_shell()
            
            self.stdin = self.channel.makefile('wb')
            self.stdout = self.channel.makefile('r')
            self.stderr = self.channel.makefile_stderr('rb')
        except Exception as e:
            print(f"{e}")
            try:
                self.client.close()
            except:
                print("Exception in client.close")
                pass
            try:
                self.bastion_channel.close()
            except:
                print("Exception in bastion_channel.close()")
                pass
            
    #Close connections
    def close(self):
        self.client.close()
        self.bastion.close()
        return
    
    #Cleanup
    def __del__(self):
        self.close()
            
#Main Class
class FabricTerminal():
    #Class Variable
    NodeNames = []
    Terminals = []
    
    #Initializer, with variable node input
    def __init__(self,*args,username=None,private_key_file=None,private_key_passphrase=None,height = "300px"):
        self.NodeNames = []
        self.TerminalsBox = []
        self.Terminals = []
        for node in args:
            curterm = Terminal(node)
            self.Terminals.append(curterm)
            self.TerminalsBox.append(curterm.get_terminal())
            self.NodeNames.append(node.get_name())
        
        self.tab = widgets.Tab()
        self.tab.children = self.TerminalsBox
        
        self.tab.titles = self.NodeNames
        display(self.tab)
        
    #Return Widget
    def get_widget(self):
        return self.tab
    
    #Display Widget
    def display(self):
        display(self.tab)
        
    #Remove an index
    def delete_at(self,index):
        self.get_at(index).close()
        
        self.Terminals.pop(index)
        self.TerminalsBox.pop(index)
        self.NodeNames.pop(index)
        self.tab.children = self.TerminalsBox
        self.tab.titles = self.NodeNames
        return 
    
    #Get at an index
    def get_at(self,index):
        return self.Terminals[index]
    
    #Get by name
    def get_byname(self,name):
        for i in range(len(self.NodeNames)):
            if self.NodeNames[i] == name:
                return self.get_at(i)
            
    #Add node to a terminal
    def add_node(self,node):
        curterm = Terminal(node)
        self.Terminals.append(curterm)
        self.TerminalsBox.append(curterm.get_terminal())
        self.NodeNames.append(node.get_name())
        self.tab.children = self.TerminalsBox
        self.tab.titles = self.NodeNames
        
    #Cleanup all terminals
    def close(self):
        while len(self.Terminals)>0:
            self.delete_at(0)
            
    #Cleanup
    def __del__(self):
        self.close()