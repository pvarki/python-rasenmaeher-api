"""Testthe fixtures"""
import logging
import base64

import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio(scope="session")
async def test_admin_fragment(admin_mtls_client: TestClient) -> None:
    """Test admin fragment"""
    client = admin_mtls_client
    url = "/api/v1/instructions/admin"
    resp = await client.get(url)
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload
    assert "fragments" in payload
    assert "fake" in payload["fragments"]
    assert payload["fragments"]["fake"]
    fpl = payload["fragments"]["fake"]
    assert "html" in fpl
    assert fpl["html"]
    assert fpl["html"] == "<p>Hello admin!</p>"


@pytest.mark.asyncio(scope="session")
async def test_user_fragment(user_mtls_client: TestClient) -> None:
    """Test user framgent"""
    client = user_mtls_client
    url = "/api/v1/instructions/user"
    resp = await client.get(url)
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload
    assert "files" in payload
    assert "fake" in payload["files"]
    assert payload["files"]["fake"]
    fake = payload["files"]["fake"]
    for fpl in fake:
        assert fpl["title"]
        assert fpl["filename"]
        assert fpl["data"]
        data = str(fpl["data"])
        assert data.startswith("data:")
        _, b64data = data.split(",")
        dec = base64.b64decode(b64data)
        assert dec
