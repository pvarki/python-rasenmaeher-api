"""Test the OCSP responder core: DER request in, DER response out."""

import logging
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509 import ocsp

from rasenmaeher_api.cert.cert_manager.ocsp import responder

from .helpers import LeafFactory, RequestFactory, Responder, SigningCA, add_person

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio(loop_scope="session")
async def test_garbage_is_malformed(installed_signer: SigningCA, respond: Responder) -> None:
    """Unparseable bytes get an OCSP-level malformed response"""
    _ = installed_signer
    resp = await respond(b"this is not an ocsp request")
    assert resp.response_status == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="session")
async def test_foreign_ca_is_unauthorized(
    installed_signer: SigningCA, make_leaf: LeafFactory, make_request: RequestFactory, respond: Responder
) -> None:
    """Requests about certs from another CA are not our business"""
    _ = installed_signer
    leaf = make_leaf("EVIL", foreign=True)
    resp = await respond(make_request(leaf, foreign=True))
    assert resp.response_status == ocsp.OCSPResponseStatus.UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_unsupported_hash_is_unauthorized(
    installed_signer: SigningCA, make_leaf: LeafFactory, make_request: RequestFactory, respond: Responder
) -> None:
    """CertID hash algorithms outside sha1/sha256 are rejected"""
    _ = installed_signer
    leaf = make_leaf("LEAF1")
    resp = await respond(make_request(leaf, algorithm=hashes.SHA384()))
    assert resp.response_status == ocsp.OCSPResponseStatus.UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_good_user(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
    nice_tmpdir: str,
) -> None:
    """Active user -> GOOD, signature verifies, both hash algos work"""
    _ = dbinit_func
    leaf = make_leaf("GOODUSER")
    add_person(leaf.serial_number, tmp=nice_tmpdir)
    for algo in (hashes.SHA1(), hashes.SHA256()):
        resp = await respond(make_request(leaf, algorithm=algo))
        assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
        assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD
        assert resp.serial_number == leaf.serial_number
        pubkey = installed_signer.cert.public_key()
        assert isinstance(pubkey, ec.EllipticCurvePublicKey)
        pubkey.verify(resp.signature, resp.tbs_response_bytes, ec.ECDSA(hashes.SHA256()))


@pytest.mark.asyncio(loop_scope="session")
async def test_revoked_user(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
    nice_tmpdir: str,
) -> None:
    """Deleted user -> REVOKED with reason and time"""
    _ = dbinit_func, installed_signer
    leaf = make_leaf("REVOKEDUSER")
    deleted = datetime.now(UTC)
    add_person(leaf.serial_number, deleted=deleted, revoke_reason="key_compromise", tmp=nice_tmpdir)
    resp = await respond(make_request(leaf))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert resp.certificate_status == ocsp.OCSPCertStatus.REVOKED
    assert resp.revocation_reason == x509.ReasonFlags.key_compromise
    assert resp.revocation_time_utc is not None
    assert abs((resp.revocation_time_utc - deleted).total_seconds()) < 2.0


@pytest.mark.asyncio(loop_scope="session")
async def test_nonce_echo(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
) -> None:
    """Nonce comes back byte-for-byte; oversize nonce is malformed"""
    _ = dbinit_func, installed_signer
    leaf = make_leaf("NONCELEAF")
    nonce = os.urandom(16)
    resp = await respond(make_request(leaf, nonce=nonce))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    echoed = resp.extensions.get_extension_for_class(x509.OCSPNonce).value.nonce
    assert echoed == nonce

    resp = await respond(make_request(leaf, nonce=os.urandom(33)))
    assert resp.response_status == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="function")
async def test_lookup_failure_becomes_internal_error(
    monkeypatch: pytest.MonkeyPatch, installed_signer: SigningCA, ocsp_request_der: bytes
) -> None:
    """A DB failure mid-lookup returns an OCSP internal error, it does not escape as a 500.

    The route has no exception handler of its own, so this catch-all is the only thing
    keeping a database blip from turning every OCSP query into an HTTP error.
    """
    _ = installed_signer
    monkeypatch.setattr(responder, "lookup_status", AsyncMock(side_effect=RuntimeError("db is down")))

    der, meta = await responder.build_ocsp_response(ocsp_request_der)

    assert meta.success is False
    assert ocsp.load_der_ocsp_response(der).response_status == ocsp.OCSPResponseStatus.INTERNAL_ERROR
