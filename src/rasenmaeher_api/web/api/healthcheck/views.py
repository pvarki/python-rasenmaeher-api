"""Healthcheck API views."""

from typing import cast
import logging
import os

from fastapi import APIRouter
from libpvarki.schemas.product import ProductHealthCheckResponse

from rasenmaeher_api import __version__
from .schema import BasicHealthCheckResponse, AllProductsHealthCheckResponse
from ....db import Person
from ....rmsettings import switchme_to_singleton_call
from ....productapihelpers import check_kraftwerk_manifest, get_from_all_products

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get("")
async def request_healthcheck() -> BasicHealthCheckResponse:
    """
    Basic health check. Success = 200. Checks the following things.
    - Person list from database
    - Domain name from manifest
    """
    # Do at least little bit something to check backend functionality
    async for _ in Person.list():
        break

    # Get the DNS from manifest
    my_dn: str = "Manifest not defined"
    deployment_name = "Manifest not defined"

    if check_kraftwerk_manifest():
        if "dns" in switchme_to_singleton_call.kraftwerk_manifest_dict:
            my_dn = switchme_to_singleton_call.kraftwerk_manifest_dict["dns"]
            deployment_name = my_dn.split(".")[0]
        else:
            my_dn = "DNS not defined in manifest"
            deployment_name = "DNS not defined in manifest"
    rm_version = __version__
    deployment_version = os.environ.get("RELEASE_TAG", "undefined")
    if release_status := os.environ.get("RELEASE_STATUS", ""):
        deployment_version += f"-{release_status}"
    return BasicHealthCheckResponse(
        healthcheck="success", dns=my_dn, deployment=deployment_name, version=deployment_version, rm_version=rm_version
    )


@router.get("/services")
async def request_healthcheck_services() -> AllProductsHealthCheckResponse:
    """Return the states of products' apis and if everything is ok

    Note that HTTP status-code is 200 even if all_ok is False"""

    ret = AllProductsHealthCheckResponse(all_ok=True, products={})
    statuses = await get_from_all_products("api/v1/healthcheck", ProductHealthCheckResponse)
    if not statuses:
        LOGGER.error("Did not get anything back")
        ret.all_ok = False
        return ret
    for productname, response in statuses.items():
        if not response:
            LOGGER.warning("No response from {}, setting all_ok to False".format(productname))
            ret.products[productname] = False
            ret.all_ok = False
            continue
        response = cast(ProductHealthCheckResponse, response)
        ret.products[productname] = response.healthy
        if not response.healthy:
            LOGGER.warning("Unhealthy report from {}, setting all_ok to False".format(productname))
            ret.all_ok = False

    return ret
