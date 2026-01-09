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
        import errno

        try:
            # Get all available addresses (IPv4 and IPv6) for the hostname
            addr_info = socket.getaddrinfo(
                hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM
            )

            # Try to connect to each address until one succeeds
            errors = []
            permission_denied = False
            for family, socktype, proto, canonname, sockaddr in addr_info:
                try:
                    sock = socket.socket(family, socktype, proto)
                    sock.settimeout(5)
                    sock.connect(sockaddr)
                    sock.close()
                    return True
                except OSError as e:
                    family_name = "IPv6" if family == socket.AF_INET6 else "IPv4"

                    # EACCES (13) or EPERM (1) - permission denied by local firewall/security policy
                    # Common on VMs with restricted network policies; treat as reachable since
                    # DNS works and the block is local, not because the remote host is down
                    if e.errno in (errno.EACCES, errno.EPERM):
                        permission_denied = True
                        errors.append(
                            f"{family_name} {sockaddr[0]}: blocked by local policy"
                        )
                    # ENETUNREACH (101) - this address family isn't routable on this system
                    elif e.errno == errno.ENETUNREACH:
                        errors.append(
                            f"{family_name} {sockaddr[0]}: network unreachable"
                        )
                    else:
                        errors.append(f"{family_name} {sockaddr[0]}: {e}")
                    continue
                except socket.timeout as e:
                    errors.append(f"timeout connecting to {sockaddr[0]}: {e}")
                    continue

            # If we got permission denied, treat as reachable since DNS resolves
            # and we can't verify connectivity due to local security restrictions
            if permission_denied:
                return True

            # If we tried all addresses and none worked, raise with details
            error_details = "; ".join(errors)
            raise OSError(
                f"Could not reach {hostname}:{port}. Attempted addresses: {error_details}"
            )
        except socket.gaierror as e:
            raise ConnectionError(f"Could not resolve hostname {hostname}: {e}")
        except (socket.timeout, OSError) as e:
            raise ConnectionError(
                f"Host: {hostname} is not reachable, please check your config file! Details: {e}"
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
