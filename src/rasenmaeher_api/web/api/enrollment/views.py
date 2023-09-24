"""Enrollment API views."""  # pylint: disable=too-many-lines
import logging
from typing import Dict, List, Any, Union
from fastapi import APIRouter, Request, Body, Depends, HTTPException
from multikeyjwt import Issuer
from rasenmaeher_api.web.api.enrollment.schema import (
    EnrollmentConfigTaskDone,
    EnrollmentStatusIn,
    EnrollmentStatusOut,
    EnrollmentAcceptIn,
    EnrollmentAcceptOut,
    EnrollmentGenVerifiOut,
    EnrollmentShowVerificationCodeIn,
    EnrollmentShowVerificationCodeOut,
    EnrollmentHaveIBeenAcceptedOut,
    EnrollmentListOut,
    EnrollmentPromoteIn,
    EnrollmentInitIn,
    EnrollmentInitOut,
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

from ....db import Person
from ....db import Enrollment, EnrollmentPool
from ....db.errors import NotFound

LOGGER = logging.getLogger(__name__)

ENROLLMENT_ROUTER = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])
NO_JWT_ENROLLMENT_ROUTER = APIRouter()


async def check_management_permissions(
    raise_exeption: bool = True, work_id: str = "", required_role: str = "admin"
) -> Union[bool, None]:
    """
    Simple function to check if requester has requested role.
    """

    _user = await Person.by_callsign(callsign=work_id)
    _is_admin = await _user.has_role(role=required_role)

    # Raise exeption if
    if raise_exeption and _is_admin is False:
        _reason = "Error. User doesn't have required permissions. See system logs."
        LOGGER.error(
            "Missing role from user : '{}'. Required permissions that are missing : '{}'".format(work_id, required_role)
        )
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=403, detail=_reason)

    return _is_admin


@ENROLLMENT_ROUTER.post("/generate-verification-code", response_model=EnrollmentGenVerifiOut)
async def post_generate_verification_code(
    request: Request,
) -> EnrollmentGenVerifiOut:
    """
    Update/Generate verification_code to database for given jwt/mtls
    """
    _verification_code = await Enrollment.set_approvecode(callsign=request.state.mtls_or_jwt.userid)
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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _obj = await Enrollment.by_approvecode(code=params.verification_code)

    return EnrollmentShowVerificationCodeOut(
        work_id=_obj.callsign,
        state=_obj.state,
        accepted="????",
        locked="????",
    )


@ENROLLMENT_ROUTER.get("/have-i-been-accepted", response_model=EnrollmentHaveIBeenAcceptedOut)
async def request_have_i_been_accepted(
    request: Request,
) -> EnrollmentHaveIBeenAcceptedOut:
    """
    /have-i-been-accepted
    Return's True/False in 'have_i_been_accepted'
    """

    _enrollment = await Enrollment.by_callsign(callsign=request.state.mtls_or_jwt.userid)

    # See state values in db/enrollment.py:EnrollmentState
    if _enrollment.decided_by:
        return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=True)

    return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=False)


@ENROLLMENT_ROUTER.get("/status", response_model=EnrollmentStatusOut)
async def request_enrolment_status(
    params: EnrollmentStatusIn = Depends(),
) -> EnrollmentStatusOut:
    """
    /status?work_id=xxxx
    Check the status for given work_id (enrollment). status=-1 means that there is no enrollment with given work_id
    """
    try:
        _obj = await Enrollment.by_callsign(params.work_id)

        return EnrollmentStatusOut(work_id=_obj.callsign, status=_obj.state)
    except NotFound:
        return EnrollmentStatusOut(work_id="", status=-1)


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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _enroll_list = Enrollment.list()

    _result_list: List[Dict[Any, Any]] = []
    async for _x in _enroll_list:
        _result_list.append({"work_id": _x.callsign, "approvecode": _x.approvecode, "state": _x.state})

    return EnrollmentListOut(work_id_list=_result_list)


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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    # TODO ADD POOL NAME CHECK

    _new_enrollment = await Enrollment.create_for_callsign(callsign=request_in.work_id, pool=None, extra={})

    return EnrollmentInitOut(work_id=_new_enrollment.callsign, jwt="")


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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _obj = await Person.by_callsign(callsign=request_in.work_id)

    _role_added = await _obj.assign_role(role="admin")
    if _role_added:
        return EnrollmentConfigTaskDone(success_message="Promote done")

    _reason = "Given work_id/callsign already has elevated permissions."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=400, detail=_reason)


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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _obj = await Person.by_callsign(callsign=request_in.work_id)
    _role_removed = await _obj.remove_role(role="admin")
    if _role_removed:
        return EnrollmentConfigTaskDone(success_message="Demote done")

    _reason = "Given work_id/work_id_hash doesn't have 'admin' privileges to take away."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=400, detail=_reason)


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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _admin_person = await Person.by_callsign(request.state.mtls_or_jwt.userid)
    _usr_enrollment = await Enrollment.by_callsign(callsign=request_in.work_id)
    await _usr_enrollment.reject(decider=_admin_person)

    return EnrollmentConfigTaskDone(success_message="Lock task done")


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
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _admin_user = await Person.by_callsign(callsign=request.state.mtls_or_jwt.userid)
    _pending_enrollment = await Enrollment.by_callsign(callsign=request_in.work_id)
    _new_approved_user = await _pending_enrollment.approve(approver=_admin_user)

    return EnrollmentAcceptOut(work_id=_new_approved_user.callsign)


@ENROLLMENT_ROUTER.post("/invitecode/create", response_model=EnrollmentInviteCodeCreateOut)
async def post_invite_code(
    request: Request,
) -> EnrollmentInviteCodeCreateOut:
    """
    Create a new invite code
    """

    # Veriy that the user has permissions to create invite codes
    await check_management_permissions(
        raise_exeption=True, work_id=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _pool = await EnrollmentPool.create_or_update_invitecode_for_callsign(callsign=request.state.mtls_or_jwt.userid)

    return EnrollmentInviteCodeCreateOut(invite_code=_pool.invitecode)


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
    _obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    _activated_obj = await _obj.set_active(state=True)

    if _activated_obj.active:
        return EnrollmentInviteCodeActivateOut(invite_code=request_in.invite_code)

    _reason = "Error. Unable to activate given invitecode."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=500, detail=_reason)


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
    _obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    _deactivated_obj = await _obj.set_active(state=False)

    if _deactivated_obj.active is False:
        return EnrollmentInviteCodeDeactivateOut(invite_code="DISABLED")

    _reason = "Error. Unable to deactivate given invitecode."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=500, detail=_reason)


@ENROLLMENT_ROUTER.delete("/invitecode/{invite_code}", response_model=EnrollmentInviteCodeDeleteOut)
async def delete_invite_code(
    # request: Request,
    invite_code: str,
) -> EnrollmentInviteCodeDeleteOut:
    """
    Delete an invite code
    """
    # TODO
    return EnrollmentInviteCodeDeleteOut(invite_code=f"TODO{invite_code}")


@NO_JWT_ENROLLMENT_ROUTER.get("/invitecode", response_model=EnrollmentIsInvitecodeActiveOut)
async def get_invite_codes(
    params: EnrollmentIsInvitecodeActiveIn = Depends(),
) -> EnrollmentIsInvitecodeActiveOut:
    """
    /invitecode?invitecode=xxx
    Returns true/false if the code is usable or not
    """
    try:
        _obj = await EnrollmentPool.by_invitecode(invitecode=params.invitecode)
        if _obj.active:
            return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=True)
    except NotFound:
        pass
    return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=False)


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

    # CHECK IF INVITE CODE CAN BE USED
    _obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    if _obj.active is False:
        _reason = "Error. invitecode disabled."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # CHECK THAT THE WORK ID CAN BE USED
    try:
        await Enrollment.by_callsign(callsign=request_in.work_id)
        _reason = "Error. work_id/callsign already taken."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)
    except NotFound:
        pass

    _enrollment = await _obj.create_enrollment(callsign=request_in.work_id)

    # Create JWT token for user
    _claims = {"sub": request_in.work_id}
    _new_jwt = Issuer.singleton().issue(_claims)

    return EnrollmentInitOut(work_id=_enrollment.callsign, jwt=_new_jwt)
