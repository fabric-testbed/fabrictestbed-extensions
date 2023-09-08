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

import unittest

from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.slice import Slice


class HelloFabricTests(unittest.TestCase):
    """
    Run some basic tests against the testbed.
    """

    def test_fablib_hello(self, fablib, fabric_slice):
        """
        Create a slice with a single node, and echo a message from the node.
        """
        self.assertIsInstance(fabric_slice, Slice)

        # Add a node.
        node_name = "node-1"
        site_name = fablib.get_random_site()
        slice_name = fabric_slice.get_name()

        print(
            f"Adding node '{node_name}' at site '{site_name}' to slice '{slice_name}'.."
        )
        node = fabric_slice.add_node(name=node_name, site=site_name)

        self.assertIsInstance(node, Node)

        # Submit the slice.
        print(f"Submitting slice '{slice_name}'..")
        fabric_slice.submit()

        print(f"Slice '{slice_name}' status:")
        fabric_slice.show()

        print(f"Testing node '{node_name}' on slice '{slice_name}'...")

        for node in fabric_slice.get_nodes():
            stdout, stderr = node.execute("echo Hello, FABRIC from node `hostname -s`")

            self.assertEqual(stdout, f"Hello, FABRIC from node {node_name}\n")
            self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
