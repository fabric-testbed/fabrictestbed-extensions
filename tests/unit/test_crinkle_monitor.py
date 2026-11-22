from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleMonitor


def test_monitor_data_mappings_are_per_monitor():
    """Each monitor gets its own iface_mappings."""
    first, second = CrinkleMonitor.MonitorData(), CrinkleMonitor.MonitorData()
    first.iface_mappings["h1-e0"] = ("h1", None, False, 1)
    assert second.iface_mappings == {}
