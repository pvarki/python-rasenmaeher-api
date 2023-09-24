"""Test enrollment endpoint"""
import logging
from typing import Dict, Any
import pytest

from async_asgi_testclient import TestClient  # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)


# GENERATE VERIFICATEION CODE
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_enroll_verif_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - verification code should succeed
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/generate-verification-code")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)

    assert resp.status_code == 200


# GENERATE VERIFICATEION CODE - NO JWT - FAIL
@pytest.mark.asyncio
async def test_enroll_verif_code_fail_no_jwt(unauth_client: TestClient) -> None:
    """
    Test - No JWT --> fail
    """

    resp = await unauth_client.post("/api/v1/enrollment/generate-verification-code")

    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code != 200


# SHOW VERIFICATION CODE INFO
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_enroll_show_verif_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - show verification code info
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/generate-verification-code")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    _code: str = resp_dict["verification_code"]

    resp = await tilauspalvelu_jwt_admin_client.get(
        f"/api/v1/enrollment/show-verification-code-info?verification_code={_code}"
    )
    resp_dict = resp.json()
    print(resp_dict)

    assert resp.status_code == 200
    assert resp_dict["work_id"] != ""


# SHOW VERIFICATION CODE INFO - BAD CODE
# SHOW VERIFICATION CODE INFO - CODE EMPTY
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_enroll_show_verifcode_bad_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - show verification code info
    """
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)

    assert resp.status_code == 404
    assert resp_dict["detail"] != ""

    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/show-verification-code-info?verification_code=")
    resp_dict = resp.json()
    print(resp_dict)

    assert resp.status_code == 400
    assert resp_dict["detail"] != ""


# SHOW VERIFICATION CODE INFO - NO JWT
@pytest.mark.asyncio
async def test_show_verifcode_no_jwt(unauth_client: TestClient) -> None:
    """
    Test - no JWT, should fail
    """
    resp = await unauth_client.get("/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# SHOW VERIFICATION CODE INFO - NO PERMISSION
@pytest.mark.asyncio
async def test_show_verifcode_no_permission(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - no such code --> fail
    """
    resp = await tilauspalvelu_jwt_user_client.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# SHOW VERIFICATION CODE INFO - JWT SUB CANNOT BE FOUND
@pytest.mark.asyncio
async def test_show_verifcode_sub_is_bonkers(tilauspalvelu_jwt_without_proper_user_client: TestClient) -> None:
    """
    Test - sub in JWT cannot be found
    """
    resp = await tilauspalvelu_jwt_without_proper_user_client.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 404


