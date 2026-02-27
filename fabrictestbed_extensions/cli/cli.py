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
import os

import json
import click

from fabrictestbed.util.constants import Constants

_DEFAULT_CREDMGR_HOST = "cm.fabric-testbed.net"
_DEFAULT_ORCHESTRATOR_HOST = "orchestrator.fabric-testbed.net"
_DEFAULT_CORE_API_HOST = "uis.fabric-testbed.net"
_FABRIC_RC_PATH = os.path.expanduser("~/work/fabric_config/fabric_rc")
_DEFAULT_TOKEN_DIR = os.path.expanduser("~/work/fabric_config")
_DEFAULT_TOKEN_PATH = os.path.join(_DEFAULT_TOKEN_DIR, "tokens.json")


def _load_fabric_rc():
    """Load config from ~/work/fabric_config/fabric_rc if it exists.

    Returns a dict of key-value pairs. Supports 'export KEY=VALUE' and
    'KEY=VALUE' lines; comments and blank lines are ignored.
    """
    config = {}
    if not os.path.exists(_FABRIC_RC_PATH):
        return config
    try:
        with open(_FABRIC_RC_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[len('export '):]
                if '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        config[key] = value
    except Exception:
        pass
    return config


def __get_fabric_manager(*, oc_host=None, cm_host=None, project_id=None,
                         scope="all", token_location=None, project_name=None):
    """Construct a FabricManagerV2 from CLI args, env vars, fabric_rc, and defaults."""
    from fabrictestbed.fabric_manager_v2 import FabricManagerV2
    rc = _load_fabric_rc()
    cm = cm_host or os.getenv(Constants.FABRIC_CREDMGR_HOST) or rc.get(Constants.FABRIC_CREDMGR_HOST) or _DEFAULT_CREDMGR_HOST
    oc = oc_host or os.getenv(Constants.FABRIC_ORCHESTRATOR_HOST) or rc.get(Constants.FABRIC_ORCHESTRATOR_HOST) or _DEFAULT_ORCHESTRATOR_HOST
    pid = project_id or os.getenv(Constants.FABRIC_PROJECT_ID) or rc.get(Constants.FABRIC_PROJECT_ID)
    pname = project_name or os.getenv(Constants.FABRIC_PROJECT_NAME) or rc.get(Constants.FABRIC_PROJECT_NAME)
    tl = token_location or os.getenv(Constants.FABRIC_TOKEN_LOCATION) or rc.get(Constants.FABRIC_TOKEN_LOCATION) or _DEFAULT_TOKEN_PATH
    core = os.getenv(Constants.FABRIC_CORE_API_HOST) or rc.get(Constants.FABRIC_CORE_API_HOST) or _DEFAULT_CORE_API_HOST
    return FabricManagerV2(
        credmgr_host=cm, orchestrator_host=oc, core_api_host=core,
        token_location=tl, project_id=pid, project_name=pname, scope=scope,
    )


def __resolve_tokenlocation(tokenlocation: str) -> str:
    """Resolve token file location from arg, env var, fabric_rc, or default to ~/work/fabric_config/tokens.json."""
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


def _print_slices(slices_list):
    """Print slices in a compact, human-readable table."""
    if not slices_list:
        click.echo("No slices found.")
        return
    for s in slices_list:
        state = s.get("state", "Unknown")
        name = s.get("name", "—")
        sid = s.get("slice_id", "—")
        proj = s.get("project_name") or s.get("project_id") or "—"
        lease_end = s.get("lease_end_time") or "—"
        click.echo(f"  {name} [{state}]  id={sid}")
        click.echo(f"      project: {proj}  lease_end: {lease_end}")


def _print_slivers(slivers_list):
    """Print slivers in a compact, human-readable format."""
    if not slivers_list:
        click.echo("No slivers found.")
        return
    for sv in slivers_list:
        name = sv.get("name") or "—"
        stype = sv.get("type") or sv.get("sliver_type") or "—"
        site = sv.get("site") or "—"
        state = sv.get("state") or "—"
        sid = sv.get("sliver_id") or "—"
        mgmt_ip = sv.get("mgmt_ip")

        header = f"  {name} [{stype}] @ {site}  state={state}  id={sid}"
        if mgmt_ip:
            header += f"  mgmt_ip={mgmt_ip}"
        click.echo(header)

        cap = sv.get("capacities")
        if cap and isinstance(cap, dict):
            parts = []
            if "core" in cap:
                parts.append(f"core: {_fmt_number(cap['core'])}")
            if "ram" in cap:
                parts.append(f"ram: {_fmt_number(cap['ram'])} G")
            if "disk" in cap:
                parts.append(f"disk: {_fmt_number(cap['disk'])} G")
            if parts:
                click.echo(f"      capacities: {{ {', '.join(parts)} }}")

        alloc = sv.get("label_allocations")
        if alloc and isinstance(alloc, dict):
            parent = alloc.get("instance_parent")
            if parent:
                click.echo(f"      host: {parent}")

        image = sv.get("image_ref")
        if image:
            click.echo(f"      image: {image}")

        comps = sv.get("components") or []
        if comps:
            click.echo("      Components:")
            for c in comps:
                cname = c.get("Name") or c.get("name") or "—"
                cmodel = c.get("Model") or c.get("model") or ""
                ctype = c.get("Type") or c.get("type") or ""
                label = f"{ctype} {cmodel}".strip() if ctype or cmodel else ""
                click.echo(f"          {cname}: {label}" if label else f"          {cname}")

        ifaces = sv.get("interfaces") or []
        if ifaces:
            click.echo("      Interfaces:")
            for ifc in ifaces:
                iname = ifc.get("Name") or ifc.get("name") or "—"
                itype = ifc.get("Type") or ifc.get("type") or ""
                click.echo(f"          {iname}: {itype}" if itype else f"          {iname}")


def _print_sites(sites_list):
    """Print sites in a compact, human-readable format."""
    if not sites_list:
        click.echo("No sites found.")
        return
    for site in sites_list:
        name = site.get("name") or "—"
        state = site.get("state") or "—"
        maint_mode = site.get("maint_mode", False)
        location = site.get("location") or {}
        lat = location.get("latitude", "—")
        lon = location.get("longitude", "—")

        status = f"[MAINT]" if maint_mode else f"[{state}]"
        click.echo(f"  {name} {status}")
        click.echo(f"      location: {lat}, {lon}")

        # Print host counts
        hosts = site.get("hosts", [])
        if hosts:
            click.echo(f"      hosts: {len(hosts)}")
            # Count available cores/ram/disk
            total_cores = sum(h.get("capacities", {}).get("core", 0) for h in hosts)
            total_ram = sum(h.get("capacities", {}).get("ram", 0) for h in hosts)
            total_disk = sum(h.get("capacities", {}).get("disk", 0) for h in hosts)
            click.echo(f"      total capacity: {_fmt_number(total_cores)} cores, {_fmt_number(total_ram)} G ram, {_fmt_number(total_disk)} G disk")


@click.group()
@click.option('-v', '--verbose', is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose


@click.group()
@click.pass_context
def tokens(ctx):
    """Token management

    Manage FABRIC identity and refresh tokens. Set $FABRIC_CREDMGR_HOST
    to avoid passing --cmhost on every command. Set $FABRIC_TOKEN_LOCATION
    to set the default token file path (defaults to ./tokens.json).
    """


@tokens.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--projectid', default=None, help='Project UUID (uses first project if not specified)')
@click.option('--projectname', default=None, help='Project name (uses first project if not specified)')
@click.option('--lifetime', default=4, help='Token lifetime in hours')
@click.option('--comment', default=None, help='Comment/note to associate with the token')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--tokenlocation', help='Path to save token JSON (defaults to ./tokens.json)', default=None)
@click.option('--no-browser', is_flag=True, default=False, help='Do not attempt to open a browser automatically')
@click.option('--code-file', default=None, type=click.Path(exists=True),
              help='File containing the base64 authorization code (for remote/headless use)')
@click.pass_context
def create(ctx, cmhost: str, projectid: str, projectname: str, lifetime: int, comment: str,
           scope: str, tokenlocation: str, no_browser: bool, code_file: str):
    """Create token

    Opens a browser for CILogon authentication (or prints the URL if the
    browser cannot be opened). After login, the token is automatically
    captured via a localhost callback. If running on a remote VM, press
    Ctrl+C and paste the authorization code shown in the browser.

    Token is saved to --tokenlocation, $FABRIC_TOKEN_LOCATION, or
    ./tokens.json (in that order). If no project is specified, the
    user's first project is used.
    """
    try:
        cmhost = __resolve_cmhost(cmhost)
        tokenlocation = __resolve_tokenlocation(tokenlocation)
        cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

        from fabrictestbed.external_api.credmgr_client import CredmgrClient
        client = CredmgrClient(credmgr_host=cmhost,
                                cookie_name=cookie_name or "fabric-service")

        rc = _load_fabric_rc()
        if projectid is None:
            projectid = os.getenv(Constants.FABRIC_PROJECT_ID) or rc.get(Constants.FABRIC_PROJECT_ID)
        if projectname is None:
            projectname = os.getenv(Constants.FABRIC_PROJECT_NAME) or rc.get(Constants.FABRIC_PROJECT_NAME)

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
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--projectname', default=None, help='Project name')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.pass_context
def refresh(ctx, cmhost: str, tokenlocation: str, projectid: str, projectname: str, scope: str):
    """Refresh token

    Reads the existing token file, uses the refresh_token to obtain a new
    identity token, and saves the result back. Token file is read from
    --tokenlocation, $FABRIC_TOKEN_LOCATION, or ./tokens.json.
    """
    try:
        cmhost = __resolve_cmhost(cmhost)
        tokenlocation = __resolve_tokenlocation(tokenlocation)

        if not os.path.exists(tokenlocation):
            raise click.ClickException(f"Token file not found: {tokenlocation}")

        with open(tokenlocation, 'r') as f:
            existing = json.load(f)

        refresh_token = existing.get("refresh_token")
        if not refresh_token:
            raise click.ClickException(f"No refresh_token found in {tokenlocation}")

        rc = _load_fabric_rc()
        if projectid is None:
            projectid = os.getenv(Constants.FABRIC_PROJECT_ID) or rc.get(Constants.FABRIC_PROJECT_ID)
        if projectname is None:
            projectname = os.getenv(Constants.FABRIC_PROJECT_NAME) or rc.get(Constants.FABRIC_PROJECT_NAME)

        cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

        from fabrictestbed.external_api.credmgr_client import CredmgrClient
        client = CredmgrClient(credmgr_host=cmhost,
                                cookie_name=cookie_name or "fabric-service")

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
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to ./tokens.json)', default=None)
@click.option('--refreshtoken', help='Refresh token to revoke (overrides token file)', default=None)
@click.option('--identitytoken', help='Identity token for authentication (overrides token file)', default=None)
@click.option('--tokenhash', help='SHA256 hash of the token to revoke', default=None)
@click.pass_context
def revoke(ctx, cmhost: str, tokenlocation: str, refreshtoken: str, identitytoken: str, tokenhash: str):
    """Revoke token

    Revokes a refresh or identity token. Reads tokens from --tokenlocation
    (or $FABRIC_TOKEN_LOCATION or ./tokens.json) unless --refreshtoken
    and --identitytoken are provided explicitly.

    If --refreshtoken is provided, it is revoked. Otherwise the identity
    token (by --tokenhash) is revoked.
    """
    try:
        cmhost = __resolve_cmhost(cmhost)
        cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

        # Load from file if explicit tokens not provided
        if refreshtoken is None and identitytoken is None:
            tokenlocation = __resolve_tokenlocation(tokenlocation)
            if not os.path.exists(tokenlocation):
                raise click.ClickException(f"Token file not found: {tokenlocation}")

            with open(tokenlocation, 'r') as f:
                file_tokens = json.load(f)

            refreshtoken = file_tokens.get("refresh_token")
            identitytoken = file_tokens.get("id_token")
            tokenhash = tokenhash or file_tokens.get("token_hash")

        if not identitytoken:
            raise click.ClickException("Identity token is required for revocation")

        from fabrictestbed.external_api.credmgr_client import CredmgrClient
        client = CredmgrClient(credmgr_host=cmhost,
                                cookie_name=cookie_name or "fabric-service")

        if refreshtoken:
            client.revoke(id_token=identitytoken, token_type="refresh",
                          refresh_token=refreshtoken)
        else:
            if not tokenhash:
                raise click.ClickException("Token hash is required to revoke an identity token")
            client.revoke(id_token=identitytoken, token_type="identity",
                          token_hash=tokenhash)

        click.echo("Token revoked successfully")
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e))


