"""Ensure all models are defined and then create tables"""

import asyncio
import logging
import random
import tempfile
from pathlib import Path

import filelock
import sqlalchemy as sa
from sqlalchemy.schema import CreateSchema
from sqlmodel import SQLModel

# Import all models to ensure ORM can create all tables
from .base import ORMBaseModel
from .engine import EngineWrapper
from .enrollments import Enrollment, EnrollmentPool
from .issuedcerts import IssuedCert
from .logincodes import LoginCode
from .nonces import SeenToken
from .people import Person, Role

_ = (Person, Role, EnrollmentPool, Enrollment, SeenToken, LoginCode, IssuedCert)
LOGGER = logging.getLogger(__name__)


async def init_db() -> None:
    """Create schemas and tables, normally one should use migration manager"""
    # Random sleep to avoid race conditions
    lockpath = Path(tempfile.gettempdir()) / "dbinit.lock"
    lock = filelock.FileLock(lockpath)
    wrapper = EngineWrapper.singleton()
    assert wrapper.engine  # nosec B101
    engine = wrapper.engine
    try:
        await asyncio.sleep(random.random() * 2)  # nosec B311
        lock.acquire(timeout=0.0)
        LOGGER.debug("Acquiring session")
        with engine.connect() as connection:
            if not sa.inspect(connection).has_schema(ORMBaseModel.__table_args__["schema"]):
                LOGGER.debug("Creating schema {}".format(ORMBaseModel.__table_args__["schema"]))
                connection.execute(CreateSchema(ORMBaseModel.__table_args__["schema"]))
                connection.commit()
            SQLModel.metadata.create_all(connection)
            connection.commit()
    except filelock.Timeout:
        LOGGER.warning(f"Someone has already locked {lockpath}")
        LOGGER.debug("Sleeping for ~5s and then recursing")
        await asyncio.sleep(5.0 + random.random())  # nosec B311
        return await init_db()
    finally:
        lock.release()
