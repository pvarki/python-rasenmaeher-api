"""Test product CSR signing error mapping"""

import pytest
from fastapi import HTTPException

from rasenmaeher_api.web.api.product import views
from rasenmaeher_api.web.api.product.schema import CertificatesRequest


@pytest.mark.asyncio
async def test_csr_common_rejected_csr_is_400(monkeypatch: pytest.MonkeyPatch) -> None:
    """A CSR the signer refuses is the caller's error, not a server error"""

    async def fake_get_ca() -> str:
        return "ca"

    async def refuse(csr: str) -> str:
        raise ValueError(f"CSR {csr} requests usages not allowed for it")

    monkeypatch.setattr(views, "get_ca", fake_get_ca)
    monkeypatch.setattr(views, "sign_csr", refuse)
    with pytest.raises(HTTPException) as excinfo:
        await views.csr_common(CertificatesRequest(csr="x"))
    assert excinfo.value.status_code == 400
    assert "not allowed" in str(excinfo.value.detail)
