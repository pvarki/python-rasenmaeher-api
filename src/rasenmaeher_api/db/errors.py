"""Errors"""
from typing import Sequence, Any

from starlette import status
from starlette.exceptions import HTTPException


class BackendError(RuntimeError):
    """Failure from a dependent backend"""


class DBError(RuntimeError):
    """Undefined DB error"""


class DBFetchError(ValueError, DBError):
    """Various issues when fetching an object that are input dependent"""


class NotFound(DBFetchError, HTTPException):
    """Object was not found"""

    def __init__(self, *args: Sequence[Any]) -> None:
        """make us also 404 HTTP error"""
        self.status_code = status.HTTP_404_NOT_FOUND
        self.detail = "Not found"
        new_args = [status.HTTP_404_NOT_FOUND] + list(args)
        super(HTTPException, self).__init__(*new_args)


class Deleted(NotFound):
    """Object was deleted"""


class ForbiddenOperation(RuntimeError):
    """Forbidden operation"""


class EnrollmentError(Exception):
    """Baseclass for issues with enrollments"""


class CallsignReserved(HTTPException, EnrollmentError, ValueError):
    """Callsign is already reserved"""

    def __init__(self, *args: Sequence[Any]) -> None:
        """make us also 403 HTTP error"""
        self.status_code = status.HTTP_403_FORBIDDEN
        self.detail = "Forbidden"
        new_args = [status.HTTP_403_FORBIDDEN] + list(args)
        super(HTTPException, self).__init__(*new_args)


class PoolInactive(EnrollmentError, ForbiddenOperation):
    """Inactive pool forbidden operations"""


class TokenReuse(HTTPException, ValueError):
    """Token is already reserved"""

    def __init__(self, *args: Sequence[Any]) -> None:
        """make us also 403 HTTP error"""
        self.status_code = status.HTTP_403_FORBIDDEN
        self.detail = "Forbidden"
        new_args = [status.HTTP_403_FORBIDDEN] + list(args)
        super(HTTPException, self).__init__(*new_args)
