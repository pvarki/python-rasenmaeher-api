""" v1v2 Code reusability """
from typing import Dict, List, Optional
import logging
import uuid

from fastapi import Request, HTTPException

from multikeyjwt import Issuer

from libpvarki.schemas.generic import OperationResultResponse

from .schema import (
    EnrollmentPoolListItem,
    EnrollmentInitOut,
    EnrollmentInviteCodeCreateOut,
    EnrollmentIsInvitecodeActiveOut,
)
from ....db import Person
from ....db import Enrollment, EnrollmentPool
from ....db.errors import NotFound

LOGGER = logging.getLogger(__name__)


async def list_invitepools(owner_cs: Optional[str] = None) -> List[EnrollmentPoolListItem]:
    """List current EnrollmentPools aka invitecodes"""
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
    return pools


async def enroll_with_invite_code(
    invite_code: str,
    callsign: str,
    request: Request,
) -> EnrollmentInitOut:
    """
    Enroll with an invite code
    """

    # CHECK IF INVITE CODE CAN BE USED
    obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
    if obj.active is False:
        reason = "Error. invitecode disabled."
        LOGGER.error("{} : {}".format(request.url, reason))
        raise HTTPException(status_code=400, detail=reason)

    # CHECK THAT THE CALLSIGN CAN BE USED
    try:
        await Enrollment.by_callsign(callsign=callsign)
        reason = "Error. callsign/callsign already taken."
        LOGGER.error("{} : {}".format(request.url, reason))
        raise HTTPException(status_code=400, detail=reason)
    except NotFound:
        pass

    enrollment = await obj.create_enrollment(callsign=callsign)

    # Create JWT token for user
    claims = {"sub": callsign}
    new_jwt = Issuer.singleton().issue(claims)

    return EnrollmentInitOut(callsign=enrollment.callsign, jwt=new_jwt, approvecode=enrollment.approvecode)


async def new_invite_code(request: Request) -> EnrollmentInviteCodeCreateOut:
    """
    Create a new invite code
    """
    pool = await EnrollmentPool.create_for_owner(request.state.person)
    return EnrollmentInviteCodeCreateOut(invite_code=pool.invitecode)


async def activate_invite_code(
    invite_code: str,
    request: Request,
) -> OperationResultResponse:
    """
    Activate an inactive invite code
    """
    obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
    activated_obj = await obj.set_active(state=True)

    if activated_obj.active:
        return OperationResultResponse(success=True, extra=f"Activated {invite_code}")

    reason = "Error. Unable to activate given invitecode."
    LOGGER.error("{} : {}".format(request.url, reason))
    raise HTTPException(status_code=500, detail=reason)


# /invitecode/deactivate
async def deactivate_invite_code(
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

    reason = "Error. Unable to deactivate given invitecode."
    LOGGER.error("{} : {}".format(request.url, reason))
    raise HTTPException(status_code=500, detail=reason)


# /invitecode/:code: -XDELETE
async def delete_invite_code(
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


# /invitecode/:code:  IS ACTIVE
async def check_invite_code(
    invite_code: str,
) -> EnrollmentIsInvitecodeActiveOut:
    """
    Check the invite code
    """
    try:
        obj = await EnrollmentPool.by_invitecode(invitecode=invite_code)
        if obj.active:
            return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=True)
    except NotFound:
        pass
    return EnrollmentIsInvitecodeActiveOut(invitecode_is_active=False)
