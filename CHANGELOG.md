# Change Log

This is the changelog file for FABRIC testbed extensions.  All notable
changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added 

- Support new GPU models has been added (PR [#122](https://github.com/fabric-testbed/fabrictestbed-extensions/pull/122)).

### Changed

- Fablib now uses pyproject.toml for specifying packaging metadata instead of setup.py and friends (issue [#74](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/74)).

### Fixed

- Fablib will now fail early when required configuration is missing (issue [#69](https://github.com/fabric-testbed/fabrictestbed-extensions/issues/69)).

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
