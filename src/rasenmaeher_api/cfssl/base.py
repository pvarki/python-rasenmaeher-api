"""Base helpers etc"""
from typing import Any, Mapping, Union, cast
import logging

import aiohttp

from ..settings import settings

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 2.0


class CFSSLError(RuntimeError):
    """CFSSL errors"""


class NoResult(CFSSLError, ValueError):
    """Did not get any result"""


class ErrorResult(CFSSLError, ValueError):
    """Did not get any result"""


class NoValue(CFSSLError, ValueError):
    """Did not get expected values"""


async def get_result(response: aiohttp.ClientResponse) -> Any:
    """Get the result part"""
    data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await response.json(content_type=None))
    LOGGER.debug("data={}".format(data))
    if not data:
        LOGGER.error("Got empty json from response={}".format(response))
        raise CFSSLError("Got empty response")
    if errors := data.get("errors"):
        raise ErrorResult("CFSSL returned following errors: {}".format(errors))
    result = data.get("result")
    if not result:
        raise NoResult()
    return result


async def get_result_cert(response: aiohttp.ClientResponse) -> str:
    """Shorthand for checking the response and getting the cert"""
    result = await get_result(response)
    cert = result.get("certificate")
    if not cert:
        raise NoValue("CFSSL did not return certificate")
    return cast(str, cert)


def base_url() -> str:
    """Construct the base url"""
    return f"{settings.cfssl_host}:{settings.cfssl_port}"


async def anon_session() -> aiohttp.ClientSession:
    """Anonymous session with content-type set"""
    # FIXME: Add the CA certs that are available
    session = aiohttp.ClientSession()
    session.headers.add("Content-Type", "application/json")
    return session
