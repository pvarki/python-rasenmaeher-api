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
    assert payload["sub"] == "tpadminsession"


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


@pytest.mark.asyncio
async def test_jwt_both_permissive(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test JWT-or-mTLS -check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/mtls_or_jwt/permissive")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
    assert "type" in payload
    assert payload["type"] == "jwt"
    assert "userid" in payload
    assert "payload" in payload
    subload = payload["payload"]
    assert payload["userid"] == subload["sub"]


@pytest.mark.asyncio
async def test_jwt_both_notp(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test JWT-or-mTLS -check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/mtls_or_jwt")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mtls_both(mtls_client: TestClient) -> None:
    """Test JWT-or-mTLS -check endpoint with mTLS authenticated client"""
    client = mtls_client
    resp = await client.get("/api/v1/check-auth/mtls_or_jwt")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
    assert "type" in payload
    assert payload["type"] == "mtls"
    assert "userid" in payload
    assert "payload" in payload
    subload = payload["payload"]
    assert payload["userid"] == subload["CN"]
