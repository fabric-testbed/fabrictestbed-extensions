"""Integration tests for FablibManager.find_resource_slot().

Requires valid FABRIC credentials (token, project_id, etc.) to be
configured via environment variables or fabric_rc.

Run with::

    pytest tests/integration/test_find_resource_slot.py -v
"""

import datetime

import pytest

pytestmark = [pytest.mark.compute, pytest.mark.p1]


def _search_window(days=7):
    """Return a (start, end) tuple covering the next *days* days."""
    start = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
        hours=1
    )
    end = start + datetime.timedelta(days=days)
    return start, end


@pytest.fixture(scope="module")
def two_sites(fablib):
    """Pick two random sites for all tests in this module."""
    sites = fablib.get_random_sites(count=2)
    if None in sites or len(sites) < 2:
        pytest.skip("Could not find two available sites")
    return sites[0], sites[1]


# ------------------------------------------------------------------
# Tests using raw resource dicts
# ------------------------------------------------------------------


class TestFindSlotRawResources:
    """Test find_resource_slot() with raw resource dicts."""

    def test_basic_compute(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[{"type": "compute", "site": site1, "cores": 2, "ram": 8, "disk": 10}],
            max_results=3,
        )
        assert isinstance(result, dict)

    def test_compute_with_gpu_db_format(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[{
                "type": "compute", "site": site1, "cores": 4, "ram": 16, "disk": 50,
                "components": {"GPU-Tesla T4": 1},
            }],
        )
        assert isinstance(result, dict)

    def test_compute_with_gpu_fablib_format(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[{
                "type": "compute", "site": site1, "cores": 4, "ram": 16, "disk": 50,
                "components": {"GPU_TeslaT4": 1},
            }],
        )
        assert isinstance(result, dict)

    def test_with_smartnic(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[{
                "type": "compute", "site": site1, "cores": 4, "ram": 16, "disk": 10,
                "components": {"NIC_ConnectX_6": 1},
            }],
        )
        assert isinstance(result, dict)

    def test_multi_site(self, fablib, two_sites):
        start, end = _search_window()
        site1, site2 = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[
                {"type": "compute", "site": site1, "cores": 2, "ram": 8, "disk": 10},
                {"type": "compute", "site": site2, "cores": 2, "ram": 8, "disk": 10},
            ],
        )
        assert isinstance(result, dict)

    def test_with_link(self, fablib, two_sites):
        start, end = _search_window()
        site1, site2 = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[
                {"type": "compute", "site": site1, "cores": 2, "ram": 8, "disk": 10},
                {"type": "compute", "site": site2, "cores": 2, "ram": 8, "disk": 10},
                {"type": "link", "site_a": site1, "site_b": site2, "bandwidth": 10},
            ],
        )
        assert isinstance(result, dict)

    def test_max_results(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=1,
            resources=[{"type": "compute", "site": site1, "cores": 2, "ram": 8, "disk": 10}],
            max_results=5,
        )
        assert isinstance(result, dict)

    def test_longer_duration(self, fablib, two_sites):
        start, end = _search_window(days=14)
        site1, _ = two_sites
        result = fablib.find_resource_slot(
            start=start, end=end, duration=24,
            resources=[{"type": "compute", "site": site1, "cores": 2, "ram": 8, "disk": 10}],
        )
        assert isinstance(result, dict)


# ------------------------------------------------------------------
# Tests using Slice objects
# ------------------------------------------------------------------


