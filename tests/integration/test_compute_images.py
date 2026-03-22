"""P1 compute image tests — verify default image boots correctly.

Run with::

    pytest tests/integration/test_compute_images.py -v
    pytest tests/integration -m compute -v
"""

import pytest

pytestmark = [pytest.mark.compute, pytest.mark.p1, pytest.mark.timeout(900)]


class TestDefaultImage:
    """Test that the default OS image boots and is usable."""

    def test_default_image_boots(self, fablib, available_site, slice_factory):
        """Default image should boot and respond to basic commands."""
        s = slice_factory("default-image")
        s.add_node(name="node1", site=available_site, cores=1, ram=2, disk=10)
        s.submit()

        node = s.get_node(name="node1")

        # Verify OS is running
        stdout, _ = node.execute("cat /etc/os-release | head -1", quiet=True)
        assert "NAME=" in stdout

        # Verify basic tools
        stdout, _ = node.execute("which python3 && which ip && which ping", quiet=True)
        assert "/python3" in stdout
        assert "/ip" in stdout
        assert "/ping" in stdout

    def test_node_metadata(self, fablib, available_site, slice_factory):
        """Verify node properties are populated after submit."""
        s = slice_factory("node-metadata")
        s.add_node(name="node1", site=available_site, cores=2, ram=4, disk=10)
        s.submit()

        node = s.get_node(name="node1")

        assert node.get_reservation_state() == "Active"
        assert node.get_management_ip() is not None
        assert node.get_site() is not None
        assert node.get_image() is not None
