#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2023 FABRIC Testbed
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

import socket
import time
import unittest
import pytest

from fabrictestbed_extensions.fablib.fablib import FablibManager


@pytest.fixture(scope="session")
def fablib():
    return FablibManager()


@pytest.fixture(scope="session")
def fabric_slice(fablib):
    # Give the slice a unique name so that slice creation will not
    # fail (because there is an existing slice with the same name) and
    # we will have some hints about the test that created the slice.
    time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    host = socket.gethostname()
    slice_name = f"integration test @ {time_stamp} on {host}"

    print(f"Creating slice '{slice_name}'..")
    slice = fablib.new_slice(name=slice_name)

    yield slice

    slice.delete()
