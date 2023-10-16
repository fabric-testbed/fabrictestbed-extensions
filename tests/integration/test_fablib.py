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

import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager


class FablibTests(unittest.TestCase):
    """
    Tests for fabrictestbed_extensions.fablib.fablib class.
    """

    def test_fablib_get_config(self):
        fablib = FablibManager()
        config = fablib.get_config()
        self.assertIsNotNone(config.get("fablib_version"))

    def test_fablib_list_sites(self):
        fablib = FablibManager()
        fablib.list_sites()

    def test_fablib_list_sites_with_fields(self):
        fablib = FablibManager()
        fablib.list_sites(fields=["Name", "ConnectX-5 Available", "NVMe Total"])


if __name__ == "__main__":
    unittest.main()
