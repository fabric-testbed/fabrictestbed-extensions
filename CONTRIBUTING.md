# Contributing to FABlib

Thank you for considering to help FABlib!  We welcome contributions in
the form of bug reports, feature requests, code patches, documentation
updates, and anything else that may be helpful.  Please review these
guidelines first.

## Submitting Issues

If you want to add a new feature to FABlib or report that something is
broken, please submit an issue via GitHub.  If you find a bug, please
describe it in enough detail so that we can quickly reproduce them.


## Submitting Pull Requests

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
$ pip install tox
$ tox
```

Integration tests can be run like so:

```console
$ tox -e integration
```

Tox attempts to run tests in an isolated virtual environment.  If you
want to run some tests directly using [pytest], that is possible too:

```
$ pip install -e .[test]
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

1. Bump up version in `pyproject.toml`.
2. Update `CHANGELOG.md`.
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

[flit]: https://flit.pypa.io/en/stable/
[package uploads]: https://flit.pypa.io/en/latest/upload.html

[build]: https://pypi.org/project/build/
[tox]: https://pypi.org/project/tox/
[pytest]: https://pypi.org/project/pytest/
[black]: https://pypi.org/project/black/
[isort]: https://pypi.org/project/isort/

[publish]: ./.github/workflows/publish.yml
