import json
import traceback
from fabrictestbed_extensions.fablib.fablib import fablib
import os
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from os import chmod

import paramiko

#https://learn.fabric-testbed.net/knowledge-base/using-ipv4-only-resources-like-github-or-docker-hub-from-ipv6-fabric-sites/

class mflib():
    
    measurement_node_name = "_meas_node"
    repo_branch = "experiment_mflib"
    
    # Place to put downloaded files?
    local_storage_directory = "/tmp/mflib"
    
    # Need the slice name to connect to slice
    slicename = None
    # The slice ojb
    slice = None
    # Need private key to access the mfuser on the meas node. It is stored on the slice users account on the meas node.
    mfuser_private_key_file = os.path.join(local_storage_directory, "mfuser_private_key")
    # The slice's meas node 
    meas_node = None
      
    # Keep a copy of the bootstrap status
    bootstrap_status_file = os.path.join(local_storage_directory, "bootstrap_status.json")

    # Services directory on meas node
    services_directory = os.path.join("/", "home", "mfuser", "services")

    # Many methods use the followig parameter set
    # service - unique service name
    # command - command to run in services directory on meas node
    # data - JSON serializable object
    # files - list of files to upload
    def __init__(self):
        """
        Constructor. Builds MFManager for mflib object.
        """
        super().__init__()
        try:
            os.makedirs("/tmp/mflib")
        except:
            pass
        
    def instrumentize(self):
        print("Setting up Prometheus")
        self.create("prometheus")
        
        print("Instrumentize Done.")
        #etc...

    def init(self,slicename):
        """
        Sets up the mflib object to ensure slice can be monitored.
        :param slicename: The name of the slice.
        :rtype: String
        """
        print(f"Init-ing {slicename}")
        
        ########################
        # Get slice 
        ########################
        self.slicename = slicename
        self.slice = fablib.get_slice(name=slicename)
        
        ########################
        # Check for prequisites
        #######################
        
        # Does Measurement Node exist in topology?
        if not self.find_meas_node():
            print("Failed to find meas node. Need to addMeasureNode first.")
            return False
        
        print(f"Found meas node as {self.meas_node.get_name()}")
        
        bss = self.get_bootstrap_status()
        print("bootstrap status is")
        print(bss)
        
        if ("status" in bss and bss["status"] == "ready"):
            # Slice already instrumentized and ready to go.
            self.get_mfuser_private_key() 
            print("Slice Measurement Framework is ready")
            return
        else: 
            
            ###############################
            # Need to do some boostrapping
            ###############################
 

                
            ######################   
            # Create MFUser keys
            #####################
            #if "mfuser_keys" in bss and bss["mfuser_keys"] =="ok":
            if True:
                print ("Generating MFUser Keys\n")
                key = rsa.generate_private_key(
                    backend=crypto_default_backend(),
                    public_exponent=65537,
                    key_size=2048
                )

                private_key = key.private_bytes(
                    crypto_serialization.Encoding.PEM,
                    crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                    crypto_serialization.NoEncryption()
                )

                public_key = key.public_key().public_bytes(
                    crypto_serialization.Encoding.OpenSSH,
                    crypto_serialization.PublicFormat.OpenSSH
                )

                # Decode to printable strings
                private_key_str = private_key.decode('utf-8')
                public_key_str = public_key.decode('utf-8')

                # Save public key & change mode
                public_key_file = open("/tmp/mflib/mfuser.pub", 'w');
                public_key_file.write(public_key_str);
                public_key_file.write('\n');
                public_key_file.close()
                chmod("/tmp/mflib/mfuser.pub", 0o644);

                # Save private key & change mode
                private_key_file = open("/tmp/mflib/mfuser", 'w');
                private_key_file.write(private_key_str);
                private_key_file.close()
                chmod("/tmp/mflib/mfuser", 0o600);

                print("MFUser keys Done")
            
            
                
            ###############################
            # Add mfusers
            ##############################
            #if "mfusers" in bss and bss["mfusers"] =="ok":
            if True:  
                #Install mflib user/environment
                print("Installing mfusers\n")
   
                #Add user
                threads = []
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("sudo useradd -G root -m mfuser")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])
                #Setup ssh 
                threads = []
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("sudo mkdir /home/mfuser/.ssh; sudo chmod 700 /home/mfuser/.ssh; sudo chown -R mfuser:mfuser /home/mfuser/.ssh")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])

                #Edit commands
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("echo 'mfuser ALL=(ALL:ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers.d/90-cloud-init-users")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])

                #Upload keys
                for node in self.slice.get_nodes():
                    try:
                        node.upload_file("/tmp/mflib/mfuser.pub","ansible.pub")
                    except Exception as e:
                        print(f"Fail: {e}")

                #Edit commands
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("sudo mv ansible.pub /home/mfuser/.ssh/ansible.pub; sudo chown mfuser:mfuser /home/mfuser/.ssh/ansible.pub;")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])

                #Raise Key
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("sudo cat /home/mfuser/.ssh/ansible.pub | sudo tee -a /home/mfuser/.ssh/authorized_keys;")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])

                #Authorize key
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("sudo chmod 644 /home/mfuser/.ssh/authorized_keys; sudo chown mfuser:mfuser /home/mfuser/.ssh/authorized_keys")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])

                # TODO move to meas node ansible script
                #Installs
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append([node,node.execute_thread_start("curl -fsSL https://test.docker.com -o test-docker.sh; sudo sh test-docker.sh; sudo apt-get -y update; sudo apt-get install -y python3-pip; sudo pip install docker")])
                    except Exception as e:
                        print(f"Fail: {e}")
                for thread in threads:
                       thread[0].execute_thread_join(thread[1])

              
            
                # Upload mfuser private key to meas node & move to mfuser account
                self.meas_node.upload_file("/tmp/mflib/mfuser","mfuser")
                # cp so as to keep a key copy where the slice owner can grab it
                self.meas_node.execute("sudo cp mfuser /home/mfuser/.ssh/mfuser; sudo chown mfuser:mfuser /home/mfuser/.ssh/mfuser; sudo chmod 600 /home/mfuser/.ssh/mfuser")

                print("mfusers done")
            

            #######################
            # Clone mf repo 
            #######################
            #if "repo_cloned" in bss and bss["repo_cloned"] =="ok":
            if True:
                self._clone_mf_repo()
                
                
                
            #######################################
            # Create measurement network interfaces  
            # & Get hosts info for hosts.ini
            ######################################
            #if "meas_network" in bss and bss["meas_network"] =="ok":
            if True:
                self._make_hosts_ini_file(set_ip=True)
                
                
            
            #######################
            # Run Bootstrap script
            ######################
            #if "bootstrap_script" in bss and bss["bootstrap_script"] =="ok":
            if True:
                print("Bootstrapping measurement node.")
                self._run_bootstrap_script()
            
            self._update_bootstrap("status", "ready")
            print("Init Done")
            return True
        
            self.meas_node.execute("cd mf_git/instrumentize/ansible/fabric_experiment_instramentize;/home/ubuntu/.local/bin/ansible-playbook -i ~/mf_git/promhosts.ini -b playbook_fabric_experiment_install_prometheus.yml")
            
            self.meas_node.execute("sudo apt install acl -y")
            
            print("done heres what to do...tunnel to grafana via bastion")
            
                
    #def submit(self,slice):    
    def addMeasNode(self,slice):
        """
        Adds measurement components to an unsubmitted slice, then submits.
        :param slice: Unsubmitted Slice
        :rtype: Slice
        """
        
        interfaces = []
        sites = []
        num = 1
        
        for node in slice.get_nodes():
            interfaces.append(node.add_component(model='NIC_Basic', name=("Meas_Nic"+str(num))).get_interfaces()[0])
            sites.append(node.get_site())
            num += 1
        site = max(set(sites), key = sites.count)
        
        meas = slice.add_node(name="_meas_node", site=site)
        meas.set_capacities(cores="4", ram="16", disk="50")
        meas.set_image("default_ubuntu_20")
        interfaces.append(meas.add_component(model='NIC_Basic', name="Meas_Nic").get_interfaces()[0])
        meas_net = slice.add_l2network(name="_meas_net", interfaces=interfaces)
        
        #slice.submit()
        #return
    

