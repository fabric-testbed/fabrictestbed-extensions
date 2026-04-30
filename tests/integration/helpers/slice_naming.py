"""Unique slice name generation for integration tests."""

import os
import socket
import time


def make_slice_name(test_id: str) -> str:
    """Generate a unique, traceable slice name.

    Format: itest-<test_id>-<YYYYMMDD-HHMMSS>-<hostname_prefix>
    Kept under 100 characters to avoid API issues.

    :param test_id: short identifier for the test
    :type test_id: str
    :return: unique slice name
    :rtype: str
    """
    prefix = os.environ.get("FABLIB_TEST_SLICE_PREFIX", "itest")
    time_stamp = time.strftime("%Y%m%d-%H%M%S")
    host = socket.gethostname()[:10]
    name = f"{prefix}-{test_id}-{time_stamp}-{host}"
    return name[:100]
