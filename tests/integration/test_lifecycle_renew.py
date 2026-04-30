"""P1 slice renew tests.

Run with::

    pytest tests/integration/test_lifecycle_renew.py -v
    pytest tests/integration -m lifecycle -v
"""

import pytest

pytestmark = [pytest.mark.lifecycle, pytest.mark.p1, pytest.mark.timeout(900)]


class TestSliceRenew:
    """Test slice lease renewal."""

    def test_renew_by_days(self, fablib, available_site, slice_factory):
        """Renew a slice by specifying days and verify lease extended."""
        s = slice_factory("renew-days")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        original_end = s.get_lease_end()
        s.renew(days=1)
        new_end = s.get_lease_end()

        assert (
            new_end > original_end
        ), f"Expected new lease end {new_end} > original {original_end}"
