"""Enrollment API views."""
import string
import random
import logging
from fastapi import APIRouter, Request, Body, HTTPException
from rasenmaeher_api.web.api.enrollment.schema import (
    EnrollmentStatusOut,
    EnrollmentInitIn,
    EnrollmentInitOut,
    EnrollmentDeliverOut,
    EnrollmentAcceptIn,
    EnrollmentAcceptOut,
    EnrollmentConfigAddManagerOut,
    EnrollmentConfigAddManagerIn,
    EnrollmentConfigSetDLOut,
    EnrollmentConfigSetDLIn,
    EnrollmentConfigSetStateOut,
    EnrollmentConfigSetStateIn,
    EnrollmentConfigSetMtlsIn,
    EnrollmentConfigSetMtlsOut,
    EnrollmentConfigGenVerifiIn,
    EnrollmentConfigGenVerifiOut,
)

from ....settings import settings
from ....sqlitedatabase import sqlite


router = APIRouter()
LOGGER = logging.getLogger(__name__)

# TODO ERROR LOGGAUS if _success is False, varmaankin riittaa etta se
#      on ihan ok tuolla sqlite.run_command() funkkarissa


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

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.service_management_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfm4"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'service_management_hash' doesn't have rights to update/change verification code"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

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
    Update/Set state for work_id (enrollment) using either work_id_hash or work_id.
    """

    if request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.management_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfm4"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'management_hash' doesn't have rights to set 'state'"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

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

    # Get manager hash
    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.management_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfm5"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'management_hash' doesn't have rights to set 'mtls_test_link'"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

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


@router.post("/config/set-cert-dl-link", response_model=EnrollmentConfigSetDLOut)
async def post_config_set_cert_dl_link(
    request: Request,
    request_in: EnrollmentConfigSetDLIn = Body(
        None,
        examples=[EnrollmentConfigSetDLIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigSetDLOut:
    """
    Store certificate or howto download link url for work_id (enrollment) using either work_id or work_id_hash
    """

    if request_in.work_id is None and request_in.work_id_hash is None:
        _reason = "Error. Both work_id and work_id_hash are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.management_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfm3"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'management_hash' doesn't have rights to set 'cert_download_link' or 'howto_download_link'"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

    if request_in.cert_download_link is None and request_in.howto_download_link is None:
        _reason = "Error. Both cert_download_link and howto_download_link are undefined. At least one is required"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

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

    return EnrollmentConfigSetDLOut(success=True, reason="")


@router.post("/config/add-manager", response_model=EnrollmentConfigAddManagerOut)
async def post_config_add_manager(
    request: Request,
    request_in: EnrollmentConfigAddManagerIn = Body(
        None,
        examples=[EnrollmentConfigAddManagerIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigAddManagerOut:
    """
    Add new "manager" hash that has role/permission for X.
    """

    if len(request_in.new_permit_hash) < 64:
        _reason = "Error. new_permit_hash too short. Needs to be 64 or more."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.management_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfm2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'management_hash' doesn't have rights add 'new_permit_hash'"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

    _q = settings.sqlite_insert_into_management.format(
        management_hash=request_in.new_permit_hash, special_rules=request_in.permissions_str
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssiim1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentConfigAddManagerOut(success=_success, reason="")


@router.get("/status/{work_id}", response_model=EnrollmentStatusOut)
async def request_enrolment_status(work_id: str, request: Request) -> EnrollmentStatusOut:
    """
    Check the status for given work_id (enrollment). status=None means that there is no enrollment with given work_id
    """
    _q = settings.sqlite_sel_from_enrollment.format(work_id=work_id)
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

    return EnrollmentStatusOut(work_id=work_id, work_id_hash=_work_id_hash, status=_status, success=_success, reason="")


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


@router.get("/deliver/{work_id_hash}", response_model=EnrollmentDeliverOut)
async def request_enrollment_status(request: Request, work_id_hash: str) -> EnrollmentDeliverOut:
    """
    Deliver download url link using work_id_hash
    """

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=work_id_hash)
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
            work_id_hash=work_id_hash,
            state=_result[0][2],
            cert_download_link="",
            howto_download_link="",
            mtls_test_link="",
            success=False,
            reason=_reason,
        )

    return EnrollmentDeliverOut(
        work_id=_result[0][0],
        work_id_hash=work_id_hash,
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

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.management_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssfm1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. 'management_hash' doesn't have rights to accept given 'work_id_hash'"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

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
        management_hash=request_in.management_hash, work_id_hash=request_in.work_id_hash
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_ssuae1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return EnrollmentAcceptOut(
        work_id="",
        work_id_hash=request_in.work_id_hash,
        management_hash=request_in.management_hash,
        success=_success,
        reason="",
    )
