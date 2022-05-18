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
# Author: Paul Ruth (pruth@renci.org)
import os

from abc import ABC
from fabrictestbed.util.constants import Constants


class AbcFabLIB(ABC):
    FABRIC_BASTION_USERNAME = "FABRIC_BASTION_USERNAME"
    FABRIC_BASTION_KEY_LOCATION = "FABRIC_BASTION_KEY_LOCATION"
    FABRIC_BASTION_HOST = "FABRIC_BASTION_HOST"
    FABRIC_BASTION_KEY_PASSWORD = "FABRIC_BASTION_KEY_PASSWORD"
    FABRIC_BASTION_HOST_PRIVATE_IPV4 = "FABRIC_BASTION_HOST_PRIVATE_IPV4"
    FABRIC_BASTION_HOST_PRIVATE_IPV6 = "FABRIC_BASTION_HOST_PRIVATE_IPV6"
    FABRIC_SLICE_PUBLIC_KEY_FILE = "FABRIC_SLICE_PUBLIC_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_FILE = "FABRIC_SLICE_PRIVATE_KEY_FILE"
    FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE = "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE"

    def __init__(self):
        """
        Constructor. Sets environment variables for important FABRIC values.
        """
        self.credmgr_host = None
        self.orchestrator_host = None
        self.fabric_token = None
        self.project_id = None

        self.bastion_username = None
        self.bastion_key_filename = None
        self.bastion_public_addr = None
        self.bastion_private_ipv4_addr = '0.0.0.0'
        self.bastion_private_ipv6_addr = '0:0:0:0:0:0'

        self.slice_keys = {}
        self.default_slice_key = {}
        self.slice_keys['default'] = self.default_slice_key

        if Constants.FABRIC_CREDMGR_HOST in os.environ:
            self.credmgr_host = os.environ[Constants.FABRIC_CREDMGR_HOST]

        if Constants.FABRIC_ORCHESTRATOR_HOST in os.environ:
            self.orchestrator_host = os.environ[Constants.FABRIC_ORCHESTRATOR_HOST]

        if Constants.FABRIC_TOKEN_LOCATION in os.environ:
            self.fabric_token=os.environ[Constants.FABRIC_TOKEN_LOCATION]

        if Constants.FABRIC_PROJECT_ID in os.environ:
            self.project_id = os.environ[Constants.FABRIC_PROJECT_ID]

        #Basstion host setup
        if self.FABRIC_BASTION_USERNAME in os.environ:
            self.bastion_username = os.environ[self.FABRIC_BASTION_USERNAME]
        if self.FABRIC_BASTION_KEY_LOCATION in os.environ:
            self.bastion_key_filename = os.environ[self.FABRIC_BASTION_KEY_LOCATION]
        if self.FABRIC_BASTION_HOST in os.environ:
            self.bastion_public_addr = os.environ[self.FABRIC_BASTION_HOST]
        if self.FABRIC_BASTION_HOST_PRIVATE_IPV4 in os.environ:
            self.bastion_private_ipv4_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV4]
        if self.FABRIC_BASTION_HOST_PRIVATE_IPV6 in os.environ:
            self.bastion_private_ipv6_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV6]

        #Slice Keys
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in os.environ:
            self.default_slice_key['slice_public_key_file'] = os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE]
            with open(os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key['slice_public_key'] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in os.environ:
            #self.slice_private_key_file=os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']
            self.default_slice_key['slice_private_key_file'] = os.environ[self.FABRIC_SLICE_PRIVATE_KEY_FILE]
        if "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE" in os.environ:
            #self.slice_private_key_passphrase = os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']
            self.default_slice_key['slice_private_key_passphrase'] = os.environ[self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]
