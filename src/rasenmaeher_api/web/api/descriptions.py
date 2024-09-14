"""product descriptions endpoints"""
from typing import Optional, cast
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Extra, Field
from pydantic_collections import BaseCollectionModel

from ...prodcutapihelpers import get_from_all_products, get_from_product


LOGGER = logging.getLogger(__name__)

router = APIRouter()  # These endpoints are public


# FIXME: Move to libpvarki
class ProductDescription(BaseModel):
    """Description of a product"""

    shortname: str = Field(description="Short name for the product, used as slug/key in dicts and urls")
    title: str = Field(description="Fancy name for the product")
    icon: Optional[str] = Field(description="URL for icon")
    description: str = Field(description="Short-ish description of the product")
    language: str = Field(description="Language of this response")

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configs"""

        extra = Extra.forbid


class ProductDescriptionList(BaseCollectionModel[ProductDescription]):  # type: ignore[misc] # pylint: disable=too-few-public-methods
    """List of product descriptions"""

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configs"""

        extra = Extra.forbid


@router.get(
    "/{language}",
    response_model=ProductDescriptionList,
)
async def list_product_descriptions(language: str) -> ProductDescriptionList:
    """Fetch description from each product in manifest"""
    responses = await get_from_all_products(f"api/v1/description/{language}", ProductDescription)
    if responses is None:
        raise ValueError("Everything is broken")
    return ProductDescriptionList([res for res in responses.values() if res])


@router.get(
    "/{product}/{language}",
    response_model=ProductDescription,
)
async def get_product_description(language: str, product: str) -> Optional[ProductDescription]:
    """Fetch description from given product in manifest"""
    response = await get_from_product(product, f"api/v1/description/{language}", ProductDescription)
    if response is None:
        # TODO: Raise a reasonable error instead
        return None
    response = cast(ProductDescription, response)
    return response
