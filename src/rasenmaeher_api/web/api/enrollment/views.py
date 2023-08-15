"""Enrollment API views."""
import string
import random
import logging
from typing import Dict, List, Any
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
    EnrollmentConfigGenVerifiIn,
    EnrollmentConfigGenVerifiOut,
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
)

from ....settings import settings
from ....sqlitedatabase import sqlite


router = APIRouter()
LOGGER = logging.getLogger(__name__)

# TODO ERROR LOGGAUS if _success is False, varmaankin riittaa etta se
#      on ihan ok tuolla sqlite.run_command() funkkarissa


async def check_management_hash_permissions(
    raise_exeption: bool = True, management_hash: str = "", special_rule: str = "enrollment"
) -> bool:
    """
    Simple function to check if management_hash is found and has permissions.
    """
    # Get special_rules='first-user from managment
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


@router.post("/config/generate-verification-code", response_model=EnrollmentConfigGenVerifiOut)
async def post_config_generate_verification_code(
    request: Request,
    request_in: EnrollmentConfigGenVerifiIn = Body(
        None,
        examples=[EnrollmentConfigGenVerifiIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigGenVerifiOut:
    """
    Update/Generate verification_code on database for given work_id or work_id_hash
    """

    if request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)

    if request_in.work_id_hash is not None:
        _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=request_in.work_id_hash)
    else:
        _q = settings.sqlite_sel_from_enrollment.format(work_id=request_in.work_id)

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error ssfewhx21"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Cannot set verification code. Requested work_id or work_id_hash not found..."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=404, detail=_reason)

    _verification_code = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(8)
        ]
    )

    _q = settings.sqlite_update_enrollment_verification_code.format(
        verification_code=_verification_code, work_id=request_in.work_id, work_id_hash=request_in.work_id_hash
    )

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error ssuevc1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigGenVerifiOut(
        verification_code=f"{_verification_code}",
        success=True,
        reason="",
    )


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

    if request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)

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
        _q = settings.sqlite_update_enrollment_mtls_test_link.format(
            work_id=request_in.work_id, work_id_hash=request_in.work_id_hash, mtls_test_link=request_in.mtls_test_link
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

    if request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.service_management_hash)

    if request_in.cert_download_link is None and request_in.howto_download_link is None:
        _reason = "Error. Both cert_download_link and howto_download_link are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _success: bool = True
    if request_in.cert_download_link is not None:
        _q = settings.sqlite_update_enrollment_cert_dl_link.format(
            work_id=request_in.work_id,
            work_id_hash=request_in.work_id_hash,
            cert_download_link=request_in.cert_download_link,
        )
        _success, _result = sqlite.run_command(_q)

    _success2: bool = True
    if request_in.howto_download_link is not None:
        _q = settings.sqlite_update_enrollment_cert_howto_dl_link.format(
            work_id=request_in.work_id,
            work_id_hash=request_in.work_id_hash,
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
    Return users/work-id's/enrollments. If 'accepted' has something else than 'no', it has been accepted.
    Returns a list of dicts, work_id_list = [ {  "work_id":'x', 'work_id_hash':'yy', 'state':'init', 'accepted':'no' } ]
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
        accepted="no",
        cert_dl_link="na",
        cert_howto_dl_link="na",
        mtls_test_link="na",
        verification_code="na",
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

    if request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    if request_in.work_id_hash is not None:
        _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=request_in.work_id_hash)
    else:
        _q = settings.sqlite_sel_from_enrollment.format(work_id=request_in.work_id)

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error ssfewhx22"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Cannot promote. Requested work_id or work_id_hash not found..."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=404, detail=_reason)

    # Check if the hash is already in database.
    _q = settings.sqlite_sel_from_management.format(management_hash=_result[1])
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
        _q = settings.sqlite_insert_into_management.format(management_hash=_result[1], special_rules="enrollment")
        _success, _result = sqlite.run_command(_q)

        if _success is False:
            _reason = "Error. Undefined backend error qssiim2"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentPromoteOut(success=True, reason="")


@router.post("/demote", response_model=EnrollmentDemoteOut)
async def request_enrollment_demote(
    request_in: EnrollmentDemoteIn = Body(
        None,
        examples=[EnrollmentDemoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentDemoteOut:
    """
    "Demote" work_id/user/enrollment to have 'admin' rights
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)

    return EnrollmentDemoteOut(success=True, reason="")


@router.post("/lock", response_model=EnrollmentLockOut)
async def request_enrollment_lock(
    request_in: EnrollmentLockIn = Body(
        None,
        examples=[EnrollmentLockIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentLockOut:
    """
    Lock work_id/user/enrollment so it cannot be used anymore.
    """

    await check_management_hash_permissions(raise_exeption=True, management_hash=request_in.user_management_hash)

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
