"""Firstuser API views."""

import asyncio
import logging
from fastapi import APIRouter, Request, Body, Depends, HTTPException

from multikeyjwt.middleware import JWTBearer, JWTPayload
from libadvian.tasks import TaskMaster

from rasenmaeher_api.web.api.firstuser.schema import (
    FirstuserCheckCodeIn,
    FirstuserCheckCodeOut,
    FirstuserAddAdminIn,
    FirstuserAddAdminOut,
)

from ....db import Person
from ....db import LoginCode
from ....db import Enrollment
from ....db.errors import NotFound

router = APIRouter()
LOGGER = logging.getLogger(__name__)


# /check-code
@router.get("/check-code", response_model=FirstuserCheckCodeOut)
async def get_check_code(
    request: Request,
    params: FirstuserCheckCodeIn = Depends(),
) -> FirstuserCheckCodeOut:
    """
    /check-code?temp_admin_code=xxxx,
    Checks if the given code can be used or not in this /firstuser api route...
    """
    try:
        res = await LoginCode.by_code(code=params.temp_admin_code)
    except NotFound:
        return FirstuserCheckCodeOut(code_ok=False)

    # This error should already be raised in LoginCode
    if not res:
        _reason = "Error. Undefined backend error q_ssjsfjwe1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Code already used err.
    if res.used_on is not None:
        _reason = "Code already used"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

    return FirstuserCheckCodeOut(code_ok=True)


# /add-admin
@router.post("/add-admin", response_model=FirstuserAddAdminOut)
async def post_admin_add(
    request: Request,
    request_in: FirstuserAddAdminIn = Body(
        None,
        examples=[FirstuserAddAdminIn.Config.schema_extra["examples"]],
    ),
    jwt: JWTPayload = Depends(JWTBearer(auto_error=True)),
) -> FirstuserAddAdminOut:
    """
    Add callsign aka username/identity. This callsign is also elevated to have managing permissions.
    """
    if not jwt.get("anon_admin_session", False):
        LOGGER.error("Requesting JWT must have admin session claim")
        raise HTTPException(status_code=403, detail="Forbidden")

    # Check that the anon_admin is added to persons. This 'user' is used to approve the
    # newly created actual new admin user.
    anon_admin_added = await Person.is_callsign_available(callsign="anon_admin")
    if not anon_admin_added:
        anon_user = await Person.create_with_cert(callsign="anon_admin", extra={})
        await anon_user.assign_role(role="anon_admin")

    # Create new admin user enrollment
    enrollment = await Enrollment.create_for_callsign(
        callsign=request_in.callsign, pool=None, extra={}, csr=request_in.csr
    )

    # Get the anon_admin 'user' that will be used to approve the new admin user
    # and approve the user
    anon_admin_user = await Person.by_callsign(callsign="anon_admin")
    new_admin = await enrollment.approve(approver=anon_admin_user)

    # FIXME Should the TaskMaster feature
    async def tms_wait() -> None:
        """Wait for background tasks to avoid race conditions"""
        tma = TaskMaster.singleton()
        while tma._tasks:  # pylint: disable=W0212
            await asyncio.sleep(0.1)

    try:
        await asyncio.wait_for(tms_wait(), timeout=3.0)
    except asyncio.TimeoutError:
        LOGGER.warning("Timed out while waiting for background tasks, continuing anyway")
    role_add_success = await new_admin.assign_role(role="admin")

    if role_add_success is False:
        reason = "Error. User already admin. This shouldn't happen..."
        LOGGER.error("{} : {}".format(request.url, reason))
        raise HTTPException(status_code=400, detail=reason)

    # Create JWT token for new admin user
    code = await LoginCode.create_for_claims(claims={"sub": request_in.callsign})

    return FirstuserAddAdminOut(admin_added=True, jwt_exchange_code=code)
