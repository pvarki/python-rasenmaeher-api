"""Base helpers etc"""

import json
import logging
import ssl
from collections.abc import Mapping
from typing import Any, cast

import aiohttp
from libpvarki.mtlshelp.context import get_ca_context

from ...rmsettings import RMSettings
from ..errors import CertError, DBLocked, ErrorResult, NoResult, NoValue

LOGGER = logging.getLogger(__name__)

__all__ = [
    "CFSSLError",
    "DBLocked",
    "ErrorResult",
    "NoResult",
    "NoValue",
    "anon_session",
    "base_url",
    "default_timeout",
    "get_result",
    "get_result_bundle",
    "get_result_cert",
    "ocsprest_base",
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
        data = cast(Mapping[str, Any | Mapping[str, Any]], json.loads(body) if body else {})
    except json.JSONDecodeError as exc:
        LOGGER.error(
            f"Non-JSON response from {response.url} (HTTP {response.status} {response.reason}): {body[:1000]!r}"
        )
        raise CFSSLError(
            f"HTTP {response.status} {response.reason} from {response.url} with non-JSON body: {body[:500]!r}"
        ) from exc
    LOGGER.debug(f"data={data}")
    if not data:
        LOGGER.error(f"Empty body from {response.url} (HTTP {response.status} {response.reason})")
        raise CFSSLError(f"Empty response from {response.url} (HTTP {response.status} {response.reason})")
    if errors := data.get("errors"):
        errors = cast(list[Mapping[str, Any]], errors)
        for error in errors:
            if error["code"] == 11000:
                raise DBLocked(f"CFSSL returned following errors: {errors}")
        raise ErrorResult(f"CFSSL returned following errors: {errors}")
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