@tokens.command()
@click.option('--tokenlocation', help='Path to token JSON file to delete', default=None)
@click.pass_context
def clear_cache(ctx, tokenlocation):
    """Clear cached token

    Deletes the token file at --tokenlocation, $FABRIC_TOKEN_LOCATION,
    or ./tokens.json.
    """
    try:
        tokenlocation = __resolve_tokenlocation(tokenlocation)

        if os.path.exists(tokenlocation):
            os.remove(tokenlocation)
            click.echo(f"Token cache cleared: {tokenlocation}")
        else:
            click.echo(f"No token file found at: {tokenlocation}")

    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def slices(ctx):
    """Slice management

    Create, query, modify, and delete slices. Requires $FABRIC_ORCHESTRATOR_HOST,
    $FABRIC_CREDMGR_HOST, $FABRIC_TOKEN_LOCATION, and $FABRIC_PROJECT_ID.
    """


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', default=None, help='Slice UUID (omit to list all)')
@click.option('--name', default=None, help='Filter by slice name')
@click.option('--state', default=None, help='Filter by slice state')
@click.option('--all', 'show_all', is_flag=True, default=False, help='Include Dead and Closing slices')
@click.option('--limit', default=200, help='Maximum number of slices to return')
@click.option('--offset', default=0, help='Pagination offset')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON instead of table')
@click.pass_context
def query(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str,
          name: str, state: str, show_all: bool, limit: int, offset: int, as_json: bool):
    """Query slices

    List all slices or query a specific slice by --sliceid. By default,
    Dead and Closing slices are hidden; use --all to include them.
    Use --json for raw JSON output.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        states = [state] if state else None
        excludes = None if (show_all or state) else ["Dead", "Closing"]
        result = fm.list_slices(slice_id=sliceid, name=name, states=states, exclude_states=excludes,
                               limit=limit, offset=offset, return_fmt="dict")
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            _print_slices(result)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--slicename', help='Slice name', required=True)
@click.option('--slicegraph', help='Slice graph definition', required=True)
@click.option('--sshkey', help='SSH public key', required=True)
@click.option('--leaseend', help='Lease end time', default=None)
@click.pass_context
def create(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, slicename: str,
           slicegraph: str, sshkey: str, leaseend: str):
    """Create a slice

    Create a new slice with the given name, graph, and SSH key.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.create_slice(name=slicename, graph_model=slicegraph, ssh_keys=[sshkey],
                                 lease_end_time=leaseend, return_fmt="dict")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', help='Slice UUID', required=True)
