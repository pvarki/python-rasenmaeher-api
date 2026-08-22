"""DB specific tests"""

import asyncio
import logging
import secrets
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cryptography.hazmat.primitives.serialization.pkcs12
import cryptography.x509
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from flaky import flaky  # type: ignore[import-untyped]
from libadvian.binpackers import uuid_to_b64
from multikeyjwt import Verifier

from rasenmaeher_api.cert.backend import get_crl
from rasenmaeher_api.db import (
    DBConfig,
    EngineWrapper,
    Enrollment,
    EnrollmentPool,
    EnrollmentState,
    LoginCode,
    Person,
    SeenToken,
)
from rasenmaeher_api.db.errors import (
    BackendError,
    CallsignReserved,
    Deleted,
    ForbiddenOperation,
    NotFound,
    PoolInactive,
    TokenReuse,
)
from rasenmaeher_api.db.issuedcerts import IssuedCert, record_issued_cert
from rasenmaeher_api.jwtinit import jwt_init
from rasenmaeher_api.mtlsinit import mtls_init
from rasenmaeher_api.rmsettings import RMSettings, switchme_to_singleton_call

LOGGER = logging.getLogger(__name__)


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


@pytest.mark.asyncio(loop_scope="session")
async def test_person_crud(dbinit_func) -> None:
    """Test the db abstraction of persons and roles"""
    _ = dbinit_func
    DOGGO01a = f"DOGGO01a_{secrets.token_hex(4)}"
    with EngineWrapper.singleton().get_session() as session:
        obj = Person(callsign=DOGGO01a, certspath=str(uuid.uuid4()))
        session.add(obj)
        session.commit()
        session.refresh(obj)
    obj2 = await Person.by_callsign(DOGGO01a)
    assert obj2.callsign == DOGGO01a
    assert not await obj2.has_role("admin")
    assert await obj2.assign_role("admin")
    assert not await obj2.assign_role("admin")  # already assignee, no need to create
    # Test the get pk or callsign helper
    await Person.by_pk_or_callsign(DOGGO01a)
    await Person.by_pk_or_callsign(str(obj.pk))
    await Person.by_pk_or_callsign(uuid_to_b64(obj.pk))
    await Person.by_pk_or_callsign(obj.pk)

    callsigns = []
    async for user in Person.by_role("admin"):
        callsigns.append(user.callsign)
    assert DOGGO01a in callsigns

    callsigns = []
    async for user in Person.by_role("nosuchrole"):
        callsigns.append(user.callsign)
    assert not callsigns

    assert await obj2.has_role("admin")
    assert await obj2.remove_role("admin")
    assert not await obj2.remove_role("admin")  # not assigned, no need to delete

    obj3 = await Person.by_pk(str(obj.pk))
    assert obj3.callsign == DOGGO01a
    await obj3.delete()

    with pytest.raises(NotFound):
        await Person.by_callsign("PORA22b")

    with pytest.raises(Deleted):
        await Person.by_callsign(DOGGO01a)

    obj4 = await Person.by_callsign(DOGGO01a, allow_deleted=True)
    assert obj4.callsign == DOGGO01a
    assert obj4.deleted

    DOGGO01b = f"DOGGO01b_{secrets.token_hex(4)}"
    with EngineWrapper.singleton().get_session() as session:
        person = Person(callsign=DOGGO01b, certspath=str(uuid.uuid4()))
        session.add(person)
        session.commit()
        session.refresh(person)

    callsigns = []
    async for user in Person.list(False):
        callsigns.append(user.callsign)
    assert DOGGO01a not in callsigns
    assert DOGGO01b in callsigns

    callsigns = []
    async for user in Person.list(True):
        callsigns.append(user.callsign)
    assert DOGGO01a in callsigns
    assert DOGGO01b in callsigns


