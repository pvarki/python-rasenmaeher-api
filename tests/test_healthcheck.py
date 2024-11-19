"""Test healthcheck endpoint"""
import logging
from typing import Dict, Any
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error

from rasenmaeher_api import __version__
from rasenmaeher_api.web.api.healthcheck.schema import AllProductsHealthCheckResponse

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_healthcheck(unauth_client_session: TestClient) -> None:
    """
    /healthcheck
    healthcheck should be success
    """
    resp = await unauth_client_session.get("/api/v1/healthcheck")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["healthcheck"] == "success"
    assert resp_dict["dns"] != ""
    assert resp_dict["version"] == __version__


@pytest.mark.asyncio(loop_scope="session")
async def test_get_healthcheck_services(unauth_client_session: TestClient) -> None:
    """
    /healthcheck/services
    Result should be 200
    There fakeproduct should be ok, nonexistentproduct should not...
    """
    resp = await unauth_client_session.get("/api/v1/healthcheck/services")
    assert resp.status_code == 200
    payload = resp.json()
    parsed = AllProductsHealthCheckResponse.parse_obj(payload)
    LOGGER.debug("parsed={}".format(parsed))
    assert parsed.all_ok is False
    assert parsed.products["fake"] is True
    assert parsed.products["nonexistent"] is False
