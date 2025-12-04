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
async def test_product_instructions(user_mtls_client: TestClient, lang: str) -> None:
    """Make sure we get product instructions"""
    resp = await user_mtls_client.get(f"/api/v1/instructions/fake/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload["callsign"]


@pytest.mark.asyncio
@pytest.mark.asyncio(loop_scope="session")
async def test_proxy(user_mtls_client: TestClient) -> None:
    """Test requesting interop with product 'fake' with product that is not valid"""
    client = user_mtls_client
    resp = await client.get("/api/v1/product/proxy/fake/api/v1/healthcheck")
    assert resp.status_code == 200

@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_description_list_v2(unauth_client: TestClient, lang: str) -> None:
    """Make sure we get product descriptions"""
    resp = await unauth_client.get(f"/api/v2/descriptions/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert len(payload) > 0
    assert payload[0]["shortname"] == "fake"
    assert payload[0]["title"] == "Test fake product"
    assert payload[0]["language"] == lang
    assert "docs" in payload[0]
    assert payload[0]["docs"] == "https://example.com/docs"
    assert "component" in payload[0]
    assert payload[0]["component"]["type"] == "link"


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_product_description_v2(unauth_client: TestClient, lang: str) -> None:
    """Make sure we get product description"""
    resp = await unauth_client.get(f"/api/v2/descriptions/fake/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload["shortname"] == "fake"
    assert payload["title"] == "Test fake product"
    assert payload["language"] == lang
    assert payload["description"] == "Testing things"
    assert "docs" in payload
    assert payload["docs"] == "https://example.com/docs"
    assert "component" in payload
    assert payload["component"]["type"] == "link"
    assert payload["component"]["ref"] == "https://example.com/component"


@pytest.mark.asyncio(loop_scope="session")
async def test_product_instructions_v2(user_mtls_client: TestClient) -> None:
    """Make sure we get product instructions"""
    resp = await user_mtls_client.get("/api/v2/instructions/data/fake")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert "data" in payload
    assert "tak_zips" in payload["data"]
    assert len(payload["data"]["tak_zips"]) == 3
    assert payload["data"]["tak_zips"][0]["title"] == "atak.zip"
    assert payload["data"]["tak_zips"][0]["filename"] == "FAKE_atak.zip"
    assert "data:application/zip;base64," in payload["data"]["tak_zips"][0]["data"]


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_description_list_v2_admin(user_mtls_admin_client: TestClient, lang: str) -> None:
    """Make sure admin can get product descriptions"""
    resp = await user_mtls_admin_client.get(f"/api/v2/descriptions/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert len(payload) > 0
    assert payload[0]["shortname"] == "fake"


@pytest.mark.parametrize("lang", ["fi", "en"])
@pytest.mark.asyncio(loop_scope="session")
async def test_product_description_v2_admin(user_mtls_admin_client: TestClient, lang: str) -> None:
    """Make sure admin can get product description"""
    resp = await user_mtls_admin_client.get(f"/api/v2/descriptions/fake/{lang}")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert payload["shortname"] == "fake"


@pytest.mark.asyncio(loop_scope="session")
async def test_product_instructions_v2_admin(user_mtls_admin_client: TestClient) -> None:
    """Make sure admin can get product instructions"""
    resp = await user_mtls_admin_client.get("/api/v2/admin/instructions/data/fake")
    assert resp
    payload = resp.json()
    LOGGER.debug(payload)
    assert payload
    assert "data" in payload
    assert "tak_zips" in payload["data"]
    assert len(payload["data"]["tak_zips"]) == 3


@pytest.mark.asyncio(loop_scope="session")
async def test_product_instructions_v2_admin_unauthorized(user_mtls_client: TestClient) -> None:
    """Make sure non-admin gets 403 on admin route"""
    resp = await user_mtls_client.get("/api/v2/admin/instructions/data/fake")
    assert resp.status_code == 403
    payload = resp.json()
    LOGGER.debug(payload)
    assert "detail" in payload

