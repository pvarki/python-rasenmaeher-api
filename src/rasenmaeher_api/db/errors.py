"""Errors"""
from typing import Sequence, Any

from starlette import status
from starlette.exceptions import HTTPException


class DBFetchError(ValueError):
    """Various issues when fetching an object that are input dependent"""


class NotFound(DBFetchError, HTTPException):
    """Object was not found"""

    def __init__(self, *args: Sequence[Any]) -> None:
        """make us also 404 HTTP error"""
        new_args = [status.HTTP_404_NOT_FOUND] + list(args)
        super(HTTPException, self).__init__(*new_args)


class Deleted(NotFound):
    """Object was deleted"""
