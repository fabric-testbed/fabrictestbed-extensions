"""Unit tests for FabNetv4Ext public IP handling.

A FabNetv4Ext subnet is shared by every slice at a site.  The AM replaces a
requested public IP that another slice already holds, so a node must only be
configured with an address returned by get_public_ips() after submitting;
anything else can take over another experimenter's address.

Uses a mocked FIM network service (with real FIM Labels) to avoid network
access.
"""

import threading
import unittest
import warnings
from ipaddress import IPv4Address, IPv4Network
from unittest.mock import MagicMock

from fabrictestbed.slice_editor import Labels, ServiceType

from fabrictestbed_extensions.fablib.exceptions import ValidationError
from fabrictestbed_extensions.fablib.network_service import NetworkService

SUBNET = IPv4Network("23.134.232.0/24")
GATEWAY = IPv4Address("23.134.232.1")


class FakeFim:
    """Just enough of a FIM network service: a type and settable labels."""

    def __init__(self, ns_type, labels=None):
        self.type = ns_type
        self.labels = labels

    def set_properties(self, labels=None, **kwargs):
        self.labels = labels


def make_network(ns_type=ServiceType.FABNetv4Ext, granted=None, subnet=SUBNET):
    """A NetworkService whose labels say ``granted`` were granted by the AM."""
    labels = Labels(ipv4=[str(ip) for ip in granted]) if granted else None
    ns = NetworkService.__new__(NetworkService)
    ns.fim_network_service = FakeFim(ns_type, labels)
    ns.lock = threading.Lock()
    ns._requested_public_ips = None
    ns._public_ips_pending = False
    ns._public_ip_changes_reported = False
    ns._invalidate_cache = lambda: None
    ns.get_name = lambda: "net1"
    ns.get_subnet = lambda: subnet
    ns.get_gateway = lambda: GATEWAY if subnet else None
    store = {"subnet": {"allocated_ips": []}}
    ns.get_fablib_data = lambda: store
    ns.set_fablib_data = lambda data: store.update(data)
    return ns


def am_grants(ns, granted):
    """Simulate submit + refresh: the AM wrote ``granted`` into the labels."""
    ns._mark_public_ip_request_submitted()
    ns.fim_network_service.labels = Labels(ipv4=[str(ip) for ip in granted])


class TestMakeIpPubliclyRoutable(unittest.TestCase):
    def test_rejects_non_ext_network(self):
        ns = make_network(ns_type=ServiceType.FABNetv4)
        with self.assertRaises(ValidationError):
            ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])

    def test_rejects_wrong_address_family(self):
        ns = make_network()
        with self.assertRaises(ValidationError):
            ns.make_ip_publicly_routable(ipv6=["2001:db8::10"])

    def test_accepts_a_single_string(self):
        ns = make_network()
        self.assertEqual(
            ns.make_ip_publicly_routable(ipv4="23.134.232.10"), ["23.134.232.10"]
        )
        self.assertEqual(ns.fim_network_service.labels.ipv4, ["23.134.232.10"])

    def test_rejects_address_outside_subnet(self):
        ns = make_network()
        with self.assertRaises(ValidationError):
            ns.make_ip_publicly_routable(ipv4=["10.0.0.5"])

    def test_rejects_gateway_network_and_broadcast(self):
        ns = make_network()
        for addr in ("23.134.232.1", "23.134.232.0", "23.134.232.255"):
            with self.assertRaises(ValidationError, msg=addr):
                ns.make_ip_publicly_routable(ipv4=[addr])

    def test_requires_addresses_or_count(self):
        ns = make_network()
        with self.assertRaises(ValidationError):
            ns.make_ip_publicly_routable()

    def test_count_picks_candidates(self):
        ns = make_network()
        self.assertEqual(
            ns.make_ip_publicly_routable(count=2), ["23.134.232.2", "23.134.232.3"]
        )

    def test_count_keeps_already_granted_addresses(self):
        """Asking for more must never release an address already in use."""
        ns = make_network(granted=["23.134.232.40"])
        requested = ns.make_ip_publicly_routable(count=2)
        self.assertEqual(requested[0], "23.134.232.40")
        self.assertEqual(len(requested), 2)


class TestPendingRequest(unittest.TestCase):
    def test_get_public_ips_is_none_until_submitted(self):
        """The request must not masquerade as a grant."""
        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        self.assertIsNone(ns.get_public_ips())

    def test_check_public_ip_rejects_requested_but_unsubmitted(self):
        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        with self.assertRaisesRegex(ValidationError, "pending"):
            ns.check_public_ip("23.134.232.10")


class TestGrantDiffersFromRequest(unittest.TestCase):
    def test_reports_substituted_address(self):
        """The regression: the AM swapped a conflicting IP for a free one."""
        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        am_grants(ns, ["23.134.232.11"])
        self.assertEqual(ns.get_public_ips(), [IPv4Address("23.134.232.11")])
        self.assertEqual(
            ns.get_public_ip_changes(),
            {
                "requested": ["23.134.232.10"],
                "granted": ["23.134.232.11"],
                "not_granted": ["23.134.232.10"],
            },
        )

    def test_no_report_when_granted_as_requested(self):
        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        am_grants(ns, ["23.134.232.10"])
        self.assertIsNone(ns.get_public_ip_changes())

    def test_requested_conflicting_address_cannot_be_configured(self):
        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        am_grants(ns, ["23.134.232.11"])
        with self.assertRaises(ValidationError):
            ns.check_public_ip("23.134.232.10")
        ns.check_public_ip("23.134.232.11")


