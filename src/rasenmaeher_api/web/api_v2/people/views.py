"""People API views."""  # pylint: disable=too-many-lines
from typing import List
import logging


from fastapi import APIRouter, Depends, Request, HTTPException
from libpvarki.schemas.generic import OperationResultResponse

from .schema import (
    CallSignPerson,
    PeopleListOut,
)
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from ....db import Person
from ....db.errors import BackendError

# from ....db import Enrollment, EnrollmentPool
# from ....db.errors import NotFound

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

    result_list: List[CallSignPerson] = []
    async for dbperson in Person.list():
        if dbperson.callsign == "anon_admin":
            # Skip the "dummy" user for anon_admin
            continue
        roles = await dbperson.roles_set()
        listitem = CallSignPerson(callsign=dbperson.callsign, roles=list(roles), extra=dbperson.extra)
        result_list.append(listitem)

    return PeopleListOut(callsign_list=result_list)


# GET :callsign:  palauttaa käyttäjän tiedot
# TODO TEST
@router.get(
    "/{callsign}",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def get_person(callsign: str) -> CallSignPerson:
    """get==get callsign info"""
    person = await Person.by_pk_or_callsign(callsign)
    roles = await person.roles_set()
    return CallSignPerson(callsign=callsign, roles=list(roles), extra=person.extra)


@router.delete(
    "/{callsign}",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def delete_person(callsign: str) -> OperationResultResponse:
    """delete==revoke a callsign"""
    person = await Person.by_pk_or_callsign(inval=callsign)
    try:
        deleted = await person.delete()
        return OperationResultResponse(success=deleted)
    except BackendError as exc:
        LOGGER.error("Backend failure: {}".format(exc))
        return OperationResultResponse(success=False, error=str(exc))


# POST :callsign:/promote käyttäjän ylennys
@router.post(
    "/{callsign}/promote",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_promote(
    callsign: str,
    request: Request,
) -> OperationResultResponse:
    """
    "Promote" callsign to have 'admin' rights
    """

    obj = await Person.by_pk_or_callsign(inval=callsign)

    role_added = await obj.assign_role(role="admin")
    if role_added:
        return OperationResultResponse(success=True, extra="Promote done")

    reason = "Given callsign already has elevated permissions."
    LOGGER.error("{} : {}".format(request.url, reason))
    raise HTTPException(status_code=400, detail=reason)


# POST :callsign:/demote käyttäjän alennus
@router.post(
    "/{callsign}/demote",
    response_model=OperationResultResponse,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def request_enrollment_demote(
    callsign: str,
    request: Request,
) -> OperationResultResponse:
    """
    "Demote" callsign from having 'admin' rights.
    """

    obj = await Person.by_pk_or_callsign(inval=callsign)
    _role_removed = await obj.remove_role(role="admin")
    if _role_removed:
        return OperationResultResponse(success=True, extra="Demote done")

    _reason = "Given callsign/callsign_hash doesn't have 'admin' privileges to take away."
    LOGGER.error("{} : {}".format(request.url, _reason))
    raise HTTPException(status_code=400, detail=_reason)


### DELETE ON JO
# POST :callsign:/lock käyttäjän lukitus
# POST :callsign:/unlock käyttäjän avaus
