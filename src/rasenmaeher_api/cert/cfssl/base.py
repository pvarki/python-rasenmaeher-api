"""Base helpers etc"""

from typing import Any, Mapping, Union, List, cast
import json
import logging
import ssl

import aiohttp
from libpvarki.mtlshelp.context import get_ca_context

from ...rmsettings import RMSettings
from ..errors import CertError, NoResult, ErrorResult, DBLocked, NoValue

LOGGER = logging.getLogger(__name__)

__all__ = [
    "CFSSLError",
    "NoResult",
    "ErrorResult",
    "DBLocked",
    "NoValue",
    "default_timeout",
    "get_result",
    "get_result_cert",
    "get_result_bundle",
    "base_url",
    "ocsprest_base",
    "anon_session",
]

# Backward compatibility alias
CFSSLError = CertError


def default_timeout() -> aiohttp.ClientTimeout:
    """Return configured timeout wrapped in the new aiohttp way"""
    return aiohttp.ClientTimeout(total=RMSettings.singleton().cfssl_timeout)


async def get_result(response: aiohttp.ClientResponse) -> Any:
    """Get the result part"""
    body = await response.text()
    try:
        data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], json.loads(body) if body else {})
    except json.JSONDecodeError as exc:
        LOGGER.error(
            "Non-JSON response from {} (HTTP {} {}): {!r}".format(
                response.url, response.status, response.reason, body[:1000]
            )
        )
        raise CFSSLError(
            "HTTP {} {} from {} with non-JSON body: {!r}".format(
                response.status, response.reason, response.url, body[:500]
            )
        ) from exc
    LOGGER.debug("data={}".format(data))
    if not data:
        LOGGER.error("Empty body from {} (HTTP {} {})".format(response.url, response.status, response.reason))
        raise CFSSLError("Empty response from {} (HTTP {} {})".format(response.url, response.status, response.reason))
    if errors := data.get("errors"):
        errors = cast(List[Mapping[str, Any]], errors)
        for error in errors:
            if error["code"] == 11000:
                raise DBLocked("CFSSL returned following errors: {}".format(errors))
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


async def get_result_bundle(response: aiohttp.ClientResponse) -> str:
    """Shorthand for checking the response and getting the cert"""
    result = await get_result(response)
    cert = result.get("bundle")
    if not cert:
        raise NoValue("CFSSL did not return certificate bundle")
    return cast(str, cert)


def base_url() -> str:
    """Construct the base url"""
    cnf = RMSettings.singleton()
    return f"{cnf.cfssl_host}:{cnf.cfssl_port}"


def ocsprest_base() -> str:
    """Construct the base url for ocsprest"""
    cnf = RMSettings.singleton()
    return f"{cnf.ocsprest_host}:{cnf.ocsprest_port}"


async def anon_session() -> aiohttp.ClientSession:
    """Anonymous session with content-type set"""
    ctx = get_ca_context(ssl.Purpose.SERVER_AUTH)
    conn = aiohttp.TCPConnector(ssl=ctx)
    session = aiohttp.ClientSession(connector=conn)
    session.headers.add("Content-Type", "application/json")
    return session
