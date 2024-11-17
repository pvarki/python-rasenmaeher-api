"""Test the supported authentication methods"""
import uuid
from typing import Tuple, Dict, Any, cast
import logging

import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient
from multikeyjwt import Issuer

from rasenmaeher_api.db import Person

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


@pytest_asyncio.fixture(scope="session")
async def two_users(ginosession: None) -> Tuple[Person, Person]:
    """First one is normal, second is admin"""
    _ = ginosession
    normal = await Person.create_with_cert("TestNormalUser")
    admin = await Person.create_with_cert("TestAdminUser")
    await admin.assign_role("admin")
    return normal, admin


def check_response(resp: Any, expect_type: str) -> Dict[str, Any]:
    """Check the response"""
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
    assert "type" in payload
    assert payload["type"] == expect_type
    assert "userid" in payload
    assert "payload" in payload
    return cast(Dict[str, Any], payload)


@pytest.mark.asyncio(loop_scope="session")
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


@pytest.mark.asyncio(loop_scope="session")
async def test_mtls_jwt(mtls_client: TestClient) -> None:
    """Test JWT-check endpoint with mTLS authenticated client"""
    client = mtls_client
    resp = await client.get("/api/v1/check-auth/jwt")
    LOGGER.debug("resp={}".format(resp))
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
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


@pytest.mark.asyncio(loop_scope="session")
async def test_jwt_mtls(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test mTLS-check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/mtls")
    LOGGER.debug("resp={}".format(resp))
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_jwt_both_permissive(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test JWT-or-mTLS -check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/mtls_or_jwt/permissive")
    payload = check_response(resp, "jwt")
    subload = payload["payload"]
    assert payload["userid"] == subload["sub"]


@pytest.mark.asyncio(loop_scope="session")
async def test_jwt_both_notp(tilauspalvelu_jwt_client: TestClient) -> None:
    """Test JWT-or-mTLS -check endpoint with JWT authenticated client"""
    client = tilauspalvelu_jwt_client
    resp = await client.get("/api/v1/check-auth/mtls_or_jwt")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_mtls_both(mtls_client: TestClient) -> None:
    """Test JWT-or-mTLS -check endpoint with mTLS authenticated client"""
    client = mtls_client
    resp = await client.get("/api/v1/check-auth/mtls_or_jwt")
    payload = check_response(resp, "mtls")
    subload = payload["payload"]
    assert payload["userid"] == subload["CN"]


@pytest.mark.asyncio(loop_scope="session")
async def test_valid_user_mtls(unauth_client_session: TestClient, two_users: Tuple[Person, Person]) -> None:
    """Test the valid user endpoint with valid and invalid CNs"""
    client = unauth_client_session
    for user in two_users:
        client.headers.update({"X-ClientCert-DN": f"CN={user.callsign},O=N/A"})
        resp = await client.get("/api/v1/check-auth/validuser")
        payload = check_response(resp, "mtls")
        assert payload["userid"] == user.callsign
    # Invalid user should fail
    client.headers.update({"X-ClientCert-DN": f"CN={uuid.uuid4()},O=N/A"})
    resp = await client.get("/api/v1/check-auth/validuser")
    assert resp.status_code == 403


# jotain häikkää Issuer.singleton() ??
@pytest.mark.asyncio(loop_scope="session")
async def test_valid_user_jwt(unauth_client_session: TestClient, two_users: Tuple[Person, Person]) -> None:
    """Test the valid user endpoint with valid and invalid subs"""
    client = unauth_client_session
    for user in two_users:
        token = Issuer.singleton().issue({"sub": user.callsign})
        client.headers.clear()
        client.headers.update({"Authorization": f"Bearer {token}"})
        resp = await client.get("/api/v1/check-auth/validuser")
        payload = check_response(resp, "jwt")
        assert payload["userid"] == user.callsign
    # Invalid user should fail
    token = Issuer.singleton().issue({"sub": str(uuid.uuid4())})
    client.headers.update({"Authorization": f"Bearer {token}"})
    resp = await client.get("/api/v1/check-auth/validuser")
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_valid_admin_mtls(unauth_client_session: TestClient, two_users: Tuple[Person, Person]) -> None:
    """Test the valid user endpoint with admin and non-admin CNs"""
    client = unauth_client_session
    for user in two_users:
        client.headers.update({"X-ClientCert-DN": f"CN={user.callsign},O=N/A"})
        resp = await client.get("/api/v1/check-auth/validuser/admin")
        LOGGER.debug("resp={}".format(resp))
        if user.callsign == "TestNormalUser":
            assert resp.status_code == 403
            continue
        payload = check_response(resp, "mtls")
        assert payload["userid"] == user.callsign


@pytest.mark.asyncio(loop_scope="session")
async def test_valid_admin_jwt(unauth_client_session: TestClient, two_users: Tuple[Person, Person]) -> None:
    """Test the valid user endpoint with admin and non-admin subs"""
    client = unauth_client_session
    for user in two_users:
        token = Issuer.singleton().issue({"sub": user.callsign})
        client.headers.clear()
        client.headers.update({"Authorization": f"Bearer {token}"})
        resp = await client.get("/api/v1/check-auth/validuser/admin")
        LOGGER.debug("resp={}".format(resp))
        if user.callsign == "TestNormalUser":
            assert resp.status_code == 403
            continue
        payload = check_response(resp, "jwt")
        assert payload["userid"] == user.callsign
