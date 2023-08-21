"""Enrollment API views."""
import string
import random
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Request, Body, Depends, HTTPException
from rasenmaeher_api.web.api.enrollment.schema import (
    EnrollmentStatusIn,
    EnrollmentStatusOut,
    EnrollmentAcceptIn,
    EnrollmentAcceptOut,
    EnrollmentAddServiceManagementOut,
    EnrollmentAddServiceManagementIn,
    EnrollmentConfigSetDLCertOut,
    EnrollmentConfigSetDLCertIn,
    EnrollmentConfigSetStateOut,
    EnrollmentConfigSetStateIn,
    EnrollmentConfigSetMtlsIn,
    EnrollmentConfigSetMtlsOut,
    EnrollmentGenVerifiIn,
    EnrollmentGenVerifiOut,
    EnrollmentShowVerificationCodeIn,
    EnrollmentShowVerificationCodeOut,
    EnrollmentHaveIBeenAcceptedIn,
    EnrollmentHaveIBeenAcceptedOut,
    EnrollmentListIn,
    EnrollmentListOut,
    EnrollmentPromoteIn,
    EnrollmentPromoteOut,
    EnrollmentInitIn,
    EnrollmentInitOut,
    EnrollmentDeliverIn,
    EnrollmentDeliverOut,
    EnrollmentDemoteIn,
    EnrollmentDemoteOut,
    EnrollmentLockIn,
    EnrollmentLockOut,
    EnrollmentInviteCodeOut,
    EnrollmentInviteCodeIn,
)

from ....settings import settings
from ....sqlitedatabase import sqlite

router = APIRouter()
LOGGER = logging.getLogger(__name__)


# TODO ERROR LOGGAUS if _success is False, varmaankin riittaa etta se
#      on ihan ok tuolla sqlite.run_command() funkkarissa


async def check_management_hash_permissions(
    raise_exeption: bool = True, management_hash: str = "", special_rule: str = "enrollment", hash_like: bool = False
) -> bool:
    """
    Simple function to check if management_hash is found and has permissions. Use hash_like to use LIKE instead of =.
    """
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

    if len(_result) > 0:
        return True

    if raise_exeption is True:
        _reason = "Error. Given management hash doesn't have 'enrollment' permissions."
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=403, detail=_reason)

    return False


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


@router.post("/generate-verification-code", response_model=EnrollmentGenVerifiOut)
async def post_generate_verification_code(
    request: Request,
    request_in: EnrollmentGenVerifiIn = Body(
        None,
        examples=[EnrollmentGenVerifiIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentGenVerifiOut:
    """
    Update/Generate verification_code on database for given work_id or work_id_hash
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)
    await is_workid_or_workidhash_given(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _work_id_hash = await get_hash_with_either_workid_or_hash(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _verification_code = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(8)
        ]
    )

    _q = settings.sqlite_update_enrollment_verification_code.format(
        verification_code=_verification_code, work_id_hash=_work_id_hash
    )

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error ssuevc1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentGenVerifiOut(
        verification_code=f"{_verification_code}",
        success=True,
        reason="",
    )


@router.get("/show-verification-code-info", response_model=EnrollmentShowVerificationCodeOut)
async def request_show_verification_code(
    request: Request,
    params: EnrollmentShowVerificationCodeIn = Depends(),
) -> EnrollmentShowVerificationCodeOut:
    """
    /show-verification-code-info?user_management_hash=dasqdsdasqwe&verification_code=jaddajaa
    Return's information about the user/enrollment that made the code.
    """

    if params.verification_code in ("na", ""):
        _reason = "Verification code cannot be empty or na"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_hash_permissions(raise_exeption=True, management_hash=params.user_management_hash)

    # Get the code from db
    _q = settings.sqlite_sel_from_enrollment_where_verification_code.format(verification_code=params.verification_code)

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error qsssfmewvc1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Code not found."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=404, detail=_reason)

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=_result[0][0])
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error qsssfewh1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentShowVerificationCodeOut(
        work_id=_result[0][0],
        work_id_hash=_result[0][1],
        state=_result[0][2],
        accepted=_result[0][3],
        locked=_result[0][8],
        success=True,
        reason="",
    )


@router.get("/have-i-been-accepted", response_model=EnrollmentHaveIBeenAcceptedOut)
async def request_have_i_been_accepted(
    request: Request,
    params: EnrollmentHaveIBeenAcceptedIn = Depends(),
) -> EnrollmentHaveIBeenAcceptedOut:
    """
    /have-i-been-accepted?service_management_hash=dasqdsdasqwe&work_id_hash=jaddajaa
    Return's True/False in 'have_i_been_accepted'
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=params.service_management_hash)

    await is_workid_or_workidhash_given(raise_exeption=True, work_id=None, work_id_hash=params.work_id_hash)

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=params.work_id_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_sssfewh2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if _result[0][3] != "":
        return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=True, success=True, reason="")

    return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=False, success=True, reason="")


