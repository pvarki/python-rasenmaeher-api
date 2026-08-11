"""Test the cert-manager public surface: CA bundle reads and the CRL placeholders"""

import logging
from pathlib import Path
from typing import Any

import cryptography.x509
import pytest

from rasenmaeher_api.cert.cert_manager import public
from rasenmaeher_api.cert.cert_manager.base import CertManagerError
from rasenmaeher_api.rmsettings import RMSettings
from tests.cert.helpers import FakePKI

LOGGER = logging.getLogger(__name__)


@pytest.fixture()
def ca_bundle_path(monkeypatch: pytest.MonkeyPatch, ca_chain_path: Path) -> RMSettings:
    """Point cert_manager_ca_bundle_path at the test trust bundle"""
    settings = RMSettings.singleton()
    monkeypatch.setattr(settings, "cert_manager_ca_bundle_path", str(ca_chain_path))
    return settings


@pytest.mark.asyncio(loop_scope="function")
async def test_get_ca_reads_the_mounted_bundle(ca_bundle_path: RMSettings, ca_chain_pem: str) -> None:
    """The CA bundle is returned verbatim from the configured path"""
    _ = ca_bundle_path
    assert await public.get_ca() == ca_chain_pem


@pytest.mark.asyncio(loop_scope="function")
async def test_get_ca_missing_path_wrapped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A missing bundle surfaces as CertManagerError naming the path, not FileNotFoundError"""
    missing = tmp_path / "nosuch.pem"
    monkeypatch.setattr(RMSettings.singleton(), "cert_manager_ca_bundle_path", str(missing))
    with pytest.raises(CertManagerError, match=str(missing)):
        await public.get_ca()


@pytest.mark.asyncio(loop_scope="function")
async def test_get_ca_unreadable_path_wrapped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Any other OSError, here a directory instead of a file, is wrapped too"""
    monkeypatch.setattr(RMSettings.singleton(), "cert_manager_ca_bundle_path", str(tmp_path))
    with pytest.raises(CertManagerError):
        await public.get_ca()


@pytest.mark.parametrize("coro_name, args", (("get_crl", ()), ("get_ocsprest_crl", ("/crl.der",))))
@pytest.mark.asyncio(loop_scope="function")
async def test_crl_helpers_are_empty(coro_name: str, args: tuple[Any, ...]) -> None:
    """There is no CRL under cert-manager, revocation rides the Traefik plugin instead"""
    assert await getattr(public, coro_name)(*args) == b""


@pytest.mark.asyncio(loop_scope="function")
async def test_get_bundle_appends_the_chain(ca_bundle_path: RMSettings, pki: FakePKI) -> None:
    """get_bundle appends the CA chain to the cert and drops the self-signed root"""
    _ = ca_bundle_path
    out = await public.get_bundle(pki.leaf)
    certs = cryptography.x509.load_pem_x509_certificates(out.encode("utf-8"))
    assert [cert.subject.rfc4514_string() for cert in certs] == ["CN=test leaf", "CN=localmaeher,OU=RASENMAEHER"]
