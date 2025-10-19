"""The Gino baseclass with db connection wrapping"""

from typing import Self, Union
import uuid
import logging
import datetime


from libadvian.binpackers import b64_to_uuid, ensure_utf8, ensure_str
from sqlmodel import Field, SQLModel, select
import sqlalchemy as sa

from .errors import NotFound, Deleted
from .engine import EngineWrapper

utcnow = sa.func.current_timestamp()  # pylint: disable=invalid-name,not-callable  # not-callable is false-positive

LOGGER = logging.getLogger(__name__)


class ORMBaseModel(SQLModel, table=False):  # type: ignore[call-arg]
    """Baseclass with common fields"""

    __table_args__ = {"schema": "raesenmaeher"}

    pk: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    created: datetime.datetime = Field(sa_column_kwargs={"default": utcnow}, nullable=False)
    updated: datetime.datetime = Field(sa_column_kwargs={"default": utcnow, "onupdate": utcnow}, nullable=False)
    deleted: datetime.datetime = Field(nullable=True)

    @classmethod
    async def by_pk(cls, pkin: Union[str, uuid.UUID], allow_deleted: bool = False) -> Self:
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
