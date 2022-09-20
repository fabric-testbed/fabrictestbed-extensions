# MIT License
#
# Copyright (c) 2022 FABRIC Testbed
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


import json
import traceback
import os

from fabrictestbed_extensions.fablib.fablib import fablib
# For getting vars to make tunnel
from fabrictestbed_extensions.fablib.fablib import FablibManager

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from os import chmod

import string
import random
import paramiko

#import logging


class core():

    core_sanity_version = "1.0.21"

    @property
    def slice_name(self):
        return self._slice_name 

    @slice_name.setter
    def slice_name( self, value ):
        # Set the slice name
        self._slice_name = value 

        # Create the local slice directory
        try:
            os.makedirs(self.local_slice_directory)
            os.makedirs(self.log_directory)
            log_file_path = os.path.join(self.log_directory, "mflib.log")
            ## logging.basicConfig(filename=log_file_path, format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level="INFO", force=True)
            # logging.info(f"-----Set slice name {value}.-----")
        except FileExistsError:
            pass 
        
            # TODO add check for exists

    @property
    def local_slice_directory(self):
        return os.path.join(self.local_storage_directory, self.slice_name)

    @property
    def log_directory(self):
        return os.path.join(self.local_slice_directory, "log")
        
    @property 
    def bootstrap_status_file(self):
        return os.path.join(self.local_slice_directory, "bootstrap_status.json")

    @property 
    def common_hosts_file(self):
        return os.path.join(self.local_slice_directory, "hosts.ini")    

    @property 
    def local_mfuser_private_key_filename(self):
        return os.path.join(self.local_slice_directory, "mfuser_private_key")    

    @property 
    def local_mfuser_public_key_filename(self):
        return os.path.join(self.local_slice_directory, "mfuser_pubic_key")    

    @property
    def meas_node(self):
        if self._meas_node:
            return self._meas_node 
        else:
            self._find_meas_node()
            return self._meas_node 
            
    @property
    def meas_node_ip(self):
        if self.meas_node:
            return self._meas_node.get_management_ip() 
        else:
            return ""

    @property
    def slice_username(self):
        if self.meas_node:
            return self._meas_node.get_username() 
        else:
            return ""


    @property
    def tunnel_host(self):
        """
        If a tunnel is used, this value must be set for the localhost, Otherwise it is set to empty string."""
        return self._tunnel_host
        
    @tunnel_host.setter
    def tunnel_host(self, value):
        """ 
        Set to "localhost" if using tunnnel.
        """
        self._tunnel_host = value
        

    @property
    def grafana_tunnel_local_port(self):
        """
        If a tunnel is used, this value must be set for the port"""
        return self._grafana_tunnel_local_port
        
    @grafana_tunnel_local_port.setter
    def grafana_tunnel_local_port(self, value):
        """ 
        Set to port_number if using tunnnel.
        """
        self._grafana_tunnel_local_port = value
        

    @property
    def kibana_tunnel_local_port(self):
        """
        If a tunnel is used, this value must be set for the port"""
        return self._kibana_tunnel_local_port
        
    @kibana_tunnel_local_port.setter
    def kibana_tunnel_local_port(self, value):
        """ 
        Set to port_number if using tunnnel.
        """
        self._kibana_tunnel_local_port = value
                

    # Tunnels are needed to access the meas node via the bastion host
    # In the future these may be combinded into one port with diff nginx paths mappings.
    # alt copy is a selection added to the fabric_rc file for setting a alertnate location for the files 
    #   such as on a laptop. This makes it easy to create a tunnel on a users laptop where they will need access
    #   to the web uis. 

    @property
    def grafana_tunnel(self):
        return self._meas_node_ssh_tunnel(local_port = self.grafana_tunnel_local_port, remote_port="443")

    @property
    def kibana_tunnel(self):
        return self._meas_node_ssh_tunnel(local_port = self.kibana_tunnel_local_port, remote_port="80")

    def _meas_node_ssh_tunnel(self, local_port, remote_port):
        """
        Returns the SSH tunnel command for accessing the meas node via bastion host.
        """

        slice_username = self.slice_username
        meas_node_ip = self.meas_node_ip
        
        # User has setup an ssh config file
        extra_fm = FablibManager()
        errmsg = ""
        ssh_config = ""
        private_key_file = ""
    
        extra_fm_vars = extra_fm.read_fabric_rc(extra_fm.default_fabric_rc)
        if extra_fm_vars:
            if "FABRIC_ALT_COPY_SSH_CONFIG" in extra_fm_vars:
                ssh_config = extra_fm_vars["FABRIC_ALT_COPY_SSH_CONFIG"]
            else:
                errmsg += "FABRIC_ALT_COPY_SSH_CONFIG not found in fabric_rc file. "

            if "FABRIC_ALT_COPY_SLICE_PRIVATE_KEY_FILE" in extra_fm_vars:
                private_key_file = extra_fm_vars["FABRIC_ALT_COPY_SLICE_PRIVATE_KEY_FILE"]
            else:
                errmsg += "FABRIC_ALT_COPY_SLICE_PRIVATE_KEY_FILE not found in fabric_rc file. "
            
        if errmsg:
            return "It appears you have not added alternate ssh config or slice key file locations to the fabric_rc file. " + errmsg
        else:
            #return f'ssh -L 10010:localhost:443 -F {extra_fm_vars["FABRIC_ALT_SSH_CONFIG"]} -i {extra_fm_vars["FABRIC_ALT_SLICE_PRIVATE_KEY_FILE"]} {self.slice_username}@{self.meas_node_ip}'
            tunnel_cmd = f'ssh -L {local_port}:localhost:{remote_port} -F {ssh_config} -i {private_key_file} {slice_username}@{meas_node_ip}'
            return tunnel_cmd 


    # Repo branch made class varible so it can be set before creating object
    mf_repo_branch = "main"
    
  
    def __init__(self, local_storage_directory="/tmp/mflib"):
        """
        Constructor.
        """
        super().__init__()

        # logging.info("Creating mflib object.")
        
        #self.mf_repo_branch = "dev"
        self.tunnel_host = "localhost"
        self.grafana_tunnel_local_port = "10010"
        self.kibana_tunnel_local_port = "10020"


        # The slice_name
        self._slice_name = ""
        # The slice object
        self.slice = None
        # The meas_node object
        self._meas_node = None 

        # The following are normally constant values
        # Name given to the meas node
        self.measurement_node_name = "_meas_node"
        # Services directory on meas node
        self.services_directory = os.path.join("/", "home", "mfuser", "services")
        # Base names for keys
        self.mfuser_private_key_filename = "mfuser_private_key"
        self.mfuser_public_key_filename = "mfuser_public_key"


        try:
            self.local_storage_directory = local_storage_directory
            os.makedirs(self.local_storage_directory)
        except FileExistsError:
            pass


