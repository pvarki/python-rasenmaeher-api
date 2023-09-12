"""Test the CA routes"""
from typing import Tuple
from pathlib import Path
import logging

import pytest
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


def test_have_csrfile(csrfile: Path) -> None:
    """Check that csr generation works"""
    assert csrfile.exists()


@pytest.mark.asyncio
async def test_have_mtlscert(mtlsfiles: Tuple[Path, Path]) -> None:
    """Test that we got the files"""
    certpath, privkeypath = mtlsfiles
    assert certpath.exists()
    assert privkeypath.exists()


@pytest.mark.asyncio
async def test_sign(csrfile: Path, kraftwerk_jwt_client: TestClient) -> None:
    """Test signing"""
    client = kraftwerk_jwt_client
    resp = await client.post(
        "/api/v1/product/sign_csr",
        json={
            "csr": csrfile.read_text(),
        },
    )
    LOGGER.debug("Got response {}".format(resp))
    resp.raise_for_status()
    payload = resp.json()
    assert "certificate" in payload
    assert "ca" in payload


@pytest.mark.xfail(reason="Nonce checking not implemented yet")
@pytest.mark.asyncio
async def test_sign_twice(csrfile: Path, kraftwerk_jwt_client: TestClient) -> None:
    """Test using same nonce twice, should fail"""
    # First signing, should work fine
    client = kraftwerk_jwt_client
    resp = await client.post(
        "/api/v1/product/sign_csr",
        json={
            "csr": csrfile.read_text(),
        },
    )
    LOGGER.debug("Got response {}".format(resp))
    resp.raise_for_status()
    payload = resp.json()
    assert "certificate" in payload

    # Second signing, should return 401
    resp2 = await client.post(
        "/api/v1/product/sign_csr",
        json={
            "csr": csrfile.read_text(),
        },
    )
    LOGGER.debug("Got second response {}".format(resp2))
    assert resp2.status_code == 401
