"""Init mTLS client cert for RASENMAEHER itself"""

import asyncio
import logging
import random
from pathlib import Path

import aiohttp
import filelock
from libpvarki.mtlshelp.csr import async_create_client_csr, async_create_keypair, resolve_filepaths
from libpvarki.mtlshelp.session import get_session as libsession

from .cert.errors import CertError
from .rmsettings import CertBackend, RMSettings

LOGGER = logging.getLogger(__name__)


async def _anon_sign_csr(csr: str) -> str:
    """Lazy import wrapper to avoid circular imports.

    The circular import chain is:
    productapihelpers -> mtlsinit -> cert.cfssl.anoncsr (at module load)
    productapihelpers -> cert/__init__ -> cfssl/__init__ -> private -> mtls -> mtlsinit.get_session_winit
    """
    backend = RMSettings.singleton().cert_backend
    if backend == CertBackend.CERT_MANAGER:
        from .cert.cert_manager.anoncsr import anon_sign_csr
    elif backend == CertBackend.CFSSL:
        from .cert.cfssl.anoncsr import anon_sign_csr
    else:
        raise ValueError(f"Unknown cert backend: {backend}")
    return await anon_sign_csr(csr)


CERT_NAME_PREFIX = "rm_mtls_client"


def check_settings_clientpaths() -> bool:
    """Make sure the paths are defined, to defaults if needed, return True if setting was changed"""
    changed = False
    config = RMSettings.singleton()
    if not config.mtls_client_cert_path:
        config.mtls_client_cert_path = str(Path(config.persistent_data_dir) / "public" / f"{CERT_NAME_PREFIX}.pem")
        changed = True
    if not config.mtls_client_key_path:
        config.mtls_client_key_path = str(Path(config.persistent_data_dir) / "private" / f"{CERT_NAME_PREFIX}.key")
        changed = True
    return changed


def check_mtls_init() -> bool:
    """Check if we have the cert and key"""
    check_settings_clientpaths()
    config = RMSettings.singleton()
    assert config.mtls_client_cert_path is not None  # nosec B101
    assert config.mtls_client_key_path is not None  # nosec B101
    cert_path = Path(config.mtls_client_cert_path)
    key_path = Path(config.mtls_client_key_path)
    LOGGER.debug(f"cert_path={cert_path}  exits={cert_path.exists()}")
    LOGGER.debug(f"key_path={key_path}  exits={key_path.exists()}")
    return bool(cert_path.exists() and key_path.exists())


async def mtls_init() -> None:
    """If needed: Create keypair, CSR, and get it signed"""
    if check_mtls_init():
        return
    privkeypath, pubkeypath, csrpath = resolve_filepaths(
        Path(RMSettings.singleton().persistent_data_dir), CERT_NAME_PREFIX
    )
    check_settings_clientpaths()
    config = RMSettings.singleton()
    assert config.mtls_client_key_path is not None  # nosec B101
    assert config.mtls_client_cert_path is not None  # nosec B101
    if (pth := Path(config.mtls_client_key_path)) != privkeypath:
        privkeypath = pth
    certpath = pubkeypath.parent / f"{CERT_NAME_PREFIX}.pem"
    if (pth := Path(config.mtls_client_cert_path)) != certpath:
        certpath = pth
    lockpath = privkeypath.with_suffix(".lock")
    # Random sleep to avoid race conditions on these file accesses
    await asyncio.sleep(random.random() * 3.0)  # nosec B311
    lock = filelock.FileLock(lockpath)
    csrpem: str | None = None
    try:
        lock.acquire(timeout=0.0)
        # Check the privkey again to avoid overwriting.
        if not privkeypath.exists():
            LOGGER.info("No mTLS client cert yet, creating it, this will take a moment")
            keypair = await async_create_keypair(privkeypath, pubkeypath, ktype=config.cert_key_type)
            LOGGER.debug("Creating mTLS client CSR")
            csrpem = await async_create_client_csr(keypair, csrpath, {"CN": config.mtls_client_cert_cn})
        if not certpath.exists():
            if not csrpem:
                LOGGER.debug(f"Loading mTLS client CSR from {csrpath}")
                csrpem = csrpath.read_text()
            try:
                LOGGER.debug("Getting CSR signed")
                certpem = (await _anon_sign_csr(csrpem)).replace("\\n", "\n")
                LOGGER.debug(f"Saving mTLS cert to {certpath}")
                certpath.write_text(certpem, encoding="ascii")
                # Lazy import, see _anon_sign_csr for the circular import chain
                from rasenmaeher_api.db.issuedcerts import record_issued_cert

                await record_issued_cert(certpem)
            except CertError:
                LOGGER.exception("Signing failed")
    except filelock.Timeout:
        LOGGER.warning(f"Someone has already locked {lockpath}")
        LOGGER.debug("Sleeping for ~5s and then recursing")
        await asyncio.sleep(5.0 + random.random())  # nosec B311
        return await mtls_init()
    finally:
        lock.release()


async def get_session_winit() -> aiohttp.ClientSession:
    """wrap libpvarki get_session to init checks"""
    await mtls_init()
    check_settings_clientpaths()
    config = RMSettings.singleton()
    assert config.mtls_client_cert_path is not None  # nosec B101
    assert config.mtls_client_key_path is not None  # nosec B101
    cert_path = Path(config.mtls_client_cert_path)
    key_path = Path(config.mtls_client_key_path)
    return libsession((cert_path, key_path))
