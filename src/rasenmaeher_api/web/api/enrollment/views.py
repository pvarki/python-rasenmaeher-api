"""Enrollment API views."""  # pylint: disable=too-many-lines
from typing import Dict, List, Any, Union
import logging


from fastapi import APIRouter, Request, Body, Depends, HTTPException
from multikeyjwt import Issuer


from .schema import (
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
from ..middleware.mtls import MTLSorJWT
from ....db import Person
from ....db import Enrollment, EnrollmentPool
from ....db.errors import NotFound

LOGGER = logging.getLogger(__name__)

ENROLLMENT_ROUTER = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])
NO_JWT_ENROLLMENT_ROUTER = APIRouter()


async def check_management_permissions(
    raise_exeption: bool = True, callsign: str = "", required_role: str = "admin"
) -> Union[bool, None]:
    """
    Simple function to check if requester has requested role.
    """

    user = await Person.by_callsign(callsign=callsign)
    is_admin = await user.has_role(role=required_role)

    # Raise exeption if
    if raise_exeption and is_admin is False:
        _reason = "Error. User doesn't have required permissions. See system logs."
        LOGGER.error(
            "Missing role from user : '{}'. Required permissions that are missing : '{}'".format(
                callsign, required_role
            )
        )
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=403, detail=_reason)

    return is_admin


@ENROLLMENT_ROUTER.post("/generate-verification-code", response_model=EnrollmentGenVerifiOut)
async def post_generate_verification_code(
    request: Request,
) -> EnrollmentGenVerifiOut:
    """
    Update/Generate verification_code to database for given jwt/mtls
    """
    _verification_code = await Enrollment.reset_approvecode4callsign(callsign=request.state.mtls_or_jwt.userid)
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
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    obj = await Enrollment.by_approvecode(code=params.verification_code)

    return EnrollmentShowVerificationCodeOut(
        callsign=obj.callsign,
        state=obj.state,
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

    enrollment = await Enrollment.by_callsign(callsign=request.state.mtls_or_jwt.userid)

    # See state values in db/enrollment.py:EnrollmentState
    if enrollment.decided_by:
        return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=True)

    return EnrollmentHaveIBeenAcceptedOut(have_i_been_accepted=False)


@ENROLLMENT_ROUTER.get("/status", response_model=EnrollmentStatusOut)
async def request_enrolment_status(
    params: EnrollmentStatusIn = Depends(),
) -> EnrollmentStatusOut:
    """
    /status?callsign=xxxx
    Check the status for given callsign (enrollment). status=-1 means that there is no enrollment with given callsign
    """
    try:
        obj = await Enrollment.by_callsign(params.callsign)

        return EnrollmentStatusOut(callsign=obj.callsign, status=obj.state)
    except NotFound:
        return EnrollmentStatusOut(callsign="", status=-1)


@ENROLLMENT_ROUTER.get("/list", response_model=EnrollmentListOut)
async def request_enrollment_list(
    request: Request,
) -> EnrollmentListOut:
    """
    /list
    Return users/callsign/enrollments. If 'accepted' has something else than '', it has been accepted.
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', 'state':'init', 'approvecode':'' } ]
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _enroll_list = Enrollment.list()

    _result_list: List[Dict[Any, Any]] = []
    async for _x in _enroll_list:
        _result_list.append({"callsign": _x.callsign, "approvecode": _x.approvecode, "state": _x.state})

    return EnrollmentListOut(callsign_list=_result_list)


@ENROLLMENT_ROUTER.post("/init", response_model=EnrollmentInitOut)
async def request_enrollment_init(
    request: Request,
    request_in: EnrollmentInitIn = Body(
        None,
        examples=[EnrollmentInitIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentInitOut:
    """
    Add new callsign (enrollment) to environment.
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    # TODO ADD POOL NAME CHECK

    new_enrollment = await Enrollment.create_for_callsign(callsign=request_in.callsign, pool=None, extra={})
    # Create JWT token for user
    claims = {"sub": request_in.callsign}
    new_jwt = Issuer.singleton().issue(claims)
    return EnrollmentInitOut(callsign=new_enrollment.callsign, jwt=new_jwt, approvecode=new_enrollment.approvecode)


