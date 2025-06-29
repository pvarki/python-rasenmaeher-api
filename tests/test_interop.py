"""Test the interop route"""

import logging

import pytest
from async_asgi_testclient import TestClient

from rasenmaeher_api.web.api.product.schema import ProductAddRequest

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_valid_products(ginosession: None, unauth_client: TestClient) -> None:
    """Test requesting interop with product 'fake'"""
    _ = ginosession
    client = unauth_client
    client.headers.update({"X-ClientCert-DN": "CN=interoptest.localmaeher.dev.pvarki.fi,O=N/A"})
    req = ProductAddRequest(
        certcn="interoptest.localmaeher.dev.pvarki.fi",
        x509cert="-----BEGIN CERTIFICATE-----\\nMIIEwjCC...\\n-----END CERTIFICATE-----\\n",
    )
    payload = req.dict()
    resp = await client.post("/api/v1/product/interop/fake", json=payload)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_invalid_requester(ginosession: None, unauth_client: TestClient) -> None:
    """Test requesting interop with product 'fake' with product that is not valid"""
    _ = ginosession
    client = unauth_client
    client.headers.update({"X-ClientCert-DN": "CN=callsigndude,O=N/A"})
    req = ProductAddRequest(
        certcn="callsigndude",
        x509cert="-----BEGIN CERTIFICATE-----\\nMIIEwjCC...\\n-----END CERTIFICATE-----\\n",
    )
    payload = req.dict()
    resp = await client.post("/api/v1/product/interop/fake", json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invalid_tgt(ginosession: None, unauth_client: TestClient) -> None:
    """Test requesting interop with product 'nosuch'"""
    _ = ginosession
    client = unauth_client
    client.headers.update({"X-ClientCert-DN": "CN=interoptest.localmaeher.dev.pvarki.fi,O=N/A"})
    req = ProductAddRequest(
        certcn="interoptest.localmaeher.dev.pvarki.fi",
        x509cert="-----BEGIN CERTIFICATE-----\\nMIIEwjCC...\\n-----END CERTIFICATE-----\\n",
    )
    payload = req.dict()
    resp = await client.post("/api/v1/product/interop/nosuch", json=payload)
    assert resp.status_code == 404