# IPV6 to IPV4 only sites fix
# note: should set bootstrap status file when making these 2 calls, status should be set, restored, not needed.
    def set_DNS_all_nodes(self):
        # Check if we need to
        if(self.meas_node.validIPAddress(self.meas_node.get_management_ip())=="IPv6"):
            for node in self.slice.get_nodes():
                self.set_DNS(node)
            return "set"
        else:
            return "not needed"

    def restore_DNS_all_nodes(self):
        # Check if we need to
        if(self.meas_node.validIPAddress(self.meas_node.get_management_ip())=="IPv6"):
            for node in self.slice.get_nodes():
                self.restore_DNS(node)
            return "restored"
        else:
            return "not needed"

    def set_DNS(self,node):
        if(node.validIPAddress(node.get_management_ip())=="IPv6"):
            node.execute("""
            printf 'nameserver 2a00:1098:2c::1\nnameserver 2a01:4f8:c2c:123f::1\nnameserver 2a01:4f9:c010:3f02::1' > resolv.new;
            sudo mv /etc/resolv.conf /etc/resolv.old;
            sudo mv resolv.new /etc/resolv.conf;
            """)
            #Needed for fedora
            node.execute("""
                sudo resolvectl dns eth0 2a00:1098:2c::1;
                sudo resolvectl dns eth0 2a01:4f8:c2c:123f::1;
                sudo
                resolvectl dns eth0 2a01:4f9:c010:3f02::1;
            """)
            # TODO add error checking


    def restore_DNS(self,node):
        if(node.validIPAddress(node.get_management_ip())=="IPv6"):
            node.execute("""
                sudo mv /etc/resolv.old /etc/resolv.conf;
            """)

            node.execute("""
                resolvectl revert eth0;
            """)








          
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
        return self._run_on_meas_node(service, "create", data, files)

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
        return self._run_on_meas_node(service, "update", data, files)

    def info(self, service, data=None):
        """
        Gets inormation from an existing service. Strictly gets information, does not change how the service is running.
        :param service: The name of the service.
        :type service: String
        :param data: Data to be passed to a JSON file place in the service's meas node directory.
        :type data: JSON serializable object.
        """
        return self._run_on_meas_node(service, "info", data)

    def start(self, services=[]):
        """
        Restarts a stopped service using existing configs on meas node.
        """
        for service in services:
            return self._run_on_meas_node(service, "start")

    def stop(self, services=[]):
        """
        Stops a service, does not remove the service, just stops it from using resources.
        """
        for service in services:
            return self._run_on_meas_node(service, "stop")

    def status(self, services=[]):
        """
        Deprecated?, use info instead?
        Returns predefined status info. Does not change the running of the service.
        """ 
        for service in services:
            return self._run_on_meas_node(service, "status")

    def remove(self, services=[]):
        """
        Stops a service running and removes anything setup on the experiment's nodes. Service will then need to be re-created using the create command before service can be started again.
        """
        for service in services:
            return self._run_on_meas_node(service, "remove")



