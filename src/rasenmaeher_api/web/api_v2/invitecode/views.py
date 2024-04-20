"""Enrollment API views."""  # pylint: disable=too-many-lines
from typing import Dict, List, Optional
import logging
import uuid


from fastapi import APIRouter, Request, Body, Depends, HTTPException
from multikeyjwt import Issuer

from libpvarki.schemas.generic import OperationResultResponse
from .schema import (
    # EnrollmentStatusIn,
    # EnrollmentStatusOut,
    # EnrollmentAcceptIn,
    # EnrollmentGenVerifiOut,
    # EnrollmentShowVerificationCodeIn,
    # EnrollmentShowVerificationCodeOut,
    # EnrollmentHaveIBeenAcceptedOut,
    # EnrollmentListOut,
    # EnrollmentPromoteIn,
    # EnrollmentInitIn,
    EnrollmentInitOut,
    # EnrollmentDemoteIn,
    # EnrollmentLockIn,
    # EnrollmentIsInvitecodeActiveIn,
    EnrollmentIsInvitecodeActiveOut,
    EnrollmentInviteCodeCreateOut,
    EnrollmentInviteCodeEnrollIn,
    # EnrollmentInviteCodeActivateIn,
    # EnrollmentInviteCodeDeactivateIn,
    EnrollmentPoolListOut,
    EnrollmentPoolListItem,
)
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from ....db import Person
from ....db import Enrollment, EnrollmentPool
from ....db.errors import NotFound

LOGGER = logging.getLogger(__name__)

ENROLLMENT_ROUTER = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])
NO_JWT_ENROLLMENT_ROUTER = APIRouter()


# GET /invite-code PALAUTA OLEMASSA OLEVAT KOODIT
@ENROLLMENT_ROUTER.get(
    "",
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
            owner_cache[pool.owner] = await Person.by_pk(pool.owner)
        pools.append(
            EnrollmentPoolListItem(
                invitecode=pool.invitecode,
                active=pool.active,
                owner_cs=owner_cache[pool.owner].callsign,
                created=pool.created.isoformat(),
            )
        )
    return EnrollmentPoolListOut(pools=pools)


# POST /invite-code LUO UUSI INVITE CODE
@ENROLLMENT_ROUTER.post(
    "",
    response_model=EnrollmentInviteCodeCreateOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def post_invite_code(request: Request) -> EnrollmentInviteCodeCreateOut:
    """
    Create a new invite code
    """
    pool = await EnrollmentPool.create_for_owner(request.state.person)
    return EnrollmentInviteCodeCreateOut(invite_code=pool.invitecode)


# POST /invite-code/:inviteCode:/activate AKTIVOI KOODI
@ENROLLMENT_ROUTER.put("/{invite_code}/activate", response_model=OperationResultResponse)
async def put_activate_invite_code(
    invite_code: str,
    request: Request,
) -> OperationResultResponse:
    """
    Activate an invite code
    """
    obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
    _activated_obj = await obj.set_active(state=True)

    if _activated_obj.active:
        return OperationResultResponse(success=True, extra=f"Activated {invite_code}")

    _reason = "Error. Unable to activate given invitecode."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=500, detail=_reason)


# POST /invite-code/:inviteCode:/deactivate DEAKTIVOI KOODI
@ENROLLMENT_ROUTER.put("/{invite_code}/deactivate", response_model=OperationResultResponse)
async def put_deactivate_invite_code(
    invite_code: str,
    request: Request,
) -> OperationResultResponse:
    """
    Deactivate an invite code
    """
    obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
    _deactivated_obj = await obj.set_active(state=False)

    if _deactivated_obj.active is False:
        return OperationResultResponse(success=True, extra=f"Disabled {invite_code}")

    _reason = "Error. Unable to deactivate given invitecode."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=500, detail=_reason)


# DELETE /invite-code/:inviteCode: POISTA KOODI
@ENROLLMENT_ROUTER.delete("/{invite_code}", response_model=OperationResultResponse)
async def delete_invite_code(
    # request: Request,
    invite_code: str,
) -> OperationResultResponse:
    """
    Delete an invite code
    """
    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
        await obj.delete()
        return OperationResultResponse(success=True, extra="Invitecode was deleted")
    except NotFound:
        return OperationResultResponse(success=False, extra="No such invitecode found")


# GET /invite-code/:inviteCode: ONKO KOODI AKTIIVINEN
@NO_JWT_ENROLLMENT_ROUTER.get("/{invite_code}", response_model=EnrollmentIsInvitecodeActiveOut)
async def get_invite_codes(
    invite_code: str,
) -> EnrollmentIsInvitecodeActiveOut:
    """
    /invitecode?invitecode=xxx
    Returns true/false if the code is usable or not
    """
    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
        if obj.active:
            return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=True)
    except NotFound:
        pass
    return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=False)


# GET /invite-code/:inviteCode:/enroll ENROLL USING CODE
@NO_JWT_ENROLLMENT_ROUTER.post("/{invite_code}/enroll", response_model=EnrollmentInitOut)
async def post_enroll_invite_code(
    invite_code: str,
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
    obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
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
