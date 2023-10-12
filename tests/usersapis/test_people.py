"""Test people endpoint"""
import logging
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_admin_people_list(admin_mtls_client: TestClient) -> None:
    """Test people list fragment"""
    client = admin_mtls_client
    url = "/api/v1/people/list"
    resp = await client.get(url)
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_product_people_list(product_mtls_client: TestClient) -> None:
    """Test people list fragment"""
    client = product_mtls_client
    url = "/api/v1/people/list"
    resp = await client.get(url)
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
