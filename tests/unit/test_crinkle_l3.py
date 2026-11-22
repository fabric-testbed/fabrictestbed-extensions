from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from fabrictestbed_extensions.fablib.crease import crinkle
from fabrictestbed_extensions.fablib.crease.crinkle import CrinkleSlice


class FakeNet:
    def __init__(self, name, user_data):
        self.name, self.user_data = name, user_data

    def get_name(self):
        return self.name

    def get_user_data(self):
        return dict(self.user_data)

    def set_user_data(self, user_data):
        self.user_data = user_data


class FakeNode:
    """A node whose checked commands are recorded and succeed."""

    def __init__(self, name):
        self.name, self.commands = name, []
        executor = SimpleNamespace(submit=self._submit)
        manager = SimpleNamespace(get_ssh_thread_pool_executor=lambda: executor)
        self.get_fablib_manager = lambda: manager

    def get_name(self):
        return self.name

    def _submit(self, fn, *args):
        future = Future()
        future.set_result(fn(*args))
        return future

    def _execute_checked(self, cmd, what):
        self.commands.append(cmd)
        return ""


def iface(node, name, site="MAX", ip=None, mac=None, net_type="FABNetv4"):
    gateway = ip.rsplit(".", 1)[0] + ".1" if ip else None
    network = SimpleNamespace(
        get_gateway=lambda: gateway,
        get_subnet=lambda: "10.0.0.0/24",
        get_type=lambda: net_type,
    )
    return SimpleNamespace(
        get_network=lambda: network,
        get_node=lambda: node,
        get_name=lambda: name,
        get_site=lambda: site,
        get_ip_addr=lambda: ip,
        get_mac=lambda: mac,
        get_device_name=lambda: f"dev-{name}",
    )


def l3_slice(sub_nets):
    """A CrinkleSlice whose monitor and L2Bridge sub-network creation are
    stubbed: each add_monitored_l3network() builds the next sub-network."""
    s = CrinkleSlice.__new__(CrinkleSlice)
    s.prefix, s.monitors = "C", {}
    s.add_monitor = lambda **_: SimpleNamespace(
        set_monitor_data=lambda: None, data=SimpleNamespace(net_type=None)
    )
    pending = list(sub_nets)
    s._populate_l2bridge_monitor = lambda *_, **__: [pending.pop(0)]
    s.get_networks = lambda: sub_nets
    s._ifaces = {}
    s.get_interface = lambda name: s._ifaces[name]
    return s


def build_end(s, name, tunnel_node, site, fabnet_ip, endpoint_mac, vni, role):
    """Add one end of an L3 link: endpoint h<name>, tunnel node tunnel_node."""
    endpoint = iface(
        SimpleNamespace(get_name=lambda: f"h{name}"),
        f"h{name}-e",
        site,
        mac=endpoint_mac,
    )
    tunnel = iface(tunnel_node, f"t{name}-t", site)
    fabnet = iface(tunnel_node, f"t{name}-f", site, ip=fabnet_ip)
    s._ifaces.update({i.get_name(): i for i in (endpoint, tunnel, fabnet)})
    s.add_monitored_l3network(
        name=name,
        interfaces=[endpoint, tunnel],
        fabnet_iface=fabnet,
        vni=vni,
        role=role,
    )


def two_ended_slice(*ends):
    """A slice holding the given L3 link ends: (name, tunnel node, site, FABNet IP,
    endpoint MAC, vni, role)."""
    sub_nets = [FakeNet(f"C_net_{e[0]}", {"crinkle_net_name": e[0]}) for e in ends]
    s = l3_slice(sub_nets)
    for end in ends:
        build_end(s, *end)
    return s


def test_l3_ends_in_one_slice_are_joined():
    """Each tunnel node of a link in one slice gets a tunnel to the other's
    FABNet address, routed through its own FABNet gateway, with its tunnel
    interface taking the far endpoint's MAC; an end whose other end is in
    another slice waits for a peer, and get_l3_tunnel_endpoints() offers it."""
    ta, tb, tc = FakeNode("ta"), FakeNode("tb"), FakeNode("tc")
    s = two_ended_slice(
        ("a", ta, "MAX", "10.133.0.2", "aa:aa:aa:aa:aa:aa", 42, "src"),
        ("b", tb, "STAR", "10.140.0.2", "bb:bb:bb:bb:bb:bb", 42, "dst"),
        ("c", tc, "MAX", "10.133.0.3", "cc:cc:cc:cc:cc:cc", 7, "src"),
    )
    assert s.setup_l3_tunnels() == {42: "up", 7: "waiting for peer"}
    [cmd_a], [cmd_b] = ta.commands, tb.commands
    assert "address bb:bb:bb:bb:bb:bb" in cmd_a and "remote 10.140.0.2" in cmd_a
    assert "route replace 10.140.0.2 via 10.133.0.1" in cmd_a
    assert "address aa:aa:aa:aa:aa:aa" in cmd_b and "remote 10.133.0.2" in cmd_b
    assert tc.commands == []
    assert s.get_l3_tunnel_endpoints() == {
        7: {
            "role": "src",
            "fabnet_ip": "10.133.0.3",
            "endpoint_mac": "cc:cc:cc:cc:cc:cc",
        }
    }


