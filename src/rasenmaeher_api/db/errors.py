"""Errors"""


class DBFetchError(ValueError):
    """Various issues when fetching an object that are input dependent"""


class NotFound(DBFetchError):
    """Object was not found"""


class Deleted(DBFetchError):
    """Object was deleted"""
