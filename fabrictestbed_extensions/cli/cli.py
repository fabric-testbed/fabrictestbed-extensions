#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#
# Author: Erica Fu (ericafu@renci.org), Komal Thareja (kthare10@renci.org)
#
import datetime
import json
import os
import re

import click
from fabrictestbed.util.constants import Constants

_DEFAULT_CREDMGR_HOST = "cm.fabric-testbed.net"
_DEFAULT_ORCHESTRATOR_HOST = "orchestrator.fabric-testbed.net"
_DEFAULT_CORE_API_HOST = "uis.fabric-testbed.net"
_FABRIC_RC_PATH = os.path.expanduser("~/work/fabric_config/fabric_rc")
_DEFAULT_TOKEN_DIR = os.path.expanduser("~/work/fabric_config")
_DEFAULT_TOKEN_PATH = os.path.join(_DEFAULT_TOKEN_DIR, "id_token.json")


def _load_fabric_rc(path=None):
    """Load config from a fabric_rc file.

    Args:
        path: Path to the fabric_rc file. Defaults to
              ~/work/fabric_config/fabric_rc.

    Returns a dict of key-value pairs. Supports 'export KEY=VALUE' and
    'KEY=VALUE' lines; comments and blank lines are ignored.
    """
    config = {}
    rc_path = path or _FABRIC_RC_PATH
    if not os.path.exists(rc_path):
        return config
    try:
        with open(rc_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :]
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        config[key] = value
    except Exception:
        pass
    return config


def __get_fabric_manager(
    *,
    oc_host=None,
    cm_host=None,
    project_id=None,
    scope="all",
    token_location=None,
    project_name=None,
):
    """Construct a FabricManagerV2 from CLI args, env vars, fabric_rc, and defaults."""
    from fabrictestbed.fabric_manager_v2 import FabricManagerV2

    rc = _load_fabric_rc()
    cm = (
        cm_host
        or os.getenv(Constants.FABRIC_CREDMGR_HOST)
        or rc.get(Constants.FABRIC_CREDMGR_HOST)
        or _DEFAULT_CREDMGR_HOST
    )
    oc = (
        oc_host
        or os.getenv(Constants.FABRIC_ORCHESTRATOR_HOST)
        or rc.get(Constants.FABRIC_ORCHESTRATOR_HOST)
        or _DEFAULT_ORCHESTRATOR_HOST
    )
    pid = (
        project_id
        or os.getenv(Constants.FABRIC_PROJECT_ID)
        or rc.get(Constants.FABRIC_PROJECT_ID)
    )
    pname = (
        project_name
        or os.getenv(Constants.FABRIC_PROJECT_NAME)
        or rc.get(Constants.FABRIC_PROJECT_NAME)
    )
    tl = (
        token_location
        or os.getenv(Constants.FABRIC_TOKEN_LOCATION)
        or rc.get(Constants.FABRIC_TOKEN_LOCATION)
        or _DEFAULT_TOKEN_PATH
    )
    core = (
        os.getenv(Constants.FABRIC_CORE_API_HOST)
        or rc.get(Constants.FABRIC_CORE_API_HOST)
        or _DEFAULT_CORE_API_HOST
    )
    return FabricManagerV2(
        credmgr_host=cm,
        orchestrator_host=oc,
        core_api_host=core,
        token_location=tl,
        project_id=pid,
        project_name=pname,
        scope=scope,
    )


def __get_fablib_manager(
    *,
    oc_host=None,
    cm_host=None,
    project_id=None,
    scope="all",
    token_location=None,
    project_name=None,
):
    """Construct a FablibManager from CLI args, env vars, fabric_rc, and defaults."""
    from fabrictestbed_extensions.fablib.fablib import FablibManager

    rc = _load_fabric_rc()
    cm = (
        cm_host
        or os.getenv(Constants.FABRIC_CREDMGR_HOST)
        or rc.get(Constants.FABRIC_CREDMGR_HOST)
        or _DEFAULT_CREDMGR_HOST
    )
    oc = (
        oc_host
        or os.getenv(Constants.FABRIC_ORCHESTRATOR_HOST)
        or rc.get(Constants.FABRIC_ORCHESTRATOR_HOST)
        or _DEFAULT_ORCHESTRATOR_HOST
    )
    pid = (
        project_id
        or os.getenv(Constants.FABRIC_PROJECT_ID)
        or rc.get(Constants.FABRIC_PROJECT_ID)
    )
    pname = (
        project_name
        or os.getenv(Constants.FABRIC_PROJECT_NAME)
        or rc.get(Constants.FABRIC_PROJECT_NAME)
    )
    tl = (
        token_location
        or os.getenv(Constants.FABRIC_TOKEN_LOCATION)
        or rc.get(Constants.FABRIC_TOKEN_LOCATION)
        or _DEFAULT_TOKEN_PATH
    )
    core = (
        os.getenv(Constants.FABRIC_CORE_API_HOST)
        or rc.get(Constants.FABRIC_CORE_API_HOST)
        or _DEFAULT_CORE_API_HOST
    )
    return FablibManager(
        credmgr_host=cm,
        orchestrator_host=oc,
        core_api_host=core,
        token_location=tl,
        project_id=pid,
    )


def __resolve_tokenlocation(tokenlocation: str) -> str:
    """Resolve token file location from arg, env var, fabric_rc, or default to ~/work/fabric_config/id_token.json."""
    if tokenlocation is None:
        tokenlocation = os.getenv(Constants.FABRIC_TOKEN_LOCATION)
    if tokenlocation is None:
        rc = _load_fabric_rc()
        tokenlocation = rc.get(Constants.FABRIC_TOKEN_LOCATION)
    if tokenlocation is None:
        tokenlocation = _DEFAULT_TOKEN_PATH
    os.makedirs(os.path.dirname(tokenlocation), exist_ok=True)
    return tokenlocation


def __resolve_cmhost(cmhost: str) -> str:
    """Resolve credential manager host from arg, env var, fabric_rc, or default."""
    if cmhost is None:
        cmhost = os.getenv(Constants.FABRIC_CREDMGR_HOST)
    if cmhost is None:
        rc = _load_fabric_rc()
        cmhost = rc.get(Constants.FABRIC_CREDMGR_HOST)
    if cmhost is None:
        cmhost = _DEFAULT_CREDMGR_HOST
    return cmhost


def _fmt_number(n) -> str:
    """Format a number with comma separators, or return '—' for None."""
    if n is None:
        return "—"
    if isinstance(n, float) and n == int(n):
        n = int(n)
    return f"{n:,}"


# ── Component type keys and their display labels ──────────────────────────
_COMPONENT_LABELS = [
    ("tesla_t4", "T4"),
    ("rtx6000", "RTX6000"),
    ("a30", "A30"),
    ("a40", "A40"),
    ("nic_connectx_5", "CX5"),
    ("nic_connectx_6", "CX6"),
    ("nic_connectx_7_100", "CX7-100"),
    ("nic_connectx_7_400", "CX7-400"),
    ("nic_bluefield2_connectx_5", "BF2-CX5"),
    ("nvme", "NVMe"),
    ("fpga_u280", "U280"),
    ("fpga_sn1022", "SN1022"),
    ("p4_switch", "P4"),
]

_LINE_WIDTH = 72

