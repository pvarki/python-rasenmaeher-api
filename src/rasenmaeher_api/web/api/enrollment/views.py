"""Enrollment API views."""

import logging
import re
import uuid
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from libpvarki.schemas.generic import OperationResultResponse
from multikeyjwt import Issuer
from multikeyjwt import config as jwtconfig

from ....db import Enrollment, EnrollmentPool, MdmEnrolment, Person
from ....db.errors import CallsignReserved, Deleted, NotFound
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
    MdmSettingsIn,
    MdmSettingsOut,
)

LOGGER = logging.getLogger(__name__)
#: The name an MDM gives a device becomes its callsign in every product, so it has to be one they all
#: take. Hyphens and 32 characters fit the enrollment-specific ID a work-profile phone reports in place
#: of its serial; no hyphen at either end, so a name never reads as a command-line flag.
MDM_CALLSIGN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{1,30}[A-Za-z0-9]")

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
            result_list.append({"callsign": enrollment.callsign, "approvecode": code, "state": enrollment.state})
        except NotFound:
            pass
        return EnrollmentListOut(callsign_list=result_list)
    async for enrollment in Enrollment.list():
        result_list.append({"callsign": enrollment.callsign, "approvecode": "", "state": enrollment.state})

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
# certificate cannot use the reply to learn which callsigns exist. The real reason goes to the
# audit log.
MDM_REFUSED = "Not a device enrolment this agent may complete"


def mdm_agent_cn(request: Request) -> str | None:
    """The caller's CN if it is a configured MDM enrolment agent, otherwise None

    The agent authenticates with its own client certificate from the deployment CA -- in a meshed
    deployment, with its mesh identity, which reaches us through the same header. It is not a
    Person and holds no role. The single thing this CN may do is enrol a device while an admin has
    MDM enrolment open.
    """
    payload = getattr(request.state, "mtls_or_jwt", None)
    if not payload or payload.type != MTLSorJWTPayloadType.MTLS or not payload.userid:
        return None
    if payload.userid not in RMSettings.singleton().mdm_agent_cn_set:
        return None
    return str(payload.userid)


def device_csr_overreach(csrpem: str) -> str | None:
    """Is this request asking for more than a device identity, or None if it is not

    The signer picks its profile from what the request asks for, so a request that asks for server
    authentication is issued one, and nothing replaces the names it carries. On this path the
    request arrived from the public SCEP endpoint and its contents are entirely the caller's
    choice, so the shape of what gets issued cannot be one of the things they choose.

    A genuine device request from an MDM asks for none of this: it carries a subject and a public
    key and nothing else.
    """
    try:
        csr = x509.load_pem_x509_csr(csrpem.encode("utf-8"))
    except ValueError as exc:
        return f"the request does not parse: {exc}"
    try:
        usages = csr.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if [usage for usage in usages if usage != ExtendedKeyUsageOID.CLIENT_AUTH]:
            return "the request asks for a key usage beyond client authentication"
    except x509.ExtensionNotFound:
        pass
    try:
        csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return "the request carries subject alternative names"
    except x509.ExtensionNotFound:
        pass
    try:
        basic = csr.extensions.get_extension_for_class(x509.BasicConstraints).value
        if basic.ca:
            return "the request asks to be a certificate authority"
    except x509.ExtensionNotFound:
        pass
    return None


def weak_device_key(csrpem: str) -> bool:
    """Is this a key whose private half anybody could recover: RSA under 2048 bits, a curve under 256

    Whoever recovers it is the device, for as long as the certificate lasts.
    """
    key = x509.load_pem_x509_csr(csrpem.encode("utf-8")).public_key()
    if isinstance(key, rsa.RSAPublicKey):
        return key.key_size < 2048
    if isinstance(key, ec.EllipticCurvePublicKey):
        return key.curve.key_size < 256
    return not isinstance(key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey))


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
    enrolment agent enrolling a device, supplying the CSR the device generated. Authorisation for
    the second is the agent's own certificate, checked here rather than inferred from where the
    request came from.
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


