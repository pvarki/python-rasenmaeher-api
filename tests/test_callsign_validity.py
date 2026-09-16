"""Test the forwardAuth endpoint Traefik asks on every mTLS request."""

import datetime
import logging
import urllib.parse
from typing import Any

import pytest
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509 import ocsp
from cryptography.x509.oid import NameOID

from rasenmaeher_api.cert.cert_manager.ocsp.status import CertStatusResult
from rasenmaeher_api.web.api.internal import callsign_validity

LOGGER = logging.getLogger(__name__)

ENDPOINT = "/api/v1/internal/callsign-validity/check"
CERT_HEADER = callsign_validity.CERT_HEADER
GOOD = CertStatusResult(status=ocsp.OCSPCertStatus.GOOD)


def make_cert(common_name: str = "ALPHA01", serial: int = 0x4242) -> str:
    """A self-signed leaf; only the CN and serial matter here.

    The endpoint does not verify the issuer: Traefik has already checked the
    chain against the same trust bundle on the TLS connection.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(serial)
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def stripped(pem: str) -> str:
    """The PEM as Traefik sends it: armour removed, single line"""
    return "".join(line for line in pem.splitlines() if "-----" not in line)


def patch_status(monkeypatch: pytest.MonkeyPatch, result: Any, seen: list[int] | None = None) -> None:
    """Replace the DB lookup; lookup_status itself is covered in tests/cert"""

    async def fake_lookup(serial: int) -> Any:
        if seen is not None:
            seen.append(serial)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(callsign_validity, "lookup_status", fake_lookup)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("header", ["", "   ", "not-a-certificate", "%%%"])
async def test_no_usable_certificate(unauth_client_session: TestClient, header: str) -> None:
    """Without a parseable cert the verdict is no_cert and no callsign leaks"""
    resp = await unauth_client_session.get(ENDPOINT, headers={CERT_HEADER: header})
    assert resp.status_code == 200
    assert resp.headers["Callsign-Valid"] == "false"
    assert resp.headers["Callsign-Valid-Reason"] == "no_cert"
    assert "Callsign" not in resp.headers


@pytest.mark.asyncio(loop_scope="session")
async def test_missing_header(unauth_client_session: TestClient) -> None:
    """A request with no certificate header at all is still answered 200"""
    resp = await unauth_client_session.get(ENDPOINT)
    assert resp.status_code == 200
    assert resp.headers["Callsign-Valid-Reason"] == "no_cert"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "status,want_valid,want_reason",
    [
        (ocsp.OCSPCertStatus.GOOD, "true", "ok"),
        (ocsp.OCSPCertStatus.REVOKED, "false", "invalid"),
        (ocsp.OCSPCertStatus.UNKNOWN, "false", "invalid"),
    ],
)
async def test_verdict_mapping(
    unauth_client_session: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    status: ocsp.OCSPCertStatus,
    want_valid: str,
    want_reason: str,
) -> None:
    """Revoked and unknown both deny, and every verdict still rides a 200"""
    patch_status(monkeypatch, CertStatusResult(status=status))
    resp = await unauth_client_session.get(ENDPOINT, headers={CERT_HEADER: make_cert("ALPHA01", 0x4242)})
    assert resp.status_code == 200
    assert resp.headers["Callsign"] == "ALPHA01"
    assert resp.headers["Callsign-Valid"] == want_valid
    assert resp.headers["Callsign-Valid-Reason"] == want_reason


@pytest.mark.asyncio(loop_scope="session")
async def test_lookup_failure_is_an_error_verdict(
    unauth_client_session: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing lookup denies with reason=error rather than 500ing the request"""
    patch_status(monkeypatch, RuntimeError("database is down"))
    resp = await unauth_client_session.get(ENDPOINT, headers={CERT_HEADER: make_cert("ALPHA01", 0x4242)})
    assert resp.status_code == 200
    assert resp.headers["Callsign-Valid-Reason"] == "error"


@pytest.mark.asyncio(loop_scope="session")
async def test_lookup_keys_on_the_certificate_serial(
    unauth_client_session: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict must come from the serial, not the callsign.

    The endpoint this replaced looked the callsign up in the Person table, which
    can disagree with whether the certificate itself was revoked. Keying on the
    serial is what makes this the same answer the OCSP responder gives.
    """
    seen: list[int] = []
    patch_status(monkeypatch, GOOD, seen)
    await unauth_client_session.get(ENDPOINT, headers={CERT_HEADER: make_cert("BRAVO02", 0xDEADBEEF)})
    assert seen == [0xDEADBEEF]


@pytest.mark.asyncio(loop_scope="session")
async def test_accepts_every_header_encoding(
    unauth_client_session: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Traefik sends the cert armoured, stripped, url-encoded or chained"""
    pem = make_cert("CHARLIE03", 0x99)
    forms = {
        "armoured": pem,
        "stripped": stripped(pem),
        "url encoded": urllib.parse.quote(stripped(pem)),
        "chain": stripped(pem) + "," + stripped(make_cert("ISSUER", 0x1)),
    }
    for name, header in forms.items():
        seen: list[int] = []
        patch_status(monkeypatch, GOOD, seen)
        resp = await unauth_client_session.get(ENDPOINT, headers={CERT_HEADER: header})
        assert resp.headers["Callsign"] == "CHARLIE03", name
        assert seen == [0x99], f"{name} picked the wrong certificate from the chain"


def test_parse_leaf_takes_the_first_of_a_chain() -> None:
    """Only the leaf is the client; the rest of the chain is issuers"""
    leaf = make_cert("LEAF", 0x11)
    issuer = make_cert("ISSUER", 0x22)
    got = callsign_validity.parse_leaf(stripped(leaf) + "," + stripped(issuer))
    assert got is not None
    assert got.serial_number == 0x11
    assert callsign_validity.common_name(got) == "LEAF"
