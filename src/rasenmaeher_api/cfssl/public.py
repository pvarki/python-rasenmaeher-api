"""Public things, CA cert, CRL etc"""

from typing import Dict, Any
import logging
import base64

import aiohttp

from .base import (
    base_url,
    anon_session,
    get_result,
    get_result_cert,
    CFSSLError,
    get_result_bundle,
    ocsprest_base,
    default_timeout,
)
from .private import refresh_ocsp


LOGGER = logging.getLogger(__name__)
CRL_LIFETIME = "1800s"  # seconds


async def get_ca() -> str:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """

    async with await anon_session() as session:
        url = f"{base_url()}/api/v1/cfssl/info"
        payload: Dict[str, Any] = {}
        # PONDER: Why does this need to be a POST ??
        try:
            async with session.post(url, json=payload, timeout=default_timeout()) as response:
                return await get_result_cert(response)
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc


async def get_ocsprest_crl(suffix: str) -> bytes:
    """Fetch CRL from OCSPREST"""

    async with await anon_session() as session:
        url = f"{ocsprest_base()}/api/v1/crl/{suffix}"
        try:
            async with session.get(url) as response:
                data = await response.read()
                LOGGER.debug("{} returned {}".format(url, repr(data)))
                return data
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc


async def get_crl() -> bytes:
    """
    Quick and dirty method to get CRL from CFSSL, should not be used.
    returns: DER binary encoded Certificate Revocation List
    """

    async with await anon_session() as session:
        url = f"{base_url()}/api/v1/cfssl/crl"
        try:
            async with session.get(url, params={"expiry": CRL_LIFETIME}, timeout=default_timeout()) as response:
                crl_b64 = await get_result(response)
                data = base64.b64decode(crl_b64)
                return data
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc


async def get_bundle(cert: str) -> str:
    """
    Get the optimal cert bundle for given cert
    """

    # FIXME: This is not a good way but I don't have a better one right now either
    # Force OCSP refresh before getting the bundle so we hopefully get all we need
    await refresh_ocsp()
    async with await anon_session() as session:
        url = f"{base_url()}/api/v1/cfssl/bundle"
        payload: Dict[str, Any] = {"certificate": cert, "flavor": "optimal"}
        try:
            async with session.post(url, json=payload, timeout=default_timeout()) as response:
                return await get_result_bundle(response)
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc
