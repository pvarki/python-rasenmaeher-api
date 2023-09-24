"""Private apis"""
import logging

import aiohttp

from .base import base_url, get_result_cert, DEFAULT_TIMEOUT, CFSSLError
from .mtls import mtls_session

LOGGER = logging.getLogger(__name__)


async def sign_csr(csr: str) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL
    params: csr
    returns: certificate
    """
    async with (await mtls_session()) as session:
        url = f"{base_url()}/api/v1/cfssl/sign"
        payload = {"certificate_request": csr}
        try:
            async with session.post(url, json=payload, timeout=DEFAULT_TIMEOUT) as response:
                return await get_result_cert(response)
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc
