"""Test firstuser endpoint"""
import logging
from typing import Dict, Any
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error
from rasenmaeher_api.settings import settings


LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_firstuser(app_client: TestClient) -> None:
    """
    /firstuser/is-active
    Result should be success
    """

    resp = await app_client.get("/api/v1/firstuser/is-active")
    resp_dict: Dict[Any, Any] = resp.json()

    if resp_dict["api_is_active"] is False:
        json_dict: Dict[Any, Any] = {"permit_str": settings.sqlite_init_management_hash}
        resp = await app_client.post("/api/v1/firstuser/enable", json=json_dict)

    resp = await app_client.get("/api/v1/firstuser/is-active")

    assert resp.status_code == 200
    assert resp_dict["success"] is True
    assert resp_dict["api_is_active"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_check_code(app_client: TestClient) -> None:
    """
    /firstuser/check-code
    Result should be success
    """
    resp = await app_client.get(f"/api/v1/firstuser/check-code?temp_admin_code={settings.sqlite_first_time_user_hash}")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_add_admin(app_client: TestClient) -> None:
    """
    /firstuser/add-admin
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {"temp_admin_code": settings.sqlite_first_time_user_hash, "work_id": "testikoira123"}
    resp = await app_client.post("/api/v1/firstuser/add-admin", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_list_admin(app_client: TestClient) -> None:
    """
    /firstuser/list-admin
    Result should be success
    """
    resp = await app_client.get(f"/api/v1/firstuser/list-admin?temp_admin_code={settings.sqlite_first_time_user_hash}")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict["reason"])
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_delete_admin(app_client: TestClient) -> None:
    """
    /firstuser/delete-admin
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {"temp_admin_code": settings.sqlite_first_time_user_hash, "work_id": "testikoira123"}
    resp = await app_client.post("/api/v1/firstuser/delete-admin", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict["reason"])
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_add_disable(app_client: TestClient) -> None:
    """
    /firstuser/disable
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {"permit_str": settings.sqlite_init_management_hash}
    resp = await app_client.post("/api/v1/firstuser/disable", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_add_enable(app_client: TestClient) -> None:
    """
    /firstuser/enable
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {"permit_str": settings.sqlite_init_management_hash}
    resp = await app_client.post("/api/v1/firstuser/enable", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True
