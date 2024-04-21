"""Enrollment API views."""  # pylint: disable=too-many-lines
from typing import List, Optional
import logging


from fastapi import APIRouter, Request, Body, Depends

from libpvarki.schemas.generic import OperationResultResponse
from .schema import (
    EnrollmentInitOut,
    EnrollmentIsInvitecodeActiveOut,
    EnrollmentInviteCodeCreateOut,
    EnrollmentInviteCodeEnrollIn,
    EnrollmentPoolListOut,
    EnrollmentPoolListItem,
)
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from .invitecode_helpers import (
    list_invitepools,
    enroll_with_invite_code,
    check_invite_code,
    delete_invite_code,
    deactivate_invite_code,
    activate_invite_code,
    new_invite_code,
)

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
    pools: List[EnrollmentPoolListItem] = await list_invitepools(owner_cs=owner_cs)
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
    code_response: EnrollmentInviteCodeCreateOut = await new_invite_code(request)
    return code_response


# POST /invite-code/:inviteCode:/activate AKTIVOI KOODI
@ENROLLMENT_ROUTER.put("/{invite_code}/activate", response_model=OperationResultResponse)
async def put_activate_invite_code(
    invite_code: str,
    request: Request,
) -> OperationResultResponse:
    """
    Activate an invite code
    """
    op_response: OperationResultResponse = await activate_invite_code(invite_code=invite_code, request=request)
    return op_response


# POST /invite-code/:inviteCode:/deactivate DEAKTIVOI KOODI
@ENROLLMENT_ROUTER.put("/{invite_code}/deactivate", response_model=OperationResultResponse)
async def put_deactivate_invite_code(
    invite_code: str,
    request: Request,
) -> OperationResultResponse:
    """
    Deactivate an invite code
    """
    op_response: OperationResultResponse = await deactivate_invite_code(invite_code=invite_code, request=request)
    return op_response


# DELETE /invite-code/:inviteCode: POISTA KOODI
@ENROLLMENT_ROUTER.delete("/{invite_code}", response_model=OperationResultResponse)
async def del_invite_code(
    # request: Request,
    invite_code: str,
) -> OperationResultResponse:
    """
    Delete an invite code
    """
    op_response: OperationResultResponse = await delete_invite_code(invite_code=invite_code)
    return op_response


# GET /invite-code/:inviteCode: ONKO KOODI AKTIIVINEN
@NO_JWT_ENROLLMENT_ROUTER.get("/{invite_code}", response_model=EnrollmentIsInvitecodeActiveOut)
async def get_invite_codes(
    invite_code: str,
) -> EnrollmentIsInvitecodeActiveOut:
    """
    /:invitecode:
    Returns true/false if the code is usable or not
    """
    is_active: EnrollmentIsInvitecodeActiveOut = await check_invite_code(invite_code=invite_code)
    return is_active


@NO_JWT_ENROLLMENT_ROUTER.post("/{invite_code}/enroll", response_model=EnrollmentInitOut)
async def post_invitecode_enroll(
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
    enroll_init: EnrollmentInitOut = await enroll_with_invite_code(
        invite_code=invite_code, callsign=request_in.callsign, request=request
    )
    return enroll_init