class TestCheckPublicIp(unittest.TestCase):
    def test_available_ip_is_not_a_public_ip(self):
        """get_available_ips() returns candidates, not addresses we own."""
        ns = make_network(granted=["23.134.232.50"])
        candidate = ns.get_available_ips(count=1)[0]
        with self.assertRaises(ValidationError):
            ns.check_public_ip(candidate)

    def test_no_grant_at_all(self):
        ns = make_network()
        with self.assertRaisesRegex(ValidationError, "make_ip_publicly_routable"):
            ns.check_public_ip("23.134.232.10")

    def test_other_network_types_are_not_restricted(self):
        ns = make_network(ns_type=ServiceType.FABNetv4)
        ns.check_public_ip("23.134.232.10")


class TestAllocateIpOnFabNetv4Ext(unittest.TestCase):
    def test_auto_allocation_uses_only_granted_ips(self):
        ns = make_network(granted=["23.134.232.50", "23.134.232.51"])
        self.assertEqual(ns.allocate_ip(), IPv4Address("23.134.232.50"))
        self.assertEqual(ns.allocate_ip(), IPv4Address("23.134.232.51"))

    def test_auto_allocation_returns_none_when_exhausted(self):
        ns = make_network(granted=["23.134.232.50"])
        ns.allocate_ip()
        self.assertIsNone(ns.allocate_ip())

    def test_explicit_non_granted_address_is_rejected(self):
        ns = make_network(granted=["23.134.232.50"])
        with self.assertRaises(ValidationError):
            ns.allocate_ip(IPv4Address("23.134.232.2"))

    def test_explicit_granted_address_given_as_string(self):
        ns = make_network(granted=["23.134.232.50"])
        self.assertEqual(ns.allocate_ip("23.134.232.50"), IPv4Address("23.134.232.50"))


class TestNodeIpAddrAddGuard(unittest.TestCase):
    def test_refuses_non_granted_address_before_touching_the_node(self):
        from fabrictestbed_extensions.fablib.node import Node

        ns = make_network(granted=["23.134.232.50"])
        iface = MagicMock()
        iface.get_network.return_value = ns
        node = Node.__new__(Node)
        node._get_effective_backend = MagicMock()

        with self.assertRaises(ValidationError):
            node.ip_addr_add(IPv4Address("23.134.232.2"), SUBNET, iface)
        node._get_effective_backend.assert_not_called()


class TestInterfaceAutoMode(unittest.TestCase):
    def test_set_ip_addr_does_not_store_none(self):
        """auto mode used to store the string 'None' when nothing was free."""
        from fabrictestbed_extensions.fablib.interface import Interface

        ns = make_network(granted=["23.134.232.50"])
        ns.allocate_ip()  # the only granted IP is now taken
        iface = Interface.__new__(Interface)
        data = {Interface.MODE: Interface.AUTO}
        iface.get_fablib_data = lambda: data
        iface.set_fablib_data = lambda d: data.update(d)
        iface.get_network = lambda: ns

        iface.set_ip_addr(mode=Interface.AUTO)
        self.assertNotIn(Interface.ADDR, data)


class TestSliceReportsSubstitution(unittest.TestCase):
    def test_warns_when_am_substituted_an_address(self):
        from fabrictestbed_extensions.fablib.slice import Slice

        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        s = Slice.__new__(Slice)
        s.network_services = {"net1": ns}
        s._Slice__public_ip_requests_sent()
        s.update_topology = lambda: am_grants(ns, ["23.134.232.11"])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            s._Slice__report_public_ip_changes()
        messages = [str(w.message) for w in caught]
        self.assertTrue(
            any("23.134.232.10" in m and "23.134.232.11" in m for m in messages),
            messages,
        )

    def test_reports_each_substitution_once(self):
        """A later submit in the same session must not warn again."""
        from fabrictestbed_extensions.fablib.slice import Slice

        ns = make_network()
        ns.make_ip_publicly_routable(ipv4=["23.134.232.10"])
        s = Slice.__new__(Slice)
        s.network_services = {"net1": ns}
        s._Slice__public_ip_requests_sent()
        s.update_topology = MagicMock(
            side_effect=lambda: am_grants(ns, ["23.134.232.11"])
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            s._Slice__report_public_ip_changes()
            s._Slice__report_public_ip_changes()
        self.assertEqual(len(caught), 1)
        self.assertEqual(s.update_topology.call_count, 1)
        # The changes stay queryable after the warning.
        self.assertIsNotNone(ns.get_public_ip_changes())

    def test_silent_when_nothing_requested(self):
        from fabrictestbed_extensions.fablib.slice import Slice

        s = Slice.__new__(Slice)
        s.network_services = {"net1": make_network(granted=["23.134.232.50"])}
        s.update_topology = MagicMock()
        s._Slice__report_public_ip_changes()
        s.update_topology.assert_not_called()


if __name__ == "__main__":
    unittest.main()
