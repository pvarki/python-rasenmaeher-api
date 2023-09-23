"""Package level tests"""
from typing import Any, Dict

import pytest
from async_asgi_testclient import TestClient


from rasenmaeher_api import __version__


def test_version() -> None:
    """Make sure version matches expected"""
    assert __version__ == "0.6.0"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_openapi_json(app_client: TestClient) -> None:
    """Check that we can get the openapi spec"""
    resp = await app_client.get("/api/openapi.json")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert len(resp_dict) > 0