def test_cross_slice_peer_is_remembered():
    """A peer from another slice, given once, is saved with the link, so a
    later call for that link alone (as start_monitor() makes after a reboot)
    needs no peers."""
    tc = FakeNode("tc")
    s = two_ended_slice(("c", tc, "MAX", "10.133.0.3", "cc:cc:cc:cc:cc:cc", 7, "src"))
    saves = []
    s.save_fablib_data = lambda: saves.append(1)
    peer = {
        "role": "dst",
        "fabnet_ip": "10.150.0.9",
        "endpoint_mac": "dd:dd:dd:dd:dd:dd",
    }
    assert s.setup_l3_tunnels(peers={7: peer}) == {7: "up"}
    assert s.setup_l3_tunnels(net_names=["c"]) == {7: "up"}
    assert [("remote 10.150.0.9" in cmd) for cmd in tc.commands] == [True, True]
    assert saves == [1]


@pytest.mark.parametrize(
    "case",
    [
        "no-interfaces",
        "two-sites",
        "fabnet-elsewhere",
        "fabnet-wrong-family",
        "tunnel-is-sink",
        "vni",
        "role",
    ],
)
def test_add_monitored_l3network_rejects_bad_input(case):
    """Bad input fails before any monitor is added to the slice."""
    h, t, other = (SimpleNamespace(get_name=lambda n=n: n) for n in ("h", "t", "o"))
    endpoint, tunnel = iface(h, "h-e"), iface(t, "t-t")
    args = {
        "name": "l3",
        "interfaces": [endpoint, tunnel],
        "fabnet_iface": iface(t, "t-f"),
        "vni": 42,
    }
    args.update(
        {
            "no-interfaces": {"interfaces": None},
            "two-sites": {"interfaces": [endpoint, iface(t, "t-t", site="STAR")]},
            "fabnet-elsewhere": {"fabnet_iface": iface(other, "o-f")},
            "fabnet-wrong-family": {
                "fabnet_iface": iface(t, "t-f", net_type="FABNetv6")
            },
            "tunnel-is-sink": {"sinks": [tunnel]},
            "vni": {"vni": 2**24},
            "role": {"role": "both"},
        }[case]
    )
    s = l3_slice([])
    s.add_monitor = lambda **_: pytest.fail("monitor added")
    with pytest.raises(ValueError):
        s.add_monitored_l3network(**args)


class FakeVM:
    def __init__(self, name, **attrs):
        self.name, self.host = name, None
        self.__dict__.update(attrs)

    def get_name(self):
        return self.name

    def get_site(self):
        return "STAR"

    def get_host(self):
        return self.host

    def set_host(self, host_name):
        self.host = host_name


@pytest.mark.parametrize("net_type", ["L2Bridge", crinkle.L3_NET_TYPE])
def test_monitor_is_placed_away_from_its_neighbours(monkeypatch, net_type):
    """allocate_hosts() puts a monitor on another worker than both nodes it
    sits between: on a shared worker, a VF receives only frames addressed to
    its own MAC, and the monitor sees nothing. An L3 end's monitor sits
    between its endpoint and tunnel node like any other."""
    monkeypatch.setattr(
        crinkle.NodeValidator,
        "can_allocate_node_in_host",
        lambda host, node, allocated, site: (
            allocated.update(core=0, ram=0, disk=0) or True,
        ),
    )
    endpoint, tunnel = FakeVM("hB"), FakeVM("tB")
    monitor = FakeVM(
        "C_monitor_l3B",
        data=SimpleNamespace(net_name="l3B", net_type=net_type),
        creation_data=[("hB",), ("tB",)],
    )
    hosts = {f"star-w{i}.fabric-testbed.net": {} for i in (1, 2, 3)}
    resources = SimpleNamespace(
        get_site=lambda name: {}, get_hosts_by_site=lambda name: hosts
    )
    s = CrinkleSlice.__new__(CrinkleSlice)
    s.monitors = {"l3B": monitor}
    s.get_all_nodes = lambda: [endpoint, tunnel, monitor]
    s.get_node = lambda name: {"hB": endpoint, "tB": tunnel}[name]
    s.get_fablib_manager = lambda: SimpleNamespace(get_resources=lambda: resources)
    s.set_crinkle_data = lambda: None

    s.allocate_hosts()
    assert monitor.get_host() not in {endpoint.get_host(), tunnel.get_host()}