@click.option('--slicegraph', help='Updated slice graph definition', required=True)
@click.pass_context
def modify(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str,
           slicegraph: str):
    """Modify a slice

    Update an existing slice with a new graph definition.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.modify_slice(slice_id=sliceid, graph_model=slicegraph, return_fmt="dict")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', help='Slice UUID', required=True)
@click.pass_context
def modifyaccept(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str):
    """Accept a modified slice

    Accept the pending modifications on a slice.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.accept_modify(slice_id=sliceid, return_fmt="dict")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', help='Slice UUID', required=True)
@click.pass_context
def delete(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str):
    """Delete a slice

    Delete a slice by --sliceid.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        fm.delete_slice(slice_id=sliceid)
        click.echo(f"Slice {sliceid} deleted successfully")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', help='Slice UUID', required=True)
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def get(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str, as_json: bool):
    """Get detailed slice information

    Retrieve full details about a specific slice including topology graph.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.get_slice(slice_id=sliceid, return_fmt="dict")
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            # Print slice overview
            click.echo(f"Slice: {result.get('name', '—')} [{result.get('state', 'Unknown')}]")
            click.echo(f"  ID: {result.get('slice_id', '—')}")
            click.echo(f"  Project: {result.get('project_name') or result.get('project_id', '—')}")
            click.echo(f"  Lease End: {result.get('lease_end_time', '—')}")
            click.echo(f"  Created: {result.get('lease_start_time', '—')}")

            # Print graph if available
            graph = result.get('graph_model')
            if graph:
                click.echo(f"\nTopology Graph (length: {len(graph)} chars)")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slices.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', help='Slice UUID', required=True)
