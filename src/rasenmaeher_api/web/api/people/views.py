"""People API views."""  # pylint: disable=too-many-lines

from typing import List, Optional
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
async def request_people_list(revoked: bool = False) -> PeopleListOut:
    """
    /list
    Return people/list.
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', "roles": ["str"] 'extra':'x' } ]

    if revoked is given will list *also* revoked users.
    """

    result_list: List[CallSignPerson] = []
    async for dbperson in Person.list(include_deleted=revoked):
        if dbperson.callsign == "anon_admin":
            # Skip the "dummy" user for anon_admin
            continue
        roles = await dbperson.roles_set()
        revoked_date: Optional[str] = None
        if dbperson.deleted:
            revoked_date = dbperson.deleted.isoformat()
        listitem = CallSignPerson(
            callsign=dbperson.callsign, roles=list(roles), extra=dbperson.extra, revoked=revoked_date
        )
        result_list.append(listitem)

    return PeopleListOut(callsign_list=result_list)


@router.get(
    "/list/revoked",
    response_model=PeopleListOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_people_list_onlydeleted() -> PeopleListOut:
    """
    /list/revoked
    Return list of deleted/revoked users
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', "roles": ["str"] 'extra':'x' } ]

    """

    result_list: List[CallSignPerson] = []
    async for dbperson in Person.list(only_deleted=True):
        if dbperson.callsign == "anon_admin":
            # Skip the "dummy" user for anon_admin, this should never be revoked though...
            continue
        listitem = CallSignPerson(
            callsign=dbperson.callsign, roles=[], extra=dbperson.extra, revoked=dbperson.deleted.isoformat()
        )
        result_list.append(listitem)

    return PeopleListOut(callsign_list=result_list)


@router.get(
    "/list/{role}",
    response_model=PeopleListOut,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_people_list_byrole(role: str) -> PeopleListOut:
    """
    /list/{role}
    Return people list by roles
    Returns a list of dicts, callsign_list = [ {  "callsign":'x', "roles": ["str"] 'extra':'x' } ]

    """

    result_list: List[CallSignPerson] = []
    async for dbperson in Person.by_role(role):
        if dbperson.callsign == "anon_admin":
            # Skip the "dummy" user for anon_admin
            continue
        roles = await dbperson.roles_set()
        listitem = CallSignPerson(callsign=dbperson.callsign, roles=list(roles), extra=dbperson.extra, revoked=None)
        result_list.append(listitem)

    return PeopleListOut(callsign_list=result_list)


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
