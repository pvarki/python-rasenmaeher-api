"""Test users own info things"""
import logging

import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error
from cryptography.hazmat.primitives.serialization import pkcs12

LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("fname", ["ENROLLUSERa", "ENROLLUSERa.pfx"])
@pytest.mark.asyncio(scope="session")
async def test_user_pfx(user_mtls_client: TestClient, fname: str) -> None:
    """Test that we can get the pfx"""
    client = user_mtls_client
    url = f"/api/v1/enduserpfx/{fname}"
    resp = await client.get(url)
    LOGGER.debug(resp)
    resp.raise_for_status()
    pfxdata = pkcs12.load_pkcs12(resp.content, fname.replace(".pfx", "").encode("utf-8"))
    assert pfxdata.key
    assert pfxdata.cert
