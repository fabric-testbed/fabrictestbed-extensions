import warnings

from fabrictestbed_fablib import component

warnings.warn(
    "fabrictestbed_extensions.fablib.component module is deprecated;"
    " please import fabrictestbed_fablib.component instead",
    DeprecationWarning,
    stacklevel=2,
)

Component = fablib.Component