# ── State → color mapping ─────────────────────────────────────────────────
_STATE_COLORS = {
    "Active": "green",
    "StableOK": "green",
    "ModifyOK": "green",
    "Ticketed": "cyan",
    "Nascent": "cyan",
    "Configuring": "cyan",
    "Maintenance": "yellow",
    "ModifyError": "yellow",
    "AllocatedOK": "yellow",
    "Dead": "red",
    "Closing": "red",
    "StableError": "red",
    "CloseFail": "red",
    "Unknown": "white",
}


# ── Shared display utilities ──────────────────────────────────────────────


def _status(state):
    """Return a colored ● dot + state label."""
    color = _STATE_COLORS.get(state, "white")
    return click.style("●", fg=color) + " " + click.style(state, fg=color, bold=True)


def _header(title, subtitle=""):
    """Render a section header:  ── Title ────────────── subtitle ──"""
    left = f"── {title} "
    if subtitle:
        right = f" {subtitle} ──"
    else:
        right = "──"
    fill_len = max(0, _LINE_WIDTH - len(left) - len(right))
    line = left + "─" * fill_len + right
    click.echo(click.style(line, dim=True))


def _footer():
    """Render a section footer line."""
    click.echo(click.style("─" * _LINE_WIDTH, dim=True))


def _dim(text):
    """Shorthand for dim text."""
    return click.style(text, dim=True)


def _bold(text):
    """Shorthand for bold text."""
    return click.style(text, bold=True)


def _cyan(text):
    """Shorthand for cyan text."""
    return click.style(text, fg="cyan")


def _usage_bar(available, capacity, width=10):
    """Render a usage bar colored by how full the resource is.

    The filled portion represents used resources (capacity - available).
    Green = plenty free, yellow = getting full, red = nearly exhausted.
    """
    if not capacity or capacity <= 0:
        return click.style("░" * width, dim=True)
    used = max(0, (capacity or 0) - (available or 0))
    ratio = min(1.0, used / capacity)
    filled = round(ratio * width)
    bar_str = "█" * filled + "░" * (width - filled)
    if ratio >= 0.85:
        return click.style(bar_str, fg="red")
    elif ratio >= 0.6:
        return click.style(bar_str, fg="yellow")
    else:
        return click.style(bar_str, fg="green")


def _res(label, available, capacity, unit=""):
    """Format a resource metric: 'label ████░░ avail/cap unit'."""
    bar = _usage_bar(available, capacity)
    avail_s = _fmt_number(available)
    cap_s = _fmt_number(capacity)
    u = f" {unit}" if unit else ""
    return f"{_dim(label)} {bar} {avail_s}/{cap_s}{u}"


def _component_tags(data):
    """Build a list of 'LABEL:avail/cap' tags for components with capacity > 0."""
    tags = []
    for key, label in _COMPONENT_LABELS:
        cap = data.get(f"{key}_capacity", 0) or 0
        if cap > 0:
            avail = data.get(f"{key}_available", 0) or 0
            if avail == cap:
                tag = click.style(f"{label}:{avail}/{cap}", fg="green")
            elif avail == 0:
                tag = click.style(f"{label}:{avail}/{cap}", fg="red")
            else:
                tag = click.style(f"{label}:{avail}/{cap}", fg="yellow")
            tags.append(tag)
    return tags


def _kv(label, value):
    """Format a key-value pair with dim label."""
    return f"{_dim(label)}  {value}"


def _row(*parts):
    """Print an indented row with 4-space indent."""
    click.echo(f"    {'   '.join(parts)}")


# ── Slices ─────────────────────────────────────────────────────────────────


def _print_slices(slices_list):
    """Print slices in a dashboard-style table."""
    if not slices_list:
        click.echo("No slices found.")
        return
    _header("Slices", f"{len(slices_list)} slice{'s' if len(slices_list) != 1 else ''}")
    click.echo()
    for s in slices_list:
        state = s.get("state") or s.get("State") or "Unknown"
        name = s.get("name") or s.get("Name") or "—"
        sid = s.get("id") or s.get("ID") or s.get("slice_id") or "—"
        proj = s.get("project_id") or s.get("Project ID") or "—"
        lease_end = (
            s.get("lease_end")
            or s.get("Lease Expiration (UTC)")
            or s.get("lease_end_time")
            or "—"
        )

        click.echo(f"  {_bold(name)}   {_status(state)}")
        _row(_kv("ID:", sid))
        _row(_kv("Project:", proj), _kv("Lease End:", lease_end))
        click.echo()
    _footer()


def _print_slice_detail(slice_dict):
    """Print detailed info for a single slice."""
    s = slice_dict
    name = s.get("name") or s.get("Name") or "—"
    state = s.get("state") or s.get("State") or "Unknown"
    sid = s.get("id") or s.get("ID") or s.get("slice_id") or "—"
    proj = s.get("project_id") or s.get("Project ID") or "—"
    lease_start = s.get("lease_start") or s.get("Lease Start (UTC)") or "—"
    lease_end = s.get("lease_end") or s.get("Lease Expiration (UTC)") or "—"
    email = s.get("email") or s.get("Email") or "—"

    _header("Slice Detail")
    click.echo()
    click.echo(f"  {_bold(name)}   {_status(state)}")
    click.echo()
    _row(_kv("ID:", sid))
    _row(_kv("Project:", proj))
    _row(_kv("Email:", email))
    _row(_kv("Lease Start:", lease_start))
    _row(_kv("Lease End:", lease_end))
    click.echo()
    _footer()


# ── Nodes ──────────────────────────────────────────────────────────────────


def _print_nodes(nodes_list):
    """Print nodes in a dashboard-style format."""
    if not nodes_list:
        click.echo("No nodes found.")
        return
    _header("Nodes", f"{len(nodes_list)} node{'s' if len(nodes_list) != 1 else ''}")
    click.echo()
    for n in nodes_list:
        name = n.get("name") or n.get("Name") or "—"
        state = n.get("state") or n.get("State") or "Unknown"
        site = n.get("site") or n.get("Site") or "—"
        cores = n.get("cores") or n.get("Cores") or "—"
        ram = n.get("ram") or n.get("RAM") or "—"
        disk = n.get("disk") or n.get("Disk") or "—"
        image = n.get("image") or n.get("Image") or "—"
        host = n.get("host") or n.get("Host") or ""
        mgmt_ip = n.get("management_ip") or n.get("Management IP") or ""
        ssh_cmd = n.get("ssh_command") or n.get("SSH Command") or ""

        click.echo(f"  {_bold(name)}   {_status(state)}   {_dim('@')} {_cyan(site)}")
        _row(
            _kv("cores:", cores),
            _kv("ram:", f"{ram} G"),
            _kv("disk:", f"{disk} G"),
            _kv("image:", image),
        )
        detail = []
        if host:
            detail.append(_kv("host:", host))
        if mgmt_ip:
            detail.append(_kv("mgmt_ip:", mgmt_ip))
        if detail:
            _row(*detail)
        if ssh_cmd:
            _row(_kv("ssh:", _dim(ssh_cmd)))
        click.echo()
    _footer()


# ── Networks ───────────────────────────────────────────────────────────────


