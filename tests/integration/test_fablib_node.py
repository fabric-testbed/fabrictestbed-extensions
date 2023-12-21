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

import socket
import time
import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager
from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.slice import Slice


class FablibNodeTests(unittest.TestCase):
    """
    Tests for fabrictestbed_extensions.fablib.node.Node.
    """

    def setUp(self):
        self.fablib = FablibManager()

        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        slice_name = f"integration test @ {time_stamp} on {host}"

        self.slice = self.fablib.new_slice(name=slice_name)
        self.node = self.slice.add_node(name="node-1")

        self.assertIsInstance(self.fablib.get_config(), dict)
        self.assertIsInstance(self.slice, Slice)
        self.assertIsInstance(self.node, Node)

        self.slice.submit()

    def tearDown(self):
        self.slice.delete()

    def test_list_networks(self):
        self.assertEqual(self.node.list_networks(), "")
        self.assertEqual(self.node.list_networks(pretty_names=True), "")
        self.assertEqual(self.node.list_networks(pretty_names=False), "")


if __name__ == "__main__":
    unittest.main()
