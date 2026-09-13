"""Enrollment API views."""

import logging
import uuid
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from libpvarki.schemas.generic import OperationResultResponse
from multikeyjwt import Issuer
from multikeyjwt import config as jwtconfig

from ....db import Enrollment, EnrollmentPool, EnrollmentState, Person
from ....db.errors import Deleted, NotFound
from ....rmsettings import RMSettings
from ..middleware.datatypes import MTLSorJWTPayloadType
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from ..utils.auditcontext import build_audit_extra
from ..utils.csr_utils import verify_csr
from .schema import (
    EnrollmentAcceptIn,
    EnrollmentAcceptResultOut,
    EnrollmentDemoteIn,
    EnrollmentGenVerifiOut,
    EnrollmentHaveIBeenAcceptedOut,
    EnrollmentInitIn,
    EnrollmentInitOut,
    EnrollmentInviteCodeActivateIn,
    EnrollmentInviteCodeCreateOut,
    EnrollmentInviteCodeDeactivateIn,
    EnrollmentInviteCodeEnrollIn,
    EnrollmentIsInvitecodeActiveIn,
    EnrollmentIsInvitecodeActiveOut,
    EnrollmentListOut,
    EnrollmentLockIn,
    EnrollmentPoolListItem,
    EnrollmentPoolListOut,
    EnrollmentPromoteIn,
    EnrollmentShowVerificationCodeIn,
    EnrollmentShowVerificationCodeOut,
    EnrollmentStatusIn,
    EnrollmentStatusOut,
)

LOGGER = logging.getLogger(__name__)

ENROLLMENT_ROUTER = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])
NO_JWT_ENROLLMENT_ROUTER = APIRouter()


