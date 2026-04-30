"""P1 slice modification tests.

Run with::

    pytest tests/integration/test_lifecycle_modify.py -v
    pytest tests/integration -m lifecycle -v
"""

import pytest

pytestmark = [
    pytest.mark.lifecycle,
    pytest.mark.p1,
    pytest.mark.slow,
    pytest.mark.timeout(1200),
]


class TestSliceModify:
    """Test adding nodes/networks to an existing slice."""

    def test_modify_add_node(self, fablib, available_site, slice_factory):
        """Submit a slice with 1 node, then modify to add a second."""
        s = slice_factory("modify-add-node")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        assert len(s.get_nodes()) == 1

        # Modify: add a second node
        s.add_node(name="node2", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        assert len(s.get_nodes()) == 2
        node2 = s.get_node(name="node2")
        stdout, _ = node2.execute("echo modified_ok", quiet=True)
        assert "modified_ok" in stdout