# HAVE I BEEN ACCEPTED - YES
@pytest.mark.asyncio
async def test_have_i_been_accepted_yes(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - have i been accepted, yes
    """
    resp = await tilauspalvelu_jwt_user_client.get("/api/v1/enrollment/have-i-been-accepted")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["have_i_been_accepted"] is True
    assert resp.status_code == 200


# HAVE I BEEN ACCEPTED - NO
@pytest.mark.asyncio
async def test_have_i_been_accepted_no(tilauspalvelu_jwt_user_koira_client: TestClient) -> None:
    """
    Test - have i been accepted, no
    """
    resp = await tilauspalvelu_jwt_user_koira_client.get("/api/v1/enrollment/have-i-been-accepted")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["have_i_been_accepted"] is False
    assert resp.status_code == 200


# HAVE I BEEN ACCEPTED - NO - NO JWT
@pytest.mark.asyncio
async def test_have_i_been_accepted_no_jwt(unauth_client: TestClient) -> None:
    """
    Test - have i been - no JWt
    """
    resp = await unauth_client.get("/api/v1/enrollment/have-i-been-accepted")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# STATUS USER FOUND
@pytest.mark.asyncio
async def test_status_koira(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - get status
    """
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/status?work_id=koira")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200


# STATUS USER NOT FOUND
@pytest.mark.asyncio
async def test_status_not_found(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - no such status
    """
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/status?work_id=ponikadoksissa")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)

    assert resp.status_code == 200


# LIST AS ADMIN USER
@pytest.mark.asyncio
async def test_list_as_adm(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - list enrollments
    """
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/list")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["work_id_list"] is not None
    assert resp.status_code == 200


# LIST AS NORMAL USER
@pytest.mark.asyncio
async def test_list_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - list enrollments as normal user
    """
    resp = await tilauspalvelu_jwt_user_client.get("/api/v1/enrollment/list")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# INIT NEW USER
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_init(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - init new user
    """
    json_dict: Dict[Any, Any] = {"work_id": "superjuusto"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["work_id"] != ""

    ## INIT USER ALREADY FOUND
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# INIT AS NORMAL USER
@pytest.mark.asyncio
async def test_init_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - init as normal user --> fail
    """
    json_dict: Dict[Any, Any] = {"work_id": "superkayra"}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/list", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 405


# PROMOTE NORMAL USER
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_promote_demote(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - promote user
    """
    json_dict: Dict[Any, Any] = {"work_id": "kissa"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/promote", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    # DEMOTE NORMAL USER
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/demote", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    # PROMOTE USER - ALREADY ADMIN
    json_dict = {"work_id": "secondadmin"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/promote", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 400


# PROMOTE AS NORMAL USER - NO PERMISSION
# DEMOTE AS NORMAL USER - NO PERMISSION
@pytest.mark.asyncio
async def test_promote_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - promote user, no permissions
    """
    json_dict: Dict[Any, Any] = {"work_id": "superkayra"}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/promote", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# LOCK USER
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_lock(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - lock
    """
    json_dict: Dict[Any, Any] = {"work_id": "lockme"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    assert resp.status_code == 200

    json_dict = {"work_id": "lockme", "lock_reason": "pytest"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/lock", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200


# LOCK USER - NO PERMISSION
@pytest.mark.asyncio
async def test_lock_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - lock as normal use
    """
    json_dict: Dict[Any, Any] = {"work_id": "secondadmin"}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/lock", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 422


# ACCEPT
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_accept(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - accept enrollment
    """
    json_dict: Dict[Any, Any] = {"work_id": "acceptme"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    json_dict = {"work_id": "acceptme"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["work_id"] != ""

    # ACCEPT - ALREADY ACCEPTED
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 403


# ACCEPT - NO PERMISSIONS
@pytest.mark.asyncio
async def test_accept_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - accept, no permissions -> fail
    """
    json_dict: Dict[Any, Any] = {"work_id": "koira"}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# ACCEPT - NO SUCH USER
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_accept_no_such_user(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - accept a ghost
    """
    json_dict: Dict[Any, Any] = {"work_id": "duhnosuchuser"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp.status_code == 404
    assert resp_dict["detail"] != ""


# CREATE INVITE CODE
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_invitecode_create(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - create invite code
    """
    # json_dict: Dict[Any, Any] = {"work_id": "duhnosuchuser"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    # INVITE CODE SHOULD CHANGE
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict = resp.json()
    assert resp.status_code == 200
    assert _inv_code != resp_dict["invite_code"]


# CREATE INVITE - NO RIGHTS
@pytest.mark.asyncio
async def test_create_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - normal user create invite code --> fail
    """
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# INVITE CODE DEACTIVATE
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_invitecode_dectivate(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - deactivate invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    json_dict: Dict[Any, Any] = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/deactivate", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    # INVITE CODE DEACTIVATE - ALREADY DEACTIVATED
    json_dict = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/deactivate", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200


# INVITE CODE ACTIVATE
@pytest.mark.asyncio
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_invitecode_activate(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - activate invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    json_dict: Dict[Any, Any] = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/activate", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    # INVITE CODE ACTIVATE - ALREADY ACTIVE
    json_dict = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/activate", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200


# CHECK INVITE CODE
@pytest.mark.asyncio
async def test_invite_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - check invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    resp = await tilauspalvelu_jwt_admin_client.get(f"/api/v1/enrollment/invitecode?invitecode={_inv_code}")
    resp_dict = resp.json()
    print(resp_dict)
    assert resp_dict["invitecode_is_active"] is True
    assert resp.status_code == 200

    # CHECK INVITE CODE - NOT FOUND
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/invitecode?invitecode=qweewqioweqioweq")
    resp_dict = resp.json()
    print(resp_dict)
    assert resp_dict["invitecode_is_active"] is False
    assert resp.status_code == 200


# ENROLL WITH INVITE CODE
@pytest.mark.asyncio
async def test_enroll_with_invite_code(tilauspalvelu_jwt_admin_client: TestClient, unauth_client: TestClient) -> None:
    """
    Test - enroll with invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: Dict[Any, Any] = resp.json()
    print(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    json_dict: Dict[Any, Any] = {"invite_code": _inv_code, "work_id": "enrollenrique"}
    resp = await unauth_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["jwt"] != ""

    # ENROLL WITH INVITE CODE - BAD CODE
    json_dict = {"invite_code": "nosuchcode123", "work_id": "asdasds"}
    resp = await unauth_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 404
    assert resp_dict["detail"] != ""

    # ENROLL WITH INVITE CODE - USERNAME TAKEN
    json_dict = {"invite_code": _inv_code, "work_id": "enrollenrique"}
    resp = await unauth_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 400
    assert "taken" in resp_dict["detail"]

    # ENROLL WITH INVITE CODE - CODE IS LOCKED
    json_dict = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/deactivate", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 200

    json_dict = {"invite_code": _inv_code, "work_id": "enriquescousin"}
    resp = await unauth_client.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    print(resp_dict)
    assert resp.status_code == 400
    assert "disabled" in resp_dict["detail"]
