"""Shared fixtures and configuration for FABlib integration tests.

Environment variables:
    FABLIB_TEST_MAX_PARALLEL: Maximum parallel test workers (default: 1)
    FABLIB_TEST_SLICE_PREFIX: Prefix for test slice names (default: "itest")
    FABLIB_TEST_TIMEOUT: Default test timeout in seconds (default: 900)
    FABLIB_TEST_SITE: Force tests to use a specific site
"""

import logging
import os
import socket
import time

import pytest

from fabrictestbed_extensions.fablib.fablib import FablibManager

from .helpers.resource_checker import find_site_with_component

log = logging.getLogger("fablib.integration")


# ─── pytest CLI options ───────────────────────────────────────────────


def pytest_addoption(parser):
    """Add custom CLI options for integration tests."""
    parser.addoption(
        "--max-parallel",
        action="store",
        default=os.environ.get("FABLIB_TEST_MAX_PARALLEL", "1"),
        type=int,
        help="Maximum number of parallel test workers (default: 1)",
    )
    parser.addoption(
        "--fabric-site",
        action="store",
        default=os.environ.get("FABLIB_TEST_SITE", None),
        help="Force tests to use a specific site (default: auto-discover)",
    )
    parser.addoption(
        "--skip-cleanup",
        action="store_true",
        default=False,
        help="Skip slice deletion in teardown (for debugging)",
    )


# ─── Session-scoped fixtures ──────────────────────────────────────────


@pytest.fixture(scope="session")
def fablib():
    """Session-scoped FablibManager instance.

    Shared across all tests to avoid repeated token negotiation.
    """
    fm = FablibManager()
    yield fm


# ─── Slice lifecycle management ───────────────────────────────────────


@pytest.fixture
def slice_factory(fablib, request):
    """Factory fixture that creates slices and guarantees cleanup.

    Usage::

        def test_something(slice_factory):
            s = slice_factory("my-test")
            node = s.add_node(...)
            s.submit()
            # Slice is deleted automatically after the test
    """
    created_slices = []
    skip_cleanup = request.config.getoption("--skip-cleanup", default=False)

    def _create(suffix: str, **kwargs):
        time_stamp = time.strftime("%Y%m%d-%H%M%S")
        host = socket.gethostname()[:10]
        prefix = os.environ.get("FABLIB_TEST_SLICE_PREFIX", "itest")
        name = f"{prefix}-{suffix}-{time_stamp}-{host}"[:100]
        s = fablib.new_slice(name=name, **kwargs)
        created_slices.append(s)
        return s

    yield _create

    for s in created_slices:
        if skip_cleanup:
            log.warning(f"Skipping cleanup for slice: {s.get_name()}")
            continue
        try:
            s.delete()
            log.info(f"Cleaned up slice: {s.get_name()}")
        except Exception as e:
            log.warning(f"Failed to clean up slice {s.get_name()}: {e}")


# ─── Site discovery fixtures ──────────────────────────────────────────


@pytest.fixture
def available_site(fablib, request):
    """Find an available site with basic compute resources.

    Skips the test if no suitable site is found.
    """
    forced_site = request.config.getoption("--fabric-site", default=None)
    if forced_site:
        return forced_site

    try:
        site = fablib.get_random_site(
            filter_function=lambda s: (
                s["cores_available"] >= 2
                and s["ram_available"] >= 8
                and s["disk_available"] >= 10
            ),
        )
        return site
    except Exception:
        pytest.skip("No site with basic compute resources available")


@pytest.fixture
def available_sites_pair(fablib, request):
    """Find two available sites for cross-site tests.

    Returns a tuple of (site1, site2). Skips if unavailable.
    """
    forced_site = request.config.getoption("--fabric-site", default=None)
    if forced_site:
        pytest.skip("Cross-site test skipped when --fabric-site is specified")

    try:
        sites = fablib.get_random_sites(
            count=2,
            filter_function=lambda s: (
                s["cores_available"] >= 2 and s["ram_available"] >= 8
            ),
        )
        if None in sites or len(sites) < 2:
            pytest.skip("Could not find two available sites")
        return tuple(sites)
    except Exception:
        pytest.skip("Could not find two available sites")


@pytest.fixture
def available_sites_trio(fablib, request):
    """Find three available sites for multi-site tests.

    Returns a tuple of (site1, site2, site3). Skips if unavailable.
    """
    try:
        sites = fablib.get_random_sites(
            count=3,
            filter_function=lambda s: (
                s["cores_available"] >= 2 and s["ram_available"] >= 8
            ),
        )
        if None in sites or len(sites) < 3:
            pytest.skip("Could not find three available sites")
        return tuple(sites)
    except Exception:
        pytest.skip("Could not find three available sites")


@pytest.fixture
def available_site_with_shared_nic(fablib, request):
    """Find a site with SharedNIC (NIC_Basic) available."""
    forced_site = request.config.getoption("--fabric-site", default=None)
    if forced_site:
        return forced_site
    site = find_site_with_component(fablib, "nic_basic_available")
    if not site:
        pytest.skip("No site with available SharedNIC found")
    return site


@pytest.fixture
def available_site_with_gpu(fablib):
    """Find a site with at least one GPU available."""
    for key in [
        "tesla_t4_available",
        "rtx6000_available",
        "a30_available",
        "a40_available",
    ]:
        site = find_site_with_component(fablib, key)
        if site:
            return site
    pytest.skip("No site with available GPU found")


@pytest.fixture
def available_site_with_smartnic(fablib):
    """Find a site with at least one dedicated SmartNIC available."""
    for key in ["nic_connectx_6_available", "nic_connectx_5_available"]:
        site = find_site_with_component(fablib, key)
        if site:
            return site
    pytest.skip("No site with available SmartNIC found")


@pytest.fixture
def available_site_with_fpga(fablib):
    """Find a site with FPGA available."""
    site = find_site_with_component(fablib, "fpga_u280_available")
    if not site:
        pytest.skip("No site with available FPGA found")
    return site


@pytest.fixture
def available_site_with_nvme(fablib):
    """Find a site with NVMe available."""
    site = find_site_with_component(fablib, "nvme_available")
    if not site:
        pytest.skip("No site with available NVMe found")
    return site
