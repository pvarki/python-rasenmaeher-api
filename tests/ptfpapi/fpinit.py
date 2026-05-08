"""Create server cert and get it signed by CFSSL"""

from typing import cast, Any, Mapping, Union, Dict
import asyncio
import logging
from os import environ
import sys
from pathlib import Path

import aiohttp
from libadvian.logging import init_logging
from libpvarki.mtlshelp.csr import (
    async_create_client_csr,
    async_create_keypair,
    async_create_server_csr,
    resolve_filepaths,
)


LOGGER = logging.getLogger(__name__)
DATAPATH = Path("/data/persistent")
TIMEOUT = aiohttp.ClientTimeout(total=2.0)


async def get_ca() -> str:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """
    cfssl_host = environ.get("CFSSL_HOST", "http://cfssl")
    cfssl_port = int(environ.get("CFSSL_PORT", "7777"))
    async with aiohttp.ClientSession() as session:
        session.headers.add("Content-Type", "application/json")
        url = f"{cfssl_host}:{cfssl_port}/api/v1/cfssl/info"
        payload: Dict[str, Any] = {}

        # FIXME: Why does this need to be a POST ??
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=2.0)) as response:
            data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await response.json())
            result = data.get("result")
            if not result:
                raise ValueError("CFSSL did not return result")
            cert = result.get("certificate")
            if not cert:
                raise ValueError("CFSSL did not return certificate")
            return cast(str, cert)


async def sign_csr(csr: str) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL
    params: csr
    returns: certificate
    """
    cfssl_host = environ.get("CFSSL_HOST", "cfssl")
    cfssl_port = int(environ.get("CFSSL_PORT", "7777"))
    async with aiohttp.ClientSession() as session:
        session.headers.add("Content-Type", "application/json")
        url = f"{cfssl_host}:{cfssl_port}/api/v1/cfssl/sign"
        payload = {"certificate_request": csr}
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=2.0)) as response:
            data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await response.json())
            result = data.get("result")
            if not result:
                raise ValueError("CFSSL did not return result")
            cert = result.get("certificate")
            if not cert:
                raise ValueError("CFSSL did not return certificate")
            return cast(str, cert)


async def main() -> int:
    """Main entrypoint, return exit code"""
    LOGGER.debug("Called")
    cert_path = DATAPATH / "public" / "server.pem"
    chain_path = DATAPATH / "public" / "server_chain.pem"
    cert_path2 = DATAPATH / "public" / "client.pem"
    if chain_path.exists() and cert_path2.exists():
        LOGGER.info("Init already done")
        return 0
    LOGGER.info("Initializing server cert")
    server_priv, server_pub, server_csrpath = resolve_filepaths(DATAPATH, "server")
    keypair = await async_create_keypair(server_priv, server_pub)
    server_cn = environ.get("FPAPI_HOST_NAME", "fake.localmaeher.dev.pvarki.fi")
    csr_pem = await async_create_server_csr(keypair, server_csrpath, [server_cn, "IP:127.0.0.1", "DNS:localhost"])
    certpem = (await sign_csr(csr_pem)).replace("\\n", "\n")
    capem = (await get_ca()).replace("\\n", "\n")
    cert_path.write_text(certpem, encoding="ascii")
    certhain = certpem + capem
    chain_path.write_text(certhain, encoding="ascii")

    LOGGER.info("Initializing client cert")
    client_priv, client_pub, client_csrpath = resolve_filepaths(DATAPATH, "client")
    keypair2 = await async_create_keypair(client_priv, client_pub)
    csr_pem2 = await async_create_client_csr(keypair2, client_csrpath, {"CN": "mtlstestclient"})
    certpem2 = (await sign_csr(csr_pem2)).replace("\\n", "\n")
    cert_path2 = DATAPATH / "public" / "client.pem"
    cert_path2.write_text(certpem2, encoding="ascii")
    LOGGER.info("All done")

    return 0


if __name__ == "__main__":
    loglevel = int(environ.get("LOG_LEVEL", "10"))
    init_logging(loglevel)
    LOGGER.setLevel(loglevel)
    sys.exit(asyncio.get_event_loop().run_until_complete(main()))
