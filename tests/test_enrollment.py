"""Test enrollment endpoint"""

import datetime
import logging
import re
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
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from fastapi import FastAPI
from libpvarki.mtlshelp.csr import async_create_client_csr, async_create_keypair

from rasenmaeher_api.db import (
    EngineWrapper,
    Enrollment,
    EnrollmentPool,
    MdmEnrolment,
    Person,
)
from rasenmaeher_api.db.errors import CallsignReserved, NotFound
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


@pytest_asyncio.fixture(scope="function")
async def mdm_challenge(mdm_agent_client: TestClient) -> str:
    """Open MDM enrolment for the test, and the challenge the agent passes on from the device"""
    _ = mdm_agent_client
    return (await (await MdmEnrolment.current()).open_for(1)).challenge


async def _device_csr(tempdir: Path, callsign: str, name: str = "device") -> str:
    """A CSR the way a device sends one through its MDM: its own key, the name the MDM gave it as the CN"""
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


async def _mdm_enrol(client: TestClient, callsign: str, csrpem: str | None, challenge: str | None) -> Any:
    body: dict[str, Any] = {"callsign": callsign, "challenge": challenge}
    if csrpem is not None:
        body["csr"] = csrpem
    return await client.post("/api/v1/enrollment/accept", json=body)


async def _no_person(callsign: str) -> bool:
    try:
        await Person.by_callsign(callsign, allow_deleted=True)
    except NotFound:
        return True
    return False


@pytest.mark.asyncio(loop_scope="session")
async def test_mdm_agent_enrols_a_device_under_its_mdm_name(
    mdm_agent_client: TestClient, mdm_challenge: str, nice_tmpdir: str
) -> None:
    """The whole agent path: the MDM names the device, and a repeat gets the same certificate"""
    tempdir = Path(nice_tmpdir)
    callsign = f"R58N{secrets.token_hex(4).upper()}"
    csrpem = await _device_csr(tempdir, callsign)
    resp = await _mdm_enrol(mdm_agent_client, callsign, csrpem, mdm_challenge)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    certpem = body["certificate"]

    # The certificate must be for the key the device holds. If this ever regresses, rasenmaeher
    # generated a keypair of its own and the device received a certificate it cannot use.
    assert _public_key_der(certpem) == _public_key_der(csrpem)
    # The mTLS edge authorises on the CN it reads off the certificate: exactly one, the MDM's name
    issued = x509.load_pem_x509_certificate(certpem.encode("utf-8"))
    assert [attr.value for attr in issued.subject.get_attributes_for_oid(NameOID.COMMON_NAME)] == [callsign]
    person = await Person.by_callsign(callsign)
    assert person.extra == {"mdm": True}, "the admin UI lists devices by this mark"

    # The reply can be lost on the way back to the MDM, which then repeats the request verbatim
    resp = await _mdm_enrol(mdm_agent_client, callsign, csrpem, mdm_challenge)
    assert resp.status_code == 200
    assert resp.json()["certificate"] == certpem

    # ...but a different key for the same name is somebody else
    other_csr = await _device_csr(tempdir, callsign, name="imposter")
    resp = await _mdm_enrol(mdm_agent_client, callsign, other_csr, mdm_challenge)
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_mdm_agent_refusals(
    tilauspalvelu_jwt_admin_client: TestClient,
    mdm_agent_client: TestClient,
    mdm_challenge: str,
    unauth_client_session: TestClient,
    nice_tmpdir: str,
) -> None:
    """What the agent may not do"""
    tempdir = Path(nice_tmpdir)

    # A request whose CN is not the name being enrolled
    name = f"mdmmismatch{secrets.token_hex(4)}"
    wrong_csr = await _device_csr(tempdir, f"{name}X", name="mismatch")
    resp = await _mdm_enrol(mdm_agent_client, name, wrong_csr, mdm_challenge)
    assert resp.status_code == 403
    assert await _no_person(name)

    # No CSR at all
    resp = await _mdm_enrol(mdm_agent_client, name, None, mdm_challenge)
    assert resp.status_code == 400

    # And without the agent certificate the route is what it always was
    resp = await unauth_client_session.post("/api/v1/enrollment/accept", json={"callsign": name, "csr": wrong_csr})
    assert resp.status_code == 403

    # A name a person is waiting for an admin under.
    # A plain init hands the caller the new callsign's JWT as a session cookie, and JWTBearer
    # prefers that cookie over the Authorization header, so this client would stop being an admin.
    human = f"mdmhuman{secrets.token_hex(4)}"
    resp = await tilauspalvelu_jwt_admin_client.post("/api/v1/enrollment/init", json={"callsign": human})
    assert resp.status_code == 200
    if tilauspalvelu_jwt_admin_client.cookie_jar is not None:
        tilauspalvelu_jwt_admin_client.cookie_jar.clear()
    resp = await _mdm_enrol(mdm_agent_client, human, await _device_csr(tempdir, human, name="human"), mdm_challenge)
    assert resp.status_code == 403
    assert await _no_person(human)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "name", ["KÄRPPÄ1", "AB", "A" * 33, "-OTTER1", "OTTER1-", "OTTER_1", "fake.localmaeher.dev.pvarki.fi"]
)
async def test_mdm_agent_refuses_a_name_not_every_product_takes(
    mdm_agent_client: TestClient, mdm_challenge: str, nice_tmpdir: str, name: str
) -> None:
    """The MDM's name becomes the callsign everywhere, so it has to be one every product takes"""
    resp = await _mdm_enrol(mdm_agent_client, name, await _device_csr(Path(nice_tmpdir), name), mdm_challenge)
    assert resp.status_code == 403
    assert await _no_person(name)