# User Methods 
    def create(self, service, data=None, files=[]):
        """
        Creates a new service for the slice. 
        :param service: The name of the service.
        :type service: String
        :param data: Data to be passed to a JSON file place in the service's meas node directory.
        :type data: JSON serializable object.
        :param files: List of filepaths to be uploaded.
        :type files: List of Strings
        """
        self._run_on_meas_node(service, "create", data, files)

    def update(self, service, data=None, files=[]):
        """
        Updates an existing service for the slice.
        :param service: The name of the service.
        :type service: String
        :param data: Data to be passed to a JSON file place in the service's meas node directory.
        :type data: JSON serializable object.
        :param files: List of filepaths to be uploaded.
        :type files: List of Strings
        """
        self._run_on_meas_node(service, "update", data, files)

    def info(self, service, data=None):
        """
        Gets inormation from an existing service. Strictly gets information, does not change how the service is running.
        :param service: The name of the service.
        :type service: String
        :param data: Data to be passed to a JSON file place in the service's meas node directory.
        :type data: JSON serializable object.
        """
        self._run_on_meas_node(service, "info", data)

        
        
    def start(self, services=[]):
        """
        Restarts a stopped service using existing configs on meas node.
        """
        for service in services:
            self._run_on_meas_node(service, "start")

    def stop(self, services=[]):
        """
        Stops a service, does not remove the service, just stops it from using resources.
        """
        for service in services:
            self._run_on_meas_node(service, "stop")

    def status(self, services=[]):
        """
        Deprecated?, use info instead?
        Returns predefined status info. Does not change the running of the service.
        """ 
        for service in services:
            self._run_on_meas_node(service, "status")

    def remove(self, services=[]):
        """
        Stops a service running and removes anything setup on the experiment's nodes. Service will then need to be re-created using the create command before service can be started again.
        """
        for service in services:
            self._run_on_meas_node(service, "remove")



