"""Product integration API helpers"""
from typing import Dict, Optional, Type, Any, Mapping
import logging
from pathlib import Path
import json

import aiohttp
import pydantic
from libpvarki.schemas.generic import OperationResultResponse


from .rmsettings import switchme_to_singleton_call
from .mtlsinit import get_session_winit

LOGGER = logging.getLogger(__name__)


def check_kraftwerk_manifest() -> bool:
    """Check that settings has manifest"""
    if not switchme_to_singleton_call.kraftwerk_manifest_bool or not switchme_to_singleton_call.kraftwerk_manifest_dict:
        LOGGER.warning("KRAFTWERK manifest file not read, it should have been done on init")
        pth = Path(switchme_to_singleton_call.kraftwerk_manifest_path)
        if not pth.exists():
            LOGGER.error("KRAFTWERK manifest file not found")
            return False
        switchme_to_singleton_call.kraftwerk_manifest_dict = json.loads(pth.read_text(encoding="utf-8"))
        switchme_to_singleton_call.kraftwerk_manifest_bool = True
    return switchme_to_singleton_call.kraftwerk_manifest_bool


async def post_to_all_products(
    url_suffix: str, data: Mapping[str, Any], respose_schema: Type[pydantic.BaseModel]
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given POST endpoint on call products in the manifest"""
    return await _method_to_all_products("post", url_suffix, data, respose_schema)


async def put_to_all_products(
    url_suffix: str, data: Mapping[str, Any], respose_schema: Type[pydantic.BaseModel]
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given PUT endpoint on call products in the manifest"""
    return await _method_to_all_products("put", url_suffix, data, respose_schema)


async def get_from_all_products(
    url_suffix: str, respose_schema: Type[pydantic.BaseModel]
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given GET endpoint on call products in the manifest"""
    return await _method_to_all_products("get", url_suffix, None, respose_schema)


async def _method_to_all_products(
    methodname: str, url_suffix: str, data: Optional[Mapping[str, Any]], respose_schema: Type[pydantic.BaseModel]
) -> Optional[Dict[str, Optional[pydantic.BaseModel]]]:
    """Call given POST endpoint on call products in the manifest"""
    if not check_kraftwerk_manifest():
        return None
    manifest = switchme_to_singleton_call.kraftwerk_manifest_dict
    if "products" not in manifest:
        LOGGER.error("Manifest does not have products key")
        return None
    ret: Dict[str, Optional[pydantic.BaseModel]] = {}
    session = await get_session_winit()
    LOGGER.debug("data={}".format(data))
    async with session as client:
        for name, conf in manifest["products"].items():
            try:
                url = f"{conf['api']}{url_suffix}"
                LOGGER.debug("calling {}({})".format(methodname, url))
                if data is None:
                    resp = await getattr(client, methodname)(url)
                else:
                    resp = await getattr(client, methodname)(url, json=data)
                resp.raise_for_status()
                payload = await resp.json()
                LOGGER.debug("payload={}".format(payload))
                ret[name] = respose_schema.parse_obj(payload)
                # Log a commong error case here for DRY
                if isinstance(ret[name], OperationResultResponse):
                    if not ret[name].success:  # type: ignore[union-attr]
                        LOGGER.error("Failure at {}, response: {}".format(url, ret[name]))
            except aiohttp.ClientError:
                LOGGER.exception("Failure to call {}".format(url))
                ret[name] = None
                continue
            except pydantic.ValidationError:
                LOGGER.exception("Invalid response from {}".format(url))
                ret[name] = None
                continue
    return ret
