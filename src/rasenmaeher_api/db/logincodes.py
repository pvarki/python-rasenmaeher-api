"""DB abstraction for storing nonces etc things needed to prevent re-use of certain tokens"""

import datetime
import logging
import secrets
import string
from typing import Any

from multikeyjwt import Issuer
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, select

from .base import ORMBaseModel
from .engine import EngineWrapper
from .errors import Deleted, ForbiddenOperation, NotFound, TokenReuse

LOGGER = logging.getLogger(__name__)
CODE_CHAR_COUNT = 12  # TODO: Make configurable ??
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_MAX_ATTEMPTS = 100


class LoginCode(ORMBaseModel, table=True):
    """Track the login codes that can be exchanged for session JWTs"""

    __tablename__ = "logincodes"

    code: str = Field(nullable=False, index=True, unique=True)
    auditmeta: dict[str, Any] = Field(sa_type=JSONB, nullable=False, sa_column_kwargs={"server_default": "{}"})
    used_on: datetime.datetime = Field(nullable=True)
    claims: dict[str, Any] = Field(sa_type=JSONB, nullable=False, sa_column_kwargs={"server_default": "{}"})

    @classmethod
    async def use_code(cls, code: str, auditmeta: dict[str, Any] | None = None) -> str:
        """Exchange the code for JWT, if it was already used raise error that is also 403, return JWT with the claims"""
        try:
            obj = await LoginCode.by_code(code)
            if obj.used_on:
                LOGGER.error(f"{obj.code} was used on {obj.used_on}")
                raise TokenReuse()
        except NotFound:
            pass
        if not auditmeta:
            auditmeta = {}
        with EngineWrapper.get_session() as session:
            obj.used_on = datetime.datetime.now(datetime.UTC)
            obj.auditmeta = auditmeta
            session.add(obj)
            session.commit()
            return Issuer.singleton().issue(obj.claims)

    @classmethod
    async def by_code(cls, code: str) -> "LoginCode":
        """Get by token"""
        with EngineWrapper.get_session() as session:
            statement = select(LoginCode).where(LoginCode.code == code)
            obj = session.exec(statement).first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error(f"Got a deleted token {obj.pk}, this should not be possible")
            raise Deleted()  # This should *not* be happening
        return obj

    @classmethod
    async def create_for_claims(cls, claims: dict[str, Any], auditmeta: dict[str, Any] | None = None) -> str:
        """Create a new one with random code for the given claims"""
        # TODO: Do this in a transaction to avoid race conditions
        attempt = 0
        with EngineWrapper.get_session() as session:
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
            session.add(dbobj)
            session.commit()
            return code

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of login codes is not allowed, use one to revoke it")