@pytest.mark.asyncio(loop_scope="session")
async def test_mdm_agent_takes_a_work_profile_enrollment_id(
    mdm_agent_client: TestClient, mdm_challenge: str, nice_tmpdir: str
) -> None:
    """A work-profile phone reports no serial, only a 32-character hyphenated enrollment-specific ID"""
    raw = secrets.token_hex(14).upper()
    name = "-".join([raw[0:4], raw[4:8], raw[8:12], raw[12:17], raw[17:21], raw[21:25], raw[25:26]])
    assert len(name) == 32
    resp = await _mdm_enrol(
        mdm_agent_client, name, await _device_csr(Path(nice_tmpdir), name, name="esid"), mdm_challenge
    )
    assert resp.status_code == 200, resp.text
    assert (await Person.by_callsign(name)).extra == {"mdm": True}


@pytest.mark.asyncio(loop_scope="session")
async def test_the_enrolment_window_and_challenge_gate_the_agent(
    mdm_agent_client: TestClient, mdm_challenge: str, nice_tmpdir: str
) -> None:
    """A request that would otherwise succeed is refused while closed or with the wrong challenge

    And it creates nothing, so the device can still enrol once the operator opens the window.
    """
    callsign = f"mdmwindow{secrets.token_hex(4)}"
    csrpem = await _device_csr(Path(nice_tmpdir), callsign, name="window")

    for wrong in (None, "", "0" * 32, f"{mdm_challenge}x"):
        resp = await _mdm_enrol(mdm_agent_client, callsign, csrpem, wrong)
        assert resp.status_code == 403, f"challenge {wrong!r} must be refused"

    await (await MdmEnrolment.current()).open_for(0)
    resp = await _mdm_enrol(mdm_agent_client, callsign, csrpem, mdm_challenge)
    assert resp.status_code == 403, "a closed window must refuse even a correct request"
    assert await _no_person(callsign)

    await (await MdmEnrolment.current()).open_for(1)
    resp = await _mdm_enrol(mdm_agent_client, callsign, csrpem, mdm_challenge)
    assert resp.status_code == 200, resp.text


def test_the_enrolment_window_closes_itself() -> None:
    """Nobody has to remember to close it"""
    now = datetime.datetime.now(datetime.UTC)
    assert MdmEnrolment(challenge="c", open_until=now + datetime.timedelta(minutes=1)).is_open
    assert not MdmEnrolment(challenge="c", open_until=now - datetime.timedelta(seconds=1)).is_open
    assert not MdmEnrolment(challenge="c").is_open


