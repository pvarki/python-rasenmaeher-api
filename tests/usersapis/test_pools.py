"""Test EnrollmentPool ops"""
import logging

import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_list_pools(admin_mtls_client: TestClient) -> None:
    """Check lists"""
    client = admin_mtls_client
    url = "/api/v1/enrollment/pools"
    resp = await client.get(url)
    LOGGER.debug(resp)
    resp.raise_for_status()
    payload = resp.json()
    LOGGER.debug(payload)
    assert "pools" in payload
    assert payload["pools"]
    assert payload["pools"][0]["owner_cs"]


@pytest.mark.asyncio
async def test_list_pools_by_owner(admin_mtls_client: TestClient) -> None:
    """Check list by owner"""
    client = admin_mtls_client
    url = "/api/v1/enrollment/pools?owner_cs=FIRSTADMINa"
    resp = await client.get(url)
    LOGGER.debug(resp)
    resp.raise_for_status()
    payload = resp.json()
    LOGGER.debug(payload)
    assert "pools" in payload
    assert payload["pools"]
    owners = {pool["owner_cs"] for pool in payload["pools"]}
    assert owners == {"FIRSTADMINa"}


@pytest.mark.asyncio
async def test_list_pools_wrong_owner(admin_mtls_client: TestClient) -> None:
    """Check nonexistent owner"""
    client = admin_mtls_client
    url = "/api/v1/enrollment/pools?owner_cs=NoSuchAdmin"
    resp = await client.get(url)
    LOGGER.debug(resp)
    assert resp.status_code == 404
