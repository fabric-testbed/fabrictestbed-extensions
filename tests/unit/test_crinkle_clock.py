from concurrent.futures import Future

import pytest

from fabrictestbed_extensions.fablib.crease import crinkle
from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleSlice

SYNCED = (
    "CLOCK_KERNEL=5.15.0-186-generic\n"
    "CLOCK_PTPDEV=yes\n"
    "CLOCK_SYNC=active\n"
    "CLOCK_OFFSET_NS=-480\n"
)
# A kernel without linux-modules-extra after the monitor reboot.
NO_DEVICE = (
    "CLOCK_KERNEL=5.15.0-204-generic\n"
    "CLOCK_PTPDEV=no\n"
    "CLOCK_SYNC=failed\n"
    "FileNotFoundError: [Errno 2] No such file or directory: '/dev/ptp_kvm'\n"
)


@pytest.mark.parametrize(
    "output, ok",
    [
        (SYNCED, True),
        (SYNCED.replace("CLOCK_PTPDEV=yes", "CLOCK_PTPDEV=no"), False),
        (SYNCED.replace("active", "inactive"), False),
        (SYNCED.replace("-480", str(crinkle.CLOCK_SYNC_TOLERANCE_NS + 1)), False),
        (None, False),
    ],
    ids=["synced", "no-device", "phc2sys-down", "offset-too-large", "no-output"],
)
def test_parse_clock_check(output, ok):
    assert CrinkleSlice.parse_clock_check(output)["ok"] is ok


class FakeNode:
    def __init__(self, name, checks):
        self.name, self.checks, self.commands = name, list(checks), []

    def get_name(self):
        return self.name

    def execute_thread(self, cmd):
        self.commands.append(cmd)
        out = self.checks.pop(0) if cmd == crinkle.CLOCK_CHECK_CMD else ""
        future = Future()
        future.set_result((out, ""))
        return future


def test_check_clock_sync_repairs_and_reports(monkeypatch, capsys):
    """Only nodes still failing after the settle wait are repaired (a clock
    converging after the reboot is left alone), a node still failing after
    the repair is reported, and nodes setup_ptp skipped (sites without PTP)
    are not checked."""
    monkeypatch.setattr(crinkle.time, "sleep", lambda seconds: None)
    converging = SYNCED.replace("-480", str(crinkle.CLOCK_SYNC_TOLERANCE_NS + 1))
    good = FakeNode("good", [SYNCED])
    settling = FakeNode("settling", [converging, SYNCED])
    fixed = FakeNode("fixed", [NO_DEVICE, NO_DEVICE, SYNCED])
    broken = FakeNode("broken", [NO_DEVICE, NO_DEVICE, NO_DEVICE])
    skipped = FakeNode("skipped", [])
    s = CrinkleSlice.__new__(CrinkleSlice)
    s.analyzer = good
    s.monitors = {n.get_name(): n for n in (settling, fixed, broken, skipped)}
    s.ptp_nodes = ["good", "settling", "fixed", "broken"]

    status = s.check_clock_sync()

    assert {k: v["ok"] for k, v in status.items()} == {
        "good": True,
        "settling": True,
        "fixed": True,
        "broken": False,
    }

    def repaired(node):
        return any(cmd != crinkle.CLOCK_CHECK_CMD for cmd in node.commands)

    assert not repaired(good) and not repaired(settling)
    assert repaired(fixed) and repaired(broken)
    assert skipped.commands == []
    assert "broken" in capsys.readouterr().out