def _print_networks(networks_list):
    """Print networks in a dashboard-style format."""
    if not networks_list:
        click.echo("No networks found.")
        return
    _header(
        "Networks",
        f"{len(networks_list)} network{'s' if len(networks_list) != 1 else ''}",
    )
    click.echo()
    for net in networks_list:
        name = net.get("name") or net.get("Name") or "—"
        state = net.get("state") or net.get("State") or "Unknown"
        ntype = net.get("type") or net.get("Type") or "—"
        layer = net.get("layer") or net.get("Layer") or "—"
        site = net.get("site") or net.get("Site") or "—"
        subnet = net.get("subnet") or net.get("Subnet") or ""
        gateway = net.get("gateway") or net.get("Gateway") or ""
        error = net.get("error") or net.get("Error") or ""

        click.echo(
            f"  {_bold(name)}   {_status(state)}   {_cyan(ntype)}  {_dim(layer)}"
        )
        detail = [_kv("site:", site)]
        if subnet:
            detail.append(_kv("subnet:", subnet))
        if gateway:
            detail.append(_kv("gateway:", gateway))
        _row(*detail)
        if error:
            _row(click.style("error:", fg="red") + f"  {error}")
        click.echo()
    _footer()


# ── Interfaces ─────────────────────────────────────────────────────────────


def _print_interfaces(interfaces_list):
    """Print interfaces in a dashboard-style format."""
    if not interfaces_list:
        click.echo("No interfaces found.")
        return
    _header(
        "Interfaces",
        f"{len(interfaces_list)} interface{'s' if len(interfaces_list) != 1 else ''}",
    )
    click.echo()
    for ifc in interfaces_list:
        name = ifc.get("name") or ifc.get("Name") or "—"
        node = ifc.get("node") or ifc.get("Node") or "—"
        network = ifc.get("network") or ifc.get("Network") or "—"
        bw = ifc.get("bandwidth") or ifc.get("Bandwidth") or "—"
        vlan = ifc.get("vlan") or ifc.get("VLAN") or ""
        mode = ifc.get("mode") or ifc.get("Mode") or ""
        mac = ifc.get("mac") or ifc.get("MAC") or ""
        ip_addr = ifc.get("ip_addr") or ifc.get("IP Address") or ""
        dev = ifc.get("dev") or ifc.get("Device") or ""

        click.echo(f"  {_bold(name)}   " f"{_cyan(node)} {_dim('━━')} {_cyan(network)}")
        detail = [_kv("bw:", f"{bw} Mbps")]
        if vlan:
            detail.append(_kv("vlan:", vlan))
        if mode:
            detail.append(_kv("mode:", mode))
        if mac:
            detail.append(_kv("mac:", mac))
        _row(*detail)

        if ip_addr or dev:
            os_parts = []
            if dev:
                os_parts.append(_kv("dev:", dev))
            if ip_addr:
                os_parts.append(_kv("ip:", ip_addr))
            _row(*os_parts)
        click.echo()
    _footer()


# ── Slice Slivers ──────────────────────────────────────────────────────────


def _print_slice_slivers(slivers_list):
    """Print slivers in a dashboard-style format."""
    if not slivers_list:
        click.echo("No slivers found.")
        return
    _header(
        "Slivers", f"{len(slivers_list)} sliver{'s' if len(slivers_list) != 1 else ''}"
    )
    click.echo()
    for sv in slivers_list:
        name = sv.get("name") or sv.get("Name") or "—"
        state = sv.get("state") or sv.get("State") or "Unknown"
        site = sv.get("site") or sv.get("Site") or "—"
        stype = sv.get("type") or sv.get("Type") or "—"
        sid = sv.get("id") or sv.get("ID") or "—"
        error = sv.get("error") or sv.get("Error") or ""

        click.echo(
            f"  {_bold(name)}   {_status(state)}   {_cyan(stype)}   {_dim('@')} {site}"
        )
        _row(_kv("id:", sid))
        if error:
            _row(click.style("error:", fg="red") + f"  {error}")
        click.echo()
    _footer()


# ── Sites ──────────────────────────────────────────────────────────────────


def _print_sites(sites_list):
    """Print sites in a dashboard-style format with usage bars."""
    if not sites_list:
        click.echo("No sites found.")
        return
    _header("Sites", f"{len(sites_list)} site{'s' if len(sites_list) != 1 else ''}")
    click.echo()

    max_name = max((len(s.get("name", "")) for s in sites_list), default=4)
    max_name = min(max_name, 20)

    for s in sites_list:
        name = s.get("name", "—")
        state = s.get("state", "Unknown")
        hosts = s.get("hosts", 0)

        click.echo(
            f"  {_bold(name.ljust(max_name))}   "
            f"{_status(state)}   "
            f"{_bold(str(hosts))} hosts"
        )
        _row(
            _res("cores", s.get("cores_available"), s.get("cores_capacity")),
            _res("ram", s.get("ram_available"), s.get("ram_capacity"), "G"),
            _res("disk", s.get("disk_available"), s.get("disk_capacity"), "G"),
        )
        tags = _component_tags(s)
        if tags:
            _row("  ".join(tags))
        click.echo()
    _footer()


def _print_site_detail(site_dict):
    """Print detailed info for a single site."""
    s = site_dict
    name = s.get("name", "—")
    state = s.get("state", "Unknown")
    address = s.get("address", "—")
    location = s.get("location", "—")
    if isinstance(location, list) and len(location) == 2:
        location = f"({location[0]}, {location[1]})"
    ptp = s.get("ptp_capable", False)
    hosts = s.get("hosts", 0)
    cpus = s.get("cpus", 0)

    _header("Site Detail")
    click.echo()
    click.echo(f"  {_bold(name)}   {_status(state)}")
    click.echo()
    _row(_kv("Address:", address))
    _row(_kv("Location:", str(location)))
    _row(
        _kv("PTP:", "Yes" if ptp else "No"),
        _kv("Hosts:", str(hosts)),
        _kv("CPUs:", str(cpus)),
    )
    click.echo()

    for label, key, unit in [
        ("Cores", "cores", ""),
        ("RAM", "ram", "G"),
        ("Disk", "disk", "G"),
    ]:
        _row(
            _res(
                f"{label:<5s}",
                s.get(f"{key}_available"),
                s.get(f"{key}_capacity"),
                unit,
            )
        )
    click.echo()

    comp_lines = []
    for key, label in _COMPONENT_LABELS:
        cap = s.get(f"{key}_capacity", 0) or 0
        if cap > 0:
            avail = s.get(f"{key}_available", 0) or 0
            comp_lines.append((label, avail, cap))

    if comp_lines:
        _row(_dim("Components:"))
        for i in range(0, len(comp_lines), 3):
            parts = []
            for label, avail, cap in comp_lines[i : i + 3]:
                if avail == cap:
                    val = click.style(f"{avail}/{cap}", fg="green")
                elif avail == 0:
                    val = click.style(f"{avail}/{cap}", fg="red")
                else:
                    val = click.style(f"{avail}/{cap}", fg="yellow")
                parts.append(f"{label + ':':<12s} {val}")
            click.echo(f"      {'    '.join(parts)}")
        click.echo()
    _footer()


# ── Hosts ──────────────────────────────────────────────────────────────────


def _print_hosts(hosts_list):
    """Print hosts in a dashboard-style format with usage bars."""
    if not hosts_list:
        click.echo("No hosts found.")
        return
    _header("Hosts", f"{len(hosts_list)} host{'s' if len(hosts_list) != 1 else ''}")
    click.echo()

    for h in hosts_list:
        name = h.get("name", "—")
        state = h.get("state", "Unknown")

        click.echo(f"  {_bold(name)}   {_status(state)}")
        _row(
            _res("cores", h.get("cores_available"), h.get("cores_capacity")),
            _res("ram", h.get("ram_available"), h.get("ram_capacity"), "G"),
            _res("disk", h.get("disk_available"), h.get("disk_capacity"), "G"),
        )
        tags = _component_tags(h)
        if tags:
            _row("  ".join(tags))
        click.echo()
    _footer()


