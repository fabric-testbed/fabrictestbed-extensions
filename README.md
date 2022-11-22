# fabrictestbed-extensions

[![requirements-badge]][requirements] [![pypi-badge]][pypy]

This repository contains implementation of a Python API for
intereacting with [FABRIC][fabric] testbed, colloquially known as
"FABlib".

## Installing fabrictestbed-extensions

Install released versions of FABlib from PyPI:

```console
$ pip install fabrictestbed-extensions
```

If you want a more "bleeding edge" version of FABlib, install it from
the git repository:


```console
$ pip install git+https://github.com/fabric-testbed/fabrictestbed-extensions.git
```

Note that installing FABlib using either methods will also install a
number of dependencies, so you might want to install FABlib in a
virtual environment.  Use your favorite: [venv], [virtualenv], or
[virtualenvwrapper].


## Using fabrictestbed-extensions

Your first encounter with FABlib might be through FABRIC project's
[JupyterHub][fabric-jupyter] instance.  You will be presented with
many examples on FABlib usage when you log in there.  The [notebook
sources][fabric-jupyter-examples] can be found on GitHub as well.

FABlib API documentation can be found [here][fablib-api-rtd], since
version 1.4.  Older API docs are [here][fablib-api-old].

If you want to interact with FABRIC from Jupyter installed on your
computer, see [Install the FABRIC Python API][fablib-install].


## Building the Python package

Do not do `python setup.py sdist bdist_wheel`. Instead, do:

```console
$ pip install build
$ python -m build
```

Following that, upload to PyPi using:

```console
$ twine upload dist/*
```

<!-- URLs -->

[requirements]: https://requires.io/github/fabric-testbed/fabrictestbed-extensions/requirements/?branch=main
[requirements-badge]: https://requires.io/github/fabric-testbed/fabrictestbed-extensions/requirements.svg?branch=main (Requirements Status)

[pypy]: https://pypi.org/project/fabrictestbed-extensions/
[pypi-badge]: https://img.shields.io/pypi/v/fabrictestbed-extensions?style=plastic (PyPI)

[fabric]: https://fabric-testbed.net/

[venv]: https://docs.python.org/3/library/venv.html
[virtualenv]: https://virtualenv.pypa.io/en/latest/
[virtualenvwrapper]: https://virtualenvwrapper.readthedocs.io/en/latest/

[fabric-jupyter]: https://jupyter.fabric-testbed.net/
[fabric-jupyter-examples]: https://github.com/fabric-testbed/jupyter-examples
[fabrlib-install]: https://learn.fabric-testbed.net/knowledge-base/install-the-python-api/

[fablib-api-rtd]: https://fabric-fablib.readthedocs.io/en/latest/
[fablib-api-old]: https://learn.fabric-testbed.net/docs/fablib/fablib.html

