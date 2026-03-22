"""P1 slice state transition tests.

Run with::

    pytest tests/integration/test_lifecycle_states.py -v
    pytest tests/integration -m lifecycle -v
"""

import pytest

pytestmark = [pytest.mark.lifecycle, pytest.mark.p1, pytest.mark.timeout(900)]


class TestSliceStates:
    """Test slice state transitions."""

    def test_stable_ok_after_submit(self, fablib, available_site, slice_factory):
        """Verify slice reaches StableOK after successful submit."""
        s = slice_factory("states-ok")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        state = s.get_state()
        assert state in ("StableOK", "ModifyOK"), f"Unexpected state: {state}"

    def test_delete_removes_slice(self, fablib, available_site, slice_factory):
        """Verify deleting an active slice makes it unretrievable."""
        s = slice_factory("states-delete")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        slice_name = s.get_name()
        s.delete()

        # After deletion, getting the same slice should fail
        with pytest.raises(Exception):
            fablib.get_slice(name=slice_name)

    def test_is_stable_true_after_submit(self, fablib, available_site, slice_factory):
        """Verify isStable() returns True after successful submit."""
        s = slice_factory("states-stable")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        assert s.isStable() is True
