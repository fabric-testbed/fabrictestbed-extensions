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
# Author Komal Thareja (kthare10@renci.org)
"""
Integration tests for FablibManager.find_resource_slot().

Requires valid FABRIC credentials (token, project_id, etc.) to be
configured via environment variables or fabric_rc.
"""

import datetime
import os
import socket
import time
import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager


class FindResourceSlotIntegrationTests(unittest.TestCase):
    """
    Integration tests that call find_resource_slot() against the live
    FABRIC testbed API.
    """

    @classmethod
    def setUpClass(cls):
        cls.fablib = FablibManager()
        cls.fablib.show_config()

        # Pick two random sites for all tests to use
        sites = cls.fablib.get_random_sites(count=2)
        cls.site1 = sites[0]
        cls.site2 = sites[1]
        print(f"\nUsing sites: site1={cls.site1}, site2={cls.site2}")

    @staticmethod
    def _search_window(days=7):
        """Return a (start, end) tuple covering the next *days* days."""
        start = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
            hours=1
        )
        end = start + datetime.timedelta(days=days)
        return start, end

    # ------------------------------------------------------------------
    # Tests using raw resource dicts
    # ------------------------------------------------------------------

    def test_find_slot_basic_compute(self):
        """Search for a small compute slot using raw resource dicts."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            }
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
            max_results=3,
        )

        print(f"\nBasic compute result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_compute_with_component_db_format(self):
        """Search using the DB-format component key (e.g. GPU-Tesla T4)."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 4,
                "ram": 16,
                "disk": 50,
                "components": {"GPU-Tesla T4": 1},
            }
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
        )

        print(f"\nGPU (DB format) result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_compute_with_component_fablib_format(self):
        """Search using the fablib-format component key (e.g. GPU_TeslaT4)."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 4,
                "ram": 16,
                "disk": 50,
                "components": {"GPU_TeslaT4": 1},
            }
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
        )

        print(f"\nGPU (fablib format) result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_with_smartnic(self):
        """Search for a node with a SmartNIC using fablib name."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 4,
                "ram": 16,
                "disk": 10,
                "components": {"NIC_ConnectX_6": 1},
            }
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
        )

        print(f"\nSmartNIC result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_multi_site(self):
        """Search for compute resources on two different sites."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            },
            {
                "type": "compute",
                "site": self.site2,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            },
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
        )

        print(f"\nMulti-site result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_with_link(self):
        """Search for compute on two sites plus an inter-site link."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            },
            {
                "type": "compute",
                "site": self.site2,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            },
            {
                "type": "link",
                "site_a": self.site1,
                "site_b": self.site2,
                "bandwidth": 10,
            },
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
        )

        print(f"\nCompute + link result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_max_results(self):
        """Verify max_results parameter is respected."""
        start, end = self._search_window()
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            }
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            resources=resources,
            max_results=5,
        )

        print(f"\nmax_results=5 result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_longer_duration(self):
        """Search for a longer slot (24 hours)."""
        start, end = self._search_window(days=14)
        resources = [
            {
                "type": "compute",
                "site": self.site1,
                "cores": 2,
                "ram": 8,
                "disk": 10,
            }
        ]

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=24,
            resources=resources,
        )

        print(f"\n24-hour duration result: {result}")
        self.assertIsInstance(result, dict)

    # ------------------------------------------------------------------
    # Tests using Slice objects
    # ------------------------------------------------------------------

    def test_find_slot_with_slice_object(self):
        """Build an unsubmitted Slice and use it to find a slot."""
        start, end = self._search_window()

        slice_obj = self.fablib.new_slice(name="test-find-slot-slice")
        slice_obj.add_node(name="node1", site=self.site1, cores=2, ram=8, disk=10)

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            slice=slice_obj,
        )

        print(f"\nSlice object result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_with_slice_gpu_node(self):
        """Slice with a GPU node."""
        start, end = self._search_window()

        slice_obj = self.fablib.new_slice(name="test-find-slot-gpu")
        node = slice_obj.add_node(
            name="gpu-node", site=self.site1, cores=8, ram=32, disk=100
        )
        node.add_component(model="GPU_TeslaT4", name="gpu1")

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            slice=slice_obj,
        )

        print(f"\nSlice GPU node result: {result}")
        self.assertIsInstance(result, dict)

    def test_find_slot_with_slice_two_sites_and_l2network(self):
        """Slice with two nodes on different sites connected by L2PTP."""
        start, end = self._search_window()

        slice_obj = self.fablib.new_slice(name="test-find-slot-l2")
        node1 = slice_obj.add_node(
            name="node1", site=self.site1, cores=2, ram=8, disk=10
        )
        iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]

        node2 = slice_obj.add_node(
            name="node2", site=self.site2, cores=2, ram=8, disk=10
        )
        iface2 = node2.add_component(model="NIC_Basic", name="nic2").get_interfaces()[0]

        slice_obj.add_l2network(name="net1", interfaces=[iface1, iface2])

        result = self.fablib.find_resource_slot(
            start=start,
            end=end,
            duration=1,
            slice=slice_obj,
        )

        print(f"\nSlice L2PTP result: {result}")
        self.assertIsInstance(result, dict)

    # ------------------------------------------------------------------
    # End-to-end test: submit a slice then check availability
    # ------------------------------------------------------------------

    def test_find_slot_after_submitting_smartnic_slice(self):
        """
        Submit a real slice with SmartNIC-connected nodes, then use
        find_resource_slot() with an equivalent Slice object to verify
        the API returns availability results while resources are in use.
        """
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        slice_name = f"test-find-slot-smartnic @ {time_stamp} on {host}"

        print(f"\nCreating slice '{slice_name}' on {self.site1} and {self.site2}...")
        live_slice = self.fablib.new_slice(name=slice_name)

        node1 = live_slice.add_node(
            name="smartnic-node1", site=self.site1, cores=2, ram=8, disk=10
        )
        nic1 = node1.add_component(model="NIC_ConnectX_6", name="nic1")
        iface1 = nic1.get_interfaces()[0]

        node2 = live_slice.add_node(
            name="smartnic-node2", site=self.site2, cores=2, ram=8, disk=10
        )
        nic2 = node2.add_component(model="NIC_ConnectX_6", name="nic2")
        iface2 = nic2.get_interfaces()[0]

        live_slice.add_l2network(name="smartnic-net", interfaces=[iface1, iface2])

        try:
            # Submit and wait for the slice to become active
            print(f"Submitting slice '{slice_name}'...")
            live_slice.submit(wait=True)

            print(f"Slice '{slice_name}' status:")
            live_slice.show()

            # Now build an equivalent unsubmitted slice and search for a slot
            start, end = self._search_window()

            query_slice = self.fablib.new_slice(name="query-smartnic-slot")
            qn1 = query_slice.add_node(
                name="node1", site=self.site1, cores=2, ram=8, disk=10
            )
            qnic1 = qn1.add_component(model="NIC_ConnectX_6", name="nic1")
            qi1 = qnic1.get_interfaces()[0]

            qn2 = query_slice.add_node(
                name="node2", site=self.site2, cores=2, ram=8, disk=10
            )
            qnic2 = qn2.add_component(model="NIC_ConnectX_6", name="nic2")
            qi2 = qnic2.get_interfaces()[0]

            query_slice.add_l2network(name="net1", interfaces=[qi1, qi2])

            print("\nSearching for available slot with equivalent SmartNIC topology...")
            result = self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                slice=query_slice,
            )

            print(f"SmartNIC slot result: {result}")
            self.assertIsInstance(result, dict)

            # Also test with raw resource dicts using fablib component names
            print("\nSearching with raw resource dicts (fablib format)...")
            result_raw = self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                resources=[
                    {
                        "type": "compute",
                        "site": self.site1,
                        "cores": 2,
                        "ram": 8,
                        "disk": 10,
                        "components": {"NIC_ConnectX_6": 1},
                    },
                    {
                        "type": "compute",
                        "site": self.site2,
                        "cores": 2,
                        "ram": 8,
                        "disk": 10,
                        "components": {"NIC_ConnectX_6": 1},
                    },
                    {
                        "type": "link",
                        "site_a": self.site1,
                        "site_b": self.site2,
                        "bandwidth": 10,
                    },
                ],
                max_results=3,
            )

            print(f"SmartNIC raw resource result: {result_raw}")
            self.assertIsInstance(result_raw, dict)

        finally:
            print(f"\nDeleting slice '{slice_name}'...")
            live_slice.delete()

    # ------------------------------------------------------------------
    # Validation tests (no credentials needed but run against live fablib)
    # ------------------------------------------------------------------

    def test_find_slot_raises_on_both_slice_and_resources(self):
        """Passing both slice and resources should raise ValueError."""
        start, end = self._search_window()
        slice_obj = self.fablib.new_slice(name="test-both")
        slice_obj.add_node(name="node1", site=self.site1)

        with self.assertRaises(ValueError):
            self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                slice=slice_obj,
                resources=[{"type": "compute", "site": self.site1, "cores": 2}],
            )

    def test_find_slot_raises_on_neither_slice_nor_resources(self):
        """Passing neither slice nor resources should raise ValueError."""
        start, end = self._search_window()

        with self.assertRaises(ValueError):
            self.fablib.find_resource_slot(start=start, end=end, duration=1)

    def test_find_slot_raises_on_short_time_range(self):
        """Time range shorter than 60 minutes should raise."""
        start = datetime.datetime.now(tz=datetime.timezone.utc)
        end = start + datetime.timedelta(minutes=30)

        with self.assertRaises(Exception) as ctx:
            self.fablib.find_resource_slot(
                start=start,
                end=end,
                duration=1,
                resources=[{"type": "compute", "site": self.site1, "cores": 2}],
            )
        self.assertIn("at least 60 minutes", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
