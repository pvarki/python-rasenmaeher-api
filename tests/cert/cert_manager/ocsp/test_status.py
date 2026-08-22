"""Test the serial -> certificate status resolution against the DB."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography import x509
from cryptography.x509 import ocsp

from rasenmaeher_api.cert.cert_manager.ocsp.status import lookup_status
from rasenmaeher_api.db import EngineWrapper
from rasenmaeher_api.db.issuedcerts import IssuedCert
from rasenmaeher_api.rmsettings import RMSettings, switchme_to_singleton_call

from .helpers import LeafFactory, RequestFactory, Responder, SigningCA, add_issued, add_person

LOGGER = logging.getLogger(__name__)

VALID_PRODUCT_CN = "fake.localmaeher.dev.pvarki.fi"  # from the test kraftwerk manifest


@pytest.mark.asyncio(loop_scope="session")
async def test_product_cert_valid_cn(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
) -> None:
    """Recorded product certs with manifest CNs (and rmapi's own CN) -> GOOD"""
    _ = dbinit_func, installed_signer
    for common_name in (VALID_PRODUCT_CN, switchme_to_singleton_call.mtls_client_cert_cn):
        leaf = make_leaf(common_name)
        add_issued(leaf.serial_number, common_name)
        resp = await respond(make_request(leaf))
        assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
        assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD


@pytest.mark.asyncio(loop_scope="session")
async def test_issued_cert_active_user_cn(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
    nice_tmpdir: str,
) -> None:
    """Per-user cert signed via product path (e.g. TAK) with an active owner -> GOOD"""
    _ = dbinit_func, installed_signer
    callsign = f"atakuser_{uuid.uuid4()}"
    add_person(tmp=nice_tmpdir, callsign=callsign)  # active owner, different (main) cert serial
    leaf = make_leaf(callsign)
    add_issued(leaf.serial_number, callsign)  # TAK's separate per-user cert
    resp = await respond(make_request(leaf))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD


@pytest.mark.asyncio(loop_scope="session")
async def test_issued_cert_revoked_user_cn(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
    nice_tmpdir: str,
) -> None:
    """Per-user cert signed via product path whose owner is revoked -> REVOKED with owner's reason"""
    _ = dbinit_func, installed_signer
    callsign = f"atakuser_{uuid.uuid4()}"
    add_person(tmp=nice_tmpdir, callsign=callsign, deleted=datetime.now(UTC), revoke_reason="privilege_withdrawn")
    leaf = make_leaf(callsign)
    add_issued(leaf.serial_number, callsign)
    resp = await respond(make_request(leaf))
    assert resp.certificate_status == ocsp.OCSPCertStatus.REVOKED
    assert resp.revocation_reason == x509.ReasonFlags.privilege_withdrawn


@pytest.mark.asyncio(loop_scope="session")
async def test_issued_cert_no_owner_cn(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
) -> None:
    """Recorded cert whose CN matches no Person and no product -> GOOD (we issued it)"""
    _ = dbinit_func, installed_signer
    leaf = make_leaf("orphan.example.invalid")
    add_issued(leaf.serial_number, "orphan.example.invalid")
    resp = await respond(make_request(leaf))
    assert resp.certificate_status == ocsp.OCSPCertStatus.GOOD


@pytest.mark.asyncio(loop_scope="session")
async def test_unknown_serial(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    respond: Responder,
    dbinit_func,
) -> None:
    """Serial in neither table -> UNKNOWN"""
    _ = dbinit_func, installed_signer
    leaf = make_leaf("NEVERRECORDED")
    resp = await respond(make_request(leaf))
    assert resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert resp.certificate_status == ocsp.OCSPCertStatus.UNKNOWN


@pytest.mark.asyncio(loop_scope="session")
async def test_product_cn_lookup_failure_falls_back(monkeypatch: pytest.MonkeyPatch, dbinit_func) -> None:
    """A broken manifest lookup degrades to an empty product list instead of raising.

    valid_product_cns reads the kraftwerk manifest, which is absent in some deployments.
    Without the fallback every OCSP query for a recorded cert would become an internal error.
    """
    _ = dbinit_func
    serial = x509.random_serial_number()
    with EngineWrapper.get_session() as session:
        session.add(IssuedCert(serial=str(serial), cn="orphan.example.invalid"))
        session.commit()

    def _boom(_self: Any) -> list[str]:
        raise RuntimeError("no manifest here")

    monkeypatch.setattr(RMSettings, "valid_product_cns", property(_boom))

    result = await lookup_status(serial)

    # The cert is ours and has no revoked owner, so it stays GOOD despite the failed lookup
    assert result.status == ocsp.OCSPCertStatus.GOOD
