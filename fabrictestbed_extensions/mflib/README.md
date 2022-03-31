# MFLIB - Measurement Framework Library 

mflib class creates base methods that will allow jupyter notebook to easily connect to the meas node to run code in a standard way as well as create hooks for managing the meas node.

A common directory structure will help standardize the code.

* A standard linux user called mfuser is created on the meas node 
* The MeasurementFramework repo is cloned into /home/mfuser/MeasurementFramework
* A services directory holds the scripts, files, json and variable files for each service.
 * /home/mfuser/services 
* Each service has their control scripts in a /home/mfuser/services/<service-name> directory. 
  * /home/mfuser/services/<service-name>/create.py
  * /home/mfuser/services/<service-name>/upate.py
  * /home/mfuser/services/<service-name>/start.py
  * /home/mfuser/services/<service-name>/stop.py
  * /home/mfuser/services/<service-name>/remove.py
* Each service has a landing spot for uploaded json and files. 
  * /home/mfuser/services/<service-name>/files
* Each service should consider caching results.
* Each service has a /home/mfuser/services/<service-name>/readme.md file.

fablib is used to upload files and to run the commands on the meas node. Each method described below uses fablib to ensure the the files are successfully uploaded to the meas node. Fablib also ensures that the corresponding python script succesfully runs or reports an error to the user. 

## Currently there are no fablib calls that let us use a non-slice owners key. So we may have to test using the users's key?
Turns out making the mfuser may be problematic since there is no good fablib way to work as another user yet, For now we can still create the mfuser on the slice nodes but just use the regular users account on the meas node.



#Methods

## init
The init method will check/setup the slice. 
* Ensure a meas node exists in the slice topology.
* Ensure meas node has mfuser with keys. Perhaps retrieve mfuser key from slice users account on meas node? 
* Ensure meas node has cloned (updated?) MeasurementFramework repo in mfuser home directory.
* Ensure the services directory has been created and populated with the defaults for each service.
* Ensure that a there is an mfuser account on all slice nodes. 
* Possibly ensure that current ansible host file for slice is on the meas node.
* Write a file to /home/mfuser/bootstrap.json with bootstrap results to prevent rerunning bootstrap code.


## create
The create method will aid in the setup and initialization of a service. 
* Will upload given files to a predefined location.
* Will upload given json to a predefined location. 
* Will run create.py code located in a predefined location. create.py should return a json. 
 * The create.py file can be anything that the service creator wants it to do. It could run a bash script at some location, start ansible scripts, etc..


## update
The update method is basically the same as the create method 
* Will upload given files to a predefined location.
* Will upload given json to a predefined location. 
* Will run update.py code located in a predefined location. update.py should return a json. 
 * The update.py file can be anything that the service creator wants it to do. It could run a bash script at some location, start ansible scripts, etc..

# Start and stop 
Start and stop commmands are similar to the update command except they enforce a standard way to start and stop services and do not upload any files or json.

## start
The start method will start the service running. It generally would not create anything, just start the daemons and anything that is using resources such as CPU or RAM. 
Having the start.py file in a standard location will also make it easy to ensure services are restarted on node reboots. It also allows easy start all or start ([x,y,z]) commands.
* Will run start.py code located in a predefined location. start.py should return a json. 
 * The start.py file can be anything that the service creator wants it to do. It could run a bash script at some location, start ansible scripts, etc..

## stop
The stop method will stop the service from running. It will not remove anything, just stop anything that is using resources such as CPU or RAM... 
Having the stop.py file in a standard location will also make it easy to shut down a monitoring service by means other than the user or mflib calls. This could be used for graceful automatic shutdowns when shutting down or removeing the meas node from a topology. It could also be used for emergency shutdowns. 
* Will run stop.py code located in a predefined location. stop.py should return a json. 
 * The stop.py file can be anything that the service creator wants it to do. It could run a bash script at some location, start ansible scripts, etc..

## remove
The remove method will stop the service and remove all artifacts from the slice's nodes. It may keep the resources created on the meas node such as config files etc?
Having the remove.py file in a standard location will also make it easy to remove the monitoring service by means other than the user or mflib calls. This could be used for graceful automatic shutdowns when shutting down or removeing the meas node from a topology. It could also be used for emergency shutdowns. 
* Will run remove.py code located in a predefined location. remove.py should return a json. 
 * The remove.py file can be anything that the service creator wants it to do. It could run a bash script at some location, start ansible scripts, etc..




# Possible additions
 ## progress
Retrive a json that descibes the progress of the last method called on a service. 
* A stop command that takes several minutes to complete could store the current progress state in a json file that is updated for each stop step. The progress method would then retrive that json for the user.
* A status or info command might need to process a large amount of data. The processing state could be stored in a json file that is updated for each step. The progress method would then retrive that json for the user.
 ## log
 Retrive log files for a service. 
 ## history
 Retrive a history of commands run on a service.
