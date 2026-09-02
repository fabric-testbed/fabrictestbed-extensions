#!/usr/bin/env python3
"""Check that our declared minimum Python version is the truth.

We shipped 2.0.7 with ``requires-python = ">=3.10"`` while the code had
already started using ``datetime.UTC`` (3.11+), so ``pip install`` happily
resolved on 3.10 and then blew up at import time with::

    ImportError: cannot import name 'UTC' from 'datetime'

See https://github.com/fabric-testbed/fabrictestbed-extensions/issues/513.

Two independent things went wrong there, so this script checks both:

1. **The code must not require anything newer than the declared floor.**
   ``vermin`` walks the sources and reports the minimum interpreter they
   actually need; we fail if that is newer than ``requires-python``.

2. **Everything that names a Python version must agree with the floor.**
   ``requires-python`` is the single source of truth, and CI, ruff, mypy and
   Read the Docs all have to match it.  It was the *disagreement* between
   them that let the bad metadata reach PyPI unnoticed -- CI was only ever
   running 3.11+, so nothing exercised the 3.10 we were promising.

Run via ``tox -e min-python``, or directly.  Exits non-zero on any mismatch.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Sources vermin should walk.  Tests are excluded on purpose: they are not
# shipped to users, so they do not constrain `requires-python`.
PACKAGE = "fabrictestbed_extensions"

Version = tuple[int, int]


def fail(message: str) -> None:
    """Report a problem and remember that we have to exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    fail.count += 1


fail.count = 0


def parse_version(text: str) -> Version:
    """Turn a Python version into a ``(3, 11)`` tuple.

    Handles both the dotted form everything else uses (``"3.11"``) and
    ruff's undotted ``target-version`` spelling (``"py311"``).
    """
    text = text.strip()
    match = re.fullmatch(r"(?:py)?(\d+)\.(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    # ruff: "py311" -> 3.11. The minor version is everything after the
    # leading major digit, so this keeps working at py310+.
    match = re.fullmatch(r"py(\d)(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    raise ValueError(f"cannot read a Python version out of {text!r}")


def show(version: Version) -> str:
    """Render ``(3, 11)`` back as ``"3.11"``."""
    return f"{version[0]}.{version[1]}"


def declared_floor(pyproject: dict) -> Version:
    """The floor from ``requires-python``, which everything else follows."""
    requires = pyproject["project"]["requires-python"]
    # We only understand the `>=X.Y` form, which is all we have ever used.
    # Anything else (an upper bound, `~=`, a list of ranges) changes what
    # "the floor" even means, so refuse to guess.
    match = re.fullmatch(r">=\s*(\d+\.\d+)", requires.strip())
    if not match:
        raise ValueError(
            f"requires-python is {requires!r}; this check only understands "
            'the ">=X.Y" form. Update tools/check_python_floor.py.'
        )
    return parse_version(match.group(1))


def check_code_against_floor(floor: Version) -> None:
    """Fail if the sources need a newer interpreter than we advertise."""
    # vermin ships only a console script -- it has no __main__, so
    # `python -m vermin` does not work.
    vermin = shutil.which("vermin")
    if vermin is None:
        fail("vermin is not installed; run this via `tox -e min-python`")
        return

    # `-t=X.Y-` means "must run on X.Y and up"; vermin exits 1 when some
    # construct in the tree needs more than that, and prints each offender.
    result = subprocess.run(
        [
            vermin,
            f"-t={show(floor)}-",
            "--violations",
            "--eval-annotations",
            "--no-tips",
            PACKAGE,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(
            f"{PACKAGE} uses features newer than the declared floor "
            f"(requires-python = >={show(floor)}). Either drop the feature or "
            f"raise requires-python.\n\n{result.stdout}{result.stderr}"
        )


def check_tool_config(pyproject: dict, floor: Version) -> None:
    """Fail if ruff's or mypy's target version disagrees with the floor."""
    ruff_target = pyproject["tool"]["ruff"]["target-version"]
    if parse_version(ruff_target) != floor:
        fail(
            f"[tool.ruff] target-version is {ruff_target!r}, but "
            f"requires-python floor is {show(floor)}"
        )

    mypy_target = pyproject["tool"]["mypy"]["python_version"]
    if parse_version(mypy_target) != floor:
        fail(
            f"[tool.mypy] python_version is {mypy_target!r}, but "
            f"requires-python floor is {show(floor)}"
        )


def check_readthedocs(floor: Version) -> None:
    """Fail if Read the Docs builds on something other than the floor."""
    path = ROOT / ".readthedocs.yaml"
    config = yaml.safe_load(path.read_text())
    rtd_python = config["build"]["tools"]["python"]
    if parse_version(str(rtd_python)) != floor:
        fail(
            f".readthedocs.yaml builds with Python {rtd_python!r}, but "
            f"requires-python floor is {show(floor)}"
        )


def check_ci_matrix(floor: Version) -> None:
    """Fail unless CI actually tests the floor -- the check that matters.

    An untested floor is exactly how this bug shipped: the matrix started at
    3.11 while the metadata promised 3.10, so no job ever imported the
    package on the oldest interpreter we claimed to support.
    """
    path = ROOT / ".github/workflows/test.yml"
    config = yaml.safe_load(path.read_text())
    versions = config["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    tested = sorted(parse_version(str(v)) for v in versions)

    if floor not in tested:
        fail(
            f"the test matrix in {path.name} does not include the declared "
            f"floor {show(floor)} (it tests "
            f"{', '.join(show(v) for v in tested)}). The oldest supported "
            f"Python must be tested, or breakage on it goes unnoticed."
        )
    elif tested[0] != floor:
        fail(
            f"the test matrix in {path.name} tests {show(tested[0])}, which "
            f"is older than the declared floor {show(floor)}"
        )


def main() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    floor = declared_floor(pyproject)

    check_code_against_floor(floor)
    check_tool_config(pyproject, floor)
    check_readthedocs(floor)
    check_ci_matrix(floor)

    if fail.count:
        print(
            f"\n{fail.count} problem(s) found. Python {show(floor)} is what "
            "pyproject.toml promises; everything above has to agree with it.",
            file=sys.stderr,
        )
        return 1

    print(f"ok: minimum supported Python is {show(floor)}, consistently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
