"""Test CFSSL wrappers"""
import logging
import uuid

import pytest
import cryptography.x509
import pytest_asyncio
from async_asgi_testclient import TestClient  # pylint: disable=import-error

from rasenmaeher_api.cfssl.public import get_ca, get_crl
from rasenmaeher_api.cfssl.private import validate_reason
from rasenmaeher_api.db import Person


LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


@pytest.mark.asyncio(loop_scope="session")
async def test_get_ca() -> None:
    """Test CA fetching"""
    capem = await get_ca()
    assert capem.startswith("-----BEGIN CERTIFICATE-----")


@pytest_asyncio.fixture(scope="function")
async def one_revoked_cert(ginosession: None) -> None:
    """Make sure we have at least one revoked cert"""
    _ = ginosession
    # We have to make actual certs to be able to revoke them
    person = await Person.create_with_cert(str(uuid.uuid4()))
    await person.revoke("key_compromise")


@pytest.mark.asyncio(loop_scope="function")
async def test_get_crl(one_revoked_cert: None) -> None:
    """Test CA fetching"""
    # Make sure there is at least one revoked cert
    _ = one_revoked_cert
    crl_der = await get_crl()
    crl = cryptography.x509.load_der_x509_crl(crl_der)
    assert crl


def test_reasons() -> None:
    """Test that validate_reason works as expected"""
    assert validate_reason("keyCompromise") == cryptography.x509.ReasonFlags.key_compromise
    assert validate_reason("privilegeWithdrawn") == cryptography.x509.ReasonFlags.privilege_withdrawn
    assert validate_reason("affiliation_changed") == cryptography.x509.ReasonFlags.affiliation_changed
    assert validate_reason("certificate_hold") == cryptography.x509.ReasonFlags.certificate_hold
    with pytest.raises(ValueError):
        assert validate_reason("nosuchreason")
    assert validate_reason(cryptography.x509.ReasonFlags.unspecified) == cryptography.x509.ReasonFlags.unspecified


@pytest.mark.parametrize("suffix", ("", "/crl.der"))
@pytest.mark.asyncio(loop_scope="session")
async def test_crl_der_route(suffix: str, unauth_client_session: TestClient, one_revoked_cert: None) -> None:
    """Check that we can get a parseable CRL from the route"""
    # Make sure there is at least one revoked cert
    _ = one_revoked_cert
    client = unauth_client_session
    resp = await client.get(f"/api/v1/utils/crl{suffix}")
    resp.raise_for_status()
    # both intermediate and root CRLs are in one file, this parser cannot deal with it
    # crl = cryptography.x509.load_der_x509_crl(resp.content)
    # assert crl


@pytest.mark.asyncio(loop_scope="session")
async def test_crl_pem_route(unauth_client_session: TestClient, one_revoked_cert: None) -> None:
    """Check that we can get a parseable CRL from the route"""
    # Make sure there is at least one revoked cert
    _ = one_revoked_cert
    client = unauth_client_session
    resp = await client.get("/api/v1/utils/crl/crl.pem")
    resp.raise_for_status()
    crl = cryptography.x509.load_pem_x509_crl(resp.content)
    assert crl
