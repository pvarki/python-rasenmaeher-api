"""Test enrollment endpoint"""

import asyncio
import logging
import secrets
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import cryptography.hazmat.primitives.serialization.pkcs12
import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI
from libpvarki.mtlshelp.csr import async_create_client_csr, async_create_keypair

from rasenmaeher_api.db import (
    EngineWrapper,
    Enrollment,
    EnrollmentPool,
    EnrollmentState,
    Person,
)
from rasenmaeher_api.db.errors import CallsignReserved
from rasenmaeher_api.rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


# GENERATE VERIFICATEION CODE
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_enroll_verif_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - verification code should succeed
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/generate-verification-code")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)

    assert resp.status_code == 200


# GENERATE VERIFICATEION CODE - NO JWT - FAIL
@pytest.mark.asyncio(loop_scope="session")
async def test_enroll_verif_code_fail_no_jwt(unauth_client_session: TestClient) -> None:
    """
    Test - No JWT --> fail
    """

    resp = await unauth_client_session.post("/api/v1/enrollment/generate-verification-code")

    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code != 200


# SHOW VERIFICATION CODE INFO
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_enroll_show_verif_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - show verification code info
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/generate-verification-code")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    _code: str = resp_dict["verification_code"]

    resp = await tilauspalvelu_jwt_admin_client.get(
        f"/api/v1/enrollment/show-verification-code-info?verification_code={_code}"
    )
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)

    assert resp.status_code == 200
    assert resp_dict["callsign"] != ""


# SHOW VERIFICATION CODE INFO - BAD CODE
# SHOW VERIFICATION CODE INFO - CODE EMPTY
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_enroll_show_verifcode_bad_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - show verification code info
    """
    resp = await tilauspalvelu_jwt_admin_client.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)

    assert resp.status_code == 404
    assert resp_dict["detail"] != ""

    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/show-verification-code-info?verification_code=")
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)

    assert resp.status_code == 400
    assert resp_dict["detail"] != ""


# SHOW VERIFICATION CODE INFO - NO JWT
@pytest.mark.asyncio(loop_scope="session")
async def test_show_verifcode_no_jwt(unauth_client_session: TestClient) -> None:
    """
    Test - no JWT, should fail
    """
    unauth_client_session.headers.clear()
    resp = await unauth_client_session.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# SHOW VERIFICATION CODE INFO - NO PERMISSION
@pytest.mark.asyncio(loop_scope="session")
async def test_show_verifcode_no_permission(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - no such code --> fail
    """
    resp = await tilauspalvelu_jwt_user_client.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# SHOW VERIFICATION CODE INFO - JWT SUB CANNOT BE FOUND
