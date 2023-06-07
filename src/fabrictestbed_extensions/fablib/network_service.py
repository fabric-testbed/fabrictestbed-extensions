import warnings

from fabrictestbed_fablib.network_service import NetworkService

warnings.warn(
    "fabrictestbed_extensions.fablib.network_service module is deprecated;"
    " please import fabrictestbed_fablib.network_service instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [NetworkService]
