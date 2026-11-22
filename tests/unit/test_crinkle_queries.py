import copy
from types import SimpleNamespace

import pytest

from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleSlice

LINKS = {
    "lA": ["h1-e0", "r1-e0"],
    "lB": ["r1-e1", "h2-e0"],
}


def obs(tx_interface, epoch):
    return {
        "tx_host": tx_interface.split("-")[0],
        "tx_interface": tx_interface,
        "rx_host": "",
        "rx_interface": "",
        "size": "64",
        "epoch": str(epoch),
        "time": f"t{float(epoch):08.3f}",
        "ip.src": "10.0.0.1",
        "ip.dst": "10.0.0.2",
    }


def make_slice(prov):
    slice = CrinkleSlice.__new__(CrinkleSlice)
    slice.monitors = {
        name: SimpleNamespace(
            data=SimpleNamespace(iface_mappings={iface: None for iface in ifaces})
        )
        for name, ifaces in LINKS.items()
    }
    slice.dump_provenance = lambda **query: copy.deepcopy(prov)
    return slice


def test_missing_frames_reports_both_directions():
    slice = make_slice(
        {
            "both": [obs("h1-e0", 1.0), obs("r1-e1", 1.1)],
            "only_a": [obs("h1-e0", 2.0)],
            "only_b": [obs("r1-e1", 0.5)],
        }
    )
    missing = slice.dump_missing_frames("lA", "lB")
    assert list(missing) == ["only_b", "only_a"]
    assert missing["only_a"]["link"] == "lA"
    assert missing["only_a"]["missing_link"] == "lB"
    assert missing["only_b"]["missing_link"] == "lA"


def test_reordered_frames_flags_only_overtaking_frames():
    slice = make_slice(
        {
            "first": [obs("h1-e0", 1.0), obs("r1-e1", 1.3)],
            "second": [obs("h1-e0", 1.1), obs("r1-e1", 1.2)],
            "third": [obs("h1-e0", 1.2), obs("r1-e1", 1.4)],
            # Travels lB to lA (an acknowledgement): not part of the ordering.
            "reply": [obs("r1-e1", 1.25), obs("h1-e0", 1.35)],
        }
    )
    reordered = slice.dump_reordered_frames("lA", "lB")
    assert list(reordered) == ["second"]
    assert reordered["second"]["l1_position"] == 1
    assert reordered["second"]["l2_position"] == 0


def test_reordering_resolves_nanoseconds():
    """Frames of one RX burst are stamped 1 ns apart; ordering keeps that."""
    t = "1700000000.00000000"
    slice = make_slice(
        {
            "first": [obs("h1-e0", t + "1"), obs("r1-e1", t + "4")],
            "second": [obs("h1-e0", t + "2"), obs("r1-e1", t + "3")],
        }
    )
    assert list(slice.dump_reordered_frames("lA", "lB")) == ["second"]


def test_delay_gt_is_strict_and_uses_first_observations():
    slice = make_slice(
        {
            "slow": [obs("h1-e0", 1.0), obs("r1-e1", 1.5), obs("r1-e1", 9.0)],
            "at_threshold": [obs("h1-e0", 2.0), obs("r1-e1", 2.25)],
            "slower": [obs("h1-e0", 3.0), obs("r1-e1", 4.0)],
        }
    )
    delayed = slice.dump_delay_gt("lA", "lB", 0.25)
    assert list(delayed) == ["slower", "slow"]
    assert delayed["slow"]["delay"] == pytest.approx(0.5)


def test_path_of_link_starts_at_first_observation_on_link():
    slice = make_slice(
        {
            "through": [obs("h2-e0", 0.5), obs("r1-e0", 1.0), obs("r1-e1", 1.1)],
            "elsewhere": [obs("h2-e0", 2.0)],
        }
    )
    paths = slice.dump_path_of(link="lA")
    assert list(paths) == ["through"]
    assert [hop["link"] for hop in paths["through"]] == ["lA", "lB"]
    for bad in ({}, {"pkt_id": "through", "link": "lA"}):
        with pytest.raises(Exception, match="Exactly one of pkt_id or link"):
            slice.dump_path_of(**bad)


def test_state_when_window_is_inclusive_and_per_link():
    slice = make_slice(
        {
            "target": [obs("h1-e0", 10.0), obs("r1-e1", 20.0)],
            "before_edge": [obs("h1-e0", 9.0)],
            "after_edge": [obs("r1-e1", 22.0)],
            "outside": [obs("h1-e0", 8.9), obs("r1-e1", 22.1)],
            "wrong_link": [obs("r1-e1", 10.0)],
        }
    )
    state = slice.dump_state_when("target", before=1.0, after=2.0)
    assert set(state) == {"before_edge", "after_edge"}
    assert state["before_edge"][0]["offset"] == pytest.approx(-1.0)
    assert state["after_edge"][0]["link"] == "lB"


def test_unknown_link_rejected():
    slice = make_slice({})
    with pytest.raises(Exception, match="not a monitored link"):
        slice.dump_missing_frames("lA", "nope")
