import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.interface module is deprecated;"
    " please import fabrictestbed_fablib.interface instead",
    DeprecationWarning,
    stacklevel=2,
)

Interface = fabrictestbed_fablib.interface.Interface
