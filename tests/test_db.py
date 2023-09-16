"""DB specific tests"""
from typing import Generator
import logging
import uuid
import asyncio

import pytest
import pytest_asyncio
import sqlalchemy

from rasenmaeher_api.db import DBConfig, bind_config, db, Person
from rasenmaeher_api.db.errors import NotFound, Deleted

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Session scoped event loop so the db connection can stay up"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


def test_dbconfig_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the env loading works without import side effects"""
    host = str(uuid.uuid4())
    user = str(uuid.uuid4())
    passwd = str(uuid.uuid4())
    with monkeypatch.context() as mpatch:
        mpatch.setenv("RM_DATABASE_HOST", host)
        mpatch.setenv("RM_DATABASE_USER", user)
        mpatch.setenv("RM_DATABASE_PASSWORD", passwd)

        config = DBConfig()
        assert config.host == host
        assert config.user == user
        assert str(config.password) == passwd
        assert config.dsn


def test_dbconfig_defaults(docker_ip: str) -> None:
    """Check that the fixture set port and host correctly"""
    config = DBConfig()
    assert config.port == 5542
    assert config.host == docker_ip


@pytest_asyncio.fixture(scope="session")
async def ginosession() -> None:
    """make sure db is bound etc"""
    await bind_config()
    LOGGER.debug("Creating raesenmaeher schema")
    await db.status(sqlalchemy.schema.CreateSchema("raesenmaeher"))
    await db.gino.create_all()


@pytest.mark.asyncio
async def test_person_crud(ginosession: None) -> None:
    """Test the db abstraction"""
    _ = ginosession
    obj = Person(callsign="DOGGO01a", pfxpath="/nosushcdir")
    await obj.create()
    obj2 = await Person.by_callsign("DOGGO01a")
    assert obj2.callsign == "DOGGO01a"
    assert not await obj2.has_role("admin")
    assert await obj2.assign_role("admin")
    assert not await obj2.assign_role("admin")  # already assignee, no need to create
    assert await obj2.has_role("admin")
    assert await obj2.remove_role("admin")
    assert not await obj2.remove_role("admin")  # not assigned, no need to delete

    obj3 = await Person.by_pk(str(obj.pk))
    assert obj3.callsign == "DOGGO01a"
    await obj3.delete()

    with pytest.raises(NotFound):
        await Person.by_callsign("PORA22b")

    with pytest.raises(Deleted):
        await Person.by_callsign("DOGGO01a")

    obj4 = await Person.by_callsign("DOGGO01a", allow_deleted=True)
    assert obj4.callsign == "DOGGO01a"
    assert obj4.deleted