@pytest.mark.asyncio(loop_scope="session")
async def test_enrollments_crud(dbinit_func) -> None:
    """Test the db abstraction enrollments"""
    _ = dbinit_func
    MEGAMAN00a = f"DOGGO01a_{secrets.token_hex(4)}"
    # Done this way to avoid the cost of the certificate workflow, you should never do this outside of unittests
    with EngineWrapper.singleton().get_session() as session:
        person = Person(callsign=MEGAMAN00a, certspath=str(uuid.uuid4()))
        session.add(person)
        session.commit()
        session.refresh(person)
    # refresh
    person = await Person.by_callsign(MEGAMAN00a)

    PORA22b = f"PORA22b_{secrets.token_hex(4)}"
    obj = await Enrollment.create_for_callsign(PORA22b)
    assert obj.approvecode
    assert obj.callsign == PORA22b
    assert obj.state == EnrollmentState.PENDING
    obj2 = await Enrollment.by_approvecode(obj.approvecode)
    assert obj2.callsign == obj.callsign
    obj3 = await Enrollment.by_callsign(obj.callsign)
    assert obj3.callsign == obj.callsign

    await Enrollment.by_pk_or_callsign(PORA22b)
    await Enrollment.by_pk_or_callsign(str(obj.pk))
    await Enrollment.by_pk_or_callsign(uuid_to_b64(obj.pk))
    await Enrollment.by_pk_or_callsign(obj.pk)

    old_code = str(obj.approvecode)
    new_code = await obj.reset_approvecode()
    assert old_code != new_code
    new_new_code = await Enrollment.reset_approvecode4callsign(PORA22b)
    assert new_new_code != new_code

    with pytest.raises(CallsignReserved):
        await Enrollment.create_for_callsign(PORA22b)
    with pytest.raises(ForbiddenOperation):
        await obj2.delete()

    await obj.reject(person)
    obj4 = await Enrollment.by_pk(uuid_to_b64(obj.pk))
    assert obj4.decided_on
    assert obj4.decided_by == person.pk
    assert obj4.state == EnrollmentState.REJECTED

    ERAPPROVTEST01a = f"ERAPPROVTEST01a_{secrets.token_hex(4)}"
    obj5 = await Enrollment.create_for_callsign(ERAPPROVTEST01a)
    person2 = await obj5.approve(person)
    assert person2.callsign == ERAPPROVTEST01a


@pytest.mark.asyncio(loop_scope="session")
async def test_enrollmentpools_crud(dbinit_func) -> None:
    """Test the db abstraction enrollments and enrollmentpools"""
    _ = dbinit_func
    # Done this way to avoid the cost of the certificate workflow, you should never do this outside of unittests
    POOLBOYa = f"POOLBOYa_{secrets.token_hex(4)}"
    with EngineWrapper.singleton().get_session() as session:
        person = Person(callsign=POOLBOYa, certspath=str(uuid.uuid4()))
        session.add(person)
        session.commit()
        session.refresh(person)
        pool = EnrollmentPool(owner=person.pk, extra={"jonnet": "ei tiiä"}, invitecode="12313123")
        session.add(pool)
        session.commit()
        session.refresh(pool)
    # refresh
    pool = await EnrollmentPool.by_pk(pool.pk)
    assert pool.active

    await EnrollmentPool.by_pk_or_invitecode(pool.invitecode)
    await EnrollmentPool.by_pk_or_invitecode(str(pool.pk))
    await EnrollmentPool.by_pk_or_invitecode(uuid_to_b64(pool.pk))
    await EnrollmentPool.by_pk_or_invitecode(pool.pk)

    JONNE01a = f"JONNE01a_{secrets.token_hex(4)}"
    pool = await pool.set_active(False)
    with pytest.raises(PoolInactive):
        await pool.create_enrollment(str(uuid.uuid4()))
    pool = await pool.set_active(True)
    enr1 = await pool.create_enrollment(JONNE01a)
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

    # refresh the person again (needed for some reason)
    person = await Person.by_callsign(POOLBOYa)
    pool2 = await EnrollmentPool.create_for_owner(person)
    assert pool2.invitecode
    old_code = str(pool2.invitecode)
    new_code = await pool2.reset_invitecode()
    assert old_code != new_code


