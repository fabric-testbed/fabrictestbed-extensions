#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
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
# Author: Komal Thareja (kthare10@renci.org)
import json
import logging
import os
import re
import time
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Union

import requests
import yaml
from atomicwrites import atomic_write

from fabrictestbed_extensions import __version__ as fablib_version
from fabrictestbed_extensions.fablib.constants import Constants
from fabrictestbed_extensions.utils.utils import Utils


class ConfigException(Exception):
    """
    An exception class to represent configuration errors.
    """

    pass


class Config:
    """
    A class that represents fablib configuration.
    """

    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # Mapping of the required parameters and the corresponding Environment Variable name
    REQUIRED_ATTRS = {
        Constants.ORCHESTRATOR_HOST: {
            Constants.ENV_VAR: Constants.FABRIC_ORCHESTRATOR_HOST,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_ORCHESTRATOR_HOST,
        },
        Constants.CREDMGR_HOST: {
            Constants.ENV_VAR: Constants.FABRIC_CREDMGR_HOST,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_CREDMGR_HOST,
        },
        Constants.CORE_API_HOST: {
            Constants.ENV_VAR: Constants.FABRIC_CORE_API_HOST,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_CORE_API_HOST,
        },
        Constants.AM_HOST: {
            Constants.ENV_VAR: Constants.FABRIC_AM_HOST,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_AM_HOST,
        },
        Constants.CEPH_MGR_HOST: {
            Constants.ENV_VAR: Constants.FABRIC_CEPH_MGR_HOST,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_CEPH_MGR_HOST,
        },
        Constants.TOKEN_LOCATION: {
            Constants.ENV_VAR: Constants.FABRIC_TOKEN_LOCATION,
            Constants.DEFAULT: Constants.DEFAULT_TOKEN_LOCATION,
        },
        Constants.PROJECT_ID: {
            Constants.ENV_VAR: Constants.FABRIC_PROJECT_ID,
        },
        Constants.BASTION_HOST: {
            Constants.ENV_VAR: Constants.FABRIC_BASTION_HOST,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_BASTION_HOST,
        },
        Constants.BASTION_USERNAME: {
            Constants.ENV_VAR: Constants.FABRIC_BASTION_USERNAME,
        },
        Constants.BASTION_KEY_LOCATION: {
            Constants.ENV_VAR: Constants.FABRIC_BASTION_KEY_LOCATION,
            Constants.DEFAULT: Constants.DEFAULT_BASTION_KEY_LOCATION,
        },
        Constants.FABLIB_VERSION: {Constants.DEFAULT: fablib_version},
        Constants.SLICE_PUBLIC_KEY_FILE: {
            Constants.ENV_VAR: Constants.FABRIC_SLICE_PUBLIC_KEY_FILE,
            Constants.DEFAULT: Constants.DEFAULT_SLICE_PUBLIC_KEY_FILE,
        },
        Constants.SLICE_PRIVATE_KEY_FILE: {
            Constants.ENV_VAR: Constants.FABRIC_SLICE_PRIVATE_KEY_FILE,
            Constants.DEFAULT: Constants.DEFAULT_SLICE_PRIVATE_KEY_FILE,
        },
        Constants.AVOID: {
            Constants.ENV_VAR: Constants.FABRIC_AVOID,
            Constants.DEFAULT: "",
        },
        Constants.SSH_COMMAND_LINE: {
            Constants.ENV_VAR: Constants.FABRIC_SSH_COMMAND_LINE,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_SSH_COMMAND_LINE,
        },
        Constants.LOG_LEVEL: {
            Constants.ENV_VAR: Constants.FABRIC_LOG_LEVEL,
            Constants.DEFAULT: Constants.DEFAULT_LOG_LEVEL,
        },
        Constants.LOG_FILE: {
            Constants.ENV_VAR: Constants.FABRIC_LOG_FILE,
            Constants.DEFAULT: Constants.DEFAULT_LOG_FILE,
        },
        Constants.LOG_PROPAGATE: {
            Constants.ENV_VAR: Constants.FABRIC_LOG_PROPAGATE,
            Constants.DEFAULT: Constants.DEFAULT_LOG_PROPAGATE,
        },
        Constants.BASTION_SSH_CONFIG_FILE: {
            Constants.ENV_VAR: Constants.FABRIC_BASTION_SSH_CONFIG_FILE,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_BASTION_SSH_CONFIG_FILE,
        },
        Constants.METADATA_TAG: {
            Constants.ENV_VAR: Constants.FABRIC_METADATA_TAG,
            Constants.DEFAULT: Constants.DEFAULT_FABRIC_METADATA_TAG,
        },
    }

    REQUIRED_ATTRS_PRETTY_NAMES = {
        Constants.CREDMGR_HOST: "Credential Manager",
        Constants.ORCHESTRATOR_HOST: "Orchestrator",
        Constants.CORE_API_HOST: "Core API",
        Constants.AM_HOST: "Artifact Manager",
        Constants.CEPH_MGR_HOST: "CEPH Manager",
        Constants.TOKEN_LOCATION: "Token File",
        Constants.PROJECT_ID: "Project ID",
        Constants.PROJECT_NAME: "Project Name",
        Constants.BASTION_USERNAME: "Bastion Username",
        Constants.BASTION_KEY_LOCATION: "Bastion Private Key File",
        Constants.BASTION_HOST: "Bastion Host",
        Constants.BASTION_KEY_PASSPHRASE: "Bastion Private Key Passphrase",
        Constants.SLICE_PUBLIC_KEY_FILE: "Slice Public Key File",
        Constants.SLICE_PRIVATE_KEY_FILE: "Slice Private Key File",
        Constants.SLICE_PRIVATE_KEY_PASSPHRASE: "Slice Private Key Passphrase",
        Constants.LOG_FILE: "Log File",
        Constants.LOG_LEVEL: "Log Level",
        Constants.LOG_PROPAGATE: "Log Propagate",
        Constants.FABLIB_VERSION: "Version",
        Constants.AVOID: "Sites to avoid",
        Constants.DATA_DIR: "Data directory",
        Constants.SSH_COMMAND_LINE: "SSH Command Line",
        Constants.BASTION_SSH_CONFIG_FILE: "Bastion SSH Config File",
        Constants.METADATA_TAG: "Fabric Meta Data Release Tag",
    }

    os.makedirs(Constants.LOCAL_CACHE_DIR, exist_ok=True)

    def __init__(
        self,
        fabric_rc: str = None,
        credmgr_host: str = None,
        orchestrator_host: str = None,
        core_api_host: str = None,
        am_host: str = None,
        ceph_mgr_host: str = None,
        token_location: str = None,
        project_id: str = None,
        bastion_username: str = None,
        bastion_key_location: str = None,
        log_level: str = Constants.DEFAULT_LOG_LEVEL,
        log_file: str = Constants.DEFAULT_LOG_FILE,
        log_propagate: bool = Constants.DEFAULT_LOG_PROPAGATE,
        data_dir: str = Constants.DEFAULT_DATA_DIR,
        offline: bool = True,
        **kwargs,
    ):
        """
        Constructor. Tries to get configuration from:

         - constructor parameters (high priority)
         - fabric_rc file (middle priority)
         - environment variables (low priority)
         - defaults (if needed and possible)

        """
        if fabric_rc is None:
            fabric_rc = Constants.DEFAULT_FABRIC_RC
            if os.path.exists(Constants.DEFAULT_FABRIC_CONFIG_DIR):
                Path(fabric_rc).touch()

        if fabric_rc and os.path.exists(fabric_rc):
            self.config_file_path = fabric_rc
        self.is_yaml = False
        self.runtime_config = {}
        self.offline = offline

        # Load from config file
        self.__load_configuration(file_path=fabric_rc, **kwargs)

        # Apply any parameters explicitly passed
        if credmgr_host is not None:
            self.set_credmgr_host(credmgr_host=credmgr_host)

        if orchestrator_host is not None:
            self.set_orchestrator_host(orchestrator_host=orchestrator_host)

        if core_api_host is not None:
            self.set_core_api_host(core_api_host=core_api_host)

        if ceph_mgr_host is not None:
            self.set_ceph_mgr_host(ceph_mgr_host=ceph_mgr_host)

        if am_host is not None:
            self.set_am_host(am_host=am_host)

        if token_location is not None:
            self.set_token_location(token_location=token_location)

        if project_id is not None:
            self.set_project_id(project_id=project_id)

        if bastion_username is not None:
            self.set_bastion_username(bastion_username=bastion_username)

        if bastion_key_location is not None:
            self.set_bastion_key_location(bastion_key_location=bastion_key_location)

        if log_level is not None:
            self.set_log_level(log_level=log_level)

        if log_file is not None:
            self.set_log_file(log_file=log_file)

        if log_propagate is not None:
            self.set_log_propagate(log_propagate=log_propagate)

        if data_dir is not None:
            self.set_data_dir(data_dir=data_dir)

        #        if self.get_ssh_command_line() is None:
        #            self.set_ssh_command_line(
        #                ssh_command_line=Constants.DEFAULT_FABRIC_SSH_COMMAND_LINE
        #            )

        self.required_check(partial=True)

        # Verify that Token file exists; any other checks cannot be done without this.
        token_location = self.get_token_location()
        if not os.path.exists(token_location):
            raise ConfigException(
                f"Token file does not exist, please provide the token at location: {token_location}!"
            )

        self.log = logging.getLogger("fablib")

    def __load_configuration(self, file_path, **kwargs):
        """
        Load the config parameters from config file;
        - Parses bashrc/yaml file and loads the parameters in dictionary

        :param file_path: path to the config file; can be bashrc or yaml
        :type file_path: str
        :param kwargs:
        :type kwargs:

        :raises ConfigException: if config file does not exist
        """
        if file_path and os.path.exists(file_path):
            if Utils.is_yaml_file(file_path=file_path):
                self.__load_yaml_file(file_path=file_path)
                self.is_yaml = True
            else:
                self.__load_fabric_rc_file(file_path=file_path)

        for k, v in kwargs.items():
            self.runtime_config[k] = v

    def __load_yaml_file(self, file_path):
        """
        Load the config from yml file
        :param file_path: path to the config file
        :type file_path: str

        :return True or False indicating success/failure for loading the config file
        :rtype bool
        """
        try:
            with open(file_path, "r") as file:
                config = yaml.safe_load(file)
                if (
                    isinstance(config, dict)
                    and config.get(Constants.RUNTIME_SECTION) is not None
                ):
                    for key, value in config.get(Constants.RUNTIME_SECTION).items():
                        if value is not None:
                            value = value.strip().strip("'").strip('"')
                            if key == Constants.AVOID:
                                value = value.split(",")
                            self.runtime_config[key] = value
                    self.runtime_config[Constants.FABLIB_VERSION] = fablib_version
                    return True
                return False
        except yaml.YAMLError:
            return False

    def __load_fabric_rc_file(self, file_path):
        """
        Load the config from bashrc file
        :param file_path: path to the config file
        :type file_path: str

        :return True or False indicating success/failure for loading the config file
        :rtype bool
        """
        ret_val = False
        with open(file_path, "r") as file:
            lines = file.readlines()

        export_pattern = re.compile(r"^export\s+([^=]+)=(.*)$", re.IGNORECASE)

        for line in lines:
            match = export_pattern.match(line.strip())
            if match:
                key, value = match.groups()
                value = value.strip()
                value = value.strip('"')
                value = value.strip("'")
                key = key.replace("FABRIC_", "").lower()
                if key == Constants.AVOID and value is not None and len(value):
                    value = value.split(",")
                self.runtime_config[key] = value
                ret_val = True
        self.runtime_config[Constants.FABLIB_VERSION] = fablib_version
        return ret_val

    def required_check(self, partial: bool = False):
        """
        Validates that all the required parameters are present in the loaded config
        Tries to load the parameters from environment variable or defauls if not available in config in that order

        :raises AttributeError if missing required parameters are found
        """
        errors = []

        for attr, attr_props in self.REQUIRED_ATTRS.items():
            if attr not in self.runtime_config or self.runtime_config.get(attr) is None:
                # Load from environment variables
                if (
                    attr_props.get(Constants.ENV_VAR)
                    and os.environ.get(attr_props.get(Constants.ENV_VAR)) is not None
                ):
                    self.runtime_config[attr] = os.environ.get(
                        attr_props.get(Constants.ENV_VAR)
                    )
                # Load defaults if available
                elif attr_props.get(Constants.DEFAULT) is not None:
                    self.runtime_config[attr] = attr_props.get(Constants.DEFAULT)
                # Ignore validation for this parameter if no default value exists and this partial check
                elif attr_props.get(Constants.DEFAULT) is None and partial:
                    continue
                else:
                    errors.append(f"{attr} is not set")

        if errors:
            self.log.error(f"Failing Config: {self.runtime_config}")
            # TODO: define custom exception class to report errors,
            # and emit a more helpful error message with hints about
            # setting up environment variables or configuration file.
            raise AttributeError(
                f"Error initializing {self.__class__.__name__}: {errors}"
            )

    def get_config(self) -> Dict[str, str]:
        """
        Gets a dictionary mapping keywords to configured FABRIC environment
        variable values.

        :return: dictionary mapping keywords to FABRIC values
        :rtype: Dict[String, String]
        """
        return self.runtime_config

    def get_default_slice_public_key_file(self) -> str:
        """
        Gets the path to the default slice public key file.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice public key on this fablib object
        :rtype: String
        """
        return self.runtime_config.get(Constants.SLICE_PUBLIC_KEY_FILE)

    def get_default_slice_private_key_file(self) -> str:
        """
        Gets the path to the default slice private key file.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the path to the slice private key on this fablib object
        :rtype: String
        """
        return self.runtime_config.get(Constants.SLICE_PRIVATE_KEY_FILE)

    def get_default_slice_private_key_passphrase(self) -> str:
        """
        Gets the passphrase to the default slice private key.

        Important! Slices key management is underdevelopment and this
        functionality will likely change going forward.

        :return: the passphrase to the slice private key on this fablib object
        :rtype: String
        """
        return self.runtime_config.get(Constants.SLICE_PRIVATE_KEY_PASSPHRASE)

    def get_credmgr_host(self) -> str:
        """
        Gets the credential manager host value.

        :return: the credential manager host
        :rtype: String
        """
        return self.get_config().get(Constants.CREDMGR_HOST)

    def set_credmgr_host(self, credmgr_host: str):
        """
        Sets the credential manager host value.
        :param credmgr_host: credential manager host site
        :type credmgr_host: String
        """
        self.runtime_config[Constants.CREDMGR_HOST] = credmgr_host

    def get_orchestrator_host(self) -> str:
        """
        Gets the orchestrator host value.

        :return: the orchestrator host site
        :rtype: String
        """
        return self.get_config().get(Constants.ORCHESTRATOR_HOST)

    def set_orchestrator_host(self, orchestrator_host: str):
        """
        Sets the Orchestrator host value.
        :param orchestrator_host: Orchestrator host
        :type orchestrator_host: String
        """
        self.runtime_config[Constants.ORCHESTRATOR_HOST] = orchestrator_host

    def get_core_api_host(self) -> str:
        """
        Gets the core_api host value.

        :return: the core_api host site
        :rtype: String
        """
        return self.get_config().get(Constants.CORE_API_HOST)

    def set_core_api_host(self, core_api_host: str):
        """
        Sets the core_api host value.
        :param core_api_host: core_api host
        :type core_api_host: String
        """
        self.runtime_config[Constants.CORE_API_HOST] = core_api_host

    def set_ceph_mgr_host(self, ceph_mgr_host: str):
        """
        Sets the ceph_mgr host value.
        :param ceph_mgr_host: ceph_mgr host
        :type ceph_mgr_host: String
        """
        self.runtime_config[Constants.CEPH_MGR_HOST] = ceph_mgr_host

    def get_ceph_mgr_host(self) -> str:
        """
        Gets the ceph_mgr host value.

        :return: the ceph_mgr host site
        :rtype: String
        """
        return self.runtime_config.get(Constants.CEPH_MGR_HOST)

    def get_am_host(self) -> str:
        """
        Gets the am host value.

        :return: the am host site
        :rtype: String
        """
        return self.get_config().get(Constants.AM_HOST)

    def set_am_host(self, am_host: str):
        """
        Sets the am host value.
        :param am_host: core_api host
        :type am_host: String
        """
        self.runtime_config[Constants.AM_HOST] = am_host

    def get_token_location(self) -> str:
        """
        Gets the FABRIC token location.

        :return: FABRIC token location
        :rtype: String
        """
        return self.get_config().get(Constants.TOKEN_LOCATION)

    def set_token_location(self, token_location: str):
        """
        Sets the FABRIC token location.

        :param token_location: Token Location
        :type token_location: String
        """
        self.runtime_config[Constants.TOKEN_LOCATION] = token_location

    def get_bastion_username(self) -> str:
        """
        Gets the FABRIC Bastion username.

        :return: FABRIC Bastion username
        :rtype: String
        """
        return self.get_config().get(Constants.BASTION_USERNAME)

    def set_bastion_username(self, bastion_username: str):
        """
        Sets the FABRIC Bastion username.

        :param bastion_username: Bastion username
        :type bastion_username: String
        """
        self.runtime_config[Constants.BASTION_USERNAME] = bastion_username

    def get_bastion_key_location(self) -> str:
        """
        Gets the FABRIC Bastion key filename.

        :return: FABRIC Bastion key filename
        :rtype: String
        """
        return self.get_config().get(Constants.BASTION_KEY_LOCATION)

    def set_bastion_key_location(self, bastion_key_location: str):
        """
        Sets the FABRIC Bastion Key Location.

        :param bastion_key_location: Bastion Key Location
        :type bastion_key_location: String
        """
        self.runtime_config[Constants.BASTION_KEY_LOCATION] = bastion_key_location

    def get_bastion_key_passphrase(self) -> str:
        """
        Reads the FABRIC Bastion private key passphrase.

        :return: FABRIC Bastion key passphrase
        :rtype: String
        """
        return self.runtime_config.get(Constants.BASTION_KEY_PASSPHRASE)

    def get_bastion_key(self) -> Union[str, None]:
        """
        Reads the FABRIC Bastion private key file and returns the key.

        :return: FABRIC Bastion key string
        :rtype: String
        """
        if self.get_bastion_key_location() is None or not os.path.exists(
            self.get_bastion_key_location()
        ):
            return None
        return Utils.read_file_contents(file_path=self.get_bastion_key_location())

    def get_bastion_public_key(self) -> Union[str, None]:
        """
        Reads the FABRIC Bastion public key file and returns the key.

        :return: FABRIC Bastion key string
        :rtype: String
        """
        if self.get_bastion_key_location() is None or not os.path.exists(
            self.get_bastion_key_location()
        ):
            return None
        return Utils.read_file_contents(
            file_path=f"{self.get_bastion_key_location()}.pub"
        )

    def get_bastion_host(self) -> str:
        """
        Gets the FABRIC Bastion host address.

        :return: Bastion host public address
        :rtype: String
        """
        return self.get_config().get(Constants.BASTION_HOST)

    def get_project_id(self) -> str:
        """
        Get the Project Id:
        :return: Project Id
        :rtype: String
        """
        return self.get_config().get(Constants.PROJECT_ID)

    def set_project_id(self, project_id: str):
        """
        Set the Project Id:
        :param: project_id: Project Id
        :type: String
        """
        self.runtime_config[Constants.PROJECT_ID] = project_id

    def get_project_name(self):
        """
        Get the Project Name:
        :return: Project Name
        :rtype: String
        """
        return self.runtime_config.get(Constants.PROJECT_NAME)

    def set_log_level(self, log_level: str = "INFO"):
        """
        Sets the current log level for logging

        Options:  'DEBUG'
                  'INFO'
                  'WARNING'
                  'ERROR'
                  'CRITICAL'

        :param log_level: new log level
        :type str: Level
        """

        self.runtime_config[Constants.LOG_LEVEL] = log_level

    def get_log_level(self):
        """
        Get the current log level for logging

        :return log_level: new log level
        :rtype log_level: string
        """

        return self.runtime_config.get(Constants.LOG_LEVEL)

    def get_log_file(self) -> str:
        """
        Gets the current log file for logging

        :return log_file: new log level
        :rtype log_file: string
        """

        return self.runtime_config.get(Constants.LOG_FILE)

    def set_log_file(self, log_file: str):
        """
        Sets the current log file for logging

        :param log_file: new log level
        :type log_file: string
        """
        self.runtime_config[Constants.LOG_FILE] = log_file

    def get_log_propagate(self) -> bool:
        """
        Gets whether fablib logs propagate to the root logger.

        :return: propagation flag
        :rtype: bool
        """
        val = self.runtime_config.get(Constants.LOG_PROPAGATE)
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes", "on", "y", "t")
        if val is None:
            return Constants.DEFAULT_LOG_PROPAGATE
        return bool(val)

    def set_log_propagate(self, log_propagate: Union[bool, str, int]):
        """
        Sets whether fablib logs propagate to the root logger.

        :param log_propagate: propagation flag
        :type log_propagate: bool
        """
        self.runtime_config[Constants.LOG_PROPAGATE] = log_propagate

    def get_data_dir(self) -> str:
        """
        Gets the data directory

        :return data_dir: data directory
        :rtype data_dir: string
        """

        return self.runtime_config.get(Constants.DATA_DIR)

    def set_data_dir(self, data_dir: str):
        """
        Sets the data directory

        :param data_dir: data directory
        :type data_dir: string
        """
        self.runtime_config[Constants.DATA_DIR] = data_dir

    def get_ssh_command_line(self):
        """
        Gets the data directory

        :return data_dir: data directory
        :rtype data_dir: string
        """
        return self.runtime_config.get(Constants.SSH_COMMAND_LINE)

    def set_ssh_command_line(self, ssh_command_line: str):
        """
        Sets the ssh command line

        :param ssh_command_line: ssh command line
        :type ssh_command_line: string
        """
        self.runtime_config[Constants.SSH_COMMAND_LINE] = ssh_command_line

    def get_bastion_ssh_config_file(self):
        """
        Gets the bastion ssh config file

        :return bastion_ssh_config_file: bastion_ssh_config_file
        :rtype bastion_ssh_config_file: string
        """
        return self.runtime_config.get(Constants.BASTION_SSH_CONFIG_FILE)

    def get_avoid(self):
        """
        Gets the avoid list

        :return avoid: avoid list
        :rtype avoid: string
        """
        return self.runtime_config.get(Constants.AVOID)

    def set_avoid(self, avoid: List[str]):
        """
        Sets the avoid list

        :param avoid: avoid list
        :type avoid: string
        """
        self.runtime_config[Constants.AVOID] = avoid

    def set_avoid_csv(self, avoid_csv: str = ""):
        """
        Sets the avoid site list from a CSV

        :param avoid_csv: avoid list
        :type avoid_csv: List of string
        """
        avoid_csv = avoid_csv.strip().strip('"').strip("'")

        avoid = []
        for site in avoid_csv.split(","):
            avoid.append(site.strip())

        self.set_avoid(avoid)

    def get_default_slice_private_key(self) -> Union[str, None]:
        """
        Gets the current default_slice_keys as a dictionary containg the
        public and private slice keys.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: default_slice_key dictionary from superclass
        :rtype: Dict[String, String]
        """
        if self.get_default_slice_private_key_file() is not None and os.path.exists(
            self.get_default_slice_private_key_file()
        ):
            return Utils.read_file_contents(
                file_path=self.get_default_slice_private_key_file()
            )
        return None

    def get_default_slice_public_key(self) -> Union[str, None]:
        """
        Gets the current default_slice_keys as a dictionary containg the
        public and private slice keys.

        Important! Slice key management is underdevelopment and this
        functionality will likely change going forward.

        :return: default_slice_key dictionary from superclass
        :rtype: Dict[String, String]
        """
        if self.get_default_slice_public_key_file() is not None and os.path.exists(
            self.get_default_slice_public_key_file()
        ):
            return Utils.read_file_contents(
                file_path=self.get_default_slice_public_key_file()
            )
        return None

    @staticmethod
    def get_image_names() -> dict[str, dict]:
        """
        Gets a list of available image names.

        This is statically defined for now. Eventually, images will be managed dynamically.

        :return: Dictionary of images with default user and description
        :rtype: dict[str, dict]
        """
        return Constants.IMAGE_NAMES

    def get_config_pretty_names_dict(self) -> Dict[str, str]:
        """
        Return PRETTY Names for the config

        :return: Dict of Pretty Names
        :rtype: Dict[str, str]
        """
        return self.REQUIRED_ATTRS_PRETTY_NAMES

    def save_config(self):
        """
        Write the configuration file.
        """
        if self.config_file_path is None:
            print("Config file path not set!")
            return

        if self.is_yaml:
            # Write the dictionary to the YAML file
            with atomic_write(self.config_file_path, overwrite=True) as f:
                yaml.dump(self.runtime_config, f, default_flow_style=False)
        else:
            with atomic_write(self.config_file_path, overwrite=True) as f:
                for attr, attr_props in self.REQUIRED_ATTRS.items():
                    env_var = attr_props.get(Constants.ENV_VAR)
                    value = self.runtime_config.get(attr)
                    if value is None:
                        value = ""
                    if env_var:
                        f.write(f"export {env_var}={value}\n")

    def setup_logging(self):
        """
        Create log file if it doesn't exist; setup logger
        """
        try:
            if self.get_log_file() and not os.path.isdir(
                os.path.dirname(self.get_log_file())
            ):
                os.makedirs(os.path.dirname(self.get_log_file()))
        except Exception:
            self.log.warning(
                f"Failed to create log_file directory: {os.path.dirname(self.get_log_file())}"
            )

        default_log_format = (
            "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s"
        )
        default_date_format = "%H:%M:%S"

        # Control propagation to root handlers (default False to avoid Jupyter cell spam).
        self.log.propagate = self.get_log_propagate()

        if self.get_log_level():
            self.log.setLevel(self.LOG_LEVELS[self.get_log_level()])

        if self.get_log_file():
            file_handler = RotatingFileHandler(
                self.get_log_file(), backupCount=int(5), maxBytes=int(1024 * 1024 * 5)
            )
            file_handler.setFormatter(
                logging.Formatter(default_log_format, datefmt=default_date_format)
            )
            self.log.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.CRITICAL)
        self.log.addHandler(console_handler)

    @staticmethod
    def get_metadata_tag() -> str:
        """
        Get the metadata tag used to fetch remote configuration files.

        This tag determines which version or branch (e.g., "main", "v1.0.0")
        of the metadata directory is used.

        :return: Metadata tag string.
        :rtype: str
        """
        return os.environ.get(
            Constants.FABRIC_METADATA_TAG, Constants.DEFAULT_FABRIC_METADATA_TAG
        )

    @staticmethod
    def _fetch_or_load_json(
        name: str, ttl: int = 86400, fallback_default: dict = {}
    ) -> dict:
        """
        Fetch a JSON file from a remote URL, using local caching with time-based invalidation,
        and fall back to a default if the fetch or cache read fails.

        If a valid cached file exists within the TTL, it is used.
        If not, the method tries to fetch from the remote GitHub metadata URL.
        If the fetch fails, it returns either the cached file (if available) or the fallback default.

        :param name: Name of the metadata file (without .json extension).
        :type name: str
        :param ttl: Time-to-live for cache in seconds (default is 86400 = 1 day).
        :type ttl: int
        :param fallback_default: Default dictionary to use if remote and cached fetches fail.
        :type fallback_default: dict or None
        :return: The loaded JSON data.
        :rtype: dict
        :raises RuntimeError: If no valid data can be fetched or loaded and no fallback is provided.
        """
        remote_url = Constants.FABRIC_METADATA_URL.format(Config.get_metadata_tag())
        remote_url += f"/{name}.json"
        local_file = os.path.join(Constants.LOCAL_CACHE_DIR, f"{name}.json")

        # Check if cache file is fresh
        if os.path.exists(local_file):
            age = time.time() - os.path.getmtime(local_file)
            if age < ttl:
                with open(local_file, "r") as f:
                    return json.load(f)

        try:
            response = requests.get(remote_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            with atomic_write(local_file, overwrite=True) as f:
                json.dump(data, f, indent=2)
            return data
        except Exception:
            if os.path.exists(local_file):
                with open(local_file, "r") as f:
                    return json.load(f)
            elif fallback_default is not None:
                return fallback_default
            else:
                raise RuntimeError(f"Could not retrieve or load {name}.json")

    @staticmethod
    @lru_cache(maxsize=1)
    def get_os_images() -> dict:
        """
        Get a dictionary of supported OS images from cached metadata.

        The data is fetched from a remote GitHub metadata source or returned from local cache.
        Falls back to a static default (Constants.IMAGE_NAMES) if both fail.

        :return: Dictionary of image metadata.
        :rtype: dict
        """
        return Config._fetch_or_load_json(
            "os_images", fallback_default=Constants.IMAGE_NAMES
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def get_facility_port_details() -> dict:
        """
        Get the facility port metadata including descriptions and mappings.

        Uses remote metadata cache if available, falling back to an empty dictionary.

        :return: Dictionary of facility port details.
        :rtype: dict
        """
        return Config._fetch_or_load_json("facility_ports", fallback_default={})


if __name__ == "__main__":
    config1 = Config(fabric_rc="./fabric_rc", credmgr_host="abc.def.com")
    assert config1.get_credmgr_host() == "abc.def.com"
    print(json.dumps(config1.runtime_config, indent=4))

    config2 = Config(fabric_rc="./fabric_rc.yml", credmgr_host="abc.def.com")
    assert config2.get_credmgr_host() == "abc.def.com"
    print(json.dumps(config2.runtime_config, indent=4))
