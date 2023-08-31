"""Test the CA routes"""
from typing import Tuple, Generator
from pathlib import Path
import logging
import asyncio

import pytest
import pytest_asyncio
from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from async_asgi_testclient import TestClient  # pylint: disable=import-error

from rasenmaeher_api.web.api.product.views import sign_csr, get_ca

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Module scoped event loop so we don't have to regenrate keys etc for every test"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def datadir(nice_tmpdir_mod: str) -> Path:
    """Make sure we have a well known directory structure"""
    datadir = Path(nice_tmpdir_mod) / "persistent"
    datadir.mkdir(parents=True)
    privdir = datadir / "private"
    pubdir = datadir / "public"
    privdir.mkdir()
    pubdir.mkdir()
    return datadir


@pytest.fixture(scope="module")
def keypair(datadir: Path) -> crypto.PKey:
    """Generate a keypair"""
    privkeypath = datadir / "private" / "mtlsclient.key"
    pubkeypath = datadir / "public" / "mtlsclient.pub"
    ckp = crypto.PKey()
    LOGGER.debug("Generating keypair, this will take a moment")
    ckp.generate_key(crypto.TYPE_RSA, 4096)
    LOGGER.debug("Done")
    with privkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ckp))
    with pubkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_publickey(crypto.FILETYPE_PEM, ckp))
    return ckp


@pytest.fixture(scope="module")
def csrfile(datadir: Path, keypair: crypto.PKey) -> Path:
    """Generate CSR file"""
    csrpath = datadir / "public" / "mtlsclient.csr"
    req = crypto.X509Req()
    req.get_subject().CN = "product.localmaeher.pvarki.fi"
    req.add_extensions(
        [
            crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
            crypto.X509Extension(b"extendedKeyUsage", True, b"clientAuth"),
        ]
    )
    req.set_pubkey(keypair)
    req.sign(keypair, "sha256")
    with csrpath.open("wb") as fpntr:
        fpntr.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))

    return csrpath


def test_have_csrfile(csrfile: Path) -> None:
    """Check that csr generation works"""
    assert csrfile.exists()


@pytest_asyncio.fixture(scope="module")
async def mtlsfiles(csrfile: Path) -> Tuple[Path, Path, Path]:
    """Return cert, key and ca cert paths, this will sign the CSR again every time due to fixture scoping issues"""
    privkeypath = csrfile.parent.parent / "private" / "mtlsclient.key"
    assert privkeypath.exists()
    certpath = csrfile.parent / "mtlsclient.pem"
    capath = csrfile.parent / "mtlsca.pem"
    capem = (await get_ca()).replace("\\n", "\n")
    LOGGER.debug("capem={}".format(capem))
    certpem = (await sign_csr(csrfile.read_text())).replace("\\n", "\n")
    LOGGER.debug("certpem={}".format(certpem))
    capath.write_text(capem)
    certpath.write_text(certpem)
    return certpath, privkeypath, capath


@pytest.mark.asyncio
async def test_have_mtlscert(mtlsfiles: Tuple[Path, Path, Path]) -> None:
    """Test that we got the files"""
    certpath, privkeypath, capath = mtlsfiles
    assert certpath.exists()
    assert privkeypath.exists()
    assert capath.exists()


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
