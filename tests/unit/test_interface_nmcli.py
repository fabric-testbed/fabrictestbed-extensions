"""Regression tests for the single-round-trip nmcli configuration. The command
that Interface._config_nmcli sends runs in bash against a stub nmcli, so the
tests see the nmcli calls a node would receive, in order."""

import shutil
import subprocess
import sys

import pytest
from fabrictestbed.slice_editor import ServiceType

from fabrictestbed_extensions.fablib.interface import Interface
from fabrictestbed_extensions.fablib.node import Node

# On Windows, shutil.which("bash") can find WSL's bash.exe, which is not the
# POSIX bash these stubs need.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash"
)

# sudo runs its command; nmcli records each call on fd 3, lists the existing
# connections and exits with UP_RC from "c up"; ip prints ROUTE as the
# management default route.
STUBS = """
sudo() {{ "$@"; }}
sysctl() {{ :; }}
ip() {{ echo "{route}"; }}
nmcli() {{
  echo "nmcli $*" >&3
  case "$*" in
    "-t -f NAME c show") printf '%s\\n' {existing} ;;
    "c up "*) return {up_rc} ;;
  esac
}}
exec 3>&2
"""


def configure(
    net_type, gateway=None, vlan=None, existing="", up_rc=0, mgmt_default=True
):
    """Run the real Interface._config_nmcli against a Node whose execute()
    runs the command in bash with the stubs; return the nmcli calls."""
    calls = []

    def execute(command, quiet=False):
        route = "default via 192.0.2.1 dev ens3" if mgmt_default else ""
        stubs = STUBS.format(existing=existing, up_rc=up_rc, route=route)
        run = subprocess.run(
            ["bash", "-c", stubs + command], capture_output=True, text=True
        )
        calls.extend(run.stderr.splitlines())
        return run.stdout, ""

    node = Node.__new__(Node)
    node.execute = execute
    node._detect_ip_version_for_interface = lambda iface: "ipv4"
    iface = Interface.__new__(Interface)
    iface.get_device_name = lambda: f"enp7s0.{vlan}" if vlan else "enp7s0"
    iface.get_vlan = lambda: vlan
    iface.get_physical_os_interface_name = lambda: "enp7s0"
    network = type(
        "Net", (), {"get_type": lambda s: net_type, "get_gateway": lambda s: gateway}
    )()
    iface._config_nmcli(node, network, addr="10.0.0.5", subnet="10.0.0.0/24")
    return calls


@pytest.mark.parametrize(
    "net_type, options, expected",
    [
        (
            ServiceType.L2Bridge,
            {},
            ["c add type ethernet ifname enp7s0", "ipv4.never-default yes"],
        ),
        (
            ServiceType.L2Bridge,
            {"existing": "fabric-enp7s0"},
            ["c mod fabric-enp7s0 ipv4.method manual", "ipv6.method disabled"],
        ),
        (
            ServiceType.FABNetv4,
            {"gateway": "10.0.0.1"},
            ["+ipv4.routes 10.128.0.0/10 10.0.0.1"],
        ),
        (
            ServiceType.FABNetv4Ext,
            {"gateway": "10.0.0.1"},
            ["ipv4.route-table 100", "routing-rules priority 1000 from 10.0.0.5/24"],
        ),
        (
            ServiceType.FABNetv4Ext,
            {"gateway": "10.0.0.1", "mgmt_default": False},
            ["ipv4.never-default no", "+ipv4.routes 0.0.0.0/0 10.0.0.1"],
        ),
        (
            ServiceType.L2Bridge,
            {"vlan": "100"},
            ["c add type vlan ifname enp7s0.100 con-name fabric-enp7s0.100 dev enp7s0"],
        ),
    ],
    ids=[
        "l2-new",
        "l2-rerun",
        "fabnetv4",
        "fabnetv4ext-pbr",
        "fabnetv4ext-no-mgmt-default",
        "vlan",
    ],
)
def test_config_nmcli(net_type, options, expected):
    """One SSH command creates the connection only when none of that name
    exists (NetworkManager accepts duplicate names), sets the type-specific
    settings, and brings the connection up last."""
    calls = configure(net_type, **options)
    adds = [call for call in calls if call.startswith("nmcli c add")]
    assert len(adds) == (0 if options.get("existing") else 1)
    assert calls[-1].startswith("nmcli c up")
    for setting in expected:
        assert any(setting in call for call in calls[:-1]), setting


def test_failed_connection_up_raises():
    with pytest.raises(RuntimeError, match="rc=4"):
        configure(ServiceType.L2Bridge, up_rc=4)
