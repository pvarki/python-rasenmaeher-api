"""OCSP responder tests (cert_manager backend)"""

import base64
import logging
import os
import urllib.parse
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509 import ocsp
from cryptography.x509.oid import NameOID
from fastapi import FastAPI

from rasenmaeher_api.cert.cert_manager.ocsp import signer
from rasenmaeher_api.cert.cert_manager.ocsp.responder import build_ocsp_response
from rasenmaeher_api.db import EngineWrapper, Person
from rasenmaeher_api.db.issuedcerts import IssuedCert, record_issued_cert
from rasenmaeher_api.rmsettings import switchme_to_singleton_call

LOGGER = logging.getLogger(__name__)

VALID_PRODUCT_CN = "fake.localmaeher.dev.pvarki.fi"  # from the test kraftwerk manifest


def _make_ca(common_name: str) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    """Self-signed EC-P256 CA"""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return key, cert


@dataclass
class OCSPTestEnv:
    """Throwaway CA + request helpers"""

    ca_key: ec.EllipticCurvePrivateKey
    ca_cert: x509.Certificate
    foreign_key: ec.EllipticCurvePrivateKey = field(init=False)
    foreign_cert: x509.Certificate = field(init=False)

    def __post_init__(self) -> None:
        self.foreign_key, self.foreign_cert = _make_ca("foreign-ca")

    def make_leaf(self, common_name: str, foreign: bool = False) -> x509.Certificate:
        """CA-signed leaf with a random serial"""
        cakey = self.foreign_key if foreign else self.ca_key
        cacert = self.foreign_cert if foreign else self.ca_cert
        key = ec.generate_private_key(ec.SECP256R1())
        now = datetime.now(UTC)
        return (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
            .issuer_name(cacert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=1))
            .sign(cakey, hashes.SHA256())
        )

    def make_request(
        self,
        leaf: x509.Certificate,
        algorithm: hashes.HashAlgorithm | None = None,
        nonce: bytes | None = None,
        foreign: bool = False,
    ) -> bytes:
        """DER OCSP request for the given leaf"""
        issuer = self.foreign_cert if foreign else self.ca_cert
        builder = ocsp.OCSPRequestBuilder().add_certificate(leaf, issuer, algorithm or hashes.SHA1())
        if nonce is not None:
            builder = builder.add_extension(x509.OCSPNonce(nonce), critical=False)
        return builder.build().public_bytes(serialization.Encoding.DER)


@pytest.fixture()
def ocsp_env(monkeypatch: pytest.MonkeyPatch) -> OCSPTestEnv:
    """Inject a throwaway CA into the signer cache (no k8s in tests)"""
    ca_key, ca_cert = _make_ca("test-intermediate")
    monkeypatch.setattr(signer, "_CACHED", signer.SignerMaterial(cert=ca_cert, key=ca_key))
    return OCSPTestEnv(ca_key=ca_key, ca_cert=ca_cert)


@pytest_asyncio.fixture()
async def ocsp_client() -> AsyncGenerator[TestClient, None]:
    """Minimal app with just the OCSP router (session app runs the cfssl backend)"""
    from rasenmaeher_api.cert.cert_manager.ocsp import router as ocsp_router

    app = FastAPI()
    app.include_router(ocsp_router, prefix="/api/v1/ocsp")
    async with TestClient(app) as client:
        yield client


def _add_person(
    serial: int | None = None,
    deleted: datetime | None = None,
    revoke_reason: str | None = None,
    tmp: str = "",
    callsign: str | None = None,
) -> Person:
    """Insert a Person row directly (bypasses cert signing)"""
    person = Person(
        callsign=callsign or f"ocsptest_{uuid.uuid4()}",
        certspath=f"{tmp}/ocsptest/{uuid.uuid4()}",
        extra={},
        cert_serial=str(serial) if serial is not None else None,
    )
    if deleted:
        person.deleted = deleted
        person.revoke_reason = revoke_reason or "unspecified"
    with EngineWrapper.get_session() as session:
        session.add(person)
        session.commit()
        session.refresh(person)
    return person


def _add_issued(serial: int, common_name: str) -> None:
    """Insert an IssuedCert row directly"""
    with EngineWrapper.get_session() as session:
        session.add(IssuedCert(serial=str(serial), cn=common_name))
        session.commit()


async def _respond(der: bytes) -> ocsp.OCSPResponse:
    resp_der, _ = await build_ocsp_response(der)
    return ocsp.load_der_ocsp_response(resp_der)


@pytest.mark.asyncio(loop_scope="session")
async def test_garbage_is_malformed(ocsp_env: OCSPTestEnv) -> None:
    """Unparseable bytes get an OCSP-level malformed response"""
    _ = ocsp_env
    resp = await _respond(b"this is not an ocsp request")
    assert resp.response_status == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="session")
async def test_foreign_ca_is_unauthorized(ocsp_env: OCSPTestEnv) -> None:
    """Requests about certs from another CA are not our business"""
    leaf = ocsp_env.make_leaf("EVIL", foreign=True)
    resp = await _respond(ocsp_env.make_request(leaf, foreign=True))
    assert resp.response_status == ocsp.OCSPResponseStatus.UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_unsupported_hash_is_unauthorized(ocsp_env: OCSPTestEnv) -> None:
    """CertID hash algorithms outside sha1/sha256 are rejected"""
    leaf = ocsp_env.make_leaf("LEAF1")
    resp = await _respond(ocsp_env.make_request(leaf, algorithm=hashes.SHA384()))
    assert resp.response_status == ocsp.OCSPResponseStatus.UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_good_user(ocsp_env: OCSPTestEnv, ginosession: None, nice_tmpdir: str) -> None:
    """Active user -> GOOD, signature verifies, both hash algos work"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("GOODUSER")
    _add_person(leaf.serial_number, tmp=nice_tmpdir)
    for algo in (hashes.SHA1(), hashes.SHA256()):
        resp = await _respond(ocsp_env.make_request(leaf, algorithm=algo))
        assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
        assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD
        assert resp.serial_number == leaf.serial_number
        pubkey = ocsp_env.ca_cert.public_key()
        assert isinstance(pubkey, ec.EllipticCurvePublicKey)
        pubkey.verify(resp.signature, resp.tbs_response_bytes, ec.ECDSA(hashes.SHA256()))


@pytest.mark.asyncio(loop_scope="session")
async def test_revoked_user(ocsp_env: OCSPTestEnv, ginosession: None, nice_tmpdir: str) -> None:
    """Deleted user -> REVOKED with reason and time"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("REVOKEDUSER")
    deleted = datetime.now(UTC)
    _add_person(leaf.serial_number, deleted=deleted, revoke_reason="key_compromise", tmp=nice_tmpdir)
    resp = await _respond(ocsp_env.make_request(leaf))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert resp.certificate_status == ocsp.OCSPCertStatus.REVOKED
    assert resp.revocation_reason == x509.ReasonFlags.key_compromise
    assert resp.revocation_time_utc is not None
    assert abs((resp.revocation_time_utc - deleted).total_seconds()) < 2.0


@pytest.mark.asyncio(loop_scope="session")
async def test_product_cert_valid_cn(ocsp_env: OCSPTestEnv, ginosession: None) -> None:
    """Recorded product certs with manifest CNs (and rmapi's own CN) -> GOOD"""
    _ = ginosession
    for common_name in (VALID_PRODUCT_CN, switchme_to_singleton_call.mtls_client_cert_cn):
        leaf = ocsp_env.make_leaf(common_name)
        _add_issued(leaf.serial_number, common_name)
        resp = await _respond(ocsp_env.make_request(leaf))
        assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
        assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD


@pytest.mark.asyncio(loop_scope="session")
async def test_issued_cert_active_user_cn(ocsp_env: OCSPTestEnv, ginosession: None, nice_tmpdir: str) -> None:
    """Per-user cert signed via product path (e.g. TAK) with an active owner -> GOOD"""
    _ = ginosession
    callsign = f"atakuser_{uuid.uuid4()}"
    _add_person(tmp=nice_tmpdir, callsign=callsign)  # active owner, different (main) cert serial
    leaf = ocsp_env.make_leaf(callsign)
    _add_issued(leaf.serial_number, callsign)  # TAK's separate per-user cert
    resp = await _respond(ocsp_env.make_request(leaf))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD


@pytest.mark.asyncio(loop_scope="session")
async def test_issued_cert_revoked_user_cn(ocsp_env: OCSPTestEnv, ginosession: None, nice_tmpdir: str) -> None:
    """Per-user cert signed via product path whose owner is revoked -> REVOKED with owner's reason"""
    _ = ginosession
    callsign = f"atakuser_{uuid.uuid4()}"
    _add_person(tmp=nice_tmpdir, callsign=callsign, deleted=datetime.now(UTC), revoke_reason="privilege_withdrawn")
    leaf = ocsp_env.make_leaf(callsign)
    _add_issued(leaf.serial_number, callsign)
    resp = await _respond(ocsp_env.make_request(leaf))
    assert resp.certificate_status == ocsp.OCSPCertStatus.REVOKED
    assert resp.revocation_reason == x509.ReasonFlags.privilege_withdrawn


@pytest.mark.asyncio(loop_scope="session")
async def test_issued_cert_no_owner_cn(ocsp_env: OCSPTestEnv, ginosession: None) -> None:
    """Recorded cert whose CN matches no Person and no product -> GOOD (we issued it)"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("orphan.example.invalid")
    _add_issued(leaf.serial_number, "orphan.example.invalid")
    resp = await _respond(ocsp_env.make_request(leaf))
    assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD


@pytest.mark.asyncio(loop_scope="session")
async def test_unknown_serial(ocsp_env: OCSPTestEnv, ginosession: None) -> None:
    """Serial in neither table -> UNKNOWN"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("NEVERRECORDED")
    resp = await _respond(ocsp_env.make_request(leaf))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert resp.certificate_status == ocsp.OCSPCertStatus.UNKNOWN


@pytest.mark.asyncio(loop_scope="session")
async def test_nonce_echo(ocsp_env: OCSPTestEnv, ginosession: None) -> None:
    """Nonce comes back byte-for-byte; oversize nonce is malformed"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("NONCELEAF")
    nonce = os.urandom(16)
    resp = await _respond(ocsp_env.make_request(leaf, nonce=nonce))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    echoed = resp.extensions.get_extension_for_class(x509.OCSPNonce).value.nonce
    assert echoed == nonce

    resp = await _respond(ocsp_env.make_request(leaf, nonce=os.urandom(33)))
    assert resp.response_status == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="session")
async def test_http_post_and_get(ocsp_env: OCSPTestEnv, ginosession: None, ocsp_client: TestClient) -> None:
    """POST body and GET base64-path forms return equivalent responses with cache headers"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("HTTPLEAF")
    reqder = ocsp_env.make_request(leaf)

    postresp = await ocsp_client.post("/api/v1/ocsp", data=reqder)
    assert postresp.status_code == 200
    assert postresp.headers["content-type"] == "application/ocsp-response"
    assert "max-age=" in postresp.headers["cache-control"]
    parsed = ocsp.load_der_ocsp_response(postresp.content)
    assert parsed.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert parsed.serial_number == leaf.serial_number

    b64 = urllib.parse.quote(base64.b64encode(reqder).decode("ascii"), safe="")
    getresp = await ocsp_client.get(f"/api/v1/ocsp/{b64}")
    assert getresp.status_code == 200
    gparsed = ocsp.load_der_ocsp_response(getresp.content)
    assert gparsed.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert gparsed.serial_number == parsed.serial_number
    assert gparsed.certificate_status == parsed.certificate_status


@pytest.mark.asyncio(loop_scope="session")
async def test_http_nonce_no_store(ocsp_env: OCSPTestEnv, ginosession: None, ocsp_client: TestClient) -> None:
    """Nonced responses must not be cached"""
    _ = ginosession
    leaf = ocsp_env.make_leaf("NONCEHTTP")
    reqder = ocsp_env.make_request(leaf, nonce=os.urandom(8))
    resp = await ocsp_client.post("/api/v1/ocsp", data=reqder)
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store"


@pytest.mark.asyncio(loop_scope="session")
async def test_http_bad_base64(ocsp_env: OCSPTestEnv, ocsp_client: TestClient) -> None:
    """Garbage in the GET path is an OCSP-level malformed response, still HTTP 200"""
    _ = ocsp_env
    resp = await ocsp_client.get("/api/v1/ocsp/not!!!base64===")
    assert resp.status_code == 200
    parsed = ocsp.load_der_ocsp_response(resp.content)
    assert parsed.response_status == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="session")
async def test_record_issued_cert(ocsp_env: OCSPTestEnv, ginosession: None) -> None:
    """record_issued_cert parses and stores the leaf, is idempotent, never raises"""
    _ = ginosession
    leaf = ocsp_env.make_leaf(VALID_PRODUCT_CN)
    pem = leaf.public_bytes(serialization.Encoding.PEM).decode("ascii")
    await record_issued_cert(pem)
    await record_issued_cert(pem)  # duplicate must be swallowed
    row = await IssuedCert.by_serial(str(leaf.serial_number))
    assert row is not None
    assert row.cn == VALID_PRODUCT_CN
    await record_issued_cert("not a pem at all")  # must not raise