@pytest_asyncio.fixture(scope="session")
async def masterblaster(dbinit_sess) -> AsyncGenerator[(Person, Person), None]:
    """Fixture for two persons"""
    _ = dbinit_sess
    MASTER666a = f"MASTER666a_{secrets.token_hex(4)}"
    BLASTER999a = f"BLASTER999a_{secrets.token_hex(4)}"
    # Done this way to avoid the cost of the certificate workflow, you should never do this outside of unittests
    with EngineWrapper.singleton().get_session() as session:
        owner1 = Person(callsign=MASTER666a, certspath=str(uuid.uuid4()))
        session.add(owner1)
        owner2 = Person(callsign=BLASTER999a, certspath=str(uuid.uuid4()))
        session.add(owner2)
        session.commit()
        session.refresh(owner1)
        session.refresh(owner2)
    return owner1, owner2


@pytest.mark.asyncio(loop_scope="session")
async def test_enrollmentpools_list(masterblaster: (Person, Person)) -> None:
    """Test list methods"""
    owner1, owner2 = masterblaster

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


@pytest.mark.asyncio(loop_scope="session")
async def test_enrollments_list(masterblaster: (Person, Person)) -> None:
    """Test list methods"""
    owner1, _ = masterblaster
    owner = await Person.by_callsign(owner1.callsign)
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


@pytest.mark.asyncio(loop_scope="session")
async def test_seentokens_crud(dbinit_func) -> None:
    """Test the db abstraction for seen tokens"""
    _ = dbinit_func
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


@pytest.mark.asyncio(loop_scope="session")
async def test_logincodes_crud(dbinit_func) -> None:
    """Test the db abstraction for login codes"""
    _ = dbinit_func
    sotakoira = f"sotakoira_{secrets.token_hex(4)}"

    await jwt_init()
    code = await LoginCode.create_for_claims({"sub": sotakoira})
    obj = await LoginCode.by_code(code)
    assert not obj.used_on
    jwt = await LoginCode.use_code(code)
    obj2 = await LoginCode.by_code(code)
    assert obj2.used_on
    claims = Verifier.singleton().decode(jwt)
    LOGGER.debug(f"claims={claims}")
    assert "sub" in claims
    assert claims["sub"] == sotakoira

    with pytest.raises(ForbiddenOperation):
        await obj2.delete()

    with pytest.raises(TokenReuse):
        await LoginCode.use_code(code)


@flaky(max_runs=3, min_passes=1)
@pytest.mark.asyncio(loop_scope="session")
async def test_person_with_cert(dbinit_func) -> None:
    """Test the cert creation with the classmethod (and revocation)"""
    _ = dbinit_func
    await mtls_init()
    BINGO01a = f"BINGO01a_{secrets.token_hex(4)}"
    person = await Person.create_with_cert(BINGO01a, {"kissa": "puuma"})
    assert person.privkeyfile.exists()
    assert person.pubkeyfile.exists()
    assert person.certfile.exists()
    old_crl = cryptography.x509.load_der_x509_crl(await get_crl())
    old_crl_serials = {revcert.serial_number for revcert in old_crl}
    await person.revoke("key_compromise")
    new_crl = cryptography.x509.load_der_x509_crl(await get_crl())
    new_crl_serials = {revcert.serial_number for revcert in new_crl}
    LOGGER.debug(f"old_crl={old_crl_serials} new_crl={new_crl_serials}")
    assert old_crl_serials != new_crl_serials
    refresh = await Person.by_callsign(BINGO01a, allow_deleted=True)
    assert refresh.deleted
    assert refresh.revoke_reason


