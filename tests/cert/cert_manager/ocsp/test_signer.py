"""Test how OCSP signing material is loaded and cached.

tests/test_ocsp.py injects material into the cache directly, so nothing there
exercises the Secret fetch, the EC key check, or the rotation refresh.
"""

import asyncio
import base64
import hashlib
import logging
import time
from unittest.mock import AsyncMock

import pytest
from cloudcoil.models.kubernetes.core.v1 import Secret
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from rasenmaeher_api.cert.cert_manager.base import CertManagerError
from rasenmaeher_api.cert.cert_manager.ocsp import signer
from rasenmaeher_api.rmsettings import RMSettings

from .helpers import SigningCA

LOGGER = logging.getLogger(__name__)


def _b64(raw: bytes) -> str:
    """Secret data values are base64, as the k8s API returns them"""
    return base64.b64encode(raw).decode("ascii")


def test_load_material_computes_rfc6960_hashes(ocsp_ca: SigningCA) -> None:
    """Issuer name and key hashes follow RFC 6960 4.1.1.

    Recomputed here with hashlib rather than the module's own helper: if what gets
    hashed ever changes, every OCSP client silently stops matching our responses.
    """
    material = signer._load_material(ocsp_ca.cert_pem, ocsp_ca.key_pem)

    public_key = ocsp_ca.cert.public_key()
    assert isinstance(public_key, ec.EllipticCurvePublicKey)
    key_bits = public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    assert material.name_hashes["sha256"] == hashlib.sha256(ocsp_ca.cert.subject.public_bytes()).digest()
    assert material.key_hashes["sha256"] == hashlib.sha256(key_bits).digest()
    # Both algorithms cert-manager clients may ask for are precomputed
    assert set(material.name_hashes) == {"sha1", "sha256"}
    assert set(material.key_hashes) == {"sha1", "sha256"}


def test_load_material_rejects_non_ec_key(ocsp_ca: SigningCA) -> None:
    """A non-EC CA key fails loudly instead of blowing up later inside builder.sign"""
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with pytest.raises(CertManagerError, match="RSAPrivateKey"):
        signer._load_material(ocsp_ca.cert_pem, rsa_pem)


@pytest.mark.asyncio(loop_scope="function")
async def test_fetch_secret_loads_the_tls_pair(monkeypatch: pytest.MonkeyPatch, ocsp_ca: SigningCA) -> None:
    """tls.crt and tls.key are base64-decoded out of the Secret into usable material"""
    secret = Secret(data={"tls.crt": _b64(ocsp_ca.cert_pem), "tls.key": _b64(ocsp_ca.key_pem)})
    monkeypatch.setattr(Secret, "async_get", AsyncMock(return_value=secret))

    material = await signer._fetch_secret("ca-tls", "test-ns")

    assert material.cert.subject == ocsp_ca.cert.subject
    assert isinstance(material.key, ec.EllipticCurvePrivateKey)


@pytest.mark.parametrize("data", (None, {"tls.crt": "Zm9v"}, {"tls.key": "Zm9v"}))
@pytest.mark.asyncio(loop_scope="function")
async def test_fetch_secret_missing_key_wrapped(monkeypatch: pytest.MonkeyPatch, data: dict[str, str] | None) -> None:
    """A Secret without both halves names what is missing rather than raising KeyError"""
    monkeypatch.setattr(Secret, "async_get", AsyncMock(return_value=Secret(data=data)))
    with pytest.raises(CertManagerError, match="missing key"):
        await signer._fetch_secret("ca-tls", "test-ns")


def _tls_secret(ocsp_ca: SigningCA) -> Secret:
    """The Secret cert-manager writes for a CA Certificate"""
    return Secret(data={"tls.crt": _b64(ocsp_ca.cert_pem), "tls.key": _b64(ocsp_ca.key_pem)})


@pytest.mark.asyncio(loop_scope="function")
async def test_get_signer_fetches_once_then_caches(monkeypatch: pytest.MonkeyPatch, ocsp_ca: SigningCA) -> None:
    """Every OCSP request would otherwise hit the k8s API, so the second call must be cached"""
    get_secret = AsyncMock(return_value=_tls_secret(ocsp_ca))
    monkeypatch.setattr(Secret, "async_get", get_secret)
    settings = RMSettings.singleton()

    first = await signer.get_signer()
    second = await signer.get_signer()

    assert first is second
    assert first.cert.subject == ocsp_ca.cert.subject
    assert get_secret.await_count == 1
    # Which Secret we look for comes from settings, name first then namespace
    assert get_secret.await_args_list[0].args == (settings.ocsp_ca_secret_name, settings.ocsp_ca_secret_namespace)


@pytest.mark.asyncio(loop_scope="function")
async def test_get_signer_fetches_once_under_concurrency(monkeypatch: pytest.MonkeyPatch, ocsp_ca: SigningCA) -> None:
    """Concurrent callers on a cold cache must not each hit the k8s API.

    This is what the double-checked lock buys: a burst of OCSP requests after a restart
    would otherwise fire one Secret read each.
    """
    secret = _tls_secret(ocsp_ca)
    release = asyncio.Event()

    async def _blocking_get(name: str, namespace: str) -> Secret:
        await release.wait()  # hold the lock so the other caller queues behind it
        return secret

    get_secret = AsyncMock(side_effect=_blocking_get)
    monkeypatch.setattr(Secret, "async_get", get_secret)

    waiting = asyncio.gather(signer.get_signer(), signer.get_signer())
    while get_secret.await_count == 0:
        await asyncio.sleep(0)  # let both callers reach the lock
    release.set()
    first, second = await waiting

    assert first is second
    assert get_secret.await_count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_get_signer_refreshes_when_stale(monkeypatch: pytest.MonkeyPatch, ocsp_ca: SigningCA) -> None:
    """Stale material is refetched, which is how CA rotation is picked up without a restart"""
    stale = signer.SignerMaterial(cert=ocsp_ca.cert, key=ocsp_ca.key, fetched=time.monotonic() - signer.CACHE_TTL - 1)
    assert stale.expired is True
    monkeypatch.setattr(signer, "_CACHED", stale)
    get_secret = AsyncMock(return_value=_tls_secret(ocsp_ca))
    monkeypatch.setattr(Secret, "async_get", get_secret)

    refreshed = await signer.get_signer()

    assert refreshed is not stale
    assert refreshed.expired is False
    assert get_secret.await_count == 1
