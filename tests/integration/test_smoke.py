"""P0 Smoke tests — must pass for the library to be considered operational.

Run with::

    pytest tests/integration/test_smoke.py -v
    pytest tests/integration -m smoke -v
"""

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.p0]


class TestSmokeConnectivity:
    """Verify basic FABRIC API connectivity (no slices created)."""

    def test_smoke_list_sites(self, fablib):
        """Verify we can list sites from the testbed."""
        names = fablib.get_site_names()
        assert len(names) > 0, "Expected at least one site"

    def test_smoke_get_random_site(self, fablib):
        """Verify random site selection works."""
        site = fablib.get_random_site()
        assert site is not None
        assert isinstance(site, str)
        assert len(site) > 0

    def test_smoke_get_available_resources(self, fablib):
        """Verify resource listing returns data."""
        sites = fablib.list_sites(output="list", quiet=True)
        assert len(sites) > 0
        # Each site should have a name and state
        for s in sites[:3]:
            assert "name" in s
            assert "state" in s

    def test_smoke_get_config(self, fablib):
        """Verify configuration is accessible."""
        config = fablib.get_config()
        assert isinstance(config, dict)
        assert len(config) > 0


class TestSmokeSliceLifecycle:
    """Verify single-node slice create/execute/delete cycle."""

    @pytest.mark.timeout(600)
    def test_smoke_single_node_lifecycle(self, fablib, available_site, slice_factory):
        """Create a single node, execute a command, verify output, delete."""
        s = slice_factory("smoke-lifecycle")
        node = s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        # Re-fetch node after submit to get reservation state
        node = s.get_node(name="node1")
        assert node.get_reservation_state() == "Active"

        stdout, stderr = node.execute("echo SMOKE_TEST_OK", quiet=True)
        assert "SMOKE_TEST_OK" in stdout

    @pytest.mark.timeout(600)
    def test_smoke_get_existing_slice(self, fablib, available_site, slice_factory):
        """Verify we can retrieve a slice by name after creating it."""
        s = slice_factory("smoke-get")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        retrieved = fablib.get_slice(name=s.get_name())
        assert retrieved is not None
        assert retrieved.get_name() == s.get_name()
        assert retrieved.get_state() in ("StableOK", "ModifyOK")

    @pytest.mark.timeout(600)
    def test_smoke_ssh_connection_reuse(self, fablib, available_site, slice_factory):
        """Verify SSH connection pooling — multiple commands reuse connection."""
        s = slice_factory("smoke-ssh-pool")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        node = s.get_node(name="node1")

        # First command creates the connection
        stdout1, _ = node.execute("echo cmd1", quiet=True)
        assert "cmd1" in stdout1

        # Second command should reuse the cached connection
        stdout2, _ = node.execute("echo cmd2", quiet=True)
        assert "cmd2" in stdout2

        # Third command
        stdout3, _ = node.execute("hostname -s", quiet=True)
        assert len(stdout3.strip()) > 0

        # Explicitly close
        node.close_ssh()

        # After close, next command should create a fresh connection
        stdout4, _ = node.execute("echo after_close", quiet=True)
        assert "after_close" in stdout4
