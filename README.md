# fabrictestbed-extensions

[![pypi-badge]][pypy] [![api-docs-badge]][api-docs]

This repository contains implementation of a Python API, otherwise
known as "FABlib", for intereacting with [FABRIC][fabric] testbed.


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

Your first encounter with FABlib however might be through FABRIC
project's [JupyterHub][fabric-jupyter] instance. You will be presented
with many examples on FABlib usage when you log in there. The
[notebook sources][fabric-jupyter-examples] can be found on GitHub as
well.

Since FABlib 1.4, API docs can be found [here][fablib-api-rtd]. Older
API docs are [here][fablib-api-old].

If you want to interact with FABRIC from Jupyter installed on your
computer, see: [Install the FABRIC Python API][fablib-install].


## Contributing to FABlib

Contributions to FABlib are made with GitHub Pull Requests. When you
submit a pull request, some tests will run against it:

- Code formatting will be checked using [black] and [isort].  Be sure
  that your code is formatted with these tools.
- Unit tests will be run.
- Packages will be built.
- CHANGELOG.md will be checked for updates.


## Testing FABlib

FABlib currently has a modest set of unit and integration tests, under
the top-level `tests` directory.  Unit tests can be run like so, using
[tox]:

```console
$ pip install -e .[test]
$ tox
```

Integration tests can be run like so:

```console
$ tox -e integration
```

Tox attempts to run tests in an isolated virtual environment.  If you
want to run some tests directly using [pytest], that is possible too:

```
$ pytest -s tests/integration/test_hello_fabric.py
```

## Documenting FABlib

FABlib uses Sphinx to generate API documentation from Python
docstrings. Publishing them at [Read the Docs][fablib-api-rtd] is a
mostly automated process.

When working on API documentation on your local setup, in order to
preview the generated HTML, run:

```
$ tox -e docs
```

Resulting files can be found in `docs/build/html/`.


## Packaging FABlib

FABlib uses [flit] as the build backend.  To build source and wheel
packages, do this:

```console
$ pip install flit
$ flit build
```

While using flit as the build backend, continuing to use [build] as
the build frontend should work too:

```
$ pip install build
$ python -m build
```


## Releasing FABlib

The "[publish]" workflow automates building packages and publishing
them on PyPI.  In order to publish a new FABlib version on PyPI,
follow these steps:

1. Bump up version in top-level `__init__.py`.
2. Update changelog.
3. Start a PR with these changes, and get it merged.
4. Tag the release, and push the tag to GitHub:

   ```console
   $ git tag --sign --message="Great set of features" relX.Y.Z <ref>
   $ git push <origin> --tags relX.Y.Z
   ```
This should trigger the publish workflow that will: (1) run unit
tests, (2) build FABlib sdist and wheel packages, (3) publish
the packages on PyPI, and (4) create a GitHub release.


### Manual steps

In order to "manually" upload FABlib packages (such as in the case of
release candidate versions), bump up the version string in the
appropriate place, and then do:

```console
$ flit publish
```

Continuing to use twine to publish packages is an option too:

```console
$ twine upload dist/*
```

For details about publishing to PyPI, see flit documentation about
[package uploads].


<!-- URLs -->

[pypy]: https://pypi.org/project/fabrictestbed-extensions/
[pypi-badge]: https://img.shields.io/pypi/v/fabrictestbed-extensions?style=plastic (PyPI)

[api-docs]: https://fabric-fablib.readthedocs.io/en/latest/?badge=latest
[api-docs-badge]: https://readthedocs.org/projects/fabric-fablib/badge/?version=latest (Documentation Status)

[fabric]: https://fabric-testbed.net/

[venv]: https://docs.python.org/3/library/venv.html
[virtualenv]: https://virtualenv.pypa.io/en/latest/
[virtualenvwrapper]: https://virtualenvwrapper.readthedocs.io/en/latest/

[fabric-jupyter]: https://jupyter.fabric-testbed.net/
[fabric-jupyter-examples]: https://github.com/fabric-testbed/jupyter-examples
[fablib-install]: https://learn.fabric-testbed.net/knowledge-base/install-the-python-api/

[fablib-api-rtd]: https://fabric-fablib.readthedocs.io/en/latest/
[fablib-api-old]: https://learn.fabric-testbed.net/docs/fablib/fablib.html

[flit]: https://flit.pypa.io/en/stable/
[package uploads]: https://flit.pypa.io/en/latest/upload.html

[build]: https://pypi.org/project/build/
[tox]: https://pypi.org/project/tox/
[pytest]: https://pypi.org/project/pytest/
[black]: https://pypi.org/project/black/
[isort]: https://pypi.org/project/isort/

[publish]: ./.github/workflows/publish.yml
