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
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
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
        "work_id_hash": "koira123",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
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
    reason="Error. Both work_id and work_id_hash are undefined. At least one is required",
    """
    json_dict: Dict[Any, Any] = {
        "state": "testing",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 400
    assert resp_dict["detail"] == "Error. Both work_id and work_id_hash are undefined. At least one is required"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_no_rights(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. 'management_hash' doesn't have rights to set 'state'",
    """
    json_dict: Dict[Any, Any] = {"state": "testing", "work_id": "koira", "management_hash": "no_rights"}
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 403
    assert resp_dict["detail"] == "Error. 'management_hash' doesn't have rights to set 'state'"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_oopsie_permitstr(app_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. Undefined backend error q_ssfm4"
    """
    json_dict: Dict[Any, Any] = {"state": "testing", "work_id": "koira", "management_hash": "opsie'%3Boopsie"}
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfm4"


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
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssues1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_success_work_id(app_client: TestClient) -> None:
    """
    /config/set-mtls-test-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "work_id": "kissa",
        "set_for_all": False,
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_success_all(app_client: TestClient) -> None:
    """
    /config/set-mtls-test-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "set_for_all": True,
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_fail(app_client: TestClient) -> None:
    """
    /config/set-mtls-test-link
    Result should be fail
    'Error. Both work_id and work_id_hash are undefined. At least one is required when 'set_for_all' is set to False'
    """
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "set_for_all": False,
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["success"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_fail_permissions(app_client: TestClient) -> None:
    """
    /config/set-mtls-test-link
    Result should be fail
    'Error. 'management_hash' doesn't have rights to set 'mtls_test_link''
    """
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "set_for_all": True,
        "management_hash": "Not_enough_permissions",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 403
    assert resp_dict["detail"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_fail_oopsie(app_client: TestClient) -> None:
    """
    /config/set-mtls-test-link
    Result should be fail
    'Error. Both work_id and work_id_hash are undefined. At least one is required when 'set_for_all' is set to True'
    """
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "set_for_all": True,
        "management_hash": "opsie'%3Boopsie",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_success_work_id(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "work_id": "kissa",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_howto_setdl_success_work_id(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "howto_download_link": "https://kuvaton.com",
        "work_id": "kissa",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_success_work_idhash(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "work_id_hash": "kissa123",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_missing(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Both work_id and work_id_hash are undefined. At least one is required"
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 400
    assert resp_dict["detail"] == "Error. Both work_id and work_id_hash are undefined. At least one is required"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_permit_oopsie(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssfm3"
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "work_id": "kissa",
        "management_hash": "opsie'%3Boopsie",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfm3"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_no_righs(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. 'management_hash' doesn't have rights to set 'cert_download_link' or 'howto_download_link'"
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "work_id": "kissa",
        "management_hash": "no_righs",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 403
    assert (
        resp_dict["detail"]
        == "Error. 'management_hash' doesn't have rights to set 'cert_download_link' or 'howto_download_link'"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_oopsie_link(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssuecdll1"
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "opsie'%3Boopsie",
        "work_id": "kissa",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssuecdll1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_oopsie_link2(app_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssuecdll1"
    """
    json_dict: Dict[Any, Any] = {
        "howto_download_link": "opsie'%3Boopsie",
        "work_id": "kissa",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssuecdll1"


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
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
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
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 400
    assert resp_dict["detail"] == "Error. new_permit_hash too short. Needs to be 64 or more."


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
        "management_hash": "opsie'%3Boopsie",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfm2"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_no_rights(app_client: TestClient) -> None:
    """
    /config/add-manager
    Enrollment should fail
    reason="Error. 'management_hash' doesn't have rights add 'new_permit_hash'",  <-- non existing management_hash
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_permit_hash": "beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni",
        "management_hash": "no_rights",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 403
    assert resp_dict["detail"] == "Error. 'management_hash' doesn't have rights add 'new_permit_hash'"


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
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/add-manager", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssiim1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept(app_client: TestClient) -> None:
    """
    /accept
    Enrollment accept should be successful
    """
    json_dict: Dict[Any, Any] = {
        "work_id_hash": "kissa123",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is True
    assert resp_dict["work_id_hash"] == "kissa123"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_oopsie_permitstr(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfm1"
    """
    json_dict: Dict[Any, Any] = {"work_id_hash": "kissa123", "management_hash": "oopsie'%3Boopsie"}
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfm1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_wrong_permit(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. 'management_hash' doesn't have rights to accept given 'work_id_hash'"
    """
    json_dict: Dict[Any, Any] = {"work_id_hash": "kissa123", "management_hash": "wrongenroll"}
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 403
    assert resp_dict["detail"] == "Error. 'management_hash' doesn't have rights to accept given 'work_id_hash'"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_oopsie_enroll(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfewh1", <-- sql inject work_id_hash
    """
    json_dict: Dict[Any, Any] = {
        "work_id_hash": "oopsie'%3Boopsie",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_wrong_enroll(app_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. 'work_id_hash' not found from database.",<-- wrong enroll str
    """
    json_dict: Dict[Any, Any] = {
        "work_id_hash": "not_foound",
        "management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 404
    assert resp_dict["detail"] == "Error. 'work_id_hash' not found from database."


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_kissa(app_client: TestClient) -> None:
    """
    /deliver/{work_id_hash}
    Result should be success
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/kissa123")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["cert_download_link"] != ""
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error(app_client: TestClient) -> None:
    """
    /deliver/{work_id_hash}
    Result should fail
    reason="Error. Undefined backend error q_sssfewh1"
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/oopsie'%3Boopsie")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_sssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error_not_found(app_client: TestClient) -> None:
    """
    /deliver/{work_id_hash}
    Result should fail
    reason="Error. 'work_id_hash' not found from database."
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/notfoundhash")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 404
    assert resp_dict["detail"] == "Error. 'work_id_hash' not found from database."


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error_not_finished(app_client: TestClient) -> None:
    """
    /deliver/{work_id_hash}
    Result should fail
    reason="Enrollment is still in progress or it hasn't been accepted."
    """
    resp = await app_client.get("/api/v1/enrollment/deliver/koira123")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["cert_download_link"] == ""
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
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfe3"


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
    assert resp_dict["work_id_hash"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init_already_enrolled(app_client: TestClient) -> None:
    """Enrollment init should return code 200 and {'success':False}"""
    json_dict: Dict[Any, Any] = {"work_id": "kissa"}
    resp = await app_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] == "Error. work_id has already active enrollment"
    assert resp.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_list(app_client: TestClient) -> None:
    """
    /enrollment/list
    Result should be success and work_id_list not empty
    """
    resp = await app_client.get("/api/v1/enrollment/list")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert len(resp_dict["work_id_list"]) > 0
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_get_verification_code(app_client: TestClient) -> None:
    """
    /config/generate-verification-code
    Result should be successful
    """
    json_dict: Dict[Any, Any] = {
        "work_id": "koira",
        "service_management_hash": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
    }
    resp = await app_client.post("/api/v1/enrollment/config/generate-verification-code", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    # print("###########")
    # print(resp)
    # print(resp.json())
    # print("###########")
    assert resp.status_code == 200
    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_get_verification_code_fail(app_client: TestClient) -> None:
    """
    /config/generate-verification-code
    Result should fail
    """
    json_dict: Dict[Any, Any] = {
        "work_id": "koira",
        "service_management_hash": "wrong-management_hash",
    }
    resp = await app_client.post("/api/v1/enrollment/config/generate-verification-code", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()

    print(resp_dict)
    assert resp.status_code == 403
    assert (
        resp_dict["detail"] == "Error. 'service_management_hash' doesn't have rights to update/change verification code"
    )
