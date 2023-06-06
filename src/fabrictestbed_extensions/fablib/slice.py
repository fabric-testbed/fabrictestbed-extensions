import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.slice module is deprecated;"
    " please import fabrictestbed_fablib.slice instead",
    DeprecationWarning,
    stacklevel=2,
)

Slice = fabrictestbed_fablib.fablib.Slice