@click.option('--days', type=int, default=None, help='Number of days to extend the lease')
@click.option('--leaseend', default=None, help='New lease end time (ISO format)')
@click.pass_context
def renew(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str,
          days: int, leaseend: str):
    """Renew a slice lease

    Extend the lease for a slice by specifying --days or an explicit --leaseend time.
    """
    try:
        if not days and not leaseend:
            raise click.ClickException("Either --days or --leaseend must be specified")

        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)

        # Calculate lease end time if days specified
        if days and not leaseend:
            from datetime import datetime, timedelta, timezone
            new_end = datetime.now(timezone.utc) + timedelta(days=days)
            leaseend = new_end.strftime("%Y-%m-%d %H:%M:%S %z")

        fm.renew_slice(slice_id=sliceid, lease_end_time=leaseend)
        click.echo(f"Slice {sliceid} renewed successfully")
        click.echo(f"  New lease end: {leaseend}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def slivers(ctx):
    """Sliver management

    Query slivers within a slice. Requires $FABRIC_ORCHESTRATOR_HOST,
    $FABRIC_CREDMGR_HOST, $FABRIC_TOKEN_LOCATION, and $FABRIC_PROJECT_ID.
    """


@slivers.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliceid', help='Slice UUID', required=True)
@click.option('--sliverid', default=None, help='Sliver UUID (omit to list all)')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON instead of table')
@click.pass_context
def query(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliceid: str, sliverid: str,
          as_json: bool):
    """Query slivers

    List all slivers in a slice, or query a specific sliver by --sliverid.
    Use --json for raw JSON output.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        if sliverid:
            result = fm.get_sliver(slice_id=sliceid, sliver_id=sliverid, return_fmt="dict")
        else:
            result = fm.list_slivers(slice_id=sliceid, return_fmt="dict")
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if isinstance(result, dict):
                result = [result]
            _print_slivers(result)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slivers.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliverid', help='Sliver UUID', required=True)
@click.pass_context
def reboot(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliverid: str):
    """Reboot a sliver

    Issue a reboot operation on a node sliver.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.os_reboot(sliver_id=sliverid, return_fmt="dict")
        click.echo(f"Reboot initiated for sliver {sliverid}")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slivers.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliverid', help='Sliver UUID', required=True)
@click.option('--keyname', default=None, help='SSH key name to add (from Core API)')
@click.option('--publickey', default=None, help='Raw public key string (must include key type)')
@click.pass_context
def addkey(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliverid: str,
           keyname: str, publickey: str):
    """Add SSH public key to a sliver

    Add an SSH public key to a node sliver. Provide either --keyname (to fetch
    from Core API) or --publickey (raw key string).
    """
    try:
        if not keyname and not publickey:
            raise click.ClickException("Either --keyname or --publickey must be specified")

        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.add_public_key(sliver_id=sliverid, sliver_key_name=keyname, sliver_public_key=publickey)
        click.echo(f"SSH key added to sliver {sliverid}")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slivers.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliverid', help='Sliver UUID', required=True)
@click.option('--keyname', default=None, help='SSH key name to remove (from Core API)')
@click.option('--publickey', default=None, help='Raw public key string (must include key type)')
@click.pass_context
def removekey(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliverid: str,
              keyname: str, publickey: str):
    """Remove SSH public key from a sliver

    Remove an SSH public key from a node sliver. Provide either --keyname (to fetch
    from Core API) or --publickey (raw key string).
    """
    try:
        if not keyname and not publickey:
            raise click.ClickException("Either --keyname or --publickey must be specified")

        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.remove_public_key(sliver_id=sliverid, sliver_key_name=keyname, sliver_public_key=publickey)
        click.echo(f"SSH key removed from sliver {sliverid}")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@slivers.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--sliverid', help='Sliver UUID', required=True)
@click.option('--operation', required=True,
              type=click.Choice(['cpuinfo', 'numainfo', 'cpupin', 'numatune', 'reboot', 'addkey', 'removekey', 'rescan']),
              help='POA operation to perform')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def poa(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, sliverid: str,
        operation: str, as_json: bool):
    """Perform operational action on a sliver

    Execute a POA operation on a node sliver. Supported operations:
    cpuinfo, numainfo, cpupin, numatune, reboot, addkey, removekey, rescan.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.poa_create(sliver_id=sliverid, operation=operation, return_fmt="dict")
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"POA '{operation}' initiated for sliver {sliverid}")
            if result and isinstance(result, list) and result:
                poa_id = result[0].get("poa_id", "—")
                state = result[0].get("state", "—")
                click.echo(f"  POA ID: {poa_id}")
                click.echo(f"  State: {state}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def resources(ctx):
    """Resource management

    Query available testbed resources. Requires $FABRIC_ORCHESTRATOR_HOST,
    $FABRIC_CREDMGR_HOST, and $FABRIC_PROJECT_ID.
    """


@resources.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--force', is_flag=True, default=False, help='Force a fresh snapshot instead of using cache')
@click.option('--summary', is_flag=True, default=False, help='Show JSON summary instead of full topology')
@click.option('--site', default=None, help='Filter by site name')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def query(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, force: bool,
          summary: bool, site: str, as_json: bool):
    """Query resources

    Show available testbed resources. Use --force to bypass the cache.
    Use --summary for a compact JSON overview. Use --site to filter by site name.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        if summary or site:
            result = fm.resources_summary(force_refresh=force)
            if site:
                # Filter by site
                sites = result.get("sites", [])
                filtered = [s for s in sites if s.get("name") == site or site.lower() in s.get("name", "").lower()]
                if not filtered:
                    click.echo(f"No site matching '{site}' found.")
                    return
                if as_json:
                    click.echo(json.dumps(filtered, indent=2))
                else:
                    _print_sites(filtered)
            else:
                if as_json:
                    click.echo(json.dumps(result, indent=2))
                else:
                    # Print human-readable summary
                    sites = result.get("sites", [])
                    _print_sites(sites)
        else:
            result = fm.resources(force_refresh=force)
            click.echo(result)
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
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to existing token JSON file (for authentication)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--projectname', default=None, help='Project name')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--lifetime', default=4, help='Token lifetime in hours')
@click.option('--no-browser', is_flag=True, default=False,
              help='Do not attempt to open a browser automatically')
