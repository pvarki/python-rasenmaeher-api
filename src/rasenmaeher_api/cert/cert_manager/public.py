"""Public surface for cert-manager backend - CA cert, CRL etc.

The CA bundle is read from a path mounted into the rmapi pod (the same
``opendefence-bundle`` ConfigMap that already feeds mTLS trust). CRLs are
not produced under cert-manager — revocation is consumed by the Traefik
plugin via websocket — so the CRL helpers return an empty placeholder.
"""

import asyncio
import logging
from pathlib import Path

from ...rmsettings import RMSettings
from .base import CertManagerError


LOGGER = logging.getLogger(__name__)


def _read_ca_sync(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


async def get_ca() -> str:
    """Return the CA bundle PEM from the mounted ConfigMap file."""
    settings = RMSettings.singleton()
    path = settings.cert_manager_ca_bundle_path
    try:
        return await asyncio.to_thread(_read_ca_sync, path)
    except FileNotFoundError as exc:
        raise CertManagerError(f"CA bundle not found at {path}") from exc
    except OSError as exc:
        raise CertManagerError(f"Failed to read CA bundle from {path}: {exc}") from exc


async def get_ocsprest_crl(suffix: str) -> bytes:
    """No CRL under cert-manager. Returns an empty byte string."""
    LOGGER.debug("get_ocsprest_crl called under cert-manager backend (suffix=%s); empty response", suffix)
    return b""


async def get_crl() -> bytes:
    """No CRL under cert-manager. Returns an empty byte string."""
    LOGGER.debug("get_crl called under cert-manager backend; empty response")
    return b""


async def get_bundle(cert: str) -> str:
    """Return cert concatenated with the CA bundle."""
    ca_pem = await get_ca()
    if not cert.endswith("\n"):
        cert = cert + "\n"
    return cert + ca_pem
