"""Create server cert and get it signed by CFSSL"""
from typing import cast, Any, Mapping, Union, Dict
import asyncio
import logging
from os import environ
import sys
from pathlib import Path

import aiohttp
from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from libadvian.logging import init_logging


# FIXME: refactor to use the helpers from libpvarki 1.6.0

LOGGER = logging.getLogger(__name__)
DATAPATH = Path("/data/persistent")

# we know we have copy-pasted this shit here, it's for the best, this time...
# pylint: disable=R0801


def create_keypair(name: str) -> crypto.PKey:
    """Generate a keypair"""

    privkeypath = DATAPATH / "private" / f"{name}.key"
    if not privkeypath.parent.exists():
        privkeypath.parent.mkdir(parents=True)
    pubkeypath = DATAPATH / "public" / f"{name}.pub"
    if not pubkeypath.parent.exists():
        pubkeypath.parent.mkdir(parents=True)
    ckp = crypto.PKey()
    LOGGER.debug("Generating keypair, this will take a moment")
    ckp.generate_key(crypto.TYPE_RSA, 4096)
    LOGGER.debug("Done")
    with privkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ckp))
    with pubkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_publickey(crypto.FILETYPE_PEM, ckp))
    return ckp


def create_csr(keypair: crypto.PKey, certname: str, cnstr: str, client: bool = False) -> Path:
    """Generate CSR file"""
    cert_path = DATAPATH / "public" / f"{certname}.pem"
    if not cert_path.parent.exists():
        cert_path.parent.mkdir(parents=True)
    csrpath = cert_path.parent / cert_path.name.replace(".pem", ".csr")

    req = crypto.X509Req()
    sanbytes = ", ".join([f"DNS:{cnstr}", "IP:127.0.0.1", "DNS:localhost"]).encode("utf-8")
    req.get_subject().CN = cnstr
    extensions = [
        crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
    ]
    if client:
        extensions.append(crypto.X509Extension(b"extendedKeyUsage", True, b"clientAuth"))
    else:
        extensions.append(crypto.X509Extension(b"extendedKeyUsage", True, b"serverAuth"))
        extensions.append(crypto.X509Extension(b"subjectAltName", False, sanbytes))
    req.add_extensions(extensions)
    req.set_pubkey(keypair)
    req.sign(keypair, "sha256")
    with csrpath.open("wb") as fpntr:
        fpntr.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))

    return csrpath


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
        async with session.post(url, json=payload, timeout=2.0) as response:
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
        async with session.post(url, json=payload, timeout=2.0) as response:
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
    keypair = await asyncio.get_event_loop().run_in_executor(None, create_keypair, "server")
    csr_path = await asyncio.get_event_loop().run_in_executor(
        None, create_csr, keypair, "server", environ.get("FPAPI_HOST_NAME", "fake.localmaeher.pvarki.fi")
    )
    certpem = (await sign_csr(csr_path.read_text())).replace("\\n", "\n")
    capem = (await get_ca()).replace("\\n", "\n")
    cert_path.write_text(certpem, encoding="ascii")
    certhain = certpem + capem
    chain_path.write_text(certhain, encoding="ascii")

    LOGGER.info("Initializing client cert")
    keypair2 = await asyncio.get_event_loop().run_in_executor(None, create_keypair, "client")
    csr_path2 = await asyncio.get_event_loop().run_in_executor(
        None, create_csr, keypair2, "client", "mtlstestclient", True
    )
    certpem2 = (await sign_csr(csr_path2.read_text())).replace("\\n", "\n")
    cert_path2 = DATAPATH / "public" / "client.pem"
    cert_path2.write_text(certpem2, encoding="ascii")
    LOGGER.info("All done")

    return 0


if __name__ == "__main__":
    loglevel = int(environ.get("LOG_LEVEL", "10"))
    init_logging(loglevel)
    LOGGER.setLevel(loglevel)
    sys.exit(asyncio.get_event_loop().run_until_complete(main()))