@click.option('--config-dir', default=None,
              help='Config directory (default: current working directory)')
@click.option('--overwrite', is_flag=True, default=False,
              help='Overwrite existing keys and config files')
@click.pass_context
def setup(ctx, cmhost, ochost, tokenlocation, projectid, projectname, scope,
          lifetime, no_browser, config_dir, overwrite):
    """Set up FABRIC environment

    Creates the config directory, creates a token, generates bastion and
    sliver SSH keys, and writes ssh_config and fabric_rc files.
    """
    try:
        config_dir = os.path.expanduser(config_dir) if config_dir else _DEFAULT_TOKEN_DIR
        os.makedirs(config_dir, exist_ok=True)
        click.echo(f"Config directory: {config_dir}")

        # Resolve hosts
        rc = _load_fabric_rc()
        cm = cmhost or os.getenv(Constants.FABRIC_CREDMGR_HOST) or rc.get(Constants.FABRIC_CREDMGR_HOST) or _DEFAULT_CREDMGR_HOST
        oc = ochost or os.getenv(Constants.FABRIC_ORCHESTRATOR_HOST) or rc.get(Constants.FABRIC_ORCHESTRATOR_HOST) or _DEFAULT_ORCHESTRATOR_HOST
        core = os.getenv(Constants.FABRIC_CORE_API_HOST) or rc.get(Constants.FABRIC_CORE_API_HOST) or _DEFAULT_CORE_API_HOST
        pid = projectid or os.getenv(Constants.FABRIC_PROJECT_ID) or rc.get(Constants.FABRIC_PROJECT_ID)
        pname = projectname or os.getenv(Constants.FABRIC_PROJECT_NAME) or rc.get(Constants.FABRIC_PROJECT_NAME)

        # Token location in the config directory
        config_token_path = os.path.join(config_dir, "tokens.json")

        # Check if existing token is expired
        token_needs_refresh = False
        if not overwrite and os.path.exists(config_token_path):
            token_needs_refresh = _is_token_expired(config_token_path)
            if token_needs_refresh:
                click.echo("Existing token is expired, will refresh...")

        # Create or refresh token
        if overwrite or not os.path.exists(config_token_path) or token_needs_refresh:
            cookie_name = os.getenv(Constants.FABRIC_COOKIE_NAME)

            from fabrictestbed.external_api.credmgr_client import CredmgrClient
            client = CredmgrClient(credmgr_host=cm,
                                    cookie_name=cookie_name or "fabric-service")

            # Try refreshing if token exists and has a refresh_token
            refreshed = False
            if token_needs_refresh:
                try:
                    with open(config_token_path, 'r') as f:
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
            click.echo(f"Token exists and is valid, skipping (use --overwrite to replace)")

        # Build FabricManagerV2 using the config dir token
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=pid,
                                  token_location=config_token_path, project_name=pname)

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
            raise click.ClickException("Could not determine bastion_login from user info")
        click.echo(f"Bastion username: {bastion_login}")

        # Key file paths
        bastion_key_path = os.path.join(config_dir, "fabric_bastion_key")
        bastion_pub_path = os.path.join(config_dir, "fabric_bastion_key.pub")
        sliver_key_path = os.path.join(config_dir, "slice_key")
        sliver_pub_path = os.path.join(config_dir, "slice_key.pub")

        # Check if bastion keys still exist on the server (they expire server-side)
        bastion_keys_valid = False
        sliver_keys_valid = False
        if not overwrite and (os.path.exists(bastion_key_path) or os.path.exists(sliver_key_path)):
            click.echo("Checking SSH keys on server...")
            try:
                server_keys = fm.get_ssh_keys()
                for k in (server_keys or []):
                    kt = k.get("keytype") or k.get("ssh_key_type") or ""
                    if "bastion" in kt.lower():
                        bastion_keys_valid = True
                    if "sliver" in kt.lower():
                        sliver_keys_valid = True
            except Exception:
                click.echo("  Could not verify keys on server, will regenerate")

        # Generate bastion SSH keys
        need_bastion = overwrite or not os.path.exists(bastion_key_path)
        if not need_bastion and not bastion_keys_valid and os.path.exists(bastion_key_path):
            click.echo("Bastion keys expired on server, regenerating...")
            need_bastion = True
        if need_bastion:
            click.echo("Generating bastion SSH keys...")
            bastion_keys = fm.create_ssh_keys(key_type="bastion",
                                               description="bastion-key-via-cli",
                                               comment="fabric-bastion-key")
            if bastion_keys:
                key_data = bastion_keys[0]
                _write_key_file(bastion_key_path, key_data.get("private_openssh", ""), private=True)
                _write_key_file(bastion_pub_path, key_data.get("public_openssh", ""), private=False)
                click.echo(f"  {bastion_key_path}")
                click.echo(f"  {bastion_pub_path}")
        else:
            click.echo(f"Bastion keys exist and are valid, skipping (use --overwrite to replace)")

        # Generate sliver SSH keys
        need_sliver = overwrite or not os.path.exists(sliver_key_path)
        if not need_sliver and not sliver_keys_valid and os.path.exists(sliver_key_path):
            click.echo("Sliver keys expired on server, regenerating...")
            need_sliver = True
        if need_sliver:
            click.echo("Generating sliver SSH keys...")
            sliver_keys = fm.create_ssh_keys(key_type="sliver",
                                              description="sliver-key-via-cli",
                                              comment="fabric-sliver-key")
            if sliver_keys:
                key_data = sliver_keys[0]
                _write_key_file(sliver_key_path, key_data.get("private_openssh", ""), private=True)
                _write_key_file(sliver_pub_path, key_data.get("public_openssh", ""), private=False)
                click.echo(f"  {sliver_key_path}")
                click.echo(f"  {sliver_pub_path}")
        else:
            click.echo(f"Sliver keys exist and are valid, skipping (use --overwrite to replace)")

        # Write ssh_config
        ssh_config_path = os.path.join(config_dir, "ssh_config")
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
            with open(ssh_config_path, 'w') as f:
                f.write(ssh_config)
            click.echo(f"  {ssh_config_path}")
        else:
            click.echo(f"ssh_config exists, skipping (use --overwrite to replace)")

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
            with open(fabric_rc_path, 'w') as f:
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
    with open(path, 'w') as f:
        f.write(content)
    os.chmod(path, 0o600 if private else 0o644)


