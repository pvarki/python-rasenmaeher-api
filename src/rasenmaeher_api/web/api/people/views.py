"""People API views."""  # pylint: disable=too-many-lines

from typing import List, Optional
import logging


from fastapi import APIRouter, Depends
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.auditlogging import audit_iam, AUDIT

from .schema import (
    CallSignPerson,
    PeopleListOut,
)
from ..middleware.mtls import MTLSorJWT
from ..middleware.user import ValidUser
from ....db import Person
from ....db.errors import BackendError, NotFound

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
    try:
        person = await Person.by_callsign(callsign)
    except NotFound:
        LOGGER.log(
            AUDIT,
            "User revocation failed - user not found: %s",
            callsign,
            extra=audit_iam(
                action="user_revoke",
                outcome="failure",
                target_user=callsign,
                admin_action=True,
                error_code="USER_NOT_FOUND",
                error_message="User does not exist",
            ),
        )
        return OperationResultResponse(success=False, error="User not found")

    try:
        deleted = await person.delete()
        if deleted:
            LOGGER.log(
                AUDIT,
                "User revoked: %s",
                callsign,
                extra=audit_iam(
                    action="user_revoke",
                    outcome="success",
                    target_user=callsign,
                    admin_action=True,
                ),
            )
        else:
            LOGGER.log(
                AUDIT,
                "User revocation returned false: %s",
                callsign,
                extra=audit_iam(
                    action="user_revoke",
                    outcome="failure",
                    target_user=callsign,
                    admin_action=True,
                    error_code="DELETE_RETURNED_FALSE",
                    error_message="Delete operation returned false",
                ),
            )
        return OperationResultResponse(success=deleted)
    except BackendError as exc:
        LOGGER.log(
            AUDIT,
            "User revocation failed - backend error: %s",
            callsign,
            extra=audit_iam(
                action="user_revoke",
                outcome="failure",
                target_user=callsign,
                admin_action=True,
                error_code="BACKEND_ERROR",
                error_message=str(exc),
            ),
        )
        LOGGER.error("Backend failure: {}".format(exc))
        return OperationResultResponse(success=False, error=str(exc))
