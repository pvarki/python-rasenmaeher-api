"""Enrollment API views."""  # pylint: disable=too-many-lines
import string
import random
import logging
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Request, Body, Depends, HTTPException
from multikeyjwt import Issuer
from rasenmaeher_api.web.api.enrollment.schema import (
    EnrollmentConfigTaskDone,
    EnrollmentStatusIn,
    EnrollmentStatusOut,
    EnrollmentAcceptIn,
    EnrollmentAcceptOut,
    EnrollmentAddServiceManagementIn,
    EnrollmentConfigSetDLCertIn,
    EnrollmentConfigSetStateIn,
    EnrollmentConfigSetMtlsIn,
    EnrollmentGenVerifiOut,
    EnrollmentShowVerificationCodeIn,
    EnrollmentShowVerificationCodeOut,
    EnrollmentHaveIBeenAcceptedOut,
    EnrollmentListOut,
    EnrollmentPromoteIn,
    EnrollmentInitIn,
    EnrollmentInitOut,
    EnrollmentDeliverIn,
    EnrollmentDeliverOut,
    EnrollmentDemoteIn,
    EnrollmentLockIn,
    EnrollmentIsInvitecodeActiveIn,
    EnrollmentIsInvitecodeActiveOut,
    EnrollmentInviteCodeCreateOut,
    EnrollmentInviteCodeEnrollIn,
    EnrollmentInviteCodeActivateOut,
    EnrollmentInviteCodeActivateIn,
    EnrollmentInviteCodeDeactivateOut,
    EnrollmentInviteCodeDeactivateIn,
    EnrollmentInviteCodeDeleteOut,
)
from ..middleware import MTLSorJWT
from ....settings import settings
from ....sqlitedatabase import sqlite

from ....db import Person

LOGGER = logging.getLogger(__name__)

ENROLLMENT_ROUTER = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])
NO_JWT_ENROLLMENT_ROUTER = APIRouter()


async def check_management_permissions(
    raise_exeption: bool = False,
    management_hash: str = "",
    work_id: str = "",
    special_rule: str = "",
    hash_like: bool = False,
) -> Union[bool, None]:
    """
    Simple function to check if requester has admin permissions. Use hash_like to use LIKE instead of =.
    """
    # TODO check permissions in new orm, now it passes everything...
    if management_hash != "asddasdsaadsasdsad":
        return True
    # If management hash is not provided, try to use one pro
    if management_hash == "" and work_id == "":
        _reason = "Error. check_management_permissions() both work_id and management_hash are empty"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=400, detail=_reason)
    if management_hash == "":
        management_hash = await get_hash_with_either_workid_or_hash(
            raise_exeption=True, work_id=work_id, work_id_hash=None
        )

    # Get special_rules='first-user from managment
    if hash_like is True:
        _q = settings.sqlite_sel_from_management_where_hash_like_and_special_rule.format(
            special_rules=special_rule, management_hash=management_hash
        )
    else:
        _q = settings.sqlite_sel_from_management_where_hash_and_special_rule_like.format(
            special_rules=special_rule, management_hash=management_hash
        )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_sssfmwhasrl1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)

    if special_rule == "invite-code" and len(_result) >= 1:
        return True

    if len(_result) > 0:
        return True

    if raise_exeption is True:
        _reason = "Error. Given userid doesn't have enough permissions."
        LOGGER.error(
            "Missing permissions! User id/hash : {}, required permissions that are missing {}".format(
                management_hash, special_rule
            )
        )
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=403, detail=_reason)

    return False


async def update_management_hash_permissions(management_hash: str, special_rule: str, active: bool) -> None:
    """
    Update the active status of a management hash in the management table
    """

    # convert bool to int
    if active is True:
        active_int = 1
    else:
        active_int = 0

    _q = settings.sqlite_update_management_state.format(
        management_hash=management_hash, special_rules=special_rule, active=active_int
    )
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error q_ssumha1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)


