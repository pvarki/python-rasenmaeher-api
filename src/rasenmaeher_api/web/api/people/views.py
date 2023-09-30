"""People API views."""  # pylint: disable=too-many-lines
from typing import Dict, List, Any, Union
import logging


from fastapi import APIRouter, Request, Depends, HTTPException

from .schema import (
    PeopleListOut,
)
from ..middleware.mtls import MTLSorJWT
from ....db import Person

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])


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


@router.get("/list", response_model=PeopleListOut)
async def request_people_list(
    request: Request,
) -> PeopleListOut:
    """
    /list
    Return people/list.
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', "roles": ["str"] 'extra':'x' } ]
    """

    await check_management_permissions(
        raise_exeption=True, callsign=request.state.mtls_or_jwt.userid, required_role="admin"
    )

    _people_list = Person.list()

    _result_list: List[Dict[Any, Any]] = []
    async for _x in _people_list:
        _result_list.append({"callsign": _x.callsign, "roles": _x.roles, "extra": _x.extra})

    return PeopleListOut(callsign_list=_result_list)
