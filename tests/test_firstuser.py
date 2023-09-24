"""Test firstuser endpoint"""
import logging
from typing import Dict, Any
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error

from rasenmaeher_api.db import LoginCode
from rasenmaeher_api.jwtinit import jwt_init

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_code_exchange_and_admin_creation(unauth_client: TestClient) -> None:
    """
    Firstuser route to test token exchange to admin user
    """
    await jwt_init()

    # Get the anon token
    code = await LoginCode.create_for_claims({"anon_admin_session": True})
    print(f"Claimed code : {code}")

    # Check the token
    resp = await unauth_client.get(f"/api/v1/firstuser/check-code?temp_admin_code={code}")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["code_ok"] is True
    assert resp.status_code == 200

    # Exchange the token
    json_dict: Dict[Any, Any] = {"code": code}
    resp = await unauth_client.post("/api/v1/token/code/exchange", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["jwt"] != ""
    tmp_jwt: str = resp_dict["jwt"]
    print(tmp_jwt)

    # Create new admin user
    unauth_client.headers.update({"Authorization": f"Bearer {tmp_jwt}"})
    json_dict = {"work_id": "nahkaesa"}
    resp = await unauth_client.post("/api/v1/firstuser/add-admin", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    # Create new admin user, the user already exits.. should not be 200
    unauth_client.headers.update({"Authorization": f"Bearer {tmp_jwt}"})
    json_dict = {"work_id": "nahkaesa"}
    resp = await unauth_client.post("/api/v1/firstuser/add-admin", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code != 200


@pytest.mark.asyncio
async def test_code_exchange_bad_code(unauth_client: TestClient) -> None:
    """
    Firstuser route fail using incorrect code
    """
    resp = await unauth_client.get("/api/v1/firstuser/check-code?temp_admin_code=thiswontdo")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["code_ok"] is False
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_with_admin_client(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {"work_id": "some_other_admin_ukkeli"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/firstuser/add-admin", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200
