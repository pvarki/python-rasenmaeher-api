"""Tests for the OCSP responder at /api/v1/ocsp."""

import base64
import datetime
import logging
import uuid
from pathlib import Path
from typing import Tuple

import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import ocsp
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from rasenmaeher_api.db.people import Person
from rasenmaeher_api.mtlsinit import mtls_init
from rasenmaeher_api.rmsettings import RMSettings
from rasenmaeher_api.web.api.ocsp import views as ocsp_views


LOGGER = logging.getLogger(__name__)


def _make_signer(tmp_path: Path) -> Tuple[Path, Path]:
    """Generate a self-signed OCSP signer cert + key for the test."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ocsp-signer")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.OCSP_SIGNING]),
            critical=False,
        )
        .sign(private_key=key, algorithm=hashes.SHA256())
    )
    cert_path = tmp_path / "ocsp-signer.crt"
    key_path = tmp_path / "ocsp-signer.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


def _build_ocsp_request_for(person_cert_pem: bytes, issuer_cert: x509.Certificate) -> bytes:
    """Build a DER OCSP request for the given (subject_cert, issuer_cert) pair."""
    subject = x509.load_pem_x509_certificate(person_cert_pem)
    req = ocsp.OCSPRequestBuilder().add_certificate(subject, issuer_cert, hashes.SHA1()).build()
    return req.public_bytes(serialization.Encoding.DER)


@pytest_asyncio.fixture
async def ocsp_signer_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Tuple[Path, Path]:
    """Provision a signer cert+key on disk and point RMSettings at them."""
    cert_path, key_path = _make_signer(tmp_path)
    settings = RMSettings.singleton()
    monkeypatch.setattr(settings, "cert_manager_ocsp_signer_cert_path", str(cert_path))
    monkeypatch.setattr(settings, "cert_manager_ocsp_signer_key_path", str(key_path))
    # New paths -> bust the lru_cache.
    ocsp_views._load_signer_cached.cache_clear()
    return cert_path, key_path


@pytest.mark.asyncio(loop_scope="session")
async def test_ocsp_good(
    ginosession: None,
    unauth_client: TestClient,
    ocsp_signer_paths: Tuple[Path, Path],
) -> None:
    """A live person's cert returns OCSP status GOOD."""
    _ = ginosession, ocsp_signer_paths
    await mtls_init()
    callsign = f"OCSPGOOD{uuid.uuid4().hex[:6]}"
    person = await Person.create_with_cert(callsign)
    assert person.cert_serial is not None

    person_pem = person.certfile.read_bytes()
    # We don't have the real issuer cert handy in this test; use a self-signed
    # placeholder. The responder uses add_response_by_hash and echoes whatever
    # hashes the request carries, so this still exercises the full path.
    placeholder_issuer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.UTC)
    placeholder_issuer = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "placeholder")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "placeholder")]))
        .public_key(placeholder_issuer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key=placeholder_issuer_key, algorithm=hashes.SHA256())
    )

    der_req = _build_ocsp_request_for(person_pem, placeholder_issuer)
    resp = await unauth_client.post(
        "/api/v1/ocsp",
        data=der_req,
        headers={"Content-Type": "application/ocsp-request"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/ocsp-response"
    ocsp_resp = ocsp.load_der_ocsp_response(resp.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert ocsp_resp.certificate_status == ocsp.OCSPCertStatus.GOOD
    assert ocsp_resp.serial_number == int(person.cert_serial)


@pytest.mark.asyncio(loop_scope="session")
async def test_ocsp_revoked(
    ginosession: None,
    unauth_client: TestClient,
    ocsp_signer_paths: Tuple[Path, Path],
) -> None:
    """A revoked person's cert returns OCSP status REVOKED with a reason."""
    _ = ginosession, ocsp_signer_paths
    await mtls_init()
    callsign = f"OCSPREV{uuid.uuid4().hex[:6]}"
    person = await Person.create_with_cert(callsign)
    await person.revoke("privilege_withdrawn")

    person_pem = person.certfile.read_bytes()
    placeholder_issuer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.UTC)
    placeholder_issuer = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "placeholder")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "placeholder")]))
        .public_key(placeholder_issuer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key=placeholder_issuer_key, algorithm=hashes.SHA256())
    )

    der_req = _build_ocsp_request_for(person_pem, placeholder_issuer)
    resp = await unauth_client.post(
        "/api/v1/ocsp",
        data=der_req,
        headers={"Content-Type": "application/ocsp-request"},
    )
    assert resp.status_code == 200
    ocsp_resp = ocsp.load_der_ocsp_response(resp.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert ocsp_resp.certificate_status == ocsp.OCSPCertStatus.REVOKED
    assert ocsp_resp.revocation_reason == x509.ReasonFlags.privilege_withdrawn
    assert ocsp_resp.revocation_time_utc is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_ocsp_unknown(
    ginosession: None,
    unauth_client: TestClient,
    ocsp_signer_paths: Tuple[Path, Path],
) -> None:
    """A serial that isn't in the DB returns OCSP status UNKNOWN."""
    _ = ginosession, ocsp_signer_paths
    # Forge a request for a never-issued serial by building a request against a
    # self-signed throwaway cert. add_response_by_hash echoes the serial back.
    throwaway_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.UTC)
    issuer = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "throw-iss")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "throw-iss")]))
        .public_key(throwaway_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key=throwaway_key, algorithm=hashes.SHA256())
    )
    subject = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "throw-sub")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "throw-iss")]))
        .public_key(throwaway_key.public_key())
        .serial_number(0xDEADBEEF)  # not in DB
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key=throwaway_key, algorithm=hashes.SHA256())
    )
    req = ocsp.OCSPRequestBuilder().add_certificate(subject, issuer, hashes.SHA1()).build()
    der_req = req.public_bytes(serialization.Encoding.DER)
    resp = await unauth_client.post(
        "/api/v1/ocsp",
        data=der_req,
        headers={"Content-Type": "application/ocsp-request"},
    )
    assert resp.status_code == 200
    ocsp_resp = ocsp.load_der_ocsp_response(resp.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert ocsp_resp.certificate_status == ocsp.OCSPCertStatus.UNKNOWN
    assert ocsp_resp.serial_number == 0xDEADBEEF


@pytest.mark.asyncio(loop_scope="session")
async def test_ocsp_malformed(
    ginosession: None,
    unauth_client: TestClient,
    ocsp_signer_paths: Tuple[Path, Path],
) -> None:
    """Garbage in the request body produces MALFORMED_REQUEST per RFC 6960."""
    _ = ginosession, ocsp_signer_paths
    resp = await unauth_client.post(
        "/api/v1/ocsp",
        data=b"this is not DER",
        headers={"Content-Type": "application/ocsp-request"},
    )
    assert resp.status_code == 200
    ocsp_resp = ocsp.load_der_ocsp_response(resp.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="session")
async def test_ocsp_get_equivalent_to_post(
    ginosession: None,
    unauth_client: TestClient,
    ocsp_signer_paths: Tuple[Path, Path],
) -> None:
    """GET /api/v1/ocsp/{b64req} returns the same status as POST."""
    _ = ginosession, ocsp_signer_paths
    await mtls_init()
    callsign = f"OCSPGET{uuid.uuid4().hex[:6]}"
    person = await Person.create_with_cert(callsign)
    person_pem = person.certfile.read_bytes()
    placeholder_issuer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.UTC)
    placeholder_issuer = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "placeholder")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "placeholder")]))
        .public_key(placeholder_issuer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key=placeholder_issuer_key, algorithm=hashes.SHA256())
    )
    der_req = _build_ocsp_request_for(person_pem, placeholder_issuer)
    # base64.urlsafe_b64encode keeps `/` etc out of the path so it survives any
    # routing layer that might object to literal slashes in the path param.
    b64 = base64.urlsafe_b64encode(der_req).decode("ascii").rstrip("=")

    resp = await unauth_client.get(f"/api/v1/ocsp/{b64}")
    assert resp.status_code == 200
    ocsp_resp = ocsp.load_der_ocsp_response(resp.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert ocsp_resp.certificate_status == ocsp.OCSPCertStatus.GOOD