# ── Links ──────────────────────────────────────────────────────────────────


def _print_links(links_list):
    """Print links in a dashboard-style format."""
    if not links_list:
        click.echo("No links found.")
        return
    _header("Links", f"{len(links_list)} link{'s' if len(links_list) != 1 else ''}")
    click.echo()

    for lnk in links_list:
        layer = lnk.get("layer", "—")
        bw = lnk.get("bandwidth", 0) or 0
        alloc_bw = lnk.get("allocated_bandwidth", 0) or 0
        avail_bw = bw - alloc_bw
        sites = lnk.get("sites", [])

        if isinstance(sites, list) and len(sites) == 2:
            site_str = f"{_bold(sites[0])} {_dim('━━')} {_bold(sites[1])}"
        else:
            site_str = str(sites)

        bw_bar = _usage_bar(avail_bw, bw, width=8)

        click.echo(
            f"  {site_str}   "
            f"{bw_bar}  "
            f"{_bold(str(bw))} Gbps  "
            f"{_dim(f'({alloc_bw} allocated)')}  "
            f"{_dim(layer)}"
        )
    click.echo()
    _footer()


# ── Facility Ports ─────────────────────────────────────────────────────────


def _print_facility_ports(fp_list):
    """Print facility ports in a dashboard-style format."""
    if not fp_list:
        click.echo("No facility ports found.")
        return
    _header("Facility Ports", f"{len(fp_list)} port{'s' if len(fp_list) != 1 else ''}")
    click.echo()
    for fp in fp_list:
        name = fp.get("name", "—")
        site = fp.get("site", "—")
        vlans = fp.get("vlans", "—")
        allocated = fp.get("allocated_vlans", "—")

        click.echo(f"  {_bold(name)}   {_dim('@')} {_cyan(site)}")
        _row(_kv("vlans:", str(vlans)), _kv("allocated:", str(allocated)))
        click.echo()
    _footer()


@click.group()
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    """FABRIC testbed command-line interface."""
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose


@click.group()
@click.pass_context
def tokens(ctx):
    """Token management

    Manage FABRIC identity and refresh tokens. Set $FABRIC_CREDMGR_HOST
    to avoid passing --cmhost on every command. Set $FABRIC_TOKEN_LOCATION
    to set the default token file path (defaults to
    ~/work/fabric_config/id_token.json).
    """


@tokens.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option(
    "--projectid",
    default=None,
    help="Project UUID (uses first project if not specified)",
)
@click.option(
    "--projectname",
    default=None,
    help="Project name (uses first project if not specified)",
)
@click.option("--lifetime", default=4, help="Token lifetime in hours")
@click.option(
    "--comment", default=None, help="Comment/note to associate with the token"
)
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--location",
    help="Path to save token JSON (defaults to ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not attempt to open a browser automatically",
)
@click.option(
    "--code-file",
    default=None,
    type=click.Path(exists=True),
    help="File containing the base64 authorization code (for remote/headless use)",
)
@click.pass_context
def create(
    ctx,
    cmhost: str,
    projectid: str,
    projectname: str,
    lifetime: int,
    comment: str,
    scope: str,
    location: str,
    no_browser: bool,
    code_file: str,
):
    """Create token

    Opens a browser for CILogon authentication (or prints the URL if the
    browser cannot be opened). After login, the token is automatically
    captured via a localhost callback. If running on a remote VM, press
    Ctrl+C and paste the authorization code shown in the browser.

    Token is saved to --location, $FABRIC_TOKEN_LOCATION, or
    ~/work/fabric_config/id_token.json (in that order). If no project is
    specified, the user's first project is used.
    """
    try:
        cmhost = __resolve_cmhost(cmhost)
        tokenlocation = __resolve_tokenlocation(location)
        cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

        from fabrictestbed.external_api.credmgr_client import CredmgrClient

        client = CredmgrClient(
            credmgr_host=cmhost, cookie_name=cookie_name or "fabric-service"
        )

        rc = _load_fabric_rc()
        if projectid is None:
            projectid = os.getenv(Constants.FABRIC_PROJECT_ID) or rc.get(
                Constants.FABRIC_PROJECT_ID
            )
        if projectname is None:
            projectname = os.getenv(Constants.FABRIC_PROJECT_NAME) or rc.get(
                Constants.FABRIC_PROJECT_NAME
            )

        tokens = client.create_cli(
            scope=scope,
            project_id=projectid,
            project_name=projectname,
            lifetime_hours=lifetime,
            comment=comment or "Create Token via CLI",
            file_path=tokenlocation,
            open_browser=not no_browser,
            code_file=code_file,
            return_fmt="dto",
        )

        project_label = ""
        if tokens and tokens[0].id_token:
            try:
                decoded = client.validate(id_token=tokens[0].id_token, return_fmt="dto")
                if decoded.projects:
                    p = decoded.projects[0]
                    project_label = f" for project: '{p.name}' ({p.uuid})"
            except Exception:
                pass

        click.echo(f"\nToken saved at: {tokenlocation}{project_label}")
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e))


@tokens.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option("--projectname", default=None, help="Project name")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.pass_context
def refresh(
    ctx, cmhost: str, location: str, projectid: str, projectname: str, scope: str
):
    """Refresh token

    Reads the existing token file, uses the refresh_token to obtain a new
    identity token, and saves the result back. Token file is read from
    --location, $FABRIC_TOKEN_LOCATION, or
    ~/work/fabric_config/id_token.json.
    """
    try:
        cmhost = __resolve_cmhost(cmhost)
        tokenlocation = __resolve_tokenlocation(location)

        if not os.path.exists(tokenlocation):
            raise click.ClickException(f"Token file not found: {tokenlocation}")

        with open(tokenlocation, "r") as f:
            existing = json.load(f)

        refresh_token = existing.get("refresh_token")
        if not refresh_token:
            raise click.ClickException(f"No refresh_token found in {tokenlocation}")

        rc = _load_fabric_rc()
        if projectid is None:
            projectid = os.getenv(Constants.FABRIC_PROJECT_ID) or rc.get(
                Constants.FABRIC_PROJECT_ID
            )
        if projectname is None:
            projectname = os.getenv(Constants.FABRIC_PROJECT_NAME) or rc.get(
                Constants.FABRIC_PROJECT_NAME
            )

        cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

        from fabrictestbed.external_api.credmgr_client import CredmgrClient

        client = CredmgrClient(
            credmgr_host=cmhost, cookie_name=cookie_name or "fabric-service"
        )

        result = client.refresh(
            refresh_token=refresh_token,
            scope=scope,
            project_id=projectid,
            project_name=projectname,
            file_path=tokenlocation,
            return_fmt="dto",
        )

        click.echo(f"Token refreshed and saved at: {tokenlocation}")
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e))


