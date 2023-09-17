"""Test enrollment endpoint"""
from typing import Tuple, List, Dict, Any
import string
import random
import logging

import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_success_work_id(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-state
    Result should be successful
    """
    work_ids, _ = test_user_secrets
    koiraid = work_ids[2]
    json_dict: Dict[Any, Any] = {
        "state": "testing",
        "work_id": koiraid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_both_missing(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /config/set-state
    Result should fail
    reason="work_id missing",
    """
    json_dict: Dict[Any, Any] = {
        "state": "testing",
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_missing_value(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-state
    Result should fail
    reason=values are missing from query
    """
    workids, _ = test_user_secrets
    koiraid = workids[2]
    json_dict: Dict[Any, Any] = {"state": "testing", "err_something_missing": koiraid}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setstate_fail_oopsie_state(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-state
    Result should fail
    reason="Error. Undefined backend error q_ssues1",
    """
    workids, _ = test_user_secrets
    koiraid = workids[2]
    json_dict: Dict[Any, Any] = {
        "state": "opsie'%3Boopsie",
        "work_id": koiraid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-state", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssues1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_success_work_id(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-mtls-test-link
    Result should be successful
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "work_id": kissaid,
        "set_for_all": False,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_success_all(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-mtls-test-link
    Result should be successful
    """
    # We need the workids to exist for set_all
    _ = test_user_secrets
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "set_for_all": True,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_fail(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /config/set-mtls-test-link
    Result should be fail
    'Error. Both work_id and work_id_hash are undefined. At least one is required when 'set_for_all' is set to False'
    """
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "https://kuvaton.com",
        "set_for_all": False,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setmtlstest_fail_oopsie(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-mtls-test-link
    Result should be fail
    'Error. Both work_id and work_id_hash are undefined. At least one is required when 'set_for_all' is set to True'
    """
    # FIXME: Use the ids/hashes from test_user_secrets
    _ = test_user_secrets
    json_dict: Dict[Any, Any] = {
        "mtls_test_link": "opsie'%3Boopsie",
        "set_for_all": True,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-mtls-test-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_success_work_id(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-cert-dl-link
    Result should be successful
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "work_id": kissaid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_howto_setdl_success_work_id(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-cert-dl-link
    Result should be successful
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    json_dict: Dict[Any, Any] = {
        "howto_download_link": "https://kuvaton.com",
        "work_id": kissaid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_success_work_idhash(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-cert-dl-link
    Result should be successful
    """
    _, workhashes = test_user_secrets
    kissahash = workhashes[1]
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
        "work_id_hash": kissahash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_missing(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Both work_id and work_id_hash are undefined or empty. At least one is required"
    """
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "https://kuvaton.com",
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 400
    assert (
        resp_dict["detail"] == "Error. Both work_id and work_id_hash are undefined or empty. At least one is required"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_permit_oopsie(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssuecdll1"
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "opsie'%3Boopsie",
        "work_id": kissaid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssuecdll1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_oopsie_link(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssuecdll1"
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    json_dict: Dict[Any, Any] = {
        "cert_download_link": "opsie'%3Boopsie",
        "work_id": kissaid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssuecdll1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_setdl_fail_oopsie_link2(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /config/set-cert-dl-link
    Result should fail
    reason="Error. Undefined backend error q_ssuecdll1"
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    json_dict: Dict[Any, Any] = {
        "howto_download_link": "opsie'%3Boopsie",
        "work_id": kissaid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/config/set-cert-dl-link", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssuecdll1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_add_mgr(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /config/add-service-management-hash
    Enrollment accept should be successful
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_service_management_hash": "beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni",
    }
    resp = await tilauspalvelu_jwt_admin_client.post(
        "/api/v1/enrollment/config/add-service-management-hash", json=json_dict
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_short(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /config/add-service-management-hash
    Enrollment should fail
    reason="Error. new_service_management_hash too short. Needs to be 64 or more.",
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "banana",
        "new_service_management_hash": "too_short",
    }
    resp = await tilauspalvelu_jwt_admin_client.post(
        "/api/v1/enrollment/config/add-service-management-hash", json=json_dict
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 400
    assert resp_dict["detail"] == "Error. new_service_management_hash too short. Needs to be 64 or more."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_config_fail_mgr_bad_perm_str(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /config/add-service-management-hash
    Enrollment should fail
    reason="Error. Undefined backend error q_ssiim1", <-- permissions_str sql inject
    """
    json_dict: Dict[Any, Any] = {
        "permissions_str": "opsie'%3Boopsie",
        "new_service_management_hash": "beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni5666beni",
    }
    resp = await tilauspalvelu_jwt_admin_client.post(
        "/api/v1/enrollment/config/add-service-management-hash", json=json_dict
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssiim1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /accept
    Enrollment accept should be successful
    """
    _, workhashes = test_user_secrets
    kissahash = workhashes[1]
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "work_id_hash": kissahash,
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["work_id_hash"] == "kissa123"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_oopsie_permitstr(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfm1"
    """
    json_dict: Dict[Any, Any] = {"work_id_hash": "oopsie'%3Boopsie"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_user_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_wrong_permit(
    tilauspalvelu_jwt_user_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. 'management_hash' doesn't have rights to accept given 'work_id_hash'"
    """
    _, workhashes = test_user_secrets
    kissahash = workhashes[1]
    json_dict: Dict[Any, Any] = {"work_id_hash": kissahash, "user_management_hash": "wrongenroll"}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 403
    assert resp_dict["detail"] == "Error. Given userid doesn't have enough permissions."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_oopsie_enroll(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. Undefined backend error q_ssfewh1", <-- sql inject work_id_hash
    """
    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "work_id_hash": "oopsie'%3Boopsie",
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_accept_fail_wrong_enroll(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /accept
    Enrollment should fail
    reason="Error. 'work_id_hash' not found from database.",<-- wrong enroll str
    """
    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "work_id_hash": "not_foound",
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 404
    assert resp_dict["detail"] == "Error. 'work_id_hash' not found from database."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_kissa(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /deliver
    Result should be success
    """
    _, workhashes = test_user_secrets
    kissahash = workhashes[1]
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/deliver", query_string={"work_id_hash": kissahash}
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["cert_download_link"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /deliver/{work_id_hash}
    Result should fail
    reason="Error. Undefined backend error q_sssfewh1"
    """
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/deliver", query_string={"work_id_hash": "oopsie'%3Boopsie"}
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_sssfewh1"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error_not_found(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /deliver/{work_id_hash}
    Result should fail
    reason="Error. 'work_id_hash' not found from database."
    """
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/deliver", query_string={"work_id_hash": "notfoundhash"}
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 404
    assert resp_dict["detail"] == "Error. 'work_id_hash' not found from database."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_deliver_error_not_finished(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /deliver/{work_id_hash}
    Result should fail
    reason="Enrollment is still in progress or it hasn't been accepted."
    """
    _, workhashes = test_user_secrets
    koirahash = workhashes[2]
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/deliver", query_string={"work_id_hash": koirahash}
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 202
    assert resp_dict["detail"] == "Enrollment is still in progress or it hasn't been accepted."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status_kissa(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    Enrollment status should be 200 !str(none)
    """
    workids, _ = test_user_secrets
    kissaid = workids[1]
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/status", query_string={"work_id": kissaid})
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["status"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status_nope(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Enrollment status should be 200 str('none')
    """
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/status", query_string={"work_id": "notexisting"}
    )
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["status"] == "none"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_status_error(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Enrollment status should be 200 str('none')
    """
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/status", query_string={"work_id": "oopsie'%3Boopsie"}
    )
    resp_dict: Dict[Any, Any] = resp.json()
    LOGGER.debug("#test_get_enrollment_status#")
    LOGGER.debug(resp)
    LOGGER.debug(resp.json())
    LOGGER.debug("###########")
    assert resp.status_code == 500
    assert resp_dict["detail"] == "Error. Undefined backend error q_ssfe3"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init_missing_values(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """Enrollment init should return code 422 for missing json values"""
    json_dict: Dict[Any, Any] = {"missing": "json", "params": None}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """Enrollment init should return code 200 and {'success':True}"""
    _enrollment_id: str = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(64)
        ]
    )
    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "work_id": _enrollment_id,
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["work_id_hash"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_init_already_enrolled(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """Enrollment init should return code 200 and {'success':False}"""
    workids, workhashes = test_user_secrets
    kissaid = workids[1]
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "work_id": kissaid,
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] == "Error. work_id has already active enrollment"
    assert resp.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_list(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /enrollment/list
    Result should be success and work_id_list not empty
    """
    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/list", query_string={"user_management_hash": usermgmnthash}
    )
    LOGGER.debug(resp)
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert len(resp_dict["work_id_list"]) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_get_verification_code(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /generate-verification-code
    Result should be successful
    """
    workids, _ = test_user_secrets
    koiraid = workids[2]
    json_dict: Dict[Any, Any] = {
        "work_id": koiraid,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/generate-verification-code", json=json_dict)
    # LOGGER.debug("###########")
    # LOGGER.debug(resp)
    # LOGGER.debug(resp.json())
    # LOGGER.debug("###########")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_invitecode_create(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /invitecode/create
    Result should succeed
    """
    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    LOGGER.debug(resp)
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["invite_code"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_user_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_invitecode_create_fail(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    /invitecode/create
    Result should fail
    """
    json_dict: Dict[Any, Any] = {
        "user_management_hash": "no permissions",
    }
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/invitecode/create", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    LOGGER.debug(resp)
    LOGGER.debug(resp_dict)
    assert resp.status_code == 403
    assert resp_dict["detail"] == "Error. Given userid doesn't have enough permissions."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_invitecode_enroll(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /invitecode/create
    /invitecode/enroll
    Result should succeed
    """
    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()

    _enrollment_id: str = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(32)
        ]
    )

    json_dict = {
        "work_id": f"taikaperuna666_{_enrollment_id}",
        "invite_code": resp_dict["invite_code"],
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()

    LOGGER.debug(resp)
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["work_id"] != ""
    assert resp_dict["work_id_hash"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_invitecode_enroll_invalid(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /invitecode/enroll
    Result should fail
    """
    _enrollment_id: str = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(32)
        ]
    )
    json_dict: Dict[Any, Any] = {
        "work_id": f"taikaperuna666_{_enrollment_id}",
        "invite_code": "this_shouldnt_be",
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()

    LOGGER.debug(resp)
    LOGGER.debug(resp_dict)
    assert resp.status_code == 400
    assert resp_dict["detail"] == "Error. invitecode not valid."


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_enrollment_invitecode_enroll_already_active(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /invitecode/create
    /invitecode/enroll
    Result should fail
    """
    workids, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    koiraid = workids[2]
    json_dict: Dict[Any, Any] = {
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()

    json_dict = {
        "work_id": koiraid,
        "invite_code": resp_dict["invite_code"],
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()

    LOGGER.debug(resp)
    LOGGER.debug(resp_dict)
    assert resp.status_code == 400
    assert resp_dict["detail"] == "Error. work_id has already active enrollment"


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_invitecode_check(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: Tuple[List[str], List[str]]
) -> None:
    """
    /invitecode?invitecode=xxxx
    Result should be success
    """

    _, workhashes = test_user_secrets
    usermgmnthash = workhashes[0]
    json_dict: Dict[Any, Any] = {
        "user_management_hash": usermgmnthash,
    }
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()

    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/invitecode", query_string={"invitecode": resp_dict["invite_code"]}
    )
    resp_dict = resp.json()
    assert resp.status_code == 200
    assert resp_dict["invitecode_is_active"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_enrollment_invitecode_check_fail(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    /invitecode?invitecode=xxxx
    Result should be invitecode_is_active == False
    """

    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/invitecode?invitecode=nope")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    print(resp_dict)
    assert resp_dict["invitecode_is_active"] is False
