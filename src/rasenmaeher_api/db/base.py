"""The Gino baseclass with db connection wrapping"""
from typing import Self, cast, Union
import uuid
import logging
from pathlib import Path
import tempfile
import asyncio
import random

from gino import Gino
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa
from asyncpg.exceptions import DuplicateSchemaError, UniqueViolationError
from libadvian.binpackers import b64_to_uuid, ensure_utf8, ensure_str
import filelock

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
    # Random sleep to avoid race conditions
    lockpath = Path(tempfile.gettempdir()) / "dbinit.lock"
    lock = filelock.FileLock(lockpath)
    try:
        await asyncio.sleep(random.random() * 2)  # nosec
        lock.acquire(timeout=0.0)
        try:
            LOGGER.debug("Acquiring connection")
            async with db.acquire() as conn:
                LOGGER.debug("Acquiring transaction")
                async with conn.transaction():
                    LOGGER.debug("Creating raesenmaeher schema")
                    await db.status(sa.schema.CreateSchema("raesenmaeher"))
                    LOGGER.debug("Creating tables")
                    await db.gino.create_all()
        except (DuplicateSchemaError, UniqueViolationError):
            pass
    except filelock.Timeout:
        LOGGER.warning("Someone has already locked {}".format(lockpath))
        LOGGER.debug("Sleeping for ~5s and then recursing")
        await asyncio.sleep(5.0 + random.random())  # nosec
        return await init_db()
    finally:
        lock.release()
