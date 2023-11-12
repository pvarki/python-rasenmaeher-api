"""People API views."""  # pylint: disable=too-many-lines
from typing import List
import logging


from fastapi import APIRouter, Depends
from libpvarki.schemas.generic import OperationResultResponse

from .schema import (
    CallSignPerson,
    PeopleListOut,
)
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from ....db import Person
from ....db.errors import BackendError

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSorJWT(auto_error=True))])


@router.get(
    "/list", response_model=PeopleListOut, dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))]
)
async def request_people_list() -> PeopleListOut:
    """
    /list
    Return people/list.
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', "roles": ["str"] 'extra':'x' } ]
    """

    _people_list = Person.list()

    _result_list: List[CallSignPerson] = []
    async for _x in _people_list:
        _roles = [str(role) async for role in _x.roles() if role is not None]
        _person = CallSignPerson(callsign=_x.callsign, roles=_roles, extra=_x.extra)
        _result_list.append(_person)

    return PeopleListOut(callsign_list=_result_list)


@router.delete(
    "/{callsign}",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def delete_person(callsign: str) -> OperationResultResponse:
    """delete==revoke a callsign"""
    person = await Person.by_callsign(callsign)
    try:
        deleted = await person.delete()
        return OperationResultResponse(success=deleted)
    except BackendError as exc:
        LOGGER.error("Backend failure: {}".format(exc))
        return OperationResultResponse(success=False, error=str(exc))