@tokens.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option(
    "--refreshtoken",
    help="Refresh token to revoke (overrides token file)",
    default=None,
)
@click.option(
    "--identitytoken",
    help="Identity token for authentication (overrides token file)",
    default=None,
)
@click.option("--tokenhash", help="SHA256 hash of the token to revoke", default=None)
@click.pass_context
def revoke(
    ctx,
    cmhost: str,
    location: str,
    refreshtoken: str,
    identitytoken: str,
    tokenhash: str,
):
    """Revoke token

    Revokes a refresh or identity token. Reads tokens from --location
    (or $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json) unless --refreshtoken
    and --identitytoken are provided explicitly.

    If --refreshtoken is provided, it is revoked. Otherwise the identity
    token (by --tokenhash) is revoked.
    """
    try:
        cmhost = __resolve_cmhost(cmhost)
        cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

        # Load from file if explicit tokens not provided
        if refreshtoken is None and identitytoken is None:
            tokenlocation = __resolve_tokenlocation(location)
            if not os.path.exists(tokenlocation):
                raise click.ClickException(f"Token file not found: {tokenlocation}")

            with open(tokenlocation, "r") as f:
                file_tokens = json.load(f)

            refreshtoken = file_tokens.get("refresh_token")
            identitytoken = file_tokens.get("id_token")
            tokenhash = tokenhash or file_tokens.get("token_hash")

        if not identitytoken:
            raise click.ClickException("Identity token is required for revocation")

        from fabrictestbed.external_api.credmgr_client import CredmgrClient

        client = CredmgrClient(
            credmgr_host=cmhost, cookie_name=cookie_name or "fabric-service"
        )

        if refreshtoken:
            client.revoke(
                id_token=identitytoken, token_type="refresh", refresh_token=refreshtoken
            )
        else:
            if not tokenhash:
                raise click.ClickException(
                    "Token hash is required to revoke an identity token"
                )
            client.revoke(
                id_token=identitytoken, token_type="identity", token_hash=tokenhash
            )

        click.echo("Token revoked successfully")
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def slices(ctx):
    """Slice management

    List, show, renew, and delete slices.
    """


