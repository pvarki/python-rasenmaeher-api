"""Test enrollment endpoint"""
import string
import random
import logging
from typing import Dict, Any
import pytest

# from libadvian.binpackers import uuid_to_b64, b64_to_uuid
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)

#
#   Check the predefined test users from settings.py
#


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_success_work_id(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "state": "testing",
        "work_id": "koira",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    # print("###########")
    # print(resp)
    # print(resp.json())
    # print("###########")
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_success_work_idhash(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "state": "testing",
        "enroll_str": "koira123",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_both_missing(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. Both work_id and enroll_str are undefined. At least one is required",
    """
    json_dict: Dict[Any, Any] = {
        "state": "testing",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Both work_id and enroll_str are undefined. At least one is required"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_no_rights(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. 'permit_str' doesn't have rights to set 'state'",
    """
    json_dict: Dict[Any, Any] = {"state": "testing", "work_id": "koira", "permit_str": "no_rights"}
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. 'permit_str' doesn't have rights to set 'state'"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_oopsie_permitstr(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. Undefined backend error q_ssfm4"
    """
    json_dict: Dict[Any, Any] = {"state": "testing", "work_id": "koira", "permit_str": "opsie'%3Boopsie"}
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssfm4"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_oopsie_state(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. Undefined backend error q_ssues1",
    """
    json_dict: Dict[Any, Any] = {
        "state": "opsie'%3Boopsie",
        "work_id": "koira",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssues1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_success_work_id(app_client: TestClient) -> None:
    """
    /config/set-dl-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "download_link": "https://kuvaton.com",
        "work_id": "kissa",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_success_work_idhash(app_client: TestClient) -> None:
    """
    /config/set-dl-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "download_link": "https://kuvaton.com",
        "enroll_str": "kissa123",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_missing(app_client: TestClient) -> None:
    """
    /config/set-dl-link
    Result should fail
    reason="Error. Both work_id and enroll_str are undefined. At least one is required"
    """
    json_dict: Dict[Any, Any] = {
        "download_link": "https://kuvaton.com",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Both work_id and enroll_str are undefined. At least one is required"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_permit_oopsie(app_client: TestClient) -> None:
    """
    /config/set-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssfm3"
    """
    json_dict: Dict[Any, Any] = {
        "download_link": "https://kuvaton.com",
        "work_id": "kissa",
        "permit_str": "opsie'%3Boopsie",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssfm3"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_no_righs(app_client: TestClient) -> None:
    """
    /config/set-dl-link
    Result should fail
    reason="Error. 'permit_str' doesn't have rights to set 'download_link'", <-- non existing permit_str
    """
    json_dict: Dict[Any, Any] = {"download_link": "https://kuvaton.com", "work_id": "kissa", "permit_str": "no_righs"}
    resp = await app_client.post("/api/v1/enrollment/config/set-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. 'permit_str' doesn't have rights to set 'download_link'"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_oopsie_link(app_client: TestClient) -> None:
    """
    /config/set-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssuedl1"
    """
    json_dict: Dict[Any, Any] = {
        "download_link": "opsie'%3Boopsie",
        "work_id": "kissa",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssuedl1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_add_mgr(app_client: TestClient) -> None:
    """
    /config/add-manager
    Enrollment accept should be successful
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_permit_hash": "beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_short(app_client: TestClient) -> None:
    """
    /config/add-manager
    Enrollment should fail
    reason="Error. new_permit_hash too short. Needs to be 64 or more.",
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_permit_hash": "too_short",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. new_permit_hash too short. Needs to be 64 or more."


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_bad_permit(app_client: TestClient) -> None:
    """
    /config/add-manager
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfm2"
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_permit_hash": "toobeni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni_short",
        "permit_str": "opsie'%3Boopsie",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssfm2"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_no_rights(app_client: TestClient) -> None:
    """
    /config/add-manager
    Enrollment should fail
    reason="Error. 'permit_str' doesn't have rights add 'new_permit_hash'",  <-- non existing permit_str
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_permit_hash": "beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni",
        "permit_str": "no_rights",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. 'permit_str' doesn't have rights add 'new_permit_hash'"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_bad_perm_str(app_client: TestClient) -> None:
    """
    /config/add-manager
    Enrollment should fail
    reason="Error. Undefined backend error q_ssiim1", <-- permissions_str sql inject
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "opsie'%3Boopsie",
        "new_permit_hash": "beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssiim1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept(app_client: TestClient) -> None:
    """
    /accept
    Enrollment accept should be successful
    """
    json_dict: Dict[Any, Any] = {
        "enroll_str": "kissa123",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True
    assert resp_dict["enroll_str"] == "kissa123"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_oopsie_permitstr(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfm1"
    """
    json_dict: Dict[Any, Any] = {"enroll_str": "kissa123", "permit_str": "oopsie'%3Boopsie"}
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssfm1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_wrong_permit(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. 'permit_str' doesn't have rights to accept given 'enroll_str'"
    """
    json_dict: Dict[Any, Any] = {"enroll_str": "kissa123", "permit_str": "wrongenroll"}
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. 'permit_str' doesn't have rights to accept given 'enroll_str'"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_oopsie_enroll(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfewh1", <-- sql inject enroll_str
    """
    json_dict: Dict[Any, Any] = {
        "enroll_str": "oopsie'%3Boopsie",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_ssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_wrong_enroll(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. 'enroll_str' not found from database.",<-- wrong enroll str
    """
    json_dict: Dict[Any, Any] = {
        "enroll_str": "not_foound",
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. 'enroll_str' not found from database."


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_kissa(app_client: TestClient) -> None:
    """
    /deliver/{enroll_str}
    Result should be success
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/kissa123")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["download_url"] != ""
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error(app_client: TestClient) -> None:
    """
    /deliver/{enroll_str}
    Result should fail
    reason="Error. Undefined backend error q_sssfewh1"
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/oopsie'%3Boopsie")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["download_url"] == ""
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error q_sssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error_not_found(app_client: TestClient) -> None:
    """
    /deliver/{enroll_str}
    Result should fail
    reason="Error. 'enroll_str' not found from database."
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/notfoundhash")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["download_url"] == ""
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. 'enroll_str' not found from database."


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error_not_finished(app_client: TestClient) -> None:
    """
    /deliver/{enroll_str}
    Result should fail
    reason="Enrollment is still in progress or it hasn't been accepted."
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/koira123")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["download_url"] == ""
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Enrollment is still in progress or it hasn't been accepted."


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status_kissa(app_client: TestClient) -> None:
    """
    Enrollment status should be 200 !str(none)
    """
    resp = await app_client.get("/api/v1/enrollment/status/kissa")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["status"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status_nope(app_client: TestClient) -> None:
    """
    Enrollment status should be 200 str('none')
    """
    resp = await app_client.get("/api/v1/enrollment/status/notexisting")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["status"] == "none"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status_error(app_client: TestClient) -> None:
    """
    Enrollment status should be 200 str('none')
    """
    resp = await app_client.get("/api/v1/enrollment/status/oopsie'%3Boopsie")
    resp_dict: Dict[Any, Any] = resp.json()
    print("#test_get_enrollment_status#")
    print(resp)
    print(resp.json())
    print("###########")
    assert resp.status_code == 200
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. Undefined backend error sssfe2"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init_missing_values(app_client: TestClient) -> None:
    """Enrollment init should return code 422 for missing json values"""
    json_dict: Dict[Any, Any] = {"missing": "json", "params": None}
    resp = await app_client.post("/api/v1/enrollment/init", json=json_dict)
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
    assert resp_dict["success"] is False
    assert resp_dict["reason"] == "Error. work_id has already active enrollment"
    assert resp.status_code == 200