@ENROLLMENT_ROUTER.get(
    "/pools",
    response_model=EnrollmentPoolListOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def list_pools(owner_cs: str | None = None) -> EnrollmentPoolListOut:
    """List EnrollmentPools (aka invitecodes)"""
    owner: Person | None = None
    if owner_cs:
        owner = await Person.by_callsign(owner_cs)
    pools: list[EnrollmentPoolListItem] = []
    owner_cache: dict[uuid.UUID, Person] = {}
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
        LOGGER.error(f"{request.url} : {_reason}")
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
async def request_enrollment_list(code: str | None = None) -> EnrollmentListOut:
    """
    /list
    Return users/callsign/enrollments. If 'accepted' has something else than '', it has been accepted.
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', 'state':'init', 'approvecode':'' } ]
    if ?code= is given the results are filtered by that approvecode
    """

    result_list: list[dict[Any, Any]] = []
    if code:
        try:
            enrollment = await Enrollment.by_approvecode(code)
            result_list.append(
                {
                    "callsign": enrollment.callsign,
                    "approvecode": code,
                    "state": enrollment.state,
                    "mdm": enrollment.planned_for_mdm,
                }
            )
        except NotFound:
            pass
        return EnrollmentListOut(callsign_list=result_list)
    async for enrollment in Enrollment.list():
        # mdm marks a device an admin planned for MDM enrolment. It is waiting for the device's own
        # CSR through the agent, not for a human to approve it, and approving it by hand is refused.
        result_list.append(
            {
                "callsign": enrollment.callsign,
                "approvecode": "",
                "state": enrollment.state,
                "mdm": enrollment.planned_for_mdm,
            }
        )

    return EnrollmentListOut(callsign_list=result_list)


def issue_enrollment_jwt(response: Response, claims: dict[str, Any]) -> str:
    """Issue longer lived JWT and set persistent cookie"""
    enroll_issuer = Issuer()
    enroll_issuer.config.lifetime = RMSettings.singleton().enrollment_lifetime
    new_jwt = enroll_issuer.issue(claims)
    response.set_cookie(
        key=jwtconfig.ENVCONFIG("JWT_COOKIE_NAME"),
        value=new_jwt,
        httponly=True,
        secure=True,
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

    extra: dict[str, Any] = {"mdm": True} if request_in.mdm else {}
    new_enrollment = await Enrollment.create_for_callsign(callsign=callsign, pool=None, extra=extra, csr=request_in.csr)
    # Create JWT token for user. Never for a device planned for MDM enrolment: that token is a live
    # credential for the callsign, the device will never use it (it receives a certificate through
    # the agent), and issuing it here also overwrites the calling admin's own session cookie, which
    # is unhelpful when planning three hundred of them.
    new_jwt = "" if request_in.mdm else issue_enrollment_jwt(response, {"sub": callsign})

    LOGGER.audit(  # type: ignore[attr-defined]
        "Enrollment initiated by admin",
        extra=build_audit_extra(
            action="enrollment_init",
            outcome="success",
            target=callsign,
            request=request,
            mdm=request_in.mdm,
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
    LOGGER.error(f"{request.url} : {reason}")
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
    LOGGER.error(f"{request.url} : {_reason}")
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


# One detail for every MDM refusal. The agent sees only "no", so a caller holding the agent
# certificate cannot use the reply to learn which callsigns exist or which are planned. The real
# reason goes to the audit log.
MDM_REFUSED = "Not a device enrolment this agent may complete"


def mdm_agent_cn(request: Request) -> str | None:
    """The caller's CN if it is a configured MDM enrolment agent, otherwise None

    The agent authenticates with its own client certificate from the deployment CA -- in a meshed
    deployment, with its mesh identity, which reaches us through the same header. It is not a
    Person and holds no role. The single thing this CN may do is complete a device enrolment an
    admin has already planned.
    """
    payload = getattr(request.state, "mtls_or_jwt", None)
    if not payload or payload.type != MTLSorJWTPayloadType.MTLS or not payload.userid:
        return None
    if payload.userid not in RMSettings.singleton().mdm_agent_cn_set:
        return None
    return str(payload.userid)


def same_public_key(csrpem: str, certpem: str) -> bool:
    """Does this CSR carry the key that was certified"""
    csr = x509.load_pem_x509_csr(csrpem.encode("utf-8"))
    cert = x509.load_pem_x509_certificate(certpem.encode("utf-8"))
    encoding, fmt = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    return csr.public_key().public_bytes(encoding, fmt) == cert.public_key().public_bytes(encoding, fmt)


@ENROLLMENT_ROUTER.post(
    "/accept",
    response_model=EnrollmentAcceptResultOut,
)
async def post_enrollment_accept(
    request: Request,
    request_in: EnrollmentAcceptIn = Body(),
) -> EnrollmentAcceptResultOut:
    """
    Accept callsign_hash (callsign/enrollment)

    Two kinds of caller. An admin approving a person by hand, which is unchanged. Or the MDM
    enrolment agent completing a device enrolment an admin planned, supplying the CSR the device
    generated. Authorisation for the second is the agent's own certificate, checked here rather
    than inferred from where the request came from.
    """
    agent_cn = mdm_agent_cn(request)
    if agent_cn:
        return await accept_as_mdm_agent(request, request_in, agent_cn)
    admin_user = await ValidUser(auto_error=True, require_roles=["admin"])(request)
    if not admin_user:
        # ValidUser returns None without a Person for product certificates; they have no business
        # approving enrollments and used to fall through to a confusing 404.
        raise HTTPException(status_code=403, detail="Not authenticated")
    return await accept_as_admin(request, request_in, admin_user)


async def accept_as_admin(
    request: Request,
    request_in: EnrollmentAcceptIn,
    admin_user: Person,
) -> EnrollmentAcceptResultOut:
    """An admin approves an enrollment by hand, with the code the enrollee gave them"""
    target_callsign = request_in.callsign

    try:
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

    if pending_enrollment.planned_for_mdm and not pending_enrollment.csr:
        # Approving it here would have rasenmaeher generate the keypair, and the device could then
        # never have this callsign: callsigns are unique and are never released.
        LOGGER.audit(  # type: ignore[attr-defined]
            "Enrollment approval refused - planned for MDM",
            extra=build_audit_extra(
                action="enrollment_approve",
                outcome="failure",
                actor=admin_user.callsign,
                target=target_callsign,
                request=request,
                error_code="PLANNED_FOR_MDM",
            ),
        )
        raise HTTPException(
            status_code=409,
            detail="This device enrolls itself through the MDM, approving it by hand would spend the callsign",
        )

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

    return EnrollmentAcceptResultOut(success=True, extra=f"Approved {new_approved_user.callsign}")


async def accept_as_mdm_agent(  # pylint: disable=too-many-return-statements
    request: Request,
    request_in: EnrollmentAcceptIn,
    agent_cn: str,
) -> EnrollmentAcceptResultOut:
    """The MDM agent completes a device enrollment an admin planned

    Everything is checked before the enrollment is claimed, so a request we are going to refuse
    never consumes the callsign.
    """
    target_callsign = request_in.callsign

    def refuse(status_code: int, error_code: str, detail: str = MDM_REFUSED) -> HTTPException:
        LOGGER.audit(  # type: ignore[attr-defined]
            "MDM enrollment refused",
            extra=build_audit_extra(
                action="enrollment_mdm_accept",
                outcome="failure",
                actor=agent_cn,
                target=target_callsign,
                request=request,
                error_code=error_code,
            ),
        )
        return HTTPException(status_code=status_code, detail=detail)

    csrpem = request_in.csr
    if not csrpem:
        raise refuse(400, "CSR_MISSING", "The device CSR is required")

    try:
        planned = await Enrollment.by_callsign(callsign=target_callsign)
    except NotFound as exc:
        raise refuse(403, "NOT_PLANNED") from exc
    if not planned.planned_for_mdm:
        raise refuse(403, "NOT_PLANNED_FOR_MDM")
    if not verify_csr(csrpem, planned.callsign):
        raise refuse(403, "CSR_SUBJECT")

    if planned.state != EnrollmentState.PENDING or planned.csr:
        return await mdm_repeat(request, csrpem, planned, refuse)

    if not await planned.claim_with_csr(csrpem):
        raise refuse(403, "ALREADY_CLAIMED")
    # Re-read: approve() takes the CSR off the instance, and the claim was a separate statement.
    claimed = await Enrollment.by_callsign(callsign=target_callsign)
    try:
        person = await claimed.approve(approver=None)
    except Exception:
        # Issuing is a network call to the CA. Let the device's next attempt have the callsign
        # back -- unless a Person row was already committed, which mdm_repeat then reports.
        await claimed.release_claim()
        raise

    LOGGER.audit(  # type: ignore[attr-defined]
        "Enrollment completed by MDM agent",
        extra=build_audit_extra(
            action="enrollment_mdm_accept",
            outcome="success",
            actor=agent_cn,
            target=target_callsign,
            request=request,
        ),
    )
    return EnrollmentAcceptResultOut(
        success=True,
        extra=f"Approved {person.callsign}",
        certificate=person.certfile.read_text(encoding="utf-8"),
    )


async def mdm_repeat(
    request: Request,
    csrpem: str,
    planned: Enrollment,
    refuse: Any,
) -> EnrollmentAcceptResultOut:
    """The agent asked again for a callsign that is no longer waiting

    Almost always the reply was lost on the way back and the MDM repeated the identical request,
    so hand the same certificate over again -- it is public, and the alternative is a device
    stranded behind "callsign already taken".
    """
    _ = request
    try:
        person = await Person.by_callsign(planned.callsign)
    except (NotFound, Deleted) as exc:
        raise refuse(403, "ALREADY_DECIDED") from exc
    if not person.certfile.exists():
        # The Person row is committed before the CA is called and that commit cannot be rolled
        # back, so a CA failure at just the wrong moment leaves the callsign unusable for good.
        raise refuse(409, "CALLSIGN_SPENT", "That callsign was spent by a failed issue, plan another")
    certpem = person.certfile.read_text(encoding="utf-8")
    if not same_public_key(csrpem, certpem):
        raise refuse(403, "DIFFERENT_KEY")
    return EnrollmentAcceptResultOut(
        success=True,
        extra=f"Approved {person.callsign}",
        certificate=certpem,
    )


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


@ENROLLMENT_ROUTER.put(
    "/invitecode/activate",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
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
    LOGGER.error(f"{request.url} : {_reason}")
    raise HTTPException(status_code=500, detail=_reason)


@ENROLLMENT_ROUTER.put(
    "/invitecode/deactivate",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
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
    LOGGER.error(f"{request.url} : {_reason}")
    raise HTTPException(status_code=500, detail=_reason)


@ENROLLMENT_ROUTER.delete(
    "/invitecode/{invite_code}",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
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
        LOGGER.error(f"{request.url} : {_reason}")
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
        LOGGER.error(f"{request.url} : {_reason}")
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