# Utility Methods
     


    def find_meas_node(self):
        """
        Finds the node named "meas" in the slice and sets the value for class's meas_node
        :return: If node found, sets self.meas_node and returns True. If node not found, clears self.meas_node and returns False.
        :rtype: Boolean
        """
        try:
            #slice = fablib.get_slice(self.slicename)
            for node in self.slice.get_nodes():
                if node.get_name() == self.measurement_node_name:
                    self.meas_node = node 
                    return True 
        except Exception as e:
            print(f"Fail: {e}")
        self.meas_node = None
        return False


        
    def _run_on_meas_node(self, service, command, data=None, files=[]):
        """
        Runs a command on the meas node.
        :param service: The name of the service.
        :type service: String
        :param command: The name of the command to run.
        :type command: String
        :param data: Data to be passed to a JSON file place in the service's meas node directory.
        :type data: JSON serializable object.
        :param files: List of filepaths to be uploaded.
        :type files: List of Strings
        :return: The stdout & stderr values from running the command ? Reformat to dict??
        :rtype: String ? dict??
        """
        # upload resources 
        if data:
            self._upload_service_data(service, data)
        if files:
            self._upload_service_files(service, files)

        # run command 
        return self._run_service_command(service, command )

        
    def _upload_service_data(self, service, data):
        """
        Uploads the json serializable object data to a json file on the meas node.
        :param service: The service to which the data belongs.
        :type service: String
        :param data: A JSON serializable dictionary 
        :type data: dict
        """
        try:
            local_file_path = "tmp_mf_service_data.json"
            remote_file_path = os.path.join(self.services_directory, service, "data.json")
            with open(local_file_path) as datafile:
                json.dump(data, datafile)
            stdout, stderr = self.meas_node.upload_file(local_file_path, remote_file_path) # retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key")
        except Exception as e:
            print(f"Fail: {e}")



    def _upload_service_files(self, service, files):
        """
        Uploads the given local files to the given service's directory on the meas node.
        :param service: Service name for which the files are being upload to the meas node.
        :type service: String
        :param files: List of file paths on local machine.
        :type files: List
        :raises: Exception: for misc failures....
        :return: ?
        :rtype: ?
        """

        # TODO could add option to upload a directory of files using fablib.upload_directory
        try:
            for file in files:
                # Set src/dst filenames
                # file is local path
                local_file_path = file 
                filename = os.path.basename(file)
                remote_file_path = os.path.join(self.services_directory, service, filename)
                # upload file
                stdout, stderr = self.meas_node.upload_file(local_file_path, remote_file_path) # retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key")
        except Exception as e:
            print(f"Fail: {e}")


    def _run_service_command( self, service, command ):
        """
        Runs the given comand for the given service on the meas node. 
        :param service: Service name for which the command is being run on the meas node.
        :type service: String
        :param files: Command name.
        :type files: String
        :raises: Exception: for misc failures....
        :return: Resulting output? JSON output or dictionary?
        :rtype: ?
        """

        try:
            #full_command = f"python {self.services_directory}/{service}/{command}.py"
            full_command = f"sudo -u mfuser python3 {self.services_directory}/{service}/{command}.py"
            stdout, stderr = self.meas_node.execute(full_command) #retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key"
        except Exception as e:
            print(f"Fail: {e}")
        print(stdout)
        print(stderr)
        return (stdout, stderr)


    def _download_service_file(self, service, filename):
        """
        Downloads service files from the meas node and places them in the local storage directory.
        :param service: Service name
        :type service: String
        :param filename: The filename to download from the meas node.
        """
        # 
        #  Download a file from a service directory
        # Probably most useful for grabbing output from a command run.
        # TODO figure out how to name/where to put file locally
        try:
            local_file_path = os.path.join(local_storage_directory, service, filename)
            remote_file_path = os.path.join(self.services_directory, service, filename)
            stdout, stderr = self.meas_node.download_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
        except Exception as e:
            print(f"Fail: {e}")
        
        
        
        
