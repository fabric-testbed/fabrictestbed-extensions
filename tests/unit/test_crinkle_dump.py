import os
from types import SimpleNamespace

from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleSlice
from fabrictestbed_extensions.fablib.slice import Slice

EMPTY = {"nodes": {}, "networks": {}, "interfaces": {}, "components": {}}


def test_dump_outlives_the_submit_that_wrote_it(monkeypatch, tmp_path):
    """A blocking submit runs post_boot_config, whose save may be rejected
    (e.g. HTTP 413) and fall back to the local dump; that submit must keep the
    dump, and only a later successful submit removes it."""
    s = CrinkleSlice.__new__(CrinkleSlice)
    s.analyzer, s.do_allocate_hosts = object(), False
    s.get_slice_id = lambda: "slice-1"
    s.get_fablib_manager = lambda: SimpleNamespace(get_data_dir=lambda: str(tmp_path))
    s._collect_user_data = lambda: dict(EMPTY)
    save_accepted = False

    def orchestrator_submit(self, post_boot_config=True, **_):
        if post_boot_config:
            self.save_fablib_data()
        elif not save_accepted:
            raise Exception("413 Request Entity Too Large")

    monkeypatch.setattr(Slice, "submit", orchestrator_submit)
    s.submit()
    assert os.path.isfile(s.user_data_dump_path())

    save_accepted = True
    s.submit(post_boot_config=False)
    assert not os.path.isfile(s.user_data_dump_path())


def test_update_keeps_the_dumped_data(monkeypatch, tmp_path):
    """update() replaces the topology with FABRIC's copy, which lacks the
    dumped data; the dump is reapplied, so the next submit still carries it
    before removing the dump."""
    s = CrinkleSlice.__new__(CrinkleSlice)
    s.get_slice_id = lambda: "slice-1"
    s.get_fablib_manager = lambda: SimpleNamespace(get_data_dir=lambda: str(tmp_path))
    dumped = dict(EMPTY, nodes={"C_monitor_l1": {"monitor_config": "args"}})
    s._collect_user_data = lambda: dict(dumped)
    s.dump_user_data_locally()
    topology = {}
    monkeypatch.setattr(Slice, "update", lambda self: topology.clear())
    s._apply_user_data = lambda data: topology.update(data["nodes"])

    s.update()
    assert topology == {"C_monitor_l1": {"monitor_config": "args"}}
