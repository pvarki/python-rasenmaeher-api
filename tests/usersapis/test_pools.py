"""Test EnrollmentPool ops"""
from typing import List, AsyncGenerator
import logging

import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient  # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


@pytest_asyncio.fixture
async def five_pools(admin_mtls_client: TestClient) -> AsyncGenerator[List[str], None]:
    """Check lists"""
    client = admin_mtls_client
    codes: List[str] = []
    for _ in range(5):
        url = "/api/v1/enrollment/invitecode/create"
        resp = await client.post(url)
        resp.raise_for_status()
        payload = resp.json()
        codes.append(payload["invite_code"])
    yield codes


@pytest.mark.asyncio(scope="session")
async def test_list_pools(admin_mtls_client: TestClient, five_pools: List[str]) -> None:
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
    assert len(payload["pools"]) >= 5
    codes = [pool["invitecode"] for pool in payload["pools"]]
    LOGGER.debug(codes)
    for expect_code in five_pools:
        assert expect_code in codes
    assert payload["pools"][0]["owner_cs"]


@pytest.mark.asyncio(scope="session")
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


@pytest.mark.asyncio(scope="session")
async def test_list_pools_wrong_owner(admin_mtls_client: TestClient) -> None:
    """Check nonexistent owner"""
    client = admin_mtls_client
    url = "/api/v1/enrollment/pools?owner_cs=NoSuchAdmin"
    resp = await client.get(url)
    LOGGER.debug(resp)
    assert resp.status_code == 404
