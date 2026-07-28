"""Middleware to require valid user"""

import logging
from collections.abc import Sequence
from typing import cast

from fastapi import HTTPException, Request

from ....db.errors import DBError, Deleted, NotFound
from ....db.people import Person
from ....rmsettings import RMSettings
from .datatypes import MTLSorJWTPayloadType
from .mtls import MTLSorJWT

LOGGER = logging.getLogger(__name__)


class ValidUser(MTLSorJWT):
    """Check that the subject is a valid user"""

    def __init__(self, *, auto_error: bool = True, require_roles: Sequence[str] = ()):
        self.require_roles = require_roles
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Person | None:  # type: ignore[override]
        """Call parent and check the userid"""
        request.state.person = None
        payload = await super().__call__(request)
        if not payload:
            if self.auto_error:
                raise HTTPException(status_code=403, detail="Not authenticated")
            return cast(None, request.state.person)
        if not payload.userid:
            if self.auto_error:
                raise HTTPException(status_code=403, detail="No userid in payload")
            return cast(None, request.state.person)

        if payload.type == MTLSorJWTPayloadType.MTLS and (payload.userid in RMSettings.singleton().valid_product_cns):
            # PONDER: Try to load the default anon_admin user ??
            LOGGER.debug("product mTLS client, allowing and skipping role checks")
            return cast(None, request.state.person)

        try:
            request.state.person = await Person.by_callsign(payload.userid)
        except DBError as exc:
            if isinstance(exc, (NotFound, Deleted)):
                if self.auto_error:
                    raise HTTPException(status_code=403, detail="Invalid userid in payload") from exc
            else:
                raise HTTPException(status_code=500, detail="DB failure when looking for user") from exc

        if not request.state.person:
            return cast(None, request.state.person)

        roles = await request.state.person.roles_set()
        required = set(self.require_roles)
        LOGGER.debug(f"required={required} roles={roles}")
        if not required.issubset(roles):
            LOGGER.warning(f"Required roles not granted, required={required} roles={roles}")
            if self.auto_error:
                raise HTTPException(status_code=403, detail="Required role(s) not granted")

        return cast(Person, request.state.person)
