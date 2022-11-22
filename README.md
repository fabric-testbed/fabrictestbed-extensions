# fabrictestbed-extensions

[![requirements-badge]][requirements]

[![pypi-badge]][pypy]

Extensions for the FABRIC API/CLI.  

## Build instructions
(Do not do `python setup.py sdist bdist_wheel`)
```
python -m build
```
Following that upload to PyPi using
```
twine upload dist/*
```

## Install Instructions
```
git clone https://github.com/fabric-testbed/fabrictestbed-extensions.git 
cd fabrictestbed-extensions
pip install --user .
```

<!-- Badges -->

[requirements]: https://requires.io/github/fabric-testbed/fabrictestbed-extensions/requirements/?branch=main
[requirements-badge]: https://requires.io/github/fabric-testbed/fabrictestbed-extensions/requirements.svg?branch=main (Requirements Status)

[pypy]: https://pypi.org/project/fabrictestbed-extensions/
[pypi-badge]: https://img.shields.io/pypi/v/fabrictestbed-extensions?style=plastic (PyPI)