async def accept_as_mdm_agent(
    request: Request,
    request_in: EnrollmentAcceptIn,
    agent_cn: str,
) -> EnrollmentAcceptResultOut:
    """The MDM agent enrols a device under the name its MDM gave it

    The MDM decides who a device is: the common name of the device's own request becomes its
    callsign. What stands between the public SCEP endpoint and a new identity is the window an
    admin opened and the challenge, so keep the window short. A name already in use is never handed
    to a second key, and everything is checked before anything is written.
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

    # First, so that while enrolment is closed nothing behind it can be probed.
    enrolment = await MdmEnrolment.current()
    if not enrolment.is_open:
        raise refuse(403, "MDM_CLOSED")
    if not enrolment.accepts(request_in.challenge):
        raise refuse(403, "WRONG_CHALLENGE")

    csrpem = request_in.csr
    if not csrpem:
        raise refuse(400, "CSR_MISSING", "The device CSR is required")
    if not MDM_CALLSIGN.fullmatch(target_callsign):
        raise refuse(403, "CALLSIGN_FORMAT")
    if not verify_csr(csrpem, target_callsign):
        raise refuse(403, "CSR_SUBJECT")
    if device_csr_overreach(csrpem):
        raise refuse(403, "CSR_OVERREACH")
    if weak_device_key(csrpem):
        raise refuse(403, "CSR_WEAK_KEY")

    try:
        existing = await Person.by_callsign(target_callsign, allow_deleted=True)
    except NotFound:
        existing = None
    if existing:
        return await mdm_repeat(csrpem, existing, refuse)
    try:
        await Enrollment.by_callsign(target_callsign)
    except (NotFound, Deleted):
        pass
    else:
        # A person enrolled, or is waiting for an admin, under this name; taking it would strand them.
        raise refuse(403, "CALLSIGN_PENDING")

    try:
        person = await Person.create_with_cert(target_callsign, extra={"mdm": True}, csrpem=csrpem)
    except CallsignReserved as exc:
        raise refuse(403, "CALLSIGN_RESERVED") from exc

    LOGGER.audit(  # type: ignore[attr-defined]
        "Device enrolled by MDM agent",
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


async def mdm_repeat(csrpem: str, person: Person, refuse: Any) -> EnrollmentAcceptResultOut:
    """The agent asked for a name that is already somebody's

    Almost always the reply was lost on the way back and the MDM repeated the identical request,
    so hand the same certificate over again -- it is public, and the alternative is a device
    stranded behind "callsign already taken". Any other key is somebody else.
    """
    if person.deleted:
        raise refuse(403, "CALLSIGN_REVOKED")
    if not person.certfile.exists():
        # The Person row is committed before the CA is called and that commit cannot be rolled
        # back, so a CA failure at just the wrong moment leaves the name unusable for good.
        raise refuse(409, "CALLSIGN_SPENT", "That name was spent by a failed issue, give the device another")
    certpem = person.certfile.read_text(encoding="utf-8")
    if not same_public_key(csrpem, certpem):
        raise refuse(403, "CALLSIGN_TAKEN")
    return EnrollmentAcceptResultOut(
        success=True,
        extra=f"Approved {person.callsign}",
        certificate=certpem,
    )


async def human_admin(request: Request) -> Person:
    """An admin who is a person

    ValidUser lets a product certificate through without a Person or a role check. Products have
    no business switching device enrolment: that is the operator's decision.
    """
    admin = await ValidUser(auto_error=True, require_roles=["admin"])(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return admin


def _mdm_settings(request: Request, enrolment: MdmEnrolment) -> MdmSettingsOut:
    host = (request.url.hostname or "").removeprefix("mtls.")
    return MdmSettingsOut(
        scep_url=f"https://{host}/scep" if host else "",
        challenge=enrolment.challenge,
        open_until=enrolment.open_until if enrolment.is_open else None,
    )


@ENROLLMENT_ROUTER.get(
    "/mdm-settings",
    response_model=MdmSettingsOut,
    dependencies=[Depends(human_admin)],
)
async def request_mdm_settings(request: Request) -> MdmSettingsOut:
    """What to configure the MDM with, and until when devices may enrol through it

    Admin only, though the challenge is no secret: there is no reason for anybody else to read it.
    """
    return _mdm_settings(request, await MdmEnrolment.current())


@ENROLLMENT_ROUTER.put("/mdm-settings", response_model=MdmSettingsOut)
async def put_mdm_settings(
    request: Request,
    request_in: MdmSettingsIn = Body(),
    admin: Person = Depends(human_admin),
) -> MdmSettingsOut:
    """Open MDM enrolment for some hours, or close it with 0

    It closes itself when the time runs out, so a forgotten window does not stay open.
    """
    enrolment = await (await MdmEnrolment.current()).open_for(request_in.hours)
    LOGGER.audit(  # type: ignore[attr-defined]
        "MDM enrolment opened" if request_in.hours else "MDM enrolment closed",
        extra=build_audit_extra(
            action="mdm_enrolment_window",
            outcome="success",
            actor=admin.callsign,
            request=request,
            hours=request_in.hours,
        ),
    )
    return _mdm_settings(request, enrolment)


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
