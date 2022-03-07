# fabrictestbed-extensions

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
