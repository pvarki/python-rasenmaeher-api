"""Enrollment API views."""
import string
import random
from fastapi import APIRouter
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
)

from ....settings import settings, sqlite


router = APIRouter()


# TODO ERROR LOGGAUS if _success is False, varmaankin riittaa etta se
#      on ihan ok tuolla sqlite.run_command() funkkarissa


@router.post("/config/set-state", response_model=EnrollmentConfigSetStateOut)
async def post_config_set_state(
    request_in: EnrollmentConfigSetStateIn,
) -> EnrollmentConfigSetStateOut:
    """
    TODO set state link
    """

    if request_in.work_id is None and request_in.enroll_str is None:
        return EnrollmentConfigSetStateOut(
            success=False,
            reason="Error. Both work_id and enroll_str are undefined. At least one is required",
        )

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.permit_str)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentConfigSetStateOut(
            success=False,
            reason="Error. Undefined backend error q_ssfm4",
        )

    if len(_result) == 0:
        return EnrollmentConfigSetStateOut(
            success=False,
            reason="Error. 'permit_str' doesn't have rights to set 'state'",
        )

    _q = settings.sqlite_update_enrollment_state.format(
        work_id=request_in.work_id, work_id_hash=request_in.enroll_str, state=request_in.state
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentConfigSetStateOut(
            success=False,
            reason="Error. Undefined backend error q_ssues1",
        )

    return EnrollmentConfigSetStateOut(
        success=True,
    )


@router.post("/config/set-dl-link", response_model=EnrollmentConfigSetDLOut)
async def post_config_set_dl_link(
    request_in: EnrollmentConfigSetDLIn,
) -> EnrollmentConfigSetDLOut:
    """
    TODO set download link
    """

    if request_in.work_id is None and request_in.enroll_str is None:
        return EnrollmentConfigSetDLOut(
            success=False,
            reason="Error. Both work_id and enroll_str are undefined. At least one is required",
        )

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.permit_str)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentConfigSetDLOut(
            success=False,
            reason="Error. Undefined backend error q_ssfm3",
        )

    if len(_result) == 0:
        return EnrollmentConfigSetDLOut(
            success=False,
            reason="Error. 'permit_str' doesn't have rights to set 'download_link'",
        )

    _q = settings.sqlite_update_enrollment_dl_link.format(
        work_id=request_in.work_id, work_id_hash=request_in.enroll_str, download_link=request_in.download_link
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentConfigSetDLOut(
            success=False,
            reason="Error. Undefined backend error q_ssuedl1",
        )

    return EnrollmentConfigSetDLOut(
        success=True,
    )


@router.post("/config/add-manager", response_model=EnrollmentConfigAddManagerOut)
async def post_config_add_manager(
    request_in: EnrollmentConfigAddManagerIn,
) -> EnrollmentConfigAddManagerOut:
    """
    TODO add manager hash
    """

    if len(request_in.new_permit_hash) < 64:
        return EnrollmentConfigAddManagerOut(
            success=False,
            reason="Error. new_permit_hash too short. Needs to be 64 or more.",
        )

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.permit_str)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentConfigAddManagerOut(
            success=False,
            reason="Error. Undefined backend error q_ssfm2",
        )

    if len(_result) == 0:
        return EnrollmentConfigAddManagerOut(
            success=False,
            reason="Error. 'permit_str' doesn't have rights add 'new_permit_hash'",
        )

    _q = settings.sqlite_insert_into_management.format(
        management_hash=request_in.new_permit_hash, special_rules=request_in.permissions_str
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentConfigAddManagerOut(
            success=False,
            reason="Error. Undefined backend error q_ssiim1",
        )

    return EnrollmentConfigAddManagerOut(success=_success)


@router.get("/status/{work_id}", response_model=EnrollmentStatusOut)
async def request_enrolment_status(work_id: str) -> EnrollmentStatusOut:
    """
    TODO Check sqlite for status
    """
    _q = settings.sqlite_sel_from_enrollment.format(work_id=work_id)
    _success, _result = sqlite.run_command(_q)

    if len(_result) > 0:
        _status: str = _result[0][2]
    else:
        _status = "none"

    if _success is False:
        return EnrollmentStatusOut(
            work_id=work_id, status=_status, success=_success, reason="Error. Undefined backend error sssfe2"
        )

    return EnrollmentStatusOut(work_id=work_id, status=_status, success=_success)


@router.post("/init", response_model=EnrollmentInitOut)
async def request_enrollment_init(
    request: EnrollmentInitIn,
) -> EnrollmentInitOut:
    """
    TODO init enrollment in background?
    """

    # First check if there is already enrollment for requested workid
    _q = settings.sqlite_sel_from_enrollment.format(work_id=request.work_id)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentInitOut(
            work_id=request.work_id, enroll_str="", success=_success, reason="Error. Undefined backend error sssfe1"
        )
    # Skip enrollment if work_id already used
    if len(_result) > 0:
        return EnrollmentInitOut(
            work_id=request.work_id, enroll_str="", success=False, reason="Error. work_id has already active enrollment"
        )

    _work_id_hash = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(64)
        ]
    )

    _q = settings.sqlite_insert_into_enrollment.format(
        work_id=request.work_id, work_id_hash=_work_id_hash, state="init", accepted="no", dl_link="na"
    )

    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentInitOut(
            work_id=request.work_id, enroll_str="", success=_success, reason="Error. Undefined backend error ssiie1"
        )
    return EnrollmentInitOut(work_id=request.work_id, enroll_str=_work_id_hash, success=_success)


