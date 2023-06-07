import warnings

from fabrictestbed_fablib.facility_port import FacilityPort

warnings.warn(
    "fabrictestbed_extensions.fablib.facility_port module is deprecated;"
    " please import fabrictestbed_fablib.facility_port instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [FacilityPort]
