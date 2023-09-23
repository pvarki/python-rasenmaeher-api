"""Init mTLS client cert for RASENMAEHER itself"""
import asyncio
from pathlib import Path
import logging
import random


from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from libpvarki.mtlshelp.session import get_session as libsession
import aiohttp
import filelock


from .cfssl.anoncsr import anon_sign_csr
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
    privkeypath = Path(settings.mtls_client_key_path)
    lockpath = privkeypath.with_suffix(".lock")
    # Random sleep to avoid race conditions on these file accesses
    await asyncio.sleep(random.random() * 3.0)  # nosec
    lock = filelock.FileLock(lockpath)
    try:
        lock.acquire(timeout=0.0)
        privkeypath = Path(settings.mtls_client_key_path)
        # Check the privkey again to avoid overwriting.
        if privkeypath.exists():
            return None
        LOGGER.info("No mTLS client cert yet, creating it, this will take a moment")
        keypair = await asyncio.get_event_loop().run_in_executor(None, create_keypair)
        csr_path = await asyncio.get_event_loop().run_in_executor(None, create_csr, keypair)
        certpem = (await anon_sign_csr(csr_path.read_text())).replace("\\n", "\n")
    except filelock.Timeout:
        LOGGER.warning("Someone has already locked {}".format(lockpath))
        LOGGER.debug("Sleeping for ~5s and then recursing")
        await asyncio.sleep(5.0 + random.random())  # nosec
        return await mtls_init()
    finally:
        lock.release()
    cert_path = Path(settings.mtls_client_cert_path)
    cert_path.write_text(certpem, encoding="ascii")


async def get_session_winit() -> aiohttp.ClientSession:
    """wrap libpvarki get_session to init checks"""
    await mtls_init()
    cert_path = Path(settings.mtls_client_cert_path)
    key_path = Path(settings.mtls_client_key_path)
    return libsession((cert_path, key_path))
