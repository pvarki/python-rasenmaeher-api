"""Get the openapi.json from the API container via NGinx proxy"""
from typing import Tuple
import logging

import aiohttp
import pytest


LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_openapi_json(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str, float],
    openapi_version: Tuple[str, str],
) -> None:
    """Fetch openapi spec and check certain things exist"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/openapi.json"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=localmaeher_api[2])
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["openapi"] == f"{openapi_version[0]}"
    assert payload["info"] is not None
    assert payload["info"]["title"] == "FastAPI"
    assert payload["info"]["version"] == f"{openapi_version[1]}"
    assert payload["paths"] is not None
    assert payload["paths"][f"/api/{localmaeher_api[1]}/healthcheck"] is not None
    assert payload["components"] is not None
    assert payload["components"]["schemas"] is not None
    assert payload["components"]["schemas"]["CertificatesRequest"] is not None
    assert payload["components"]["securitySchemes"] is not None
    assert payload["components"]["securitySchemes"]["JWTBearer"] is not None
