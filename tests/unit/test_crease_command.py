import pytest

from fabrictestbed_extensions.fablib.crease import crinkle
from fabrictestbed_extensions.fablib.crease.crease_command import build_payload
from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleSlice

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


def test_replay_commands_the_monitor_would_ignore_raise(monkeypatch):
    """Monitors silently drop a run sent while the recording window is open,
    and a clear or run sent while a replay runs. Those calls raise, and succeed
    once the window or replay is over. A run after a clear raises too. A
    recording starts by clearing the previous one."""
    clock = [1000.0]
    monkeypatch.setattr(crinkle.time, "monotonic", lambda: clock[0])
    sent = []
    s = CrinkleSlice.__new__(CrinkleSlice)
    s._send_crease_commands = lambda *commands: sent.append(commands)
    s.record_replay(start_offset=1.0, end_offset=3.0)
    assert sent == [(("clear", []), ("record", [1.0, 3.0]))]
    with pytest.raises(Exception, match="recording window closes"):
        s.run_replay()
    clock[0] += 3.0
    s.run_replay(start_offset=2.0)
    clock[0] += 2.0 + 2.0
    for call in (s.clear_replay, s.run_replay, s.record_replay):
        with pytest.raises(Exception, match="replay may still be running"):
            call()
    clock[0] += crinkle.REPLAY_LATE_MARGIN_S
    s.clear_replay()
    assert [cmd for cmd, _ in sent[-1]] == ["clear"]
    with pytest.raises(Exception, match="recording was cleared"):
        s.run_replay()
