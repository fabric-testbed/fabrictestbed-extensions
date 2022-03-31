
import os 
import fablib 
import json 



class mflib():
    
    # Need the slice name to connect to slice
    slicename = ""
    # Need private key to access the mfuser on the meas node. It is stored on the slice users account on the meas node.
    mfuser_private_key = None
    # The slice's meas node 
    meas_node = None
    # Place to put downloaded files?
    local_storage_directory = ""  
    # Keep a copy of the bootstrap status
    bootstrap_status_file = os.join(local_storage_directory, "bootstrap_status.json")

    # Services directory on meas node
    services_directory = os.path.join("home", "myfuser", "services")

    # Many methods use the followig parameter set
    # service - unique service name
    # command - command to run in services directory on meas node
    # data - JSON serializable object
    # files - list of files to upload


    def init(slicename):
        """
        Sets up the mflib object to ensure slice can be monitored.
        :param slicename: The name of the slice.
        :rtype: String
        """
        # Ensure the slice is setup with a meas node and mfuser.
        # Ensure the MeasusrementFramework repo has been cloned on the meas node.
        # Ensure mfuser accounts are created on all nodes
        self.slicename = slicename
        self.find_meas_node()
        self.get_mfuser_private_key() 
        self.get_bootstrap_status()

    

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
        self._run_on_meas_node(self, service, "create", data, files)

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
        self._run_on_meas_node(self, service, "update", data, files)


    def start(self, services=[]):
        for service in services:
            self._run_on_meas_node(self, service, "start")

    def stop(self, services=[]):
        for service in services:
            self._run_on_meas_node(self, service, "stop")

    def status(self, services=[])
        for service in services:
            self._run_on_meas_node(self, service, "status")

    def remove(self, services=[])
        for service in services:
            self._run_on_meas_node(self, service, "remove")



# Utility Methods
     
    def get_mfuser_private_key(self):
        # scp key from slice users directory

        self.mfuser_private_key = "downloaded key location?"
        pass    

    def find_meas_node(self):
        """
        Finds the node named "meas" in the slice and sets the value for class's meas_node
        :return: If node found, sets self.meas_node and returns True. If node not found, clears self.meas_node and returns False.
        :rtype: Boolean
        """
        try:
            slice = fablib.get_slice(slicename)
            for node in slice.get_nodes():
                if node.name == "meas":
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
        return self._run_service_command_on_meas_node( service, command )

        
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
            remote_file_path = os.join(self.services_directory, service, "data.json")
            with open(local_file_path) as datafile:
                json.dump(data, datafile)
            stdout, stderr = node.upload_file(self, local_file_path, remote_file_path) # retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key")
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
                remote_file_path = os.path.join(self.services_dir, service, filename)
                # upload file
                stdout, stderr = node.upload_file(self, local_file_path, remote_file_path) # retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key")
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
            full_command = f"python {self.services_dir}/{service}/{command}.py"
            stdout, stderr = node.execute(full_command) #retry=3, retry_interval=10, username="mfuser", private_key="mfuser_private_key"
        except Exception as e:
            print(f"Fail: {e}")
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
            remote_file_path = os.path.join(self.services_dir, service, filename"
            stdout, stderr = download_file(self, local_file_path, remote_file_path) #, retry=3, retry_interval=10):
        except Exception as e:
            print(f"Fail: {e}")
        

    def get_bootstrap_status(self, force=True):
        """
        Returns the bootstrap status for the slice. Default setting of force will always download the most recent file from the meas node.
        :param force: If downloaded file already exists locally, it will not be downloaded unless force is True. The downloaded file will be stored locally for future reference. 
        :return: True if slice is ready, false otherwise. 
        :rtype: Boolean # or maybe just the entire json?
        """
        if force or not os.path.exists(self.bootstrap_status_file):
            self._download_bootstrap_status()

        if os.path.exists(self.bootstrap_status_file):
           #?? parse the file to see what the status is
            boostrap_dict = json.load(local_file_path)
            if boostrap_dict["status"] == "ready":
                return True 
        else:
            return False 


    def _download_bootstrap_status(self):
        """
        Downloaded file will be stored locally for future reference.  
        :return: True if bootstrap file downloaded, False otherwise. 
        :rtype: Boolean # or maybe just the entire json?
        """
        try:
            local_file_path = self.bootstrap_status_file
            remote_file_path =  os.path.join(self.services_dir, "bootstrap_status.json")
            stdout, stderr = download_file(self, local_file_path, remote_file_path) #, retry=3, retry_interval=10):
            return True
        except Exception as e:
            print(f"Fail: {e}")
        return False     
    