"""Product integration API helpers"""

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import pydantic
from libadvian.tasks import TaskMaster
from libpvarki.schemas.generic import OperationResultResponse

from .cert.backend import refresh_ocsp
from .mtlsinit import get_session_winit
from .rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


def check_kraftwerk_manifest() -> bool:
    """Check that settings has manifest"""
    RMSettings.singleton().load_manifest()
    return RMSettings.singleton().kraftwerk_manifest_bool


async def post_to_all_products(
    url_suffix: str, data: Mapping[str, Any], response_schema: type[pydantic.BaseModel], collect_responses: bool = True
) -> dict[str, pydantic.BaseModel | None] | None:
    """Call given POST endpoint on all products in the manifest"""
    return await _method_to_all_products("post", url_suffix, data, response_schema, collect_responses)


async def put_to_all_products(
    url_suffix: str, data: Mapping[str, Any], response_schema: type[pydantic.BaseModel], collect_responses: bool = True
) -> dict[str, pydantic.BaseModel | None] | None:
    """Call given PUT endpoint on all products in the manifest"""
    return await _method_to_all_products("put", url_suffix, data, response_schema, collect_responses)


async def get_from_all_products(
    url_suffix: str, response_schema: type[pydantic.BaseModel], collect_responses: bool = True
) -> dict[str, pydantic.BaseModel | None] | None:
    """Call given GET endpoint on all products in the manifest"""
    return await _method_to_all_products("get", url_suffix, None, response_schema, collect_responses)


async def get_from_product(
    name: str, url_suffix: str, response_schema: type[pydantic.BaseModel]
) -> pydantic.BaseModel | None:
    """Call given GET endpoint on named product in the manifest"""
    return await _method_to_product(name, "get", url_suffix, None, response_schema)


async def post_to_product(
    name: str, url_suffix: str, data: Mapping[str, Any], response_schema: type[pydantic.BaseModel]
) -> pydantic.BaseModel | None:
    """Call given POST endpoint on named product in the manifest"""
    return await _method_to_product(name, "post", url_suffix, data, response_schema)


async def put_to_product(
    name: str, url_suffix: str, data: Mapping[str, Any], response_schema: type[pydantic.BaseModel]
) -> pydantic.BaseModel | None:
    """Call given PUT endpoint on named product in the manifest"""
    return await _method_to_product(name, "put", url_suffix, data, response_schema)


async def _method_to_all_products(
    methodname: str,
    url_suffix: str,
    data: Mapping[str, Any] | None,
    response_schema: type[pydantic.BaseModel],
    collect_responses: bool = True,
) -> dict[str, pydantic.BaseModel | None] | None:
    """Call given POST endpoint on call products in the manifest"""
    if not check_kraftwerk_manifest():
        return None
    manifest = RMSettings.singleton().kraftwerk_manifest_dict
    if "products" not in manifest:
        LOGGER.error("Manifest does not have products key")
        return None
    await refresh_ocsp()
    LOGGER.debug(f"data={data}")

    async def handle_one(name: str) -> tuple[str, pydantic.BaseModel | None]:
        """Do one call"""
        nonlocal url_suffix, methodname, response_schema, data
        try:
            return name, await _method_to_product(name, methodname, url_suffix, data, response_schema)
        except Exception:
            LOGGER.exception("Unhandled exception")
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
    data: Mapping[str, Any] | None,
    response_schema: type[pydantic.BaseModel],
) -> pydantic.BaseModel | None:
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
            # Normalise the join: every manifest "api" value ends in "/" (see
            # miniwerk manifests), so a suffix that also starts with one gave
            # "https://host:4626//api/v1/..." — which Starlette does not route,
            # so the product 404s and the caller sees only a swallowed None.
            url = f"{productconf['api'].rstrip('/')}/{url_suffix.lstrip('/')}"
            LOGGER.debug(f"calling {methodname}({url})")
            if data is None:
                resp = await getattr(client, methodname)(url, timeout=rmconf.integration_api_timeout)
            else:
                resp = await getattr(client, methodname)(
                    url, json=data, timeout=aiohttp.ClientTimeout(total=rmconf.integration_api_timeout)
                )
            resp.raise_for_status()
            payload = await resp.json()
            LOGGER.debug(f"{methodname}({url}) payload={payload}")
            retval = response_schema.parse_obj(payload)
            # Log a common error case here for DRY
            if isinstance(retval, OperationResultResponse) and not retval.success:
                LOGGER.error(f"Failure at {url}, response: {retval}")
            return retval
        except (aiohttp.ClientError, TimeoutError) as exc:
            LOGGER.error(f"Failure to call {url}: {exc!r}")
            return None
        except pydantic.ValidationError as exc:
            LOGGER.error(f"Invalid response from {url}: {exc!r}")
            return None
        except Exception:
            LOGGER.exception(f"Something went seriously wrong calling {url}")
            return None
