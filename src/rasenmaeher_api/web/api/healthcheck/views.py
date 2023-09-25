"""Healthcheck API views."""
import logging
from typing import Any, Dict, List
from fastapi import APIRouter

from ....db import Person

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get("")
async def request_healthcheck() -> Dict[Any, Any]:
    """
    Basic health check. Success = 200. Checks the following things.
    - Local db connection
    """
    Person.list()
    return {"healthcheck": "success"}


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
