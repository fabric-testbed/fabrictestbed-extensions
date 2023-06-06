import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.resources module is deprecated;"
    " please import fabrictestbed_fablib.resources instead",
    DeprecationWarning,
    stacklevel=2,
)

Resources = fabrictestbed_fablib.fablib.Resources
