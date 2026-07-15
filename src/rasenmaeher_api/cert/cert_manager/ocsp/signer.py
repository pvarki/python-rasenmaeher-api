"""OCSP response signing material.

Responses are signed directly with the intermediate CA key, read from the
cert-manager ``kubernetes.io/tls`` Secret via cloudcoil (rmapi has a pinned
RBAC grant for it).
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
import asyncio
import base64
import logging
import time

from cloudcoil.models.kubernetes.core.v1 import Secret
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from rasenmaeher_api.rmsettings import RMSettings
from rasenmaeher_api.cert.cert_manager.base import CertManagerError

LOGGER = logging.getLogger(__name__)

CACHE_TTL = 600.0  # seconds; picks up CA rotation without a restart
HASH_ALGORITHMS = {
    "sha1": hashes.SHA1,
    "sha256": hashes.SHA256,
}


@dataclass
class SignerMaterial:
    """CA cert + key with issuer hashes precomputed for request matching"""

    cert: x509.Certificate
    key: ec.EllipticCurvePrivateKey
    name_hashes: Dict[str, bytes] = field(init=False)
    key_hashes: Dict[str, bytes] = field(init=False)
    fetched: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        # RFC 6960 4.1.1: issuerNameHash is over the DER of the issuer subject,
        # issuerKeyHash over the subjectPublicKey BIT STRING content, which for
        # EC keys is the uncompressed point.
        name_der = self.cert.subject.public_bytes()
        key_bits = self.cert.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.name_hashes = {name: _digest(name_der, alg()) for name, alg in HASH_ALGORITHMS.items()}
        self.key_hashes = {name: _digest(key_bits, alg()) for name, alg in HASH_ALGORITHMS.items()}

    @property
    def expired(self) -> bool:
        """Should this material be refreshed"""
        return time.monotonic() - self.fetched > CACHE_TTL


def _digest(data: bytes, algorithm: hashes.HashAlgorithm) -> bytes:
    """Hash data with the given algorithm"""
    hasher = hashes.Hash(algorithm)
    hasher.update(data)
    return hasher.finalize()


def _load_material(cert_pem: bytes, key_pem: bytes) -> SignerMaterial:
    """Parse PEMs into SignerMaterial, enforcing the expected EC key type"""
    cert = x509.load_pem_x509_certificate(cert_pem)
    key = serialization.load_pem_private_key(key_pem, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise CertManagerError(f"OCSP CA key is {type(key).__name__}, expected an EC key")
    return SignerMaterial(cert=cert, key=key)


async def _fetch_secret(name: str, namespace: str) -> SignerMaterial:
    """Load signing material from the cert-manager tls Secret via the k8s API"""
    LOGGER.debug("Fetching OCSP signing material from secret {}/{}".format(namespace, name))
    secret = await Secret.async_get(name, namespace)
    data = secret.data or {}
    try:
        cert_pem = base64.b64decode(data["tls.crt"])
        key_pem = base64.b64decode(data["tls.key"])
    except KeyError as exc:
        raise CertManagerError(f"Secret {namespace}/{name} is missing key {exc}") from exc
    return _load_material(cert_pem, key_pem)


_CACHED: Optional[SignerMaterial] = None
_LOCK = asyncio.Lock()


async def get_signer() -> SignerMaterial:
    """Get cached signing material, refreshing when stale"""
    global _CACHED
    if _CACHED and not _CACHED.expired:
        return _CACHED
    async with _LOCK:
        if _CACHED and not _CACHED.expired:
            return _CACHED
        settings = RMSettings.singleton()
        _CACHED = await _fetch_secret(settings.ocsp_ca_secret_name, settings.ocsp_ca_secret_namespace)
        return _CACHED
