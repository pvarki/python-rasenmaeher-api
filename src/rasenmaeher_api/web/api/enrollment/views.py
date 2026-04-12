"""Enrollment API views."""  # pylint: disable=too-many-lines

from typing import Dict, List, Any, Optional
import logging
import uuid


from fastapi import APIRouter, Request, Body, Depends, HTTPException, Response
from multikeyjwt import Issuer
from multikeyjwt import config as jwtconfig

from libpvarki.schemas.generic import OperationResultResponse
from .schema import (
    EnrollmentStatusIn,
    EnrollmentStatusOut,
    EnrollmentAcceptIn,
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
    EnrollmentInviteCodeActivateIn,
    EnrollmentInviteCodeDeactivateIn,
    EnrollmentPoolListOut,
    EnrollmentPoolListItem,
)
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from ..utils.auditcontext import build_audit_extra
from ....db import Person
from ....db import Enrollment, EnrollmentPool
from ....db.errors import NotFound

LOGGER = logging.getLogger(__name__)

ENROLLMENT_ROUTER = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])
NO_JWT_ENROLLMENT_ROUTER = APIRouter()


@ENROLLMENT_ROUTER.get(
    "/pools",
    response_model=EnrollmentPoolListOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def list_pools(owner_cs: Optional[str] = None) -> EnrollmentPoolListOut:
    """List EnrollmentPools (aka invitecodes)"""
    owner: Optional[Person] = None
    if owner_cs:
        owner = await Person.by_callsign(owner_cs)
    pools: List[EnrollmentPoolListItem] = []
    owner_cache: Dict[uuid.UUID, Person] = {}
    async for pool in EnrollmentPool.list(owner):
        if pool.owner not in owner_cache:
            owner_cache[pool.owner] = await Person.by_pk(pool.owner, allow_deleted=True)
        pools.append(
            EnrollmentPoolListItem(
                invitecode=pool.invitecode,
                active=pool.active,
                owner_cs=owner_cache[pool.owner].callsign,
                created=pool.created.isoformat(),
            )
        )
    return EnrollmentPoolListOut(pools=pools)


@ENROLLMENT_ROUTER.post("/generate-verification-code", response_model=EnrollmentGenVerifiOut)
async def post_generate_verification_code(
    request: Request,
) -> EnrollmentGenVerifiOut:
    """
    Update/Generate verification_code to database for given jwt/mtls
    """
    callsign = request.state.mtls_or_jwt.userid

    _verification_code = await Enrollment.reset_approvecode4callsign(callsign=callsign)

    LOGGER.audit(  # type: ignore[attr-defined]
        "Verification code generated",
        extra=build_audit_extra(
            action="verification_code_generate",
            outcome="success",
            actor=callsign,
            target=callsign,
            request=request,
        ),
    )

    return EnrollmentGenVerifiOut(verification_code=f"{_verification_code}")


@ENROLLMENT_ROUTER.get(
    "/show-verification-code-info",
    response_model=EnrollmentShowVerificationCodeOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_show_verification_code(
    request: Request, params: EnrollmentShowVerificationCodeIn = Depends()
) -> EnrollmentShowVerificationCodeOut:
    """
    /show-verification-code-info?verification_code=jaddajaa
    Return's information about the user/enrollment that made the code.
    """

    if params.verification_code in ("na", ""):
        _reason = "Verification code cannot be empty or na"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    obj = await Enrollment.by_approvecode(code=params.verification_code)

    return EnrollmentShowVerificationCodeOut(
        callsign=obj.callsign,
        state=str(obj.state),
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


@ENROLLMENT_ROUTER.get(
    "/list",
    response_model=EnrollmentListOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_list(code: Optional[str] = None) -> EnrollmentListOut:
    """
    /list
    Return users/callsign/enrollments. If 'accepted' has something else than '', it has been accepted.
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', 'state':'init', 'approvecode':'' } ]
    if ?code= is given the results are filtered by that approvecode
    """

    result_list: List[Dict[Any, Any]] = []
    if code:
        try:
            enrollment = await Enrollment.by_approvecode(code)
            result_list.append({"callsign": enrollment.callsign, "approvecode": code, "state": enrollment.state})
        except NotFound:
            pass
        return EnrollmentListOut(callsign_list=result_list)
    async for enrollment in Enrollment.list():
        result_list.append({"callsign": enrollment.callsign, "approvecode": "", "state": enrollment.state})

    return EnrollmentListOut(callsign_list=result_list)


def issue_enrollment_jwt(response: Response, claims: Dict[str, Any]) -> str:
    """Issue longer lived JWT and set persistent cookie"""
    enroll_issuer = Issuer()
    enroll_issuer.config.lifetime = 60 * 60 * 4  # 4 hours
    new_jwt = enroll_issuer.issue(claims)
    response.set_cookie(
        key=jwtconfig.ENVCONFIG("JWT_COOKIE_NAME"),
        value=new_jwt,
        httponly=False,
        samesite="strict",
        max_age=enroll_issuer.config.lifetime,
    )
    return new_jwt


@ENROLLMENT_ROUTER.post(
    "/init",
    response_model=EnrollmentInitOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_init(
    request: Request,
    response: Response,
    request_in: EnrollmentInitIn = Body(),
) -> EnrollmentInitOut:
    """
    Add new callsign (enrollment) to environment.
    """
    callsign = request_in.callsign

    # TODO ADD POOL NAME CHECK

    new_enrollment = await Enrollment.create_for_callsign(callsign=callsign, pool=None, extra={}, csr=request_in.csr)
    # Create JWT token for user
    claims = {"sub": callsign}
    new_jwt = issue_enrollment_jwt(response, claims)

    LOGGER.audit(  # type: ignore[attr-defined]
        "Enrollment initiated by admin",
        extra=build_audit_extra(
            action="enrollment_init",
            outcome="success",
            target=callsign,
            request=request,
        ),
    )

    return EnrollmentInitOut(callsign=new_enrollment.callsign, jwt=new_jwt, approvecode=new_enrollment.approvecode)


@ENROLLMENT_ROUTER.post(
    "/promote",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_promote(
    request: Request,
    request_in: EnrollmentPromoteIn = Body(),
) -> OperationResultResponse:
    """
    "Promote" callsign/user/enrollment to have 'admin' rights
    """
    target_callsign = request_in.callsign

    try:
        obj = await Person.by_callsign(callsign=target_callsign)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "User promotion failed - user not found",
            extra=build_audit_extra(
                action="user_promote",
                outcome="failure",
                target=target_callsign,
                request=request,
                error_code="USER_NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="User not found") from exc

    role_added = await obj.assign_role(role="admin")
    if role_added:
        LOGGER.audit(  # type: ignore[attr-defined]
            "User promoted to admin",
            extra=build_audit_extra(
                action="user_promote",
                outcome="success",
                target=target_callsign,
                request=request,
            ),
        )
        return OperationResultResponse(success=True, extra="Promote done")

    LOGGER.audit(  # type: ignore[attr-defined]
        "User promotion failed - already admin",
        extra=build_audit_extra(
            action="user_promote",
            outcome="failure",
            target=target_callsign,
            request=request,
            error_code="ALREADY_ADMIN",
        ),
    )
    reason = "Given callsign/callsign already has elevated permissions."
    LOGGER.error("{} : {}".format(request.url, reason))
    raise HTTPException(status_code=400, detail=reason)


@ENROLLMENT_ROUTER.post(
    "/demote",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_demote(
    request: Request,
    request_in: EnrollmentDemoteIn = Body(),
) -> OperationResultResponse:
    """
    "Demote" callsign/user/enrollment from having 'admin' rights. callsign_hash can be used too.
    """
    target_callsign = request_in.callsign

    try:
        obj = await Person.by_callsign(callsign=target_callsign)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "User demotion failed - user not found",
            extra=build_audit_extra(
                action="user_demote",
                outcome="failure",
                target=target_callsign,
                request=request,
                error_code="USER_NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="User not found") from exc

    _role_removed = await obj.remove_role(role="admin")
    if _role_removed:
        LOGGER.audit(  # type: ignore[attr-defined]
            "User demoted from admin",
            extra=build_audit_extra(
                action="user_demote",
                outcome="success",
                target=target_callsign,
                request=request,
            ),
        )
        return OperationResultResponse(success=True, extra="Demote done")

    LOGGER.audit(  # type: ignore[attr-defined]
        "User demotion failed - not an admin",
        extra=build_audit_extra(
            action="user_demote",
            outcome="failure",
            target=target_callsign,
            request=request,
            error_code="NOT_ADMIN",
        ),
    )
    _reason = "Given callsign/callsign_hash doesn't have 'admin' privileges to take away."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=400, detail=_reason)


@ENROLLMENT_ROUTER.post(
    "/lock",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_lock(
    request: Request,
    request_in: EnrollmentLockIn = Body(),
) -> OperationResultResponse:
    """
    Lock callsign/user/enrollment so it cannot be used anymore.
    """
    target_callsign = request_in.callsign
    actor = request.state.mtls_or_jwt.userid

    try:
        _admin_person = await Person.by_callsign(actor)
        _usr_enrollment = await Enrollment.by_callsign(callsign=target_callsign)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment lock failed - not found",
            extra=build_audit_extra(
                action="enrollment_lock",
                outcome="failure",
                target=target_callsign,
                request=request,
                error_code="NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="Enrollment not found") from exc

    await _usr_enrollment.reject(decider=_admin_person)

    LOGGER.audit(  # type: ignore[attr-defined]
        "Enrollment locked/rejected",
        extra=build_audit_extra(
            action="enrollment_lock",
            outcome="success",
            target=target_callsign,
            request=request,
        ),
    )

    return OperationResultResponse(success=True, extra="Lock task done")


@ENROLLMENT_ROUTER.post(
    "/accept",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def post_enrollment_accept(
    request: Request,
    request_in: EnrollmentAcceptIn = Body(),
) -> OperationResultResponse:
    """
    Accept callsign_hash (callsign/enrollment)
    """
    target_callsign = request_in.callsign
    actor = request.state.mtls_or_jwt.userid

    try:
        admin_user = await Person.by_callsign(callsign=actor)
        pending_enrollment = await Enrollment.by_callsign(callsign=target_callsign)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment approval failed - not found",
            extra=build_audit_extra(
                action="enrollment_approve",
                outcome="failure",
                target=target_callsign,
                request=request,
                error_code="NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="Enrollment not found") from exc

    if request_in.approvecode != pending_enrollment.approvecode:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment approval failed - invalid approvecode",
            extra=build_audit_extra(
                action="enrollment_approve",
                outcome="failure",
                target=target_callsign,
                request=request,
                error_code="INVALID_APPROVECODE",
            ),
        )
        raise HTTPException(status_code=403, detail="Invalid approval code for this enrollment")

    new_approved_user = await pending_enrollment.approve(approver=admin_user)

    LOGGER.audit(  # type: ignore[attr-defined]
        "Enrollment approved",
        extra=build_audit_extra(
            action="enrollment_approve",
            outcome="success",
            target=target_callsign,
            request=request,
        ),
    )

    return OperationResultResponse(success=True, extra=f"Approved {new_approved_user.callsign}")


@ENROLLMENT_ROUTER.post(
    "/invitecode/create",
    response_model=EnrollmentInviteCodeCreateOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def post_invite_code(request: Request) -> EnrollmentInviteCodeCreateOut:
    """
    Create a new invite code
    """

    pool = await EnrollmentPool.create_for_owner(request.state.person)

    LOGGER.audit(  # type: ignore[attr-defined]
        "Invite code created",
        extra=build_audit_extra(
            action="invitecode_create",
            outcome="success",
            request=request,
            invitecode_id=str(pool.pk),
        ),
    )

    return EnrollmentInviteCodeCreateOut(invite_code=pool.invitecode)


@ENROLLMENT_ROUTER.put("/invitecode/activate", response_model=OperationResultResponse)
async def put_activate_invite_code(
    request: Request,
    request_in: EnrollmentInviteCodeActivateIn = Body(),
) -> OperationResultResponse:
    """
    Activate an invite code
    """

    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Invite code activation failed - not found",
            extra=build_audit_extra(
                action="invitecode_activate",
                outcome="failure",
                request=request,
                error_code="NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="Invite code not found") from exc

    _activated_obj = await obj.set_active(state=True)

    if _activated_obj.active:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Invite code activated",
            extra=build_audit_extra(
                action="invitecode_activate",
                outcome="success",
                request=request,
                invitecode_id=str(obj.pk),
            ),
        )
        return OperationResultResponse(success=True, extra=f"Activated invite code {obj.pk}")

    LOGGER.audit(  # type: ignore[attr-defined]
        "Invite code activation failed",
        extra=build_audit_extra(
            action="invitecode_activate",
            outcome="failure",
            request=request,
            invitecode_id=str(obj.pk),
            error_code="ACTIVATION_FAILED",
        ),
    )
    _reason = "Error. Unable to activate given invitecode."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=500, detail=_reason)


@ENROLLMENT_ROUTER.put("/invitecode/deactivate", response_model=OperationResultResponse)
async def put_deactivate_invite_code(
    request: Request,
    request_in: EnrollmentInviteCodeDeactivateIn = Body(),
) -> OperationResultResponse:
    """
    Deactivate an invite code
    """

    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Invite code deactivation failed - not found",
            extra=build_audit_extra(
                action="invitecode_deactivate",
                outcome="failure",
                request=request,
                error_code="NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="Invite code not found") from exc

    _deactivated_obj = await obj.set_active(state=False)

    if _deactivated_obj.active is False:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Invite code deactivated",
            extra=build_audit_extra(
                action="invitecode_deactivate",
                outcome="success",
                request=request,
                invitecode_id=str(obj.pk),
            ),
        )
        return OperationResultResponse(success=True, extra=f"Disabled invite code {obj.pk}")

    LOGGER.audit(  # type: ignore[attr-defined]
        "Invite code deactivation failed",
        extra=build_audit_extra(
            action="invitecode_deactivate",
            outcome="failure",
            request=request,
            invitecode_id=str(obj.pk),
            error_code="DEACTIVATION_FAILED",
        ),
    )
    _reason = "Error. Unable to deactivate given invitecode."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=500, detail=_reason)


@ENROLLMENT_ROUTER.delete("/invitecode/{invite_code}", response_model=OperationResultResponse)
async def delete_invite_code(
    request: Request,
    invite_code: str,
) -> OperationResultResponse:
    """
    Delete an invite code
    """

    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
        pool_pk = str(obj.pk)
        await obj.delete()

        LOGGER.audit(  # type: ignore[attr-defined]
            "Invite code deleted",
            extra=build_audit_extra(
                action="invitecode_delete",
                outcome="success",
                request=request,
                invitecode_id=pool_pk,
            ),
        )

        return OperationResultResponse(success=True, extra="Invitecode was deleted")
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Invite code deletion failed - not found",
            extra=build_audit_extra(
                action="invitecode_delete",
                outcome="failure",
                request=request,
                error_code="NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="Invite code not found") from exc


@NO_JWT_ENROLLMENT_ROUTER.get("/invitecode", response_model=EnrollmentIsInvitecodeActiveOut)
async def get_invite_codes(
    params: EnrollmentIsInvitecodeActiveIn = Depends(),
) -> EnrollmentIsInvitecodeActiveOut:
    """
    /invitecode?invitecode=xxx
    Returns true/false if the code is usable or not
    """
    # Note: This is a check endpoint similar to firstuser/check-code
    # Not logging at audit level to avoid noise from normal UI flow
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
    response: Response,
    request_in: EnrollmentInviteCodeEnrollIn = Body(),
) -> EnrollmentInitOut:
    """
    Enroll with an invite code
    """
    callsign = request_in.callsign

    # CHECK IF INVITE CODE CAN BE USED
    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=request_in.invite_code)
    except NotFound as exc:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment via invitecode failed - code not found",
            extra=build_audit_extra(
                action="enrollment_invitecode",
                outcome="failure",
                target=callsign,
                request=request,
                error_code="INVITECODE_NOT_FOUND",
            ),
        )
        raise HTTPException(status_code=404, detail="Invite code not found") from exc

    if obj.active is False:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment via invitecode failed - code disabled",
            extra=build_audit_extra(
                action="enrollment_invitecode",
                outcome="failure",
                target=callsign,
                request=request,
                error_code="INVITECODE_DISABLED",
                invitecode_id=str(obj.pk),
            ),
        )
        _reason = "Error. invitecode disabled."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # CHECK THAT THE CALLSIGN CAN BE USED
    try:
        await Enrollment.by_callsign(callsign=callsign)
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment via invitecode failed - callsign taken",
            extra=build_audit_extra(
                action="enrollment_invitecode",
                outcome="failure",
                target=callsign,
                request=request,
                error_code="CALLSIGN_TAKEN",
                invitecode_id=str(obj.pk),
            ),
        )
        _reason = "Error. callsign/callsign already taken."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)
    except NotFound:
        pass

    enrollment = await obj.create_enrollment(callsign=callsign, csr=request_in.csr)

    # Create JWT token for user
    claims = {"sub": callsign}
    new_jwt = issue_enrollment_jwt(response, claims)

    LOGGER.audit(  # type: ignore[attr-defined]
        "Enrollment via invitecode successful",
        extra=build_audit_extra(
            action="enrollment_invitecode",
            outcome="success",
            actor=callsign,
            target=callsign,
            request=request,
            invitecode_id=str(obj.pk),
        ),
    )

    return EnrollmentInitOut(callsign=enrollment.callsign, jwt=new_jwt, approvecode=enrollment.approvecode)