@pytest.mark.xfail(reason="monkeypatching the host does not work as expected")
@pytest.mark.asyncio(loop_scope="session")
async def test_person_with_cert_cfsslfail(dbinit_func, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the cert creation with the classmethod with CFSSL failure"""
    _ = dbinit_func
    await mtls_init()
    BONGO01a = f"BONGO01a_{secrets.token_hex(4)}"
    peoplepath = Path(switchme_to_singleton_call.persistent_data_dir) / "private" / "people"
    old_files = set(peoplepath.rglob("*"))
    RMSettings.singleton()
    assert RMSettings._singleton
    with monkeypatch.context() as mpatch:
        mpatch.setattr(RMSettings._singleton, "cfssl_host", "http://nosuchost")
        mpatch.setenv("RM_CFSSL_HOST", RMSettings._singleton.cfssl_host)
        with pytest.raises(BackendError):
            await Person.create_with_cert(BONGO01a, {"kissa": "puuma"})
        new_files = set(peoplepath.rglob("*"))
        assert new_files == old_files
        with pytest.raises(NotFound):
            await Person.by_callsign(BONGO01a)


@flaky(max_runs=3, min_passes=1)
@pytest.mark.asyncio(loop_scope="session")
async def test_person_with_cert_duplicatename(dbinit_func) -> None:
    """Test the cert creation with the classmethod but reserved callsign"""
    _ = dbinit_func
    await mtls_init()
    callsign = f"RUOSKA23a_{secrets.token_hex(4)}"
    peoplepath = Path(switchme_to_singleton_call.persistent_data_dir) / "private" / "people"
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


@pytest.mark.asyncio(loop_scope="session")
async def test_pfx_parse(dbinit_func) -> None:
    """Test that the PFX file gets done"""
    _ = dbinit_func
    await mtls_init()
    callsign = f"PFXMAN01a_{secrets.token_hex(4)}"
    person = await Person.create_with_cert(callsign)

    async def wait_for_pfxfile() -> None:
        """wait for the background task to do it's work"""
        nonlocal person
        while not person.pfxfile.exists():
            await asyncio.sleep(0.5)

    await asyncio.wait_for(wait_for_pfxfile(), timeout=5.0)

    assert person.pfxfile.exists()
    pfxbytes = person.pfxfile.read_bytes()
    pfxdata = cryptography.hazmat.primitives.serialization.pkcs12.load_pkcs12(pfxbytes, callsign.encode("ascii"))
    assert pfxdata.key
    assert pfxdata.cert


@pytest.mark.asyncio(loop_scope="session")
async def test_productcn_forbid(dbinit_func) -> None:
    """Test that trying to create enrollment or person with callsign that matches a product CN fails"""
    _ = dbinit_func
    with pytest.raises(CallsignReserved):
        await Person.create_with_cert("fake.localmaeher.dev.pvarki.fi")
    with pytest.raises(CallsignReserved):
        await Enrollment.create_for_callsign("fake.localmaeher.dev.pvarki.fi")


def _self_signed_pem(common_name: str) -> str:
    """Throwaway self-signed cert, enough for the issued-certs parser"""
    key = ec.generate_private_key(ec.SECP256R1())
    name = cryptography.x509.Name([cryptography.x509.NameAttribute(cryptography.x509.NameOID.COMMON_NAME, common_name)])
    now = datetime.now(UTC)
    cert = (
        cryptography.x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(cryptography.x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


@pytest.mark.asyncio(loop_scope="session")
async def test_record_issued_cert(dbinit_func) -> None:
    """record_issued_cert parses and stores the leaf, is idempotent, never raises"""
    _ = dbinit_func
    common_name = "fake.localmaeher.dev.pvarki.fi"
    pem = _self_signed_pem(common_name)
    serial = cryptography.x509.load_pem_x509_certificate(pem.encode("ascii")).serial_number
    await record_issued_cert(pem)
    await record_issued_cert(pem)  # duplicate must be swallowed
    row = await IssuedCert.by_serial(str(serial))
    assert row is not None
    assert row.cn == common_name
    await record_issued_cert("not a pem at all")  # must not raise