@pytest.mark.asyncio(loop_scope="session")
async def test_show_verifcode_sub_is_bonkers(tilauspalvelu_jwt_without_proper_user_client: TestClient) -> None:
    """
    Test - sub in JWT cannot be found
    """
    resp = await tilauspalvelu_jwt_without_proper_user_client.get(
        "/api/v1/enrollment/show-verification-code-info?verification_code=nosuchcode"
    )
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# HAVE I BEEN ACCEPTED - YES
@pytest.mark.asyncio(loop_scope="session")
async def test_have_i_been_accepted_yes(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - have i been accepted, yes
    """
    resp = await tilauspalvelu_jwt_user_client.get("/api/v1/enrollment/have-i-been-accepted")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["have_i_been_accepted"] is True
    assert resp.status_code == 200


# HAVE I BEEN ACCEPTED - NO
@pytest.mark.asyncio(loop_scope="session")
async def test_have_i_been_accepted_no(tilauspalvelu_jwt_user_koira_client: TestClient) -> None:
    """
    Test - have i been accepted, no
    """
    resp = await tilauspalvelu_jwt_user_koira_client.get("/api/v1/enrollment/have-i-been-accepted")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["have_i_been_accepted"] is False
    assert resp.status_code == 200


# HAVE I BEEN ACCEPTED - NO - NO JWT
@pytest.mark.asyncio(loop_scope="session")
async def test_have_i_been_accepted_no_jwt(unauth_client_session: TestClient) -> None:
    """
    Test - have i been - no JWt
    """
    unauth_client_session.headers.clear()
    resp = await unauth_client_session.get("/api/v1/enrollment/have-i-been-accepted")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# STATUS USER FOUND
@pytest.mark.asyncio(loop_scope="session")
async def test_status_koira(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: tuple[list[str], list[str]]
) -> None:
    """
    Test - get status
    """
    work_ids, _ = test_user_secrets
    koira_id = work_ids[3]
    resp = await tilauspalvelu_jwt_admin_client.get(f"/api/v1/enrollment/status?callsign={koira_id}")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200


# STATUS USER NOT FOUND
@pytest.mark.asyncio(loop_scope="session")
async def test_status_not_found(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - no such status
    """
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/status?callsign=ponikadoksissa")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)

    assert resp.status_code == 200


# LIST AS ADMIN USER
@pytest.mark.asyncio(loop_scope="session")
async def test_list_as_adm(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - list enrollments
    """
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/list")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["callsign_list"] is not None
    assert resp_dict["callsign_list"][0]["callsign"]
    assert not resp_dict["callsign_list"][0]["approvecode"]
    assert resp.status_code == 200


# LIST AS NORMAL USER
@pytest.mark.asyncio(loop_scope="session")
async def test_list_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - list enrollments as normal user
    """
    resp = await tilauspalvelu_jwt_user_client.get("/api/v1/enrollment/list")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# INIT NEW USER
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_post_init(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - init new user
    """
    superjuusto = f"superjuusto_{secrets.token_hex(4)}"
    json_dict: dict[Any, Any] = {"callsign": superjuusto}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["callsign"] != ""

    ## INIT USER ALREADY FOUND
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# INIT AS NORMAL USER
@pytest.mark.asyncio(loop_scope="session")
async def test_init_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - init as normal user --> fail
    """
    superkayra = f"superkayra_{secrets.token_hex(4)}"
    json_dict: dict[Any, Any] = {"callsign": superkayra}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/list", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 405


# PROMOTE NORMAL USER
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_promote_demote(
    tilauspalvelu_jwt_admin_client: TestClient, test_user_secrets: tuple[list[str], list[str]]
) -> None:
    """
    Test - promote user
    """
    work_ids, _ = test_user_secrets
    kissa_id = work_ids[2]
    json_dict: dict[Any, Any] = {"callsign": kissa_id}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/promote", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # DEMOTE NORMAL USER
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/demote", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # PROMOTE USER - ALREADY ADMIN
    secondadmin = work_ids[1]
    json_dict = {"callsign": secondadmin}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/promote", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 400


# PROMOTE AS NORMAL USER - NO PERMISSION
# DEMOTE AS NORMAL USER - NO PERMISSION
@pytest.mark.asyncio(loop_scope="session")
async def test_promote_as_usr(
    tilauspalvelu_jwt_user_client: TestClient, test_user_secrets: tuple[list[str], list[str]]
) -> None:
    """
    Test - promote user, no permissions
    """
    work_ids, _ = test_user_secrets
    kissa_id = work_ids[2]
    json_dict: dict[Any, Any] = {"callsign": kissa_id}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/promote", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# LOCK USER
@pytest.mark.xfail(reason="TODO: Figure out why only these two started failing")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_lock(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - lock
    """
    lockme = f"lockme_{secrets.token_hex(4)}"
    json_dict: dict[Any, Any] = {"callsign": lockme}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    assert resp.status_code == 200

    json_dict = {"callsign": lockme, "lock_reason": "pytest"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/lock", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200


# LOCK USER - NO PERMISSION
@pytest.mark.asyncio(loop_scope="session")
async def test_lock_as_usr(
    tilauspalvelu_jwt_user_client: TestClient, test_user_secrets: tuple[list[str], list[str]]
) -> None:
    """
    Test - lock as normal use
    """
    work_ids, _ = test_user_secrets
    kissa_id = work_ids[2]
    json_dict: dict[Any, Any] = {"callsign": kissa_id}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/lock", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# ACCEPT
@pytest.mark.xfail(reason="TODO: Figure out why only these two started failing")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_accept(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - accept enrollment
    """
    acceptme = f"acceptme_{secrets.token_hex(4)}"
    json_dict: dict[Any, Any] = {"callsign": acceptme}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200
    assert "approvecode" in resp_dict

    json_dict = {"callsign": acceptme, "approvecode": resp_dict["approvecode"]}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # ACCEPT - ALREADY ACCEPTED
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 403


# ACCEPT - NO PERMISSIONS
@pytest.mark.asyncio(loop_scope="session")
async def test_accept_as_usr(
    tilauspalvelu_jwt_user_client: TestClient, test_user_secrets: tuple[list[str], list[str]]
) -> None:
    """
    Test - accept, no permissions -> fail
    """
    work_ids, _ = test_user_secrets
    kissa_id = work_ids[2]
    json_dict: dict[Any, Any] = {"callsign": kissa_id, "approvecode": "nocode"}
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# ACCEPT - NO SUCH USER
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_accept_no_such_user(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - accept a ghost
    """
    json_dict: dict[Any, Any] = {"callsign": "duhnosuchuser", "approvecode": "nosuchcode"}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 404
    assert resp_dict["detail"] != ""


# CREATE INVITE CODE
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_invitecode_create(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - create invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    # INVITE CODE SHOULD CHANGE
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict = resp.json()
    assert resp.status_code == 200
    assert _inv_code != resp_dict["invite_code"]


# CREATE INVITE - NO RIGHTS
@pytest.mark.asyncio(loop_scope="session")
async def test_create_as_usr(tilauspalvelu_jwt_user_client: TestClient) -> None:
    """
    Test - normal user create invite code --> fail
    """
    resp = await tilauspalvelu_jwt_user_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["detail"] != ""
    assert resp.status_code == 403


# INVITE CODE DEACTIVATE
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_invitecode_deactivate(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - deactivate invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    json_dict: dict[Any, Any] = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/deactivate", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # INVITE CODE DEACTIVATE - ALREADY DEACTIVATED
    json_dict = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/deactivate", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200


# INVITE CODE ACTIVATE
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("tilauspalvelu_jwt_admin_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_invitecode_activate(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - activate invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    json_dict: dict[Any, Any] = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/activate", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # INVITE CODE ACTIVATE - ALREADY ACTIVE
    json_dict = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/activate", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200


# CHECK INVITE CODE
@pytest.mark.asyncio(loop_scope="session")
async def test_invite_code(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """
    Test - check invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    resp = await tilauspalvelu_jwt_admin_client.get(f"/api/v1/enrollment/invitecode?invitecode={_inv_code}")
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["invitecode_is_active"] is True
    assert resp.status_code == 200

    # CHECK INVITE CODE - NOT FOUND
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/invitecode?invitecode=qweewqioweqioweq")
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp_dict["invitecode_is_active"] is False
    assert resp.status_code == 200


# ENROLL WITH INVITE CODE
@pytest.mark.asyncio(loop_scope="session")
async def test_enroll_with_invite_code(
    tilauspalvelu_jwt_admin_client: TestClient, unauth_client_session: TestClient
) -> None:
    """
    Test - enroll with invite code
    """
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    _inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert _inv_code != ""

    enrollenrique = f"enrollenrique_{secrets.token_hex(4)}"
    json_dict: dict[Any, Any] = {"invite_code": _inv_code, "callsign": enrollenrique}
    resp = await unauth_client_session.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["jwt"] != ""
    assert resp_dict["approvecode"] != ""
    enrique_jwt = resp_dict["jwt"]
    enrique_ac = resp_dict["approvecode"]

    # list enrollments filter by code
    resp = await tilauspalvelu_jwt_admin_client.get(f"/api/v1/enrollment/list?code={enrique_ac}")
    resp_dict = resp.json()
    assert resp_dict["callsign_list"] is not None
    assert resp_dict["callsign_list"][0]["callsign"] == enrollenrique
    assert resp_dict["callsign_list"][0]["approvecode"] == enrique_ac

    # ENROLL WITH INVITE CODE - BAD CODE
    json_dict = {"invite_code": "nosuchcode123", "callsign": "asdasds"}
    resp = await unauth_client_session.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 404
    assert resp_dict["detail"] != ""

    # ENROLL WITH INVITE CODE - USERNAME TAKEN
    json_dict = {"invite_code": _inv_code, "callsign": enrollenrique}
    resp = await unauth_client_session.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 400
    assert "taken" in resp_dict["detail"]

    # ENROLL WITH INVITE CODE - CODE IS LOCKED
    json_dict = {"invite_code": _inv_code}
    resp = await tilauspalvelu_jwt_admin_client.put("/api/v1/enrollment/invitecode/deactivate", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    enriquescousin = f"enriquescousin_{secrets.token_hex(4)}"
    json_dict = {"invite_code": _inv_code, "callsign": enriquescousin}
    resp = await unauth_client_session.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 400
    assert "disabled" in resp_dict["detail"]

    # Accept the enrollment
    json_dict = {"callsign": enrollenrique, "approvecode": enrique_ac}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # Fetch the PFX
    unauth_client_session.headers.clear()
    unauth_client_session.headers.update({"Authorization": f"Bearer {enrique_jwt}"})
    resp = await unauth_client_session.get(f"/api/v1/enduserpfx/{enrollenrique}")
    resp.raise_for_status()
    pfxdata = cryptography.hazmat.primitives.serialization.pkcs12.load_pkcs12(
        resp.content, enrollenrique.encode("ascii")
    )
    assert pfxdata.key
    assert pfxdata.cert

    # Fetch also with alternative URLs
    pfxurl = f"/api/v1/enduserpfx/{enrollenrique}.pfx"
    LOGGER.debug(f"Trying: {pfxurl}")
    unauth_client_session.headers.update({"Authorization": f"Bearer {enrique_jwt}"})
    resp = await unauth_client_session.get(pfxurl)
    resp.raise_for_status()
    pfxurl2 = f"/api/v1/enduserpfx/{enrollenrique}_{RMSettings.singleton().deployment_name}.pfx"
    LOGGER.debug(f"Trying: {pfxurl2}")
    unauth_client_session.headers.update({"Authorization": f"Bearer {enrique_jwt}"})
    resp = await unauth_client_session.get(
        pfxurl2,
    )
    resp.raise_for_status()

    del unauth_client_session.headers["Authorization"]


# ENROLL WITH CSR (and invite-code
@pytest.mark.asyncio(loop_scope="session")
async def test_enroll_with_csr(
    tilauspalvelu_jwt_admin_client: TestClient, unauth_client_session: TestClient, nice_tmpdir: str
) -> None:
    """test enrolling with CSR"""
    tempdir = Path(nice_tmpdir)
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/invitecode/create")
    resp_dict: dict[Any, Any] = resp.json()
    LOGGER.debug(resp_dict)
    inv_code = resp_dict["invite_code"]
    assert resp.status_code == 200
    assert inv_code != ""

    callsign = f"csr_roller_{secrets.token_hex(4)}"
    privkeyfile = Path(tempdir) / "user.key"
    pubkeyfile = Path(tempdir) / "user.pub"
    csrfile = Path(tempdir) / "user.csr"
    ckp = await async_create_keypair(privkeyfile, pubkeyfile)
    csrpem = await async_create_client_csr(ckp, csrfile, {"CN": callsign})

    json_dict: dict[Any, Any] = {"invite_code": inv_code, "callsign": callsign, "csr": csrpem}
    resp = await unauth_client_session.post("/api/v1/enrollment/invitecode/enroll", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200
    assert resp_dict["jwt"] != ""
    assert resp_dict["approvecode"] != ""
    user_jwt = resp_dict["jwt"]
    user_ac = resp_dict["approvecode"]

    # Accept the enrollment
    json_dict = {"callsign": callsign, "approvecode": user_ac}
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/accept", json=json_dict)
    resp_dict = resp.json()
    LOGGER.debug(resp_dict)
    assert resp.status_code == 200

    # Fetch the PFX
    unauth_client_session.headers.clear()
    unauth_client_session.headers.update({"Authorization": f"Bearer {user_jwt}"})
    resp = await unauth_client_session.get(f"/api/v1/enduserpfx/{callsign}.pfx")
    resp.raise_for_status()
    pfxdata = cryptography.hazmat.primitives.serialization.pkcs12.load_pkcs12(resp.content, callsign.encode("utf-8"))
    assert not pfxdata.key
    assert pfxdata.additional_certs[0]
    cert = pfxdata.additional_certs[0]
    assert cert.friendly_name
    assert cert.friendly_name.decode("utf-8") == callsign
    # TODO: check extensions

    # Fetch PEM cert
    resp = await unauth_client_session.get(f"/api/v1/enduserpfx/{callsign}.pem")
    resp.raise_for_status()
    certs = x509.load_pem_x509_certificates(resp.content)
    assert certs
    dn = certs[0].subject.rfc4514_string()
    LOGGER.debug(f"DN={dn} callsign={callsign}")
    assert f"CN={callsign}" in dn
    # TODO: check extensions


@pytest.mark.asyncio(loop_scope="session")
async def test_enrollmentpools_revoked_creator(dbinit_func, tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """Test that pools list does not die if creator is revoked"""
    _ = dbinit_func
    invitecode = str(uuid.uuid4())
    toberevoked = f"toberevoked_{secrets.token_hex(4)}"
    person = await Person.create_with_cert(toberevoked)
    with EngineWrapper.singleton().get_session() as session:
        pool = EnrollmentPool(owner=person.pk, invitecode=invitecode)
        session.add(pool)
        session.commit()
        session.refresh(pool)
    await person.revoke("key_compromise")
    resp = await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/pools")
    resp.raise_for_status()
    resp_dict = resp.json()
    assert "pools" in resp_dict
    found = False
    for pool in resp_dict["pools"]:
        if pool["invitecode"] == invitecode:
            found = True
            break
    assert found


MDM_AGENT_CN = "rmscep-test"


@pytest_asyncio.fixture(scope="function")
async def mdm_agent_client(app_instance: FastAPI) -> AsyncGenerator[TestClient, None]:
    """Client authenticating as the MDM enrollment agent

    The agent holds its own client certificate from the deployment CA; in a real deployment the
    front proxy puts its DN in this header exactly like it does for a browser.
    """
    settings = RMSettings.singleton()
    previous = settings.mdm_agent_cns
    settings.mdm_agent_cns = MDM_AGENT_CN
    async with TestClient(app_instance) as instance:
        instance.headers.update({"X-ClientCert-DN": f"CN={MDM_AGENT_CN},O=N/A"})
        yield instance
    settings.mdm_agent_cns = previous


async def _device_csr(tempdir: Path, callsign: str, name: str = "device") -> str:
    """A CSR the way a device would send one: its own key, its callsign as the CN"""
    privkeyfile = Path(tempdir) / f"{name}.key"
    pubkeyfile = Path(tempdir) / f"{name}.pub"
    csrfile = Path(tempdir) / f"{name}.csr"
    ckp = await async_create_keypair(privkeyfile, pubkeyfile)
    return str(await async_create_client_csr(ckp, csrfile, {"CN": callsign}))


def _public_key_der(pem: str) -> bytes:
    """SubjectPublicKeyInfo of whatever this PEM is, certificate or request"""
    encoding, fmt = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    if "CERTIFICATE REQUEST" in pem:
        return x509.load_pem_x509_csr(pem.encode("utf-8")).public_key().public_bytes(encoding, fmt)
    return x509.load_pem_x509_certificate(pem.encode("utf-8")).public_key().public_bytes(encoding, fmt)


@pytest.mark.asyncio(loop_scope="session")
async def test_mdm_planned_enrollment_is_not_approvable_by_hand(
    tilauspalvelu_jwt_admin_client: TestClient,
) -> None:
    """An admin planning a device must not be able to approve it and spend the callsign"""
    callsign = f"mdmplanned_{secrets.token_hex(4)}"
    resp = await tilauspalvelu_jwt_admin_client.post(
        "/api/v1/enrollment/init", json={"callsign": callsign, "mdm": True}
    )
    assert resp.status_code == 200
    planned = resp.json()
    assert planned["callsign"] == callsign
    # No credential for the device is handed to the admin planning it
    assert planned["jwt"] == ""

    resp = await tilauspalvelu_jwt_admin_client.post(
        "/api/v1/enrollment/accept", json={"callsign": callsign, "approvecode": planned["approvecode"]}
    )
    assert resp.status_code == 409
    # and the enrollment is untouched, so the device can still take it
    still_pending = await Enrollment.by_callsign(callsign)
    assert still_pending.state == 0
    assert still_pending.csr is None


@pytest.mark.asyncio(loop_scope="session")
async def test_mdm_agent_completes_planned_enrollment(
    tilauspalvelu_jwt_admin_client: TestClient, mdm_agent_client: TestClient, nice_tmpdir: str
) -> None:
    """The whole agent path: plan, complete with the device CSR, and survive a repeat"""
    tempdir = Path(nice_tmpdir)
    callsign = f"mdmdevice_{secrets.token_hex(4)}"
    resp = await tilauspalvelu_jwt_admin_client.post(
        "/api/v1/enrollment/init", json={"callsign": callsign, "mdm": True}
    )
    assert resp.status_code == 200

    csrpem = await _device_csr(tempdir, callsign)
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": callsign, "csr": csrpem})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    certpem = body["certificate"]
    assert certpem

    # The certificate must be for the key the device holds. If this ever regresses, rasenmaeher
    # generated a keypair of its own and the device received a certificate it cannot use.
    assert _public_key_der(certpem) == _public_key_der(csrpem)
    assert [attr.value for attr in x509.load_pem_x509_certificate(certpem.encode("utf-8")).subject] == [callsign]

    # The reply can be lost on the way back to the MDM, which then repeats the request verbatim
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": callsign, "csr": csrpem})
    assert resp.status_code == 200
    assert resp.json()["certificate"] == certpem

    # ...but a different key for the same callsign is somebody else
    other_csr = await _device_csr(tempdir, callsign, name="imposter")
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": callsign, "csr": other_csr})
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_mdm_agent_refusals(
    tilauspalvelu_jwt_admin_client: TestClient,
    mdm_agent_client: TestClient,
    unauth_client_session: TestClient,
    nice_tmpdir: str,
) -> None:
    """What the agent may not do"""
    tempdir = Path(nice_tmpdir)

    # A callsign nobody planned
    unplanned = f"mdmunplanned_{secrets.token_hex(4)}"
    csrpem = await _device_csr(tempdir, unplanned, name="unplanned")
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": unplanned, "csr": csrpem})
    assert resp.status_code == 403
    with pytest.raises(Exception):  # noqa: B017 -- NotFound, and nothing was written
        await Enrollment.by_callsign(unplanned)

    # A CSR for a different callsign than the one being completed
    planned = f"mdmmismatch_{secrets.token_hex(4)}"
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json={"callsign": planned, "mdm": True})
    assert resp.status_code == 200
    wrong_csr = await _device_csr(tempdir, f"{planned}X", name="mismatch")
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": planned, "csr": wrong_csr})
    assert resp.status_code == 403
    assert (await Enrollment.by_callsign(planned)).csr is None

    # No CSR at all
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": planned})
    assert resp.status_code == 400

    # And without the agent certificate the route is what it always was
    resp = await unauth_client_session.post("/api/v1/enrollment/accept", json={"callsign": planned, "csr": wrong_csr})
    assert resp.status_code == 403

    # An enrollment a human started: not the agent's business.
    # A plain init hands the caller the new callsign's JWT as a session cookie, and JWTBearer
    # prefers that cookie over the Authorization header, so this client would stop being an admin.
    # Clean up after it here; not issuing it at all is exactly what the mdm form is for.
    human = f"mdmhuman_{secrets.token_hex(4)}"
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json={"callsign": human})
    assert resp.status_code == 200
    if tilauspalvelu_jwt_admin_client.cookie_jar is not None:
        tilauspalvelu_jwt_admin_client.cookie_jar.clear()
    human_csr = await _device_csr(tempdir, human, name="human")
    resp = await mdm_agent_client.post("/api/v1/enrollment/accept", json={"callsign": human, "csr": human_csr})
    assert resp.status_code == 403
    assert (await Enrollment.by_callsign(human)).csr is None


@pytest.mark.asyncio(loop_scope="session")
async def test_planning_many_devices_keeps_the_admin_session(
    tilauspalvelu_jwt_admin_client: TestClient,
) -> None:
    """Planning a fleet is one call per device and must not log the admin out on the first one

    A plain /enrollment/init issues the new callsign's JWT and sets it as the session cookie of
    whoever called it, and JWTBearer prefers that cookie over the Authorization header -- so the
    next call would arrive as a freshly created non-admin user. Devices planned for MDM get no JWT
    at all, nobody should be holding a device's credential anyway, so this stays an admin.
    """
    for _ in range(3):
        callsign = f"mdmfleet_{secrets.token_hex(4)}"
        resp = await tilauspalvelu_jwt_admin_client.post(
            "/api/v1/enrollment/init", json={"callsign": callsign, "mdm": True}
        )
        assert resp.status_code == 200
        assert resp.json()["jwt"] == ""


@pytest.mark.asyncio(loop_scope="session")
async def test_list_marks_devices_planned_for_mdm(tilauspalvelu_jwt_admin_client: TestClient) -> None:
    """An admin has to be able to tell a planned device from a person waiting for approval

    Both sit in the list in state PENDING, but a device is waiting for its own CSR through the
    agent and approving it by hand is refused, so without the marker the approve-users queue fills
    with rows nobody may act on.
    """
    device = f"mdmlisted_{secrets.token_hex(4)}"
    human = f"humanlisted_{secrets.token_hex(4)}"
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json={"callsign": device, "mdm": True})
    assert resp.status_code == 200
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json={"callsign": human})
    assert resp.status_code == 200
    # A plain init hands back the new callsign's JWT as a cookie, which would unseat the admin
    if tilauspalvelu_jwt_admin_client.cookie_jar is not None:
        tilauspalvelu_jwt_admin_client.cookie_jar.clear()

    listed = (await tilauspalvelu_jwt_admin_client.get("/api/v1/enrollment/list")).json()["callsign_list"]
    marks = {row["callsign"]: row["mdm"] for row in listed if row["callsign"] in (device, human)}
    assert marks == {device: True, human: False}


@pytest.mark.asyncio(loop_scope="session")
async def test_two_devices_cannot_both_claim_one_planned_callsign() -> None:
    """The clause the MVP plan will not sign off without

    A callsign is spent the moment it is used and can never be released, so if two devices both
    got past the claim one of them would receive a certificate for an identity the other also
    holds, and the loser could never be enrolled under any name it had been promised. The check
    and the write are one UPDATE for exactly this reason, so the guarantee is the database's and
    not a check-then-act in Python.
    """
    callsign = f"mdmrace_{secrets.token_hex(4)}"
    planned = await Enrollment.create_for_callsign(callsign=callsign, extra={"mdm": True})

    first, second = await asyncio.gather(
        (await Enrollment.by_callsign(callsign)).claim_with_csr("csr-from-device-one"),
        (await Enrollment.by_callsign(callsign)).claim_with_csr("csr-from-device-two"),
    )
    assert sorted([first, second]) == [False, True], "exactly one device may claim a planned callsign"

    settled = await Enrollment.by_callsign(callsign)
    assert settled.csr in ("csr-from-device-one", "csr-from-device-two")
    assert settled.state == EnrollmentState.PENDING, "claiming must not decide the enrollment"
    _ = planned


@pytest.mark.asyncio(loop_scope="session")
async def test_agent_cn_cannot_be_taken_as_a_callsign(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent CN is a service identity, not a name anyone may enroll under

    A certificate carrying it is accepted as the MDM agent on sight, with no Person, role or
    product check, so issuing one to a person would hand them every planned device's identity.
    Both creation paths have to refuse it, and case cannot be used to slip past: callsign lookups
    fold case, so a near-miss would be a confusing collision rather than a second identity.

    No database here on purpose -- the guard is meant to fire before anything is written.
    """
    settings = RMSettings.singleton()
    monkeypatch.setattr(settings, "mdm_agent_cns", f"{MDM_AGENT_CN},second-agent")

    for taken in (MDM_AGENT_CN, MDM_AGENT_CN.upper(), "second-agent"):
        with pytest.raises(CallsignReserved):
            await Enrollment.create_for_callsign(callsign=taken)
        with pytest.raises(CallsignReserved):
            await Person.create_with_cert(callsign=taken)
