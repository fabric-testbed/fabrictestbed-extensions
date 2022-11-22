# fabrictestbed-extensions

[![requirements-badge]][requirements] [![pypi-badge]][pypy]

This repository contains implementation of a Python API for
intereacting with [FABRIC][fabric] testbed, colloquially known as
"FABlib".

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

## Installing the Python package

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


<!-- URLs -->

[requirements]: https://requires.io/github/fabric-testbed/fabrictestbed-extensions/requirements/?branch=main
[requirements-badge]: https://requires.io/github/fabric-testbed/fabrictestbed-extensions/requirements.svg?branch=main (Requirements Status)

[pypy]: https://pypi.org/project/fabrictestbed-extensions/
[pypi-badge]: https://img.shields.io/pypi/v/fabrictestbed-extensions?style=plastic (PyPI)

[fabric]: https://fabric-testbed.net/

[venv]: https://docs.python.org/3/library/venv.html
[virtualenv]: https://virtualenv.pypa.io/en/latest/
[virtualenvwrapper]: https://virtualenvwrapper.readthedocs.io/en/latest/