#############untested############################        
    def _execute( self, command):
        """
        Does the same thing that node.execute would do in fablib, but uses the mfuser account.
        """
       
        key = paramiko.RSAKey.from_private_key_file(self.mfuser_private_key_file)
        bastion=paramiko.SSHClient()
        bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #bastion.connect(bastion_public_addr, username=self.bastion_username, key_filename=self.bastion_private_key_file)
        bastion.connect(fablib.get_bastion_public_addr(), username=fablib.get_bastion_username(), key_filename=fablib.get_bastion_key_filename())

        bastion_transport = bastion.get_transport()
        src_addr = (bastion_private_ipv6_addr, 22)

        dest_addr = (self.meas_ip, self.meas_port)
        bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)


        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.meas_ip,username=mfuser,pkey = key, sock=bastion_channel)

        stdin, stdout, stderr = client.exec_command(command )

        stdout_str = str(stdout.read(),'utf-8').replace('\\n','\n')
        stderr_str = str(stderr.read(),'utf-8').replace('\\n','\n')

        client.close()

        return  (stdout, stderr)   
        
    def _scp_file(isrcfile, destfile):
        print("SCPing file: {0}".format(srcfile))

        key = paramiko.RSAKey.from_private_key_file(self.mfuser_private_key_file)
        bastion=paramiko.SSHClient()
        bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        bastion.connect(bastion_public_addr, username=self.bastion_username, key_filename=self.bastion_private_key_file)

        bastion_transport = bastion.get_transport()
        src_addr = (bastion_private_ipv6_addr, 22)

        dest_addr = (self.meas_ip, self.meas_port)
        bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.meas_ip,username=mfuser,pkey = key, sock=bastion_channel)

        sftp = client.open_sftp()
        sftp.put(srcfile, destfile)
        sftp.close()
        client.close()
