"""Test CFSSL wrappers"""
import logging

import pytest

from rasenmaeher_api.cfssl.public import get_ca, get_crl

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_ca() -> None:
    """Test CA fetching"""
    capem = await get_ca()
    assert capem.startswith("-----BEGIN CERTIFICATE-----")


@pytest.mark.asyncio
async def test_get_crl() -> None:
    """Test CA fetching"""
    crl = await get_crl()
    LOGGER.debug("crl={}".format(crl))
    assert crl.startswith("MII")  # PEM header
