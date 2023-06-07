import warnings

warnings.warn(
    "fabrictestbed_extensions module is deprecated", DeprecationWarning, stacklevel=2
)

import fabrictestbed_fablib

__version__ = fabrictestbed_fablib.__version__
