"""Test people endpoint"""
import logging
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error

from .conftest import enroll_user

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


@pytest.mark.asyncio
async def test_person_delete(admin_mtls_client: TestClient, enroll_poolcode: str) -> None:
    """Test enrolling and then deleting a person"""
    admin = admin_mtls_client
    _p12bytes = await enroll_user(enroll_poolcode, "TOBEREVOKED", admin)
    url = "/api/v1/people/TOBEREVOKED"
    resp1 = await admin.delete(url)
    LOGGER.debug("got response {} from {}".format(resp1, url))
    resp1.raise_for_status()
    payload = resp1.json()
    assert payload["success"]

    resp2 = await admin.delete(url)
    LOGGER.debug("got response {} from {}".format(resp2, url))
    assert resp2.status_code == 404

    # TODO: Make sure the person can no longer access things with their mTLS cert
