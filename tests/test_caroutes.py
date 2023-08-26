"""Test the CA routes"""
from pathlib import Path
import logging

import pytest
from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621


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


@pytest.mark.asyncio
async def test_sign(csrfile: Path, kraftwerk_jwt_client: TestClient) -> None:
    """Test signing once"""
    certpath = csrfile.parent / "mtlsclient.pem"
    capath = csrfile.parent / "mtlsca.pem"
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
    LOGGER.debug("payload={}".format(payload))
    assert "ca" in payload
    capem = payload["ca"].replace("\\n", "\n")
    capath.write_text(capem)
    assert "certificate" in payload
    certpem = payload["certificate"].replace("\\n", "\n")
    certpath.write_text(certpem)
