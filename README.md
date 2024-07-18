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