def _is_token_expired(token_path):
    """Check if the token in a JSON file is expired."""
    try:
        with open(token_path, 'r') as f:
            data = json.load(f)
        id_token = data.get("id_token")
        if not id_token:
            return True
        from fabrictestbed.util.auth_provider import AuthProvider
        auth = AuthProvider.from_token(id_token=id_token)
        return auth.is_expired()
    except Exception:
        return True


@click.group()
@click.pass_context
def sshkeys(ctx):
    """SSH key management

    Manage SSH keys registered in FABRIC Core API.
    """


@sshkeys.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--uuid', default=None, help='User UUID to query (defaults to current user)')
@click.option('--email', default=None, help='User email to query')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def query(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str,
          uuid: str, email: str, as_json: bool):
    """Query SSH keys

    List SSH keys for the current user or specified user.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.get_ssh_keys(uuid=uuid, email=email)
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if not result:
                click.echo("No SSH keys found.")
            else:
                for key in result:
                    key_type = key.get("keytype") or key.get("ssh_key_type") or "—"
                    comment = key.get("comment") or "—"
                    created = key.get("created_on") or key.get("created") or "—"
                    fingerprint = key.get("fingerprint") or "—"
                    click.echo(f"  {comment} [{key_type}]")
                    click.echo(f"      fingerprint: {fingerprint}")
                    click.echo(f"      created: {created}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@sshkeys.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--keytype', required=True, type=click.Choice(['sliver', 'bastion'], case_sensitive=False),
              help='Key type to create')
@click.option('--description', required=True, help='Description for the key')
@click.option('--comment', default='ssh-key-via-cli', help='Comment for the key')
@click.pass_context
def create(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str,
           keytype: str, description: str, comment: str):
    """Create SSH key pair

    Generate and register a new SSH key pair.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.create_ssh_keys(key_type=keytype, description=description, comment=comment)
        click.echo(f"SSH key created successfully")
        click.echo(json.dumps(result, indent=2))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def user(ctx):
    """User and project information

    Query user info and project memberships.
    """


