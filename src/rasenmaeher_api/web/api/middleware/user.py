"""Middleware to require valid user"""
from typing import Optional, Sequence
import logging

from fastapi import Request, HTTPException


from ....db.people import Person
from ....db.errors import DBError, NotFound, Deleted
from .mtls import MTLSorJWT

LOGGER = logging.getLogger(__name__)


class ValidUser(MTLSorJWT):  # pylint: disable=too-few-public-methods
    """Check that the subject is a valid user"""

    def __init__(self, *, auto_error: bool = True, require_roles: Sequence[str] = ()):
        self.require_roles = require_roles
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[Person]:
        """Call parent and check the userid"""
        request.state.person = None
        payload = await super().__call__(request)
        if not payload:
            if self.auto_error:
                raise HTTPException(status_code=403, detail="Not authenticated")
            return request.state.person
        if not payload.userid:
            if self.auto_error:
                raise HTTPException(status_code=403, detail="No userid in payload")
            return request.state.person

        try:
            request.state.person = await Person.by_callsign(payload.userid)
        except DBError as exc:
            if isinstance(exc, (NotFound, Deleted)):
                if self.auto_error:
                    raise HTTPException(status_code=403, detail="Invalid userid in payload") from exc
            else:
                raise HTTPException(status_code=500, detail="DB failure when looking for user") from exc

        if not request.state.person:
            return request.state.person

        roles = {role async for role in request.state.person.roles()}
        required = set(self.require_roles)
        LOGGER.debug("required={} roles={}".format(required, roles))
        if not required.issubset(roles):
            LOGGER.warning("Required roles not granted, required={} roles={}".format(required, roles))
            if self.auto_error:
                raise HTTPException(status_code=403, detail="Required role(s) not granted")

        return request.state.person
