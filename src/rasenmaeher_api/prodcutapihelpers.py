"""Product integration API helpers"""
from typing import Dict, Optional, Type, Any, Mapping, Tuple
import asyncio
import logging

import aiohttp
import pydantic
from libpvarki.schemas.generic import OperationResultResponse
from libadvian.tasks import TaskMaster


from .rmsettings import RMSettings
from .mtlsinit import get_session_winit
from .cfssl.private import refresh_ocsp

LOGGER = logging.getLogger(__name__)


def check_kraftwerk_manifest() -> bool:
    """Check that settings has manifest"""
    RMSettings.singleton().load_manifest()
    return RMSettings.singleton().kraftwerk_manifest_bool


async def post_to_all_products(
    url_suffix: str, data: Mapping[str, Any], respose_schema: Type[pydantic.BaseModel], collect_responses: bool = True
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given POST endpoint on all products in the manifest"""
    return await _method_to_all_products("post", url_suffix, data, respose_schema, collect_responses)


async def put_to_all_products(
    url_suffix: str, data: Mapping[str, Any], respose_schema: Type[pydantic.BaseModel], collect_responses: bool = True
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given PUT endpoint on all products in the manifest"""
    return await _method_to_all_products("put", url_suffix, data, respose_schema, collect_responses)


async def get_from_all_products(
    url_suffix: str, respose_schema: Type[pydantic.BaseModel], collect_responses: bool = True
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given GET endpoint on all products in the manifest"""
    return await _method_to_all_products("get", url_suffix, None, respose_schema, collect_responses)


async def get_from_product(
    name: str, url_suffix: str, respose_schema: Type[pydantic.BaseModel]
) -> Optional[pydantic.BaseModel]:
    """Call given GET endpoint on named product in the manifest"""
    return await _method_to_product(name, "get", url_suffix, None, respose_schema)


async def post_to_product(
    name: str, url_suffix: str, data: Mapping[str, Any], respose_schema: Type[pydantic.BaseModel]
) -> Optional[pydantic.BaseModel]:
    """Call given POST endpoint on named product in the manifest"""
    return await _method_to_product(name, "post", url_suffix, data, respose_schema)


async def put_to_product(
    name: str, url_suffix: str, data: Mapping[str, Any], respose_schema: Type[pydantic.BaseModel]
) -> Optional[pydantic.BaseModel]:
    """Call given PUT endpoint on named product in the manifest"""
    return await _method_to_product(name, "put", url_suffix, data, respose_schema)


async def _method_to_all_products(
    methodname: str,
    url_suffix: str,
    data: Optional[Mapping[str, Any]],
    respose_schema: Type[pydantic.BaseModel],
    collect_responses: bool = True,
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given POST endpoint on call products in the manifest"""
    if not check_kraftwerk_manifest():
        return None
    manifest = RMSettings.singleton().kraftwerk_manifest_dict
    if "products" not in manifest:
        LOGGER.error("Manifest does not have products key")
        return None
    await refresh_ocsp()
    LOGGER.debug("data={}".format(data))

    async def handle_one(name: str) -> Tuple[str, Optional[pydantic.BaseModel]]:
        """Do one call"""
        nonlocal url_suffix, methodname, respose_schema, data
        try:
            return name, await _method_to_product(name, methodname, url_suffix, data, respose_schema)
        except Exception as exc:  # pylint: disable=W0718
            LOGGER.exception(exc)
            return name, None

    if not collect_responses:
        tma = TaskMaster.singleton()
        for name in manifest["products"]:
            tma.create_task(handle_one(name))
        return None

    coros = []
    for name in manifest["products"]:
        coros.append(handle_one(name))
    return dict(await asyncio.gather(*coros))


async def _method_to_product(
    productname: str,
    methodname: str,
    url_suffix: str,
    data: Optional[Mapping[str, Any]],
    respose_schema: Type[pydantic.BaseModel],
) -> Optional[Optional[pydantic.BaseModel]]:
    """Do a call to named product"""

    manifest = RMSettings.singleton().kraftwerk_manifest_dict
    if "products" not in manifest:
        LOGGER.error("Manifest does not have products key")
        return None
    rmconf = RMSettings.singleton()
    productconf = manifest["products"][productname]

    session = await get_session_winit()
    async with session as client:
        try:
            url = f"{productconf['api']}{url_suffix}"
            LOGGER.debug("calling {}({})".format(methodname, url))
            if data is None:
                resp = await getattr(client, methodname)(url, timeout=rmconf.integration_api_timeout)
            else:
                resp = await getattr(client, methodname)(url, json=data, timeout=rmconf.integration_api_timeout)
            resp.raise_for_status()
            payload = await resp.json()
            LOGGER.debug("{}({}) payload={}".format(methodname, url, payload))
            retval = respose_schema.parse_obj(payload)
            # Log a common error case here for DRY
            if isinstance(retval, OperationResultResponse):
                if not retval.success:
                    LOGGER.error("Failure at {}, response: {}".format(url, retval))
            return retval
        except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as exc:
            LOGGER.error("Failure to call {}: {}".format(url, repr(exc)))
            return None
        except pydantic.ValidationError as exc:
            LOGGER.error("Invalid response from {}: {}".format(url, repr(exc)))
            return None
        except Exception:  # pylint: disable=W0718
            LOGGER.exception("Something went seriously wrong calling {}".format(url))
            return None
