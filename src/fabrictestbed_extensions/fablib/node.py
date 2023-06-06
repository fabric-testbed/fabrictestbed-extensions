import warnings

import fabrictestbed_fablib

warnings.warn(
    "fabrictestbed_extensions.fablib.node module is deprecated;"
    " please import fabrictestbed_fablib.node instead",
    DeprecationWarning,
    stacklevel=2,
)

Node = fabrictestbed_fablib.fablib.Node
