import warnings

from fabrictestbed_fablib.component import Component

warnings.warn(
    "fabrictestbed_extensions.fablib.component module is deprecated;"
    " please import fabrictestbed_fablib.component instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [Component]
