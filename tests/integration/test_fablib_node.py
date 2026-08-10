"""Integration tests for fabrictestbed_extensions.fablib.node.Node.

Run with::

    pytest tests/integration/test_fablib_node.py -v
"""

import pytest

pytestmark = [pytest.mark.compute, pytest.mark.p1]


@pytest.mark.timeout(600)
def test_node_list_networks(fablib, available_site, slice_factory):
    """A node with no networks should have an empty network list."""
    s = slice_factory("node-networks")
    s.add_node(name="node-1", site=available_site, cores=1, ram=2, disk=10)
    s.submit()

    node = s.get_node(name="node-1")
    assert len(node.get_networks()) == 0
