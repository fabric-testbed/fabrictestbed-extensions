import warnings

from fabrictestbed_fablib.interface import Interface

warnings.warn(
    "fabrictestbed_extensions.fablib.interface module is deprecated;"
    " please import fabrictestbed_fablib.interface instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [Interface]
