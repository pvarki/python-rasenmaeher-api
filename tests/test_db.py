"""DB specific tests"""
import logging
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from libadvian.binpackers import uuid_to_b64
from multikeyjwt import Verifier
import cryptography.x509

from rasenmaeher_api.db import DBConfig, Person, Enrollment, EnrollmentState, EnrollmentPool, SeenToken, LoginCode
from rasenmaeher_api.db.base import init_db, bind_config
from rasenmaeher_api.db.errors import (
    NotFound,
    Deleted,
    CallsignReserved,
    ForbiddenOperation,
    PoolInactive,
    TokenReuse,
    BackendError,
)
from rasenmaeher_api.jwtinit import jwt_init
from rasenmaeher_api.mtlsinit import mtls_init
from rasenmaeher_api.settings import settings
from rasenmaeher_api.cfssl.public import get_crl

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


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
    await init_db()


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
    # Done this way to avoid the cost of the certificate workflow, you should never do this outside of unittests
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

    old_code = str(obj.approvecode)
    new_code = await obj.reset_approvecode()
    assert old_code != new_code
    new_new_code = await Enrollment.reset_approvecode4callsign("PORA22b")
    assert new_new_code != new_code

    with pytest.raises(CallsignReserved):
        await Enrollment.create_for_callsign("PORA22b")
    with pytest.raises(ForbiddenOperation):
        await obj2.delete()

    await obj.reject(person)
    obj4 = await Enrollment.by_pk(uuid_to_b64(obj.pk))
    assert obj4.decided_on
    assert obj4.decided_by == person.pk
    assert obj4.state == EnrollmentState.REJECTED

    obj5 = await Enrollment.create_for_callsign("ERAPPROVTEST01a")
    person2 = await obj5.approve(person)
    assert person2.callsign == "ERAPPROVTEST01a"


@pytest.mark.asyncio
async def test_enrollmentpools_crud(ginosession: None) -> None:
    """Test the db abstraction enrollments and enrollmentpools"""
    _ = ginosession
    # Done this way to avoid the cost of the certificate workflow, you should never do this outside of unittests
    person = Person(callsign="POOLBOYa", certspath=str(uuid.uuid4()))
    await person.create()
    # Done this way to test low level things, you should always use EnrollmentPool.create_for_owner
    pool = EnrollmentPool(owner=person.pk, extra={"jonnet": "ei tiiä"}, invitecode="12313123")
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

    pool2 = await EnrollmentPool.create_for_owner(person)
    assert pool2.invitecode
    old_code = str(pool2.invitecode)
    new_code = await pool2.reset_invitecode()
    assert old_code != new_code


@pytest.mark.asyncio
async def test_enrollmentpools_list(ginosession: None) -> None:
    """Test list methods"""
    _ = ginosession
    # Done this way to avoid the cost of the certificate workflow, you should never do this outside of unittests
    owner1 = Person(callsign="MASTER666a", certspath=str(uuid.uuid4()))
    await owner1.create()
    owner2 = Person(callsign="BLASTER999a", certspath=str(uuid.uuid4()))
    await owner2.create()

    for _ in range(5):
        await EnrollmentPool.create_for_owner(owner2)
        await EnrollmentPool.create_for_owner(owner1)

    all_codes = {pool.invitecode async for pool in EnrollmentPool.list()}
    owner1_codes = {pool.invitecode async for pool in EnrollmentPool.list(by_owner=owner1)}
    owner2_codes = {pool.invitecode async for pool in EnrollmentPool.list(by_owner=owner2)}
    assert len(all_codes) >= 10
    assert len(owner1_codes) == 5
    assert len(owner2_codes) == 5
    assert owner1_codes.issubset(all_codes)
    assert owner2_codes.issubset(all_codes)
    assert not owner1_codes.intersection(owner2_codes)

    for code in owner1_codes:
        pool = await EnrollmentPool.by_invitecode(code)
        assert pool.owner == owner1.pk

    for code in owner2_codes:
        pool = await EnrollmentPool.by_invitecode(code)
        assert pool.owner == owner2.pk


@pytest.mark.asyncio
async def test_enrollments_list(ginosession: None) -> None:
    """Test list methods"""
    _ = ginosession
    # FIXME: should use fixtures instead of trusting on side effects from previous tests
    # Created in test_enrollmentpools_list
    owner = await Person.by_callsign("MASTER666a")
    active_codes = [pool.invitecode async for pool in EnrollmentPool.list(by_owner=owner) if pool.active]
    pool1 = await EnrollmentPool.by_invitecode(active_codes[0])
    pool2 = await EnrollmentPool.by_invitecode(active_codes[1])

    for _ in range(5):
        await Enrollment.create_for_callsign(str(uuid.uuid4()))
        await Enrollment.create_for_callsign(str(uuid.uuid4()), pool=pool1)
        await Enrollment.create_for_callsign(str(uuid.uuid4()), pool=pool2)

    all_codes = {enr.approvecode async for enr in Enrollment.list()}
    pool1_codes = {enr.approvecode async for enr in Enrollment.list(by_pool=pool1)}
    pool2_codes = {enr.approvecode async for enr in Enrollment.list(by_pool=pool2)}
    assert len(all_codes) >= 15
    assert len(pool1_codes) == 5
    assert len(pool2_codes) == 5
    assert pool1_codes.issubset(all_codes)
    assert pool2_codes.issubset(all_codes)
    assert not pool1_codes.intersection(pool2_codes)


