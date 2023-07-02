"""Test healthcheck endpoint"""
import logging
from typing import Dict, Any
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_healthcheck(app_client: TestClient) -> None:
    """
    /healthcheck
    healthcheck should be success
    """
    resp = await app_client.get("/api/v1/healthcheck")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["healthcheck"] == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_healthcheck_delivery(app_client: TestClient) -> None:
    """
    /healthcheck/delivery
    response status should be 200,201,204
    """
    resp = await app_client.get("/api/v1/healthcheck/delivery")
    assert resp.status_code in (200, 201, 204)


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_healthcheck_services(app_client: TestClient) -> None:
    """
    /healthcheck/services
    Result should be 200
    There should be at least more than one result on dict...
    """
    resp = await app_client.get("/api/v1/healthcheck/services")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert len(resp_dict) > 0
