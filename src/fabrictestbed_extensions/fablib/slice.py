import warnings

from fabrictestbed_fablib.fablib import Slice

warnings.warn(
    "fabrictestbed_extensions.fablib.slice module is deprecated;"
    " please import fabrictestbed_fablib.slice instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [Slice]
