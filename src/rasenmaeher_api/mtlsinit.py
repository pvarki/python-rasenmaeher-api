"""Init mTLS client cert for RASENMAEHER itself"""
import asyncio
from pathlib import Path
import logging


from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from libpvarki.mtlshelp.session import get_session as libsession
import aiohttp

from rasenmaeher_api.web.api.product.views import sign_csr
from .settings import settings

LOGGER = logging.getLogger(__name__)


def check_mtls_init() -> bool:
    """Check if we have the cert and key"""
    cert_path = Path(settings.mtls_client_cert_path)
    key_path = Path(settings.mtls_client_key_path)
    LOGGER.debug("cert_path={}  exits={}".format(cert_path, cert_path.exists()))
    LOGGER.debug("key_path={}  exits={}".format(key_path, key_path.exists()))
    if cert_path.exists() and key_path.exists():
        return True
    return False


def create_keypair() -> crypto.PKey:
    """Generate a keypair"""
    privkeypath = Path(settings.mtls_client_key_path)
    pubkeypath = privkeypath.parent / privkeypath.name.replace(".key", ".pub")
    ckp = crypto.PKey()
    LOGGER.debug("Generating keypair, this will take a moment")
    ckp.generate_key(crypto.TYPE_RSA, 4096)
    LOGGER.debug("Done")
    with privkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ckp))
    with pubkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_publickey(crypto.FILETYPE_PEM, ckp))
    return ckp


def create_csr(keypair: crypto.PKey) -> Path:
    """Generate CSR file"""
    cert_path = Path(settings.mtls_client_cert_path)
    csrpath = cert_path.parent / cert_path.name.replace(".pem", ".csr")

    req = crypto.X509Req()
    req.get_subject().CN = settings.mtls_client_cert_cn
    req.add_extensions(
        [
            crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
            crypto.X509Extension(b"extendedKeyUsage", True, b"clientAuth"),
        ]
    )
    req.set_pubkey(keypair)
    req.sign(keypair, "sha256")
    with csrpath.open("wb") as fpntr:
        fpntr.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))

    return csrpath


async def mtls_init() -> None:
    """If needed: Create keypair, CSR, and get it signed"""
    if check_mtls_init():
        return
    LOGGER.info("No mTLS client cert yet, creating it, this will take a moment")
    keypair = await asyncio.get_event_loop().run_in_executor(None, create_keypair)
    csr_path = await asyncio.get_event_loop().run_in_executor(None, create_csr, keypair)
    certpem = (await sign_csr(csr_path.read_text())).replace("\\n", "\n")
    cert_path = Path(settings.mtls_client_cert_path)
    cert_path.write_text(certpem, encoding="ascii")


async def get_session_winit() -> aiohttp.ClientSession:
    """wrap libpvarki get_session to init checks"""
    await mtls_init()
    cert_path = Path(settings.mtls_client_cert_path)
    key_path = Path(settings.mtls_client_key_path)
    return libsession((cert_path, key_path))