@slices.command(name="list")
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    default=False,
    help="Include Dead and Closing slices",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def list_slices(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    show_all: bool,
    as_json: bool,
):
    """List slices

    Show all slices for the current user. Dead and Closing slices are
    hidden by default; use --all to include them.
    """
    try:
        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        from fabrictestbed.slice_manager import SliceState

        excludes = [] if show_all else [SliceState.Dead, SliceState.Closing]
        result = fablib.list_slices(excludes=excludes, output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_slices(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def show(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    name: str,
    sliceid: str,
    as_json: bool,
):
    """Show slice details

    Display details for a single slice by --name or --sliceid.
    """
    try:
        if not name and not sliceid:
            raise click.ClickException("Either --name or --sliceid must be specified")

        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        result = fablib.show_slice(name=name, id=sliceid, output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            if isinstance(data, list):
                data = data[0] if data else {}
            _print_slice_detail(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.pass_context
def delete(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    name: str,
    sliceid: str,
):
    """Delete a slice

    Delete a slice by --name or --sliceid.
    """
    try:
        if not name and not sliceid:
            raise click.ClickException("Either --name or --sliceid must be specified")

        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        s = fablib.get_slice(name=name, slice_id=sliceid)
        slice_label = name or sliceid
        s.delete()
        click.echo(f"Slice '{slice_label}' deleted successfully")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.option(
    "--days", type=int, default=None, help="Number of days to extend the lease"
)
@click.option(
    "--end",
    "leaseend",
    default=None,
    help='New lease end time (UTC format: "YYYY-MM-DD HH:MM:SS +0000")',
)
@click.pass_context
def renew(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    name: str,
    sliceid: str,
    days: int,
    leaseend: str,
):
    """Renew a slice lease

    Extend the lease for a slice by --days or an explicit --end time.
    Specify the slice by --name or --sliceid.
    """
    try:
        if not name and not sliceid:
            raise click.ClickException("Either --name or --sliceid must be specified")
        if not days and not leaseend:
            raise click.ClickException("Either --days or --end must be specified")

        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        s = fablib.get_slice(name=name, slice_id=sliceid)
        s.renew(end_date=leaseend, days=days)

        slice_label = name or sliceid
        if days:
            click.echo(f"Slice '{slice_label}' renewed for {days} day(s)")
        else:
            click.echo(f"Slice '{slice_label}' renewed until {leaseend}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


# Common options for slice subcommands that need to resolve a slice
def _get_slice_from_opts(cmhost, ochost, location, projectid, scope, name, sliceid):
    """Helper: build fablib and resolve a slice by name or ID."""
    if not name and not sliceid:
        raise click.ClickException("Either --name or --sliceid must be specified")
    fablib = __get_fablib_manager(
        cm_host=cmhost,
        oc_host=ochost,
        project_id=projectid,
        scope=scope,
        token_location=location,
    )
    return fablib, fablib.get_slice(name=name, slice_id=sliceid)


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def nodes(ctx, cmhost, ochost, location, projectid, scope, name, sliceid, as_json):
    """List nodes in a slice

    Show all nodes in a slice identified by --name or --sliceid.
    """
    try:
        _, s = _get_slice_from_opts(
            cmhost, ochost, location, projectid, scope, name, sliceid
        )
        result = s.list_nodes(output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_nodes(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def networks(ctx, cmhost, ochost, location, projectid, scope, name, sliceid, as_json):
    """List networks in a slice

    Show all network services in a slice identified by --name or --sliceid.
    """
    try:
        _, s = _get_slice_from_opts(
            cmhost, ochost, location, projectid, scope, name, sliceid
        )
        result = s.list_networks(output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_networks(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def interfaces(ctx, cmhost, ochost, location, projectid, scope, name, sliceid, as_json):
    """List interfaces in a slice

    Show all interfaces in a slice identified by --name or --sliceid.
    """
    try:
        _, s = _get_slice_from_opts(
            cmhost, ochost, location, projectid, scope, name, sliceid
        )
        result = s.list_interfaces(output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_interfaces(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--location", help="Path to token JSON file", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--name", default=None, help="Slice name")
@click.option("--sliceid", default=None, help="Slice UUID")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def slivers(ctx, cmhost, ochost, location, projectid, scope, name, sliceid, as_json):
    """List slivers in a slice

    Show all slivers in a slice identified by --name or --sliceid.
    """
    try:
        _, s = _get_slice_from_opts(
            cmhost, ochost, location, projectid, scope, name, sliceid
        )
        result = s.list_slivers(output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_slice_slivers(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def resources(ctx):
    """Resource management

    Query available testbed resources including sites, hosts, links,
    and facility ports.
    """


@resources.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force a fresh snapshot instead of using cache",
)
@click.option("--site", default=None, help="Show details for a specific site")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output JSON instead of table",
)
@click.pass_context
def sites(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    force: bool,
    site: str,
    as_json: bool,
):
    """List testbed sites

    Show all available sites and their resources. Use --site to show
    details for a specific site. Use --json for JSON output.
    """
    try:
        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        if site:
            result = fablib.get_resources(force_refresh=force).show_site(
                site_name=site,
                output="json",
                quiet=True,
            )
            if as_json:
                click.echo(result)
            else:
                data = json.loads(result)
                if isinstance(data, list):
                    data = data[0] if data else {}
                _print_site_detail(data)
        else:
            result = fablib.list_sites(output="json", quiet=True, force_refresh=force)
            if as_json:
                click.echo(result)
            else:
                data = json.loads(result)
                _print_sites(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@resources.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force a fresh snapshot instead of using cache",
)
@click.option("--site", default=None, help="Filter hosts by site name")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output JSON instead of table",
)
@click.pass_context
def hosts(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    force: bool,
    site: str,
    as_json: bool,
):
    """List testbed hosts

    Show all available hosts and their resources. Use --site to filter
    by site name. Use --json for JSON output.
    """
    try:
        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        includes = [site] if site else None
        result = fablib.list_hosts(
            output="json", quiet=True, force_refresh=force, includes=includes
        )
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_hosts(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@resources.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output JSON instead of table",
)
@click.pass_context
def links(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    as_json: bool,
):
    """List inter-site network links

    Show all available inter-site links. Use --json for JSON output.
    """
    try:
        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        result = fablib.list_links(output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_links(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@resources.command(name="facility-ports")
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--site", default=None, help="Filter facility ports by site name")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output JSON instead of table",
)
@click.pass_context
def facility_ports(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    site: str,
    as_json: bool,
):
    """List facility ports

    Show all available facility ports for external connectivity.
    Use --site to filter by site name. Use --json for JSON output.
    """
    try:
        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        if site:
            filter_fn = lambda fp: fp["site"] == site
            result = fablib.list_facility_ports(
                output="json", quiet=True, filter_function=filter_fn
            )
        else:
            result = fablib.list_facility_ports(output="json", quiet=True)
        if as_json:
            click.echo(result)
        else:
            data = json.loads(result)
            _print_facility_ports(data)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@resources.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--start",
    required=True,
    help="Start date (ISO 8601, e.g. 2025-07-01T00:00:00+00:00)",
)
@click.option(
    "--end", required=True, help="End date (ISO 8601, e.g. 2025-07-04T00:00:00+00:00)"
)
@click.option(
    "--interval",
    type=click.Choice(["hour", "day", "week"], case_sensitive=False),
    default="day",
    help="Time slot granularity (default: day)",
)
@click.option("--site", multiple=True, help="Include site (repeatable)")
@click.option("--host", multiple=True, help="Include host (repeatable)")
@click.option("--exclude-site", multiple=True, help="Exclude site (repeatable)")
@click.option("--exclude-host", multiple=True, help="Exclude host (repeatable)")
@click.option(
    "--show",
    type=click.Choice(["all", "sites", "hosts"], case_sensitive=False),
    default="all",
    help="Show sites, hosts, or all (default: all)",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output JSON instead of table",
)
@click.pass_context
def calendar(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    start: str,
    end: str,
    interval: str,
    site: tuple,
    host: tuple,
    exclude_site: tuple,
    exclude_host: tuple,
    show: str,
    as_json: bool,
):
    """Resource availability calendar

    Show resource capacity, allocation, and availability per site/host
    over time slots. Use --interval to control granularity.
    """
    try:
        from datetime import datetime, timezone

        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        fablib.resources_calendar(
            start=start_dt,
            end=end_dt,
            interval=interval,
            site=list(site) or None,
            host=list(host) or None,
            exclude_site=list(exclude_site) or None,
            exclude_host=list(exclude_host) or None,
            show=show,
            output="json" if as_json else "text",
        )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@resources.command(name="find-slot")
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--start",
    required=True,
    help="Start date (ISO 8601, e.g. 2025-07-01T00:00:00+00:00)",
)
@click.option(
    "--end", required=True, help="End date (ISO 8601, e.g. 2025-07-04T00:00:00+00:00)"
)
@click.option("--duration", required=True, type=int, help="Consecutive hours needed")
@click.option(
    "--resources",
    "resources_json",
    required=True,
    help='JSON array of resource requests, e.g. \'[{"type":"compute","site":"RENC","cores":2,"ram":8,"disk":10}]\'',
)
@click.option(
    "--max-results",
    type=int,
    default=1,
    help="Maximum number of windows to return (default: 1)",
)
@click.option(
    "--live",
    "use_live_data",
    is_flag=True,
    default=False,
    help="Use live orchestrator data instead of Reports API",
)
@click.pass_context
def find_slot(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    start: str,
    end: str,
    duration: int,
    resources_json: str,
    max_results: int,
    use_live_data: bool,
):
    """Find available time slots

    Find time windows where all requested resources are simultaneously
    available. Use --live for real-time data from the orchestrator instead
    of the Reports API.
    """
    try:
        import json as json_mod
        from datetime import datetime, timezone

        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        try:
            resources_list = json_mod.loads(resources_json)
        except json_mod.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON for --resources: {exc}")

        if not isinstance(resources_list, list):
            raise click.ClickException("--resources must be a JSON array")

        fablib = __get_fablib_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        result = fablib.find_resource_slot(
            start=start_dt,
            end=end_dt,
            duration=duration,
            resources=resources_list,
            max_results=max_results,
            use_live_data=use_live_data,
        )
        click.echo(json_mod.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def configure(ctx):
    """Environment configuration

    Set up the FABRIC config directory with SSH keys, ssh_config, and
    fabric_rc so you can start using FABRIC from the CLI or notebooks.
    """


_BASTION_HOST = "bastion.fabric-testbed.net"


@configure.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option("--projectid", default=None, help="Project UUID")
@click.option("--projectname", default=None, help="Project name")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--lifetime", default=4, help="Token lifetime in hours")
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not attempt to open a browser automatically",
)
@click.option(
    "--config-dir",
    default=None,
    help="Config directory (default: ~/work/fabric_config)",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing keys and config files",
)
@click.pass_context
def setup(
    ctx,
    cmhost,
    ochost,
    projectid,
    projectname,
    scope,
    lifetime,
    no_browser,
    config_dir,
    overwrite,
):
    """Set up FABRIC environment

    Creates the config directory, creates a token, generates bastion and
    sliver SSH keys, and writes ssh_config and fabric_rc files.

    When --config-dir is specified, all files are read from and written to
    that directory. An existing fabric_rc in the directory is used for
    configuration; default paths outside the directory are not consulted.
    """
    try:
        config_dir = (
            os.path.expanduser(config_dir) if config_dir else _DEFAULT_TOKEN_DIR
        )
        os.makedirs(config_dir, exist_ok=True)
        click.echo(f"Config directory: {config_dir}")

        # Load fabric_rc from the config directory if it exists, otherwise
        # fall back to the default location only when no --config-dir was given
        config_dir_rc_path = os.path.join(config_dir, "fabric_rc")
        if os.path.exists(config_dir_rc_path):
            rc = _load_fabric_rc(config_dir_rc_path)
        elif config_dir == _DEFAULT_TOKEN_DIR:
            rc = _load_fabric_rc()
        else:
            rc = {}

        # Resolve hosts from CLI args, fabric_rc in config_dir, or defaults
        cm = cmhost or rc.get(Constants.FABRIC_CREDMGR_HOST) or _DEFAULT_CREDMGR_HOST
        oc = (
            ochost
            or rc.get(Constants.FABRIC_ORCHESTRATOR_HOST)
            or _DEFAULT_ORCHESTRATOR_HOST
        )
        core = rc.get(Constants.FABRIC_CORE_API_HOST) or _DEFAULT_CORE_API_HOST
        pid = projectid or rc.get(Constants.FABRIC_PROJECT_ID)
        pname = projectname or rc.get(Constants.FABRIC_PROJECT_NAME)

        # All file paths are resolved from fabric_rc in config_dir,
        # falling back to config_dir-based defaults (no env var lookups)
        config_token_path = rc.get("FABRIC_TOKEN_LOCATION") or os.path.join(
            config_dir, "id_token.json"
        )
        bastion_key_path = rc.get("FABRIC_BASTION_KEY_LOCATION") or os.path.join(
            config_dir, "fabric_bastion_key"
        )
        bastion_pub_path = f"{bastion_key_path}.pub"
        sliver_key_path = rc.get("FABRIC_SLICE_PRIVATE_KEY_FILE") or os.path.join(
            config_dir, "slice_key"
        )
        sliver_pub_path = (
            rc.get("FABRIC_SLICE_PUBLIC_KEY_FILE") or f"{sliver_key_path}.pub"
        )
        ssh_config_path = rc.get("FABRIC_BASTION_SSH_CONFIG_FILE") or os.path.join(
            config_dir, "ssh_config"
        )

        # Check if existing token is expired
        token_needs_refresh = False
        if not overwrite and os.path.exists(config_token_path):
            token_needs_refresh = _is_token_expired(config_token_path)
            if token_needs_refresh:
                click.echo(
                    f"Existing token at {config_token_path} is expired, will refresh..."
                )

        # Create or refresh token
        if overwrite or not os.path.exists(config_token_path) or token_needs_refresh:
            cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

            from fabrictestbed.external_api.credmgr_client import CredmgrClient

            client = CredmgrClient(
                credmgr_host=cm, cookie_name=cookie_name or "fabric-service"
            )

            # Try refreshing if token exists and has a refresh_token
            refreshed = False
            if token_needs_refresh:
                try:
                    with open(config_token_path, "r") as f:
                        existing = json.load(f)
                    refresh_token = existing.get("refresh_token")
                    if refresh_token:
                        click.echo("Refreshing token...")
                        client.refresh(
                            refresh_token=refresh_token,
                            scope=scope,
                            project_id=pid,
                            project_name=pname,
                            file_path=config_token_path,
                            return_fmt="dto",
                        )
                        click.echo(f"  Token refreshed at: {config_token_path}")
                        refreshed = True
                except Exception:
                    click.echo("  Refresh failed, creating new token...")

            if not refreshed:
                click.echo("Creating token...")
                client.create_cli(
                    scope=scope,
                    project_id=pid,
                    project_name=pname,
                    lifetime_hours=lifetime,
                    comment="Create Token via CLI configure",
                    file_path=config_token_path,
                    open_browser=not no_browser,
                    return_fmt="dto",
                )
                click.echo(f"  Token saved at: {config_token_path}")
        else:
            click.echo(
                f"Token at {config_token_path} is valid, skipping (use --overwrite to replace)"
            )

        # Build FabricManagerV2 using the resolved token path
        fm = __get_fabric_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=pid,
            token_location=config_token_path,
            project_name=pname,
        )

        # If no project ID specified, use the first active project
        if not pid:
            click.echo("No project ID specified, fetching projects...")
            projects = fm.get_project_info()
            if projects:
                pid = projects[0].get("uuid")
                pname = projects[0].get("name")
                click.echo(f"Using project: {pname} ({pid})")
            else:
                raise click.ClickException("No active projects found for this user")

        # Fetch user info to get bastion_login
        click.echo("Fetching user info...")
        user_info = fm.get_user_info()
        bastion_login = user_info.get("bastion_login", "")
        if not bastion_login:
            raise click.ClickException(
                "Could not determine bastion_login from user info"
            )
        click.echo(f"Bastion username: {bastion_login}")

        # Validate bastion key against server using fingerprint
        bastion_valid = False
        if not overwrite:
            click.echo("Checking bastion key against server...")
            bastion_valid = _is_key_valid_on_server(fm, bastion_pub_path, "bastion")

        # Generate bastion SSH keys
        if overwrite or not bastion_valid:
            if not overwrite and os.path.exists(bastion_key_path):
                click.echo(
                    f"Bastion key at {bastion_key_path} missing or expired on server, regenerating..."
                )
            else:
                click.echo("Generating bastion SSH keys...")
            bastion_keys = fm.create_ssh_keys(
                key_type="bastion",
                description="bastion-key-via-cli",
                comment="fabric-bastion-key",
            )
            if bastion_keys:
                key_data = bastion_keys[0]
                _write_key_file(
                    bastion_key_path, key_data.get("private_openssh", ""), private=True
                )
                _write_key_file(
                    bastion_pub_path, key_data.get("public_openssh", ""), private=False
                )
                click.echo(f"  {bastion_key_path}")
                click.echo(f"  {bastion_pub_path}")
        else:
            click.echo(
                f"Bastion key at {bastion_key_path} is valid (fingerprint matches server), skipping"
            )

        # Sliver keys — only generate if files don't exist (user may have their own keys)
        if overwrite or not os.path.exists(sliver_key_path):
            click.echo("Generating sliver SSH keys...")
            sliver_keys = fm.create_ssh_keys(
                key_type="sliver",
                description="sliver-key-via-cli",
                comment="fabric-sliver-key",
            )
            if sliver_keys:
                key_data = sliver_keys[0]
                _write_key_file(
                    sliver_key_path, key_data.get("private_openssh", ""), private=True
                )
                _write_key_file(
                    sliver_pub_path, key_data.get("public_openssh", ""), private=False
                )
                click.echo(f"  {sliver_key_path}")
                click.echo(f"  {sliver_pub_path}")
        else:
            click.echo(
                f"Sliver key exists at {sliver_key_path}, skipping (use --overwrite to replace)"
            )

        # Write ssh_config
        if overwrite or not os.path.exists(ssh_config_path):
            click.echo("Writing ssh_config...")
            ssh_config = (
                f"UserKnownHostsFile /dev/null\n"
                f"StrictHostKeyChecking no\n"
                f"ServerAliveInterval 120\n"
                f"\n"
                f"Host {_BASTION_HOST}\n"
                f"     User {bastion_login}\n"
                f"     ForwardAgent yes\n"
                f"     Hostname %h\n"
                f"     IdentityFile {bastion_key_path}\n"
                f"     IdentitiesOnly yes\n"
                f"\n"
                f"Host * !{_BASTION_HOST}\n"
                f"     ProxyJump {bastion_login}@{_BASTION_HOST}:22\n"
            )
            with open(ssh_config_path, "w") as f:
                f.write(ssh_config)
            click.echo(f"  {ssh_config_path}")
        else:
            click.echo(
                f"ssh_config exists at {ssh_config_path}, skipping (use --overwrite to replace)"
            )

        # Write fabric_rc
        fabric_rc_path = os.path.join(config_dir, "fabric_rc")
        if overwrite or not os.path.exists(fabric_rc_path):
            click.echo("Writing fabric_rc...")
            fabric_rc_content = (
                f"export FABRIC_CREDMGR_HOST={cm}\n"
                f"export FABRIC_ORCHESTRATOR_HOST={oc}\n"
                f"export FABRIC_CORE_API_HOST={core}\n"
                f"export FABRIC_TOKEN_LOCATION={config_token_path}\n"
                f"export FABRIC_PROJECT_ID={pid}\n"
                f"export FABRIC_BASTION_HOST={_BASTION_HOST}\n"
                f"export FABRIC_BASTION_USERNAME={bastion_login}\n"
                f"export FABRIC_BASTION_KEY_LOCATION={bastion_key_path}\n"
                f"export FABRIC_SLICE_PRIVATE_KEY_FILE={sliver_key_path}\n"
                f"export FABRIC_SLICE_PUBLIC_KEY_FILE={sliver_pub_path}\n"
                f"export FABRIC_BASTION_SSH_CONFIG_FILE={ssh_config_path}\n"
            )
            with open(fabric_rc_path, "w") as f:
                f.write(fabric_rc_content)
            click.echo(f"  {fabric_rc_path}")
        else:
            click.echo(f"fabric_rc exists, skipping (use --overwrite to replace)")

        click.echo("\nConfiguration complete!")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


def _write_key_file(path, content, private=True):
    """Write an SSH key file with appropriate permissions."""
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o600 if private else 0o644)


def _is_token_expired(token_path):
    """Check if the token in a JSON file is expired."""
    try:
        with open(token_path, "r") as f:
            data = json.load(f)
        id_token = data.get("id_token")
        if not id_token:
            return True
        from fabrictestbed.util.auth_provider import AuthProvider

        auth = AuthProvider.from_token(id_token=id_token)
        return auth.is_expired()
    except Exception:
        return True


def _is_key_valid_on_server(fm, pub_key_path, key_type):
    """Check if a local SSH public key exists and matches a non-expired key on the server.

    Reads the local public key file, computes its fingerprint, then checks
    against the server's SSH keys (filtered by key_type and expiration).
    Returns True only if the local key's fingerprint matches a valid server key.
    """
    try:
        if not os.path.exists(pub_key_path):
            return False
        with open(pub_key_path, "r") as f:
            local_pub_key = f.read().strip()
        if not local_pub_key:
            return False

        from fss_utils.sshkey import FABRICSSHKey

        local_fingerprint = FABRICSSHKey(local_pub_key).get_fingerprint()

        user_info = fm.get_user_info()
        server_keys = user_info.get("sshkeys", []) or []

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        for key in server_keys:
            # Skip expired keys
            expires_on = key.get("expires_on")
            if expires_on:
                expires_dt = datetime.datetime.fromisoformat(expires_on)
                if now > expires_dt:
                    continue
            # Skip keys of a different type
            kt = key.get("fabric_key_type", "")
            if kt and kt != key_type:
                continue
            # Match by fingerprint
            if key.get("fingerprint") == local_fingerprint:
                return True
        return False
    except Exception:
        return False


# ── User / Projects ───────────────────────────────────────────────────────


def _print_user_info(user_data):
    """Print user info in dashboard style."""
    if not user_data:
        click.echo("No user information found.")
        return
    _header("User")
    click.echo()
    name = user_data.get("name") or user_data.get("Name") or "—"
    email = user_data.get("email") or user_data.get("Email") or "—"
    uid = user_data.get("uuid") or user_data.get("UUID") or "—"
    bastion = user_data.get("bastion_login") or user_data.get("Bastion Login") or "—"
    eppn = user_data.get("eppn") or "—"
    click.echo(f"  {_bold(name)}")
    _row(_kv("email:", _cyan(email)))
    _row(_kv("uuid:", uid))
    _row(_kv("bastion:", bastion))
    if eppn != "—":
        _row(_kv("eppn:", eppn))
    # Show any extra fields like fabric_roles, enrolled_on, etc.
    enrolled = user_data.get("enrolled_on") or user_data.get("created") or None
    if enrolled:
        _row(_kv("enrolled:", enrolled))
    roles = user_data.get("fabric_roles") or user_data.get("roles") or None
    if roles:
        if isinstance(roles, list):
            role_names = []
            for r in roles:
                if isinstance(r, dict):
                    role_names.append(r.get("name") or r.get("role") or str(r))
                else:
                    role_names.append(str(r))
            # Filter out entries containing UUIDs (project-specific roles like uuid-pm, uuid-po)
            _uuid_pat = re.compile(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                re.IGNORECASE,
            )
            role_names = [n for n in role_names if not _uuid_pat.search(n)]
            if role_names:
                _row(_kv("roles:", ", ".join(role_names)))
        else:
            _row(_kv("roles:", str(roles)))
    click.echo()
    _footer()


def _print_projects(projects_list):
    """Print projects in dashboard style."""
    if not projects_list:
        click.echo("No projects found.")
        return
    count = len(projects_list)
    _header("Projects", f"{count} project{'s' if count != 1 else ''}")
    click.echo()
    for proj in projects_list:
        name = proj.get("name") or proj.get("Name") or "—"
        uid = proj.get("uuid") or proj.get("UUID") or "—"
        active = proj.get("active", proj.get("Active", None))
        desc = proj.get("description") or proj.get("Description") or None
        created = proj.get("created") or proj.get("created_time") or None
        expires = proj.get("expires_on") or None

        # API filters out expired projects, so if active field is absent they're active
        if active is False:
            state_str = click.style("● Inactive", fg="red", bold=True)
        else:
            state_str = click.style("● Active", fg="green", bold=True)

        click.echo(f"  {_bold(name)}   {state_str}")
        _row(_kv("uuid:", _dim(uid)))

        if desc:
            _row(_kv("desc:", desc))

        # Roles from memberships
        memberships = proj.get("memberships", {})
        if memberships:
            roles = []
            if memberships.get("is_owner"):
                roles.append(click.style("owner", fg="cyan", bold=True))
            if memberships.get("is_lead"):
                roles.append(click.style("lead", fg="yellow", bold=True))
            if memberships.get("is_member"):
                roles.append(click.style("member", fg="green"))
            if memberships.get("is_creator"):
                roles.append(click.style("creator", fg="magenta"))
            if roles:
                _row(_kv("roles:", "  ".join(roles)))

        # Dates
        date_parts = []
        if created:
            date_parts.append(_kv("created:", created))
        if expires:
            date_parts.append(_kv("expires:", expires))
        if date_parts:
            _row(*date_parts)

        # Tags / facility
        tags = proj.get("tags") or None
        facility = proj.get("facility") or None
        if tags:
            tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
            _row(_kv("tags:", tag_str))
        if facility:
            _row(_kv("facility:", facility))

        click.echo()
    _footer()


@click.group()
@click.pass_context
def user(ctx):
    """User and project information

    Query user info and project memberships.
    """


@user.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option(
    "--uuid", default=None, help="User UUID to query (defaults to current user)"
)
@click.option("--email", default=None, help="User email to query")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def info(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    scope: str,
    uuid: str,
    email: str,
    as_json: bool,
):
    """Get user information

    Retrieve user details including email, UUID, and bastion login.
    """
    try:
        fm = __get_fabric_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        result = fm.get_user_info(uuid=uuid, email=email)
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            _print_user_info(result)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@user.command()
@click.option("--cmhost", help="Credential Manager host", default=None)
@click.option("--ochost", help="Orchestrator host", default=None)
@click.option(
    "--location",
    help="Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ~/work/fabric_config/id_token.json)",
    default=None,
)
@click.option("--projectid", default=None, help="Project UUID")
@click.option("--projectname", default=None, help="Project name")
@click.option(
    "--scope",
    type=click.Choice(["cf", "mf", "all"], case_sensitive=False),
    default="all",
    help="Token scope",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def projects(
    ctx,
    cmhost: str,
    ochost: str,
    location: str,
    projectid: str,
    projectname: str,
    scope: str,
    as_json: bool,
):
    """List user projects

    Show all projects the current user belongs to.
    """
    try:
        fm = __get_fabric_manager(
            cm_host=cmhost,
            oc_host=ochost,
            project_id=projectid,
            scope=scope,
            token_location=location,
        )
        result = fm.get_project_info(
            project_id=projectid or "all", project_name=projectname or "all"
        )
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            _print_projects(result)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


cli.add_command(tokens)
cli.add_command(slices)
cli.add_command(resources)
cli.add_command(user)
cli.add_command(configure)
