"""Test CFSSL wrappers"""
import logging

import pytest
import cryptography.x509
from async_asgi_testclient import TestClient  # pylint: disable=import-error


from rasenmaeher_api.cfssl.public import get_ca, get_crl
from rasenmaeher_api.cfssl.private import validate_reason

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_ca() -> None:
    """Test CA fetching"""
    capem = await get_ca()
    assert capem.startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.asyncio
async def test_get_crl() -> None:
    """Test CA fetching"""
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


@pytest.mark.asyncio
async def test_crl_route(unauth_client: TestClient) -> None:
    """Check that we can get a parseable CRL from the route"""
    client = unauth_client
    resp = await client.get("/api/v1/utils/crl")
    resp.raise_for_status()
    crl = cryptography.x509.load_der_x509_crl(resp.content)
    assert crl
