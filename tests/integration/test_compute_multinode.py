"""P1 multi-node compute tests.

Run with::

    pytest tests/integration/test_compute_multinode.py -v
    pytest tests/integration -m compute -v
"""

import pytest

pytestmark = [pytest.mark.compute, pytest.mark.p1, pytest.mark.timeout(900)]


class TestMultiNode:
    """Test multi-node slice creation and parallel SSH."""

    def test_three_node_cluster(self, fablib, available_site, slice_factory):
        """Create a 3-node cluster and verify all nodes are reachable."""
        s = slice_factory("multinode-3")
        for i in range(3):
            s.add_node(name=f"node{i}", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        nodes = s.get_nodes()
        assert len(nodes) == 3

        for node in nodes:
            stdout, stderr = node.execute("hostname -s", quiet=True)
            assert len(stdout.strip()) > 0
            assert stderr == ""

    def test_parallel_execute_threads(self, fablib, available_site, slice_factory):
        """Verify execute_thread works for parallel SSH across nodes."""
        s = slice_factory("parallel-ssh")
        for i in range(2):
            s.add_node(name=f"node{i}", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        threads = {}
        for node in s.get_nodes():
            t = node.execute_thread("echo done-$(hostname -s)")
            threads[node.get_name()] = t

        for name, t in threads.items():
            stdout, stderr = t.result()
            assert "done-" in stdout
