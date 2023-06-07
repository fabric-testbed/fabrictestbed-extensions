# fabrictestbed-fablib

[![pypi-badge]][pypy] [![api-docs-badge]][api-docs]

This repository contains implementation of a Python API, otherwise
known as "FABlib", for intereacting with [FABRIC][fabric] testbed.


## Installing FABlib

You can install released versions of FABlib from PyPI:

```console
$ pip install fabrictestbed-fablib
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
from fabrictestbed_fablib import FablibManager

try:
    fablib = FablibManager()
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

- Code formatting will be checked using [black].  Be sure that your
  code is formatted with black, using its defaults.
- CHANGELOG.md will be checked for updates.
- Packages will be built.
- Unit tests will be run.

You can run tests in your environment, like so, using [pytest]:

```console
$ pip install -e .[test]
$ pytest
```

## Packaging FABlib

To build source and wheel packages, do this:

```console
$ pip install build
$ python -m build
```


## Releasing FABlib

When it is time to release a new version of FABlib, remember to: 

1. Update `version` in `pyproject.toml`.
2. Tag the release tag and push the tag to GitHub:

```console
$ git tag --sign --message "Great new features" rel<x.y.z> <commit>
$ git push origin --tags rel<x.y.z>
```

2. Build the source and wheel packages.
3. Upload packages to PyPI using [twine]:

```console
$ pip install twine
$ twine upload dist/*
```


<!-- URLs -->

[pypy]: https://pypi.org/project/fabrictestbed-fablib/
[pypi-badge]: https://img.shields.io/pypi/v/fabrictestbed-fablib?style=plain (PyPI)

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

[build]: https://pypi.org/project/build/
[pytest]: https://pypi.org/project/pytest/
[black]: https://pypi.org/project/black/
[twine]: https://pypi.org/project/twine/
