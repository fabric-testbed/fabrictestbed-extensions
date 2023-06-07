import warnings

from fabrictestbed_fablib.node import Node

warnings.warn(
    "fabrictestbed_extensions.fablib.node module is deprecated;"
    " please import fabrictestbed_fablib.node instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [Node]
