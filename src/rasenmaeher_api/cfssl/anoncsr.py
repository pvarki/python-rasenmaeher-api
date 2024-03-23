"""This needs to be separated to avoid circular imports"""
import logging

import aiohttp


from .base import anon_session, get_result_cert, CFSSLError, ocsprest_base
from ..rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


async def anon_sign_csr(csr: str, bundle: bool = True) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL.

    This should only used by mtlsinit

    params: csr
    returns: certificate
    """
    async with (await anon_session()) as session:
        url = f"{ocsprest_base()}/api/v1/csr/sign"
        payload = {"certificate_request": csr, "profile": "client", "bundle": bundle}
        try:
            async with session.post(url, json=payload, timeout=RMSettings.singleton().cfssl_timeout) as response:
                resp = await get_result_cert(response)
                return resp
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc
