import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.fablib module is deprecated;"
    " please import fabrictestbed_fablib.fablib instead",
    DeprecationWarning,
    stacklevel=2,
)

FablibManager = fabrictestbed_fablib.fablib.FablibManager
