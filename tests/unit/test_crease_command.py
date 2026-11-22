import pytest

from fabrictestbed_extensions.fablib.crease.crease_command import build_payload

NOW_NS = 1_700_000_000 * 10**9


def at(seconds):
    return (NOW_NS + int(seconds * 10**9)).to_bytes(8, "big")


@pytest.mark.parametrize(
    "cmd, args, expected",
    [
        ("record", ["2", "4.5"], b"\x01" + at(2) + at(4.5)),
        ("run", ["3"], b"\x04" + at(3)),
        ("clear", [], b"\x02\x00"),
    ],
)
def test_payload_wire_format(cmd, args, expected):
    """The monitor (monitor_source.c TYPE_REPLAY_*) parses these bytes: the
    command type, then big-endian ns epochs."""
    assert build_payload(cmd, NOW_NS, args) == expected
