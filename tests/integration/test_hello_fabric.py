"""Basic integration test — create a single node and execute a command.

Run with::

    pytest tests/integration/test_hello_fabric.py -v
"""

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.p0]


@pytest.mark.timeout(600)
def test_fablib_hello(fablib, available_site, slice_factory):
    """Create a slice with a single node, and echo a message from the node."""
    s = slice_factory("hello-fabric")
    node_name = "node-1"

    node = s.add_node(name=node_name, site=available_site)
    s.submit()

    for node in s.get_nodes():
        stdout, stderr = node.execute("echo Hello, FABRIC from node `hostname -s`")
        assert stdout == f"Hello, FABRIC from node {node_name}\n"
        assert stderr == ""
