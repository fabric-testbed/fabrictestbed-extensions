import os
import re

from fabrictestbed_extensions.fablib.crease import crinkle
from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleMonitor


def test_monitor_data_mappings_are_per_monitor():
    """Each monitor gets its own iface_mappings."""
    first, second = CrinkleMonitor.MonitorData(), CrinkleMonitor.MonitorData()
    first.iface_mappings["h1-e0"] = ("h1", None, False, 1)
    assert second.iface_mappings == {}


def test_monitor_url_matches_source_version():
    """The downloaded binary is the hosted build of this version of
    monitor_source.c."""
    with open(os.path.join(crinkle.CREASEDIR, "monitor_source.c")) as f:
        version = re.search(r'CREASEVER "Crease Monitor v([\d.]+)', f.read()).group(1)
    assert version == crinkle.MONITOR_VERSION
    assert crinkle.MONITORURL.endswith(f"v{version}")
