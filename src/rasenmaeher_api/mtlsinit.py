"""Init mTLS client cert for RASENMAEHER itself"""
import asyncio
from pathlib import Path
import logging
import random

from libpvarki.mtlshelp.session import get_session as libsession
from libpvarki.mtlshelp.csr import async_create_client_csr, async_create_keypair, resolve_filepaths
import aiohttp
import filelock


from .cfssl.anoncsr import anon_sign_csr
from .settings import settings

LOGGER = logging.getLogger(__name__)
CERT_NAME_PREFIX = "rm_mtls_client"


def check_settings_clientpaths() -> bool:
    """Make sure the paths are defined, to defaults if needed, return True if setting was changed"""
    changed = False
    if not settings.mtls_client_cert_path:
        settings.mtls_client_cert_path = str(Path(settings.persistent_data_dir) / "public" / f"{CERT_NAME_PREFIX}.pem")
        changed = True
    if not settings.mtls_client_key_path:
        settings.mtls_client_key_path = str(Path(settings.persistent_data_dir) / "private" / f"{CERT_NAME_PREFIX}.key")
        changed = True
    return changed


def check_mtls_init() -> bool:
    """Check if we have the cert and key"""
    check_settings_clientpaths()
    assert settings.mtls_client_cert_path is not None
    assert settings.mtls_client_key_path is not None
    cert_path = Path(settings.mtls_client_cert_path)
    key_path = Path(settings.mtls_client_key_path)
    LOGGER.debug("cert_path={}  exits={}".format(cert_path, cert_path.exists()))
    LOGGER.debug("key_path={}  exits={}".format(key_path, key_path.exists()))
    if cert_path.exists() and key_path.exists():
        return True
    return False


async def mtls_init() -> None:
    """If needed: Create keypair, CSR, and get it signed"""
    if check_mtls_init():
        return
    privkeypath, pubkeypath, csrpath = resolve_filepaths(Path(settings.persistent_data_dir), CERT_NAME_PREFIX)
    check_settings_clientpaths()
    assert settings.mtls_client_key_path is not None
    assert settings.mtls_client_cert_path is not None
    if (pth := Path(settings.mtls_client_key_path)) != privkeypath:
        privkeypath = pth
    certpath = pubkeypath.parent / f"{CERT_NAME_PREFIX}.pem"
    if (pth := Path(settings.mtls_client_cert_path)) != certpath:
        certpath = pth
    lockpath = privkeypath.with_suffix(".lock")
    # Random sleep to avoid race conditions on these file accesses
    await asyncio.sleep(random.random() * 3.0)  # nosec
    lock = filelock.FileLock(lockpath)
    try:
        lock.acquire(timeout=0.0)
        # Check the privkey again to avoid overwriting.
        if privkeypath.exists():
            return None
        LOGGER.info("No mTLS client cert yet, creating it, this will take a moment")
        keypair = await async_create_keypair(privkeypath, pubkeypath)
        csrpem = await async_create_client_csr(keypair, csrpath, {"CN": settings.mtls_client_cert_cn})
        certpem = (await anon_sign_csr(csrpem)).replace("\\n", "\n")
    except filelock.Timeout:
        LOGGER.warning("Someone has already locked {}".format(lockpath))
        LOGGER.debug("Sleeping for ~5s and then recursing")
        await asyncio.sleep(5.0 + random.random())  # nosec
        return await mtls_init()
    finally:
        lock.release()
    certpath.write_text(certpem, encoding="ascii")


async def get_session_winit() -> aiohttp.ClientSession:
    """wrap libpvarki get_session to init checks"""
    await mtls_init()
    check_settings_clientpaths()
    assert settings.mtls_client_cert_path is not None
    assert settings.mtls_client_key_path is not None
    cert_path = Path(settings.mtls_client_cert_path)
    key_path = Path(settings.mtls_client_key_path)
    return libsession((cert_path, key_path))
