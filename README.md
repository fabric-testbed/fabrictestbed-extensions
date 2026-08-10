# fabrictestbed-extensions

[![pypi-badge]][pypy] [![api-docs-badge]][api-docs]

This is the implementation of a Python library, otherwise known as
"FABlib", for interacting with [FABRIC][fabric] testbed.

Your first encounter with FABlib might be through FABRIC project's
[JupyterHub instance][fabric-jupyter], where FABlib is pre-installed
for you. You will be presented with many examples of interacting with
FABRIC testbed and FABlib usage when you log in there. Those [notebook
sources][fabric-jupyter-examples] can be found on GitHub as well.

If you want to interact with FABRIC from Jupyter or a Python project
on your local development environment, that is possible too.  See
[Install the FABRIC Python API][fablib-install] and the notes below
for details.

FABlib API docs can be found [here][fablib-api-rtd].  If you have
questions about FABRIC or FABlib usage, please ask them in FABRIC
[forums].

## Installing FABlib

You can install released versions of FABlib from PyPI:

```console
$ pip install fabrictestbed-extensions
```

If you need the current development version of FABlib, install it from
the git repository:

```console
$ pip install git+https://github.com/fabric-testbed/fabrictestbed-extensions@main
```

Note that installing FABlib using either methods will also install a
number of dependencies, so you might want to install FABlib in a
virtual environment. Your favorite tool for managing virtual
environments ([venv], [virtualenv], or [virtualenvwrapper]) should
work. FABRIC team tends to favor virtualenvwrapper.

**NOTE:** This package has been tested and verified to work with Python versions 3.11 through 3.14.

## Using FABlib

Once installed, you can use FABlib in your Python projects:

```python
from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager

try:
    fablib = fablib_manager()
    fablib.show_config()
except Exception as e:
    print(f"Exception: {e}")
```

Please note that some [configuration] is required for this to work.

## Command-Line Interface

FABlib includes a CLI tool (`fabric-cli`) that is automatically installed
with the package. It provides commands for token management, slice
operations, resource queries, user info, and environment setup — all from
the terminal.

### Quick start

```console
# One-time setup: creates tokens, SSH keys, ssh_config, and fabric_rc
$ fabric-cli configure setup

# List your slices
$ fabric-cli slices list

# Check available testbed sites
$ fabric-cli resources sites
```

### Configuration

The CLI resolves settings from (highest to lowest priority):

1. Command-line options (`--cmhost`, `--location`, etc.)
2. Environment variables (`FABRIC_CREDMGR_HOST`, `FABRIC_TOKEN_LOCATION`, etc.)
3. Config file at `~/work/fabric_config/fabric_rc`
4. Built-in defaults

### Commands

#### `fabric-cli configure setup`

Interactive first-time setup. Creates the config directory, obtains a
token via browser-based CILogon authentication, generates bastion and
sliver SSH keys, and writes `ssh_config` and `fabric_rc` files. Re-run
to refresh expired tokens automatically; use `--overwrite` to regenerate
everything.

When `--config-dir` is specified, all files are read from and written to
that directory. An existing `fabric_rc` in the directory is used for
configuration; default paths outside the directory are not consulted.

```console
$ fabric-cli configure setup
$ fabric-cli configure setup --config-dir ~/my_fabric_config --overwrite
```

#### `fabric-cli tokens`

Manage FABRIC identity tokens.

```console
$ fabric-cli tokens create                    # Create a new token (opens browser)
$ fabric-cli tokens create --no-browser       # Print URL instead of opening browser
$ fabric-cli tokens create --location ~/my_tokens/id_token.json  # Save to custom path
$ fabric-cli tokens refresh                   # Refresh an existing token
$ fabric-cli tokens revoke                    # Revoke a token
```

#### `fabric-cli slices`

List, inspect, renew, and delete slices.

```console
$ fabric-cli slices list                      # List active slices
$ fabric-cli slices list --all                # Include Dead and Closing slices
$ fabric-cli slices show --name MySlice       # Show slice details
$ fabric-cli slices delete --name MySlice     # Delete a slice
$ fabric-cli slices renew --name MySlice --days 7  # Extend lease by 7 days
$ fabric-cli slices nodes --name MySlice      # List nodes in a slice
$ fabric-cli slices networks --name MySlice   # List networks in a slice
$ fabric-cli slices interfaces --name MySlice # List interfaces in a slice
$ fabric-cli slices slivers --name MySlice    # List slivers in a slice
```

#### `fabric-cli resources`

Query testbed resources.

```console
$ fabric-cli resources sites                  # List all sites with usage bars
$ fabric-cli resources sites --site TACC      # Show details for a specific site
$ fabric-cli resources hosts                  # List all hosts
$ fabric-cli resources hosts --site TACC      # Filter hosts by site
$ fabric-cli resources links                  # List inter-site network links
$ fabric-cli resources facility-ports         # List facility ports
```

#### `fabric-cli user`

Query user and project information.

```console
$ fabric-cli user info                        # Show current user info
$ fabric-cli user projects                    # List your projects
```

### Common options

Most commands accept the following options:

| Option              | Description                              |
|---------------------|------------------------------------------|
| `--cmhost`          | Credential Manager host                  |
| `--ochost`          | Orchestrator host                        |
| `--location`        | Path to token JSON file                  |
| `--projectid`       | Project UUID                             |
| `--scope`           | Token scope (`cf`, `mf`, or `all`)       |
| `--json`            | Output raw JSON instead of formatted text|

### Help

Use `--help` on any command or subcommand for full usage details:

```console
$ fabric-cli --help
$ fabric-cli slices --help
$ fabric-cli tokens create --help
```

## Contributing to FABlib

We welcome contributions in the form of bug reports, feature requests,
code patches, documentation updates, etc.  If you have ideas that can
help FABlib, please review the [guidelines] first.


<!-- URLs -->

[pypy]: https://pypi.org/project/fabrictestbed-extensions/
[pypi-badge]: https://img.shields.io/pypi/v/fabrictestbed-extensions (PyPI)

[api-docs]: https://fabric-fablib.readthedocs.io/en/latest/?badge=latest
[api-docs-badge]: https://readthedocs.org/projects/fabric-fablib/badge/?version=latest (Documentation Status)

[fabric]: https://fabric-testbed.net/
[forums]: https://learn.fabric-testbed.net/forums/

[fablib-api-rtd]: https://fabric-fablib.readthedocs.io/en/latest/

[venv]: https://docs.python.org/3/library/venv.html
[virtualenv]: https://virtualenv.pypa.io/en/latest/
[virtualenvwrapper]: https://virtualenvwrapper.readthedocs.io/en/latest/

[fabric-jupyter]: https://jupyter.fabric-testbed.net/
[fabric-jupyter-examples]: https://github.com/fabric-testbed/jupyter-examples
[fablib-install]: https://learn.fabric-testbed.net/knowledge-base/install-the-python-api/

[configuration]: https://fabric-fablib.readthedocs.io/en/latest/#configuring-fablib

[guidelines]: ./CONTRIBUTING.md



