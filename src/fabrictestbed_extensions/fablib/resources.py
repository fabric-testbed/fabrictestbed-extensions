import warnings

from fabrictestbed_fablib.fablib import Resources

warnings.warn(
    "fabrictestbed_extensions.fablib.resources module is deprecated;"
    " please import fabrictestbed_fablib.resources instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [Resources]