@router.post("/config/set-state", response_model=EnrollmentConfigSetStateOut)
async def post_config_set_state(
    request: Request,
    request_in: EnrollmentConfigSetStateIn = Body(
        None,
        examples=[EnrollmentConfigSetStateIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigSetStateOut:
    """
    Update/Set state/status for work_id/user/enrollment using either work_id_hash or work_id.
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)
    await is_workid_or_workidhash_given(
        raise_exeption=True, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _q = settings.sqlite_update_enrollment_state.format(
        work_id=request_in.work_id, work_id_hash=request_in.work_id_hash, state=request_in.state
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssues1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)
    return EnrollmentConfigSetStateOut(success=True, reason="")


# mtls_test_link
@router.post("/config/set-mtls-test-link", response_model=EnrollmentConfigSetMtlsOut)
async def post_config_set_mtls_test_link(
    request: Request,
    request_in: EnrollmentConfigSetMtlsIn = Body(
        None,
        examples=[EnrollmentConfigSetMtlsIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigSetMtlsOut:
    """
    Set MTLS test link for one or all work_id's
    """
    if request_in.set_for_all is False and request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required when \
'set_for_all' is set to False"
        LOGGER.error("{} : {}".format(request.url, _reason))
        return EnrollmentConfigSetMtlsOut(
            success=False,
            reason=_reason,
        )

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)

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

    return EnrollmentConfigSetMtlsOut(success=True, reason="")


@router.post("/config/set-cert-dl-link", response_model=EnrollmentConfigSetDLCertOut)
async def post_config_set_cert_dl_link(
    request: Request,
    request_in: EnrollmentConfigSetDLCertIn = Body(
        None,
        examples=[EnrollmentConfigSetDLCertIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigSetDLCertOut:
    """
    Store certificate or howto download link url for work_id (enrollment) using either work_id or work_id_hash
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)
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

    return EnrollmentConfigSetDLCertOut(success=True, reason="")


@router.post("/config/add-service-management-hash", response_model=EnrollmentAddServiceManagementOut)
async def post_config_add_manager(
    request: Request,
    request_in: EnrollmentAddServiceManagementIn = Body(
        None,
        examples=[EnrollmentAddServiceManagementIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentAddServiceManagementOut:
    """
    Add new "management hash" with certain permissions. This is not same as users/work-id's promotion to admin.
    You should think this as of adding "machine admin permissions". User related admin promotions should
    be done using /promote and /demote /lock.
    """

    if len(request_in.new_service_management_hash) < 64:
        _reason = "Error. new_service_management_hash too short. Needs to be 64 or more."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)

    _q = settings.sqlite_insert_into_management.format(
        management_hash=request_in.new_service_management_hash, special_rules=request_in.permissions_str
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssiim1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentAddServiceManagementOut(success=_success, reason="")


@router.get("/status", response_model=EnrollmentStatusOut)
async def request_enrolment_status(
    request: Request,
    params: EnrollmentStatusIn = Depends(),
) -> EnrollmentStatusOut:
    """
    Check the status for given work_id (enrollment). status=None means that there is no enrollment with given work_id
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=params.service_management_hash)

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

    return EnrollmentStatusOut(
        work_id=params.work_id, work_id_hash=_work_id_hash, status=_status, success=_success, reason=""
    )


@router.get("/list", response_model=EnrollmentListOut)
async def request_enrollment_list(
    request: Request,
    params: EnrollmentListIn = Depends(),
) -> EnrollmentListOut:
    """
    /list?service_management_hash=dasqdsdasqwe
    Return users/work-id's/enrollments. If 'accepted' has something else than '', it has been accepted.
    Returns a list of dicts, work_id_list = [ {  "work_id":'x', 'work_id_hash':'yy', 'state':'init', 'accepted':'' } ]
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=params.user_management_hash)

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

    return EnrollmentListOut(work_id_list=_work_id_list, success=True, reason="")


@router.post("/init", response_model=EnrollmentInitOut)
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

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)

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

    return EnrollmentInitOut(work_id=request_in.work_id, work_id_hash=_work_id_hash, success=_success, reason="")


@router.post("/promote", response_model=EnrollmentPromoteOut)
async def request_enrollment_promote(
    request: Request,
    request_in: EnrollmentPromoteIn = Body(
        None,
        examples=[EnrollmentPromoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentPromoteOut:
    """
    "Promote" work_id/user/enrollment to have 'admin' rights
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)
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
        _q = settings.sqlite_insert_into_management.format(management_hash=_work_id_hash, special_rules="enrollment")
        _success, _result = sqlite.run_command(_q)

        if _success is False:
            _reason = "Error. Undefined backend error qssiim2"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentPromoteOut(success=True, reason="")


@router.post("/demote", response_model=EnrollmentDemoteOut)
async def request_enrollment_demote(
    request: Request,
    request_in: EnrollmentDemoteIn = Body(
        None,
        examples=[EnrollmentDemoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentDemoteOut:
    """
    "Demote" work_id/user/enrollment from having 'admin' rights. work_id_hash can be used too.
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)
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

    return EnrollmentDemoteOut(success=True, reason="")


@router.post("/lock", response_model=EnrollmentLockOut)
async def request_enrollment_lock(
    request: Request,
    request_in: EnrollmentLockIn = Body(
        None,
        examples=[EnrollmentLockIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentLockOut:
    """
    Lock work_id/user/enrollment so it cannot be used anymore.
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)
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

    return EnrollmentLockOut(success=True, reason="")


@router.get("/deliver", response_model=EnrollmentDeliverOut)
async def request_enrollment_status(
    request: Request,
    params: EnrollmentDeliverIn = Depends(),
) -> EnrollmentDeliverOut:
    """
    Deliver download url link using work_id_hash
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=params.service_management_hash)

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
        LOGGER.error("{} : {}".format(request.url, _reason))
        return EnrollmentDeliverOut(
            work_id="",
            work_id_hash=params.work_id_hash,
            state=_result[0][2],
            cert_download_link="",
            howto_download_link="",
            mtls_test_link="",
            success=False,
            reason=_reason,
        )

    return EnrollmentDeliverOut(
        work_id=_result[0][0],
        work_id_hash=params.work_id_hash,
        success=True,
        cert_download_link=_result[0][4],
        howto_download_link=_result[0][5],
        mtls_test_link=_result[0][6],
        reason="",
        state=_result[0][2],
    )


@router.post("/accept", response_model=EnrollmentAcceptOut)
async def post_enrollment_accept(
    request: Request,
    request_in: EnrollmentAcceptIn = Body(
        None,
        examples=[EnrollmentAcceptIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentAcceptOut:
    """
    Accept work_id_hash (work_id/enrollment) using management_hash
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)

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

    _q = settings.sqlite_update_accept_enrollment.format(
        management_hash=request_in.user_management_hash, work_id_hash=request_in.work_id_hash
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssuae1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentAcceptOut(
        work_id="",
        work_id_hash=request_in.work_id_hash,
        management_hash=request_in.user_management_hash,
        success=_success,
        reason="",
    )


@router.post("/invitecode/create", response_model=EnrollmentInviteCodeOut)
async def post_invite_code(
    request: Request,
    request_in: EnrollmentInviteCodeIn = Body(
        None,
        examples=EnrollmentInviteCodeIn.Config.schema_extra["examples"],
    ),
) -> EnrollmentInviteCodeOut:
    """
    Create a new invite code
    """

    # Veriy that the user has permissions to create invite codes ??? is user-admin
    await check_management_hash_permissions(
        raise_exeption=True, management_hash=request_in.service_management_hash, special_rule="user-admin"
    )

    # Check does the user have existing invite code that matches their management hash
    _existing_invite_code = await check_management_hash_permissions(
        raise_exeption=False,
        management_hash=request_in.service_management_hash,
        special_rule="invite-code",
        hash_like=True,
    )

    # Random string for invite-code eg. GLXBT0
    _invite_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Update existing code if existing LIKE management_hash and invite-code
    if _existing_invite_code:
        _q = settings.sqlite_update_from_management_where_management_like.format(
            special_rules="invite-code",
            new_management_hash=f"{request_in.service_management_hash}_{_invite_code}",
            management_hash=request_in.service_management_hash,
        )
        _success, _result = sqlite.run_command(_q)

    else:
        # Create a new invite code for management_hash_GLXBT0
        _q = settings.sqlite_insert_into_management.format(
            management_hash=f"{request_in.service_management_hash}_{_invite_code}", special_rules="invite-code"
        )
        _success, _result = sqlite.run_command(_q)

    return EnrollmentInviteCodeOut(
        invite_code=f"{request_in.service_management_hash}_{_invite_code}",
        success=True,
        reason="",
    )


@router.get("/invitecode", response_model=List[EnrollmentInviteCodeOut])
async def get_invite_codes(request: Request) -> List[EnrollmentInviteCodeOut]:
    """
    Get all invite codes
    """

    # Your code logic here

    invite_codes = []

    # Your code logic here

    return invite_codes
