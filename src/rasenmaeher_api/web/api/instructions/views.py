"""Instruction routes"""

from typing import cast, Optional
import logging

from fastapi import Depends, APIRouter, Request, HTTPException
from libpvarki.schemas.product import UserCRUDRequest, UserInstructionFragment


from .schema import (
    AllProductsInstructionFragments,
    ProductFileList,
    AllProductsInstructionFiles,
    InstructionData,
)
from ..middleware.user import ValidUser
from ....productapihelpers import get_from_all_products, post_to_all_products, post_to_product
from ....db import Person


LOGGER = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/admin",
    response_model=AllProductsInstructionFragments,
    dependencies=[Depends(ValidUser(auto_error=True))],
    deprecated=True,
)
async def admin_instruction_fragment() -> AllProductsInstructionFragments:
    """Return admin instructions"""
    responses = await get_from_all_products("api/v1/admins/fragment", UserInstructionFragment)
    if responses is None:
        raise ValueError("Everything is broken")
    return AllProductsInstructionFragments(
        fragments={key: cast(UserInstructionFragment, val) for key, val in responses.items()}
    )


@router.get(
    "/user",
    response_model=AllProductsInstructionFiles,
    dependencies=[Depends(ValidUser(auto_error=True))],
    deprecated=True,
)
async def user_instruction_fragment(request: Request) -> AllProductsInstructionFiles:
    """Return end-user files"""
    person = cast(Person, request.state.person)
    user = UserCRUDRequest(
        uuid=str(person.pk), callsign=person.callsign, x509cert=person.certfile.read_text(encoding="utf-8")
    )
    LOGGER.debug("person={}, user={}".format(person, user))
    responses = await post_to_all_products("api/v1/clients/fragment", user.dict(), ProductFileList)
    if responses is None:
        raise ValueError("Everything is broken")
    return AllProductsInstructionFiles(files={key: cast(ProductFileList, val) for key, val in responses.items()})


@router.get(
    "/{product}/{language}",
    dependencies=[Depends(ValidUser(auto_error=True))],
    response_model=InstructionData,
)
async def get_product_instructions(request: Request, product: str, language: str) -> Optional[InstructionData]:
    """Get instructions JSON for given product and language"""
    person = cast(Person, request.state.person)
    user = UserCRUDRequest(
        uuid=str(person.pk), callsign=person.callsign, x509cert=person.certfile.read_text(encoding="utf-8")
    )
    endpoint_url = f"api/v1/instructions/{language}"
    response = await post_to_product(product, endpoint_url, user.dict(), InstructionData)
    if response is None:
        _reason = f"Unable to get instructions for {product}"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=404, detail=_reason)
    response = cast(InstructionData, response)
    return response
