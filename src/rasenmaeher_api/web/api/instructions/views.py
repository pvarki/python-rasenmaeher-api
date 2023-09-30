"""Instruction routes"""
from typing import cast
import logging

from fastapi import Depends, APIRouter, Request
from libpvarki.schemas.product import UserCRUDRequest, UserInstructionFragment


from .schema import AllProdcutsInstructionFragments
from ..middleware.user import ValidUser
from ....prodcutapihelpers import get_from_all_products, post_to_all_products
from ....db import Person


LOGGER = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/admin",
    response_model=AllProdcutsInstructionFragments,
    dependencies=[Depends(ValidUser(auto_error=True))],
)
async def admin_instruction_fragment() -> AllProdcutsInstructionFragments:
    """Return admin instructions"""
    responses = await get_from_all_products("api/v1/admins/fragment", UserInstructionFragment)
    if responses is None:
        raise ValueError("Everything is broken")
    return AllProdcutsInstructionFragments(
        fragments={key: cast(UserInstructionFragment, val) for key, val in responses.items()}
    )


@router.get(
    "/user",
    response_model=AllProdcutsInstructionFragments,
    dependencies=[Depends(ValidUser(auto_error=True))],
)
async def user_instruction_fragment(request: Request) -> AllProdcutsInstructionFragments:
    """Return end-user instructions"""
    person = cast(Person, request.state.person)
    user = UserCRUDRequest(
        uuid=str(person.pk), callsign=person.callsign, x509cert=person.certfile.read_text(encoding="utf-8")
    )
    LOGGER.debug("person={}, user={}".format(person, user))
    responses = await post_to_all_products("api/v1/clients/fragment", user.dict(), UserInstructionFragment)
    if responses is None:
        raise ValueError("Everything is broken")
    return AllProdcutsInstructionFragments(
        fragments={key: cast(UserInstructionFragment, val) for key, val in responses.items()}
    )