# Utility Methods

    def _upload_mfuser_keys(self, private_filename=None, public_filename=None):
        """
        Uploads the mfuser keys to the default user for easy access later.
        """
        if  private_filename is None:
            private_filename=self.local_mfuser_private_key_filename
        if  public_filename is None:
            public_filename=self.local_mfuser_public_key_filename

        try:
            local_file_path = private_filename
            remote_file_path = self.mfuser_private_key_filename
            stdout, stderr = self.meas_node.upload_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
        except TypeError:
            pass 
            # TODO set file permissions on remote
            # This error is happening due to the file permmissions not being correctly set on the remote?
        except Exception as e:
            print(f"Failed Private Key Upload: {e}")

        try:
            local_file_path = public_filename
            remote_file_path = self.mfuser_public_key_filename
            stdout, stderr = self.meas_node.upload_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
        except TypeError:
            pass 
            # TODO set file permissions on remote
            # This error is happening due to the file permmissions not being correctly set on the remote?   
            # Errors are:
            # Failed Private Key Upload: cannot unpack non-iterable SFTPAttributes object
            # Failed Public Key Upload: cannot unpack non-iterable SFTPAttributes object     
        except Exception as e:
            print(f"Failed Public Key Upload: {e}")


        # Set the permissions correctly on the remote machine.
        cmd = f"chmod 644 {self.mfuser_public_key_filename}"
        self.meas_node.execute(cmd)
        cmd = f"chmod 600 {self.mfuser_private_key_filename}"
        self.meas_node.execute(cmd)
        
    def _copy_mfuser_keys_to_mfuser_on_meas_node(self):
        """
        Copies mfuser keys from default location to mfuser .ssh folder and sets ownership & permissions.
        """
        try:
            cmd = f"sudo cp {self.mfuser_public_key_filename} /home/mfuser/.ssh/{self.mfuser_public_key_filename}; sudo chown mfuser:mfuser /home/mfuser/.ssh/{self.mfuser_public_key_filename}; sudo chmod 644 /home/mfuser/.ssh/{self.mfuser_public_key_filename}"
            stdout, stderr = self.meas_node.execute(cmd)
        
            print(stdout)
            print(stderr)

            cmd = f"sudo cp {self.mfuser_private_key_filename} /home/mfuser/.ssh/{self.mfuser_private_key_filename}; sudo chown mfuser:mfuser /home/mfuser/.ssh/{self.mfuser_private_key_filename}; sudo chmod 600 /home/mfuser/.ssh/{self.mfuser_private_key_filename}"
            stdout, stderr = self.meas_node.execute(cmd)

            print(stdout)
            print(stderr)
        except Exception as e:
            print(f"Failed mfuser key user key copy: {e}")
            return False 
        return True


    def _download_mfuser_keys(self, private_filename=None, public_filename=None):
        """
        Downloads the mfuser keys.
        """
        if  private_filename is None:
            private_filename=self.local_mfuser_private_key_filename
        if  public_filename is None:
            public_filename=self.local_mfuser_public_key_filename
        

        try:
            local_file_path = private_filename
            remote_file_path = self.mfuser_private_key_filename
            stdout, stderr = self.meas_node.download_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):

            local_file_path = public_filename
            remote_file_path = self.mfuser_public_key_filename
            stdout, stderr = self.meas_node.download_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
            
        except Exception as e:
            print(f"Download mfuser Keys Failed: {e}")


    def _find_meas_node(self):
        """
        Finds the node named "meas" in the slice and sets the value for class's meas_node
        :return: If node found, sets self.meas_node and returns True. If node not found, clears self.meas_node and returns False.
        :rtype: Boolean
        """
        try:
            for node in self.slice.get_nodes():
                if node.get_name() == self.measurement_node_name:
                    self._meas_node = node 
                    return True 
        except Exception as e:
            print(f"Find Measure Node Failed: {e}")
        self._meas_node = None
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
        else:
            # Ensure old stale data is remove on meas node
            self._upload_service_data(service, {})
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
        
            
        letters = string.ascii_letters
        try:
            # Create temp file for serialized json data
            randdataname = "mf_service_data_" + "".join(random.choice(letters) for i in range(10))
            local_file_path = os.path.join("/tmp", randdataname)
            with open(local_file_path, 'w') as datafile:
                #print("dumping data")
                json.dump(data, datafile)
            
            # Create remote filenames
            final_remote_file_path = os.path.join(self.services_directory, service, "data", "data.json")
            remote_tmp_file_path = os.path.join("/tmp", randdataname)
    
            # upload file
            fa = self.meas_node.upload_file(local_file_path, remote_tmp_file_path)
            
            # mv file to final location
            cmd = f"sudo mv {remote_tmp_file_path} {final_remote_file_path};  sudo chown mfuser:mfuser {final_remote_file_path}"
            
            self.meas_node.execute(cmd)
            
            # Remove local temp file.
            os.remove(local_file_path)
            
        except Exception as e:
            print(f"Service Data Upload Failed: {e}")  
            return False
        return True


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
        letters = string.ascii_letters

        # TODO could add option to upload a directory of files using fablib.upload_directory
        try:
            for file in files:
                # Set src/dst filenames
                # file is local path
                local_file_path = file 
                filename = os.path.basename(file)
                final_remote_file_path = os.path.join(self.services_directory, service, "files", filename)

                randfilename = "mf_file_" + "".join(random.choice(letters) for i in range(10))
                remote_tmp_file_path = os.path.join("/tmp", randfilename)
                
                # upload file
                fa = self.meas_node.upload_file(local_file_path, remote_tmp_file_path) # retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key")
                cmd = f"sudo mv {remote_tmp_file_path} {final_remote_file_path};  sudo chown mfuser:mfuser {final_remote_file_path}; sudo rm {remote_tmp_file_path}"
 
                self.meas_node.execute(cmd)

        except Exception as e:
            print(f"Service File Upload Failed: {e}")
            return False
        return True


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
            full_command = f"sudo -u mfuser python3 {self.services_directory}/{service}/{command}.py"
            stdout, stderr = self.meas_node.execute(full_command) #retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key"
        except Exception as e:
            print(f"Service Commnad Run Failed: {e}")
