"""product descriptions endpoints"""

import logging
from typing import Literal, TypeVar, cast

from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from pydantic import BaseModel, ConfigDict, Field, RootModel

from rasenmaeher_api.web.api.middleware.user import ValidUser

from ...productapihelpers import get_from_all_products, get_from_product

LOGGER = logging.getLogger(__name__)

router = APIRouter()  # These endpoints are public
router_v2 = APIRouter()

router_v2_admin = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


# FIXME: Move to libpvarki
class ProductDescription(BaseModel):
    """Description of a product"""

    model_config = ConfigDict(extra="forbid")

    shortname: str = Field(description="Short name for the product, used as slug/key in dicts and urls")
    title: str = Field(description="Fancy name for the product")
    icon: str | None = Field(description="URL for icon")
    description: str = Field(description="Short-ish description of the product")
    language: str = Field(description="Language of this response")


class ProductComponent(BaseModel):
    """Product component info"""

    type: Literal["link", "markdown", "component"]
    ref: str


class ProductDescriptionExtended(BaseModel):
    """Description of a product"""

    model_config = ConfigDict(extra="forbid")

    shortname: str = Field(description="Short name for the product, used as slug/key in dicts and urls")
    title: str = Field(description="Fancy name for the product")
    icon: str | None = Field(description="URL for icon")
    description: str = Field(description="Short-ish description of the product")
    language: str = Field(description="Language of this response")
    docs: str | None = Field(description="Link to documentation")
    component: ProductComponent = Field(description="Component type and ref")


class ProductDescriptionList(RootModel[list[ProductDescription]]):
    """List of product descriptions"""


class ProductDescriptionExtendedList(RootModel[list[ProductDescriptionExtended]]):
    """List of product descriptions"""


DescriptionT = TypeVar("DescriptionT", ProductDescription, ProductDescriptionExtended)


def _with_manifest_shortname(name: str, description: DescriptionT) -> DescriptionT:
    """Force shortname to the manifest key.

    Products self-report their shortname and are not consistent about it, but the manifest key is what
    we use as the slug in dicts and urls, so it must be the authoritative value.
    """
    if description.shortname != name:
        LOGGER.debug(f"Overriding self-reported shortname {description.shortname!r} with manifest key {name!r}")
        description = description.model_copy(update={"shortname": name})
    return description


@router.get(
    "/{language}",
    response_model=ProductDescriptionList,
)
async def list_product_descriptions(language: str) -> ProductDescriptionList:
    """Fetch description from each product in manifest"""
    responses = await get_from_all_products(f"api/v1/description/{language}", ProductDescription)
    if responses is None:
        raise ValueError("Everything is broken")
    return ProductDescriptionList(
        [_with_manifest_shortname(name, cast(ProductDescription, res)) for name, res in responses.items() if res]
    )


@router.get(
    "/{product}/{language}",
    response_model=ProductDescription,
)
async def get_product_description(language: str, product: str) -> ProductDescription | None:
    """Fetch description from given product in manifest"""
    response = await get_from_product(product, f"api/v1/description/{language}", ProductDescription)
    if response is None:
        # TODO: Raise a reasonable error instead
        return None
    return _with_manifest_shortname(product, cast(ProductDescription, response))


@router_v2.get(
    "/{language}",
    response_model=ProductDescriptionExtendedList,
)
async def list_product_descriptions_extended(language: str) -> ProductDescriptionExtendedList:
    """Fetch description from each product in manifest"""
    responses = await get_from_all_products(f"api/v2/description/{language}", ProductDescriptionExtended)
    if responses is None:
        raise ValueError("Everything is broken")
    return ProductDescriptionExtendedList(
        [
            _with_manifest_shortname(name, cast(ProductDescriptionExtended, res))
            for name, res in responses.items()
            if res
        ]
    )


@router_v2.get(
    "/{product}/{language}",
    response_model=ProductDescriptionExtended,
)
async def get_product_description_extended(language: str, product: str) -> ProductDescriptionExtended | None:
    """Fetch description from given product in manifest"""
    response = await get_from_product(product, f"api/v2/description/{language}", ProductDescriptionExtended)

    if response is None:
        # TODO: Raise a reasonable error instead
        return None
    return _with_manifest_shortname(product, cast(ProductDescriptionExtended, response))


@router_v2_admin.get(
    "/{language}",
    response_model=ProductDescriptionExtendedList,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def list_admin_product_descriptions_extended(language: str) -> ProductDescriptionExtendedList:
    """Fetch admin description from each product in manifest"""
    responses = await get_from_all_products(f"api/v2/admin/description/{language}", ProductDescriptionExtended)
    if responses is None:
        raise ValueError("Everything is broken")
    return ProductDescriptionExtendedList(
        [
            _with_manifest_shortname(name, cast(ProductDescriptionExtended, res))
            for name, res in responses.items()
            if res
        ]
    )


@router_v2_admin.get(
    "/{product}/{language}",
    response_model=ProductDescriptionExtended,
    dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))],
)
async def get_admin_product_description_extended(language: str, product: str) -> ProductDescriptionExtended | None:
    """Fetch admin description from given product in manifest"""
    response = await get_from_product(product, f"api/v2/admin/description/{language}", ProductDescriptionExtended)

    if response is None:
        # TODO: Raise a reasonable error instead
        return None
    return _with_manifest_shortname(product, cast(ProductDescriptionExtended, response))