@ENROLLMENT_ROUTER.post("/promote", response_model=EnrollmentConfigTaskDone)
async def request_enrollment_promote(
    request: Request,
    request_in: EnrollmentPromoteIn = Body(
        None,
        examples=[EnrollmentPromoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    "Promote" callsign/user/enrollment to have 'admin' rights
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    obj = await Person.by_callsign(callsign=request_in.callsign)

    role_added = await obj.assign_role(role="admin")
    if role_added:
        return EnrollmentConfigTaskDone(success_message="Promote done")

    reason = "Given callsign/callsign already has elevated permissions."
    LOGGER.error("{} : {}".format(request.url, reason))
    raise HTTPException(status_code=400, detail=reason)


@ENROLLMENT_ROUTER.post("/demote", response_model=EnrollmentConfigTaskDone)
async def request_enrollment_demote(
    request: Request,
    request_in: EnrollmentDemoteIn = Body(
        None,
        examples=[EnrollmentDemoteIn.Config.schema_extra["examples"]],
    ),
) -> EnrollmentConfigTaskDone:
    """
    "Demote" callsign/user/enrollment from having 'admin' rights. callsign_hash can be used too.
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    obj = await Person.by_callsign(callsign=request_in.callsign)
    _role_removed = await obj.remove_role(role="admin")
    if _role_removed:
        return EnrollmentConfigTaskDone(success_message="Demote done")

    _reason = "Given callsign/callsign_hash doesn't have 'admin' privileges to take away."
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
    Lock callsign/user/enrollment so it cannot be used anymore.
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _admin_person = await Person.by_callsign(request.state.mtls_or_jwt.userid)
    _usr_enrollment = await Enrollment.by_callsign(callsign=request_in.callsign)
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
    Accept callsign_hash (callsign/enrollment)
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    admin_user = await Person.by_callsign(callsign=request.state.mtls_or_jwt.userid)
    pending_enrollment = await Enrollment.by_callsign(callsign=request_in.callsign)
    if request_in.approvecode != pending_enrollment.approvecode:
        raise HTTPException(status_code=403, detail="Invalid approval code for this enrollment")
    new_approved_user = await pending_enrollment.approve(approver=admin_user)

    return EnrollmentAcceptOut(callsign=new_approved_user.callsign)


@ENROLLMENT_ROUTER.post("/invitecode/create", response_model=EnrollmentInviteCodeCreateOut)
async def post_invite_code(
    request: Request,
) -> EnrollmentInviteCodeCreateOut:
    """
    Create a new invite code
    """

    # Veriy that the user has permissions to create invite codes
    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _pool = await EnrollmentPool.old_invitecode_for_callsign_tobedeleted(callsign=request.state.mtls_or_jwt.userid)

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
    obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    _activated_obj = await obj.set_active(state=True)

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
    obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    _deactivated_obj = await obj.set_active(state=False)

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
        obj = await EnrollmentPool.by_invitecode(invitecode=params.invitecode)
        if obj.active:
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
    obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    if obj.active is False:
        _reason = "Error. invitecode disabled."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # CHECK THAT THE CALLSIGN CAN BE USED
    try:
        await Enrollment.by_callsign(callsign=request_in.callsign)
        _reason = "Error. callsign/callsign already taken."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)
    except NotFound:
        pass

    enrollment = await obj.create_enrollment(callsign=request_in.callsign)

    # Create JWT token for user
    claims = {"sub": request_in.callsign}
    new_jwt = Issuer.singleton().issue(claims)

    return EnrollmentInitOut(callsign=enrollment.callsign, jwt=new_jwt, approvecode=enrollment.approvecode)
