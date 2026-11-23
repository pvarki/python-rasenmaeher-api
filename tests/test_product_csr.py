"""Test product CSR signing error mapping"""

import pytest
from fastapi import HTTPException

from rasenmaeher_api.web.api.product import views
from rasenmaeher_api.web.api.product.schema import CertificatesRequest
from tests.cert.helpers import CsrFactory, invalidate_signature


@pytest.mark.asyncio
async def test_csr_common_rejected_csr_is_400(monkeypatch: pytest.MonkeyPatch, mint_csr: CsrFactory) -> None:
    """A CSR the signer refuses is the caller's error, not a server error"""

    async def fake_get_ca() -> str:
        return "ca"

    async def refuse(csr: str) -> str:
        raise ValueError("CSR requests usages not allowed for it")

    monkeypatch.setattr(views, "get_ca", fake_get_ca)
    monkeypatch.setattr(views, "sign_csr", refuse)
    with pytest.raises(HTTPException) as excinfo:
        await views.csr_common(CertificatesRequest(csr=mint_csr()))
    assert excinfo.value.status_code == 400
    assert "not allowed" in str(excinfo.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("broken", ["invalid-signature", "not-a-csr"])
async def test_csr_common_requires_csr_signed_by_its_key(
    monkeypatch: pytest.MonkeyPatch, mint_csr: CsrFactory, broken: str
) -> None:
    """A CSR whose signature does not verify with its own key never reaches the signer"""

    async def must_not_sign(csr: str) -> str:
        raise AssertionError("signer called")

    monkeypatch.setattr(views, "sign_csr", must_not_sign)
    csrpem = invalidate_signature(mint_csr()) if broken == "invalid-signature" else "not a CSR"
    with pytest.raises(HTTPException) as excinfo:
        await views.csr_common(CertificatesRequest(csr=csrpem))
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "CSR is not signed by its own key"
