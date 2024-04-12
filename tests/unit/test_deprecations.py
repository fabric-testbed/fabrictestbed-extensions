#!/usr/bin/env python3
#
# MIT License
#
# Copyright (c) 2024 FABRIC Testbed
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

from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.node import Node


class FablibDeprecationTests(unittest.TestCase):
    """
    Test that deprecation warnings are emitted.
    """

    def test_interface_deprecations(self):
        """
        Test DeprecationWarnings from Interface module.
        """
        with self.assertWarns(DeprecationWarning):
            Interface().get_os_interface()

    def test_node_deprecations(self):
        """
        Test DeprecationWarnings from Node module.
        """
        with self.assertWarns(DeprecationWarning):
            try:
                Node(slice=None, node=None).set_ip_os_interface()
            except Exception:
                pass

        with self.assertWarns(DeprecationWarning):
            try:
                Node(slice=None, node=None).add_vlan_os_interface()
            except Exception:
                pass
