"""DB abstraction for storing nonces etc things needed to prevent re-use of certain tokens"""
from typing import Self, Dict, cast, Any, Optional
import logging
import string
import secrets

from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy as sa
from multikeyjwt import Issuer

from .base import BaseModel, utcnow
from .errors import ForbiddenOperation, NotFound, Deleted, TokenReuse

LOGGER = logging.getLogger(__name__)
CODE_CHAR_COUNT = 12  # TODO: Make configurable ??
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_MAX_ATTEMPTS = 100


class LoginCode(BaseModel):  # pylint: disable=R0903
    """Track the login codes that can be exchanged for session JWTs"""

    __tablename__ = "logincodes"

    code = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    auditmeta = sa.Column(JSONB, nullable=False, server_default="{}")
    used_on = sa.Column(sa.DateTime(timezone=True), nullable=True)
    claims = sa.Column(JSONB, nullable=False, server_default="{}")

    @classmethod
    async def use_code(cls, code: str, auditmeta: Optional[Dict[str, Any]] = None) -> str:
        """Exchange the code for JWT, if it was already used raise error that is also 403, return JWT with the claims"""
        obj = await LoginCode.by_code(code)
        if obj.used_on:
            LOGGER.error("{} was used on {}".format(obj.code, obj.used_on))
            raise TokenReuse()
        if not auditmeta:
            auditmeta = {}
        await obj.update(used_on=utcnow, auditmeta=auditmeta).apply()
        return Issuer.singleton().issue(obj.claims)

    @classmethod
    async def by_code(cls, code: str) -> Self:
        """Get by token"""
        obj = await LoginCode.query.where(LoginCode.code == code).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted token {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return cast(LoginCode, obj)

    @classmethod
    async def create_for_claims(cls, claims: Dict[str, Any], auditmeta: Optional[Dict[str, Any]] = None) -> str:
        """Create a new one with random code for the given claims"""
        # TODO: Do this in a transaction to avoid race conditions
        attempt = 0
        while True:
            attempt += 1
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHAR_COUNT))
            try:
                await LoginCode.by_code(code)
            except NotFound:
                break
            if attempt > CODE_MAX_ATTEMPTS:
                raise RuntimeError("Can't find unused code")
        if not auditmeta:
            auditmeta = {}
        dbobj = LoginCode(code=code, claims=claims, auditmeta=auditmeta)
        await dbobj.create()
        return code

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of login codes is not allowed, use one to revoke it")
