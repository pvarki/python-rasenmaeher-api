"""DB abstraction for storing nonces etc things needed to prevent re-use of certain tokens"""
from typing import Dict, Any, Optional
import logging

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, select


from .base import ORMBaseModel
from .errors import ForbiddenOperation, NotFound, Deleted, TokenReuse
from .engine import EngineWrapper

LOGGER = logging.getLogger(__name__)


class SeenToken(ORMBaseModel, table=True):  # type: ignore[call-arg,misc]
    """Store tokens we should see used only once"""

    __tablename__ = "seentokens"

    token: str = Field(nullable=False, index=True, unique=True)
    auditmeta: Dict[str, Any] = Field(sa_type=JSONB, nullable=False, sa_column_kwargs={"server_default": "{}"})

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
        with EngineWrapper.get_session() as session:
            dbtoken = SeenToken(token=token, auditmeta=auditmeta)
            session.add(dbtoken)
            session.commit()

    @classmethod
    async def by_token(cls, token: str) -> "SeenToken":
        """Get by token"""
        with EngineWrapper.get_session() as session:
            statement = select(SeenToken).where(SeenToken.token == token)
            obj = session.exec(statement).first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted token {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return obj

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of seen tokens is not allowed")
