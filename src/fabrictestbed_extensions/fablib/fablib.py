import warnings

from fabrictestbed_fablib.fablib import FablibManager

warnings.warn(
    "fabrictestbed_extensions.fablib.fablib module is deprecated;"
    " please import fabrictestbed_fablib.fablib instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [FablibManager]