@pytest.mark.asyncio
async def test_seentokens_crud(ginosession: None) -> None:
    """Test the db abstraction for seen tokens"""
    _ = ginosession
    token = str(uuid.uuid4())
    meta = {"koirat": "doggoi"}
    with pytest.raises(NotFound):
        await SeenToken.by_token(token)
    await SeenToken.use_token(token, meta)
    obj = await SeenToken.by_token(token)
    assert "koirat" in obj.auditmeta
    assert obj.auditmeta["koirat"] == "doggoi"

    with pytest.raises(TokenReuse):
        await SeenToken.use_token(token, meta)

    token2 = str(uuid.uuid4())
    await SeenToken.use_token(token2)
    obj2 = await SeenToken.by_token(token2)
    assert not obj2.auditmeta
    with pytest.raises(ForbiddenOperation):
        await obj2.delete()


@pytest.mark.asyncio
async def test_logincodes_crud(ginosession: None) -> None:
    """Test the db abstraction for login codes"""
    _ = ginosession
    await jwt_init()
    code = await LoginCode.create_for_claims({"sub": "sotakoira"})
    obj = await LoginCode.by_code(code)
    assert not obj.used_on
    jwt = await LoginCode.use_code(code)
    obj2 = await LoginCode.by_code(code)
    assert obj2.used_on
    claims = Verifier.singleton().decode(jwt)
    LOGGER.debug("claims={}".format(claims))
    assert "sub" in claims
    assert claims["sub"] == "sotakoira"

    with pytest.raises(ForbiddenOperation):
        await obj2.delete()

    with pytest.raises(TokenReuse):
        await LoginCode.use_code(code)


@pytest.mark.asyncio
async def test_person_with_cert(ginosession: None) -> None:
    """Test the cert creation with the classmethod (and revocation)"""
    _ = ginosession
    await mtls_init()
    person = await Person.create_with_cert("BINGO01a", {"kissa": "puuma"})
    assert person.privkeyfile.exists()
    assert person.pubkeyfile.exists()
    assert person.certfile.exists()
    old_crl = cryptography.x509.load_der_x509_crl(await get_crl())
    old_crl_serials = {revcert.serial_number for revcert in old_crl}
    await person.revoke("key_compromise")
    new_crl = cryptography.x509.load_der_x509_crl(await get_crl())
    new_crl_serials = {revcert.serial_number for revcert in new_crl}
    LOGGER.debug("old_crl={} new_crl={}".format(old_crl_serials, new_crl_serials))
    assert old_crl_serials != new_crl_serials
    refresh = await Person.by_callsign("BINGO01a", allow_deleted=True)
    assert refresh.deleted
    assert refresh.revoke_reason


@pytest.mark.asyncio
async def test_person_with_cert_cfsslfail(ginosession: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the cert creation with the classmethod with CFSSL failure"""
    _ = ginosession
    await mtls_init()
    peoplepath = Path(settings.persistent_data_dir) / "private" / "people"
    old_files = set(peoplepath.rglob("*"))
    with monkeypatch.context() as mpatch:
        mpatch.setattr(settings, "cfssl_host", "http://nosuchost")
        mpatch.setenv("RM_CFSSL_HOST", settings.cfssl_host)
        with pytest.raises(BackendError):
            await Person.create_with_cert("BONGO01a", {"kissa": "puuma"})
        new_files = set(peoplepath.rglob("*"))
        assert new_files == old_files
        with pytest.raises(NotFound):
            await Person.by_callsign("BONGO01a")


@pytest.mark.asyncio
async def test_person_with_cert_duplicatename(ginosession: None) -> None:
    """Test the cert creation with the classmethod but reserved callsign"""
    _ = ginosession
    await mtls_init()
    callsign = "RUOSKA23a"
    peoplepath = Path(settings.persistent_data_dir) / "private" / "people"
    person = await Person.create_with_cert(callsign)
    assert person.privkeyfile.exists()
    assert person.pubkeyfile.exists()
    assert person.certfile.exists()
    old_files = set(peoplepath.rglob("*"))
    assert old_files
    with pytest.raises(CallsignReserved):
        await Person.create_with_cert(callsign)
    new_files = set(peoplepath.rglob("*"))
    assert new_files == old_files