async def update_invite_code_state(invite_code: str, active: bool) -> None:
    """
    Update the active status of a invite-code in the management table
    """

    # convert bool to int
    if active is True:
        active_int = 1
    else:
        active_int = 0

    _q = settings.update_management_hash_like.format(
        management_hash=invite_code, special_rules="invite-code", active=active_int
    )
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error q_ssumha1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)


async def is_workid_or_workidhash_given(
    raise_exeption: bool = True, work_id: Optional[str] = None, work_id_hash: Optional[str] = None
) -> bool:
    """
    Simple function to check if either work_id or work_id_hash has been given.
    """

    if work_id == "":
        work_id = None

    if work_id_hash == "":
        work_id_hash = None

    if work_id is None and work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined or empty. At least one is required"
        LOGGER.error(_reason)
        if raise_exeption:
            raise HTTPException(status_code=400, detail=_reason)
        return False

    return True


async def get_hash_with_either_workid_or_hash(
    raise_exeption: bool = True, work_id: Optional[str] = None, work_id_hash: Optional[str] = None
) -> str:
    """
    Simple function to get/check the work_id_hash and return it as str.
    """
    if work_id == "":
        work_id = None
    if work_id_hash == "":
        work_id_hash = None

    if work_id_hash is not None:
        _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=work_id_hash)
    else:
        _q = settings.sqlite_sel_from_enrollment.format(work_id=work_id)

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error func_ssfewhx24"
        LOGGER.error(_reason)
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) > 1:
        _reason = "Error. Dafug, more than one hit in results..."
        LOGGER.error(_reason)
        LOGGER.error(_result)
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Wont do. Requested work_id or work_id_hash not found..."
        LOGGER.error(_reason)
        if raise_exeption:
            raise HTTPException(status_code=404, detail=_reason)

        return ""

    return str(_result[0][1])


async def delete_invite_code_like(invite_code: str) -> bool:
    """
    Delete invite code like
    """

    _q = settings.sqlite_del_from_management_where_hash_like.format(
        management_hash=invite_code, special_rules="invite-code"
    )
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error q_ssumha1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)

    return True


@ENROLLMENT_ROUTER.post("/generate-verification-code", response_model=EnrollmentGenVerifiOut)
async def post_generate_verification_code(
    request: Request,
) -> EnrollmentGenVerifiOut:
    """
    Update/Generate verification_code to database for given jwt/mtls
    """
    # _obj = Person()
    # _verification_code = await _obj.set_verification_code(callsign=request.state.mtls_or_jwt.userid)
    _verification_code = await Person.set_verification_code(callsign=request.state.mtls_or_jwt.userid)
    return EnrollmentGenVerifiOut(verification_code=f"{_verification_code}")


@ENROLLMENT_ROUTER.get("/show-verification-code-info", response_model=EnrollmentShowVerificationCodeOut)
async def request_show_verification_code(
    request: Request,
    params: EnrollmentShowVerificationCodeIn = Depends(),
) -> EnrollmentShowVerificationCodeOut:
    """
    /show-verification-code-info?verification_code=jaddajaa
    Return's information about the user/enrollment that made the code.
    """

    if params.verification_code in ("na", ""):
        _reason = "Verification code cannot be empty or na"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    # TODO
    _obj = await Person.by_verification_code(verification_code=params.verification_code)

    _callsign = _obj.callsign

    return EnrollmentShowVerificationCodeOut(
        work_id=_callsign,
        work_id_hash="REMOVE_ME",
        state="GET_ME_FROM_ENROLLMENT",
        accepted="GET_ME_FROM_ENROLLMENT",
        locked="GET_ME_FROM_ENROLLMENT",
    )


@ENROLLMENT_ROUTER.get("/have-i-been-accepted", response_model=EnrollmentHaveIBeenAcceptedOut)
async def request_have_i_been_accepted(
    request: Request,
) -> EnrollmentHaveIBeenAcceptedOut:
    """
    /have-i-been-accepted
    Return's True/False in 'have_i_been_accepted'
    """

    _user_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, work_id_hash=None
    )

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=_user_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_sssfewh2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if _result[0][3] != "":
        return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=True)

    return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=False)


