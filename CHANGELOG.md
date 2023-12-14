# Change Log 

This is the changelog file for FABRIC testbed extensions.  All notable
changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed

- Use defaults for FABRIC CM, orchestrator and bastion hosts (Issue
  [#258](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/258))


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