#         print(type(stdout))
#         print(stdout)
#         print(stderr)
        try:
            # Convert the json string to a dict
            jsonstr = stdout
            # remove non json string
            jsonstr = jsonstr[ jsonstr.find('{'):jsonstr.rfind('}')+1]
            # Need to "undo" what the exceute command did
            jsonstr = jsonstr.replace('\n','\\n')
            #print(jsonstr)
            ret_data = json.loads(jsonstr)
            return ret_data
            # TODO add stderr to return value?
        except Exception as e:
            print("Unable to convert returned comand json.")
            print("STDOUT: ")
            print(stdout)
            print("STDERR: ")
            print(stderr)
            print(f"Fail: {e}")
        return {} #(stdout, stderr)


    def _download_service_file(self, service, filename, local_file_path=""):
        """
        Downloads service files from the meas node and places them in the local storage directory.
        :param service: Service name
        :type service: String
        :param filename: The filename to download from the meas node.
        :param local_file_path: Optional filename for local saved file. If not given, file will be in default slice directory.# Fri Sep 09 2022 14:30
        :type local_file_path: String
        """

        if not local_file_path:
            local_file_path = os.path.join(self.local_slice_directory, service, filename)
            # ensure local directory exists
            local_dir_path = os.path.dirname(local_file_path) 
            if not os.path.exists(local_dir_path):
                os.makedirs(local_dir_path)

        # 
        #  Download a file from a service directory
        # Probably most useful for grabbing output from a command run.
        # TODO figure out how to name/where to put file locally
        try:
            #local_file_path = os.path.join(self.local_slice_directory, service, filename)
            remote_file_path = os.path.join(self.services_directory, service, filename)
            file_attributes = self.meas_node.download_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
            return {"success":True, "filename":local_file_path}
        except Exception as e:
            print(f"Download service file Fail: {e}")
            return {"success":False}
        
        
    def _clone_mf_repo(self):
        """
        Clone the repo to the mfuser on the meas node.|
        """
        cmd = f"sudo -u mfuser git clone -b {self.mf_repo_branch} https://github.com/fabric-testbed/MeasurementFramework.git /home/mfuser/mf_git"
        stdout, stderr = self.meas_node.execute(cmd)
        # logging.info(f"Cloned {self.mf_repo_branch} to measure node.")
        # logging.info(stdout)
        # logging.info(stderr)
        
    def _run_bootstrap_script(self):
        """
        Run the initial bootstrap script in the meas node mf repo.
        """
        cmd = f'sudo -u mfuser /home/mfuser/mf_git/instrumentize/experiment_bootstrap/bootstrap.sh'
        stdout, stderr = self.meas_node.execute(cmd)
        
        # logging.info(stdout)
        # logging.info(stderr)
        print("Bootstrap script done")

    def _run_bootstrap_ansible(self):
        """
        Run the initial bootstrap ansible scripts in the meas node mf repo.
        """
        cmd = f'sudo -u mfuser python3 /home/mfuser/mf_git/instrumentize/experiment_bootstrap/bootstrap_playbooks.py'
        stdout, stderr = self.meas_node.execute(cmd)
        # logging.info(stdout)
        # logging.info(stderr)


        print("Bootstrap ansible scripts done")
        

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
                #print("Bootstrap file was not downloaded. Bootstrap most likely has not been done.")
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
        except FileNotFoundError:
            pass 
            # Most likely the file does not exist because it has not yet been created. So we will ignore this exception.
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
        if force or not os.path.exists(self.local_mfuser_private_key_filename):
            self._download_mfuser_private_key()

        if os.path.exists(self.local_mfuser_private_key_filename):
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
            local_file_path = self.local_mfuser_private_key_filename
            remote_file_path =  self.mfuser_private_key_filename
            file_attributes = self.meas_node.download_file(local_file_path, remote_file_path) #, retry=3, retry_interval=10):
            #print(file_attributes)
            return True
        except Exception as e:
            print(f"Download mfuser private key Failed: {e}")
        return False  
    
    
    def _update_bootstrap(self, key, value):
        """
        Updates the given key to the given value in the bootstrap_status.json file on the meas node.
        """
        bsf_dict = self.get_bootstrap_status()
        #self.download_bootstrap_status()
        #bsf_dict = {}
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
    
       
    
    def download_log_file(self, service, method):
        """
        Download the log file for the given service and method.
        Downloaded file will be stored locally for future reference. 
        :param service: The name of the service.
        :type service: String 
        :param method: The method name such as create, update, info, start, stop, remove.
        :type method: String
        :return: Writes file to local storage and returns text of the log file.
        :rtype: String
        """
        try:
            local_file_path = os.path.join( self.local_slice_directory, f"{method}.log")
            remote_file_path =  os.path.join("/","home","mfuser","services", service, "log", f"{method}.log")
            #print(local_file_path)
            #print(remote_file_path)
            file_attributes = self.meas_node.download_file(local_file_path, remote_file_path, retry=1) #, retry=3, retry_interval=10): # note retry is really tries
            #print(file_attributes)
            
            with open(local_file_path) as f:
                log_text = f.read()
                return local_file_path, log_text

        except Exception as e:
            print("Service log download has failed.")
            print(f"Downloading service log file has Failed. It may not exist: {e}")
            return "",""

    

