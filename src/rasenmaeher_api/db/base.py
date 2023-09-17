"""The Gino baseclass with db connection wrapping"""
from typing import Self, cast, Union
import uuid
import logging

from gino import Gino
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa
from asyncpg.exceptions import DuplicateSchemaError
from libadvian.binpackers import b64_to_uuid, ensure_utf8, ensure_str

from .errors import NotFound, Deleted
from .config import DBConfig

utcnow = sa.func.current_timestamp()
db = Gino()
DBModel: Gino.Model = db.Model  # workaround mypy being unhappy about using @property as baseclass
LOGGER = logging.getLogger(__name__)


class BaseModel(DBModel):  # type: ignore[misc] # pylint: disable=R0903
    """Baseclass with common fields"""

    __table_args__ = {"schema": "raesenmaeher"}

    pk = sa.Column(saUUID(), primary_key=True, default=uuid.uuid4)
    created = sa.Column(sa.DateTime(timezone=True), default=utcnow, nullable=False)
    updated = sa.Column(sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    deleted = sa.Column(sa.DateTime(timezone=True), nullable=True)

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
        obj = await cls.get(getpk)
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return cast(Self, obj)

    async def delete(self) -> bool:
        """override delete method to set the deleted timestamp instead of removing the row"""
        await self.update(deleted=utcnow).apply()
        return True


async def bind_config() -> None:
    """Set bind from config and return"""
    config = DBConfig()
    await db.set_bind(config.dsn)


async def init_db() -> None:
    """Create schemas and tables, normally one should use migration manager"""
    try:
        LOGGER.debug("Acquiring connection")
        async with db.acquire() as conn:
            LOGGER.debug("Acquiring transaction")
            async with conn.transaction():
                LOGGER.debug("Creating raesenmaeher schema")
                await db.status(sa.schema.CreateSchema("raesenmaeher"))
                LOGGER.debug("Creating tables")
                await db.gino.create_all()
    except DuplicateSchemaError:
        pass