class TestFindSlotWithSlice:
    """Test find_resource_slot() with Slice objects."""

    def test_with_slice_object(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites

        slice_obj = fablib.new_slice(name="test-find-slot-slice")
        slice_obj.add_node(name="node1", site=site1, cores=2, ram=8, disk=10)

        result = fablib.find_resource_slot(
            start=start, end=end, duration=1, slice=slice_obj,
        )
        assert isinstance(result, dict)

    def test_with_gpu_node(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites

        slice_obj = fablib.new_slice(name="test-find-slot-gpu")
        node = slice_obj.add_node(
            name="gpu-node", site=site1, cores=8, ram=32, disk=100
        )
        node.add_component(model="GPU_TeslaT4", name="gpu1")

        result = fablib.find_resource_slot(
            start=start, end=end, duration=1, slice=slice_obj,
        )
        assert isinstance(result, dict)

    def test_with_two_sites_and_l2network(self, fablib, two_sites):
        start, end = _search_window()
        site1, site2 = two_sites

        slice_obj = fablib.new_slice(name="test-find-slot-l2")
        node1 = slice_obj.add_node(name="node1", site=site1, cores=2, ram=8, disk=10)
        iface1 = node1.add_component(model="NIC_Basic", name="nic1").get_interfaces()[0]

        node2 = slice_obj.add_node(name="node2", site=site2, cores=2, ram=8, disk=10)
        iface2 = node2.add_component(model="NIC_Basic", name="nic2").get_interfaces()[0]

        slice_obj.add_l2network(name="net1", interfaces=[iface1, iface2])

        result = fablib.find_resource_slot(
            start=start, end=end, duration=1, slice=slice_obj,
        )
        assert isinstance(result, dict)


# ------------------------------------------------------------------
# End-to-end test: submit a slice then check availability
# ------------------------------------------------------------------


@pytest.mark.timeout(900)
def test_find_slot_after_submitting_smartnic_slice(
    fablib, two_sites, slice_factory
):
    """Submit a real SmartNIC slice, then search for equivalent availability."""
    site1, site2 = two_sites
    s = slice_factory("find-slot-smartnic")

    node1 = s.add_node(name="smartnic-node1", site=site1, cores=2, ram=8, disk=10)
    nic1 = node1.add_component(model="NIC_ConnectX_6", name="nic1")
    iface1 = nic1.get_interfaces()[0]

    node2 = s.add_node(name="smartnic-node2", site=site2, cores=2, ram=8, disk=10)
    nic2 = node2.add_component(model="NIC_ConnectX_6", name="nic2")
    iface2 = nic2.get_interfaces()[0]

    s.add_l2network(name="smartnic-net", interfaces=[iface1, iface2])
    s.submit(wait=True)

    # Now search for equivalent resources
    start, end = _search_window()

    query_slice = fablib.new_slice(name="query-smartnic-slot")
    qn1 = query_slice.add_node(name="node1", site=site1, cores=2, ram=8, disk=10)
    qi1 = qn1.add_component(model="NIC_ConnectX_6", name="nic1").get_interfaces()[0]

    qn2 = query_slice.add_node(name="node2", site=site2, cores=2, ram=8, disk=10)
    qi2 = qn2.add_component(model="NIC_ConnectX_6", name="nic2").get_interfaces()[0]

    query_slice.add_l2network(name="net1", interfaces=[qi1, qi2])

    result = fablib.find_resource_slot(
        start=start, end=end, duration=1, slice=query_slice,
    )
    assert isinstance(result, dict)

    # Also test with raw resource dicts
    result_raw = fablib.find_resource_slot(
        start=start, end=end, duration=1,
        resources=[
            {"type": "compute", "site": site1, "cores": 2, "ram": 8, "disk": 10,
             "components": {"NIC_ConnectX_6": 1}},
            {"type": "compute", "site": site2, "cores": 2, "ram": 8, "disk": 10,
             "components": {"NIC_ConnectX_6": 1}},
            {"type": "link", "site_a": site1, "site_b": site2, "bandwidth": 10},
        ],
        max_results=3,
    )
    assert isinstance(result_raw, dict)


# ------------------------------------------------------------------
# Validation tests
# ------------------------------------------------------------------


class TestFindSlotValidation:
    """Validation tests — these run against live fablib but don't create slices."""

    def test_raises_on_both_slice_and_resources(self, fablib, two_sites):
        start, end = _search_window()
        site1, _ = two_sites
        slice_obj = fablib.new_slice(name="test-both")
        slice_obj.add_node(name="node1", site=site1)

        with pytest.raises(ValueError):
            fablib.find_resource_slot(
                start=start, end=end, duration=1,
                slice=slice_obj,
                resources=[{"type": "compute", "site": site1, "cores": 2}],
            )

    def test_raises_on_neither_slice_nor_resources(self, fablib):
        start, end = _search_window()
        with pytest.raises(ValueError):
            fablib.find_resource_slot(start=start, end=end, duration=1)

    def test_raises_on_short_time_range(self, fablib, two_sites):
        site1, _ = two_sites
        start = datetime.datetime.now(tz=datetime.timezone.utc)
        end = start + datetime.timedelta(minutes=30)

        with pytest.raises(Exception, match="at least 60 minutes"):
            fablib.find_resource_slot(
                start=start, end=end, duration=1,
                resources=[{"type": "compute", "site": site1, "cores": 2}],
            )
