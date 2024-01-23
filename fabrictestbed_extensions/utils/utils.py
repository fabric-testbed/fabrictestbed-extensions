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
import hashlib
import os
import socket

import yaml
from atomicwrites import atomic_write


class Utils:
    @staticmethod
    def is_reachable(*, hostname: str, port: int = 443):
        try:
            # Attempt to resolve the hostname to an IP address
            ip_address = socket.gethostbyname(hostname)

            # Attempt to create a socket connection to the IP address and port 80
            with socket.create_connection((ip_address, port), timeout=5):
                return True
        except (socket.gaierror, socket.timeout, OSError):
            raise ConnectionError(
                f"Host: {hostname} is not reachable, please check your config file!"
            )

    @staticmethod
    def save_to_file(file_path: str, data: str):
        # If the file exists, use atomic_write
        if os.path.exists(file_path):
            with atomic_write(file_path, overwrite=True) as f:
                f.write(data)
        else:
            # If the file doesn't exist, create it atomically
            with open(file_path, "w") as f:
                f.write(data)

    @staticmethod
    def get_md5_fingerprint(key_string):
        key_bytes = key_string.encode("utf-8")
        md5_hash = hashlib.md5(key_bytes).hexdigest()
        return ":".join(a + b for a, b in zip(md5_hash[::2], md5_hash[1::2]))

    @staticmethod
    def is_yaml_file(file_path: str):
        try:
            with open(file_path, "r") as file:
                # Attempt to load the content as YAML
                yaml_content = yaml.safe_load(file)

                # Check if the loaded content is a dictionary or a list
                if isinstance(yaml_content, (dict, list)):
                    return True
                else:
                    return False

        except yaml.YAMLError:
            # Parsing failed, it's not a YAML file
            return False
        except FileNotFoundError:
            # File not found
            return False

    @staticmethod
    def read_file_contents(file_path: str) -> str:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
