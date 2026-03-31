"""Custom exception types for FABlib.

All exceptions inherit from :class:`FablibException` so callers can
catch the base class.  They also inherit from appropriate builtins
(``ValueError``, ``TimeoutError``, ``RuntimeError``) for compatibility
with existing ``except Exception:`` handlers.
"""


class FablibException(Exception):
    """Base exception for all FABlib errors."""

    pass


class ResourceNotFoundError(FablibException, KeyError):
    """A requested resource (node, interface, component, etc.) was not found."""

    pass


class SliceTimeoutError(FablibException, TimeoutError):
    """A slice operation exceeded the specified timeout."""

    pass


class SliceStateError(FablibException, RuntimeError):
    """A slice or node is in an invalid state for the requested operation."""

    pass


class SSHError(FablibException, ConnectionError):
    """An SSH or SCP operation failed."""

    pass


class ValidationError(FablibException, ValueError):
    """Input validation failed (invalid IP, missing parameter, etc.)."""

    pass
