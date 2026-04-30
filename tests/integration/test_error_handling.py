"""P1 error handling tests — bad inputs and edge cases.

Run with::

    pytest tests/integration/test_error_handling.py -v
    pytest tests/integration -m error -v
"""

import pytest

pytestmark = [pytest.mark.error, pytest.mark.p1, pytest.mark.timeout(300)]


class TestErrorBadSite:
    """Test error handling for invalid site names."""

    def test_nonexistent_site_fails(self, fablib, slice_factory):
        """Submitting a slice with a nonexistent site should raise."""
        s = slice_factory("err-badsite")
        s.add_node(name="node1", site="NONEXISTENT_SITE_XYZ_999")

        with pytest.raises(Exception):
            s.submit()


class TestErrorInsufficientResources:
    """Test error handling for excessive resource requests."""

    def test_excessive_cores_fails(self, fablib, available_site, slice_factory):
        """Requesting more cores than available should fail."""
        s = slice_factory("err-cores")
        s.add_node(name="node1", site=available_site, cores=99999)

        with pytest.raises(Exception):
            s.submit()

    def test_excessive_ram_fails(self, fablib, available_site, slice_factory):
        """Requesting more RAM than available should fail."""
        s = slice_factory("err-ram")
        s.add_node(name="node1", site=available_site, ram=999999)

        with pytest.raises(Exception):
            s.submit()
