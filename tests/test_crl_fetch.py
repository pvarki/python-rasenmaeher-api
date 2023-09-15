"""Test the CRL fetching via Nginx and API container"""
from typing import Tuple
import logging

import requests
import aiohttp
import pytest

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_localmaeher_fetch_crl(
    session_with_testcas: aiohttp.ClientSession, localmaeher_api: Tuple[str, str, float]
) -> None:
    """Test that we can get CRL via https api dns name"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/utils/crl"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=localmaeher_api[2])
    response.raise_for_status()
    assert response.status == 200


@pytest.mark.asyncio
async def test_localmaeher_fetch_crl_sslfail(
    localmaeher_api: Tuple[str, str, float]
) -> None:
    """Make sure the tls check fails when CA certs are not loaded in"""
    async with aiohttp.ClientSession() as client:
        url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/utils/crl"
        LOGGER.debug("Fetching {}".format(url))
        with pytest.raises(aiohttp.ClientConnectorCertificateError):
            response = await client.get(url, timeout=localmaeher_api[2])
            response.raise_for_status()


def test_localhost_fetch_crl(localhost_api: Tuple[str, str, float]) -> None:
    """Test that we can get CRL via the direct localhost access to rasenmaeher"""
    url = f"{localhost_api[0]}/{localhost_api[1]}/utils/crl"
    response = requests.get(
        url, json=None, headers=None, verify=False, timeout=localhost_api[2]
    )
    assert response.status_code == 200
