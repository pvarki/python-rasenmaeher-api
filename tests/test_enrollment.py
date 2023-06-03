"""Test enrolmment endpoint"""
import string
import random
import logging
from typing import Dict, Any
import pytest

# from libadvian.binpackers import uuid_to_b64, b64_to_uuid
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status(app_client: TestClient) -> None:
    """Enrollment status should be str(none)"""
    resp = await app_client.get("/api/v1/enrollment/status/kissa")
    print("#test_get_enrollment_status#")
    print(resp)
    print(resp.json())
    print("###########")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init_missing_values(app_client: TestClient) -> None:
    """Enrollment init should return code 422 for missing json values"""
    json_dict: Dict[Any, Any] = {"missing": "json", "params": None}
    resp = await app_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print("#test_post_enrollment_init_missing_values#")
    print(resp)
    print(resp_dict)
    print("###########")
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init(app_client: TestClient) -> None:
    """Enrollment init should return code 200 and {'success':True}"""
    _enrollment_id: str = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(64)
        ]
    )
    json_dict: Dict[Any, Any] = {"work_id": _enrollment_id}
    resp = await app_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print("#test_post_enrollment_init#")
    print(resp)
    print(resp_dict)
    print("###########")
    assert resp.status_code == 200
    assert resp_dict["success"] is True
    assert resp_dict["enroll_str"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init_already_enrolled(app_client: TestClient) -> None:
    """Enrollment init should return code 200 and {'success':False}"""
    json_dict: Dict[Any, Any] = {"work_id": "kissa"}
    resp = await app_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print("#test_post_enrollment_init_already_enrolled#")
    print(resp)
    print(resp_dict)
    print("###########")
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. work_id has already active enrollment"
    assert resp.status_code == 200
