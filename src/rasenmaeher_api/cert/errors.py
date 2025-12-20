"""Generic certificate operation errors."""


class CertError(RuntimeError):
    """Base exception for certificate operations."""


class NoResult(CertError, ValueError):
    """Did not get any result."""


class ErrorResult(CertError, ValueError):
    """Got error in result."""


class DBLocked(CertError):
    """Database is locked, retry needed."""


class NoValue(CertError, ValueError):
    """Did not get expected values."""
