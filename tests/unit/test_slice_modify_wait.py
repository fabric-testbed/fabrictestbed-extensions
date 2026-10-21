"""Unit tests for the modify/resubmit wait path.

A modify request is accepted by the orchestrator before the slice-level
state leaves its pre-modify value, and that pre-modify value (StableOK) is
also what wait()/wait_jupyter() treat as "finished".  Waiting on the state
directly after a modify is therefore a race, and losing it means the caller
gets the pre-modify topology back with no error raised anywhere.

Uses mocked FIM and FablibManager to avoid network access.
"""

import unittest
from unittest.mock import MagicMock


# What modify_slice() returns when the orchestrator has slivers to add or
# modify at an AM.
RESERVATIONS = [{"sliver_id": "s1"}]


class TestWaitForModifyStart(unittest.TestCase):
    """Test Slice.__wait_for_modify_start()."""

    def _make_slice(self, states):
        """A mock Slice whose state walks through ``states`` as it polls."""
        try:
            from fabrictestbed_extensions.fablib.slice import Slice
        except Exception:
            self.skipTest("Cannot import Slice (requires Python 3.10+)")

        s = Slice.__new__(Slice)
        s.fablib_manager = MagicMock()
        s.slice_name = "test-slice"
        s.polls = 0

        def update_slice():
            s.polls += 1

        s.update_slice = update_slice
        s.get_state = lambda: states[min(s.polls, len(states) - 1)]
        return s

    def _wait(self, s, **kwargs):
        kwargs.setdefault("reservations", RESERVATIONS)
        # Name-mangled private method.
        return s._Slice__wait_for_modify_start(**kwargs)

    def test_returns_once_the_state_changes(self):
        s = self._make_slice(["StableOK", "StableOK", "StableOK", "Modifying"])
        state = self._wait(s, previous_state="StableOK", timeout=10, interval=0.01)
        self.assertEqual(state, "Modifying")
        self.assertEqual(s.polls, 3)

    def test_does_not_accept_the_pre_modify_state_as_done(self):
        """The regression: StableOK before == StableOK after."""
        s = self._make_slice(["StableOK", "StableOK", "ModifyOK"])
        state = self._wait(s, previous_state="StableOK", timeout=10, interval=0.01)
        self.assertEqual(state, "ModifyOK")
        self.assertGreater(s.polls, 0)

    def test_detects_a_modify_after_an_unaccepted_previous_modify(self):
        """A prior ModifyOK must not be mistaken for the new modify."""
        s = self._make_slice(["ModifyOK", "ModifyOK", "Modifying"])
        state = self._wait(s, previous_state="ModifyOK", timeout=10, interval=0.01)
        self.assertEqual(state, "Modifying")

    def test_returns_on_a_failed_modify_so_the_caller_can_raise(self):
        s = self._make_slice(["StableOK", "ModifyError"])
        state = self._wait(s, previous_state="StableOK", timeout=10, interval=0.01)
        self.assertEqual(state, "ModifyError")

    def test_times_out_when_the_modify_is_never_picked_up(self):
        from fabrictestbed_extensions.fablib.slice import SliceTimeoutError

        s = self._make_slice(["StableOK"])
        with self.assertRaises(SliceTimeoutError):
            self._wait(s, previous_state="StableOK", timeout=0.05, interval=0.01)

    def test_no_reservations_and_no_state_change_falls_through(self):
        """A user-data-only modify (e.g. saving fablib_data) never changes
        the slice state; it must not wait out the full timeout and fail."""
        s = self._make_slice(["StableOK"])
        s.MODIFY_NO_RESERVATIONS_GRACE = 0.05
        state = self._wait(
            s,
            previous_state="StableOK",
            timeout=1800,
            interval=0.01,
            reservations=[],
            removes_slivers=False,
        )
        self.assertEqual(state, "StableOK")

    def test_no_reservations_but_a_removal_still_times_out(self):
        """A remove-only modify also returns no reservations; falling through
        would let wait() accept the pre-removal StableOK as done."""
        from fabrictestbed_extensions.fablib.slice import SliceTimeoutError

        s = self._make_slice(["StableOK"])
        s.MODIFY_NO_RESERVATIONS_GRACE = 0.05
        with self.assertRaises(SliceTimeoutError):
            self._wait(
                s,
                previous_state="StableOK",
                timeout=0.2,
                interval=0.01,
                reservations=[],
                removes_slivers=True,
            )

    def test_no_reservations_still_waits_for_a_remove_only_modify(self):
        """A remove-only modify returns no reservations but does change state."""
        s = self._make_slice(["StableOK", "StableOK", "Modifying"])
        state = self._wait(
            s,
            previous_state="StableOK",
            timeout=10,
            interval=0.01,
            reservations=[],
        )
        self.assertEqual(state, "Modifying")

    def _removal_slice(self, live, submitted, broken=False):
        s = self._make_slice(["StableOK"])
        s.get_slivers = lambda: [
            MagicMock(sliver_id=rid, state=state) for rid, state in live
        ]

        def element(rid):
            e = MagicMock()
            e.get_property.return_value = MagicMock(reservation_id=rid)
            return e

        topology = MagicMock()
        topology.nodes = {r: element(r) for r in submitted}
        topology.network_services = {}
        topology.facilities = {}
        if broken:
            s.get_fim_topology = MagicMock(side_effect=RuntimeError("boom"))
        else:
            s.get_fim_topology = lambda: topology
        return s._Slice__modify_removes_slivers()

    def test_user_data_only_modify_removes_nothing(self):
        self.assertFalse(
            self._removal_slice([("a", "Active"), ("b", "Active")], ["a", "b"])
        )

    def test_deleted_node_is_a_removal(self):
        self.assertTrue(self._removal_slice([("a", "Active"), ("b", "Active")], ["a"]))

    def test_already_closed_slivers_are_not_a_removal(self):
        self.assertFalse(self._removal_slice([("a", "Active"), ("b", "Closed")], ["a"]))

    def test_undeterminable_removal_is_assumed(self):
        self.assertTrue(self._removal_slice([], [], broken=True))

    def test_unknown_previous_state_does_not_block(self):
        s = self._make_slice(["StableOK"])
        state = self._wait(s, previous_state=None, timeout=10, interval=0.01)
        self.assertEqual(state, "StableOK")
        self.assertEqual(s.polls, 0)


