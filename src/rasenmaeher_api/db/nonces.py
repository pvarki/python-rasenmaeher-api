"""DB abstraction for storing nonces etc things needed to prevent re-use of certain tokens"""
from typing import Self, Dict, cast, Any, Optional
import logging

from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy as sa
from pydantic import Extra

from .base import BaseModel
from .errors import ForbiddenOperation, NotFound, Deleted, TokenReuse

LOGGER = logging.getLogger(__name__)


class SeenToken(BaseModel):  # pylint: disable=R0903
    """Store tokens we should see used only once"""

    __tablename__ = "seentokens"

    token = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    auditmeta = sa.Column(JSONB, nullable=False, server_default="{}")

    class Config:  # pylint: disable=R0903
        """Basemodel config"""

        extra = Extra.forbid

    @classmethod
    async def use_token(cls, token: str, auditmeta: Optional[Dict[str, Any]] = None) -> None:
        """Use token if it was already used raise error that is also 403"""
        try:
            obj = await SeenToken.by_token(token)
            if obj:
                LOGGER.error("{} was used on {}".format(obj.token, obj.created))
                raise TokenReuse()
        except NotFound:
            pass
        if not auditmeta:
            auditmeta = {}
        token = SeenToken(token=token, auditmeta=auditmeta)
        await token.create()

    @classmethod
    async def by_token(cls, token: str) -> Self:
        """Get by token"""
        obj = await SeenToken.query.where(SeenToken.token == token).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted token {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return cast(SeenToken, obj)

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of seen tokens is not allowed")
