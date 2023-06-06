import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.facility_port module is deprecated;"
    " please import fabrictestbed_fablib.facility_port instead",
    DeprecationWarning,
    stacklevel=2,
)

FacilityPort = fabrictestbed_fablib.fablib.FacilityPort

