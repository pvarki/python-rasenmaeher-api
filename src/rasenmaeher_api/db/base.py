"""The Gino baseclass with db connection wrapping"""

import datetime
import logging
import uuid
from typing import Self

import sqlalchemy as sa
from libadvian.binpackers import b64_to_uuid, ensure_str, ensure_utf8
from sqlmodel import Field, SQLModel, select

from .engine import EngineWrapper
from .errors import Deleted, NotFound

utcnow = sa.func.current_timestamp()

LOGGER = logging.getLogger(__name__)


class ORMBaseModel(SQLModel, table=False):
    """Baseclass with common fields"""

    __table_args__ = {"schema": "raesenmaeher"}

    pk: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    created: datetime.datetime = Field(sa_column_kwargs={"default": utcnow}, nullable=False)
    updated: datetime.datetime = Field(sa_column_kwargs={"default": utcnow, "onupdate": utcnow}, nullable=False)
    deleted: datetime.datetime = Field(nullable=True)

    @classmethod
    async def by_pk(cls, pkin: str | uuid.UUID, allow_deleted: bool = False) -> Self:
        """Get by pk"""
        if isinstance(pkin, uuid.UUID):
            getpk = pkin
        else:
            try:
                getpk = b64_to_uuid(ensure_utf8(pkin))
            except ValueError:
                getpk = uuid.UUID(ensure_str(pkin))
        with EngineWrapper.get_session() as session:
            statement = select(cls).where(cls.pk == getpk)
            obj = session.exec(statement).first()
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return obj

    async def delete(self) -> bool:
        """override delete method to set the deleted timestamp instead of removing the row"""
        with EngineWrapper.get_session() as session:
            self.deleted = datetime.datetime.now(datetime.UTC)
            session.add(self)
            session.commit()
            session.refresh(self)
        return True