@ENROLLMENT_ROUTER.post("/config/set-state", response_model=EnrollmentConfigTaskDone)
async def post_config_set_state(
    request: Request,
    request_in: EnrollmentConfigSetStateIn = Body(
        None,
        examples=[EnrollmentConfigSetStateIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    Update/Set state/status for work_id/user/enrollment using either work_id_hash or work_id.
    """

    await is_workid_or_workidhash_given(raise_exeption=True, work_id=request_in.work_id, work_id_hash=None)

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    _q = settings.sqlite_update_enrollment_state.format(
        work_id=request_in.work_id, work_id_hash=None, state=request_in.state
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssues1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)
    return EnrollmentConfigTaskDone(success_message="State was set")


# mtls_test_link
@ENROLLMENT_ROUTER.post("/config/set-mtls-test-link", response_model=EnrollmentConfigTaskDone)
async def post_config_set_mtls_test_link(
    request: Request,
    request_in: EnrollmentConfigSetMtlsIn = Body(
        None,
        examples=[EnrollmentConfigSetMtlsIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    Set MTLS test link for one or all work_id's
    """
    if request_in.set_for_all is False and request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required when \
'set_for_all' is set to False"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    if request_in.set_for_all is True:
        _q = settings.sqlite_update_enrollment_mtls_test_link_all.format(mtls_test_link=request_in.mtls_test_link)
        _success, _result = sqlite.run_command(_q)
    else:
        _work_id_hash = await get_hash_with_either_workid_or_hash(
            raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
        )

        _q = settings.sqlite_update_enrollment_mtls_test_link.format(
            work_id_hash=_work_id_hash, mtls_test_link=request_in.mtls_test_link
        )
        _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssuemtl1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigTaskDone(success_message="Test link was set")


@ENROLLMENT_ROUTER.post("/config/set-cert-dl-link", response_model=EnrollmentConfigTaskDone)
async def post_config_set_cert_dl_link(
    request: Request,
    request_in: EnrollmentConfigSetDLCertIn = Body(
        None,
        examples=[EnrollmentConfigSetDLCertIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    Store certificate or howto download link url for work_id (enrollment) using either work_id or work_id_hash
    """
    LOGGER.error("asdasd {} ".format(request.state.mtls_or_jwt.userid))
    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    await is_workid_or_workidhash_given(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    if request_in.cert_download_link is None and request_in.howto_download_link is None:
        _reason = "Error. Both cert_download_link and howto_download_link are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _work_id_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _admin_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, work_id_hash=None
    )

    await check_management_permissions(raise_exeption=True, management_hash=_admin_hash)

    _success: bool = True
    if request_in.cert_download_link is not None:
        _q = settings.sqlite_update_enrollment_cert_dl_link.format(
            work_id_hash=_work_id_hash,
            cert_download_link=request_in.cert_download_link,
        )
        _success, _result = sqlite.run_command(_q)

    _success2: bool = True
    if request_in.howto_download_link is not None:
        _q = settings.sqlite_update_enrollment_cert_howto_dl_link.format(
            work_id_hash=_work_id_hash,
            howto_download_link=request_in.howto_download_link,
        )
        _success2, _result = sqlite.run_command(_q)

    if _success is False or _success2 is False:
        _reason = "Error. Undefined backend error q_ssuecdll1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigTaskDone(success_message="Cert DL link was set")


@ENROLLMENT_ROUTER.post("/config/add-service-management-hash", response_model=EnrollmentConfigTaskDone)
async def post_config_add_manager(
    request: Request,
    request_in: EnrollmentAddServiceManagementIn = Body(
        None,
        examples=[EnrollmentAddServiceManagementIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    Add new "management hash" with certain permissions. This is not same as users/work-id's promotion to admin.
    You should think this as of adding "machine admin permissions". User related admin promotions should
    be done using /promote and /demote /lock.
    """
    # TODO, REFAK, SERVICE's SHOULD BE ADDES AS enrollments and added then special permissions if needed...
    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    if len(request_in.new_service_management_hash) < 64:
        _reason = "Error. new_service_management_hash too short. Needs to be 64 or more."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _q = settings.sqlite_insert_into_management.format(
        management_hash=request_in.new_service_management_hash, special_rules=request_in.permissions_str, active=1
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssiim1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigTaskDone(success_message="Service management hash added")


@ENROLLMENT_ROUTER.get("/status", response_model=EnrollmentStatusOut)
async def request_enrolment_status(
    request: Request,
    params: EnrollmentStatusIn = Depends(),
) -> EnrollmentStatusOut:
    """
    Check the status for given work_id (enrollment). status=None means that there is no enrollment with given work_id
    """

    _q = settings.sqlite_sel_from_enrollment.format(work_id=params.work_id)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfe3"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) > 0:
        _status: str = _result[0][2]
        _work_id_hash: str = _result[0][1]
    else:
        _status = "none"
        _work_id_hash = "none"

    if _success is False:
        _reason = "Error. Undefined backend error sssfe2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentStatusOut(work_id=params.work_id, work_id_hash=_work_id_hash, status=_status)


@ENROLLMENT_ROUTER.get("/list", response_model=EnrollmentListOut)
async def request_enrollment_list(
    request: Request,
) -> EnrollmentListOut:
    """
    /list
    Return users/work-id's/enrollments. If 'accepted' has something else than '', it has been accepted.
    Returns a list of dicts, work_id_list = [ {  "work_id":'x', 'work_id_hash':'yy', 'state':'init', 'accepted':'' } ]
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    _q = settings.sqlite_sel_from_enrollment_all.format()
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfea1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    LOGGER.info(_result)
    if len(_result) == 0:
        return EnrollmentListOut(work_id_list=[], success=True, reason="")

    _work_id_list: List[Dict[Any, Any]] = []
    for _id in _result:
        _work_id_list.append({"work_id": _id[0], "work_id_hash": _id[1], "state": _id[2], "accepted": _id[3]})

    return EnrollmentListOut(work_id_list=_work_id_list)


@ENROLLMENT_ROUTER.post("/init", response_model=EnrollmentInitOut)
async def request_enrollment_init(
    request: Request,
    request_in: EnrollmentInitIn = Body(
        None,
        examples=[EnrollmentInitIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentInitOut:
    """
    Add new work_id (enrollment) to environment.
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    # First check if there is already enrollment for requested workid
    _q = settings.sqlite_sel_from_enrollment.format(work_id=request_in.work_id)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error sssfe1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Skip enrollment if work_id already used
    if len(_result) > 0:
        _reason = "Error. work_id has already active enrollment"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _work_id_hash = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(64)
        ]
    )

    _q = settings.sqlite_insert_into_enrollment.format(
        work_id=request_in.work_id,
        work_id_hash=_work_id_hash,
        state="init",
        accepted="",
        cert_dl_link="na",
        cert_howto_dl_link="na",
        mtls_test_link="na",
        verification_code="na",
        locked="",
    )

    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssiie1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentInitOut(work_id=request_in.work_id, work_id_hash=_work_id_hash, jwt="")


@ENROLLMENT_ROUTER.post("/promote", response_model=EnrollmentConfigTaskDone)
async def request_enrollment_promote(
    request: Request,
    request_in: EnrollmentPromoteIn = Body(
        None,
        examples=[EnrollmentPromoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    "Promote" work_id/user/enrollment to have 'admin' rights
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    await is_workid_or_workidhash_given(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _work_id_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    # Check if the hash is already in database.
    _q = settings.sqlite_sel_from_management.format(management_hash=_work_id_hash)
    _success2, _result2 = sqlite.run_command(_q)
    if _success2 is False:
        _reason = "Error. Undefined backend error sssfm3"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result2) > 0:
        if "enrollment" in _result2[0][1]:
            _reason = "Given work_id already has elevated permissions."
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=400, detail=_reason)

        _q = settings.sqlite_update_management_rules.format(
            special_rules=f"{_result2[0][1]}:enrollment", management_hash=_result2[0][0]
        )
        _success, _result = sqlite.run_command(_q)
        if _success is False:
            _reason = "Error. Undefined backend error qsumr1"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

    else:
        _q = settings.sqlite_insert_into_management.format(
            management_hash=_work_id_hash, special_rules="enrollment", active=1
        )
        _success, _result = sqlite.run_command(_q)

        if _success is False:
            _reason = "Error. Undefined backend error qssiim2"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigTaskDone(success_message="Promote done")


@ENROLLMENT_ROUTER.post("/demote", response_model=EnrollmentConfigTaskDone)
async def request_enrollment_demote(
    request: Request,
    request_in: EnrollmentDemoteIn = Body(
        None,
        examples=[EnrollmentDemoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    "Demote" work_id/user/enrollment from having 'admin' rights. work_id_hash can be used too.
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )
    await is_workid_or_workidhash_given(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _work_id_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    # Check if the hash is already in database.
    _q = settings.sqlite_sel_from_management.format(management_hash=_work_id_hash)
    _success2, _result2 = sqlite.run_command(_q)
    if _success2 is False:
        _reason = "Error. Undefined backend error sssfm4"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result2) > 0:
        _reason = "Given work_id/work_id_hash doesn't have any privileges to take away. Skipping..."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    if "enrollment" not in _result2[0][1]:
        _reason = "Given work_id/work_id_hash doesn't have 'enrollment' privileges to take away. Skipping..."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # If the updated _new_rules is empty. Remove the whole hash from db
    _new_rules: str = _result2[0][1].replace("enrollment", "").replace("::", ":")
    if _new_rules == "":
        _q = settings.sqlite_del_from_management_where_hash.format(management_hash=_result2[0][0])
        _success, _result = sqlite.run_command(_q)

        if _success is False:
            _reason = "Error. Undefined backend error qssdfmwhs1"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

    else:
        _q = settings.sqlite_update_management_rules.format(special_rules=_new_rules, management_hash=_result2[0][0])
        _success, _result = sqlite.run_command(_q)
        if _success is False:
            _reason = "Error. Undefined backend error qsumr2"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigTaskDone(success_message="Demote done")


@ENROLLMENT_ROUTER.post("/lock", response_model=EnrollmentConfigTaskDone)
async def request_enrollment_lock(
    request: Request,
    request_in: EnrollmentLockIn = Body(
        None,
        examples=[EnrollmentLockIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    Lock work_id/user/enrollment so it cannot be used anymore.
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )
    await is_workid_or_workidhash_given(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _work_id_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    if request_in.lock_reason == "":
        _reason = "lock_reason cannot be empty."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _q = settings.sqlite_update_enrollment_locked_state.format(
        work_id_hash=_work_id_hash, locked=request_in.lock_reason
    )
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error qsuels1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigTaskDone(success_message="Lock task done")


@ENROLLMENT_ROUTER.get("/deliver", response_model=EnrollmentDeliverOut)
async def request_enrollment_status(
    request: Request,
    params: EnrollmentDeliverIn = Depends(),
) -> EnrollmentDeliverOut:
    """
    Deliver download url link using work_id_hash
    """

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=params.work_id_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_sssfewh1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'work_id_hash' not found from database."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=404, detail=_reason)

    if _result[0][2] != "ReadyForDelivery":
        _reason = "Enrollment is still in progress or it hasn't been accepted."
        LOGGER.info("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=202, detail=_reason)

    return EnrollmentDeliverOut(
        work_id=_result[0][0],
        work_id_hash=params.work_id_hash,
        cert_download_link=_result[0][4],
        howto_download_link=_result[0][5],
        mtls_test_link=_result[0][6],
    )


@ENROLLMENT_ROUTER.post("/accept", response_model=EnrollmentAcceptOut)
async def post_enrollment_accept(
    request: Request,
    request_in: EnrollmentAcceptIn = Body(
        None,
        examples=[EnrollmentAcceptIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentAcceptOut:
    """
    Accept work_id_hash (work_id/enrollment)
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=request_in.work_id_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfewh1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'work_id_hash' not found from database."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=404, detail=_reason)

    _admin_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, work_id_hash=None
    )

    _q = settings.sqlite_update_accept_enrollment.format(
        management_hash=_admin_hash, work_id_hash=request_in.work_id_hash
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssuae1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentAcceptOut(work_id_hash=request_in.work_id_hash)


@ENROLLMENT_ROUTER.post("/invitecode/create", response_model=EnrollmentInviteCodeCreateOut)
async def post_invite_code(
    request: Request,
) -> EnrollmentInviteCodeCreateOut:
    """
    Create a new invite code using user_management_hash
    This method checks for permission user-admin
    This method checks for existing invite code and updates it if found
    This method creates invite code if not found
    """

    # Veriy that the user has permissions to create invite codes ??? is user-admin
    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid, special_rule=""
    )

    _admin_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, work_id_hash=None
    )

    # Check does the user have existing invite code that matches their management hash
    _existing_invite_code = await check_management_permissions(
        raise_exeption=False,
        management_hash=_admin_hash,
        special_rule="invite-code",
        hash_like=True,
    )

    # Random string for invite-code eg. GLXBT0
    _invite_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))  # nosec B311
    # Update existing code if existing LIKE management_hash and invite-code
    if _existing_invite_code:
        _q = settings.sqlite_update_from_management_where_management_like.format(
            special_rules="invite-code",
            new_management_hash=f"{_admin_hash}_{_invite_code}",
            management_hash=_admin_hash,
        )
        _success, _result = sqlite.run_command(_q)

    else:
        # Create a new invite code for management_hash_GLXBT0
        _q = settings.sqlite_insert_into_management.format(
            management_hash=f"{_admin_hash}_{_invite_code}", special_rules="invite-code", active=1
        )
        _success, _result = sqlite.run_command(_q)

    return EnrollmentInviteCodeCreateOut(invite_code=f"{_invite_code}")


@ENROLLMENT_ROUTER.put("/invitecode/activate", response_model=EnrollmentInviteCodeActivateOut)
async def put_activate_invite_code(
    request: Request,
    request_in: EnrollmentInviteCodeActivateIn = Body(
        None,
        examples=EnrollmentInviteCodeActivateIn.Config.schema_extra["examples"],
    ),
) -> EnrollmentInviteCodeActivateOut:
    """
    Activate an invite code
    """

    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid, special_rule="enrollment"
    )

    # Check if there is an invite code matching the one in request
    _existing_invite_code = await check_management_permissions(
        raise_exeption=True, management_hash=request_in.invite_code, special_rule="invite-code", hash_like=True
    )

    if _existing_invite_code is False:
        raise HTTPException(status_code=404, detail="Invite code not found or deactivated")

    _q = settings.sqlite_sel_from_management_where_hash_like.format(management_hash=request_in.invite_code)
    _success2, _result2 = sqlite.run_command(_q)

    # Activate the invite code
    await update_invite_code_state(invite_code=request_in.invite_code, active=True)

    return EnrollmentInviteCodeActivateOut(invite_code=request_in.invite_code)


@ENROLLMENT_ROUTER.put("/invitecode/deactivate", response_model=EnrollmentInviteCodeDeactivateOut)
async def put_deactivate_invite_code(
    request: Request,
    request_in: EnrollmentInviteCodeDeactivateIn = Body(
        None,
        examples=EnrollmentInviteCodeDeactivateIn.Config.schema_extra["examples"],
    ),
) -> EnrollmentInviteCodeDeactivateOut:
    """
    Deactivate an invite code
    """
    # Check requester permissions
    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    # Check if there is an invite code matching the one in request
    _existing_invite_code = await check_management_permissions(
        raise_exeption=True, management_hash=request_in.invite_code, special_rule="invite-code", hash_like=True
    )

    if _existing_invite_code is False:
        raise HTTPException(status_code=404, detail="Invite code not found or deactivated")

    _q = settings.sqlite_sel_from_management_where_hash_like.format(management_hash=request_in.invite_code)
    _success2, _result2 = sqlite.run_command(_q)

    # Deactivate the invite code
    await update_invite_code_state(invite_code=request_in.invite_code, active=False)

    return EnrollmentInviteCodeDeactivateOut(invite_code=request_in.invite_code)


@ENROLLMENT_ROUTER.delete("/invitecode/{invite_code}", response_model=EnrollmentInviteCodeDeleteOut)
async def delete_invite_code(
    request: Request,
    invite_code: str,
) -> EnrollmentInviteCodeDeleteOut:
    """
    Delete an invite code
    """
    # Check requester permissions
    await check_management_permissions(
        raise_exeption=True, management_hash="", work_id=request.state.mtls_or_jwt.userid
    )

    # Check if there is an invite code matching the one in request
    _existing_invite_code = await check_management_permissions(
        raise_exeption=False, management_hash=invite_code, special_rule="invite-code", hash_like=True
    )

    if _existing_invite_code is False:
        raise HTTPException(status_code=404, detail="Invite code not found")

    # Delete the invite code
    await delete_invite_code_like(invite_code=invite_code)

    return EnrollmentInviteCodeDeleteOut(invite_code=invite_code)


@NO_JWT_ENROLLMENT_ROUTER.get("/invitecode", response_model=EnrollmentIsInvitecodeActiveOut)
async def get_invite_codes(
    params: EnrollmentIsInvitecodeActiveIn = Depends(),
) -> EnrollmentIsInvitecodeActiveOut:
    """
    /invitecode?invitecode=xxx
    Returns true/false if the code is usable or not
    """

    # Check if there is a invite code matching the one in request
    _existing_invite_code = await check_management_permissions(
        raise_exeption=False, management_hash=params.invitecode, special_rule="invite-code", hash_like=True
    )

    if _existing_invite_code is False:
        return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=False)

    return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=True)


@NO_JWT_ENROLLMENT_ROUTER.post("/invitecode/enroll", response_model=EnrollmentInitOut)
async def post_enroll_invite_code(
    request: Request,
    request_in: EnrollmentInviteCodeEnrollIn = Body(
        None,
        examples=EnrollmentInviteCodeEnrollIn.Config.schema_extra["examples"],
    ),
) -> EnrollmentInitOut:
    """
    Enroll with an invite code
    """

    # Check if there is a invite code matching the one in request
    _existing_invite_code = await check_management_permissions(
        raise_exeption=False, management_hash=request_in.invite_code, special_rule="invite-code", hash_like=True
    )

    if _existing_invite_code is False:
        _reason = "Error. invitecode not valid."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # First check if there is already enrollment for requested workid
    _q = settings.sqlite_sel_from_enrollment.format(work_id=request_in.work_id)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error sssfe1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Skip enrollment if work_id already used
    if len(_result) > 0:
        _reason = "Error. work_id has already active enrollment"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _work_id_hash = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(64)
        ]
    )

    _q = settings.sqlite_insert_into_enrollment.format(
        work_id=request_in.work_id,
        work_id_hash=_work_id_hash,
        state="init",
        accepted="",
        cert_dl_link="na",
        cert_howto_dl_link="na",
        mtls_test_link="na",
        verification_code="na",
        locked="",
    )

    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssiie1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Create JWT token for user
    _claims = {"sub": request_in.work_id}
    _new_jwt = Issuer.singleton().issue(_claims)

    return EnrollmentInitOut(work_id=request_in.work_id, work_id_hash=_work_id_hash, jwt=_new_jwt)
