# Change Log 

This is the changelog file for FABRIC testbed extensions.  All notable
changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## Unreleased

### Changed

- Renamed the package to fabrictestbed-fablib.  Modules are also renamed, such
  that we will have the shorter `import fabrictestbed_fablib.fablib` instead
  of the longer `import fabrictestbed_extensions.fablib.fablib` (PR
  [#172](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/172),
  issue [#164](https://github.com/fabric-testbed/fabrictestbed-extensions/issue/164)). 
  A comatibility shim module is added so that we do not break existing code and
  notebooks in the interim.  The existence of two top-level modules also
  necessitates a switch to setuptools as the build backend.


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
