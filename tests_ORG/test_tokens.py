"""Test the token endpoints"""
from typing import cast
import logging

import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error
from requests.exceptions import HTTPError
from multikeyjwt import Verifier

LOGGER = logging.getLogger(__name__)


async def get_code(client: TestClient) -> str:
    """Get a code"""
    resp = await client.post("/api/v1/token/code/generate", json={"claims": {"anon_admin_session": True}})
    LOGGER.debug("resp={}".format(resp))
    resp.raise_for_status()
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert "code" in payload
    return cast(str, payload["code"])


@pytest.mark.asyncio(scope="session")
async def test_get_code(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test that we can get a new code"""
    code = await get_code(tilauspalvelu_jwt_client)
    assert len(code) > 10


@pytest.mark.asyncio(scope="session")
async def test_get_code_422(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test that we get error if trying to give wrong input"""
    client = tilauspalvelu_jwt_client
    resp = await client.post(
        "/api/v1/token/code/generate", json={"claims": {"anon_admin_session": True}, "nosuchfield": "trollollooo"}
    )
    LOGGER.debug("resp={}".format(resp))
    assert resp.status_code == 422
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))


async def use_code(client: TestClient, code: str) -> str:
    """Use the code"""
    # This always fails for now
    resp2 = await client.post("/api/v1/token/code/exchange", json={"code": code})
    LOGGER.debug("resp2={}".format(resp2))
    resp2.raise_for_status()
    payload2 = resp2.json()
    LOGGER.debug("payload2={}".format(payload2))
    assert "jwt" in payload2
    return cast(str, payload2["jwt"])


@pytest.mark.asyncio(scope="session")
async def test_use_code(tilauspalvelu_jwt_client: TestClient, unauth_client: TestClient) -> None:
    """Test that we can get a new code and use one with fresh session"""
    code = await get_code(tilauspalvelu_jwt_client)
    token = await use_code(unauth_client, code)
    assert token


@pytest.mark.asyncio(scope="session")
async def test_use_code_twice(tilauspalvelu_jwt_client: TestClient, unauth_client: TestClient) -> None:
    """Test that we can get a new code and re-using it fails"""
    code = await get_code(tilauspalvelu_jwt_client)
    token = await use_code(unauth_client, code)
    assert token

    # TODO: How to check it's 403 specifically
    with pytest.raises(HTTPError):
        await use_code(unauth_client, code)


@pytest.mark.asyncio(scope="session")
async def test_refresh_jwt(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test that the refresh endpoint works"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/token/jwt/refresh")
    LOGGER.debug("resp={}".format(resp))
    resp.raise_for_status()
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert "jwt" in payload
    assert payload["jwt"]
    claims = Verifier.singleton().decode(payload["jwt"])
    LOGGER.debug("claims={}".format(claims))
    assert claims
    # TODO: check issue time is recent
    # Check some claims we know should have been copied
    assert "anon_admin_session" in claims
    assert claims["anon_admin_session"]
