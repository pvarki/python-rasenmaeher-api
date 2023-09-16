"""The Gino baseclass with db connection wrapping"""
from typing import Self, cast
import uuid

from gino import Gino
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa
from libadvian.binpackers import b64_to_uuid, ensure_utf8, ensure_str

from .errors import NotFound, Deleted
from .config import DBConfig

utcnow = sa.func.current_timestamp()
db = Gino()
DBModel: Gino.Model = db.Model  # workaround mypy being unhappy about using @property as baseclass


class BaseModel(DBModel):  # type: ignore[misc] # pylint: disable=R0903
    """Baseclass with common fields"""

    __table_args__ = {"schema": "raesenmaeher"}

    pk = sa.Column(saUUID(), primary_key=True, default=uuid.uuid4)
    created = sa.Column(sa.DateTime(timezone=True), default=utcnow, nullable=False)
    updated = sa.Column(sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    deleted = sa.Column(sa.DateTime(timezone=True), nullable=True)

    @classmethod
    async def by_pk(cls, pkin: str, allow_deleted: bool = False) -> Self:
        """Get by pk"""
        try:
            getpk = b64_to_uuid(ensure_utf8(pkin))
        except ValueError:
            getpk = uuid.UUID(ensure_str(pkin))
        obj = await cls.get(getpk)
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return cast(Self, obj)


async def bind_config() -> None:
    """Set bind from config and return"""
    config = DBConfig()
    await db.set_bind(config.dsn)
