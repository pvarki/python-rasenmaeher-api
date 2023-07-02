"""Healthcheck API views."""
import logging
from typing import Any, Dict, List
import json
import aiohttp
from fastapi import APIRouter, Request, HTTPException

from ....settings import settings
from ....sqlitedatabase import sqlite

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get("")
async def request_healthcheck(
    request: Request,
) -> Dict[Any, Any]:
    """
    Basic health check. Success = 200. Checks the following things.
    - Local sqlite connection
    """
    _success, _result = sqlite.run_command(settings.sqlite_healtcheck_query)

    if _success is False:
        _reason = "Error. Sqlite healthcheck _success is false. Undefined backend error hc_ssfm4"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=503, detail=_reason)

    if len(_result) == 0:
        _reason = "Sqlite healthcheck returned zero results. Please check and fix query in settings..."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=503, detail=_reason)

    return {"healthcheck": "success"}


@router.get("/delivery")
async def request_healthcheck_delivery(
    request: Request,
) -> Dict[Any, Any]:
    """
    Delivery endpoint healthcheck.
    200 {"state":"ready-for-delivery"}
    201 {"detail":{"state":"init"}}
    204 {"detail":{"state":"waiting-for-services"}}
    """

    # settings.sqlite_sel_from_services
    # _res = service_name, init_state, endpoint_proto_host_port, healthcheck_url, healthcheck_headers
    _success, _result = sqlite.run_command(settings.sqlite_sel_from_services)
    if _success is False:
        _reason = "Error. sqlite_sel_from_services _success is false. Undefined backend error hc_rhd"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=503, detail=_reason)

    if len(_result) == 0:
        _reason = "sqlite_sel_from_services returned zero results. There should be at least one... Most likely issue in init"  # pylint: disable=line-too-long
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=503, detail=_reason)

    for _res in _result:
        if _res[0] == "rasenmaeher" and _res[1] == "init":
            raise HTTPException(status_code=201, detail={"state": "init"})
        if _res[1] != "ready-for-delivery":
            raise HTTPException(status_code=204, detail={"state": "waiting-for-services"})

    return {"state": "ready-for-delivery"}


@router.get("/services")
async def request_healthcheck_services(
    request: Request,
) -> List[Dict[Any, Any]]:
    """
    Serices endpoint healthcheck.
    return list of services
    """

    _success, _result = sqlite.run_command(settings.sqlite_sel_from_services)

    if _success is False:
        _reason = "Error. sqlite_sel_from_services _success is false. Undefined backend error hc_rhs"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=503, detail=_reason)

    if len(_result) == 0:
        _reason = "sqlite_sel_from_services returned zero results. There should be at least one... Most likely issue in init"  # pylint: disable=line-too-long
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=503, detail=_reason)

    _returnable: List[Dict[Any, Any]] = []
    for _res in _result:
        # settings.sqlite_sel_from_services
        # _res = service_name, init_state, endpoint_proto_host_port, healthcheck_url, healthcheck_headers
        _url = f"{_res[2]}{_res[3]}"
        _hc_headers: Dict[Any, Any] = {}
        try:
            _hc_headers = json.loads(_res[4])
        except ValueError as _e:
            _returnable.append(
                {
                    "service": _res[0],
                    "status": 500,
                    "reason": f"JSON headers load error (service headers not proper json in database) : {_e}",
                }
            )
            continue

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(_url) as response:
                    _r_code = response.status
        except aiohttp.client_exceptions.ClientConnectorError as _e:
            _returnable.append(
                {
                    "service": _res[0],
                    "status": 503,
                    "reason": f"ClientConnectorError : {_e}",
                }
            )
            continue

        _returnable.append({"service": _res[0], "response_code": _r_code, "reason": ""})

    print(_returnable)
    return _returnable
