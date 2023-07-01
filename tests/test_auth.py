"""Test the supported authentication methods"""
import logging

import pytest
from async_asgi_testclient import TestClient


LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_jwt_jwt(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test JWT-check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/jwt")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
    assert "sub" in payload
    assert payload["sub"] == "adminsession"


@pytest.mark.asyncio
async def test_mtls_jwt(mtls_client: TestClient) -> None:
    """Test JWT-check endpoint with mTLS authenticated client"""
    client = mtls_client
    resp = await client.get("/api/v1/check-auth/jwt")
    LOGGER.debug("resp={}".format(resp))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mtls_mtls(mtls_client: TestClient) -> None:
    """Test mTLS-check endpoint with mTLS authenticated client"""
    client = mtls_client
    resp = await client.get("/api/v1/check-auth/mtls")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
    assert "CN" in payload
    assert payload["CN"]
    assert "O" in payload
    assert payload["O"] == "N/A"


@pytest.mark.asyncio
async def test_jwt_mtls(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test mTLS-check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/mtls")
    LOGGER.debug("resp={}".format(resp))
    assert resp.status_code == 403
