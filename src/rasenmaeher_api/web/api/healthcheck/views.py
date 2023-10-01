"""Healthcheck API views."""
import logging
from typing import Any, Dict, List
from fastapi import APIRouter

from .schema import HealthCheckResponse
from ....db import Person
from ....settings import settings
from ....prodcutapihelpers import check_kraftwerk_manifest

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get("")
async def request_healthcheck() -> HealthCheckResponse:
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

    if check_kraftwerk_manifest():
        if "dns" in settings.kraftwerk_manifest_dict:
            my_dn = settings.kraftwerk_manifest_dict["dns"]
        else:
            my_dn = "DNS not defined in manifest"
    return HealthCheckResponse(healthcheck="success", dns=my_dn)


# Keep / needed?
@router.get("/delivery")
async def request_healthcheck_delivery() -> Dict[Any, Any]:
    """
    Delivery endpoint healthcheck.
    200 {"state":"ready-for-delivery"}
    201 {"detail":{"state":"init"}}
    204 {"detail":{"state":"waiting-for-services"}}
    """

    return {"state": "ready-for-delivery"}


# Keep / needed?
@router.get("/services")
async def request_healthcheck_services() -> List[Dict[Any, Any]]:
    """
    Serices endpoint healthcheck.
    return list of services
    """

    returnable: List[Dict[Any, Any]] = []
    returnable.append({"service": "TODO1", "response_code": "TODO1"})
    returnable.append({"service": "TODO2", "response_code": "TODO2"})

    return returnable