@user.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--uuid', default=None, help='User UUID to query (defaults to current user)')
@click.option('--email', default=None, help='User email to query')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def info(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str,
         uuid: str, email: str, as_json: bool):
    """Get user information

    Retrieve user details including email, UUID, and bastion login.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.get_user_info(uuid=uuid, email=email)
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"User: {result.get('name', '—')}")
            click.echo(f"  Email: {result.get('email', '—')}")
            click.echo(f"  UUID: {result.get('uuid', '—')}")
            click.echo(f"  Bastion login: {result.get('bastion_login', '—')}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@user.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--projectname', default=None, help='Project name')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def projects(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, projectname: str,
             scope: str, as_json: bool):
    """List user projects

    Show all projects the current user belongs to.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.get_project_info(project_id=projectid or "all", project_name=projectname or "all")
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if not result:
                click.echo("No projects found.")
            else:
                for proj in result:
                    name = proj.get("name", "—")
                    uuid = proj.get("uuid", "—")
                    active = proj.get("active", False)
                    status = "[ACTIVE]" if active else "[INACTIVE]"
                    click.echo(f"  {name} {status}")
                    click.echo(f"      UUID: {uuid}")
                    memberships = proj.get("memberships", {})
                    if memberships:
                        roles = []
                        if memberships.get("is_owner"):
                            roles.append("owner")
                        if memberships.get("is_lead"):
                            roles.append("lead")
                        if memberships.get("is_member"):
                            roles.append("member")
                        if roles:
                            click.echo(f"      roles: {', '.join(roles)}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def storage(ctx):
    """Storage volume management

    Query FABRIC storage volumes.
    """


@storage.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--uuid', default=None, help='Storage volume UUID')
@click.option('--limit', default=200, help='Maximum number of volumes to return')
@click.option('--offset', default=0, help='Pagination offset')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def query(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str,
          uuid: str, limit: int, offset: int, as_json: bool):
    """Query storage volumes

    List all storage volumes or get details of a specific volume by UUID.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        if uuid:
            result = fm.get_storage(uuid=uuid)
        else:
            result = fm.list_storage(offset=offset, limit=limit)

        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if not result:
                click.echo("No storage volumes found.")
            else:
                volumes = result if isinstance(result, list) else [result]
                for vol in volumes:
                    name = vol.get("name", "—")
                    vol_uuid = vol.get("uuid", "—")
                    size = vol.get("size", "—")
                    site = vol.get("site", "—")
                    click.echo(f"  {name} [{site}]")
                    click.echo(f"      UUID: {vol_uuid}")
                    click.echo(f"      Size: {size}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@click.group()
@click.pass_context
def artifacts(ctx):
    """Artifact management

    Create, list, and manage FABRIC artifacts.
    """


@artifacts.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--artifactid', default=None, help='Artifact UUID')
@click.option('--search', default=None, help='Search by artifact title')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output raw JSON')
@click.pass_context
def query(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str,
          artifactid: str, search: str, as_json: bool):
    """Query artifacts

    List all artifacts or search by title or UUID.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.list_artifacts(artifact_id=artifactid, search=search)
        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if not result:
                click.echo("No artifacts found.")
            else:
                for artifact in result:
                    title = artifact.get("title", "—")
                    uuid = artifact.get("uuid", "—")
                    visibility = artifact.get("visibility", "—")
                    authors = artifact.get("authors", [])
                    author_names = [a.get("name", "—") for a in authors] if authors else []
                    click.echo(f"  {title} [{visibility}]")
                    click.echo(f"      UUID: {uuid}")
                    if author_names:
                        click.echo(f"      Authors: {', '.join(author_names)}")
                    versions = artifact.get("versions", [])
                    if versions:
                        click.echo(f"      Versions: {len(versions)}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@artifacts.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--artifactid', required=True, help='Artifact UUID to delete')
@click.pass_context
def delete(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str, artifactid: str):
    """Delete an artifact

    Delete an artifact by UUID.
    """
    try:
        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        fm.delete_artifact(artifact_id=artifactid)
        click.echo(f"Artifact {artifactid} deleted successfully")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@artifacts.command()
@click.option('--cmhost', help='Credential Manager host', default=None)
@click.option('--ochost', help='Orchestrator host', default=None)
@click.option('--tokenlocation', help='Path to token JSON file (defaults to $FABRIC_TOKEN_LOCATION or ./tokens.json)', default=None)
@click.option('--projectid', default=None, help='Project UUID')
@click.option('--scope', type=click.Choice(['cf', 'mf', 'all'], case_sensitive=False),
              default='all', help='Token scope')
@click.option('--artifactid', default=None, help='Artifact UUID')
@click.option('--artifacttitle', default=None, help='Artifact title')
@click.option('--downloaddir', required=True, help='Directory to save downloaded file')
@click.option('--version', default=None, help='Specific version to download')
@click.pass_context
def download(ctx, cmhost: str, ochost: str, tokenlocation: str, projectid: str, scope: str,
             artifactid: str, artifacttitle: str, downloaddir: str, version: str):
    """Download an artifact

    Download an artifact file by UUID or title. Optionally specify --version.
    """
    try:
        if not artifactid and not artifacttitle:
            raise click.ClickException("Either --artifactid or --artifacttitle must be specified")

        fm = __get_fabric_manager(cm_host=cmhost, oc_host=ochost, project_id=projectid, scope=scope,
                                  token_location=tokenlocation)
        result = fm.download_artifact(download_dir=downloaddir, artifact_id=artifactid,
                                      artifact_title=artifacttitle, version=version)
        click.echo(f"Artifact downloaded to: {result}")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))

cli.add_command(tokens)
cli.add_command(slices)
cli.add_command(slivers)
cli.add_command(resources)
cli.add_command(sshkeys)
cli.add_command(user)
cli.add_command(storage)
cli.add_command(artifacts)
cli.add_command(configure)
