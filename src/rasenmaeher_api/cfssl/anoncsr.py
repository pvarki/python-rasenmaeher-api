"""This needs to be separated to avoid circular imports"""
import logging

import aiohttp

from .base import base_url, anon_session, get_result_cert, CFSSLError
from ..rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


async def anon_sign_csr(csr: str) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL.

    This should only used by mtlsinit

    params: csr
    returns: certificate
    """
    async with (await anon_session()) as session:
        url = f"{base_url()}/api/v1/cfssl/sign"
        payload = {"certificate_request": csr}
        try:
            async with session.post(url, json=payload, timeout=RMSettings.singleton().cfssl_timeout) as response:
                return await get_result_cert(response)
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc
