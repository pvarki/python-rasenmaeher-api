"""Testthe fixtures"""
import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error


@pytest.mark.asyncio(scope="session")
async def test_check_auth_admin(admin_mtls_client: TestClient) -> None:
    """Test admin fixture"""
    client = admin_mtls_client
    url = "/api/v1/check-auth/validuser/admin"
    resp = await client.get(url)
    payload = resp.json()
    assert payload["type"] == "mtls"


@pytest.mark.asyncio(scope="session")
async def test_check_auth_user(user_mtls_client: TestClient) -> None:
    """Test user fixture"""
    client = user_mtls_client
    url = "/api/v1/check-auth/validuser"
    resp = await client.get(url)
    payload = resp.json()
    assert payload["type"] == "mtls"
