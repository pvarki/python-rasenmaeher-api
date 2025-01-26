"""Test the descriptions endpoint"""
import logging

import pytest
from async_asgi_testclient import TestClient

LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_description_list(unauth_client: TestClient, lang: str) -> None:
    """Make sure we get product descriptions"""
    resp = await unauth_client.get(f"/api/v1/descriptions/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload[0]["shortname"]


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_product_description(unauth_client: TestClient, lang: str) -> None:
    """Make sure we get product description"""
    resp = await unauth_client.get(f"/api/v1/descriptions/fake/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload["shortname"]


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_product_instructons(user_mtls_client: TestClient, lang: str) -> None:
    """Make sure we get product instructions"""
    resp = await user_mtls_client.get(f"/api/v1/instructions/fake/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload["callsign"]