##################end untested############################
        
        
        
    def _make_hosts_ini_file(self, set_ip=False):
        hosts = []                    
        num=1
        base = "10.0.0."
        hosts = []
        print("Setting measurement nic IPs")
        for node in self.slice.get_nodes():
            for interface in node.get_interfaces():
                if ("Meas_Nic" in interface.get_name()):
                    ip = base + str(num)
                   
                    if set_ip:
                        print("setting interface ip")
                        interface.set_ip(ip = ip, cidr = "24")
                    hosts.append("{0} ansible_host={1} hostname={1} ansible_ssh_user={2} node_exporter_listen_ip={1} node_exporter_username={3} node_exporter_password={3} snmp_community_string={4} grafana_admin_password={3} fabric_prometheus_ht_user={3} fabric_prometheus_ht_password={3}".format(node.get_name(), ip ,"mfuser","fabric","not-in-use"))
                    num+=1


        print("Creating Ansible Hosts File\n")
        # Prometheus e_Elk
        hosts_txt = ""
        e_hosts_txt = ""

        experiment_nodes = "[Experiment_Nodes]\n"
        e_experiment_nodes = "[workers]\n"
        for host in hosts:
            if "_meas_node" in host:

                hosts_txt += "[Meas_Node]\n"
                hosts_txt += host + '\n\n'

                e_hosts_txt += "[elk]\n"
                e_hosts_txt += host + '\n\n'

            else: # It is an experimenters node
                experiment_nodes += host + '\n'
                e_experiment_nodes += host + '\n'

        hosts_txt += experiment_nodes
        e_hosts_txt += e_experiment_nodes
        with open('/tmp/mflib/promhosts.ini', 'w') as f:
            f.write(hosts_txt)
        with open('/tmp/mflib/elkhosts.ini', 'w') as f:
            f.write(e_hosts_txt)

        print("Uploading hosts files")
        # Upload
        self.meas_node.upload_file("/tmp/mflib/promhosts.ini","promhosts.ini")
        stdout, stderr = self.meas_node.execute("sudo mv promhosts.ini /home/mfuser/mf_git/instrumentize/ansible/fabric_experiment_instramentize/promhosts.ini")
        print(stdout)
        print(stderr)
        stdout, stderr = self.meas_node.execute("sudo chown mfuser:mfuser /home/mfuser/mf_git/instrumentize/ansible/fabric_experiment_instramentize/promhosts.ini")
        print(stdout)
        print(stderr)
        
        self.meas_node.upload_file("/tmp/mflib/elkhosts.ini","elkhosts.ini")
        self.meas_node.execute("sudo mv elkhosts.ini /home/hosts/mf_git/elkhosts.ini")
        
        
        
    def _clone_mf_repo(self):
        """
        Clone the repo to the mfuser on the meas node.|
        """
        cmd = f"sudo -u mfuser git clone -b {self.repo_branch} https://github.com/fabric-testbed/MeasurementFramework.git /home/mfuser/mf_git"
        stdout, stderr = self.meas_node.execute(cmd)
        #print(stdout)
        #print(stderr)
        
    def _run_bootstrap_script(self):
        """
        Run the initial boostrap script in the meas node mf repo.
        """
        cmd = f'sudo -u mfuser /home/mfuser/mf_git/instrumentize/experiment_bootstrap/bootstrap.sh'
        stdout, stderr = self.meas_node.execute(cmd)
        print(stdout)
        print(stderr)
        print("Boostrap script done")
        

    ############################
    # Calls made as slice user
    ###########################
    def get_bootstrap_status(self, force=True):
        """
        Returns the bootstrap status for the slice. Default setting of force will always download the most recent file from the meas node.
        :param force: If downloaded file already exists locally, it will not be downloaded unless force is True. The downloaded file will be stored locally for future reference. 
        :return: Bootstrap dict if any type of bootstraping has occured, None otherwise. 
        :rtype: dict
        """
        if force or not os.path.exists(self.bootstrap_status_file):
            if not self._download_bootstrap_status():
                print("Boostrap file was not downloaded.")
                return {}
        
            
        if os.path.exists(self.bootstrap_status_file):
            with open(self.bootstrap_status_file) as bsf:
                try:
                    bootstrap_dict = json.load(bsf)
                    print(bootstrap_dict)
                    if bootstrap_dict:
                        return bootstrap_dict 
                    else:
                        return {}
                except Exception as e:
                    print(f"Bootstrap failed to decode")
                    print(f"Fail: {e}")
                    return {}
        else:
            return {}


    def _download_bootstrap_status(self):
        """
        Downloaded file will be stored locally for future reference.  
        :return: True if bootstrap file downloaded, False otherwise. 
        :rtype: Boolean # or maybe just the entire json?
        """
        try:
            local_file_path = self.bootstrap_status_file
            remote_file_path =  os.path.join("bootstrap_status.json")
            #print(local_file_path)
            #print(remote_file_path)
            file_attributes = self.meas_node.download_file(local_file_path, remote_file_path, retry=1) #, retry=3, retry_interval=10): # note retry is really tries
            #print(file_attributes)
            
            return True
        except Exception as e:
            print("Bootstrap download has failed.")
            print(f"Fail: {e}")
            return False
        return False  
    
    
    
    def get_mfuser_private_key(self, force=True):
        """
        Returns the mfuser private key. Default setting of force will always download the most recent file from the meas node.
        :param force: If downloaded file already exists locally, it will not be downloaded unless force is True. The downloaded file will be stored locally for future reference. 
        :return: True if file is found, false otherwise. 
        :rtype: Boolean
        """
        if force or not os.path.exists(self.mfuser_key_file):
            self._download_mfuser_private_key()

        if os.path.exists(self.mfuser_private_key_file):
                return True 
        else:
            return False 


    def _download_mfuser_private_key(self):
        """
        Downloaded file will be stored locally for future reference.  
        :return: True if key file downloaded, False otherwise. 
        :rtype: Boolean
        """
        try:
            local_file_path = self.mfuser_private_key_file
            remote_file_path =  os.path.join("mfuser")
            file_attributes = self.meas_node.download_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
            #print(file_attributes)
            return True
        except Exception as e:
            print(f"Fail: {e}")
        return False  
    
    
    # TODO
    def _update_bootstrap(self, key, value):
        """
        Updates the given key to the given value in the bootstrap_status.json file on the meas node.
        """
        
        
        #self.download_bootstrap_status()
        bsf_dict = {}
        bsf_dict[key] = value
        
        with open(self.bootstrap_status_file, "w") as bsf:
            json.dump(bsf_dict, bsf)
    
        try:
            local_file_path = self.bootstrap_status_file
            remote_file_path =  os.path.join("bootstrap_status.json")
            #print(local_file_path)
            #print(remote_file_path)
            file_attributes = self.meas_node.upload_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
            #print(file_attributes)
            
            return True
        except Exception as e:
            print("Bootstrap upload has failed.")
            print(f"Fail: {e}")
        return False  
    
        