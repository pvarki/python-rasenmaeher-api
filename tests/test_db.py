"""DB specific tests"""
from typing import Generator
import logging
import uuid
import asyncio

import pytest
import pytest_asyncio
import sqlalchemy
from libadvian.binpackers import uuid_to_b64

from rasenmaeher_api.db import DBConfig, bind_config, db, Person, Enrollment, EnrollmentState, EnrollmentPool
from rasenmaeher_api.db.errors import NotFound, Deleted, CallsignReserved, ForbiddenOperation, PoolInactive

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
    """Test the db abstraction of persons and roles"""
    _ = ginosession
    obj = Person(callsign="DOGGO01a", certspath=str(uuid.uuid4()))
    await obj.create()
    obj2 = await Person.by_callsign("DOGGO01a")
    assert obj2.callsign == "DOGGO01a"
    assert not await obj2.has_role("admin")
    assert await obj2.assign_role("admin")
    assert not await obj2.assign_role("admin")  # already assignee, no need to create

    callsigns = []
    async for user in Person.by_role("admin"):
        callsigns.append(user.callsign)
    assert "DOGGO01a" in callsigns

    callsigns = []
    async for user in Person.by_role("nosuchrole"):
        callsigns.append(user.callsign)
    assert not callsigns

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

    person = Person(callsign="DOGGO01b", certspath=str(uuid.uuid4()))
    await person.create()

    callsigns = []
    async for user in Person.list(False):
        callsigns.append(user.callsign)
    assert "DOGGO01a" not in callsigns
    assert "DOGGO01b" in callsigns

    callsigns = []
    async for user in Person.list(True):
        callsigns.append(user.callsign)
    assert "DOGGO01a" in callsigns
    assert "DOGGO01b" in callsigns


@pytest.mark.asyncio
async def test_enrollments_crud(ginosession: None) -> None:
    """Test the db abstraction enrollments"""
    _ = ginosession
    person = Person(callsign="MEGAMAN00a", certspath=str(uuid.uuid4()))
    await person.create()
    # refresh
    person = await Person.by_callsign("MEGAMAN00a")

    obj = await Enrollment.create_for_callsign("PORA22b")
    assert obj.approvecode
    assert obj.callsign == "PORA22b"
    assert obj.state == EnrollmentState.PENDING
    obj2 = await Enrollment.by_approvecode(obj.approvecode)
    assert obj2.callsign == obj.callsign
    obj3 = await Enrollment.by_callsign(obj.callsign)
    assert obj3.callsign == obj.callsign

    with pytest.raises(CallsignReserved):
        await Enrollment.create_for_callsign("PORA22b")
    with pytest.raises(ForbiddenOperation):
        await obj2.delete()

    await obj.reject(person)
    obj4 = await Enrollment.by_pk(uuid_to_b64(obj.pk))
    assert obj4.decided_on
    assert obj4.decided_by == person.pk
    assert obj4.state == EnrollmentState.REJECTED
    # Approval is missing functionality in person class


@pytest.mark.asyncio
async def test_enrollmentpools_crud(ginosession: None) -> None:
    """Test the db abstraction enrollments and enrollmentpools"""
    _ = ginosession
    person = Person(callsign="POOLBOYa", certspath=str(uuid.uuid4()))
    await person.create()
    pool = EnrollmentPool(owner=person.pk, extra={"jonnet": "ei tiiä"})
    await pool.create()
    # refresh
    pool = await EnrollmentPool.by_pk(pool.pk)
    assert pool.active

    pool = await pool.set_active(False)
    with pytest.raises(PoolInactive):
        await pool.create_enrollment(str(uuid.uuid4()))
    pool = await pool.set_active(True)
    enr1 = await pool.create_enrollment("JONNE01a")
    assert "jonnet" in enr1.extra
    assert enr1.extra["jonnet"] == "ei tiiä"
    assert enr1.pool == pool.pk

    await pool.delete()
    with pytest.raises(Deleted):
        await EnrollmentPool.by_pk(pool.pk)
    # refresh
    pool = await EnrollmentPool.by_pk(pool.pk, allow_deleted=True)
    with pytest.raises(Deleted):
        await pool.create_enrollment(str(uuid.uuid4()))
