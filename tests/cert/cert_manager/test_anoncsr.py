"""Test that anonymous CSR signing is a straight delegation under cert-manager"""

import logging

import pytest

from rasenmaeher_api.cert.cert_manager import anoncsr

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio(loop_scope="function")
async def test_anon_sign_csr_forwards_to_sign_csr(monkeypatch: pytest.MonkeyPatch) -> None:
    """There is no anonymous path at the CA layer, so the bundle flag is forwarded as-is.

    The cfssl backend does have a separate anon session and endpoint, so this pins the
    deliberate difference rather than letting a future anon path appear unnoticed.
    """
    calls: list[tuple[str, bool]] = []

    async def _fake_sign_csr(csr: str, bundle: bool = True) -> str:
        calls.append((csr, bundle))
        return "signed pem"

    monkeypatch.setattr(anoncsr, "sign_csr", _fake_sign_csr)
    assert await anoncsr.anon_sign_csr("csr pem", bundle=False) == "signed pem"
    assert calls == [("csr pem", False)]
