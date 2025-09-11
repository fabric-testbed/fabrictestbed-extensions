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
import logging
import os


class Constants:
    DEFAULT_FABRIC_CREDMGR_HOST = "cm.fabric-testbed.net"
    DEFAULT_FABRIC_ORCHESTRATOR_HOST = "orchestrator.fabric-testbed.net"
    DEFAULT_FABRIC_CORE_API_HOST = "uis.fabric-testbed.net"
    DEFAULT_FABRIC_AM_HOST = "artifacts.fabric-testbed.net"
    DEFAULT_FABRIC_BASTION_HOST = "bastion.fabric-testbed.net"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FILE = "/tmp/fablib/fablib.log"
    DEFAULT_DATA_DIR = "/tmp/fablib"
    DEFAULT_WORK_DIR = f"{os.environ['HOME']}/work"
    DEFAULT_FABRIC_CONFIG_DIR = f"{DEFAULT_WORK_DIR}/fabric_config"
    DEFAULT_FABRIC_RC = f"{DEFAULT_FABRIC_CONFIG_DIR}/fabric_rc"
    DEFAULT_TOKEN_LOCATION = f"{os.environ['HOME']}/.tokens.json"
    DEFAULT_SLICE_PRIVATE_KEY_FILE = f"{DEFAULT_FABRIC_CONFIG_DIR}/slice_key"
    DEFAULT_SLICE_PUBLIC_KEY_FILE = f"{DEFAULT_SLICE_PRIVATE_KEY_FILE}.pub"
    DEFAULT_BASTION_KEY_LOCATION = f"{DEFAULT_FABRIC_CONFIG_DIR}/fabric_bastion_key"
    DEFAULT_FABRIC_BASTION_SSH_CONFIG_FILE = f"{DEFAULT_FABRIC_CONFIG_DIR}/ssh_config"
    DEFAULT_FABRIC_METADATA_TAG = "main"

    DEFAULT_FABRIC_SSH_COMMAND_LINE = (
        "ssh -i {{ _self_.private_ssh_key_file }} -F "
        + DEFAULT_FABRIC_BASTION_SSH_CONFIG_FILE
        + " {{ _self_.username }}@{{ _self_.management_ip }}"
    )

    FABRIC_CREDMGR_HOST = "FABRIC_CREDMGR_HOST"
    FABRIC_ORCHESTRATOR_HOST = "FABRIC_ORCHESTRATOR_HOST"
    FABRIC_CORE_API_HOST = "FABRIC_CORE_API_HOST"
    FABRIC_AM_HOST = "FABRIC_AM_HOST"
    FABRIC_TOKEN_LOCATION = "FABRIC_TOKEN_LOCATION"
    FABRIC_PROJECT_ID = "FABRIC_PROJECT_ID"
    FABRIC_BASTION_HOST = "FABRIC_BASTION_HOST"
    FABRIC_BASTION_USERNAME = "FABRIC_BASTION_USERNAME"
    FABRIC_BASTION_KEY_LOCATION = "FABRIC_BASTION_KEY_LOCATION"
    FABRIC_SLICE_PUBLIC_KEY_FILE = "FABRIC_SLICE_PUBLIC_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_FILE = "FABRIC_SLICE_PRIVATE_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE = "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE"
    FABRIC_LOG_FILE = "FABRIC_LOG_FILE"
    FABRIC_LOG_LEVEL = "FABRIC_LOG_LEVEL"
    FABRIC_AVOID = "FABRIC_AVOID"
    FABRIC_SSH_COMMAND_LINE = "FABRIC_SSH_COMMAND_LINE"
    FABLIB_VERSION = "fablib_version"
    FABRIC_BASTION_SSH_CONFIG_FILE = "FABRIC_BASTION_SSH_CONFIG_FILE"
    FABRIC_METADATA_TAG = "FABRIC_METADATA_TAG"

    FABRIC_PRIMARY = "#27aae1"
    FABRIC_PRIMARY_LIGHT = "#cde4ef"
    FABRIC_PRIMARY_DARK = "#078ac1"
    FABRIC_SECONDARY = "#f26522"
    FABRIC_SECONDARY_LIGHT = "#ff8542"
    FABRIC_SECONDARY_DARK = "#d24502"
    FABRIC_BLACK = "#231f20"
    FABRIC_DARK = "#433f40"
    FABRIC_GREY = "#666677"
    FABRIC_LIGHT = "#f3f3f9"
    FABRIC_WHITE = "#ffffff"
    FABRIC_LOGO = "fabric_logo.png"

    FABRIC_PRIMARY_EXTRA_LIGHT = "#dbf3ff"

    SUCCESS_COLOR = "#8eff92"
    SUCCESS_LIGHT_COLOR = "#c3ffc4"
    SUCCESS_DARK_COLOR = "#59cb63"

    ERROR_COLOR = "#ff8589"
    ERROR_LIGHT_COLOR = "#ffb7b9"
    ERROR_DARK_COLOR = "#b34140"

    IN_PROGRESS_COLOR = "#ffff8c"
    IN_PROGRESS_LIGHT_COLOR = "#ffffbe"
    IN_PROGRESS_DARK_COLOR = "#c8555c"

    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    RUNTIME_SECTION = "runtime"

    CREDMGR_HOST = "credmgr_host"
    ORCHESTRATOR_HOST = "orchestrator_host"
    CORE_API_HOST = "core_api_host"
    AM_HOST = "am_host"
    TOKEN_LOCATION = "token_location"
    PROJECT_ID = "project_id"
    PROJECT_NAME = "project_name"
    BASTION_HOST = "bastion_host"
    BASTION_USERNAME = "bastion_username"
    BASTION_KEY_LOCATION = "bastion_key_location"
    BASTION_KEY_PASSPHRASE = "bastion_key_passphrase"
    LOG_FILE = "log_file"
    LOG_LEVEL = "log_level"
    DATA_DIR = "data_dir"
    SSH_COMMAND_LINE = "ssh_command_line"
    AVOID = "avoid"
    SLICE_PRIVATE_KEY_FILE = "slice_private_key_file"
    SLICE_PUBLIC_KEY_FILE = "slice_public_key_file"
    SLICE_PRIVATE_KEY = "slice_private_key"
    SLICE_PUBLIC_KEY = "slice_public_key"
    SLICE_PRIVATE_KEY_PASSPHRASE = "slice_private_key_passphrase"
    BASTION_SSH_CONFIG_FILE = "bastion_ssh_config_file"
    METADATA_TAG = "metadata_tag"

    IMAGE_NAMES = {
        "default_centos8_stream": {
            "description": "CentOS 8 Stream (non-stream)",
            "default_user": "centos",
        },
        "default_centos9_stream": {
            "description": "CentOS 9 Stream (default install)",
            "default_user": "cloud-user",
        },
        "default_centos10_stream": {
            "description": "CentOS 10 Stream (default install)",
            "default_user": "cloud-user",
        },
        "default_debian_11": {
            "description": "Debian 11 Bullseye",
            "default_user": "debian",
        },
        "default_debian_12": {
            "description": "Debian 12 Bookworm",
            "default_user": "debian",
        },
        "default_fedora_39": {"description": "Fedora 39", "default_user": "fedora"},
        "default_fedora_40": {"description": "Fedora 40", "default_user": "fedora"},
        "default_freebsd_13_zfs": {
            "description": "FreeBSD 13 with ZFS",
            "default_user": "freebsd",
        },
        "default_freebsd_14_zfs": {
            "description": "FreeBSD 14 with ZFS",
            "default_user": "freebsd",
        },
        "default_kali": {
            "description": "Kali Linux (for penetration testing)",
            "default_user": "kali",
        },
        "default_openbsd_7": {"description": "OpenBSD 7", "default_user": "openbsd"},
        "default_rocky_8": {"description": "Rocky Linux 8", "default_user": "rocky"},
        "default_rocky_9": {"description": "Rocky Linux 9", "default_user": "rocky"},
        "default_ubuntu_20": {
            "description": "Ubuntu 20.04 LTS Focal Fossa",
            "default_user": "ubuntu",
        },
        "default_ubuntu_22": {
            "description": "Ubuntu 22.04 LTS Jammy Jellyfish",
            "default_user": "ubuntu",
        },
        "default_ubuntu_24": {
            "description": "Ubuntu 24.04 LTS Noble Numbat",
            "default_user": "ubuntu",
        },
        "docker_rocky_8": {
            "description": "Rocky Linux 8 Docker image",
            "default_user": "rocky",
        },
        "docker_rocky_9": {
            "description": "Rocky Linux 9 Docker image",
            "default_user": "rocky",
        },
        "docker_ubuntu_20": {
            "description": "Ubuntu 20.04 LTS Docker image",
            "default_user": "ubuntu",
        },
        "docker_ubuntu_22": {
            "description": "Ubuntu 22.04 LTS Docker image",
            "default_user": "ubuntu",
        },
        "attestable_bmv2_v1_ubuntu_20": {
            "description": "Ubuntu 20.04 LTS Focal Fossa with BMv2 essentials",
            "default_user": "ubuntu",
        },
    }

    ENV_VAR = "env_var"
    DEFAULT = "default"

    UUID = "uuid"
    NAME = "name"
    BASTION_LOGIN = "bastion_login"
    KEY_TYPE_BASTION = "bastion"
    KEY_TYPE_SLIVER = "sliver"
    PRIVATE_OPENSSH = "private_openssh"
    PUBLIC_OPENSSH = "public_openssh"
    EMAIL = "email"
    SSH_KEYS = "sshkeys"
    EXPIRES_ON = "expires_on"
    LEASE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S %z"
    FABRIC_KEY_TYPE = "fabric_key_type"

    NON_PRETTY_NAME = "non_pretty_name"
    PRETTY_NAME = "pretty_name"
    HEADER_NAME = "header_name"
    AVAILABLE = "Available"
    CAPACITY = "Capacity"
    ALLOCATED = "Allocated"
    VALUE = "value"

    NIC_SHARED_CONNECTX_6 = "SharedNIC-ConnectX-6"
    SMART_NIC_CONNECTX_6 = "SmartNIC-ConnectX-6"
    SMART_NIC_CONNECTX_5 = "SmartNIC-ConnectX-5"
    SMART_NIC_CONNECTX_7_100 = "SmartNIC-ConnectX-7-100"
    SMART_NIC_CONNECTX_7_400 = "SmartNIC-ConnectX-7-400"
    SMART_NIC_BlueField2_CONNECTX_6 = "SmartNIC-BlueField2-ConnectX-6"
    NVME_P4510 = "NVME-P4510"
    GPU_TESLA_T4 = "GPU-Tesla T4"
    GPU_RTX6000 = "GPU-RTX6000"
    GPU_A30 = "GPU-A30"
    GPU_A40 = "GPU-A40"
    FPGA_XILINX_U280 = "FPGA-Xilinx-U280"
    FPGA_XILINX_SN1022 = "FPGA-Xilinx-SN1022"
    CORES = "Cores"
    RAM = "Ram"
    DISK = "Disk"
    CPUS = "CPUs"
    HOSTS = "Hosts"
    P4_SWITCH = "P4-Switch"

    CMP_NIC_Basic = "NIC_Basic"
    CMP_NIC_BlueField2_ConnectX_6 = "NIC_BlueField_2_ConnectX_6"
    CMP_NIC_ConnectX_7_400 = "NIC_ConnectX_7_400"
    CMP_NIC_ConnectX_7_100 = "NIC_ConnectX_7_100"
    CMP_NIC_ConnectX_6 = "NIC_ConnectX_6"
    CMP_NIC_ConnectX_5 = "NIC_ConnectX_5"
    CMP_NIC_P4 = "NIC_P4"
    CMP_NVME_P4510 = "NVME_P4510"
    CMP_GPU_TeslaT4 = "GPU_TeslaT4"
    CMP_GPU_RTX6000 = "GPU_RTX6000"
    CMP_GPU_A40 = "GPU_A40"
    CMP_GPU_A30 = "GPU_A30"
    CMP_NIC_OpenStack = "NIC_OpenStack"
    CMP_FPGA_Xilinx_U280 = "FPGA_Xilinx_U280"
    CMP_FPGA_Xilinx_SN1022 = "FPGA_Xilinx_SN1022"
    P4_DedicatedPort = "P4_DedicatedPort"

    FABRIC_USER = "fabric"
    FABRIC_METADATA_URL = "https://raw.githubusercontent.com/fabric-testbed/fabric-global-metadata/{}/metadata"
    LOCAL_CACHE_DIR = os.path.expanduser("~/.fabric/cache")