class mflib(core):

    mflib_sanity_version = "1.0.21"
          
    # This is a temporary method needed untill modify slice ability is avaialble. 
    @staticmethod 
    def addMeasNode(slice, cores=None, ram=None, disk=None):
        """
        Adds measurement components to an unsubmitted slice object
        :param slice: Unsubmitted Slice Object
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

        if not cores: 
            cores = meas.default_cores 

        if not ram: 
            ram = meas.default_ram 

        if not disk: 
            disk = 32 #meas.default_disk

        meas.set_capacities(cores=cores, ram=ram, disk=32)
        meas.set_image("default_ubuntu_20")
        interfaces.append(meas.add_component(model='NIC_Basic', name="Meas_Nic").get_interfaces()[0])
        meas_net = slice.add_l2network(name="_meas_net", interfaces=interfaces)
    


    def __init__(self, slice_name="",local_storage_directory="/tmp/mflib"):
        """
        Constructor.
        """
        super().__init__(local_storage_directory=local_storage_directory)

        if slice_name:
            self.init(slice_name)


    def init(self,slice_name):
        """
        Sets up the mflib object to ensure slice can be monitored.
        :param slice_name: The name of the slice.
        :rtype: String
        """
        print(f'Inititializing slice "{slice_name}" for MeasurementFramework.')
        
        ########################
        # Get slice 
        ########################
        self.slice_name = slice_name


        # logging.info(f'Inititializing slice "{slice_name}" for MeasurementFramework.')
        self.slice = fablib.get_slice(name=slice_name)
        

        ########################
        # Check for prequisites
        #######################
        
        # Does Measurement Node exist in topology?
        if not self.meas_node:
            print("Failed to find meas node. Need to addMeasureNode first.")
            # logging.warning("Failed to find meas node. Need to addMeasureNode first.")
            return False
        
        print(f"Found meas node as {self.meas_node.get_name()} at {self.meas_node.get_management_ip()}")
        # logging.info(f"Found meas node as {self.meas_node.get_name()} at {self.meas_node.get_management_ip()}")
        
        bss = self.get_bootstrap_status()
        if bss:
            print("Bootstrap status is")
            print(bss)
            # logging.info("Bootstrap status is")
            # logging.info(bss)
        else:
            print("Bootstrap status not found. Will now start bootstrap process...")
            # logging.info("Bootstrap status not found. Will now start bootstrap process...")
            
        
        if ("status" in bss and bss["status"] == "ready"):
            # Slice already instrumentized and ready to go.
            self.get_mfuser_private_key() 
            print("Bootstrap status indicates Slice Measurement Framework is ready.")
            # logging.info("Bootstrap status indicates Slice Measurement Framework is ready.")
            return
        else: 
            
            ###############################
            # Need to do some bootstrapping
            ###############################
 

                
            ######################   
            # Create MFUser keys
            #####################
            if "mfuser_keys" in bss and bss["mfuser_keys"] =="ok":
                print( "mfuser_keys already generated" )
                # logging.info( "mfuser_keys already generated" )
            else:
            #if True:
                print ("Generating MFUser Keys...")
                # logging.info( "Generating MFUser Keys..." )
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
                public_key_file = open(self.local_mfuser_public_key_filename, 'w');
                #public_key_file = open("/tmp/mflib/mfuser.pub", 'w');
                public_key_file.write(public_key_str);
                public_key_file.write('\n');
                public_key_file.close()
                #chmod("/tmp/mflib/mfuser.pub", 0o644);
                chmod(self.local_mfuser_public_key_filename, 0o644);


                # Save private key & change mode
                private_key_file = open(self.local_mfuser_private_key_filename, 'w');
                #private_key_file = open("/tmp/mflib/mfuser", 'w');
                private_key_file.write(private_key_str);
                private_key_file.close()
                #chmod("/tmp/mflib/mfuser", 0o600);
                chmod(self.local_mfuser_private_key_filename, 0o600);

                # Upload mfuser keys to default user dir for future retrieval
                self._upload_mfuser_keys()

                self._update_bootstrap("mfuser_keys", "ok")
                print("MFUser keys Done.")
                # logging.info("MFUser keys Done.")
            
            
                
            ###############################
            # Add mfusers
            ##############################
            if "mfuser_accounts" in bss and bss["mfuser_accounts"] =="ok":
                print("mfuser accounts are already setup.")
                # logging.info("mfuser already setup.")
            else:
            #if True:  
                #Install mflib user/environment
                # logging.info("Installing mfusers...")
                print("Installing mfuser accounts...")
                mfusers_install_success = True
   
                #Add user
                threads = []
                for node in self.slice.get_nodes():
                    try:
                        threads.append( node.execute_thread("sudo useradd -G root -m mfuser") )
                    
                    except Exception as e:
                        print(f"Failed to add user: {e}")
                        # logging.error(f"Failed to add user: {e}")
                        mfusers_install_success = False
                # logging.info("Adding mfuser results:")
                for thread in threads:
                    stdout, stderr = thread.result()
                    # logging.info(stdout)
                    # logging.error(stderr)

                        
                #Setup ssh directory
                threads = []
                for node in self.slice.get_nodes():
                    try:
                        threads.append( node.execute_thread("sudo mkdir /home/mfuser/.ssh; sudo chmod 700 /home/mfuser/.ssh; sudo chown -R mfuser:mfuser /home/mfuser/.ssh"))
                        
                    except Exception as e:
                        print(f"Fail to setup ssh directory: {e}")
                        # logging.error(f"Fail to setup ssh directory: {e}")
                        mfusers_install_success = False
                # logging.info("Adding SSH dir results:")
                for thread in threads:
                    stdout, stderr = thread.result()
                    # logging.info(stdout)
                    # logging.error(stderr)

                #Add mfuser to sudoers
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append( node.execute_thread("echo 'mfuser ALL=(ALL:ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers.d/90-cloud-init-users"))
                        
                    except Exception as e:
                        print(f"Fail to add to sudoers: {e}")
                        # logging.error(f"Fail to add to sudoers: {e}")
                        mfusers_install_success = False
                # logging.info("Add to sudoers results:")
                for thread in threads:
                    stdout, stderr = thread.result()
                    # logging.info(stdout)
                    # logging.error(stderr)
 

                #Upload keys
                # Ansible.pub is nolonger a good name here
                for node in self.slice.get_nodes():
                    try:
                        #node.upload_file("/tmp/mflib/mfuser.pub","ansible.pub")
                        threads.append( node.upload_file(self.local_mfuser_public_key_filename ,"ansible.pub"))
                        
                    except Exception as e:
                        print(f"Failed to upload keys: {e}")
                        # logging.error(f"Failed to upload keys: {e}")
                        mfusers_install_success = False
                
                #Edit commands
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append( node.execute_thread("sudo mv ansible.pub /home/mfuser/.ssh/ansible.pub; sudo chown mfuser:mfuser /home/mfuser/.ssh/ansible.pub;"))
                        
                        #node. execute_thread("sudo mv ansible.pub /home/mfuser/.ssh/ansible.pub; sudo chown mfuser:mfuser /home/mfuser/.ssh/ansible.pub;")
                    except Exception as e:
                        print(f"Fail to set key permissions: {e}")
                        # logging.error(f"Fail to set key permissions: {e}")
                        mfusers_install_success = False
                # logging.info("Moved keys on node results:")
                for thread in threads:
                    stdout, stderr = thread.result()

                    # logging.info(stdout)
                    # logging.error(stderr)

                #Raise Key
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append( node.execute_thread("sudo cat /home/mfuser/.ssh/ansible.pub | sudo tee -a /home/mfuser/.ssh/authorized_keys;"))
                        
                    except Exception as e:
                        print(f"Failed to create authorized_keys: {e}")
                        # logging.error(f"Failed to create authorized_keys: {e}")
                        mfusers_install_success = False
                # logging.info("Set key permission results:")
                for thread in threads:
                    stdout, stderr = thread.result()
                    # logging.info(stdout)
                    # logging.error(stderr)
 

                #Authorize key
                threads=[]
                for node in self.slice.get_nodes():
                    try:
                        threads.append( node.execute_thread("sudo chmod 644 /home/mfuser/.ssh/authorized_keys; sudo chown mfuser:mfuser /home/mfuser/.ssh/authorized_keys"))
                        
                    except Exception as e:
                        print(f"Failed to set authorized_keys permissions: {e}")
                        # logging.error(f"Failed to set authorized_keys permissions: {e}")
                        mfusers_install_success = False
                # logging.info("Set authorized keys results:")
                for thread in threads:
                    stdout, stderr = thread.result()
                    # logging.info(stdout)
                    # logging.error(stderr)

                if not self._copy_mfuser_keys_to_mfuser_on_meas_node():
                    mfusers_install_success = False


                if mfusers_install_success:
                    self._update_bootstrap("mfusers", "ok")
                    print("mfuser installations Done.")
                    # logging.info("Mfuser installs done.")
                else:
                    print("mfuser installations Failed")
                    # logging.info("Mfuser installs Failed.")
                    return 
            


            #######################
            # Set ipv6 to ipv4 DNS 
            #######################
            if "ipv6_4_nat" in bss and (bss["ipv6_4_nat"] == "set" or bss["ipv6_4_nat"] == "not_needed"):
                print("ipv6 to 4 DNS nat already set or is not needed.")
            else:
            #if True:
                nat_set_results = self.set_DNS_all_nodes()
                self._update_bootstrap("ipv6_4_nat", nat_set_results)


            #######################
            # Clone mf repo 
            #######################
            if "repo_cloned" in bss and bss["repo_cloned"] =="ok":
                print("repo already cloned.")
            else:
            #if True:
                self._clone_mf_repo()
                self._update_bootstrap("repo_cloned", "ok")
                
                
                
            #######################################
            # Create measurement network interfaces  
            # & Get hosts info for hosts.ini
            ######################################
            if "meas_network" in bss and bss["meas_network"] =="ok":
                print("measurement network already setup.")
            else:
            #if True:
                self._make_hosts_ini_file(set_ip=True)
                self._update_bootstrap("meas_network", "ok")
                
                
            
            #######################
            # Run Bootstrap script
            ######################
            if "bootstrap_script" in bss and bss["bootstrap_script"] =="ok":
                print("Bootstrap script aleady run on measurment node.")
            else:
            #if True:
                print("Bootstrapping measurement node via bash...")
                self._run_bootstrap_script()
                self._update_bootstrap("bootstrap_script", "ok")


            if "bootstrap_ansible" in bss and bss["bootstrap_ansible"] =="ok":
                print("Bootstrap ansible script already run on measurement node.")
            else:
            #if True:
                print("Bootstrapping measurement node via ansible...")
                self._run_bootstrap_ansible()
            

            self._update_bootstrap("status", "ready")
            print("Inititialization Done.")




# intend this to be overidden
    def instrumentize(self):
        # logging.info(f"Instrumentizing {self.slice_name}")
        # logging.info("Setting up Prometheus.")
        print("Setting up Prometheus...")
        prom_data = self.create("prometheus")
        print(prom_data)
        # logging.info("Setting up ELK.")
        print("Setting up ELK...")
        elk_data = self.create("elk")
        print(elk_data)

        # Install the default grafana dashboards.
        # logging.info("Setting up grafana_manager & dashboards.")
        grafana_manager_data = self.create("grafana_manager")
        print("Instrumentize Done.")

        all_data = {}
        all_data["elk"] = elk_data
        all_data["prometheues"] = prom_data 
        all_data["grafana_manager"] = grafana_manager_data
        
        return all_data



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
                    #hosts.append("{0} ansible_host={1} hostname={1} ansible_ssh_user={2} node_exporter_listen_ip={1} node_exporter_username={3} node_exporter_password={3} snmp_community_string={4} grafana_admin_password={3} fabric_prometheus_ht_user={3} fabric_prometheus_ht_password={3}".format(node.get_name(), ip ,"mfuser","fabric","not-in-use"))
                    hosts.append("{0} ansible_host={1} hostname={1} ansible_ssh_user={2} node_exporter_listen_ip={1}".format(node.get_name(), ip ,"mfuser"))
                    num+=1


        # print("Creating Ansible Hosts File\n")
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

        local_prom_hosts_filename = os.path.join(self.local_slice_directory, "promhosts.ini")
        local_elk_hosts_filename = os.path.join(self.local_slice_directory, "elkhosts.ini")

        with open(local_prom_hosts_filename, 'w') as f:
            f.write(hosts_txt)
        with open(local_elk_hosts_filename, 'w') as f:
            f.write(e_hosts_txt)

        # Upload the files to the meas node and move to correct locations

        # Upload Prom hosts
        self.meas_node.upload_file(local_prom_hosts_filename,"promhosts.ini")

        # create a common version of hosts.ini for all to access
        stdout, stderr = self.meas_node.execute("sudo mkdir -p /home/mfuser/services/common")
        stdout, stderr = self.meas_node.execute("sudo chown mfuser:mfuser /home/mfuser/services")
        stdout, stderr = self.meas_node.execute("sudo chown mfuser:mfuser /home/mfuser/services/common")
        stdout, stderr = self.meas_node.execute("sudo cp promhosts.ini /home/mfuser/services/common/hosts.ini")
        stdout, stderr = self.meas_node.execute("sudo chown mfuser:mfuser /home/mfuser/services/common/hosts.ini")
        
        # create the promhosts.ini file
        stdout, stderr = self.meas_node.execute("sudo mv promhosts.ini /home/mfuser/mf_git/instrumentize/ansible/fabric_experiment_instramentize/promhosts.ini")
        stdout, stderr = self.meas_node.execute("sudo chown mfuser:mfuser /home/mfuser/mf_git/instrumentize/ansible/fabric_experiment_instramentize/promhosts.ini")
        
        # Upload the elkhosts.ini file.
        self.meas_node.upload_file(local_elk_hosts_filename,"elkhosts.ini")

        # create the elk.ini file
        stdout, stderr = self.meas_node.execute("sudo mv elkhosts.ini /home/mfuser/mf_git/elkhosts.ini")
        stdout, stderr = self.meas_node.execute("sudo chown mfuser:mfuser /home/mfuser/mf_git/elkhosts.ini")
        
               
 

    def download_common_hosts(self):
        """
        Downloads hosts.ini file and returns file text.
        Downloaded hosts.ini file will be stored locally for future reference.  
        :param service: The name of the service.
        :type service: String 
        :param method: The method name such as create, update, info, start, stop, remove.
        :type method: String
        :return: Writes file to local storage and returns text of the log file.
        :rtype: String
        """
        try:
            local_file_path = self.common_hosts_file
            remote_file_path =  os.path.join("/home/mfuser/services/common/hosts.ini")
            #print(local_file_path)
            #print(remote_file_path)
            file_attributes = self.meas_node.download_file(local_file_path, remote_file_path, retry=1) #, retry=3, retry_interval=10): # note retry is really tries
            #print(file_attributes)
            
            with open(local_file_path) as f:
                hosts_text = f.read()
                return local_file_path, hosts_text

        except Exception as e:
            print("Common hosts.ini download has failed.")
            print(f"downloading common hosts file Failed: {e}")
            return "",""
        