class TestUnprovisionedNetworkAddressing(unittest.TestCase):
    """A network with no resources yet reports "<name>.gateway" / "<name>.subnet"
    placeholders, which routes added before submit (e.g. add_fabnet) store and
    Node.config() resolves to the real addresses after provisioning."""

    def _make_network(self):
        try:
            from fabrictestbed_extensions.fablib.network_service import NetworkService
        except Exception:
            self.skipTest("Cannot import NetworkService (requires Python 3.10+)")

        ns = NetworkService.__new__(NetworkService)
        ns._cached_subnet = None
        ns._cached_gateway = None
        ns.get_fablib_data = lambda: {}  # nothing instantiated, nothing set
        # get_name() must work: the placeholder is built from it.
        ns.get_name = lambda: "meas-net6_IPv6_KANS"
        return ns

    def test_gateway_is_a_placeholder_string(self):
        ns = self._make_network()
        self.assertEqual(ns.get_gateway(), "meas-net6_IPv6_KANS.gateway")

    def test_subnet_is_a_placeholder_string(self):
        ns = self._make_network()
        self.assertEqual(ns.get_subnet(), "meas-net6_IPv6_KANS.subnet")

    def test_available_ips_is_falsy_when_unprovisioned(self):
        ns = self._make_network()
        self.assertFalse(ns.get_available_ips(count=1))


class TestNetworkServiceCacheRefresh(unittest.TestCase):
    """A topology refresh must invalidate cached network service values."""

    def test_existing_network_service_is_updated_not_just_reassigned(self):
        try:
            from fabrictestbed_extensions.fablib.network_service import NetworkService
            from fabrictestbed_extensions.fablib.slice import Slice
        except Exception:
            self.skipTest("Cannot import fablib (requires Python 3.10+)")

        net_type = next(iter(NetworkService.get_fim_network_service_types()))

        fim_net = MagicMock()
        fim_net.get_property.return_value = net_type

        existing = MagicMock()

        s = Slice.__new__(Slice)
        s.fablib_manager = MagicMock()
        s.slice_name = "test-slice"
        s._topology_dirty = True
        s.network_services = {"net1": existing}
        s.get_fim_topology = lambda: MagicMock(network_services={"net1": fim_net})

        s.get_network_services(force_refresh=True)

        # update() invalidates _cached_subnet/_cached_gateway/
        # _cached_reservation_state; a bare attribute assignment does not.
        existing.update.assert_called_once_with(fim_network_service=fim_net)


if __name__ == "__main__":
    unittest.main()
