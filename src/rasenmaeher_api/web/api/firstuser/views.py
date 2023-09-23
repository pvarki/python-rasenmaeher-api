"""Firstuser API views."""
import logging
import string
from fastapi import APIRouter, Request, Body, Depends, HTTPException

from multikeyjwt.middleware import JWTBearer, JWTPayload

from rasenmaeher_api.web.api.firstuser.schema import (
    FirstuserCheckCodeIn,
    FirstuserCheckCodeOut,
    FirstuserAddAdminIn,
    FirstuserAddAdminOut,
)

from ....db import Person
from ....db import LoginCode


router = APIRouter()
LOGGER = logging.getLogger(__name__)
CODE_CHAR_COUNT = 12  # TODO: Make configurable ??
CODE_ALPHABET = string.ascii_uppercase + string.digits


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
    _res = await LoginCode.by_code(code=params.temp_admin_code)

    # This error should already be raised in LoginCode
    if not _res:
        _reason = "Error. Undefined backend error q_ssjsfjwe1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Code alreay used err.
    if _res.used_on is not None:
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
    Add work_id aka username/identity. This work_id is also elevated to have managing permissions.
    """
    if not jwt.get("anon_admin_session", False):
        LOGGER.error("Requesting JWT must have admin session claim")
        raise HTTPException(status_code=403, detail="Forbidden")

    _user = await Person.create_with_cert(callsign=request_in.work_id, extra={})

    _role_success = await _user.assign_role(role="admin")
    if _role_success is False:
        _reason = "Error. User already admin. This shouldn't happen..."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)
    _code = await LoginCode.create_for_claims(claims={"sub": request_in.work_id})

    return FirstuserAddAdminOut(admin_added=True, jwt_exchange_code=_code)