@router.get("/deliver/{enroll_str}", response_model=EnrollmentDeliverOut)
async def request_enrollment_status(enroll_str: str) -> EnrollmentDeliverOut:
    """
    TODO deliver enrollment download url if enrollment status is complete???
    """

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=enroll_str)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentDeliverOut(
            work_id="", enroll_str=enroll_str, success=False, reason="Error. Undefined backend error q_sssfewh1"
        )

    if len(_result) == 0:
        return EnrollmentDeliverOut(
            work_id="", enroll_str=enroll_str, success=False, reason="Error. 'enroll_str' not found from database."
        )

    if _result[0][2] != "ReadyForDelivery":
        return EnrollmentDeliverOut(
            work_id="",
            enroll_str=enroll_str,
            state=_result[0][2],
            success=False,
            reason="Enrollment is still in progress or it hasn't been accepted.",
        )

    return EnrollmentDeliverOut(work_id=_result[0][0], enroll_str=enroll_str, download_url=_result[0][4])


@router.post("/accept", response_model=EnrollmentAcceptOut)
async def post_enrollment_accept(
    request_in: EnrollmentAcceptIn,
) -> EnrollmentAcceptOut:
    """
    TODO accept something in sqlite
    """

    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.permit_str)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentAcceptOut(
            work_id="",
            enroll_str=request_in.enroll_str,
            permit_str=request_in.permit_str,
            success=False,
            reason="Error. Undefined backend error q_ssfm1",
        )

    if len(_result) == 0:
        return EnrollmentAcceptOut(
            work_id="",
            enroll_str=request_in.enroll_str,
            permit_str=request_in.permit_str,
            success=False,
            reason="Error. 'permit_str' doesn't have rights to accept given 'enroll_str'",
        )

    _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=request_in.enroll_str)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentAcceptOut(
            work_id="",
            enroll_str=request_in.enroll_str,
            permit_str=request_in.permit_str,
            success=False,
            reason="Error. Undefined backend error q_ssfewh1",
        )

    if len(_result) == 0:
        return EnrollmentAcceptOut(
            work_id="",
            enroll_str=request_in.enroll_str,
            permit_str=request_in.permit_str,
            success=False,
            reason="Error. 'enroll_str' not found from database.",
        )

    _q = settings.sqlite_update_accept_enrollment.format(
        enroll_str=request_in.permit_str, work_id_hash=request_in.enroll_str
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        return EnrollmentAcceptOut(
            work_id="",
            enroll_str=request_in.enroll_str,
            permit_str=request_in.permit_str,
            success=False,
            reason="Error. Undefined backend error q_ssuae1",
        )

    return EnrollmentAcceptOut(
        work_id="", enroll_str=request_in.enroll_str, permit_str=request_in.permit_str, success=_success
    )
