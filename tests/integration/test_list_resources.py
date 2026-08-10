"""Integration tests for resource listing.

Run with::

    pytest tests/integration/test_list_resources.py -v
"""

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.p0]


def test_list_sites(fablib):
    """Verify site listing returns data."""
    sites = fablib.list_sites(output="json")
    assert sites is not None


def test_list_facility_ports(fablib):
    """Verify facility port listing returns data."""
    facilities = fablib.list_facility_ports(output="json")
    assert facilities is not None
