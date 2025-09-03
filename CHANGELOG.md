# Change Log 

This is the changelog file for FABRIC testbed extensions.  All notable
changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
- Fix Attestable Switch failing to start and improve its functioning (Issue [#444](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/444))
- Fix Attestable Switch config initialization causing some functions to fail (Issue [#445](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/445))

## 1.9.2
- List Nodes fails to list P4 switches (Issue [#436](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/436))
- pip install not working (Issue [#418](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/418))

## 1.9.1
- `get_interfaces()` and `get_interface()` behavior for `NetworkService` and `Node` (Issue [#434](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/434))

## 1.9.0
- Simplifying FPGA Flash workflow - PCI Rescan (Issue [#421](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/421))
- Support Explicit Route Objects (ERO) with Guaranteed QoS in FABlib (Issue [#422](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/422))
- Store policies, images, PTP availability and other transient bits in a pullable file. (Issue [#425](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/425))
- Validate and update configuration as part of object initialization (Issue [#428](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/428))
- fablib.list_links(output='json') results in an exception (Issue [#427](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/427))
- slice.add_facility_port set a default bandwidth 10G (Issue [#419](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/419))
- Blue Field3 support (Issue [#430](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/430))

## 1.8.2

### Fixed
- Display Slice owner information (Issue [#409](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/409))
- Non cloud facility ports should report local_name just like cloud facility ports (Issue [#402](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/402))
- urllib3 deprecated warning (Issue [#397](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/397))
- Improvements for get_interfaces and get_components (Issue [#378](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/378))
- TypeError: Switch.get_interfaces() got an unexpected keyword argument 'output' (Issue([#405](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/405)))
- Exception: Interface not found using Node.get_interface(name) (Issue[#407](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/407))
- Delete Facility port from a slice (Issue [#411](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/411))
- Disable Config VLAN interfaces for SharedPort (Issue [#413](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/413))
- Modify interface bw does not pass bw to network service (Issue [#415](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/415))
- Support for create_ssh_tunnel_config (Issue [#432](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/432))

### Added
- Add support for BlueField NICs (Issue [#399](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/399))

## 1.8.1 - 01/29/2025

### Added
- Support for interactive execution of commands (Issue [#393](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/393)
- Show username for Switch (Issue [#395](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/395))

## 1.8.0 - 01/07/2025

### Added
- Advance Scheduling Improvements (Issue [#388](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/388))
- Support for P4 switches (Issue [#392](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/392))

### Fixed
- Ensure slice key and bastion key names are not identical (Issue [#389](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/389))

## [1.7.4] - 11/05/2024 

### Added 
- Missing docstrings in network_service module (Issue [#313](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/314))
- Artifact Manager Support (Issue [#358](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/358))
- FabNet user specified subnets (Issue [#361](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/361))
- Print a hint when bastion probe fails (Issue [#363](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/363))
- Missing docstrings in resources module (Issue [#315](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/315))
- Missing docstrings in slice module (Issue [#316](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/316))
- Missing docstrings in component module (Issue [#317](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/317))
- Missing docstrings in fablib module (Issue [#319](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/319))
- Missing docstrings in fablib.config module (Issue [#320](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/320))
- Renew Slice leaves the slivers in ActiveTicketed State (Issue [#364](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/364))
- get_management_os_interface and get_dataplane_os_interfaces doesn't take into account IPv6 addresses. (Issue [#362](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/362))
- Disable post boot config for renew (Issue [#373](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/373))
- slice.renew() should pass **kwargs through to slice.submit() (Issue [#374](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/374))
- node.execute() retry parameter is off-by-one (and/or misnamed) (Issue [#375](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/375))
- FacilityPort.show() errors out (Issue [#346](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/346))
- Add support for FPGA model SN1022 (Issue [#382](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/382))
- Node objects returned from slice.get_node(name) are not the same as the node objects returned from slice.get_nodes() (Issue [#380](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/380))
- Multiple calls to fablib.get_slice(name) in the same interpreter yield different objects (Issue [#379](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/379))
- FablibManager.get_slices doesn't return unsubmitted slices created by new_slice() (Issue [#294](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/294))
- Display Project Name in show_config() (Issue [#384](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/384))
- Add support for Attestable Switch from CREASE project (PR [#386](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/386))


## [1.7.3] - 08/05/2024
### Fixed
- Add kali linux user name and prefix subinterface name with Node name (Issue [#356](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/356))

## [1.7.2] - 07/22/2024
### Fixed
- Post Boot config check to run for current slices (PR [#353](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/353))

## [1.7.1] - 07/19/2024

### Fixed
- Use cached resource information unless fresh information explicitly requested (Issue [#352](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/352))

## [1.7.0] - 07/18/2024

### Fixed
- Error *may* be inaccurate or wrong when I issue an invalid configuration. (Issue [#304](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/304))
- Get Device Name and corresponding deprecated function (Issue[#341](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/341))
- Failures when adding interfaces to a network (Issue[#329](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/329))
- Add Facility Port to allow adding multiple interfaces (Issue [#289](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/289))
- validate_config errors out when config directory does not exist (Issue [#299](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/299))
- create_ssh_config adds extra indentation (Issue [#300](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/300))
- Remove duplicate Node.delete() method (Issue [#321](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/321))

## Added
- Missing docstrings in interface module (Issue [#313](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/313))
- Missing docstrings in facility_port module (Issue [#312](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/312))
- Missing docstrings in node module (Issue [#318](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/318))
- Sub Interface Support (Issue [#350](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/350))
- Advanced reservations (Issue [#345](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/345))
- Port Mirroring with Basic NICs (Issue [#343](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/343))
- P4 support (Issue [#340](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/340))
- ERO Support (Issue [#338](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/338))
- List hosts (Issue [#331](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/331))
- AL2S Support (Issue [#325](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/325))
- Deny infeasible slices (Issue [#326](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/326))
- Add display of switch port name to network service table listing (Issue [#152](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/152))

## [1.6.4] - 2024-03-05

### Fixed
- Can't instantiate FablibManager without config file (Issue [#286](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/286))
- Reduce the time taken for the call node.get_ssh_command() (Issue [#280](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/280))
- Allow access to other user's slices in a project (Issue [#279](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/279))
- Allow user to specify Lease End time for Slice creation (Issue [#51](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/51)]
- Ubuntu images need ifaces brought up (Issue [#123](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/123)
- Add/Remove Network Interfaces for Facility Ports (Issue [#284](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/284))

## [1.6.3] - 2024-01-26

### Fixed

- Ability to disable auto refresh tokens (Issue [#277](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/277))
- Use L2STS when connecting two facility ports via L2 (Issue [#275](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/275))

## [1.6.2] - 2024-01-23

### Fixed

- fablib: Using portal sliver keys (Issue
  [#61](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/61),

- Standardize and validate configuration, support for creating ssh keys (Issue
  [#127](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/127),


## [1.6.0] - 2024-01-03

### Fixed

- Fix an error in `Node.list_networks()` (Issue
  [#239](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/239),
  PR [#241](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/241))
- Honor wait_timeout in slice.submit()
  ([#253](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/253))
- Reconfigure on slice update/modify (Issue
  [#261](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/261))

### Added

- Missing docstrings for `Node.add_fabnet()` (PR
  [#240](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/240))
- Offer a hint when bastion probe fails (Issue
  [#246](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/246),
  PR [#247](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/247))
- Version in pyproject.toml (Issue
  [#248](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/248))
- Separate contribution guidelines (Issue
  [#242](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/242),
  [#243](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/243),
  PR [#251](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/251))
- Module docstrings (PR
  [#256](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/256))

### Changed

- Use defaults for FABRIC CM, orchestrator and bastion hosts (Issue
  [#258](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/258))
- Refactor logging setup (Issue
  [#263](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/263))

## [1.5.5]

### Added

- Display and filter by PTP availability at each site based on ARM
  information (PR [#236](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/236)).
- Missing docstrings for Node module (PR
  [#237](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/237))


### [1.5.4] - 2023-08-21

### Changed

- Some optimizations in `list_sites()`, `show_site()`, `get_random_site()`
  (PR [#230](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/230))
- Fix `slice.wait()` to update slice ensuring slice is in `StableOK` or `StableError` state (Issue [#231](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/231))

### Fixed
- Update default username for `defaul_centos9_stream` image (Issue [#227](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/227))

## [1.5.2] - 2023-08-02

### Fixed

- Address a crash when querying NUMA properties. (Issue
  [#191](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/191),
  PR [#192](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/192))

### Changed

- Update list of OS images (PR
  [#202](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/202))
- List Facility Ports updated to include additional parameters (Issue
  [#210](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/210))
- Fail early when connection with bastion host fails (Issue
  [#151](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/151))
- Overhaul API docs (PR
  [#217](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/217),
  issue [#215](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/215))
- Update/reformat API docstrings (PR
  [#220](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/220))

### Added

- Add/update integration tests (Issues
  [#184](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/184),
  [#186](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/186),
  PR [#187](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/187))
- Make Network Interface Config Idempotant
  (Issue [#205](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/205))
- Methods added to retrieve SSH keys for bastion and sliver (PR
  [#207](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/207))
- Support for PortMirror service (PR
  [#214](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/214))
- Support for CPU Pinning and Numa tuning (Issue [#221](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/221))

### Removed
  
- Remove unused `AbcFabLIB` class (Issue
  [#117](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/117))


## [1.4.4] - 2023-05-21

### Fixed

- Changed some error that were printing to stdout to log instead.

### Added

- Added a get_public_ips call to NetworkService for user to get list of public IPs assigned to their FabNetExt


## [1.4.3] - 2023-04-22

### Fixed

- The interface.get_ip_addr() fuction now returns address strings for devs that were manually configured. 

## [1.4.2] - 2023-04-21

### Added

- Support new GPU models has been added (PR
  [#122](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/122)).
- Support for maintenance mode (PR
  [#137](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/137/),
  issues
  [#120](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/120),
  [#125](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/125))
- Userdata support.
- Automatically assigning IPs, depending on mode.
- Support for post-boot configuration.  Files or directories can be
  uploaded post-boot, and commands can be submitted to be run
  post-boot.
- A way to define layer-2 networks.
- A way to query link and facility port information
- Added function to make IP address of node publicly routable with external networking. `make_ip_publicly_routable`
- Streamlined polling after a submit to reduce load on the control framework
- Added easy, one-line "add_fabnet" functionality simple L3 networks
- ipython 8.12.0 is added as a direct dependency; this is a short-term
  workaround until FABRIC's JupyterHub is updated.

### Changed

- Fablib now uses pyproject.toml for specifying packaging metadata
  instead of setup.py and friends (issue
  [#74](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/74)).
- Make configure_nvme() more generic (PR
  [#126](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/126)).



### Fixed

- Fixed an issue with auto network configuration executing twice
- Fablib will now fail early when required configuration is missing
  (issue
  [#69](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/69)).
- A workaround for Debian/Ubuntu nmcli transition.

## [1.3.4] - 2023-01-19

### Fixed

- FABLIB: Better clean up of SSH connections to bastion proxy.


## [1.3.3] - 2022-12-01


### Added
- FABLIB:  Show and list functionallity for all resource object types.

### Changed

- FABLIB:  Now leaves network manager for management iface but does not manage other ifaces

### Fixed

- FABLIB: node.upload_directory now uses correct temporary file names


## [1.3.2] - 2022-10-25

Older changes are not included in change log.
