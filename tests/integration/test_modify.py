"""Integration tests for slice modify operations.

Tests L2 + L3 network configuration with and without modify.

Run with::

    pytest tests/integration/test_modify.py -v
"""

import logging

import pytest
from ipaddress import IPv4Network

pytestmark = [pytest.mark.lifecycle, pytest.mark.p1]


class TestModifySlice:
    """Tests for slice modification with L2/L3 networks."""

    @pytest.mark.timeout(1200)
    def test_modify_add_l2_l3_nodes(
        self, fablib, available_sites_trio, slice_factory
    ):
        """Add nodes with L2 network, submit, add a third node with L3, resubmit."""
        site1, site2, site3 = available_sites_trio
        s = slice_factory("modify-l2-l3")

        self._add_l2(s, site1, site2)
        s.submit()

        logging.info("@@@@@@@@@@@@@@@ BEGIN MODIFY @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

        self._add_l3(s, site1, site2, site3)
        s.submit()

        logging.info("############### END MODIFY #################################")

        self._check_interfaces(s)

    @pytest.mark.timeout(900)
    def test_no_modify_l2_l3_nodes(
        self, fablib, available_sites_trio, slice_factory
    ):
        """Add nodes with L2 and L3 networks, then submit once."""
        site1, site2, site3 = available_sites_trio
        s = slice_factory("no-modify-l2-l3")

        self._add_l2(s, site1, site2)
        self._add_l3(s, site1, site2, site3)
        s.submit()

        self._check_interfaces(s)

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _add_l2(s, site1, site2):
        """Add an L2 network with two nodes."""
        l2_net = s.add_l2network(
            name="net-L2", subnet=IPv4Network("192.168.1.0/24")
        )

        for site in [site1, site2]:
            node = s.add_node(name=f"node-{site}", site=site)
            iface = node.add_component(
                model="NIC_Basic", name=f"nic-L2-{site}"
            ).get_interfaces()[0]
            iface.set_mode("auto")
            l2_net.add_interface(iface)

    @staticmethod
    def _add_l3(s, site1, site2, site3):
        """Add L3 networking to existing nodes and a new node."""
        for site in [site1, site2]:
            node = s.get_node(name=f"node-{site}")
            iface = node.add_component(
                model="NIC_Basic", name=f"nic-L3-{site}"
            ).get_interfaces()[0]
            iface.set_mode("auto")

            l3_net = s.add_l3network(name=f"net-L3-{site}", type="IPv4")
            l3_net.add_interface(iface)

        # New node at site3
        node3 = s.add_node(name=f"node-L3-{site3}", site=site3)
        iface3 = node3.add_component(
            model="NIC_Basic", name=f"nic-L3-{site3}"
        ).get_interfaces()[0]
        iface3.set_mode("auto")

        l3_net3 = s.add_l3network(name=f"net-L3-{site3}", type="IPv4")
        l3_net3.add_interface(iface3)

    @staticmethod
    def _check_interfaces(s):
        """Verify all interfaces have IP addresses."""
        ifaces = s.get_interfaces()
        errors = [
            f"iface {iface.get_name()} has no IP address"
            for iface in ifaces
            if iface.get_ip_addr() is None
        ]
        assert errors == [], f"Interfaces missing IPs: {errors}"