@pytest.mark.asyncio(loop_scope="session")
async def test_an_admin_opens_and_closes_mdm_enrolment(
    tilauspalvelu_jwt_admin_client: TestClient, tilauspalvelu_jwt_user_client: TestClient, app_instance: FastAPI
) -> None:
    """The operator's switch, with the challenge to configure the MDM with"""
    url = "/api/v1/enrollment/mdm-settings"
    resp = await tilauspalvelu_jwt_admin_client.put(url, json={"hours": 0})
    assert resp.status_code == 200
    closed = resp.json()
    assert closed["open_until"] is None
    assert re.fullmatch(r"[0-9a-f]{32}", closed["challenge"])
    assert closed["scep_url"].endswith("/scep")

    resp = await tilauspalvelu_jwt_admin_client.put(url, json={"hours": 24})
    assert resp.status_code == 200
    left = datetime.datetime.fromisoformat(resp.json()["open_until"]) - datetime.datetime.now(datetime.UTC)
    assert datetime.timedelta(hours=23, minutes=59) < left <= datetime.timedelta(hours=24)

    opened = (await tilauspalvelu_jwt_admin_client.get(url)).json()
    assert opened["challenge"] == closed["challenge"], "reopening must not mean reconfiguring the MDM"
    assert opened["open_until"]

    assert (await tilauspalvelu_jwt_admin_client.put(url, json={"hours": 169})).status_code == 422
    assert (await tilauspalvelu_jwt_user_client.get(url)).status_code == 403
    assert (await tilauspalvelu_jwt_user_client.put(url, json={"hours": 24})).status_code == 403
    # A product passes the admin check without being a person; switching enrolment is not its call
    async with TestClient(app_instance) as product:
        product.headers.update({"X-ClientCert-DN": "CN=fake.localmaeher.dev.pvarki.fi,O=N/A"})
        assert (await product.put(url, json={"hours": 24})).status_code == 403
        assert (await product.get(url)).status_code == 403

    assert (await tilauspalvelu_jwt_admin_client.put(url, json={"hours": 0})).json()["open_until"] is None


@pytest.mark.asyncio(loop_scope="session")
async def test_agent_cn_cannot_be_taken_as_a_callsign(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent CN is a service identity, not a name anyone may enroll under

    A certificate carrying it is accepted as the MDM agent on sight, with no Person, role or
    product check, so issuing one to a person would let them enrol devices.
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


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("service_cn", ["rasenmaeher", "RASENMAEHER", "Rasenmaeher"])
async def test_the_service_cn_cannot_be_taken_in_any_case(service_cn: str) -> None:
    """Keycloak and Matrix lowercase the name, so RASENMAEHER downstream is rasenmaeher

    No database here on purpose -- the guard is meant to fire before anything is written.
    """
    assert RMSettings.singleton().mtls_client_cert_cn == "rasenmaeher"
    with pytest.raises(CallsignReserved):
        await Enrollment.create_for_callsign(callsign=service_cn)
    with pytest.raises(CallsignReserved):
        await Person.create_with_cert(callsign=service_cn)


def _csr_asking_for(callsign: str, **extensions: Any) -> str:
    """A device request that asks for more than a device identity"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, callsign)])
    )
    if extensions.get("server_auth"):
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False
        )
    if extensions.get("san"):
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(str(extensions["san"]))]), critical=False
        )
    if extensions.get("ca"):
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.mark.asyncio(loop_scope="session")
async def test_a_device_request_may_not_choose_what_it_is_issued(
    mdm_agent_client: TestClient, mdm_challenge: str
) -> None:
    """The signer picks its profile from what the request asks for

    So a request asking for server authentication is issued one, and nothing replaces the names it
    carries. On this path the request arrived from the public SCEP endpoint, where its contents are
    entirely the caller's choice, and every device in the deployment trusts this CA. A genuine MDM
    device request asks for none of it.
    """
    for label, kwargs in (
        ("server_auth", {"server_auth": True}),
        ("san", {"san": "evil.example"}),
        ("ca", {"ca": True}),
    ):
        callsign = f"mdmoverreach{secrets.token_hex(4)}"
        resp = await _mdm_enrol(mdm_agent_client, callsign, _csr_asking_for(callsign, **kwargs), mdm_challenge)
        assert resp.status_code == 403, f"{label} must be refused"
        assert await _no_person(callsign), f"{label} must not spend the name"
