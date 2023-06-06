import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.network_service module is deprecated;"
    " please import fabrictestbed_fablib.network_service instead",
    DeprecationWarning,
    stacklevel=2,
)

NetworkService = fabrictestbed_fablib.fablib.NetworkService
