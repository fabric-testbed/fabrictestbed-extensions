"""Custom exception types for FABlib.

All exceptions inherit from :class:`FablibException` so callers can
catch the base class.  They also inherit from appropriate builtins
(``ValueError``, ``TimeoutError``, ``RuntimeError``) for compatibility
with existing ``except Exception:`` handlers.
"""


class FablibException(Exception):
    """Base exception for all FABlib errors.

    All FABlib exceptions accept an optional ``payload`` keyword argument
    that carries structured error data (e.g. a list of validation errors
    or an erring object) alongside the human-readable message::

        raise ValidationError("Slice validation failed", payload=errors)

    Callers can access it via ``exc.payload``.
    """

    def __init__(self, *args, payload=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.payload = payload


class ResourceNotFoundError(FablibException, KeyError):
    """A requested resource (node, interface, component, etc.) was not found."""

    pass


class SliceTimeoutError(FablibException, TimeoutError):
    """A slice operation exceeded the specified timeout."""

    pass


class SliceNotFoundError(FablibException, KeyError):
    """The requested slice was not found."""

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
