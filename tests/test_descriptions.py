"""Test the descriptions endpoint"""
import logging

import pytest
from async_asgi_testclient import TestClient

LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio
async def test_description_list(unauth_client: TestClient, lang: str) -> None:
    """Make sure we have seen at least one announce call"""
    resp = await unauth_client.get(f"/api/v1/descriptions/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload[0]["shortname"]
